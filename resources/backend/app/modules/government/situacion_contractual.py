"""Situación jurídica del contrato por fecha (CNT-07, GOV-CNT-008). Sin dependencias de otros servicios: la consultan CNT-02, CNT-03, CNT-04, CNT-08 y CNT-09."""

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.modules.government.models import (
    GovernmentAct,
    GovernmentContractExecutionAct,
    GovernmentContractTermination,
)

ETIQUETA_FIGURA = {
    "RESCISION_NO_IMPUTABLE": "Rescisión unilateral por causa no imputable al contratista",
    "RESOLUCION_MUTUO_ACUERDO": "Resolución por mutuo acuerdo",
    "RESCISION_IMPUTABLE": "Rescisión por causa imputable al contratista",
}
ETIQUETA_SITUACION = {"VIGENTE": "Vigente", "EXTINGUIDO": "Extinguido"}
MENSAJE_ACTO_BASE = "Acto base revocado o declarado nulo: requiere actuación jurídica. La extinción no se reactiva automáticamente."


def terminacion_formalizada(db: Session, company_id: str, contract_id: str) -> GovernmentContractTermination | None:
    return db.execute(
        select(GovernmentContractTermination).where(
            GovernmentContractTermination.company_id == company_id,
            GovernmentContractTermination.contract_id == contract_id,
            GovernmentContractTermination.estado == "FORMALIZADA",
        )
    ).scalar_one_or_none()


def fecha_limite(db: Session, company_id: str, contract_id: str) -> date | None:
    t = terminacion_formalizada(db, company_id, contract_id)
    if t is None:
        return None
    return t.conclusion_hasta if t.conclusion_hasta else t.fecha_eficacia


def situacion_contractual(db: Session, company_id: str, contract_id: str, fecha: date) -> dict[str, Any]:
    t = terminacion_formalizada(db, company_id, contract_id)
    extinguido = t is not None and t.fecha_eficacia is not None and t.fecha_eficacia <= fecha
    cumplimiento = (
        db.execute(
            select(GovernmentContractExecutionAct).where(
                GovernmentContractExecutionAct.contract_id == contract_id,
                GovernmentContractExecutionAct.tipo == "CIERRE",
            )
        ).scalar_one_or_none()
        is not None
    )
    alerta = None
    if t and t.act_id:
        acto = db.get(GovernmentAct, t.act_id)
        if acto and acto.status in ("REVOCADO", "NULO"):
            alerta = {
                "estado": acto.status,
                "mensaje": MENSAJE_ACTO_BASE,
                "enlace": f"/gobierno/actos/{acto.id}",
            }
    limite = fecha_limite(db, company_id, contract_id)
    estado = "EXTINGUIDO" if extinguido else "VIGENTE"
    return {
        "estado": estado,
        "estado_etiqueta": ETIQUETA_SITUACION[estado],
        "figura": t.figura if t is not None and extinguido else None,
        "figura_etiqueta": ETIQUETA_FIGURA[t.figura] if t is not None and extinguido else None,
        "fecha_eficacia": t.fecha_eficacia.isoformat() if t and t.fecha_eficacia else None,
        "fecha_limite_ejecucion": limite.isoformat() if limite else None,
        "cumplimiento_cnt03": cumplimiento,
        "alerta_acto_base": alerta,
    }


def exigir_vigente_en(db: Session, company_id: str, contract_id: str, fecha: date) -> None:
    limite = fecha_limite(db, company_id, contract_id)
    if limite is not None and fecha > limite:
        t = terminacion_formalizada(db, company_id, contract_id)
        figura = t.figura if t is not None else ""
        raise ConflictError(
            "GOV_CONTRACT_TERMINATED",
            f"El contrato está extinguido ({ETIQUETA_FIGURA.get(figura, 'terminación')}): no admite hechos posteriores al {limite:%d/%m/%Y}",
            details={"fecha_limite": limite.isoformat(), "figura": figura},
        )


def exigir_vigente_para_modificacion(db: Session, company_id: str, contract_id: str, fecha: date) -> None:
    t = terminacion_formalizada(db, company_id, contract_id)
    if t and t.fecha_eficacia and fecha >= t.fecha_eficacia:
        raise ConflictError(
            "GOV_CONTRACT_TERMINATED",
            f"El contrato está extinguido ({ETIQUETA_FIGURA[t.figura]}): no admite hechos posteriores al {t.fecha_eficacia:%d/%m/%Y}",
            details={"fecha_limite": t.fecha_eficacia.isoformat(), "figura": t.figura},
        )
