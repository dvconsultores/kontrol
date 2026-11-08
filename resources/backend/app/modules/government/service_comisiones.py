from __future__ import annotations

import csv
from collections.abc import Sequence
from datetime import UTC, datetime
from io import StringIO
from typing import Any

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.government.models import (
    AREAS_COMISION,
    GovernmentAct,
    GovernmentOfficial,
    GovernmentPosition,
    GovernmentProcurementCommittee,
    GovernmentProcurementCommitteeConflict,
    GovernmentProcurementCommitteeHistory,
    GovernmentProcurementCommitteeMember,
)
from app.modules.government.service_auditoria import _instante, _usuarios_por_ids
from app.modules.government.service_identidad import _celda
from app.modules.government.service_ocupacion import (
    _funcionario_de_empresa,
    ocupaciones_de_funcionario,
)
from app.modules.government.service_sod import (
    evaluar_antes_de_actuar,
    funcionarios_de_actor,
    usuarios_equivalentes,
)
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio

ENTIDAD = "GovernmentProcurementCommittee"
REGLA_VERSION = "LCP-2014+RLCP-2009"
_ETIQUETAS_TIPO_ACTO = {
    "DECRETO": "Decreto",
    "RESOLUCION": "Resolución",
    "ORDEN": "Orden",
    "PROVIDENCIA": "Providencia",
    "INSTRUCCION": "Instrucción",
    "CIRCULAR": "Circular",
    "OTRA_DECISION": "Otra decisión",
}

FUENTE_REGLA = (
    "Decreto Ley de Contrataciones Públicas, G.O. 6.154 Ext. (2014), art. 14; "
    "Reglamento, G.O. 39.181 (2009), arts. 15, 18 y 20"
)
ETIQUETAS = {
    "tipos": {"PERMANENTE": "Permanente", "TEMPORAL": "Temporal"},
    "funciones": {"MIEMBRO": "Miembro", "SECRETARIO": "Secretario (voz sin voto)"},
    "areas": {
        "JURIDICA": "Jurídica",
        "TECNICA": "Técnica",
        "ECONOMICO_FINANCIERA": "Económico financiera",
    },
    "condiciones": {"PRINCIPAL": "Principal", "SUPLENTE": "Suplente"},
    "causas": {
        "MUERTE_INCAPACIDAD": "Muerte o incapacidad absoluta y permanente",
        "DESPIDO_DESTITUCION": "Despido o destitución",
        "RETIRO_RENUNCIA_REMOCION": "Retiro, renuncia, jubilación, remoción o disponibilidad",
        "FIN_DESIGNACION": "Fin de la designación",
    },
    "situaciones": {
        "BORRADOR": "En preparación",
        "FUTURA": "Aún no inicia",
        "EN_VIGOR": "En vigor",
        "VENCIDA": "Vencida sin cerrar",
        "CERRADA": "Cerrada",
        "DESCARTADA": "Descartada",
    },
}
CAUSALES = {
    "INTERES": (
        "Interés propio, del cónyuge o de pariente en el procedimiento",
        "RLCP art. 18.1",
    ),
    "AMISTAD_ENEMISTAD": (
        "Amistad íntima o enemistad manifiesta con un interesado",
        "RLCP art. 18.2",
    ),
    "INTERVENCION_PREVIA": (
        "Intervención previa como testigo, perito u opinión previa",
        "RLCP art. 18.3",
    ),
    "SERVICIO_SUBORDINACION": (
        "Relación de servicio o subordinación con un interesado",
        "RLCP art. 18.4",
    ),
}


def situacion_de(c, fecha: Any) -> str:
    if c.status == "BORRADOR":
        return "BORRADOR"
    if c.status == "DESCARTADA":
        return "DESCARTADA"
    if c.status == "CERRADA":
        return "CERRADA"
    if c.status == "VIGENTE":
        if fecha < c.desde:
            return "FUTURA"
        if c.hasta and fecha > c.hasta:
            return "VENCIDA"
        return "EN_VIGOR"
    return "BORRADOR"


def _para_escribir(db: Session, ctx: CompanyContext, id: str, version: int | None):
    if version is None:
        raise KontrolError(
            code="GOV_COMMITTEE_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión",
            status_code=428,
        )
    c = db.scalar(
        select(GovernmentProcurementCommittee)
        .where(
            GovernmentProcurementCommittee.id == id,
            GovernmentProcurementCommittee.company_id == ctx.company_id,
        )
        .with_for_update()
    )
    if not c:
        raise NotFoundError("GOV_COMMITTEE_NOT_FOUND", "La comisión no existe en este ente")
    if c.version != version:
        raise ConflictError(
            "GOV_COMMITTEE_STALE",
            "La comisión cambió desde que la abrió; recárguela",
            details={"version_actual": c.version},
        )
    return c


def _exigir_estado(c, estado: str) -> None:
    if c.status != estado:
        raise ConflictError(
            "GOV_COMMITTEE_INVALID_STATE",
            f"La comisión debe estar en estado {estado}",
        )


def _historia(db: Session, ctx: CompanyContext, c, tipo: str, descripcion: str) -> None:
    db.add(
        GovernmentProcurementCommitteeHistory(
            committee_id=c.id,
            company_id=ctx.company_id,
            tipo=tipo,
            detalle={"descripcion": descripcion},
            created_by=ctx.user_id,
            created_at=datetime.now(UTC),
        )
    )


def _auditar(
    db: Session,
    ctx: CompanyContext,
    accion: str,
    id: str,
    despues: dict[str, Any],
    motivo: str | None = None,
) -> None:
    permitidas = {
        "acto",
        "area",
        "asunto",
        "causa",
        "causal",
        "codigo",
        "condicion",
        "desde",
        "estado",
        "fecha",
        "filtros",
        "funcion",
        "funcionario",
        "hasta",
        "miembro",
        "motivo",
        "nombre",
        "referencia",
        "regla_version",
        "total",
        "version",
    }
    limpio: dict[str, Any] = {}
    for k, v in despues.items():
        if k not in permitidas:
            continue
        if hasattr(v, "isoformat"):
            limpio[k] = v.isoformat()
        else:
            limpio[k] = v
    record_audit(
        db,
        action=accion,
        entity_type=ENTIDAD,
        entity_id=id,
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=limpio,
        reason=motivo,
    )


