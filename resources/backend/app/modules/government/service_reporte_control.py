"""Servicio para el Reporte de control interno (REP10-R1).

Consolida conflictos SoD, bloqueos de identidad, bloqueos de cierre y hallazgos/acciones
correctivas de un período, con exportación CSV auditada.
"""

from __future__ import annotations

import csv
import io
from collections import Counter
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import KontrolError
from app.modules.audit.models import AuditEvent
from app.modules.government import procesos as autoridad_procesos
from app.modules.government.models import (
    GovernmentCorrectiveAction,
    GovernmentFinding,
)
from app.modules.government.service_auditoria import _instante, _usuarios_por_ids
from app.modules.government.service_cierres import ACCIONES_CIERRE, TIPOS_CONTROL
from app.modules.government.service_hallazgos import _accion_vencida
from app.modules.government.service_separacion import _etiqueta_denegacion
from app.modules.government.service_sod_eventos import consultar, normalizar
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio, instante_actual, limites_del_dia_utc

ESTADOS_HALLAZGO = ["ABIERTO", "PLAN_DE_ACCION", "EN_REMEDIACION", "EVIDENCIA_PRESENTADA", "CERRADO"]
RIESGOS_HALLAZGO = ["ALTO", "MEDIO", "BAJO"]
ESTADOS_ACCION = ["PENDIENTE", "EN_CURSO", "COMPLETADA"]


def _etiqueta_proceso(codigo: str | None) -> str:
    if not codigo:
        return "Proceso no especificado"
    return autoridad_procesos.nombre_de(codigo) or codigo



def _eventos_periodo(
    db: Session,
    ctx: CompanyContext,
    action: str,
    desde: date,
    hasta: date,
    limite: int | None = None,
) -> list[AuditEvent]:
    inicio, fin = limites_del_dia_utc(desde), limites_del_dia_utc(hasta)
    stmt = (
        select(AuditEvent)
        .where(
            AuditEvent.tenant_id == ctx.tenant_id,
            AuditEvent.company_id == ctx.company_id,
            AuditEvent.action == action,
            AuditEvent.event_time >= inicio[0],
            AuditEvent.event_time < fin[1],
        )
        .order_by(AuditEvent.event_time.desc())
    )
    if limite is not None:
        stmt = stmt.limit(limite)
    return list(db.execute(stmt).scalars().all())


def _usuario_de(db: Session, ctx: CompanyContext, eventos: list[AuditEvent]) -> dict[str, str]:
    ids = {e.user_id for e in eventos if e.user_id is not None}
    return _usuarios_por_ids(db, list(ids), ctx.tenant_id)


def _seccion_conflictos_sod(
    db: Session,
    ctx: CompanyContext,
    desde: date,
    hasta: date,
    limite: int | None = None,
) -> dict[str, Any]:
    inicio = limites_del_dia_utc(desde)
    fin = limites_del_dia_utc(hasta)
    todos = consultar(db, ctx, inicio=inicio[0], fin=fin[1])
    normalizados = normalizar(db, ctx, todos)
    eventos = normalizados[:limite] if limite is not None else normalizados

    por_regla: Counter[tuple[str, str, str, str, str, str]] = Counter()
    for n in normalizados:
        por_regla[
            (
                n["regla_codigo"],
                n["regla_nombre"],
                n["proceso"],
                n["proceso_etiqueta"],
                n["tipo_conflicto"],
                n["tipo_conflicto_etiqueta"],
            )
        ] += 1

    por_proceso: Counter[tuple[str, str]] = Counter()
    por_tipo: Counter[tuple[str, str]] = Counter()
    for n in normalizados:
        por_proceso[(n["proceso"], n["proceso_etiqueta"])] += 1
        por_tipo[(n["tipo_conflicto"], n["tipo_conflicto_etiqueta"])] += 1

    eventos_serializados: list[dict[str, Any]] = []
    for n in eventos:
        eventos_serializados.append(
            {
                "evento_id": n["evento_id"],
                "fecha": n["fecha"].isoformat() if n["fecha"] else None,
                "usuario": n["usuario"],
                "regla_codigo": n["regla_codigo"],
                "regla_nombre": n["regla_nombre"],
                "proceso": n["proceso"],
                "proceso_etiqueta": n["proceso_etiqueta"],
                "tipo_conflicto": n["tipo_conflicto"],
                "tipo_conflicto_etiqueta": n["tipo_conflicto_etiqueta"],
                "recurso_etiqueta": n["recurso_etiqueta"],
                "accion_etiqueta": n["operacion_etiqueta"],
                "accion_previa_etiqueta": n["operacion_previa_etiqueta"],
            }
        )

    return {
        "total": len(todos),
        "por_regla": [
            {
                "regla_codigo": codigo,
                "regla_nombre": nombre,
                "proceso": proceso,
                "proceso_etiqueta": proceso_etiqueta,
                "tipo_conflicto": tipo_conflicto,
                "tipo_conflicto_etiqueta": tipo_conflicto_etiqueta,
                "total": total,
            }
            for (codigo, nombre, proceso, proceso_etiqueta, tipo_conflicto, tipo_conflicto_etiqueta), total in por_regla.most_common()
        ],
        "por_proceso": [
            {"proceso": proceso, "proceso_etiqueta": proceso_etiqueta, "total": total}
            for (proceso, proceso_etiqueta), total in por_proceso.most_common()
        ],
        "por_tipo": [
            {"tipo_conflicto": tipo_conflicto, "tipo_conflicto_etiqueta": tipo_conflicto_etiqueta, "total": total}
            for (tipo_conflicto, tipo_conflicto_etiqueta), total in por_tipo.most_common()
        ],
        "eventos": eventos_serializados,
    }


