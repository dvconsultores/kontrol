"""Una entidad **real** por cada tipo vinculable (ARCH-MC-001, fase N9).

`REM-046-001` lo dijo mejor que ningún resumen: *el registro existía; la
capacidad, no*. Diecinueve tipos declarados y una sola vinculación ejercitada.

Esto siembra una fila de verdad, persistida en PostgreSQL, para cada uno de los
veintitrés. No hay identificadores inventados ni modelos simulados: si un tipo
no puede sembrarse, su prueba **falla**, porque un tipo que no se puede crear
tampoco se puede vincular.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session


#: Columnas obligatorias de cada tipo, más allá de la empresa. Se escriben una
#: vez aquí en lugar de repetirse en cada prueba.
def sembrar(db: Session, kind: str, empresa: str, sufijo: str) -> str:
    """Crea una entidad del tipo pedido en esa empresa. Devuelve su id."""
    from app.modules.approvals.models import ApprovalRequest
    from app.modules.homologation.models import HomologationRecord
    from app.modules.inventory.models import InventoryAdjustment, StockCount
    from app.modules.master_data.models import CatalogItem, Party
    from app.modules.organization.models import Installation, Warehouse
    from app.modules.purchasing.models import (
        GoodsReceipt,
        Payment,
        PurchaseOrder,
        PurchaseRequisition,
        SupplierInvoice,
    )
    from app.modules.regulatory.models import (
        OfficialDocument,
        PermitInstance,
        TransportDriver,
        TransportVehicle,
    )
    from app.modules.sales.models import SalesInvoice, SalesOrder, SalesReturn, Shipment
    from app.modules.treasury.models import (
        BankTransaction,
        CashSession,
        FinancialAccount,
        FinancialBank,
        Reconciliation,
    )

    marca = f"N9-{sufijo}"
    ahora = datetime.now(UTC)

    def _party(rol: str) -> str:
        p = Party(company_id=empresa, code=f"{marca}-{rol}", name=f"Tercero {marca}",
                  person_type="JURIDICA", roles=[rol], status="ACTIVE")
        db.add(p)
        db.flush()
        return str(p.id)

    def _item() -> str:
        c = CatalogItem(company_id=empresa, code=f"{marca}-IT", name=f"Artículo {marca}",
                        item_type="PRODUCT", status="ACTIVE")
        db.add(c)
        db.flush()
        return str(c.id)

    def _almacen() -> str:
        w = Warehouse(company_id=empresa, code=f"{marca}-W", name=f"Almacén {marca}",
                      warehouse_type="PHYSICAL", status="ACTIVE")
        db.add(w)
        db.flush()
        return str(w.id)

    def _cuenta() -> str:
        b = FinancialBank(company_id=empresa, code=f"{marca}-B", name=f"Banco {marca}",
                          status="ACTIVE")
        db.add(b)
        db.flush()
        a = FinancialAccount(company_id=empresa, bank_id=str(b.id), code=f"{marca}-CTA",
                             name=f"Cuenta {marca}", currency="VED", status="ACTIVE")
        db.add(a)
        db.flush()
        return str(a.id)

    def _caja() -> str:
        from app.modules.treasury.models import Cashbox

        c = Cashbox(company_id=empresa, code=f"{marca}-CJ", name=f"Caja {marca}",
                    currency="VED", status="ACTIVE")
        db.add(c)
        db.flush()
        return str(c.id)

    def _tipo_permiso() -> str:
        from app.modules.regulatory.models import PermitType, RegulatoryAuthority

        a = RegulatoryAuthority(company_id=empresa, code=f"{marca}-AU",
                                name=f"Autoridad {marca}", status="ACTIVE")
        db.add(a)
        db.flush()
        t = PermitType(company_id=empresa, authority_id=str(a.id), code=f"{marca}-TP",
                       name=f"Tipo {marca}", status="ACTIVE")
        db.add(t)
        db.flush()
        return str(t.id)

    def _orden_compra() -> str:
        o = PurchaseOrder(company_id=empresa, code=f"{marca}-OC",
                          supplier_id=_party("PROVEEDOR"), status="DRAFT")
        db.add(o)
        db.flush()
        return str(o.id)

    def _orden_venta() -> str:
        o = SalesOrder(company_id=empresa, code=f"{marca}-OV",
                       customer_id=_party("CLIENTE"), status="DRAFT")
        db.add(o)
        db.flush()
        return str(o.id)

    creadores = {
        "ApprovalRequest": lambda: ApprovalRequest(
            company_id=empresa, process_type="PURCHASE_ORDER", document_type="PurchaseOrder",
            document_id=str(uuid.uuid4()), fingerprint=marca, status="PENDING"),
        "PurchaseOrder": lambda: PurchaseOrder(
            company_id=empresa, code=f"{marca}-OC2", supplier_id=_party("PROV2"), status="DRAFT"),
        "PurchaseRequisition": lambda: PurchaseRequisition(
            company_id=empresa, code=f"{marca}-RQ", status="DRAFT"),
        "GoodsReceipt": lambda: GoodsReceipt(
            company_id=empresa, code=f"{marca}-RC", order_id=_orden_compra(),
            warehouse_id=_almacen(), status="DRAFT", quality_status="PENDING"),
        "SupplierInvoice": lambda: SupplierInvoice(
            company_id=empresa, supplier_id=_party("PROV3"),
            invoice_number=f"{marca}-FP", status="DRAFT"),
        "Payment": lambda: Payment(
            company_id=empresa, party_id=_party("PROV4"), direction="OUT",
            currency="VED", amount=100.0, applied=0.0, status="DRAFT"),
        "SalesOrder": lambda: SalesOrder(
            company_id=empresa, code=f"{marca}-OV2", customer_id=_party("CLI2"), status="DRAFT"),
        "SalesInvoice": lambda: SalesInvoice(
            company_id=empresa, customer_id=_party("CLI3"), status="DRAFT"),
        "Shipment": lambda: Shipment(
            company_id=empresa, code=f"{marca}-SH", order_id=_orden_venta(),
            origin_warehouse_id=_almacen(), status="DRAFT"),
        "SalesReturn": lambda: SalesReturn(
            company_id=empresa, code=f"{marca}-DV", reason="Prueba N9", status="DRAFT"),
        "InventoryAdjustment": lambda: InventoryAdjustment(
            company_id=empresa, warehouse_id=_almacen(), product_id=_item(),
            quantity=1, reason="Prueba N9", status="DRAFT"),
        "StockCount": lambda: StockCount(
            company_id=empresa, code=f"{marca}-CT", warehouse_id=_almacen(), status="DRAFT"),
        "Party": lambda: Party(
            company_id=empresa, code=f"{marca}-TR", name=f"Tercero {marca}",
            person_type="JURIDICA", roles=["CLIENTE"], status="ACTIVE"),
        "CatalogItem": lambda: CatalogItem(
            company_id=empresa, code=f"{marca}-CI", name=f"Artículo {marca}",
            item_type="PRODUCT", status="ACTIVE"),
        "PermitInstance": lambda: PermitInstance(
            company_id=empresa, number=f"{marca}-PM", permit_type_id=_tipo_permiso(),
            status="DRAFT", hash=marca),
        "OfficialDocument": lambda: OfficialDocument(
            company_id=empresa, kind="SICA", number=f"{marca}-DO", status="DRAFT"),
        "TransportVehicle": lambda: TransportVehicle(
            company_id=empresa, plate=f"{marca[:6]}-{sufijo[:3]}", status="ACTIVE"),
        "TransportDriver": lambda: TransportDriver(
            company_id=empresa, party_id=_party("CONDUCTOR"), status="ACTIVE"),
        "Warehouse": lambda: Warehouse(
            company_id=empresa, code=f"{marca}-W2", name=f"Almacén {marca}",
            warehouse_type="PHYSICAL", status="ACTIVE"),
        "BankTransaction": lambda: BankTransaction(
            company_id=empresa, account_id=_cuenta(), direction="IN", amount=50.0,
            currency="VED", txn_date=ahora.date(), status="PENDING"),
        "CashSession": lambda: CashSession(
            company_id=empresa, cashbox_id=_caja(), status="OPEN"),
        "Reconciliation": lambda: Reconciliation(
            company_id=empresa, account_id=_cuenta(), status="DRAFT"),
        # Sin empresa a propósito: el acto de homologación es de la instalación.
        "HomologationRecord": lambda: HomologationRecord(
            installation_id=str(db.query(Installation).first().id),
            fiscal_version=f"{marca}-1.0"),
    }

    crear = creadores.get(kind)
    if crear is None:
        raise AssertionError(
            f"el tipo «{kind}» está registrado y no tiene semilla: "
            "un tipo que no se puede crear tampoco se puede vincular")
    entidad = crear()
    db.add(entidad)
    db.flush()
    return str(entidad.id)