def _acto(db: Session, ctx: CompanyContext, acto_id: str | None):
    if not acto_id:
        return None
    acto = db.scalar(
        select(GovernmentAct).where(
            GovernmentAct.id == acto_id,
            GovernmentAct.company_id == ctx.company_id,
        )
    )
    if not acto:
        raise NotFoundError("GOV_COMMITTEE_ACT_NOT_FOUND", "El acto no existe en este ente")
    return acto


def _acto_ref(db: Session, acto) -> dict[str, Any] | None:
    if not acto:
        return None
    emisor = None
    if acto.cargo_id:
        pos = db.scalar(select(GovernmentPosition).where(GovernmentPosition.id == acto.cargo_id))
        emisor = pos.name if pos else None
    return {
        "id": acto.id,
        "etiqueta": f"{_ETIQUETAS_TIPO_ACTO.get(acto.tipo, acto.tipo)} {acto.numero} · {acto.asunto}",
        "medio": acto.medio,
        "fecha_eficacia": acto.fecha_eficacia,
        "emisor": emisor,
    }


def _acto_valido(acto, fecha: Any) -> str | None:
    if acto.status != "EFICAZ" or not acto.fecha_eficacia or acto.fecha_eficacia > fecha:
        return "El acto debe estar eficaz al inicio de la vigencia"
    if acto.medio != "GACETA":
        return "El acto debe estar publicado en gaceta (RLCP art. 15)"
    return None


def _activos(
    miembros: Sequence[GovernmentProcurementCommitteeMember],
) -> list[GovernmentProcurementCommitteeMember]:
    return [m for m in miembros if m.fin_efectivo is None]


def _faltantes(db: Session, ctx: CompanyContext, c, miembros) -> list[str]:
    resultado: list[str] = []
    activos = _activos(miembros)
    if not c.act_id:
        resultado.append("Falta el acto que crea la comisión")
    else:
        acto = db.scalar(
            select(GovernmentAct).where(
                GovernmentAct.id == c.act_id,
                GovernmentAct.company_id == ctx.company_id,
            )
        )
        if acto:
            error = _acto_valido(acto, c.desde)
            if error:
                resultado.append(error)
    if c.tipo == "TEMPORAL" and not c.hasta:
        resultado.append("Una comisión temporal necesita fecha final")
    principales = [
        m
        for m in activos
        if m.funcion == "MIEMBRO" and m.condicion == "PRINCIPAL"
    ]
    if len(principales) % 2 == 0:
        resultado.append("El número de miembros principales debe ser impar (LCP art. 14)")
    areas_con_principal = {m.area for m in principales if m.area}
    for area in AREAS_COMISION:
        if area not in areas_con_principal:
            resultado.append(f"Falta un principal del área {ETIQUETAS['areas'][area]} (LCP art. 14)")
    for p in principales:
        if not any(
            m.funcion == "MIEMBRO"
            and m.condicion == "SUPLENTE"
            and m.suplente_de_id == p.id
            for m in activos
        ):
            oficial = db.scalar(
                select(GovernmentOfficial).where(
                    GovernmentOfficial.id == p.official_id,
                    GovernmentOfficial.company_id == ctx.company_id,
                )
            )
            nombre = oficial.nombre if oficial else p.official_id
            resultado.append(f"{nombre} no tiene suplente (LCP art. 14)")
    if not any(m.funcion == "SECRETARIO" and m.condicion == "PRINCIPAL" for m in activos):
        resultado.append("Falta el secretario (LCP art. 14)")
    if not any(m.funcion == "SECRETARIO" and m.condicion == "SUPLENTE" for m in activos):
        resultado.append("Falta el suplente del secretario (LCP art. 14)")
    for m in activos:
        oficial = db.scalar(
            select(GovernmentOfficial).where(
                GovernmentOfficial.id == m.official_id,
                GovernmentOfficial.company_id == ctx.company_id,
            )
        )
        if oficial and oficial.estado != "ACTIVO":
            resultado.append(f"{oficial.nombre} no está activo")
    return resultado


def _resumenes(
    db: Session,
    ctx: CompanyContext,
    comisiones: Sequence[GovernmentProcurementCommittee],
) -> dict[str, dict[str, Any]]:
    if not comisiones:
        return {}
    ids = [c.id for c in comisiones]
    conteos = {
        fila.committee_id: fila
        for fila in db.execute(
            select(
                GovernmentProcurementCommitteeMember.committee_id,
                func.count().label("total"),
                func.sum(
                    case(
                        (
                            (GovernmentProcurementCommitteeMember.funcion == "MIEMBRO")
                            & (GovernmentProcurementCommitteeMember.condicion == "PRINCIPAL"),
                            1,
                        ),
                        else_=0,
                    )
                ).label("principales"),
            )
            .where(
                GovernmentProcurementCommitteeMember.committee_id.in_(ids),
                GovernmentProcurementCommitteeMember.fin_efectivo.is_(None),
            )
            .group_by(GovernmentProcurementCommitteeMember.committee_id)
        ).all()
    }
    actos_ids = [c.act_id for c in comisiones if c.act_id]
    actos: dict[str, GovernmentAct] = {}
    if actos_ids:
        for acto in db.scalars(
            select(GovernmentAct).where(
                GovernmentAct.id.in_(actos_ids),
                GovernmentAct.company_id == ctx.company_id,
            )
        ).all():
            actos[str(acto.id)] = acto
    return {
        str(c.id): {
            "miembros_total": (
                conteos.get(c.id, (c.id, 0, 0))[1]
            ),
            "miembros_principales": int(
                conteos.get(c.id, (c.id, 0, 0))[2] or 0
            ),
            "acto_ref": _acto_ref(db, actos.get(str(c.act_id))) if c.act_id else None,
        }
        for c in comisiones
    }