def _seccion_bloqueos_identidad(
    db: Session,
    ctx: CompanyContext,
    desde: date,
    hasta: date,
    limite: int | None = None,
) -> dict[str, Any]:
    todos = _eventos_periodo(db, ctx, "GOV_IDENTITY_GUARD_BLOCKED", desde, hasta)
    eventos = todos[:limite] if limite is not None else todos
    usuarios = _usuario_de(db, ctx, eventos)
    por_motivo: Counter[str] = Counter()
    eventos_serializados: list[dict[str, Any]] = []
    for e in todos:
        after = e.after or {}
        codigo = str(after.get("operacion") or "")
        por_motivo[codigo] += 1
    for e in eventos:
        after = e.after or {}
        codigo = str(after.get("operacion") or "")
        etiqueta = _etiqueta_denegacion(codigo)
        eventos_serializados.append(
            {
                "evento_id": str(e.id),
                "fecha": _instante(e.event_time).isoformat() if e.event_time else None,
                "usuario": usuarios.get(str(e.user_id)) if e.user_id is not None else None,
                "etiqueta": etiqueta,
            }
        )
    return {
        "total": len(todos),
        "por_motivo": [
            {"codigo": codigo, "etiqueta": _etiqueta_denegacion(codigo), "total": total}
            for codigo, total in por_motivo.most_common()
        ],
        "eventos": eventos_serializados,
    }


def _seccion_bloqueos_cierre(
    db: Session,
    ctx: CompanyContext,
    desde: date,
    hasta: date,
    limite: int | None = None,
) -> dict[str, Any]:
    todos = _eventos_periodo(db, ctx, "GOV_MATERIAL_CLOSE_BLOCKED", desde, hasta)
    eventos = todos[:limite] if limite is not None else todos
    usuarios = _usuario_de(db, ctx, eventos)
    por_politica: Counter[tuple[str, str]] = Counter()
    eventos_serializados: list[dict[str, Any]] = []
    for e in todos:
        after = e.after or {}
        politica_codigo = str(after.get("politica_codigo") or "")
        accion_cierre = str(after.get("accion_cierre") or "")
        accion_etiqueta = ACCIONES_CIERRE.get(accion_cierre, "Cierre")
        por_politica[(politica_codigo, accion_etiqueta)] += 1
    for e in eventos:
        after = e.after or {}
        politica_codigo = str(after.get("politica_codigo") or "")
        accion_cierre = str(after.get("accion_cierre") or "")
        accion_etiqueta = ACCIONES_CIERRE.get(accion_cierre, "Cierre")
        objeto_codigo = str(after.get("objeto_codigo") or "")
        controles_raw = after.get("controles") or []
        controles = [
            {
                "etiqueta": TIPOS_CONTROL.get(str(c.get("tipo") or ""), {}).get("etiqueta", "Control de cierre"),
                "pendientes": c.get("pendientes"),
            }
            for c in controles_raw
            if isinstance(c, dict)
        ]
        eventos_serializados.append(
            {
                "evento_id": str(e.id),
                "fecha": _instante(e.event_time).isoformat() if e.event_time else None,
                "usuario": usuarios.get(str(e.user_id)) if e.user_id is not None else None,
                "politica_codigo": politica_codigo,
                "accion_etiqueta": accion_etiqueta,
                "objeto_codigo": objeto_codigo,
                "controles": controles,
            }
        )
    return {
        "total": len(todos),
        "por_politica": [
            {"politica_codigo": codigo, "accion_etiqueta": etiqueta, "total": total}
            for (codigo, etiqueta), total in por_politica.most_common()
        ],
        "eventos": eventos_serializados,
    }


