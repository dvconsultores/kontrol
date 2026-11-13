"""Autoridad única del suministro abierto por almacén.

Este módulo es la única fuente de verdad para calcular cuántas unidades
de una línea de orden de compra están abiertas (ordenadas y no recibidas)
para un almacén destino. El cálculo es por línea y por lote; los estados
de la orden aplican la semántica de negocio de la Spec 015. Aquí no se
crean movimientos de inventario, recepciones, saldos ni costos.
"""
from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.modules.purchasing.models import PurchaseOrder, PurchaseOrderLine

OPEN_SUPPLY_ORDER_STATUSES = ("APPROVED", "PARTIALLY_RECEIVED")


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
    ordered = func.coalesce(PurchaseOrderLine.base_quantity_ordered, PurchaseOrderLine.quantity_ordered)
    pending = ordered - func.coalesce(PurchaseOrderLine.quantity_received, 0)
    pending_floor = case((pending > 0, pending), else_=0)

    stmt = (
        select(PurchaseOrderLine.product_id, func.sum(pending_floor).label("total_open"))
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderLine.order_id)
        .where(
            PurchaseOrder.company_id == company_id,
            PurchaseOrder.status.in_(OPEN_SUPPLY_ORDER_STATUSES),
            PurchaseOrderLine.destination_warehouse_id == warehouse_id,
            PurchaseOrderLine.needs_inventory.is_(True),
            PurchaseOrderLine.product_id.in_(product_ids_list),
        )
        .group_by(PurchaseOrderLine.product_id)
    )

    result = {str(product_id): Decimal("0") for product_id in product_ids_list}
    for product_id, total_open in db.execute(stmt):
        result[str(product_id)] = Decimal(str(total_open))
    return result