def catalogo() -> dict:
    return {
        "tipos": [
            {"codigo": k, "etiqueta": v} for k, v in ETIQUETAS["tipos"].items()
        ],
        "funciones": [
            {"codigo": k, "etiqueta": v} for k, v in ETIQUETAS["funciones"].items()
        ],
        "areas": [
            {"codigo": k, "etiqueta": v} for k, v in ETIQUETAS["areas"].items()
        ],
        "condiciones": [
            {"codigo": k, "etiqueta": v} for k, v in ETIQUETAS["condiciones"].items()
        ],
        "causas_fin": [
            {"codigo": k, "etiqueta": v} for k, v in ETIQUETAS["causas"].items()
        ],
        "causales": [
            {"codigo": k, "etiqueta": v[0], "fuente": v[1]}
            for k, v in CAUSALES.items()
        ],
        "situaciones": [
            {"codigo": k, "etiqueta": v} for k, v in ETIQUETAS["situaciones"].items()
        ],
        "regla_version": REGLA_VERSION,
        "fuente_regla": FUENTE_REGLA,
    }


def opciones(db: Session, ctx: CompanyContext) -> dict:
    hoy = hoy_de_negocio()
    funcionarios = []
    for oficial in db.scalars(
        select(GovernmentOfficial)
        .where(
            GovernmentOfficial.company_id == ctx.company_id,
            GovernmentOfficial.estado == "ACTIVO",
        )
        .order_by(GovernmentOfficial.nombre)
    ).all():
        cargos: list[str] = []
        unidades: list[str] = []
        for ocupacion in ocupaciones_de_funcionario(db, ctx, str(oficial.id), hoy):
            if not ocupacion.get("ejerce"):
                continue
            cargo = ocupacion.get("cargo") or {}
            if cargo.get("nombre") and cargo["nombre"] not in cargos:
                cargos.append(cargo["nombre"])
            if cargo.get("unidad") and cargo["unidad"] not in unidades:
                unidades.append(cargo["unidad"])
        funcionarios.append(
            {"id": oficial.id, "nombre": oficial.nombre, "cargos": cargos, "unidades": unidades}
        )
    actos = []
    for acto in db.scalars(
        select(GovernmentAct)
        .where(
            GovernmentAct.company_id == ctx.company_id,
            GovernmentAct.status == "EFICAZ",
        )
        .order_by(GovernmentAct.fecha.desc())
    ).all():
        ref = _acto_ref(db, acto)
        if ref:
            actos.append(ref)
    return {"funcionarios": funcionarios, "actos": actos}


def listar(
    db: Session,
    ctx: CompanyContext,
    *,
    q: str | None = None,
    status: str | None = None,
    tipo: str | None = None,
    situacion: str | None = None,
    pagina: int = 1,
    por_pagina: int = 25,
) -> dict:
    hoy = hoy_de_negocio()
    condiciones = [GovernmentProcurementCommittee.company_id == ctx.company_id]
    if q:
        condiciones.append(
            or_(
                GovernmentProcurementCommittee.nombre.icontains(q, autoescape=True),
                GovernmentProcurementCommittee.codigo.icontains(q, autoescape=True),
            )
        )
    if status:
        condiciones.append(GovernmentProcurementCommittee.status == status)
    if tipo:
        condiciones.append(GovernmentProcurementCommittee.tipo == tipo)
    if situacion:
        if situacion in ("BORRADOR", "DESCARTADA", "CERRADA"):
            condiciones.append(GovernmentProcurementCommittee.status == situacion)
        elif situacion == "FUTURA":
            condiciones.extend(
                [
                    GovernmentProcurementCommittee.status == "VIGENTE",
                    GovernmentProcurementCommittee.desde > hoy,
                ]
            )
        elif situacion == "VENCIDA":
            condiciones.extend(
                [
                    GovernmentProcurementCommittee.status == "VIGENTE",
                    GovernmentProcurementCommittee.hasta < hoy,
                ]
            )
        elif situacion == "EN_VIGOR":
            condiciones.extend(
                [
                    GovernmentProcurementCommittee.status == "VIGENTE",
                    GovernmentProcurementCommittee.desde <= hoy,
                    or_(
                        GovernmentProcurementCommittee.hasta.is_(None),
                        GovernmentProcurementCommittee.hasta >= hoy,
                    ),
                ]
            )
    base = select(GovernmentProcurementCommittee).where(*condiciones)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    comisiones = db.scalars(
        base.order_by(
            GovernmentProcurementCommittee.desde.desc(),
            GovernmentProcurementCommittee.codigo.desc(),
        )
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
    ).all()
    resumenes = _resumenes(db, ctx, comisiones)
    items = []
    for c in comisiones:
        r = resumenes.get(str(c.id), {})
        items.append(
            {
                "id": str(c.id),
                "codigo": c.codigo,
                "nombre": c.nombre,
                "tipo": c.tipo,
                "status": c.status,
                "situacion": situacion_de(c, hoy),
                "desde": c.desde,
                "hasta": c.hasta,
                "acto": r.get("acto_ref"),
                "miembros_principales": r.get("miembros_principales", 0),
                "miembros_total": r.get("miembros_total", 0),
                "version": c.version,
            }
        )
    return {"items": items, "total": total, "pagina": pagina, "por_pagina": por_pagina}


def exportar_csv(
    db: Session,
    ctx: CompanyContext,
    *,
    q: str | None = None,
    status: str | None = None,
    tipo: str | None = None,
    situacion: str | None = None,
):
    datos = listar(db, ctx, q=q, status=status, tipo=tipo, situacion=situacion, pagina=1, por_pagina=100000)
    items = datos["items"]
    hoy = hoy_de_negocio()
    salida = StringIO()
    writer = csv.writer(salida, lineterminator="\n")
    writer.writerow(["Código", "Nombre", "Tipo", "Estado", "Situación", "Desde", "Hasta", "Acto", "Miembros"])
    for item in items:
        writer.writerow(
            [
                _celda(item["codigo"]),
                _celda(item["nombre"]),
                _celda(ETIQUETAS["tipos"].get(item["tipo"], item["tipo"])),
                _celda(ETIQUETAS["situaciones"].get(item["status"], item["status"])),
                _celda(ETIQUETAS["situaciones"].get(item["situacion"], item["situacion"])),
                _celda(item["desde"].isoformat()),
                _celda(item["hasta"].isoformat() if item["hasta"] else None),
                _celda(item["acto"]["etiqueta"] if item["acto"] else None),
                _celda(str(item["miembros_total"])),
            ]
        )
    filtros = {
        "q": q,
        "status": status,
        "tipo": tipo,
        "situacion": situacion,
    }
    _auditar(
        db,
        ctx,
        "GOV_COMMITTEES_EXPORTED",
        "",
        {"total": len(items), "filtros": filtros, "fecha": hoy},
    )
    return f"comisiones-{hoy.isoformat()}.csv", salida.getvalue().encode("utf-8")


