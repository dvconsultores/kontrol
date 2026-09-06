"""Spec 034 · liberación y facturación.

Lo que estas pruebas defienden es la compuerta y la procedencia. La compuerta:
sin confirmación independiente vigente no hay solicitud, sin solicitud no hay
factura, y un pedido no se factura dos veces. La procedencia: todo lo comercial
sale de las líneas del pedido —precio, descuento, presentación, factor— y toda
la numeración de la Spec 042, que la asigna atómicamente.

Multiempresa sobre PostgreSQL real, con el arnés `mundo`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import ConflictError, NotFoundError
from app.modules.fiscal import service as fiscal
from app.modules.fiscal.models import FiscalDocument
from app.modules.inventory import service as inv
from app.modules.inventory.models import InventoryBalance, InventoryMovement
from app.modules.organization.models import WarehouseLocation
from app.modules.sales import service as sales
from app.modules.sales.models import PickList, SalesInvoice, SalesOrder, SalesOrderLine

pytest_plugins = ("tests.conftest_multicompany",)


# --------------------------------------------------------------------------- #
# Un pedido confirmado, y el motor fiscal listo para emitir
# --------------------------------------------------------------------------- #
def _producto(db, company_id, marca) -> str:
    from app.modules.master_data.models import CatalogItem

    item = CatalogItem(company_id=company_id, code=f"PF-{marca}", name=f"Artículo {marca}",
                       item_type="PRODUCT", status="ACTIVE")
    db.add(item)
    db.flush()
    return str(item.id)


def _ubicacion(db, company_id, warehouse_id, code, *, sequence=1) -> str:
    loc = WarehouseLocation(company_id=company_id, warehouse_id=warehouse_id, code=code,
                            name=f"Ubicación {code}", sequence=sequence, status="ACTIVE")
    db.add(loc)
    db.flush()
    return str(loc.id)


def _pedido_confirmado(db, mundo, *, requerido=10, precio="25.00", tax_ref=None,
                       quantity=None, factor=None):
    """Toda la cadena: existencia, pedido, plan, recogida, consolidación y control."""
    marca = uuid4().hex[:8]
    prod = _producto(db, mundo.company_a, marca)
    l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"F1-{marca}", sequence=1)
    area = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"FC-{marca}", sequence=99)
    tipo = inv._get_movement_type_by_code(db, mundo.company_a, "ENTRADA_RECEPCION")
    inv.record_movement(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                        product_id=prod, movement_type_id=str(tipo.id),
                        quantity=requerido + 20, actor="qa")
    inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                product_id=prod, target_location_id=l1, quantity=requerido + 20, actor="qa")

    from app.modules.master_data.models import Party

    p = Party(company_id=mundo.company_a, code=f"CLF-{marca}", name=f"Cliente {marca}",
              roles=["CLIENTE"])
    db.add(p)
    db.flush()
    ahora = datetime.now(UTC)
    ped = SalesOrder(company_id=mundo.company_a, code=f"OVF-{marca}", customer_id=str(p.id),
                     warehouse_id=mundo.warehouse_a, currency="VED", status="RELEASED",
                     submitted_at=ahora, released_at=ahora)
    db.add(ped)
    db.flush()
    ln = SalesOrderLine(order_id=str(ped.id), product_id=prod,
                        quantity=Decimal(str(quantity if quantity is not None else requerido)),
                        unit_price=Decimal(precio), needs_inventory=True, tax_ref=tax_ref,
                        conversion_factor_snapshot=Decimal(str(factor)) if factor else None,
                        base_quantity=Decimal(str(requerido)))
    db.add(ln)
    db.flush()
    inv.reserve(db, company_id=mundo.company_a, source_document=ped.code, product_id=prod,
                warehouse_id=mundo.warehouse_a, quantity=float(ln.quantity),
                source_type="SALES_ORDER", source_order_id=str(ped.id), source_line_id=str(ln.id),
                base_quantity=Decimal(str(requerido)), actor="qa")
    db.flush()

    plan = PickList(company_id=mundo.company_a, code=f"PLF-{marca}", order_id=str(ped.id),
                    warehouse_id=mundo.warehouse_a, status="DRAFT")
    db.add(plan)
    db.flush()
    sales.allocate(db, company_id=mundo.company_a, plan_id=str(plan.id),
                   order_line_id=str(ln.id), location_id=l1, quantity=requerido, actor="qa")
    sales.confirm_plan(db, company_id=mundo.company_a, plan_id=str(plan.id), actor="planificador")
    parada = next(x for x in sales._lineas_del_plan(db, plan) if x.location_id)
    sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(plan.id),
                       line_id=str(parada.id), quantity=requerido, actor="almacenista")
    sales.consolidate(db, company_id=mundo.company_a, plan_id=str(plan.id),
                      location_id=area, actor="almacenista")
    sales.confirm_order(db, company_id=mundo.company_a, order_id=str(ped.id),
                        lines=[{"order_line_id": str(ln.id),
                                "checked_base_quantity": requerido}], actor="verificador")
    db.commit()
    return {"prod": prod, "pedido": ped, "linea": ln, "plan": plan}


def _fiscal_listo(db, mundo, *, tax_code=None, rate=16.0):
    """Regla de impuesto vigente, serie de numeración y lote de control."""
    marca = uuid4().hex[:6]
    tax_code = tax_code or f"IVA_{marca.upper()}"
    fuente = fiscal.create_legal_source(db, authority="SENIAT", source_type="LEY",
                                        number=f"L-{marca}", effective_from=date(2020, 1, 1))
    fiscal.activate_legal_source(db, source_id=str(fuente.id))
    regla = fiscal.create_tax_rule(db, tax_code=tax_code, legal_source_id=str(fuente.id),
                                   effective_from=date(2020, 1, 1), rate=rate)
    fiscal.approve_tax_rule(db, rule_id=str(regla.id), approver="fiscal")
    serie = fiscal.create_number_series(db, company_id=mundo.company_a, document_type="INVOICE",
                                        prefix="A")
    lote = fiscal.create_control_batch(db, company_id=mundo.company_a,
                                       range_from="1000", range_to="1099")
    db.commit()
    return {"series": str(serie.id), "batch": str(lote.id), "tax_code": tax_code}


def _emitir(db, mundo, e, f):
    sales.request_billing(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                          actor="verificador")
    inv_doc = sales.generate_invoice(db, company_id=mundo.company_a,
                                     order_id=str(e["pedido"].id), actor="facturador")
    db.commit()
    emitida = sales.issue_invoice(db, company_id=mundo.company_a, invoice_id=str(inv_doc.id),
                                  series_id=f["series"], batch_id=f["batch"], actor="facturador")
    db.commit()
    return emitida


# =========================================================================== #
# La compuerta
# =========================================================================== #
def test_no_se_solicita_facturacion_de_un_pedido_sin_confirmar(mundo):
    """¶89: «Facturación factura sobre un pedido previamente confirmado»."""
    db = mundo.factory()
    try:
        marca = uuid4().hex[:8]
        from app.modules.master_data.models import Party

        p = Party(company_id=mundo.company_a, code=f"CX-{marca}", name="Cliente", roles=["CLIENTE"])
        db.add(p)
        db.flush()
        ped = SalesOrder(company_id=mundo.company_a, code=f"OVX-{marca}", customer_id=str(p.id),
                         warehouse_id=mundo.warehouse_a, currency="VED", status="RELEASED")
        db.add(ped)
        db.commit()
        with pytest.raises(ConflictError) as exc:
            sales.request_billing(db, company_id=mundo.company_a, order_id=str(ped.id), actor="qa")
        assert exc.value.code == "BILLING_ORDER_NOT_CONFIRMED"
    finally:
        db.close()


def test_no_se_genera_factura_sin_solicitud(mundo):
    """¶84 y ¶92: la solicitud precede a la factura."""
    db = mundo.factory()
    try:
        e = _pedido_confirmado(db, mundo)
        with pytest.raises(ConflictError) as exc:
            sales.generate_invoice(db, company_id=mundo.company_a,
                                   order_id=str(e["pedido"].id), actor="facturador")
        assert exc.value.code == "BILLING_NOT_REQUESTED"
    finally:
        db.close()


def test_la_solicitud_deja_quien_y_cuando(mundo):
    """`B-060`: «solicitud de facturación explícita». Con autor, o no es explícita."""
    db = mundo.factory()
    try:
        e = _pedido_confirmado(db, mundo)
        sales.request_billing(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                              actor="verificador")
        db.commit()
        ped = db.get(SalesOrder, str(e["pedido"].id))
        assert ped.status == "READY_FOR_BILLING"
        assert ped.billing_requested_by == "verificador"
        assert ped.billing_requested_at is not None
    finally:
        db.close()


def test_un_pedido_no_se_factura_dos_veces(mundo):
    """`B-007`: «no se puede facturar dos veces la misma orden»."""
    db = mundo.factory()
    try:
        e = _pedido_confirmado(db, mundo)
        sales.request_billing(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                              actor="verificador")
        sales.generate_invoice(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                               actor="facturador")
        db.commit()
        with pytest.raises(ConflictError) as exc:
            sales.generate_invoice(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                                   actor="facturador")
        assert exc.value.code == "ORDER_ALREADY_INVOICED"
        db.rollback()
        assert db.execute(select(func.count(SalesInvoice.id)).where(
            SalesInvoice.order_id == str(e["pedido"].id))).scalar() == 1
    finally:
        db.close()


# =========================================================================== #
# La procedencia comercial
# =========================================================================== #
def test_la_factura_sale_del_pedido_y_queda_atada_a_el(mundo):
    """¶96: «Asocia la factura al pedido». Y el precio es el congelado."""
    db = mundo.factory()
    try:
        e = _pedido_confirmado(db, mundo, requerido=10, precio="25.00")
        sales.request_billing(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                              actor="verificador")
        factura = sales.generate_invoice(db, company_id=mundo.company_a,
                                         order_id=str(e["pedido"].id), actor="facturador")
        db.commit()
        d = sales.billing_invoice_dict(db, factura)
        assert d["order_id"] == str(e["pedido"].id)
        assert d["confirmation_id"] is not None, "la factura no dice sobre qué control se emitió"
        assert Decimal(d["lines"][0]["unit_price"]) == Decimal("25.00")
        assert Decimal(d["base_fiscal"]) == Decimal("250.00")
    finally:
        db.close()


def test_el_maestro_de_hoy_no_reescribe_una_venta_cerrada(mundo):
    """Cambiar el precio del artículo después no cambia la factura."""
    db = mundo.factory()
    try:
        from app.modules.master_data.models import CatalogItem

        e = _pedido_confirmado(db, mundo, requerido=4, precio="30.00")
        item = db.get(CatalogItem, e["prod"])
        item.name = "Nombre cambiado después de vender"
        db.commit()
        sales.request_billing(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                              actor="verificador")
        factura = sales.generate_invoice(db, company_id=mundo.company_a,
                                         order_id=str(e["pedido"].id), actor="facturador")
        db.commit()
        assert Decimal(sales.billing_invoice_dict(db, factura)["lines"][0]["unit_price"]) == Decimal("30.00")
    finally:
        db.close()


def test_la_caja_de_doce_se_factura_como_dos_cajas_de_veinticuatro_unidades(mundo):
    """P0: la factura conserva la cantidad comercial **y** la base."""
    db = mundo.factory()
    try:
        e = _pedido_confirmado(db, mundo, requerido=24, quantity=2, factor=12, precio="100.00")
        sales.request_billing(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                              actor="verificador")
        factura = sales.generate_invoice(db, company_id=mundo.company_a,
                                         order_id=str(e["pedido"].id), actor="facturador")
        db.commit()
        linea = sales.billing_invoice_dict(db, factura)["lines"][0]
        assert Decimal(linea["quantity"]) == Decimal("2"), "se facturaron unidades como cajas"
        assert Decimal(linea["base_quantity"]) == Decimal("24"), "se perdió la cantidad base"
        assert Decimal(linea["conversion_factor_snapshot"]) == Decimal("12")
        assert Decimal(linea["base_fiscal"]) == Decimal("200.00")
    finally:
        db.close()


def test_el_impuesto_lo_resuelve_la_regla_versionada(mundo):
    """`§35`: ninguna tasa escrita en esta Spec; la elige el motor por código y fecha."""
    db = mundo.factory()
    try:
        f = _fiscal_listo(db, mundo, rate=16.0)
        e = _pedido_confirmado(db, mundo, requerido=10, precio="50.00", tax_ref=f["tax_code"])
        sales.request_billing(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                              actor="verificador")
        factura = sales.generate_invoice(db, company_id=mundo.company_a,
                                         order_id=str(e["pedido"].id), actor="facturador")
        db.commit()
        d = sales.billing_invoice_dict(db, factura)
        assert Decimal(d["base_fiscal"]) == Decimal("500.00")
        assert Decimal(d["tax_total"]) == Decimal("80.00"), "el impuesto no salió de la regla"
        assert Decimal(d["total"]) == Decimal("580.00")
        assert f["series"]
    finally:
        db.close()


# =========================================================================== #
# La emisión fiscal
# =========================================================================== #
def test_emitir_consume_correlativo_y_numero_de_control(mundo):
    """¶97: la numeración es de la Spec 042 y se consume atómicamente."""
    db = mundo.factory()
    try:
        f = _fiscal_listo(db, mundo)
        e = _pedido_confirmado(db, mundo, requerido=5, precio="10.00")
        factura = _emitir(db, mundo, e, f)

        assert factura.status == "EMITTED"
        assert factura.invoice_number, "no se asignó correlativo"
        assert factura.control_number, "no se asignó número de control"
        assert factura.fiscal_document_id
        assert db.get(SalesOrder, str(e["pedido"].id)).status == "INVOICED"
        doc = db.execute(select(FiscalDocument).where(
            FiscalDocument.business_document == f"INVOICE:{factura.id}")).scalars().first()
        assert doc is not None and doc.status == "EMITTED"
    finally:
        db.close()


def test_emitir_dos_veces_no_gasta_dos_numeros(mundo):
    """`emit_document` es idempotente por `INVOICE:{id}`."""
    db = mundo.factory()
    try:
        f = _fiscal_listo(db, mundo)
        e = _pedido_confirmado(db, mundo, requerido=3, precio="10.00")
        factura = _emitir(db, mundo, e, f)
        numero, control = factura.invoice_number, factura.control_number
        otra = sales.issue_invoice(db, company_id=mundo.company_a, invoice_id=str(factura.id),
                                   series_id=f["series"], batch_id=f["batch"], actor="facturador")
        db.commit()
        assert (otra.invoice_number, otra.control_number) == (numero, control)
        assert db.execute(select(func.count(FiscalDocument.id)).where(
            FiscalDocument.business_document == f"INVOICE:{factura.id}")).scalar() == 1
    finally:
        db.close()


def test_no_se_emite_una_factura_sin_pedido(mundo):
    db = mundo.factory()
    try:
        f = _fiscal_listo(db, mundo)
        from app.modules.master_data.models import Party

        p = Party(company_id=mundo.company_a, code=f"CS-{uuid4().hex[:6]}", name="C", roles=["CLIENTE"])
        db.add(p)
        db.flush()
        suelta = sales.create_invoice(db, company_id=mundo.company_a, customer_id=str(p.id),
                                      actor="qa")
        db.commit()
        with pytest.raises(ConflictError) as exc:
            sales.issue_invoice(db, company_id=mundo.company_a, invoice_id=str(suelta.id),
                                series_id=f["series"], batch_id=f["batch"], actor="qa")
        assert exc.value.code == "INVOICE_WITHOUT_ORDER"
    finally:
        db.close()


# =========================================================================== #
# Las fronteras
# =========================================================================== #
def test_facturar_no_mueve_una_sola_unidad(mundo):
    """Facturar no es mover: la mercancía sale con el despacho, no con la factura."""
    db = mundo.factory()
    try:
        f = _fiscal_listo(db, mundo)
        e = _pedido_confirmado(db, mundo, requerido=6, precio="10.00")
        saldos0 = {(b.location_id, b.state): (Decimal(str(b.qty_on_hand)), Decimal(str(b.qty_reserved)))
                   for b in db.execute(select(InventoryBalance).where(
                       InventoryBalance.product_id == e["prod"])).scalars().all()}
        movs0 = db.execute(select(func.count(InventoryMovement.id)).where(
            InventoryMovement.product_id == e["prod"])).scalar()

        _emitir(db, mundo, e, f)

        saldos1 = {(b.location_id, b.state): (Decimal(str(b.qty_on_hand)), Decimal(str(b.qty_reserved)))
                   for b in db.execute(select(InventoryBalance).where(
                       InventoryBalance.product_id == e["prod"])).scalars().all()}
        assert saldos1 == saldos0, "facturar movió inventario o tocó la reserva"
        assert db.execute(select(func.count(InventoryMovement.id)).where(
            InventoryMovement.product_id == e["prod"])).scalar() == movs0
    finally:
        db.close()


def test_el_estado_de_facturacion_es_consultable_para_el_despacho(mundo):
    """¶103: el despacho verifica «Pedido preparado + confirmado + **factura emitida**»."""
    db = mundo.factory()
    try:
        f = _fiscal_listo(db, mundo)
        e = _pedido_confirmado(db, mundo, requerido=2, precio="10.00")
        antes = sales.order_invoice_dict(db, company_id=mundo.company_a,
                                         order_id=str(e["pedido"].id))
        assert antes["invoiced"] is False and antes["invoice"] is None
        _emitir(db, mundo, e, f)
        despues = sales.order_invoice_dict(db, company_id=mundo.company_a,
                                           order_id=str(e["pedido"].id))
        assert despues["invoiced"] is True
        assert despues["invoice"]["control_number"]
    finally:
        db.close()


def test_la_facturacion_no_cruza_empresas(mundo):
    db = mundo.factory()
    try:
        e = _pedido_confirmado(db, mundo)
        with pytest.raises(NotFoundError):
            sales.request_billing(db, company_id=mundo.company_b,
                                  order_id=str(e["pedido"].id), actor="qa")
        pendientes = sales.billable_orders(db, company_id=mundo.company_b)
        assert str(e["pedido"].id) not in [str(o.id) for o in pendientes]
    finally:
        db.close()


def test_dos_facturadores_no_generan_dos_facturas(mundo):
    """P0 sobre PostgreSQL real: un pedido, una factura."""
    import threading

    db = mundo.factory()
    try:
        e = _pedido_confirmado(db, mundo, requerido=4, precio="10.00")
        sales.request_billing(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                              actor="verificador")
        db.commit()
        order_id = str(e["pedido"].id)
    finally:
        db.close()

    exitos: list[str] = []
    choques: list[str] = []

    def _worker() -> None:
        s = mundo.factory()
        try:
            f = sales.generate_invoice(s, company_id=mundo.company_a, order_id=order_id,
                                       actor="facturador")
            s.commit()
            exitos.append(str(f.id))
        except Exception as exc:                                   # noqa: BLE001
            s.rollback()
            choques.append(type(exc).__name__)
        finally:
            s.close()

    hilos = [threading.Thread(target=_worker) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    db = mundo.factory()
    try:
        assert len(exitos) == 1, f"se generaron dos facturas: {exitos} {choques}"
        assert db.execute(select(func.count(SalesInvoice.id)).where(
            SalesInvoice.order_id == order_id)).scalar() == 1
    finally:
        db.close()


def test_no_basta_con_poner_el_pedido_en_confirmado_a_mano(mundo):
    """La compuerta comprueba **el registro**, no solo el estado.

    Es la advertencia que dejó escrita el contrato de entrega de la Spec 033: un
    control que se satisface moviendo un estado a mano no es un control. Aquí el
    pedido dice `CONFIRMED` y no existe ninguna confirmación independiente.
    """
    db = mundo.factory()
    try:
        marca = uuid4().hex[:8]
        from app.modules.master_data.models import Party

        p = Party(company_id=mundo.company_a, code=f"CM-{marca}", name="Cliente", roles=["CLIENTE"])
        db.add(p)
        db.flush()
        ped = SalesOrder(company_id=mundo.company_a, code=f"OVM-{marca}", customer_id=str(p.id),
                         warehouse_id=mundo.warehouse_a, currency="VED", status="CONFIRMED")
        db.add(ped)
        db.commit()
        with pytest.raises(ConflictError) as exc:
            sales.request_billing(db, company_id=mundo.company_a, order_id=str(ped.id),
                                  actor="verificador")
        assert exc.value.code == "BILLING_NOT_CONFIRMED"
        db.rollback()
        assert db.get(SalesOrder, str(ped.id)).status == "CONFIRMED", "el pedido avanzó igualmente"
    finally:
        db.close()
