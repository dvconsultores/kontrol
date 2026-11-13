"""Servicio para el Reporte de contrataciones de Gobierno (REP03-R1)."""

from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import KontrolError
from app.modules.government.models import (
    GovernmentProcurementDecision,
    GovernmentProcurementFile,
    GovernmentProcurementFileMilestone,
    GovernmentProcurementOffer,
)
from app.modules.government.service_expedientes import (
    _ETIQUETAS_MODALIDAD,
    _ETIQUETAS_TIPO,
)
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio, instante_actual

_ETIQUETAS_ESTADO = {
    "ABIERTO": "Abierto",
    "CERRADO": "Cerrado",
    "DESCARTADO": "Descartado",
}
_ETIQUETAS_RESULTADO = {
    "ADJUDICADA": "Adjudicada",
    "DESIERTA": "Desierta",
    "TERMINADA": "Terminada",
    "NULIDAD": "Nulidad",
    "SIN_DECISION": "Sin decisión",
}
_MONTO_NO_DISPONIBLE = (
    "No disponible: las ofertas y las decisiones no registran monto (OBS-PROC08-MONTO-01)."
)


def _inicio_periodo(hoy: date) -> date:
    return date(hoy.year, 1, 1)


def _fecha_negocio(dt: Any) -> date | None:
    if dt is None:
        return None
    return hoy_de_negocio(dt)


def _dias(a: date | None, b: date | None) -> int | None:
    if a is None or b is None:
        return None
    return (a - b).days


def _promedio(valores: list[int]) -> float | None:
    if not valores:
        return None
    return round(sum(valores) / len(valores), 1)


def _decision_vigente(file_id: str, decisiones: list[GovernmentProcurementDecision]) -> GovernmentProcurementDecision | None:
    vigentes = [d for d in decisiones if d.file_id == file_id and d.estado == "VIGENTE"]
    if not vigentes:
        return None
    return max(vigentes, key=lambda d: d.decidida_en)