def detalle(db: Session, ctx: CompanyContext, id: str, fecha: Any) -> dict:
    c = db.scalar(
        select(GovernmentProcurementCommittee).where(
            GovernmentProcurementCommittee.id == id,
            GovernmentProcurementCommittee.company_id == ctx.company_id,
        )
    )
    if not c:
        raise NotFoundError("GOV_COMMITTEE_NOT_FOUND", "La comisión no existe en este ente")
    hoy = hoy_de_negocio()
    fecha = fecha or hoy
    es_historica = fecha < hoy
    miembros = db.scalars(
        select(GovernmentProcurementCommitteeMember)
        .where(
            GovernmentProcurementCommitteeMember.committee_id == c.id,
            GovernmentProcurementCommitteeMember.company_id == ctx.company_id,
        )
        .order_by(
            GovernmentProcurementCommitteeMember.condicion,
            GovernmentProcurementCommitteeMember.funcion,
            GovernmentProcurementCommitteeMember.desde,
        )
    ).all()
    composicion: list[GovernmentProcurementCommitteeMember] = []
    if c.status == "BORRADOR":
        composicion = _activos(miembros)
    else:
        composicion = [
            m
            for m in miembros
            if m.desde <= fecha and (m.fin_efectivo is None or m.fin_efectivo >= fecha)
        ]

    def miembro_out(m: GovernmentProcurementCommitteeMember) -> dict:
        oficial = db.scalar(
            select(GovernmentOfficial).where(
                GovernmentOfficial.id == m.official_id,
                GovernmentOfficial.company_id == ctx.company_id,
            )
        )
        cargos: list[str] = []
        unidades: list[str] = []
        for ocupacion in ocupaciones_de_funcionario(db, ctx, m.official_id, fecha):
            if not ocupacion.get("ejerce"):
                continue
            cargo = ocupacion.get("cargo") or {}
            if cargo.get("nombre") and cargo["nombre"] not in cargos:
                cargos.append(cargo["nombre"])
            if cargo.get("unidad") and cargo["unidad"] not in unidades:
                unidades.append(cargo["unidad"])
        suplente_de = None
        if m.suplente_de_id:
            principal = next((x for x in miembros if x.id == m.suplente_de_id), None)
            if principal:
                oficial_principal = db.scalar(
                    select(GovernmentOfficial).where(
                        GovernmentOfficial.id == principal.official_id,
                        GovernmentOfficial.company_id == ctx.company_id,
                    )
                )
                suplente_de = oficial_principal.nombre if oficial_principal else None
        acto = None
        if m.act_id:
            acto_obj = db.scalar(
                select(GovernmentAct).where(
                    GovernmentAct.id == m.act_id,
                    GovernmentAct.company_id == ctx.company_id,
                )
            )
            acto = _acto_ref(db, acto_obj)
        return {
            "id": m.id,
            "funcionario": {
                "id": m.official_id,
                "nombre": oficial.nombre if oficial else m.official_id,
                "cargos": cargos,
                "unidades": unidades,
            },
            "funcion": m.funcion,
            "area": m.area,
            "condicion": m.condicion,
            "suplente_de": suplente_de,
            "suplente_de_id": m.suplente_de_id,
            "desde": m.desde,
            "fin_efectivo": m.fin_efectivo,
            "causa_fin": m.causa_fin,
            "motivo_fin": m.motivo_fin,
            "acto": acto,
            "certificacion_snc": m.certificacion_snc,
        }

    faltantes = []
    if c.status in ("BORRADOR", "VIGENTE"):
        faltantes = _faltantes(db, ctx, c, miembros)
    inhibiciones = db.scalars(
        select(GovernmentProcurementCommitteeConflict)
        .where(
            GovernmentProcurementCommitteeConflict.committee_id == c.id,
            GovernmentProcurementCommitteeConflict.company_id == ctx.company_id,
        )
        .order_by(GovernmentProcurementCommitteeConflict.fecha.desc())
    ).all()
    inhibiciones_out = []
    for inh in inhibiciones:
        miembro = next((m for m in miembros if m.id == inh.member_id), None)
        nombre = ""
        if miembro:
            oficial = db.scalar(
                select(GovernmentOfficial).where(
                    GovernmentOfficial.id == miembro.official_id,
                    GovernmentOfficial.company_id == ctx.company_id,
                )
            )
            nombre = oficial.nombre if oficial else miembro.official_id
        suplente = None
        if miembro:
            alterno = next(
                (
                    m
                    for m in _activos(miembros)
                    if m.suplente_de_id == miembro.id
                ),
                None,
            )
            if alterno:
                oficial_alterno = db.scalar(
                    select(GovernmentOfficial).where(
                        GovernmentOfficial.id == alterno.official_id,
                        GovernmentOfficial.company_id == ctx.company_id,
                    )
                )
                suplente = oficial_alterno.nombre if oficial_alterno else None
        inhibiciones_out.append(
            {
                "id": inh.id,
                "miembro_id": inh.member_id,
                "miembro": nombre,
                "suplente": suplente,
                "asunto": inh.asunto,
                "causal": inh.causal,
                "causal_etiqueta": CAUSALES[inh.causal][0],
                "descripcion": inh.descripcion,
                "fecha": inh.fecha,
                "soporte": inh.soporte,
                "estado": inh.estado,
                "motivo_resolucion": inh.motivo_resolucion,
                "version": inh.version,
            }
        )
    historia_rows = db.scalars(
        select(GovernmentProcurementCommitteeHistory)
        .where(
            GovernmentProcurementCommitteeHistory.committee_id == c.id,
            GovernmentProcurementCommitteeHistory.company_id == ctx.company_id,
        )
        .order_by(
            GovernmentProcurementCommitteeHistory.created_at.desc(),
            GovernmentProcurementCommitteeHistory.id.desc(),
        )
    ).all()
    creadores = list({h.created_by for h in historia_rows if h.created_by})
    usuarios = _usuarios_por_ids(db, creadores, ctx.tenant_id) if creadores else {}
    historia = []
    for h in historia_rows:
        det = h.detalle or {}
        historia.append(
            {
                "tipo": h.tipo,
                "fecha": _instante(h.created_at),
                "usuario": usuarios.get(h.created_by) if h.created_by else None,
                "descripcion": det.get("descripcion", ""),
            }
        )
    resumenes = _resumenes(db, ctx, [c])
    r = resumenes.get(str(c.id), {})
    return {
        **{
            "id": c.id,
            "codigo": c.codigo,
            "nombre": c.nombre,
            "tipo": c.tipo,
            "status": c.status,
            "situacion": situacion_de(c, hoy),
            "desde": c.desde,
            "hasta": c.hasta,
            "acto": r.get("acto_ref"),
            "miembros_principales": r.get("miembros_principales", 0),
            "miembros_total": r.get("miembros_total", 0),
            "version": c.version,
        },
        "objeto": c.objeto,
        "regla_version": c.regla_version,
        "snc_notificada_en": c.snc_notificada_en,
        "snc_referencia": c.snc_referencia,
        "snc_pendiente": c.status == "VIGENTE" and not c.snc_notificada_en,
        "motivo_cierre": c.motivo_cierre,
        "fin_efectivo": c.fin_efectivo,
        "fecha": fecha,
        "es_historica": es_historica,
        "composicion": [miembro_out(m) for m in composicion],
        "miembros": [miembro_out(m) for m in miembros],
        "faltantes": faltantes,
        "inhibiciones": inhibiciones_out,
        "historia": historia,
    }


