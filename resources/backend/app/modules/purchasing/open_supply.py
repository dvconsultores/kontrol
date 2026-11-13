"""Autoridad única del suministro abierto y recibido sin confirmar por almacén.

Este módulo es la única fuente de verdad para calcular cuántas unidades
de una línea de orden de compra están abiertas (ordenadas y no recibidas)
para un almacén destino, y cuántas unidades aceptadas en recepciones
permanecen pendientes de confirmación de inventario. El cálculo es por
línea y por lote; los estados de la orden y de la recepción aplican la
semántica de negocio de las Spec 015 y 021. Aquí no se crean movimientos
de inventario, recepciones, saldos ni costos.
"""
from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import NamedTuple

from sqlalchemy import Numeric, case, func, literal, select, union_all
from sqlalchemy.orm import Session

from app.modules.purchasing.models import (
    CONFIRMATION_PENDING,
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
)

OPEN_SUPPLY_ORDER_STATUSES = ("APPROVED", "PARTIALLY_RECEIVED")
RECEIVED_UNCONFIRMED_RECEIPT_STATUSES = ("ACCEPTED", "PARTIALLY_ACCEPTED")


class EnCamino(NamedTuple):
    open_supply: Decimal
    received_unconfirmed: Decimal


def cantidad_abierta(line: PurchaseOrderLine, order_status: str) -> Decimal:
    """Cantidad abierta de una línea para una orden en un estado dado."""
    if order_status not in OPEN_SUPPLY_ORDER_STATUSES:
        return Decimal("0")
    if not line.needs_inventory or line.destination_warehouse_id is None:
        return Decimal("0")

    ordered = Decimal(str(line.base_quantity_ordered if line.base_quantity_ordered is not None else line.quantity_ordered))
    received = Decimal(str(line.quantity_received or 0))
    pending = ordered - received
    return max(Decimal("0"), pending)


def _select_abierto(company_id: str, warehouse_id: str, product_ids: Sequence[str]):
    """Sentencia del suministro abierto agregado por producto."""
    ordered = func.coalesce(PurchaseOrderLine.base_quantity_ordered, PurchaseOrderLine.quantity_ordered)
    pending = ordered - func.coalesce(PurchaseOrderLine.quantity_received, 0)
    pending_floor = case((pending > 0, pending), else_=0)

    return (
        select(PurchaseOrderLine.product_id, func.sum(pending_floor).label("total"))
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderLine.order_id)
        .where(
            PurchaseOrder.company_id == company_id,
            PurchaseOrder.status.in_(OPEN_SUPPLY_ORDER_STATUSES),
            PurchaseOrderLine.destination_warehouse_id == warehouse_id,
            PurchaseOrderLine.needs_inventory.is_(True),
            PurchaseOrderLine.product_id.in_(list(product_ids)),
        )
        .group_by(PurchaseOrderLine.product_id)
    )


def _select_sin_confirmar(company_id: str, warehouse_id: str, product_ids: Sequence[str]):
    """Sentencia de lo aceptado y pendiente de confirmar por producto."""
    accepted = func.coalesce(
        GoodsReceiptLine.base_quantity_accepted,
        GoodsReceiptLine.quantity_accepted,
    )

    return (
        select(GoodsReceiptLine.product_id, func.sum(accepted).label("total"))
        .join(GoodsReceipt, GoodsReceipt.id == GoodsReceiptLine.receipt_id)
        .join(PurchaseOrderLine, PurchaseOrderLine.id == GoodsReceiptLine.order_line_id)
        .where(
            GoodsReceipt.company_id == company_id,
            GoodsReceipt.warehouse_id == warehouse_id,
            GoodsReceipt.status.in_(RECEIVED_UNCONFIRMED_RECEIPT_STATUSES),
            GoodsReceipt.confirmation_status == CONFIRMATION_PENDING,
            GoodsReceiptLine.quantity_accepted > 0,
            PurchaseOrderLine.needs_inventory.is_(True),
            GoodsReceiptLine.product_id.in_(list(product_ids)),
        )
        .group_by(GoodsReceiptLine.product_id)
    )


def suministro_abierto(
    db: Session,
    *,
    company_id: str,
    warehouse_id: str,
    product_ids: Sequence[str],
) -> dict[str, Decimal]:
    """Suministro abierto agregado por producto para un almacén destino."""
    if not product_ids:
        return {}

    product_ids_list = list(product_ids)
    result = {str(product_id): Decimal("0") for product_id in product_ids_list}
    for product_id, total_open in db.execute(
        _select_abierto(company_id, warehouse_id, product_ids_list)
    ):
        result[str(product_id)] = Decimal(str(total_open))
    return result


def recibido_sin_confirmar(
    db: Session,
    *,
    company_id: str,
    warehouse_id: str,
    product_ids: Sequence[str],
) -> dict[str, Decimal]:
    """Aceptado en recepciones cuya confirmación de inventario está pendiente."""
    if not product_ids:
        return {}

    product_ids_list = list(product_ids)
    result = {str(product_id): Decimal("0") for product_id in product_ids_list}
    for product_id, total in db.execute(
        _select_sin_confirmar(company_id, warehouse_id, product_ids_list)
    ):
        result[str(product_id)] = Decimal(str(total))
    return result


def en_camino(
    db: Session,
    *,
    company_id: str,
    warehouse_id: str,
    product_ids: Sequence[str],
) -> dict[str, EnCamino]:
    """Abierto y recibido sin confirmar en una única sentencia (UNION ALL)."""
    if not product_ids:
        return {}

    product_ids_list = list(product_ids)
    zero = literal(0, Numeric(18, 6))
    abierto = _select_abierto(company_id, warehouse_id, product_ids_list).subquery()
    sin_confirmar = _select_sin_confirmar(company_id, warehouse_id, product_ids_list).subquery()
    union = union_all(
        select(abierto.c.product_id.label("product_id"), abierto.c.total.label("total_abierto"), zero.label("total_sin_confirmar")),
        select(sin_confirmar.c.product_id.label("product_id"), zero.label("total_abierto"), sin_confirmar.c.total.label("total_sin_confirmar")),
    ).subquery()
    stmt = select(union.c.product_id, func.sum(union.c.total_abierto), func.sum(union.c.total_sin_confirmar)).group_by(union.c.product_id)

    result = {
        str(product_id): EnCamino(Decimal("0"), Decimal("0"))
        for product_id in product_ids_list
    }
    for product_id, total_abierto, total_sin_confirmar in db.execute(stmt):
        result[str(product_id)] = EnCamino(
            Decimal(str(total_abierto)),
            Decimal(str(total_sin_confirmar)),
        )
    return result