def _reporte_consolidado(
    db: Session,
    ctx: CompanyContext,
    *,
    desde: date,
    hasta: date,
) -> dict[str, Any]:
    filas = db.scalars(
        select(GovernmentProcurementFile).where(
            GovernmentProcurementFile.company_id == ctx.company_id,
            GovernmentProcurementFile.fecha_inicio >= desde,
            GovernmentProcurementFile.fecha_inicio <= hasta,
        )
    ).all()

    expedientes_ids = [e.id for e in filas]

    decisiones = db.scalars(
        select(GovernmentProcurementDecision).where(
            GovernmentProcurementDecision.company_id == ctx.company_id,
            GovernmentProcurementDecision.file_id.in_(expedientes_ids),
        )
    ).all() if expedientes_ids else []

    ofertas = db.scalars(
        select(GovernmentProcurementOffer).where(
            GovernmentProcurementOffer.company_id == ctx.company_id,
            GovernmentProcurementOffer.file_id.in_(expedientes_ids),
        )
    ).all() if expedientes_ids else []

    hitos = db.scalars(
        select(GovernmentProcurementFileMilestone).where(
            GovernmentProcurementFileMilestone.company_id == ctx.company_id,
            GovernmentProcurementFileMilestone.file_id.in_(expedientes_ids),
        )
    ).all() if expedientes_ids else []

    totales = {
        "expedientes": len(filas),
        "abiertos": sum(1 for e in filas if e.status == "ABIERTO"),
        "cerrados": sum(1 for e in filas if e.status == "CERRADO"),
        "descartados": sum(1 for e in filas if e.status == "DESCARTADO"),
    }

    contador_modalidad: Counter[str | None] = Counter(e.modalidad_declarada for e in filas)
    por_modalidad = [
        {"codigo": codigo, "etiqueta": _ETIQUETAS_MODALIDAD.get(codigo, "Sin modalidad declarada") if codigo else "Sin modalidad declarada", "total": contador_modalidad.get(codigo, 0)}
        for codigo in [*_ETIQUETAS_MODALIDAD.keys(), None]
    ]

    contador_estado = Counter(e.status for e in filas)
    por_estado = [
        {"codigo": codigo, "etiqueta": etiqueta, "total": contador_estado.get(codigo, 0)}
        for codigo, etiqueta in _ETIQUETAS_ESTADO.items()
    ]

    contador_tipo = Counter(e.tipo_contratacion for e in filas)
    por_tipo = [
        {"codigo": codigo, "etiqueta": etiqueta, "total": contador_tipo.get(codigo, 0)}
        for codigo, etiqueta in _ETIQUETAS_TIPO.items()
    ]

    unidades: dict[str, dict[str, Any]] = {}
    for e in filas:
        clave = str(e.unidad_id) if e.unidad_id is not None else ""
        if clave not in unidades:
            unidades[clave] = {"unidad_id": str(e.unidad_id) if e.unidad_id is not None else None, "unidad_nombre": e.unidad_nombre or "Sin unidad", "total": 0}
        unidades[clave]["total"] += 1
    por_unidad = sorted(unidades.values(), key=lambda u: (-u["total"], u["unidad_nombre"].lower()))

    decisiones_por_expediente: dict[str, GovernmentProcurementDecision | None] = {}
    for e in filas:
        decisiones_por_expediente[str(e.id)] = _decision_vigente(str(e.id), list(decisiones))

    codigos_resultado: list[str] = []
    for e in filas:
        decision_vigente = decisiones_por_expediente.get(str(e.id))
        if decision_vigente is None:
            codigos_resultado.append("SIN_DECISION")
        else:
            codigos_resultado.append(decision_vigente.resultado)
    contador_resultado = Counter(codigos_resultado)
    resultados = [
        {"codigo": codigo, "etiqueta": etiqueta, "total": contador_resultado.get(codigo, 0)}
        for codigo, etiqueta in _ETIQUETAS_RESULTADO.items()
    ]

    ofertas_por_proveedor: dict[tuple[str, str], list[GovernmentProcurementOffer]] = defaultdict(list)
    for oferta in ofertas:
        ofertas_por_proveedor[(oferta.oferente_documento or "", oferta.oferente_nombre or "")].append(oferta)

    adjudicaciones_por_oferta = {
        str(d.offer_id) for d in decisiones if d.estado == "VIGENTE" and d.resultado == "ADJUDICADA" and d.offer_id is not None
    }

    proveedores: list[dict[str, Any]] = []
    for (documento, nombre), ofertas_proveedor in ofertas_por_proveedor.items():
        adjudicaciones = sum(1 for o in ofertas_proveedor if str(o.id) in adjudicaciones_por_oferta)
        proveedores.append({"documento": documento, "nombre": nombre, "ofertas": len(ofertas_proveedor), "adjudicaciones": adjudicaciones})
    proveedores.sort(key=lambda p: (-p["adjudicaciones"], -p["ofertas"], p["nombre"].lower()))

    metrica_por_modalidad: dict[str | None, dict[str, list[float]]] = {codigo: defaultdict(list) for codigo in [*_ETIQUETAS_MODALIDAD.keys(), None]}
    globales: dict[str, list[float]] = defaultdict(list)

    for e in filas:
        recepcion = _fecha_negocio(e.recepcion_concluida_en)
        evaluacion = _fecha_negocio(e.evaluacion_concluida_en)
        decision = decisiones_por_expediente.get(str(e.id))
        decision_fecha = _fecha_negocio(decision.decidida_en) if decision else None

        inicio_recepcion = _dias(recepcion, e.fecha_inicio)
        recepcion_evaluacion = _dias(evaluacion, recepcion)
        evaluacion_decision = _dias(decision_fecha, evaluacion)
        inicio_cierre = _dias(e.cierre_fecha, e.fecha_inicio)

        metricas: dict[str, int | None] = {
            "inicio_recepcion": inicio_recepcion,
            "recepcion_evaluacion": recepcion_evaluacion,
            "evaluacion_decision": evaluacion_decision,
            "inicio_cierre": inicio_cierre,
        }
        modalidad = e.modalidad_declarada
        for clave, valor in metricas.items():
            if valor is not None:
                metrica_por_modalidad[modalidad][clave].append(float(valor))
                globales[clave].append(float(valor))

    tiempos_por_modalidad: list[dict[str, Any]] = []
    for codigo in [*_ETIQUETAS_MODALIDAD.keys(), None]:
        etiqueta = _ETIQUETAS_MODALIDAD.get(codigo, "Sin modalidad declarada") if codigo else "Sin modalidad declarada"
        fila: dict[str, Any] = {"codigo": codigo, "etiqueta": etiqueta, "expedientes": contador_modalidad.get(codigo, 0)}
        for clave in ("inicio_recepcion", "recepcion_evaluacion", "evaluacion_decision", "inicio_cierre"):
            fila[clave] = _promedio([int(v) for v in metrica_por_modalidad[codigo][clave]])
        tiempos_por_modalidad.append(fila)

    tiempos = {
        "por_modalidad": tiempos_por_modalidad,
        "global": {clave: _promedio([int(v) for v in globales[clave]]) for clave in ("inicio_recepcion", "recepcion_evaluacion", "evaluacion_decision", "inicio_cierre")},
    }

    a_tiempo = 0
    con_atraso = 0
    vencidos = 0
    hitos_con_desviacion: list[dict[str, Any]] = []
    hoy = hoy_de_negocio()
    expediente_por_id = {str(e.id): e for e in filas}

    for hito in hitos:
        if hito.estado == "NO_APLICA":
            continue
        expediente = expediente_por_id.get(str(hito.file_id))
        if expediente is None:
            continue
        if hito.estado == "CUMPLIDO":
            if hito.fecha_real is not None and hito.fecha_real <= hito.fecha_prevista:
                a_tiempo += 1
            elif hito.fecha_real is not None:
                dias = (hito.fecha_real - hito.fecha_prevista).days
                con_atraso += 1
                hitos_con_desviacion.append({
                    "expediente_id": str(expediente.id),
                    "expediente_numero": expediente.numero,
                    "hito": hito.nombre,
                    "fecha_prevista": hito.fecha_prevista.isoformat(),
                    "fecha_real": hito.fecha_real.isoformat(),
                    "estado": "CON_ATRASO",
                    "dias": dias,
                })
        elif hito.estado == "PREVISTO" and hito.fecha_prevista < hoy:
            dias = (hoy - hito.fecha_prevista).days
            vencidos += 1
            hitos_con_desviacion.append({
                "expediente_id": str(expediente.id),
                "expediente_numero": expediente.numero,
                "hito": hito.nombre,
                "fecha_prevista": hito.fecha_prevista.isoformat(),
                "fecha_real": hito.fecha_real.isoformat() if hito.fecha_real is not None else None,
                "estado": "VENCIDO",
                "dias": dias,
            })

    hitos_con_desviacion.sort(key=lambda h: -h["dias"])

    desviaciones = {
        "a_tiempo": a_tiempo,
        "con_atraso": con_atraso,
        "vencidos": vencidos,
        "hitos": hitos_con_desviacion[:50],
    }

    monto = {"disponible": False, "motivo": _MONTO_NO_DISPONIBLE}

    return {
        "todos_proveedores": proveedores,
        "proveedores": proveedores[:50],
        "totales": totales,
        "por_modalidad": por_modalidad,
        "por_estado": por_estado,
        "por_tipo": por_tipo,
        "por_unidad": por_unidad,
        "resultados": resultados,
        "tiempos": tiempos,
        "desviaciones": desviaciones,
        "todos_hitos": hitos_con_desviacion,
        "monto": monto,
    }