def crear(db: Session, ctx: CompanyContext, datos) -> dict:
    if datos.hasta and datos.hasta < datos.desde:
        raise KontrolError(
            code="GOV_COMMITTEE_INVALID_DATES",
            message="La fecha final no puede ser anterior a la inicial",
            field_errors={"hasta": ["La fecha final no puede ser anterior a la inicial"]},
            status_code=422,
        )
    if datos.acto_id:
        _acto(db, ctx, datos.acto_id)
    total = db.scalar(
        select(func.count()).select_from(GovernmentProcurementCommittee).where(
            GovernmentProcurementCommittee.company_id == ctx.company_id
        )
    ) or 0
    c = GovernmentProcurementCommittee(
        company_id=ctx.company_id,
        codigo=f"COM-{total + 1:05d}",
        nombre=datos.nombre,
        tipo=datos.tipo,
        objeto=datos.objeto,
        desde=datos.desde,
        hasta=datos.hasta,
        act_id=datos.acto_id,
        status="BORRADOR",
        version=1,
        created_by=ctx.user_id,
        created_at=datetime.now(UTC),
    )
    db.add(c)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_COMMITTEE_CONFLICT",
            "Otra comisión se registró al mismo tiempo; vuelva a intentarlo",
        ) from None
    _historia(db, ctx, c, "CREADA", "Comisión registrada")
    _auditar(
        db,
        ctx,
        "GOV_COMMITTEE_CREATED",
        str(c.id),
        {"codigo": c.codigo, "nombre": c.nombre, "estado": c.status},
    )
    return detalle(db, ctx, str(c.id), None)


def editar(db: Session, ctx: CompanyContext, id: str, version: int | None, datos) -> dict:
    c = _para_escribir(db, ctx, id, version)
    _exigir_estado(c, "BORRADOR")
    if datos.hasta and datos.hasta < datos.desde:
        raise KontrolError(
            code="GOV_COMMITTEE_INVALID_DATES",
            message="La fecha final no puede ser anterior a la inicial",
            field_errors={"hasta": ["La fecha final no puede ser anterior a la inicial"]},
            status_code=422,
        )
    if datos.acto_id:
        _acto(db, ctx, datos.acto_id)
    c.nombre = datos.nombre
    c.tipo = datos.tipo
    c.objeto = datos.objeto
    c.desde = datos.desde
    c.hasta = datos.hasta
    c.act_id = datos.acto_id
    c.version += 1
    db.execute(
        update(GovernmentProcurementCommitteeMember)
        .where(
            GovernmentProcurementCommitteeMember.committee_id == c.id,
            GovernmentProcurementCommitteeMember.fin_efectivo.is_(None),
        )
        .values(desde=c.desde)
    )
    _historia(db, ctx, c, "EDITADA", "Datos de la comisión editados")
    _auditar(
        db,
        ctx,
        "GOV_COMMITTEE_UPDATED",
        c.id,
        {"codigo": c.codigo, "nombre": c.nombre, "estado": c.status, "version": c.version},
    )
    return detalle(db, ctx, str(c.id), None)


def descartar(db: Session, ctx: CompanyContext, id: str, version: int | None, datos) -> dict:
    c = _para_escribir(db, ctx, id, version)
    _exigir_estado(c, "BORRADOR")
    c.status = "DESCARTADA"
    c.version += 1
    _historia(db, ctx, c, "DESCARTADA", f"Descartada: {datos.motivo}")
    _auditar(
        db,
        ctx,
        "GOV_COMMITTEE_DISCARDED",
        c.id,
        {"codigo": c.codigo, "estado": c.status, "motivo": datos.motivo},
        motivo=datos.motivo,
    )
    return detalle(db, ctx, str(c.id), None)


