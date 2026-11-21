from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError
from app.modules.government.models import (
    GovernmentPayment,
    GovernmentWithholdingSettlement,
)


def liquidacion_activa(
    db: Session, company_id: str, payment_id: str
) -> GovernmentWithholdingSettlement | None:
    return db.scalars(
        select(GovernmentWithholdingSettlement).where(
            GovernmentWithholdingSettlement.company_id == company_id,
            GovernmentWithholdingSettlement.payment_id == payment_id,
            GovernmentWithholdingSettlement.estado != "ANULADA",
        )
    ).one_or_none()


def montos_de_pago(
    db: Session, ctx: CompanyContext, pago: GovernmentPayment
) -> dict[str, Any]:
    activa = liquidacion_activa(db, ctx.company_id, str(pago.id))
    if activa is None:
        return {
            "bruto": f"{pago.monto:.2f}",
            "total_retenido": "0.00",
            "neto": f"{pago.monto:.2f}",
            "moneda": pago.moneda,
            "liquidacion_id": None,
            "estado_liquidacion": None,
            "definitivo": False,
        }
    return {
        "bruto": f"{activa.bruto:.2f}",
        "total_retenido": f"{activa.total_retenido:.2f}",
        "neto": f"{activa.neto:.2f}",
        "moneda": activa.moneda,
        "liquidacion_id": str(activa.id),
        "estado_liquidacion": activa.estado,
        "definitivo": activa.estado == "APLICADA",
    }


def exigir_sin_liquidacion(
    db: Session, ctx: CompanyContext, pago: GovernmentPayment
) -> None:
    if liquidacion_activa(db, ctx.company_id, str(pago.id)) is not None:
        raise ConflictError(
            "GOV_WITHHOLDING_SETTLEMENT_EXISTS",
            "El pago tiene una liquidación de retenciones activa; anúlela antes",
        )
