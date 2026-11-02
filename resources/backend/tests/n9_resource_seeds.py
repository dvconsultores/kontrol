"""Una entidad **real** por cada tipo vinculable (ARCH-MC-001, fase N9).

`REM-046-001` lo dijo mejor que ningún resumen: *el registro existía; la
capacidad, no*. Diecinueve tipos declarados y una sola vinculación ejercitada.

Esto siembra una fila de verdad, persistida en PostgreSQL, para cada uno de los
veinticuatro. No hay identificadores inventados ni modelos simulados: si un tipo
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
    from app.modules.government.models import GovernmentAct, GovernmentEntity, GovernmentNotification, GovernmentPosition, GovernmentStructure, GovernmentUnit
    from app.modules.homologation.models import HomologationRecord
    from app.modules.inventory.models import InventoryAdjustment, StockCount
    from app.modules.master_data.models import CatalogItem, Party
    from app.modules.organization.models import Installation, Warehouse
    from app.modules.purchasing.models import (
        GoodsReceipt,
        Payment,
        PurchaseOrder,
        PurchaseRequisition,
        ReceiptIncident,
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

    def _ente_de_empresa() -> str:
        existente = db.query(GovernmentEntity).filter(GovernmentEntity.company_id == empresa).first()
        if existente is not None:
            return str(existente.id)
        ente = GovernmentEntity(company_id=empresa, denominacion=f"Ente {marca}", status="BORRADOR", version=1)
        db.add(ente)
        db.flush()
        return str(ente.id)

    def _cargo_de_empresa(prefijo: str = "") -> GovernmentPosition:
        estructura = db.query(GovernmentStructure).filter(
            GovernmentStructure.company_id == empresa, GovernmentStructure.exercise == 2031).first()
        if estructura is None:
            estructura = GovernmentStructure(company_id=empresa, entity_id=_ente_de_empresa(), exercise=2031,
                                             status="BORRADOR", version=1)
            db.add(estructura)
            db.flush()
        inicio = datetime(2031, 1, 1, tzinfo=UTC).date()
        unidad = GovernmentUnit(structure_id=str(estructura.id), company_id=empresa, code=f"U{prefijo}-{sufijo[:20]}",
                                name=f"Unidad {marca}", unit_type="ORGANO", status="ACTIVA", valid_from=inicio, version=1)
        db.add(unidad)
        db.flush()
        return GovernmentPosition(structure_id=str(estructura.id), company_id=empresa, unit_id=str(unidad.id),
                                  code=f"C{prefijo}-{sufijo[:20]}", name=f"Cargo {marca}", status="BORRADOR",
                                  valid_from=inicio, version=1)

    def _acto_de_empresa(prefijo: str = "A") -> GovernmentAct:
        cargo = _cargo_de_empresa(prefijo)
        db.add(cargo)
        db.flush()
        return GovernmentAct(company_id=empresa, tipo="RESOLUCION", numero=f"A-{sufijo[:20]}",
                             numero_clave=f"A-{sufijo[:20]}".upper(),
                             fecha=datetime(2031, 1, 1, tzinfo=UTC).date(), lugar="Caracas",
                             cargo_id=str(cargo.id), competencia_accion="APROBAR",
                             competencia_materia="CONTRATACIONES",
                             fundamento_competencia="Reglamento interno de prueba",
                             funcionario="Funcionario de prueba", titularidad="TITULAR",
                             caracter="INTERNO", asunto=f"Acto {marca}", status="BORRADOR", version=1)

    def _notificacion_de_empresa() -> GovernmentNotification:
        acto = _acto_de_empresa("N")
        db.add(acto)
        db.flush()
        return GovernmentNotification(company_id=empresa, act_id=str(acto.id), tipo_persona="NATURAL",
                                      nombre=f"Destinatario {marca}", identificacion="V-1234567",
                                      identificacion_clave="V1234567", domicilio="Domicilio de prueba",
                                      recursos="No proceden recursos", status="PENDIENTE", version=1)

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

    def _recepcion() -> str:
        r = GoodsReceipt(company_id=empresa, code=f"{marca}-RC2", order_id=_orden_compra(),
                         warehouse_id=_almacen(), status="DRAFT", quality_status="PENDING")
        db.add(r)
        db.flush()
        return str(r.id)

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
        # Sin línea y sin cantidad **a propósito**: `DIFERENCIA_DOCUMENTAL` es el
        # único tipo que `ck_receipt_incidents_line_and_quantity_by_type` exige
        # así. Es una incidencia real de la 020, no una fila mínima inventada
        # para que la prueba pase.
        "ReceiptIncident": lambda: ReceiptIncident(
            company_id=empresa, code=f"{marca}-IN", receipt_id=_recepcion(),
            incident_type="DIFERENCIA_DOCUMENTAL", status="REGISTRADA",
            description=f"Diferencia documental {marca}"),
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
        "GovernmentEntity": lambda: db.query(GovernmentEntity).filter(
            GovernmentEntity.company_id == empresa).first() or GovernmentEntity(
            company_id=empresa, denominacion=f"Ente {marca}", status="BORRADOR", version=1),
        "GovernmentStructure": lambda: GovernmentStructure(
            company_id=empresa, entity_id=_ente_de_empresa(), exercise=2030, status="BORRADOR", version=1),
        "GovernmentPosition": _cargo_de_empresa,
        "GovernmentAct": _acto_de_empresa,
        "GovernmentNotification": _notificacion_de_empresa,
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