def reporte(db: Session, ctx: CompanyContext, *, desde: date | None, hasta: date | None) -> dict[str, Any]:
    hoy = hoy_de_negocio()
    desde_final = desde or _inicio_periodo(hoy)
    hasta_final = hasta or hoy
    if desde_final > hasta_final:
        raise KontrolError(
            code="INVALID_DATE_RANGE",
            message="La fecha inicial no puede ser posterior a la fecha final",
            field_errors={"desde": ["La fecha inicial no puede ser posterior a la fecha final"]},
            status_code=422,
        )

    consolidado = _reporte_consolidado(db, ctx, desde=desde_final, hasta=hasta_final)
    return {
        "periodo": {"desde": desde_final.isoformat(), "hasta": hasta_final.isoformat()},
        "generado_en": instante_actual().isoformat(),
        "totales": consolidado["totales"],
        "por_modalidad": consolidado["por_modalidad"],
        "por_estado": consolidado["por_estado"],
        "por_tipo": consolidado["por_tipo"],
        "por_unidad": consolidado["por_unidad"],
        "resultados": consolidado["resultados"],
        "proveedores": consolidado["proveedores"],
        "tiempos": consolidado["tiempos"],
        "desviaciones": consolidado["desviaciones"],
        "monto": consolidado["monto"],
    }