def activar(db: Session, ctx: CompanyContext, id: str, version: int | None) -> dict:
    c = _para_escribir(db, ctx, id, version)
    _exigir_estado(c, "BORRADOR")
    if c.created_by in usuarios_equivalentes(db, ctx, ctx.user_id):
        raise KontrolError(
            code="GOV_COMMITTEE_SELF_ACTIVATION",
            message="Quien registró la comisión no puede activarla",
            status_code=403,
        )
    miembros = db.scalars(
        select(GovernmentProcurementCommitteeMember).where(
            GovernmentProcurementCommitteeMember.committee_id == c.id,
            GovernmentProcurementCommitteeMember.company_id == ctx.company_id,
        )
    ).all()
    faltantes = _faltantes(db, ctx, c, miembros)
    if faltantes:
        raise KontrolError(
            code="GOV_COMMITTEE_INCOMPLETE",
            message="La comisión no cumple lo que exige la ley para activarse",
            details={"faltantes": faltantes},
            status_code=422,
        )
    evaluar_antes_de_actuar(db, ctx, "PROC02_ACTIVAR", ENTIDAD, c.id)
    c.status = "VIGENTE"
    c.regla_version = REGLA_VERSION
    c.activated_at = datetime.now(UTC)
    c.activated_by = ctx.user_id
    c.version += 1
    for m in _activos(miembros):
        m.act_id = c.act_id
    _historia(db, ctx, c, "ACTIVADA", f"Activada con la regla {REGLA_VERSION}")
    _auditar(
        db,
        ctx,
        "GOV_COMMITTEE_ACTIVATED",
        c.id,
        {"codigo": c.codigo, "estado": c.status, "regla_version": c.regla_version},
    )
    return detalle(db, ctx, str(c.id), None)


def cerrar(db: Session, ctx: CompanyContext, id: str, version: int | None, datos) -> dict:
    c = _para_escribir(db, ctx, id, version)
    _exigir_estado(c, "VIGENTE")
    if datos.fecha < c.desde:
        raise KontrolError(
            code="GOV_COMMITTEE_INVALID_DATES",
            message="La fecha de cierre no puede ser anterior al inicio",
            field_errors={"fecha": ["La fecha de cierre no puede ser anterior al inicio"]},
            status_code=422,
        )
    evaluar_antes_de_actuar(db, ctx, "PROC02_CERRAR", ENTIDAD, c.id)
    ahora = datetime.now(UTC)
    miembros_activos = db.scalars(
        select(GovernmentProcurementCommitteeMember)
        .where(
            GovernmentProcurementCommitteeMember.committee_id == c.id,
            GovernmentProcurementCommitteeMember.company_id == ctx.company_id,
            GovernmentProcurementCommitteeMember.fin_efectivo.is_(None),
        )
        .with_for_update()
    ).all()
    for m in miembros_activos:
        m.fin_efectivo = datos.fecha
        m.causa_fin = "FIN_DESIGNACION"
        m.motivo_fin = datos.motivo
        m.ended_at = ahora
        m.ended_by = ctx.user_id
    c.status = "CERRADA"
    c.fin_efectivo = datos.fecha
    c.motivo_cierre = datos.motivo
    c.closed_at = ahora
    c.closed_by = ctx.user_id
    c.version += 1
    _historia(db, ctx, c, "CERRADA", datos.motivo)
    _auditar(
        db,
        ctx,
        "GOV_COMMITTEE_CLOSED",
        c.id,
        {"codigo": c.codigo, "estado": c.status, "fecha": datos.fecha, "motivo": datos.motivo},
        motivo=datos.motivo,
    )
    return detalle(db, ctx, str(c.id), None)


def notificar_snc(db: Session, ctx: CompanyContext, id: str, version: int | None, datos) -> dict:
    c = _para_escribir(db, ctx, id, version)
    _exigir_estado(c, "VIGENTE")
    c.snc_notificada_en = datos.fecha
    c.snc_referencia = datos.referencia
    c.version += 1
    _historia(db, ctx, c, "SNC_NOTIFICADA", datos.referencia)
    _auditar(
        db,
        ctx,
        "GOV_COMMITTEE_SNC_NOTIFIED",
        c.id,
        {"fecha": datos.fecha, "referencia": datos.referencia},
    )
    return detalle(db, ctx, str(c.id), None)


