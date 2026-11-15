"""Límite monetario de la autoridad al adjudicar (PROC-08, delta AAL; OQ-OMA-01)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError
from app.modules.government.models import (
    GovernmentAct,
    GovernmentPosition,
    GovernmentProcurementOffer,
    GovernmentProcurementOfferAmount,
    GovernmentStructure,
)
from app.modules.government.service_autoridad import competencias_en_vigor
from app.modules.government.service_ofertas_montos import _texto
from app.shared.audit import record_audit_after_rollback

ESTADOS_LIMITE: dict[str, str] = {
    "DENTRO_LIMITE": "Dentro del límite",
    "SIN_LIMITE": "Sin límite",
    "EXCEDE_LIMITE": "Excede el límite",
    "MONEDA_DISTINTA": "No comparable por moneda",
    "MONTO_NO_DECLARADO": "Monto no declarado",
    "SIN_COMPETENCIA": "Sin competencia vigente",
}

CODIGOS_BLOQUEO: dict[str, str] = {
    "EXCEDE_LIMITE": "GOV_DECISION_AUTHORITY_AMOUNT_EXCEEDED",
    "MONEDA_DISTINTA": "GOV_DECISION_AUTHORITY_CURRENCY_MISMATCH",
    "MONTO_NO_DECLARADO": "GOV_DECISION_OFFER_AMOUNT_REQUIRED",
}


def competencia_en_vigor(
    db: Session, cargo: GovernmentPosition | None, fecha: date, accion: str, materia: str
) -> dict[str, Any] | None:
    if cargo is None:
        return None
    for competencia in competencias_en_vigor(db, cargo, fecha):
        if competencia["accion"] == accion and competencia["materia"] == materia:
            return competencia
    return None


def competencia_aprobar_contrataciones(
    db: Session, company_id: str, cargo: GovernmentPosition | None, fecha: date
) -> dict[str, Any] | None:
    return competencia_en_vigor(db, cargo, fecha, "APROBAR", "CONTRATACIONES")


def clasificar_monto(
    tipo_limite: str | None,
    monto_limite: str | None,
    moneda_limite: str | None,
    monto: Decimal | None,
    moneda: str | None,
) -> str:
    """Regla AAL (OQ-OMA-01): compara un monto con el límite de una competencia, sin convertir monedas."""
    if tipo_limite is None:
        return "SIN_COMPETENCIA"
    if tipo_limite == "SIN_LIMITE":
        return "SIN_LIMITE"
    if monto is None:
        return "MONTO_NO_DECLARADO"
    if moneda != moneda_limite:
        return "MONEDA_DISTINTA"
    if Decimal(monto) > Decimal(str(monto_limite)):
        return "EXCEDE_LIMITE"
    return "DENTRO_LIMITE"


def _cargo_del_acto(db: Session, company_id: str, acto: GovernmentAct) -> GovernmentPosition | None:
    return db.scalar(
        select(GovernmentPosition).where(
            GovernmentPosition.id == acto.cargo_id,
            GovernmentPosition.company_id == company_id,
        )
    )


def _monto_vigente(
    db: Session, company_id: str, oferta: GovernmentProcurementOffer
) -> GovernmentProcurementOfferAmount | None:
    return db.scalar(
        select(GovernmentProcurementOfferAmount)
        .where(
            GovernmentProcurementOfferAmount.company_id == company_id,
            GovernmentProcurementOfferAmount.offer_id == oferta.id,
        )
        .order_by(GovernmentProcurementOfferAmount.version.desc())
        .limit(1)
    )


def limite_de_competencia(cargo: GovernmentPosition | None, comp: dict[str, Any] | None) -> dict[str, Any]:
    if comp is None:
        return {
            "cargo": cargo.name if cargo else None,
            "tipo_limite": None,
            "monto": None,
            "moneda": None,
            "etiqueta": "Sin competencia vigente",
        }
    if comp["tipo_limite"] == "SIN_LIMITE":
        return {
            "cargo": cargo.name if cargo else None,
            "tipo_limite": "SIN_LIMITE",
            "monto": None,
            "moneda": None,
            "etiqueta": "Sin límite",
        }
    return {
        "cargo": cargo.name if cargo else None,
        "tipo_limite": "MONTO",
        "monto": _texto(Decimal(str(comp["monto"]))),
        "moneda": comp["moneda"],
        "etiqueta": f"{_texto(Decimal(str(comp['monto'])))} {comp['moneda']}",
    }


def limite_del_acto(db: Session, ctx: CompanyContext, acto: GovernmentAct) -> dict[str, Any]:
    cargo = _cargo_del_acto(db, ctx.company_id, acto)
    comp = competencia_aprobar_contrataciones(db, ctx.company_id, cargo, acto.fecha)
    if comp is None:
        return {
            "cargo": cargo.name if cargo else None,
            "tipo_limite": None,
            "monto": None,
            "moneda": None,
            "etiqueta": "Sin competencia vigente",
        }
    if comp["tipo_limite"] == "SIN_LIMITE":
        return {
            "cargo": cargo.name if cargo else None,
            "tipo_limite": "SIN_LIMITE",
            "monto": None,
            "moneda": None,
            "etiqueta": "Sin límite",
        }
    monto = _texto(Decimal(str(comp["monto"])))
    moneda = comp["moneda"]
    return {
        "cargo": cargo.name if cargo else None,
        "tipo_limite": "MONTO",
        "monto": monto,
        "moneda": moneda,
        "etiqueta": f"{monto} {moneda}",
    }


def evaluar_limite(
    db: Session, ctx: CompanyContext, acto: GovernmentAct, oferta: GovernmentProcurementOffer
) -> dict[str, Any]:
    limite = limite_del_acto(db, ctx, acto)
    cargo_texto = limite["cargo"] or "el cargo del acto"
    fila = _monto_vigente(db, ctx.company_id, oferta)
    monto_oferta = (
        {
            "total_con_tributos": _texto(fila.total_con_tributos),
            "moneda": fila.moneda,
        }
        if fila
        else None
    )

    estado = clasificar_monto(
        limite["tipo_limite"],
        limite["monto"],
        limite["moneda"],
        Decimal(fila.total_con_tributos) if fila is not None else None,
        fila.moneda if fila is not None else None,
    )

    total = monto_oferta["total_con_tributos"] if monto_oferta else None
    moneda = monto_oferta["moneda"] if monto_oferta else None
    lim = limite["monto"]
    mon_l = limite["moneda"]

    if estado == "DENTRO_LIMITE":
        mensaje = f"El total declarado de la oferta ({total} {moneda}) está dentro del límite de aprobación de {cargo_texto} ({lim} {mon_l})."
    elif estado == "SIN_LIMITE":
        mensaje = f"{cargo_texto} aprueba contrataciones sin límite de monto."
    elif estado == "EXCEDE_LIMITE":
        mensaje = f"El total declarado de la oferta ({total} {moneda}) excede el límite de aprobación de {cargo_texto} ({lim} {mon_l}). Use el acto de una autoridad con límite suficiente."
    elif estado == "MONEDA_DISTINTA":
        mensaje = f"No puede verificarse el límite de esta autoridad porque la oferta y el límite están expresados en monedas diferentes. La oferta está en {moneda} y el límite de {cargo_texto} es {lim} {mon_l}. Use una autoridad con límite en {moneda} o sin límite."
    elif estado == "MONTO_NO_DECLARADO":
        mensaje = f"La oferta no tiene monto declarado y {cargo_texto} tiene un límite de aprobación de {lim} {mon_l}. Sin el monto no puede verificarse el límite: use una autoridad sin límite."
    else:
        mensaje = "El cargo del acto no tenía la competencia Aprobar sobre Contrataciones en la fecha del acto."

    return {
        "offer_id": oferta.id,
        "oferta": f"O-{oferta.numero:02d}",
        "estado": estado,
        "estado_etiqueta": ESTADOS_LIMITE[estado],
        "permite": estado in ("DENTRO_LIMITE", "SIN_LIMITE"),
        "mensaje": mensaje,
        "cargo": limite["cargo"],
        "limite": limite,
        "monto_oferta": monto_oferta,
    }


def exigir_limite(
    db: Session, ctx: CompanyContext, expediente_id: str, acto: GovernmentAct, oferta_id: str
) -> None:
    oferta = db.scalar(
        select(GovernmentProcurementOffer).where(
            GovernmentProcurementOffer.id == oferta_id,
            GovernmentProcurementOffer.company_id == ctx.company_id,
            GovernmentProcurementOffer.file_id == expediente_id,
        )
    )
    if oferta is None:
        raise KontrolError(
            code="GOV_DECISION_OPTION_ORDER",
            message="La oferta no es una opción de la recomendación vigente",
            status_code=422,
            field_errors={"oferta_id": ["Oferta no recomendada"]},
        )

    cargo = _cargo_del_acto(db, ctx.company_id, acto)
    if cargo is not None:
        db.execute(
            select(GovernmentStructure)
            .where(
                GovernmentStructure.id == cargo.structure_id,
                GovernmentStructure.company_id == ctx.company_id,
            )
            .with_for_update()
        ).scalar_one_or_none()

    ev = evaluar_limite(db, ctx, acto, oferta)
    if ev["permite"]:
        return

    if ev["estado"] == "SIN_COMPETENCIA":
        raise KontrolError(
            code="GOV_DECISION_INVALID_ACT",
            message="La autoridad del acto no es válida para aprobar contrataciones",
            status_code=422,
            field_errors={"acto_id": ["Autoridad del acto inválida"]},
        )

    codigo = CODIGOS_BLOQUEO[ev["estado"]]
    acto_texto = f"{acto.tipo} {acto.numero}"
    tenant_id = ctx.tenant_id
    company_id = ctx.company_id
    user_id = ctx.user_id
    details = {
        "monto": ev["monto_oferta"]["total_con_tributos"] if ev["monto_oferta"] else None,
        "moneda": ev["monto_oferta"]["moneda"] if ev["monto_oferta"] else None,
        "limite": ev["limite"]["monto"],
        "moneda_limite": ev["limite"]["moneda"],
        "cargo": ev["cargo"],
    }

    record_audit_after_rollback(
        db,
        action="GOV_PROCUREMENT_DECISION_AUTHORITY_BLOCKED",
        entity_type="GovernmentProcurementFile",
        entity_id=expediente_id,
        tenant_id=tenant_id,
        company_id=company_id,
        user_id=user_id,
        after={
            "acto": acto_texto,
            "oferta": ev["oferta"],
            "causal": codigo,
            "resultado": "ADJUDICADA",
        },
    )

    raise ConflictError(codigo, ev["mensaje"], details=details)