def _seccion_hallazgos(db: Session, ctx: CompanyContext, ver_hallazgos: bool) -> dict[str, Any]:
    if not ver_hallazgos:
        return {
            "disponible": False,
            "motivo": "Sin permiso para ver hallazgos (gobierno_hallazgos:view)",
            "por_estado": {},
            "por_riesgo": {},
            "acciones_por_estado": {},
            "acciones_vencidas": [],
        }

    hallazgos = list(
        db.execute(
            select(GovernmentFinding).where(
                GovernmentFinding.tenant_id == ctx.tenant_id,
                GovernmentFinding.company_id == ctx.company_id,
            )
        )
        .scalars()
        .all()
    )
    acciones = list(
        db.execute(
            select(GovernmentCorrectiveAction)
            .join(GovernmentFinding, GovernmentCorrectiveAction.finding_id == GovernmentFinding.id)
            .where(
                GovernmentFinding.tenant_id == ctx.tenant_id,
                GovernmentFinding.company_id == ctx.company_id,
            )
        )
        .scalars()
        .all()
    )
    hallazgos_por_id = {str(h.id): h for h in hallazgos}

    por_estado = {estado: 0 for estado in ESTADOS_HALLAZGO}
    for h in hallazgos:
        if h.estado in por_estado:
            por_estado[h.estado] += 1

    por_riesgo = {riesgo: 0 for riesgo in RIESGOS_HALLAZGO}
    for h in hallazgos:
        if h.riesgo in por_riesgo:
            por_riesgo[h.riesgo] += 1

    acciones_por_estado = {estado: 0 for estado in ESTADOS_ACCION}
    for a in acciones:
        if a.estado in acciones_por_estado:
            acciones_por_estado[a.estado] += 1

    hoy = hoy_de_negocio()
    acciones_vencidas = []
    for a in acciones:
        hallazgo = hallazgos_por_id.get(str(a.finding_id))
        if hallazgo is None or hallazgo.estado == "CERRADO":
            continue
        if not _accion_vencida(a):
            continue
        dias_atraso = (hoy - a.fecha_objetivo).days if a.fecha_objetivo else 0
        acciones_vencidas.append(
            {
                "hallazgo_id": str(hallazgo.id),
                "hallazgo_codigo": hallazgo.codigo,
                "hallazgo_titulo": hallazgo.titulo,
                "accion_orden": a.orden,
                "descripcion": a.descripcion,
                "cargo": a.cargo_denominacion,
                "unidad": a.unidad_nombre,
                "fecha_objetivo": a.fecha_objetivo.isoformat() if a.fecha_objetivo else None,
                "porcentaje": a.porcentaje,
                "dias_atraso": dias_atraso,
            }
        )
    acciones_vencidas.sort(
        key=lambda item: str(item["fecha_objetivo"] or "")
    )

    return {
        "disponible": True,
        "motivo": None,
        "por_estado": por_estado,
        "por_riesgo": por_riesgo,
        "acciones_por_estado": acciones_por_estado,
        "acciones_vencidas": acciones_vencidas,
    }


def _validar_periodo(desde: date | None, hasta: date | None) -> tuple[date, date]:
    hoy = hoy_de_negocio()
    fecha_desde = desde or date(hoy.year, 1, 1)
    fecha_hasta = hasta or hoy
    if fecha_desde > fecha_hasta:
        raise KontrolError(
            code="INVALID_DATE_RANGE",
            message="La fecha inicial no puede ser posterior a la fecha final",
            field_errors={"desde": ["La fecha inicial no puede ser posterior a la fecha final"]},
            status_code=422,
        )
    return fecha_desde, fecha_hasta


def _datos(
    db: Session,
    ctx: CompanyContext,
    *,
    fecha_desde: date,
    fecha_hasta: date,
    ver_hallazgos: bool,
    limite: int | None,
) -> dict[str, Any]:
    return {
        "periodo": {"desde": fecha_desde.isoformat(), "hasta": fecha_hasta.isoformat()},
        "generado_en": instante_actual().isoformat(),
        "conflictos_sod": _seccion_conflictos_sod(db, ctx, fecha_desde, fecha_hasta, limite),
        "bloqueos_identidad": _seccion_bloqueos_identidad(db, ctx, fecha_desde, fecha_hasta, limite),
        "bloqueos_cierre": _seccion_bloqueos_cierre(db, ctx, fecha_desde, fecha_hasta, limite),
        "hallazgos": _seccion_hallazgos(db, ctx, ver_hallazgos),
        "overrides": {
            "disponible": False,
            "motivo": "No aplica: en Gobierno los controles de segregación de funciones solo bloquean; no existe excepción ni dispensa (CTL-01).",
        },
        "operaciones_duplicadas": {
            "disponible": False,
            "motivo": "No disponible: requiere órdenes de pago y pagos (TRE-03, TRE-04), que aún no existen en Gobierno.",
        },
    }