def anadir_miembro(db: Session, ctx: CompanyContext, id: str, version: int | None, datos) -> dict:
    c = _para_escribir(db, ctx, id, version)
    if c.status not in ("BORRADOR", "VIGENTE"):
        raise ConflictError(
            "GOV_COMMITTEE_INVALID_STATE",
            "La comisión debe estar en estado BORRADOR o VIGENTE",
        )
    funcionario = _funcionario_de_empresa(db, ctx, datos.funcionario_id)
    if funcionario.estado != "ACTIVO":
        raise KontrolError(
            code="GOV_COMMITTEE_OFFICIAL_INACTIVE",
            message="El funcionario no está activo",
            status_code=422,
        )
    miembros = db.scalars(
        select(GovernmentProcurementCommitteeMember)
        .where(
            GovernmentProcurementCommitteeMember.committee_id == c.id,
            GovernmentProcurementCommitteeMember.company_id == ctx.company_id,
            GovernmentProcurementCommitteeMember.fin_efectivo.is_(None),
        )
    ).all()
    area = datos.area
    suplente_de_id = datos.suplente_de_id
    if datos.funcion == "MIEMBRO":
        if datos.condicion == "PRINCIPAL":
            if not area:
                raise KontrolError(
                    code="GOV_COMMITTEE_MEMBER_INVALID",
                    message="El miembro principal necesita área",
                    field_errors={"area": ["El miembro principal necesita área"]},
                    status_code=422,
                )
        elif datos.condicion == "SUPLENTE":
            if not suplente_de_id:
                raise KontrolError(
                    code="GOV_COMMITTEE_MEMBER_INVALID",
                    message="El suplente necesita un principal",
                    field_errors={"suplente_de_id": ["El suplente necesita un principal"]},
                    status_code=422,
                )
            principal = next(
                (
                    m
                    for m in miembros
                    if m.id == suplente_de_id
                    and m.funcion == "MIEMBRO"
                    and m.condicion == "PRINCIPAL"
                ),
                None,
            )
            if not principal:
                raise KontrolError(
                    code="GOV_COMMITTEE_MEMBER_INVALID",
                    message="El suplente_de_id debe ser un principal MIEMBRO activo de esta comisión",
                    field_errors={
                        "suplente_de_id": [
                            "El suplente_de_id debe ser un principal MIEMBRO activo de esta comisión"
                        ]
                    },
                    status_code=422,
                )
            area = principal.area
    else:  # SECRETARIO
        if area or suplente_de_id:
            raise KontrolError(
                code="GOV_COMMITTEE_MEMBER_INVALID",
                message="El secretario no lleva área ni suplente_de_id",
                field_errors={
                    "area": ["El secretario no lleva área"],
                    "suplente_de_id": ["El secretario no lleva suplente_de_id"],
                },
                status_code=422,
            )
    desde = datos.desde
    act_id = datos.acto_id
    if c.status == "VIGENTE":
        if not act_id:
            raise KontrolError(
                code="GOV_COMMITTEE_MEMBER_INVALID",
                message="En una comisión vigente el acto es obligatorio",
                field_errors={"acto_id": ["En una comisión vigente el acto es obligatorio"]},
                status_code=422,
            )
        if not desde:
            raise KontrolError(
                code="GOV_COMMITTEE_MEMBER_INVALID",
                message="En una comisión vigente la fecha es obligatoria",
                field_errors={"desde": ["En una comisión vigente la fecha es obligatoria"]},
                status_code=422,
            )
        if desde < c.desde:
            raise KontrolError(
                code="GOV_COMMITTEE_MEMBER_INVALID",
                message="La fecha debe ser posterior al inicio de la comisión",
                field_errors={"desde": ["La fecha debe ser posterior al inicio de la comisión"]},
                status_code=422,
            )
        acto = _acto(db, ctx, act_id)
        error = _acto_valido(acto, desde) if acto else "El acto no existe en este ente"
        if error:
            raise KontrolError(
                code="GOV_COMMITTEE_MEMBER_INVALID",
                message=error,
                field_errors={"acto_id": [error]},
                status_code=422,
            )
    else:
        desde = c.desde
        act_id = None
    miembro = GovernmentProcurementCommitteeMember(
        company_id=ctx.company_id,
        committee_id=c.id,
        official_id=datos.funcionario_id,
        funcion=datos.funcion,
        area=area,
        condicion=datos.condicion,
        suplente_de_id=suplente_de_id,
        desde=desde,
        act_id=act_id,
        certificacion_snc=datos.certificacion_snc,
        created_by=ctx.user_id,
    )
    db.add(miembro)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_COMMITTEE_MEMBER_DUPLICATE",
            "El funcionario ya integra la comisión, o ese puesto ya está ocupado",
        ) from None
    c.version += 1
    _historia(
        db,
        ctx,
        c,
        "MIEMBRO_ANADIDO",
        f"{funcionario.nombre}: {ETIQUETAS['funciones'][datos.funcion]} {ETIQUETAS['condiciones'][datos.condicion]}",
    )
    _auditar(
        db,
        ctx,
        "GOV_COMMITTEE_MEMBER_ADDED",
        c.id,
        {
            "funcionario": funcionario.nombre,
            "funcion": datos.funcion,
            "condicion": datos.condicion,
            "area": area,
        },
    )
    return detalle(db, ctx, str(c.id), None)


def retirar_miembro(
    db: Session, ctx: CompanyContext, id: str, version: int | None, miembro_id: str
) -> dict:
    c = _para_escribir(db, ctx, id, version)
    _exigir_estado(c, "BORRADOR")
    miembro = db.scalar(
        select(GovernmentProcurementCommitteeMember).where(
            GovernmentProcurementCommitteeMember.id == miembro_id,
            GovernmentProcurementCommitteeMember.committee_id == c.id,
            GovernmentProcurementCommitteeMember.company_id == ctx.company_id,
        )
    )
    if not miembro:
        raise NotFoundError(
            "GOV_COMMITTEE_MEMBER_NOT_FOUND", "El miembro no existe en esta comisión"
        )
    if db.scalar(
        select(GovernmentProcurementCommitteeMember.id).where(
            GovernmentProcurementCommitteeMember.suplente_de_id == miembro.id,
            GovernmentProcurementCommitteeMember.fin_efectivo.is_(None),
        )
    ):
        raise ConflictError(
            "GOV_COMMITTEE_MEMBER_HAS_ALTERNATE",
            "Retire primero a su suplente",
        )
    oficial = db.scalar(
        select(GovernmentOfficial).where(
            GovernmentOfficial.id == miembro.official_id,
            GovernmentOfficial.company_id == ctx.company_id,
        )
    )
    nombre = oficial.nombre if oficial else miembro.official_id
    db.delete(miembro)
    c.version += 1
    _historia(db, ctx, c, "MIEMBRO_RETIRADO", nombre)
    _auditar(
        db,
        ctx,
        "GOV_COMMITTEE_MEMBER_REMOVED",
        c.id,
        {"funcionario": nombre},
    )
    return detalle(db, ctx, str(c.id), None)


def terminar_miembro(
    db: Session, ctx: CompanyContext, id: str, version: int | None, miembro_id: str, datos
) -> dict:
    c = _para_escribir(db, ctx, id, version)
    _exigir_estado(c, "VIGENTE")
    miembro = db.scalar(
        select(GovernmentProcurementCommitteeMember)
        .where(
            GovernmentProcurementCommitteeMember.id == miembro_id,
            GovernmentProcurementCommitteeMember.committee_id == c.id,
            GovernmentProcurementCommitteeMember.company_id == ctx.company_id,
            GovernmentProcurementCommitteeMember.fin_efectivo.is_(None),
        )
        .with_for_update()
    )
    if not miembro:
        raise NotFoundError(
            "GOV_COMMITTEE_MEMBER_NOT_FOUND", "El miembro no existe en esta comisión"
        )
    if datos.fecha < miembro.desde:
        raise KontrolError(
            code="GOV_COMMITTEE_INVALID_DATES",
            message="La fecha no puede ser anterior al inicio del miembro",
            field_errors={"fecha": ["La fecha no puede ser anterior al inicio del miembro"]},
            status_code=422,
        )
    oficial = db.scalar(
        select(GovernmentOfficial).where(
            GovernmentOfficial.id == miembro.official_id,
            GovernmentOfficial.company_id == ctx.company_id,
        )
    )
    nombre = oficial.nombre if oficial else miembro.official_id
    miembro.fin_efectivo = datos.fecha
    miembro.causa_fin = datos.causa
    miembro.motivo_fin = datos.motivo
    miembro.ended_at = datetime.now(UTC)
    miembro.ended_by = ctx.user_id
    c.version += 1
    _historia(
        db,
        ctx,
        c,
        "MIEMBRO_TERMINADO",
        f"{nombre}: {ETIQUETAS['causas'][datos.causa]}",
    )
    _auditar(
        db,
        ctx,
        "GOV_COMMITTEE_MEMBER_ENDED",
        c.id,
        {"funcionario": nombre, "causa": datos.causa, "fecha": datos.fecha},
        motivo=datos.motivo,
    )
    return detalle(db, ctx, str(c.id), None)