def _escribir_filas(writer: Any, titulo: str, columnas: list[str], filas: list[list[Any]]) -> None:
    writer.writerow([titulo])
    writer.writerow(columnas)
    for fila in filas:
        writer.writerow(["" if v is None else v for v in fila])


def exportar_csv(db: Session, ctx: CompanyContext, *, desde: date | None, hasta: date | None) -> tuple[str, bytes]:
    hoy = hoy_de_negocio()
    desde_final = desde or _inicio_periodo(hoy)
    hasta_final = hasta or hoy
    if desde_final > hasta_final:
        raise KontrolError(
            code="INVALID_DATE_RANGE",
            message="La fecha inicial no puede ser posterior a la fecha final",
            field_errors={"desde": ["La fecha inicial no puede ser posterior a la fecha final"]},
            status_code=422,
        )

    consolidado = _reporte_consolidado(db, ctx, desde=desde_final, hasta=hasta_final)

    salida = io.StringIO()
    writer = csv.writer(salida)

    filas_datos = 0



    writer.writerow(["Reporte de contrataciones", desde_final.isoformat(), hasta_final.isoformat()])

    _escribir_filas(writer, "Por modalidad", ["Modalidad", "Expedientes"], [[i["etiqueta"], i["total"]] for i in consolidado["por_modalidad"]])
    filas_datos += len(consolidado["por_modalidad"])

    _escribir_filas(writer, "Por estado", ["Estado", "Expedientes"], [[i["etiqueta"], i["total"]] for i in consolidado["por_estado"]])
    filas_datos += len(consolidado["por_estado"])

    _escribir_filas(writer, "Por tipo", ["Tipo", "Expedientes"], [[i["etiqueta"], i["total"]] for i in consolidado["por_tipo"]])
    filas_datos += len(consolidado["por_tipo"])

    _escribir_filas(writer, "Por unidad", ["Unidad", "Expedientes"], [[i["unidad_nombre"], i["total"]] for i in consolidado["por_unidad"]])
    filas_datos += len(consolidado["por_unidad"])

    _escribir_filas(writer, "Resultados", ["Resultado", "Expedientes"], [[i["etiqueta"], i["total"]] for i in consolidado["resultados"]])
    filas_datos += len(consolidado["resultados"])

    _escribir_filas(writer, "Proveedores", ["Documento", "Nombre", "Ofertas", "Adjudicaciones"], [[p["documento"], p["nombre"], p["ofertas"], p["adjudicaciones"]] for p in consolidado["todos_proveedores"]])
    filas_datos += len(consolidado["todos_proveedores"])

    _escribir_filas(
        writer,
        "Tiempos promedio por modalidad",
        ["Modalidad", "Expedientes", "Inicio-recepción", "Recepción-evaluación", "Evaluación-decisión", "Inicio-cierre"],
        [[i["etiqueta"], i["expedientes"], i["inicio_recepcion"], i["recepcion_evaluacion"], i["evaluacion_decision"], i["inicio_cierre"]] for i in consolidado["tiempos"]["por_modalidad"]],
    )
    filas_datos += len(consolidado["tiempos"]["por_modalidad"])

    _escribir_filas(
        writer,
        "Hitos con desviación",
        ["Expediente", "Hito", "Fecha prevista", "Fecha real", "Situación", "Días"],
        [[h["expediente_numero"], h["hito"], h["fecha_prevista"], h["fecha_real"], h["estado"], h["dias"]] for h in consolidado["todos_hitos"]],
    )
    filas_datos += len(consolidado["todos_hitos"])

    writer.writerow(["Monto", consolidado["monto"]["motivo"]])
    filas_datos += 1

    contenido = salida.getvalue().encode("utf-8")

    nombre = f"contrataciones-{desde_final.isoformat()}-{hasta_final.isoformat()}.csv"
    record_audit(
        db,
        action="GOV_PROCUREMENT_REPORT_EXPORTED",
        entity_type="GovernmentProcurementFile",
        entity_id=str(ctx.company_id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"filas": filas_datos, "filtros": {"desde": desde_final.isoformat(), "hasta": hasta_final.isoformat()}},
    )
    return nombre, contenido
