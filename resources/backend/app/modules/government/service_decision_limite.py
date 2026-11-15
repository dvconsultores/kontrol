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
from app.modules.government.service_tasas import verificar_limite
from app.shared.audit import record_audit_after_rollback

ESTADOS_LIMITE: dict[str, str] = {
    "DENTRO_LIMITE": "Dentro del límite",
    "SIN_LIMITE": "Sin límite",
    "EXCEDE_LIMITE": "Excede el límite",
    "SIN_TASA": "Sin tasa oficial aprobada",
    "MONTO_NO_DECLARADO": "Monto no declarado",
    "SIN_COMPETENCIA": "Sin competencia vigente",
}

CODIGOS_BLOQUEO: dict[str, str] = {
    "EXCEDE_LIMITE": "GOV_DECISION_AUTHORITY_AMOUNT_EXCEEDED",
    "SIN_TASA": "GOV_OFFICIAL_RATE_REQUIRED",
    "MONTO_NO_DECLARADO": "GOV_DECISION_OFFER_AMOUNT_REQUIRED",
}


def competencia_aprobar_contrataciones(
    db: Session, company_id: str, cargo: GovernmentPosition | None, fecha: date
) -> dict[str, Any] | None:
    if cargo is None:
        return None
    for competencia in competencias_en_vigor(db, cargo, fecha):
        if competencia["accion"] == "APROBAR" and competencia["materia"] == "CONTRATACIONES":
            return competencia
    return None


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
    db: Session,
    ctx: CompanyContext,
    acto: GovernmentAct,
    oferta: GovernmentProcurementOffer,
    *,
    bloquear: bool = False,
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

    conversion: dict[str, Any] | None = None
    monedas_sin_tasa: list[str] = []

    if limite["tipo_limite"] is None:
        estado = "SIN_COMPETENCIA"
    elif limite["tipo_limite"] == "SIN_LIMITE":
        estado = "SIN_LIMITE"
    elif fila is None:
        estado = "MONTO_NO_DECLARADO"
    else:
        conv = verificar_limite(
            db,
            ctx,
            fila.moneda,
            Decimal(fila.total_con_tributos),
            Decimal(limite["monto"]),
            limite["moneda"],
            acto.fecha,
            bloquear=bloquear,
            exigir=False,
        )
        if conv["resultado"] == "SIN_TASA":
            estado = "SIN_TASA"
            monedas_sin_tasa = conv["monedas_sin_tasa"]
        elif conv["resultado"] == "EXCEDE_LIMITE":
            estado = "EXCEDE_LIMITE"
        else:
            estado = "DENTRO_LIMITE"
        conversion = conv if conv["requiere_conversion"] and conv["resultado"] != "SIN_TASA" else None

    total = monto_oferta["total_con_tributos"] if monto_oferta else None
    moneda = monto_oferta["moneda"] if monto_oferta else None
    lim = limite["monto"]
    mon_l = limite["moneda"]
    fecha_txt = acto.fecha.strftime("%d/%m/%Y")

    if estado == "DENTRO_LIMITE" and conversion is None:
        mensaje = f"El total declarado de la oferta ({total} {moneda}) está dentro del límite de aprobación de {cargo_texto} ({lim} {mon_l})."
    elif estado == "DENTRO_LIMITE" and conversion is not None:
        mensaje = f"El total declarado de la oferta ({total} {moneda}) equivale a {conversion['total_ves']} VES y está dentro del límite de aprobación de {cargo_texto} ({lim} {mon_l}, equivalente a {conversion['limite_ves']} VES) con la tasa oficial BCV aplicable al {fecha_txt}."
    elif estado == "SIN_LIMITE":
        mensaje = f"{cargo_texto} aprueba contrataciones sin límite de monto."
    elif estado == "EXCEDE_LIMITE" and conversion is None:
        mensaje = f"El total declarado de la oferta ({total} {moneda}) excede el límite de aprobación de {cargo_texto} ({lim} {mon_l}). Use el acto de una autoridad con límite suficiente."
    elif estado == "EXCEDE_LIMITE" and conversion is not None:
        mensaje = f"El total declarado de la oferta ({total} {moneda}) equivale a {conversion['total_ves']} VES y excede el límite de aprobación de {cargo_texto} ({lim} {mon_l}, equivalente a {conversion['limite_ves']} VES) con la tasa oficial BCV aplicable al {fecha_txt}. Use el acto de una autoridad con límite suficiente."
    elif estado == "SIN_TASA":
        mensaje = f"No hay tasa oficial BCV aprobada aplicable al {fecha_txt} para {', '.join(monedas_sin_tasa)}: la oferta está en {moneda} y el límite de {cargo_texto} es {lim} {mon_l}. Registre y apruebe la tasa en Tesorería → Tasas oficiales."
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
        "conversion": conversion,
        "monedas_sin_tasa": monedas_sin_tasa if estado == "SIN_TASA" else [],
    }


def exigir_limite(
    db: Session, ctx: CompanyContext, expediente_id: str, acto: GovernmentAct, oferta_id: str
) -> dict[str, Any] | None:
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

    ev = evaluar_limite(db, ctx, acto, oferta, bloquear=True)
    if ev["permite"]:
        return ev["conversion"]

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

    if ev["estado"] == "SIN_TASA":
        from app.modules.government.monedas import canonical_currency

        raise KontrolError(
            code="GOV_OFFICIAL_RATE_REQUIRED",
            message=ev["mensaje"],
            status_code=422,
            details={
                **details,
                "moneda_operacion": canonical_currency(ev["monto_oferta"]["moneda"]) if ev["monto_oferta"] else None,
                "moneda_limite": canonical_currency(ev["limite"]["moneda"]),
                "fecha": acto.fecha.isoformat(),
                "monedas_sin_tasa": ev["monedas_sin_tasa"],
            },
        )

    raise ConflictError(
        codigo,
        ev["mensaje"],
        details={**details, "conversion": ev["conversion"]},
    )


def resumen_conversion(conv: dict[str, Any] | None) -> dict[str, Any] | None:
    if conv is None:
        return None
    return {
        "moneda_operacion": conv["moneda_operacion"],
        "moneda_limite": conv["moneda_limite"],
        "fecha": conv["fecha"],
        "tasas": [
            {
                "tasa_id": t["tasa_id"],
                "moneda": t["moneda"],
                "version": t["version"],
            }
            for t in conv["tasas"]
        ],
    }
