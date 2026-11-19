"""Proyección neutral de obligaciones del causado (BUD-09) para la orden de pago (TRE-03)."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.government.models import (
    ESTADOS_PAGO_EN_TRAMITE,
    GovernmentPayment,
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
    """Suma por orden de los pagos REGISTRADO del ente (TRE-04). Unica autoridad del monto pagado."""
    pedidos = list(order_ids)
    resultado = {order_id: Decimal("0.00") for order_id in pedidos}
    if not pedidos:
        return resultado
    suma = func.coalesce(func.sum(GovernmentPayment.monto), 0)
    filas = db.execute(
        select(GovernmentPayment.order_id, suma)
        .where(
            GovernmentPayment.company_id == company_id,
            GovernmentPayment.estado == "REGISTRADO",
            GovernmentPayment.order_id.in_(pedidos),
        )
        .group_by(GovernmentPayment.order_id)
    ).all()
    for order_id, monto in filas:
        resultado[order_id] = Decimal(monto)
    return resultado


def montos_en_tramite(db: Session, company_id: str, order_ids: Iterable[str]) -> dict[str, Decimal]:
    """Suma por orden de los pagos del ente que están en trámite de autorización (TRE-04)."""
    pedidos = list(order_ids)
    resultado = {order_id: Decimal("0.00") for order_id in pedidos}
    if not pedidos:
        return resultado
    suma = func.coalesce(func.sum(GovernmentPayment.monto), 0)
    filas = db.execute(
        select(GovernmentPayment.order_id, suma)
        .where(
            GovernmentPayment.company_id == company_id,
            GovernmentPayment.estado.in_(list(ESTADOS_PAGO_EN_TRAMITE)),
            GovernmentPayment.order_id.in_(pedidos),
        )
        .group_by(GovernmentPayment.order_id)
    ).all()
    for order_id, monto in filas:
        resultado[order_id] = Decimal(monto)
    return resultado


def pendiente_de_pagar(monto_ordenado: Decimal, monto_pagado: Decimal) -> Decimal:
    """Saldo pendiente de pago de una orden de pago."""
    return max(monto_ordenado - monto_pagado, Decimal("0.00"))


def disponible_para_pago(monto_ordenado: Decimal, monto_pagado: Decimal, monto_en_tramite: Decimal) -> Decimal:
    """Saldo disponible para preparar nuevos pagos, descontando lo que ya está en trámite."""
    return max(monto_ordenado - monto_pagado - monto_en_tramite, Decimal("0.00"))


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
