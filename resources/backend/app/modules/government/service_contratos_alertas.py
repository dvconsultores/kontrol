"""CNT-09 (GOV-CNT-010): la alerta informa y no decide.
Fuentes: CNT-01+CNT-02 términos efectivos, CNT-03, PROC-10 DIAS_POR_VENCER.
PDD-CNT09-01: las alertas solo informan del vencimiento, nunca aprueban, prorrogan, conforman, reciben, pagan ni cierran.
PDD-CNT09-02: el motor es la Spec 047; crear_alerta es idempotente por (company_id, dedupe_key) y resolver_alerta_de_sistema pasa ACTIVE a RESOLVED sin borrar.
PDD-CNT09-03: la política de preaviso es por empresa y fuente (CONTRATO, HITO, ENTREGABLE) con días de anticipación.
PDD-CNT09-04: las garantías usan el preaviso fijo PROC-10 DIAS_POR_VENCER y su estado REGISTRADA.
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import KontrolError, NotFoundError
from app.core.logging import get_logger
from app.modules.government.garantias_reglas import DIAS_POR_VENCER
from app.modules.government.models import (
    FUENTES_POLITICA_ALERTA,
    GovernmentContract,
    GovernmentContractAlertPolicy,
    GovernmentContractDeliverable,
    GovernmentContractExecutionAct,
    GovernmentContractMilestone,
    GovernmentGuaranteeInstrument,
    GovernmentProcurementFile,
)
from app.modules.government.service_contratos_ejecucion import _conforme, _cumplidos, terminos_efectivos
from app.modules.government.service_garantias import _vigencia
from app.modules.identity_access import authority
from app.modules.identity_access.models import User
from app.modules.notifications import service as notifications_service
from app.modules.notifications.models import Alert
from app.modules.scheduler.service import Contexto, Resultado
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio, instante_actual

logger = get_logger(__name__)

SOURCE_CONTRATO = "GovernmentContract"
SOURCE_HITO = "GovernmentContractMilestone"
SOURCE_ENTREGABLE = "GovernmentContractDeliverable"
SOURCE_GARANTIA = "GovernmentGuaranteeInstrument"
SOURCES = (SOURCE_CONTRATO, SOURCE_HITO, SOURCE_ENTREGABLE, SOURCE_GARANTIA)
SOURCES_CONTRATO = (SOURCE_CONTRATO, SOURCE_HITO, SOURCE_ENTREGABLE)
ROUTE_CONTRATO = "gov_contract"
ROUTE_EJECUCION = "gov_contract_execution"
ROUTE_EXPEDIENTE = "gov_procurement_file"
CATEGORIAS = {
    "contract": "gov.contract.deadline",
    "milestone": "gov.milestone.deadline",
    "deliverable": "gov.deliverable.deadline",
    "guarantee": "gov.guarantee.deadline",
}
FASES = ("UPCOMING", "DUE_TODAY", "OVERDUE")
SEVERIDAD = {"UPCOMING": "INFO", "DUE_TODAY": "WARNING", "OVERDUE": "CRITICAL"}
SEVERIDAD_GARANTIA = {"UPCOMING": "WARNING", "DUE_TODAY": "WARNING", "OVERDUE": "CRITICAL"}
PREFIJO = "cnt09"


def fase(fecha: date, hoy: date, dias_anticipacion: int | None) -> str | None:
    if hoy > fecha:
        return "OVERDUE"
    if hoy == fecha:
        return "DUE_TODAY"
    if dias_anticipacion and 1 <= (fecha - hoy).days <= dias_anticipacion:
        return "UPCOMING"
    return None


def fase_garantia(instrumento: GovernmentGuaranteeInstrument, hoy: date) -> str | None:
    if instrumento.estado != "REGISTRADA":
        return None
    estado, _ = _vigencia(instrumento, hoy)
    if estado == "VENCIDA":
        return "OVERDUE"
    if estado == "POR_VENCER":
        return "DUE_TODAY" if instrumento.vigente_hasta == hoy else "UPCOMING"
    return None


def clave(tipo: str, id_: str, fecha: date, fase_: str) -> str:
    return f"{PREFIJO}:{tipo}:{id_}:{fecha.isoformat()}:{fase_}"


def _base(dedupe_key: str) -> str:
    return re.sub(r":r\d+$", "", dedupe_key)


def _fecha_texto(fecha: date) -> str:
    return fecha.strftime("%d/%m/%Y")


def politicas_activas(db: Session, company_id: str) -> dict[str, int]:
    filas = db.scalars(
        select(GovernmentContractAlertPolicy).where(
            GovernmentContractAlertPolicy.company_id == company_id,
            GovernmentContractAlertPolicy.activo.is_(True),
        )
    ).all()
    return {p.fuente: p.dias_anticipacion for p in filas if p.dias_anticipacion is not None}


def condiciones(db: Session, company_id: str, hoy: date) -> list[notifications_service.Efecto]:
    dias = politicas_activas(db, company_id)
    cerrados = set(
        db.scalars(
            select(GovernmentContractExecutionAct.contract_id).where(
                GovernmentContractExecutionAct.company_id == company_id,
                GovernmentContractExecutionAct.tipo == "CIERRE",
            )
        ).all()
    )
    efectos: list[notifications_service.Efecto] = []

    contratos = db.scalars(
        select(GovernmentContract)
        .where(
            GovernmentContract.company_id == company_id,
            GovernmentContract.estado == "FORMALIZADO",
        )
        .order_by(GovernmentContract.id)
    ).all()
    for contrato in contratos:
        if contrato.id in cerrados:
            continue
        codigo = contrato.codigo or contrato.expediente_numero
        t = terminos_efectivos(db, contrato, hoy)
        fin = t["fecha_fin"]
        if fin is not None:
            f = fase(fin, hoy, dias.get("CONTRATO"))
            if f is not None:
                efectos.append(
                    notifications_service.Efecto(
                        company_id=company_id,
                        category=CATEGORIAS["contract"],
                        severity=SEVERIDAD[f],
                        message_key=f"{CATEGORIAS['contract']}.{f.lower()}.alert",
                        message_params={"codigo": codigo, "fecha": _fecha_texto(fin)},
                        source_type=SOURCE_CONTRATO,
                        source_id=str(contrato.id),
                        route_key=ROUTE_CONTRATO,
                        dedupe_key=clave("contract", str(contrato.id), fin, f),
                    )
                )
        cumplidos = _cumplidos(db, str(contrato.id))
        hitos = db.scalars(
            select(GovernmentContractMilestone)
            .where(
                GovernmentContractMilestone.company_id == company_id,
                GovernmentContractMilestone.contract_id == contrato.id,
                GovernmentContractMilestone.estado == "VIGENTE",
            )
            .order_by(GovernmentContractMilestone.numero)
        ).all()
        for h in hitos:
            if h.id in cumplidos:
                continue
            f = fase(h.fecha_prevista, hoy, dias.get("HITO"))
            if f is not None:
                efectos.append(
                    notifications_service.Efecto(
                        company_id=company_id,
                        category=CATEGORIAS["milestone"],
                        severity=SEVERIDAD[f],
                        message_key=f"{CATEGORIAS['milestone']}.{f.lower()}.alert",
                        message_params={"codigo": codigo, "numero": f"HIT-{h.numero:02d}", "fecha": _fecha_texto(h.fecha_prevista)},
                        source_type=SOURCE_HITO,
                        source_id=str(contrato.id),
                        source_item_id=str(h.id),
                        route_key=ROUTE_EJECUCION,
                        dedupe_key=clave("milestone", str(h.id), h.fecha_prevista, f),
                    )
                )
        entregables = db.scalars(
            select(GovernmentContractDeliverable)
            .where(
                GovernmentContractDeliverable.company_id == company_id,
                GovernmentContractDeliverable.contract_id == contrato.id,
                GovernmentContractDeliverable.estado == "VIGENTE",
            )
            .order_by(GovernmentContractDeliverable.numero)
        ).all()
        for e in entregables:
            if _conforme(db, str(e.id)):
                continue
            f = fase(e.fecha_vencimiento, hoy, dias.get("ENTREGABLE"))
            if f is not None:
                efectos.append(
                    notifications_service.Efecto(
                        company_id=company_id,
                        category=CATEGORIAS["deliverable"],
                        severity=SEVERIDAD[f],
                        message_key=f"{CATEGORIAS['deliverable']}.{f.lower()}.alert",
                        message_params={"codigo": codigo, "numero": f"ENT-{e.numero:02d}", "fecha": _fecha_texto(e.fecha_vencimiento)},
                        source_type=SOURCE_ENTREGABLE,
                        source_id=str(contrato.id),
                        source_item_id=str(e.id),
                        route_key=ROUTE_EJECUCION,
                        dedupe_key=clave("deliverable", str(e.id), e.fecha_vencimiento, f),
                    )
                )

    garantias = db.scalars(
        select(GovernmentGuaranteeInstrument)
        .where(
            GovernmentGuaranteeInstrument.company_id == company_id,
            GovernmentGuaranteeInstrument.estado == "REGISTRADA",
        )
        .order_by(GovernmentGuaranteeInstrument.id)
    ).all()
    for g in garantias:
        f = fase_garantia(g, hoy)
        if f is None:
            continue
        expediente = db.get(GovernmentProcurementFile, g.file_id)
        numero = expediente.numero if expediente else g.file_id
        efectos.append(
            notifications_service.Efecto(
                company_id=company_id,
                category=CATEGORIAS["guarantee"],
                severity=SEVERIDAD_GARANTIA[f],
                message_key=f"{CATEGORIAS['guarantee']}.{f.lower()}.alert",
                message_params={"referencia": g.referencia_emisor, "expediente": numero, "fecha": _fecha_texto(g.vigente_hasta)},
                source_type=SOURCE_GARANTIA,
                source_id=str(g.file_id),
                source_item_id=str(g.id),
                route_key=ROUTE_EXPEDIENTE,
                dedupe_key=clave("guarantee", str(g.id), g.vigente_hasta, f),
            )
        )
    return efectos


def reconciliar(db: Session, company_id: str, hoy: date, momento: datetime, correlation_id: str | None) -> tuple[int, int]:
    deseadas = condiciones(db, company_id, hoy)
    bases = {e.dedupe_key for e in deseadas}
    activas = db.scalars(
        select(Alert).where(
            Alert.company_id == company_id,
            Alert.status == "ACTIVE",
            Alert.source_type.in_(SOURCES),
            Alert.dedupe_key.like(f"{PREFIJO}:%"),
        )
    ).all()
    resueltas = 0
    for a in activas:
        if _base(a.dedupe_key) not in bases:
            if notifications_service.resolver_alerta_de_sistema(db, company_id=company_id, dedupe_key=a.dedupe_key, momento=momento):
                resueltas += 1
    creadas = 0
    for e in deseadas:
        existentes = db.scalars(
            select(Alert).where(
                Alert.company_id == company_id,
                (Alert.dedupe_key == e.dedupe_key) | (Alert.dedupe_key.like(f"{e.dedupe_key}:r%")),
            )
        ).all()
        if any(a.status == "ACTIVE" for a in existentes):
            continue
        if not existentes:
            clave_final = e.dedupe_key
        else:
            clave_final = f"{e.dedupe_key}:r{len(existentes) + 1}"
        _, creada = notifications_service.crear_alerta(db, replace(e, dedupe_key=clave_final, correlation_id=correlation_id))
        if creada:
            creadas += 1
    return creadas, resueltas


def detectar(contexto: Contexto) -> Resultado:
    hoy = hoy_de_negocio(contexto.now)
    resultado = Resultado()
    with contexto.session_factory() as db:
        empresas = set(
            db.scalars(
                select(GovernmentContract.company_id).where(GovernmentContract.estado == "FORMALIZADO")
            ).all()
        )
        empresas.update(
            db.scalars(
                select(GovernmentGuaranteeInstrument.company_id).where(GovernmentGuaranteeInstrument.estado == "REGISTRADA")
            ).all()
        )
        empresas.update(
            db.scalars(
                select(Alert.company_id).where(
                    Alert.status == "ACTIVE",
                    Alert.source_type.in_(SOURCES),
                )
            ).all()
        )
    for company_id in sorted(empresas):
        try:
            with contexto.session_factory() as db:
                c, r = reconciliar(db, company_id, hoy, contexto.now, contexto.correlation_id)
                db.commit()
                resultado.seen += 1
                resultado.processed += c + r
        except Exception:
            # Aísla el fallo de una empresa para no interrumpir el resto del recorrido.
            logger.exception("cnt09.company_failed", extra={"company_id": company_id})
            resultado.failed += 1
    return resultado


def alertas_del_contrato(db: Session, ctx: CompanyContext, user: User, contrato_id: str, estado: str) -> dict[str, Any]:
    contrato = db.get(GovernmentContract, contrato_id)
    if contrato is None or contrato.company_id != ctx.company_id:
        raise NotFoundError("GOV_CONTRACT_NOT_FOUND", "Contrato u orden no encontrado")
    condicion = Alert.company_id == ctx.company_id
    condicion &= (Alert.source_type.in_(SOURCES_CONTRATO) & (Alert.source_id == contrato.id))
    capacidades = authority.capabilities_in_company(db, user, ctx.company_id)
    if "gobierno_garantias:view" in capacidades:
        subconsulta = (
            select(GovernmentGuaranteeInstrument.id).where(
                GovernmentGuaranteeInstrument.file_id == contrato.file_id,
                GovernmentGuaranteeInstrument.offer_id == contrato.offer_id,
                GovernmentGuaranteeInstrument.company_id == ctx.company_id,
            )
        )
        condicion |= (Alert.source_type == SOURCE_GARANTIA) & (Alert.source_id == contrato.file_id) & (Alert.source_item_id.in_(subconsulta))
    consulta = select(Alert).where(condicion)
    if estado != "ALL":
        consulta = consulta.where(Alert.status == estado)
    consulta = consulta.order_by(Alert.created_at.desc(), Alert.id.desc())
    alertas = db.scalars(consulta).all()
    activas = sum(1 for a in alertas if a.status == "ACTIVE")
    items = []
    for a in alertas:
        items.append(
            {
                "id": a.id,
                "category": a.category,
                "severity": a.severity,
                "status": a.status,
                "message": notifications_service._mensaje(a.message_key, a.message_params),
                "link": notifications_service._enlace(a.source_type, a.source_id, a.source_item_id, a.route_key),
                "created_at": a.created_at,
                "resolved_at": a.resolved_at,
            }
        )
    return {"contrato_id": contrato.id, "activas": activas, "items": items}


def _politicas_actuales(db: Session, company_id: str) -> dict[str, bool | int | None]:
    filas = db.scalars(
        select(GovernmentContractAlertPolicy).where(GovernmentContractAlertPolicy.company_id == company_id)
    ).all()
    por_fuente = {p.fuente: p for p in filas}
    return {f: (por_fuente[f].dias_anticipacion if por_fuente[f].activo else None) for f in FUENTES_POLITICA_ALERTA if f in por_fuente}


def politicas(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    filas = db.scalars(
        select(GovernmentContractAlertPolicy).where(GovernmentContractAlertPolicy.company_id == ctx.company_id)
    ).all()
    por_fuente = {p.fuente: p for p in filas}
    items = [
        {
            "fuente": f,
            "activo": por_fuente[f].activo if f in por_fuente else False,
            "dias_anticipacion": por_fuente[f].dias_anticipacion if f in por_fuente else None,
        }
        for f in FUENTES_POLITICA_ALERTA
    ]
    return {"items": items, "garantias_dias_por_vencer": DIAS_POR_VENCER, "fases_por_defecto": ["DUE_TODAY", "OVERDUE"]}


def guardar_politicas(db: Session, ctx: CompanyContext, user: User, items: list[dict[str, Any]]) -> dict[str, Any]:
    fuentes = [i["fuente"] for i in items]
    if len(fuentes) != len(set(fuentes)):
        raise KontrolError(code="GOV_CONTRACT_ALERT_POLICY_INVALID", message="Cada fuente aparece una sola vez", status_code=422)
    for i in items:
        if i["activo"] and i.get("dias_anticipacion") is None:
            raise KontrolError(code="GOV_CONTRACT_ALERT_POLICY_INVALID", message="Indique los días de anticipación", status_code=422)
    before = _politicas_actuales(db, ctx.company_id)
    for i in items:
        fila = db.scalars(
            select(GovernmentContractAlertPolicy).where(
                GovernmentContractAlertPolicy.company_id == ctx.company_id,
                GovernmentContractAlertPolicy.fuente == i["fuente"],
            )
        ).first()
        if fila is None:
            fila = GovernmentContractAlertPolicy(company_id=ctx.company_id, fuente=i["fuente"])
            db.add(fila)
        fila.activo = i["activo"]
        fila.dias_anticipacion = i.get("dias_anticipacion")
        fila.actualizado_por = ctx.user_id
        fila.actualizado_en = instante_actual()
    db.flush()
    after = _politicas_actuales(db, ctx.company_id)
    record_audit(
        db,
        action="GOV_CONTRACT_ALERT_POLICY_UPDATED",
        entity_type="GovernmentContractAlertPolicy",
        entity_id=ctx.company_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        before=before,
        after=after,
        source="API",
    )
    return politicas(db, ctx)
