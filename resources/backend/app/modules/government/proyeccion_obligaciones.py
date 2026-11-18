"""Proyección neutral de obligaciones del causado (BUD-09) para la orden de pago (TRE-03)."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.government.models import (
    GovernmentPaymentOrder,
    GovernmentPaymentOrderLine,
)


def montos_ordenados(db: Session, company_id: str, cause_ids: Iterable[str]) -> dict[str, Decimal]:
    """Suma por causa de las líneas de órdenes de pago emitidas del ente.

    Incluye las causas pedidas sin órdenes, con monto 0.00.
    """
    pedidos = list(cause_ids)
    resultado = {cause_id: Decimal("0.00") for cause_id in pedidos}
    if not pedidos:
        return resultado
    suma = func.coalesce(func.sum(GovernmentPaymentOrderLine.monto), 0)
    filas = db.execute(
        select(GovernmentPaymentOrderLine.cause_id, suma)
        .join(GovernmentPaymentOrder, GovernmentPaymentOrder.id == GovernmentPaymentOrderLine.order_id)
        .where(
            GovernmentPaymentOrder.company_id == company_id,
            GovernmentPaymentOrder.estado == "EMITIDA",
            GovernmentPaymentOrderLine.cause_id.in_(pedidos),
        )
        .group_by(GovernmentPaymentOrderLine.cause_id)
    ).all()
    for cause_id, monto in filas:
        resultado[cause_id] = Decimal(monto)
    return resultado


def pendiente_de_ordenar(monto_causado: Decimal, monto_ordenado: Decimal) -> Decimal:
    """Saldo pendiente de ordenar de una obligación causada."""
    return max(monto_causado - monto_ordenado, Decimal("0.00"))


def montos_pagados(db: Session, company_id: str, order_ids: Iterable[str]) -> dict[str, Decimal]:
    """Frontera TRE-04: TRE-04 sustituirá esta proyección; es el único lugar."""
    return {order_id: Decimal("0.00") for order_id in order_ids}


def ordenes_emitidas_de_causa(db: Session, company_id: str, cause_id: str) -> list[GovernmentPaymentOrder]:
    """Órdenes de pago emitidas con al menos una línea sobre la causa indicada."""
    subquery = select(GovernmentPaymentOrderLine.order_id).where(
        GovernmentPaymentOrderLine.cause_id == cause_id
    )
    return list(
        db.scalars(
            select(GovernmentPaymentOrder).where(
                GovernmentPaymentOrder.company_id == company_id,
                GovernmentPaymentOrder.estado == "EMITIDA",
                GovernmentPaymentOrder.id.in_(subquery),
            )
        ).all()
    )
