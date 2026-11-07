"""Una línea de recepción no puede contradecir a su línea de orden (FR-019-015)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from conftest import seed_org_chain

from app.core.errors import KontrolError, NotFoundError
from app.modules.audit.models import AuditEvent
from app.modules.inventory.models import InventoryBalance, InventoryLot, InventoryMovement, MovementType, ProductSerial
from app.modules.master_data.models import CatalogItem, Party, Presentation
from app.modules.organization.models import Warehouse
from app.modules.purchasing import service as ap_service
from app.modules.purchasing.models import GoodsReceiptLine
from tests.company_seed import EMPRESA_DOS, EMPRESA_UNO

COMPANY = EMPRESA_UNO
OTHER = EMPRESA_DOS


@pytest.fixture()
def db_session(sesion_de_prueba):
    seed_org_chain(sesion_de_prueba, COMPANY, OTHER)
    return sesion_de_prueba


def _party(db, company, code):
    obj = Party(
        company_id=company,
        code=code,
        name="Proveedor SA",
        person_type="JURIDICA",
        tax_id=f"J-1234567-{abs(hash(code)) % 10}",
        roles=["PROVEEDOR"],
        status="ACTIVE",
    )
    db.add(obj)
    db.flush()
    return obj


def _producto(db, company, code):
    obj = CatalogItem(company_id=company, code=code, name="Arroz", item_type="PRODUCT", status="ACTIVE")
    db.add(obj)
    db.flush()
    return obj


def _almacen(db, company, code):
    obj = Warehouse(company_id=company, code=code, name="Principal", status="ACTIVE")
    db.add(obj)
    db.flush()
    return obj


def _movement_type(db):
    obj = MovementType(
        company_id=COMPANY,
        code="ENTRADA_RECEPCION",
        name="Entrada recepción",
        direction="IN",
        affects_balance=True,
        status="ACTIVE",
    )
    db.add(obj)
    db.flush()
    return obj


@pytest.fixture()
def mundo(db_session):
    db = db_session
    _movement_type(db)
    producto_a = _producto(db, COMPANY, "PROD-A")
    producto_b = _producto(db, COMPANY, "PROD-B")
    almacen = _almacen(db, COMPANY, "ALM-1")
    supplier = _party(db, COMPANY, "PROV-1")

    order = ap_service.create_order(db, company_id=COMPANY, code="OC-1", supplier_id=str(supplier.id))
    linea_a = ap_service.add_order_line(
        db, order_id=str(order.id), product_id=str(producto_a.id), quantity_ordered=50.0, unit_price=10.0
    )
    linea_b = ap_service.add_order_line(
        db, order_id=str(order.id), product_id=str(producto_b.id), quantity_ordered=50.0, unit_price=10.0
    )
    ap_service.transition_order(db, order=order, target="SUBMITTED")
    ap_service.transition_order(db, order=order, target="APPROVED")
    recepcion = ap_service.create_receipt(
        db, company_id=COMPANY, code="RC-1", order_id=str(order.id), warehouse_id=str(almacen.id)
    )
    # Cada petición real lee los valores de la base, no los del constructor en memoria
    db.flush()
    db.expire_all()
    return SimpleNamespace(
        producto_a=producto_a,
        producto_b=producto_b,
        almacen=almacen,
        supplier=supplier,
        order=order,
        linea_a=linea_a,
        linea_b=linea_b,
        recepcion=recepcion,
    )


def test_bt01_linea_y_producto_correctos(db_session, mundo):
    db = db_session
    receipt = mundo.recepcion
    ap_service.add_receipt_line(
        db,
        company_id=receipt.company_id,
        receipt_id=str(receipt.id),
        order_line_id=str(mundo.linea_a.id),
        product_id=str(mundo.producto_a.id),
        quantity_received=30.0,
        quantity_accepted=30.0,
        quantity_rejected=0.0,
        lot_number="L-1",
        serials=["S-1"],
        presentation_id=None,
    )
    guardada = db.query(GoodsReceiptLine).filter(GoodsReceiptLine.receipt_id == receipt.id).one()
    assert guardada.product_id == str(mundo.producto_a.id)


def test_bt02_producto_distinto_se_rechaza(db_session, mundo):
    db = db_session
    receipt = mundo.recepcion
    with pytest.raises(KontrolError) as exc:
        ap_service.add_receipt_line(
            db,
            company_id=receipt.company_id,
            receipt_id=str(receipt.id),
            order_line_id=str(mundo.linea_a.id),
            product_id=str(mundo.producto_b.id),
            quantity_received=30.0,
            quantity_accepted=30.0,
            quantity_rejected=0.0,
            lot_number="L-1",
            serials=["S-1"],
            presentation_id=None,
        )
    assert exc.value.code == "RECEIPT_LINE_PRODUCT_MISMATCH"
    assert exc.value.status_code == 422


def test_bt03_linea_de_otra_orden(db_session, mundo):
    db = db_session
    receipt = mundo.recepcion
    supplier = _party(db, COMPANY, "PROV-2")
    producto = _producto(db, COMPANY, "PROD-C")
    otra = ap_service.create_order(db, company_id=COMPANY, code="OC-2", supplier_id=str(supplier.id))
    linea_otra = ap_service.add_order_line(
        db, order_id=str(otra.id), product_id=str(producto.id), quantity_ordered=10.0, unit_price=5.0
    )
    ap_service.transition_order(db, order=otra, target="SUBMITTED")
    ap_service.transition_order(db, order=otra, target="APPROVED")
    with pytest.raises(NotFoundError) as exc:
        ap_service.add_receipt_line(
            db,
            company_id=receipt.company_id,
            receipt_id=str(receipt.id),
            order_line_id=str(linea_otra.id),
            product_id=str(producto.id),
            quantity_received=1.0,
            quantity_accepted=1.0,
            quantity_rejected=0.0,
            lot_number="L-1",
            serials=["S-1"],
            presentation_id=None,
        )
    assert exc.value.code == "PURCHASE_ORDER_LINE_NOT_FOUND"


def test_bt04_linea_de_otra_empresa(db_session, mundo):
    db = db_session
    receipt = mundo.recepcion
    supplier = _party(db, OTHER, "PROV-O")
    producto = _producto(db, OTHER, "PROD-O")
    otra = ap_service.create_order(db, company_id=OTHER, code="OC-O", supplier_id=str(supplier.id))
    linea_otra = ap_service.add_order_line(
        db, order_id=str(otra.id), product_id=str(producto.id), quantity_ordered=10.0, unit_price=5.0
    )
    with pytest.raises(NotFoundError) as exc:
        ap_service.add_receipt_line(
            db,
            company_id=receipt.company_id,
            receipt_id=str(receipt.id),
            order_line_id=str(linea_otra.id),
            product_id=str(mundo.producto_a.id),
            quantity_received=1.0,
            quantity_accepted=1.0,
            quantity_rejected=0.0,
            lot_number="L-1",
            serials=["S-1"],
            presentation_id=None,
        )
    assert exc.value.code == "PURCHASE_ORDER_LINE_NOT_FOUND"


def test_bt05_linea_inexistente(db_session, mundo):
    db = db_session
    receipt = mundo.recepcion
    with pytest.raises(NotFoundError) as exc:
        ap_service.add_receipt_line(
            db,
            company_id=receipt.company_id,
            receipt_id=str(receipt.id),
            order_line_id="00000000-0000-0000-0000-000000000099",
            product_id=str(mundo.producto_a.id),
            quantity_received=1.0,
            quantity_accepted=1.0,
            quantity_rejected=0.0,
            lot_number="L-1",
            serials=["S-1"],
            presentation_id=None,
        )
    assert exc.value.code == "PURCHASE_ORDER_LINE_NOT_FOUND"


def test_bt06_a_bt09_y_bt12_rechazo_sin_efectos(db_session, mundo):
    db = db_session
    receipt = mundo.recepcion
    with pytest.raises(KontrolError):
        ap_service.add_receipt_line(
            db,
            company_id=receipt.company_id,
            receipt_id=str(receipt.id),
            order_line_id=str(mundo.linea_a.id),
            product_id=str(mundo.producto_b.id),
            quantity_received=30.0,
            quantity_accepted=30.0,
            quantity_rejected=0.0,
            lot_number="L-X",
            serials=["S-X"],
            presentation_id=None,
        )
    assert db.query(GoodsReceiptLine).filter(GoodsReceiptLine.receipt_id == receipt.id).count() == 0
    assert (
        db.query(InventoryMovement)
        .filter(InventoryMovement.product_id == str(mundo.producto_b.id))
        .count()
        == 0
    )
    assert (
        db.query(InventoryLot).filter(InventoryLot.product_id == str(mundo.producto_b.id)).count() == 0
    )
    assert (
        db.query(ProductSerial).filter(ProductSerial.product_id == str(mundo.producto_b.id)).count() == 0
    )
    assert (
        db.query(AuditEvent)
        .filter(AuditEvent.company_id == COMPANY, AuditEvent.action == "RECEIPT_LINE_ADDED")
        .count()
        == 0
    )


def test_bt10_rechazo_no_acumula_recibido(db_session, mundo):
    db = db_session
    receipt = mundo.recepcion
    with pytest.raises(KontrolError):
        ap_service.add_receipt_line(
            db,
            company_id=receipt.company_id,
            receipt_id=str(receipt.id),
            order_line_id=str(mundo.linea_a.id),
            product_id=str(mundo.producto_b.id),
            quantity_received=30.0,
            quantity_accepted=30.0,
            quantity_rejected=0.0,
            lot_number="L-1",
            serials=["S-1"],
            presentation_id=None,
        )
    ap_service.add_receipt_line(
        db,
        company_id=receipt.company_id,
        receipt_id=str(receipt.id),
        order_line_id=str(mundo.linea_a.id),
        product_id=str(mundo.producto_a.id),
        quantity_received=10.0,
        quantity_accepted=10.0,
        quantity_rejected=0.0,
        lot_number="L-1",
        serials=["S-1"],
        presentation_id=None,
    )
    ap_service.confirm_receipt(db, receipt=receipt)
    ap_service.enviar_a_calidad(db, receipt=receipt)
    receipt.quality_status = "APPROVED"
    db.flush()
    ap_service.accept_receipt(db, receipt=receipt)
    db.refresh(mundo.linea_a)
    db.refresh(mundo.linea_b)
    assert mundo.linea_a.quantity_received == 10
    assert mundo.linea_b.quantity_received == 0


def test_bt11_flujo_correcto_mete_inventario_del_producto_de_la_linea(db_session, mundo):
    db = db_session
    receipt = mundo.recepcion
    ap_service.add_receipt_line(
        db,
        company_id=receipt.company_id,
        receipt_id=str(receipt.id),
        order_line_id=str(mundo.linea_b.id),
        product_id=str(mundo.producto_b.id),
        quantity_received=7.0,
        quantity_accepted=7.0,
        quantity_rejected=0.0,
        lot_number="L-7",
        serials=["S-7"],
        presentation_id=None,
    )
    ap_service.confirm_receipt(db, receipt=receipt)
    ap_service.enviar_a_calidad(db, receipt=receipt)
    receipt.quality_status = "APPROVED"
    db.flush()
    ap_service.accept_receipt(db, receipt=receipt)
    assert (
        db.query(InventoryMovement)
        .filter(InventoryMovement.product_id == str(mundo.producto_b.id))
        .count()
        == 1
    )
    assert (
        db.query(InventoryMovement)
        .filter(InventoryMovement.product_id == str(mundo.producto_a.id))
        .count()
        == 0
    )
    assert (
        db.query(InventoryBalance)
        .filter(InventoryBalance.product_id == str(mundo.producto_b.id))
        .count()
        == 1
    )
    assert (
        db.query(InventoryBalance)
        .filter(InventoryBalance.product_id == str(mundo.producto_a.id))
        .count()
        == 0
    )


def test_presentacion_de_otro_producto_se_rechaza(db_session, mundo):
    db = db_session
    receipt = mundo.recepcion
    presentacion = Presentation(
        company_id=COMPANY,
        product_id=str(mundo.producto_b.id),
        code="CAJA",
        name="Caja",
        status="ACTIVE",
    )
    db.add(presentacion)
    db.flush()
    with pytest.raises(KontrolError) as exc:
        ap_service.add_receipt_line(
            db,
            company_id=receipt.company_id,
            receipt_id=str(receipt.id),
            order_line_id=str(mundo.linea_a.id),
            product_id=str(mundo.producto_a.id),
            quantity_received=1.0,
            quantity_accepted=1.0,
            quantity_rejected=0.0,
            lot_number="L-1",
            serials=["S-1"],
            presentation_id=str(presentacion.id),
        )
    assert exc.value.code == "CONVERSION_NOT_RESOLVABLE"


def test_producto_de_otra_empresa_sigue_sin_existir(db_session, mundo):
    db = db_session
    receipt = mundo.recepcion
    producto_otro = _producto(db, OTHER, "PROD-X")
    with pytest.raises(NotFoundError):
        ap_service.add_receipt_line(
            db,
            company_id=receipt.company_id,
            receipt_id=str(receipt.id),
            order_line_id=str(mundo.linea_a.id),
            product_id=str(producto_otro.id),
            quantity_received=1.0,
            quantity_accepted=1.0,
            quantity_rejected=0.0,
            lot_number="L-1",
            serials=["S-1"],
            presentation_id=None,
        )
