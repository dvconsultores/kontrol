"""Registro de tipos de recurso vinculables (Spec 046, F4).

Un `resource_type` de texto libre admite cualquier cosa y hace **imposible**
autorizar: sin saber sobre qué entidad se decide el acceso, no hay decisión que
tomar. Este registro declara, para cada tipo admitido, el modelo, la columna de
empresa y el permiso requerido.

No es dato de negocio: es el mapa de integridad entre 046 y sus consumidores.
Añadir un consumidor es una entrada aquí, no una tabla nueva (FR-046-022).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import KontrolError


@dataclass(frozen=True)
class ResourceKind:
    """Un tipo de entidad al que puede vincularse un documento."""

    resource_type: str
    module: str
    model: str
    company_attr: str
    permission: str
    #: Specs que lo consumen. Documental: hace visible para quién existe.
    consumers: tuple[str, ...] = ()


#: Registro **cerrado**. Un tipo ausente se rechaza.
RESOURCE_KINDS: dict[str, ResourceKind] = {
    k.resource_type: k for k in (
        ResourceKind("ApprovalRequest", "app.modules.approvals.models",
                     "ApprovalRequest", "company_id", "aprobaciones:view", ("045",)),
        ResourceKind("PurchaseOrder", "app.modules.purchasing.models",
                     "PurchaseOrder", "company_id", "compras:view", ("017", "018")),
        ResourceKind("GoodsReceipt", "app.modules.purchasing.models",
                     "GoodsReceipt", "company_id", "compras:view", ("019", "020")),
        ResourceKind("ReceiptIncident", "app.modules.purchasing.models",
                     "ReceiptIncident", "company_id", "compras:view", ("020",)),
        ResourceKind("SupplierInvoice", "app.modules.purchasing.models",
                     "SupplierInvoice", "company_id", "compras:view", ("027",)),
        ResourceKind("PurchaseRequisition", "app.modules.purchasing.models",
                     "PurchaseRequisition", "company_id", "compras:view", ("015",)),
        ResourceKind("SalesOrder", "app.modules.sales.models",
                     "SalesOrder", "company_id", "ventas:view", ("029",)),
        ResourceKind("SalesInvoice", "app.modules.sales.models",
                     "SalesInvoice", "company_id", "ventas:view", ("034",)),
        ResourceKind("Shipment", "app.modules.sales.models",
                     "Shipment", "company_id", "ventas:view", ("035",)),
        ResourceKind("SalesReturn", "app.modules.sales.models",
                     "SalesReturn", "company_id", "ventas:view", ("036",)),
        ResourceKind("PermitInstance", "app.modules.regulatory.models",
                     "PermitInstance", "company_id", "regulatorio:view", ("044",)),
        ResourceKind("OfficialDocument", "app.modules.regulatory.models",
                     "OfficialDocument", "company_id", "regulatorio:view", ("044",)),
        ResourceKind("InventoryAdjustment", "app.modules.inventory.models",
                     "InventoryAdjustment", "company_id", "inventario:view", ("025",)),
        ResourceKind("StockCount", "app.modules.inventory.models",
                     "StockCount", "company_id", "inventario:view", ("025",)),
        ResourceKind("Party", "app.modules.master_data.models",
                     "Party", "company_id", "maestros:view", ("012",)),
        ResourceKind("CatalogItem", "app.modules.master_data.models",
                     "CatalogItem", "company_id", "maestros:view", ("010",)),
        ResourceKind("TransportVehicle", "app.modules.regulatory.models",
                     "TransportVehicle", "company_id", "regulatorio:view", ("035",)),
        ResourceKind("TransportDriver", "app.modules.regulatory.models",
                     "TransportDriver", "company_id", "regulatorio:view", ("035",)),
        # Sin `company_id`: el acto de homologación es de la instalación, no de
        # una empresa. El control se apoya entonces solo en el permiso.
        ResourceKind("HomologationRecord", "app.modules.homologation.models",
                     "HomologationRecord", "company_id", "homologacion:view", ("051",)),
        ResourceKind("Warehouse", "app.modules.organization.models",
                     "Warehouse", "company_id", "organization:view", ("008",)),
        # Las cuatro que `REM-046-001` identificó como existentes y ausentes.
        # Verificadas contra el modelo vigente, no contra el informe: las cuatro
        # tienen clave primaria `id` y `company_id` con referencia real.
        ResourceKind("Payment", "app.modules.purchasing.models",
                     "Payment", "company_id", "compras:view", ("028",)),
        ResourceKind("BankTransaction", "app.modules.treasury.models",
                     "BankTransaction", "company_id", "tesoreria:view", ("038",)),
        ResourceKind("CashSession", "app.modules.treasury.models",
                     "CashSession", "company_id", "tesoreria:view", ("038",)),
        ResourceKind("Reconciliation", "app.modules.treasury.models",
                     "Reconciliation", "company_id", "tesoreria:view", ("038",)),
    )
}


def get_kind(resource_type: str) -> ResourceKind:
    """Devuelve el tipo, o rechaza. **No hay texto libre.**"""
    kind = RESOURCE_KINDS.get(resource_type)
    if kind is None:
        raise KontrolError(
            code="RESOURCE_TYPE_UNKNOWN",
            message=f"El tipo de recurso «{resource_type}» no está registrado",
            status_code=422,
            details={"allowed": sorted(RESOURCE_KINDS)})
    return kind


def _load_model(kind: ResourceKind) -> Any:
    module = __import__(kind.module, fromlist=[kind.model])
    return getattr(module, kind.model)


def resolve_resource(db: Session, resource_type: str, resource_id: str) -> tuple[Any, str | None]:
    """Carga la entidad y devuelve `(entidad, company_id)`.

    Que la entidad exista se comprueba de verdad: un vínculo a un recurso
    inexistente sería un vínculo huérfano desde el primer día (FR-046-040).
    """
    kind = get_kind(resource_type)
    model = _load_model(kind)
    entity = db.get(model, resource_id)
    if entity is None:
        raise KontrolError(code="RESOURCE_NOT_FOUND",
                           message="El recurso indicado no existe", status_code=404)
    return entity, getattr(entity, kind.company_attr, None)


def required_permission(resource_type: str) -> str:
    return get_kind(resource_type).permission