def reporte(
    db: Session,
    ctx: CompanyContext,
    *,
    desde: date | None,
    hasta: date | None,
    ver_hallazgos: bool,
) -> dict[str, Any]:
    fecha_desde, fecha_hasta = _validar_periodo(desde, hasta)
    return _datos(
        db,
        ctx,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        ver_hallazgos=ver_hallazgos,
        limite=50,
    )


def exportar_csv(
    db: Session,
    ctx: CompanyContext,
    *,
    desde: date | None,
    hasta: date | None,
    ver_hallazgos: bool,
) -> tuple[str, bytes]:
    fecha_desde, fecha_hasta = _validar_periodo(desde, hasta)
    datos = _datos(
        db,
        ctx,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        ver_hallazgos=ver_hallazgos,
        limite=None,
    )
    salida = io.StringIO()
    writer = csv.writer(salida, quoting=csv.QUOTE_MINIMAL)
    filas = 0

    writer.writerow(["Reporte de control interno", fecha_desde, fecha_hasta])

    # Conflicto SoD
    writer.writerow(["Conflicto SoD"])
    writer.writerow(
        ["Fecha", "Usuario", "Regla", "Proceso", "Acción intentada", "Acción previa", "Tipo de conflicto", "Recurso"]
    )
    for evento in datos["conflictos_sod"]["eventos"]:
        writer.writerow(
            [
                evento["fecha"],
                evento["usuario"],
                evento["regla_codigo"] or evento["regla_nombre"],
                evento["proceso_etiqueta"],
                evento["accion_etiqueta"],
                evento["accion_previa_etiqueta"],
                evento["tipo_conflicto_etiqueta"],
                evento["recurso_etiqueta"] or "",
            ]
        )
        filas += 1

    # Bloqueo de identidad
    writer.writerow(["Bloqueo de identidad"])
    writer.writerow(["Fecha", "Usuario", "Motivo"])
    for evento in datos["bloqueos_identidad"]["eventos"]:
        writer.writerow([evento["fecha"], evento["usuario"], evento["etiqueta"]])
        filas += 1

    # Bloqueo de cierre
    writer.writerow(["Bloqueo de cierre"])
    writer.writerow(["Fecha", "Usuario", "Política", "Acción", "Objeto", "Controles"])
    for evento in datos["bloqueos_cierre"]["eventos"]:
        writer.writerow(
            [
                evento["fecha"],
                evento["usuario"],
                evento["politica_codigo"],
                evento["accion_etiqueta"],
                evento["objeto_codigo"],
                "; ".join(
                    f"{c['etiqueta']}: {c['pendientes']}"
                    for c in evento["controles"]
                ),
            ]
        )
        filas += 1

    # Acción vencida
    if ver_hallazgos and datos["hallazgos"]["disponible"]:
        writer.writerow(["Acción vencida"])
        writer.writerow(["Hallazgo", "Acción", "Cargo", "Unidad", "Fecha objetivo", "Avance %", "Días de atraso"])
        for accion in datos["hallazgos"]["acciones_vencidas"]:
            writer.writerow(
                [
                    accion["hallazgo_codigo"],
                    accion["descripcion"],
                    accion["cargo"],
                    accion["unidad"],
                    accion["fecha_objetivo"],
                    accion["porcentaje"],
                    accion["dias_atraso"],
                ]
            )
            filas += 1

    writer.writerow(["Overrides", datos["overrides"]["motivo"]])
    writer.writerow(["Operaciones duplicadas", datos["operaciones_duplicadas"]["motivo"]])

    nombre = f"control-interno-{fecha_desde}-{fecha_hasta}.csv"
    record_audit(
        db,
        action="GOV_INTERNAL_CONTROL_REPORT_EXPORTED",
        entity_type="GovernmentEntity",
        entity_id=ctx.company_id,
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={
            "filas": filas,
            "filtros": {
                "desde": fecha_desde.isoformat(),
                "hasta": fecha_hasta.isoformat(),
            },
        },
    )
    return nombre, salida.getvalue().encode("utf-8")