def declarar_inhibicion(db: Session, ctx: CompanyContext, id: str, datos) -> dict:
    c = db.scalar(
        select(GovernmentProcurementCommittee).where(
            GovernmentProcurementCommittee.id == id,
            GovernmentProcurementCommittee.company_id == ctx.company_id,
        )
    )
    if not c:
        raise NotFoundError("GOV_COMMITTEE_NOT_FOUND", "La comisión no existe en este ente")
    _exigir_estado(c, "VIGENTE")
    miembro = db.scalar(
        select(GovernmentProcurementCommitteeMember).where(
            GovernmentProcurementCommitteeMember.id == datos.miembro_id,
            GovernmentProcurementCommitteeMember.committee_id == c.id,
            GovernmentProcurementCommitteeMember.company_id == ctx.company_id,
            GovernmentProcurementCommitteeMember.fin_efectivo.is_(None),
        )
    )
    if not miembro:
        raise NotFoundError(
            "GOV_COMMITTEE_MEMBER_NOT_FOUND", "El miembro no existe en esta comisión"
        )
    oficial = db.scalar(
        select(GovernmentOfficial).where(
            GovernmentOfficial.id == miembro.official_id,
            GovernmentOfficial.company_id == ctx.company_id,
        )
    )
    nombre = oficial.nombre if oficial else miembro.official_id
    inhibicion = GovernmentProcurementCommitteeConflict(
        company_id=ctx.company_id,
        committee_id=c.id,
        member_id=miembro.id,
        asunto=datos.asunto,
        causal=datos.causal,
        descripcion=datos.descripcion,
        fecha=datos.fecha,
        soporte=datos.soporte,
        estado="DECLARADA",
        version=1,
        created_by=ctx.user_id,
    )
    db.add(inhibicion)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_COMMITTEE_CONFLICT",
            "No se pudo registrar la inhibición",
        ) from None
    _historia(db, ctx, c, "INHIBICION_DECLARADA", f"{nombre}: {datos.asunto}")
    _auditar(
        db,
        ctx,
        "GOV_COMMITTEE_CONFLICT_DECLARED",
        str(c.id),
        {"miembro": nombre, "asunto": datos.asunto, "causal": datos.causal, "fecha": datos.fecha},
    )
    return detalle(db, ctx, str(c.id), None)


def resolver_inhibicion(
    db: Session,
    ctx: CompanyContext,
    id: str,
    inhibicion_id: str,
    version: int | None,
    datos,
) -> dict:
    if version is None:
        raise KontrolError(
            code="GOV_COMMITTEE_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión",
            status_code=428,
        )
    c = db.scalar(
        select(GovernmentProcurementCommittee).where(
            GovernmentProcurementCommittee.id == id,
            GovernmentProcurementCommittee.company_id == ctx.company_id,
        )
    )
    if not c:
        raise NotFoundError("GOV_COMMITTEE_NOT_FOUND", "La comisión no existe en este ente")
    inhibicion = db.scalar(
        select(GovernmentProcurementCommitteeConflict)
        .where(
            GovernmentProcurementCommitteeConflict.id == inhibicion_id,
            GovernmentProcurementCommitteeConflict.committee_id == c.id,
            GovernmentProcurementCommitteeConflict.company_id == ctx.company_id,
        )
        .with_for_update()
    )
    if not inhibicion:
        raise NotFoundError(
            "GOV_COMMITTEE_CONFLICT_NOT_FOUND", "La inhibición no existe"
        )
    if inhibicion.version != version:
        raise ConflictError(
            "GOV_COMMITTEE_STALE",
            "La comisión cambió desde que la abrió; recárguela",
            details={"version_actual": inhibicion.version},
        )
    if inhibicion.estado != "DECLARADA":
        raise ConflictError(
            "GOV_COMMITTEE_INVALID_STATE", "La inhibición ya está resuelta"
        )
    if inhibicion.created_by in usuarios_equivalentes(db, ctx, ctx.user_id):
        raise KontrolError(
            code="GOV_COMMITTEE_SELF_RESOLUTION",
            message="Quien declara o el propio miembro no puede resolver la inhibición",
            status_code=403,
        )
    miembro = db.scalar(
        select(GovernmentProcurementCommitteeMember).where(
            GovernmentProcurementCommitteeMember.id == inhibicion.member_id,
            GovernmentProcurementCommitteeMember.company_id == ctx.company_id,
        )
    )
    if miembro is None:
        raise NotFoundError(
            "GOV_COMMITTEE_MEMBER_NOT_FOUND",
            "El miembro no existe en esta comisión",
        )
    if miembro and miembro.official_id in funcionarios_de_actor(db, ctx, ctx.user_id):
        raise KontrolError(
            code="GOV_COMMITTEE_SELF_RESOLUTION",
            message="Quien declara o el propio miembro no puede resolver la inhibición",
            status_code=403,
        )
    inhibicion.estado = datos.decision
    inhibicion.motivo_resolucion = datos.motivo
    inhibicion.resuelta_por = ctx.user_id
    inhibicion.resuelta_en = datetime.now(UTC)
    inhibicion.version += 1
    oficial = db.scalar(
        select(GovernmentOfficial).where(
            GovernmentOfficial.id == miembro.official_id,
            GovernmentOfficial.company_id == ctx.company_id,
        )
    )
    nombre = oficial.nombre if oficial else miembro.official_id
    _historia(
        db,
        ctx,
        c,
        "INHIBICION_RESUELTA",
        f"{nombre}: {datos.motivo}",
    )
    _auditar(
        db,
        ctx,
        "GOV_COMMITTEE_CONFLICT_RESOLVED",
        str(c.id),
        {"miembro": nombre, "estado": datos.decision, "motivo": datos.motivo},
    )
    return detalle(db, ctx, str(c.id), None)
