"""Spec 036 · devoluciones, notas de crédito y notas de débito.

Lo que estas pruebas defienden es el orden que la norma escribe —«Solicitud →
Verificación física → Aprobación → **Entrada de inventario** → Nota de crédito
vinculada»— y las dos cosas que ese orden implica: que una solicitud no aumenta
existencia y que recibir la mercancía no la hace vendible.

Multiempresa sobre PostgreSQL real, con el arnés `mundo`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.fiscal import service as fiscal
from app.modules.inventory import service as inv
from app.modules.inventory.models import InventoryBalance, Reservation
from app.modules.organization.models import WarehouseLocation
from app.modules.sales import service as sales
from app.modules.sales.models import PickList, SalesOrder, SalesOrderLine

pytest_plugins = ("tests.conftest_multicompany",)


# --------------------------------------------------------------------------- #
# Hasta el despacho: lo que una devolución necesita detrás
# --------------------------------------------------------------------------- #
def _producto(db, company_id, marca) -> str:
    from app.modules.master_data.models import CatalogItem

    item = CatalogItem(company_id=company_id, code=f"PR-{marca}", name=f"Artículo {marca}",
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


def _fiscal_listo(db, mundo):
    """Series para los tres documentos: la factura y las dos notas.

    Cada tipo tiene la suya porque la norma exige «consecutivo propio» a la nota
    de crédito, y el motor de la 042 se niega a gastar la serie de facturas en
    una nota.
    """
    marca = uuid4().hex[:6]
    fuente = fiscal.create_legal_source(db, authority="SENIAT", source_type="LEY",
                                        number=f"LR-{marca}", effective_from=date(2020, 1, 1))
    fiscal.activate_legal_source(db, source_id=str(fuente.id))
    series = {}
    for tipo, prefijo in (("INVOICE", "F"), ("CREDIT_NOTE", "NC"), ("DEBIT_NOTE", "ND")):
        s = fiscal.create_number_series(db, company_id=mundo.company_a, document_type=tipo,
                                        prefix=prefijo)
        series[tipo] = str(s.id)
    desde = 300000 + int(uuid4().int % 400000)
    lote = fiscal.create_control_batch(db, company_id=mundo.company_a,
                                       range_from=str(desde), range_to=str(desde + 99))
    db.flush()
    return {"series": series, "batch": str(lote.id)}


def _despachado(db, mundo, *, cantidad=10, precio="20.00", quantity=None, factor=None,
                tax_code=None):
    """Un pedido recorrido entero hasta que la mercancía salió del almacén."""
    marca = uuid4().hex[:8]
    f = _fiscal_listo(db, mundo)
    prod = _producto(db, mundo.company_a, marca)
    l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"R1-{marca}", sequence=1)
    area = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"RC-{marca}", sequence=98)
    devoluciones = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"RD-{marca}", sequence=99)
    tipo = inv._get_movement_type_by_code(db, mundo.company_a, "ENTRADA_RECEPCION")
    inv.record_movement(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                        product_id=prod, movement_type_id=str(tipo.id), quantity=cantidad + 20,
                        actor="qa")
    inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod,
                target_location_id=l1, quantity=cantidad + 20, actor="qa")

    from app.modules.master_data.models import Party

    p = Party(company_id=mundo.company_a, code=f"CLR-{marca}", name=f"Cliente {marca}",
              roles=["CLIENTE"])
    db.add(p)
    db.flush()
    ahora = datetime.now(UTC)
    ped = SalesOrder(company_id=mundo.company_a, code=f"OVR-{marca}", customer_id=str(p.id),
                     warehouse_id=mundo.warehouse_a, currency="VED", status="RELEASED",
                     submitted_at=ahora, released_at=ahora)
    db.add(ped)
    db.flush()
    ln = SalesOrderLine(order_id=str(ped.id), product_id=prod,
                        quantity=Decimal(str(quantity if quantity is not None else cantidad)),
                        unit_price=Decimal(precio), needs_inventory=True, tax_ref=tax_code,
                        conversion_factor_snapshot=Decimal(str(factor)) if factor else None,
                        base_quantity=Decimal(str(cantidad)))
    db.add(ln)
    db.flush()
    inv.reserve(db, company_id=mundo.company_a, source_document=ped.code, product_id=prod,
                warehouse_id=mundo.warehouse_a, quantity=float(ln.quantity),
                source_type="SALES_ORDER", source_order_id=str(ped.id), source_line_id=str(ln.id),
                base_quantity=Decimal(str(cantidad)), actor="qa")
    plan = PickList(company_id=mundo.company_a, code=f"PLR-{marca}", order_id=str(ped.id),
                    warehouse_id=mundo.warehouse_a, status="DRAFT")
    db.add(plan)
    db.flush()
    sales.allocate(db, company_id=mundo.company_a, plan_id=str(plan.id), order_line_id=str(ln.id),
                   location_id=l1, quantity=cantidad, actor="qa")
    sales.confirm_plan(db, company_id=mundo.company_a, plan_id=str(plan.id), actor="planificador")
    parada = next(x for x in sales._lineas_del_plan(db, plan) if x.location_id)
    sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(plan.id),
                       line_id=str(parada.id), quantity=cantidad, actor="almacenista")
    sales.consolidate(db, company_id=mundo.company_a, plan_id=str(plan.id), location_id=area,
                      actor="almacenista")
    sales.confirm_order(db, company_id=mundo.company_a, order_id=str(ped.id),
                        lines=[{"order_line_id": str(ln.id), "checked_base_quantity": cantidad}],
                        actor="verificador")
    sales.request_billing(db, company_id=mundo.company_a, order_id=str(ped.id), actor="verificador")
    factura = sales.generate_invoice(db, company_id=mundo.company_a, order_id=str(ped.id),
                                     actor="facturador")
    sales.issue_invoice(db, company_id=mundo.company_a, invoice_id=str(factura.id),
                        series_id=f["series"]["INVOICE"], batch_id=f["batch"], actor="facturador")
    sh = sales.create_shipment(db, company_id=mundo.company_a, code=f"SHR-{marca}",
                               order_id=str(ped.id), destination="Caracas",
                               transport="Transportista", actor="despachador")
    sales.validate_shipment(db, shipment=sh, actor="despachador")
    sales.confirm_shipment(db, shipment=sh, actor="despachador")
    db.commit()
    return {"prod": prod, "l1": l1, "area": area, "devoluciones": devoluciones, "pedido": ped,
            "linea": ln, "plan": plan, "factura": factura, "fiscal": f, "despacho": sh,
            "cantidad": Decimal(str(cantidad))}


def _saldos(db, company_id, product_id) -> dict:
    filas = db.execute(select(InventoryBalance).where(
        InventoryBalance.company_id == company_id,
        InventoryBalance.product_id == product_id)).scalars().all()
    return {(f.location_id, f.state): Decimal(str(f.qty_on_hand)) for f in filas if f.qty_on_hand}


def _por_estado(db, company_id, product_id) -> dict:
    salida: dict[str, Decimal] = {}
    for (_loc, estado), cantidad in _saldos(db, company_id, product_id).items():
        salida[estado] = salida.get(estado, Decimal(0)) + cantidad
    return salida


def _linea_factura(db, e):
    from app.modules.sales.models import SalesInvoiceLine

    return db.execute(select(SalesInvoiceLine).where(
        SalesInvoiceLine.invoice_id == str(e["factura"].id))).scalars().first()


def _solicitar(db, mundo, e, *, base=None, quantity=None):
    lf = _linea_factura(db, e)
    return sales.request_return(
        db, company_id=mundo.company_a, code=f"DEV-{uuid4().hex[:8]}",
        invoice_id=str(e["factura"].id), reason="Mercancía dañada en tránsito",
        lines=[{"invoice_line_id": str(lf.id),
                "base_quantity": base if base is not None else e["cantidad"],
                "quantity": quantity if quantity is not None else float(lf.quantity)}],
        actor="vendedor")


# =========================================================================== #
# El orden de los cuatro actos
# =========================================================================== #
def test_la_solicitud_no_mueve_una_sola_unidad(mundo):
    """Primer acto. La mercancía sigue con el cliente."""
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=10)
        antes = _por_estado(db, mundo.company_a, e["prod"])
        dev = _solicitar(db, mundo, e, base=4)
        db.commit()
        assert dev.status == "REQUESTED"
        assert dev.requested_at is not None
        assert _por_estado(db, mundo.company_a, e["prod"]) == antes, \
            "una solicitud de devolución movió inventario"
    finally:
        db.close()


def test_recibir_devuelve_la_custodia_pero_no_la_disponibilidad(mundo):
    """Segundo acto: `DESPACHADO → DEVUELTO`. Vendible es solo `DISPONIBLE`."""
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=10)
        disponible_antes = _por_estado(db, mundo.company_a, e["prod"]).get("DISPONIBLE", Decimal(0))
        dev = _solicitar(db, mundo, e, base=4)
        sales.receive_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             location_id=e["devoluciones"], actor="almacenista")
        db.commit()
        estados = _por_estado(db, mundo.company_a, e["prod"])
        assert estados.get("DEVUELTO") == Decimal("4")
        assert estados.get("DESPACHADO") == Decimal("6"), "no descontó de lo despachado"
        assert estados.get("DISPONIBLE", Decimal(0)) == disponible_antes, \
            "recibir una devolución la hizo vendible sin verificarla"
        assert dev.status == "RECEIVED"
        assert dev.location_id == e["devoluciones"], "la mercancía devuelta no tiene ubicación"
    finally:
        db.close()


def test_la_entrada_de_inventario_es_el_cuarto_acto_y_respeta_el_dictamen(mundo):
    """La cadena entera, con una línea aceptada solo en parte."""
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=12)
        dev = _solicitar(db, mundo, e, base=12)
        sales.receive_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             location_id=e["devoluciones"], actor="almacenista")
        linea = sales._lineas_de_devolucion(db, str(dev.id))[0]
        # Ocho vuelven a existencia; los otros cuatro no son aptos.
        sales.inspect_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             lines=[{"return_line_id": str(linea.id), "disposition": "DISPONIBLE",
                                     "accepted_base_quantity": 8}], actor="verificador")
        sales.decide_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                            approved=True, actor="jefe")
        sales.reenter_return(db, company_id=mundo.company_a, return_id=str(dev.id), actor="almacenista")
        db.commit()
        estados = _por_estado(db, mundo.company_a, e["prod"])
        assert estados.get("DISPONIBLE") == Decimal("28"), "20 que quedaban + 8 aceptadas"
        assert estados.get("DEVUELTO") == Decimal("4"), "lo no aceptado sigue en custodia"
        assert estados.get("DESPACHADO", Decimal(0)) == Decimal(0)
        assert dev.status == "CLOSED"
    finally:
        db.close()


def test_no_se_reingresa_sin_aprobacion(mundo):
    """«Aprobación» va antes de «Entrada de inventario», y el orden se cumple."""
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=5)
        dev = _solicitar(db, mundo, e, base=5)
        sales.receive_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             location_id=e["devoluciones"], actor="almacenista")
        linea = sales._lineas_de_devolucion(db, str(dev.id))[0]
        sales.inspect_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             lines=[{"return_line_id": str(linea.id), "disposition": "DISPONIBLE"}],
                             actor="verificador")
        with pytest.raises(ConflictError):
            sales.reenter_return(db, company_id=mundo.company_a, return_id=str(dev.id), actor="x")
    finally:
        db.close()


def test_no_se_inspecciona_lo_que_no_ha_llegado(mundo):
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=5)
        dev = _solicitar(db, mundo, e, base=5)
        db.flush()
        with pytest.raises(ConflictError):
            sales.inspect_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                                 lines=[{"return_line_id": "x", "disposition": "DISPONIBLE"}],
                                 actor="verificador")
    finally:
        db.close()


def test_el_destino_de_la_mercancia_devuelta_no_se_inventa(mundo):
    """`D0-10` concede a la 036 dos destinos. `CUARENTENA` tiene otra dueña."""
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=5)
        dev = _solicitar(db, mundo, e, base=5)
        sales.receive_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             location_id=e["devoluciones"], actor="almacenista")
        linea = sales._lineas_de_devolucion(db, str(dev.id))[0]
        with pytest.raises(KontrolError) as exc:
            sales.inspect_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                                 lines=[{"return_line_id": str(linea.id),
                                         "disposition": "CUARENTENA"}], actor="verificador")
        assert exc.value.code == "RETURN_DISPOSITION_INVALID"
    finally:
        db.close()


# =========================================================================== #
# La cantidad: base, no comercial
# =========================================================================== #
def test_devolver_una_caja_de_doce_reingresa_doce(mundo):
    """El caso P0 del tramo, esta vez al revés que en el despacho."""
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=24, quantity=2, factor=12)
        lf = _linea_factura(db, e)
        dev = sales.request_return(
            db, company_id=mundo.company_a, code=f"DEV-{uuid4().hex[:8]}",
            invoice_id=str(e["factura"].id), reason="Una caja llegó rota",
            lines=[{"invoice_line_id": str(lf.id), "quantity": 1, "base_quantity": 12}],
            actor="vendedor")
        sales.receive_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             location_id=e["devoluciones"], actor="almacenista")
        db.commit()
        estados = _por_estado(db, mundo.company_a, e["prod"])
        assert estados.get("DEVUELTO") == Decimal("12"), "devolvió cajas, no unidades"
        assert estados.get("DESPACHADO") == Decimal("12")
        linea = sales._lineas_de_devolucion(db, str(dev.id))[0]
        assert Decimal(str(linea.conversion_factor_snapshot)) == Decimal("12"), \
            "no congeló el factor de la factura"
    finally:
        db.close()


def test_no_se_devuelve_mas_de_lo_despachado(mundo):
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=10)
        with pytest.raises(ConflictError) as exc:
            _solicitar(db, mundo, e, base=11)
        assert exc.value.code == "RETURN_EXCEEDS_DISPATCHED"
    finally:
        db.close()


def test_dos_devoluciones_no_suman_mas_de_lo_despachado(mundo):
    """El tope es acumulativo: 8 + 4 sobre 10 despachadas no pasa."""
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=10)
        _solicitar(db, mundo, e, base=8)
        db.commit()
        elegible = sales.return_eligibility(db, company_id=mundo.company_a,
                                            invoice_id=str(e["factura"].id))
        assert Decimal(elegible["lines"][0]["returnable_base_quantity"]) == Decimal("2")
        with pytest.raises(ConflictError) as exc:
            _solicitar(db, mundo, e, base=4)
        assert exc.value.code == "RETURN_EXCEEDS_DISPATCHED"
    finally:
        db.close()


def test_una_devolucion_cancelada_libera_lo_que_reservaba(mundo):
    """Lo devuelto acumulado no cuenta las canceladas ni las denegadas."""
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=10)
        dev = _solicitar(db, mundo, e, base=10)
        db.commit()
        dev.status = "CANCELLED"
        db.flush()
        elegible = sales.return_eligibility(db, company_id=mundo.company_a,
                                            invoice_id=str(e["factura"].id))
        assert Decimal(elegible["lines"][0]["returnable_base_quantity"]) == Decimal("10")
    finally:
        db.close()


# =========================================================================== #
# La reserva no se resucita (`D0-03`)
# =========================================================================== #
def test_la_devolucion_no_reabre_la_reserva_consumida(mundo):
    """`D0-03`: «re-reservar tras liberar = nueva fila, nunca reactivación».

    Y `FULFILLED` no es liberación: es consumo. La disponibilidad nueva viene de
    la entrada de inventario, no de resucitar el compromiso de una venta que sí
    ocurrió.
    """
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=10)
        reservas = db.execute(select(Reservation).where(
            Reservation.company_id == mundo.company_a,
            Reservation.source_order_id == str(e["pedido"].id))).scalars().all()
        assert reservas and all(r.status == "FULFILLED" for r in reservas)
        antes = {str(r.id): (r.status, str(r.quantity)) for r in reservas}

        dev = _solicitar(db, mundo, e, base=10)
        sales.receive_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             location_id=e["devoluciones"], actor="almacenista")
        linea = sales._lineas_de_devolucion(db, str(dev.id))[0]
        sales.inspect_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             lines=[{"return_line_id": str(linea.id), "disposition": "DISPONIBLE"}],
                             actor="verificador")
        sales.decide_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                            approved=True, actor="jefe")
        sales.reenter_return(db, company_id=mundo.company_a, return_id=str(dev.id), actor="almacenista")
        db.commit()

        despues = db.execute(select(Reservation).where(
            Reservation.company_id == mundo.company_a,
            Reservation.source_order_id == str(e["pedido"].id))).scalars().all()
        assert {str(r.id): (r.status, str(r.quantity)) for r in despues} == antes, \
            "la devolución tocó una reserva ya consumida"
        assert len(despues) == len(reservas), "la devolución creó una reserva por su cuenta"
        # Y el pedido sigue donde estaba: la venta ocurrió.
        assert db.get(SalesOrder, str(e["pedido"].id)).status == "SHIPPED"
    finally:
        db.close()


# =========================================================================== #
# La nota de crédito
# =========================================================================== #
def test_aceptar_la_devolucion_no_emite_la_nota(mundo):
    """«La devolución física **no sustituye** una nota de crédito»."""
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=6)
        dev = _solicitar(db, mundo, e, base=6)
        sales.receive_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             location_id=e["devoluciones"], actor="almacenista")
        linea = sales._lineas_de_devolucion(db, str(dev.id))[0]
        sales.inspect_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             lines=[{"return_line_id": str(linea.id), "disposition": "DISPONIBLE"}],
                             actor="verificador")
        sales.decide_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                            approved=True, actor="jefe")
        sales.reenter_return(db, company_id=mundo.company_a, return_id=str(dev.id), actor="almacenista")
        db.commit()
        from app.modules.sales.models import SalesCreditNote

        notas = db.execute(select(SalesCreditNote).where(
            SalesCreditNote.invoice_id == str(e["factura"].id))).scalars().all()
        assert notas == [], "aceptar la devolución emitió una nota por su cuenta"
        assert db.get(type(e["factura"]), str(e["factura"].id)).status != "CREDITED"
    finally:
        db.close()


def test_la_nota_reparte_el_impuesto_de_la_factura_en_proporcion(mundo):
    """«Recalcular **proporcionalmente** base imponible e IVA».

    No se vuelve a calcular con las reglas de hoy: se reparte el que la factura
    ya lleva. Eso es lo único que «mantiene la misma clasificación tributaria de
    la operación original», porque no vuelve a clasificar nada.
    """
    db = mundo.factory()
    try:
        marca = uuid4().hex[:6]
        fuente = fiscal.create_legal_source(db, authority="SENIAT", source_type="LEY",
                                            number=f"LI-{marca}", effective_from=date(2020, 1, 1))
        fiscal.activate_legal_source(db, source_id=str(fuente.id))
        codigo = f"IVA_{marca}"
        # Una tasa que no es la corriente, a propósito: con el 16 % habitual, un
        # impuesto recalculado con la regla de hoy daría por casualidad el mismo
        # número que uno repartido, y la prueba no distinguiría las dos cosas.
        regla = fiscal.create_tax_rule(db, tax_code=codigo, legal_source_id=str(fuente.id),
                                       effective_from=date(2020, 1, 1), rate=7.0)
        fiscal.approve_tax_rule(db, rule_id=str(regla.id))
        db.flush()
        e = _despachado(db, mundo, cantidad=10, precio="100.00", tax_code=codigo)
        factura = e["factura"]
        assert Decimal(str(factura.base_fiscal)) == Decimal("1000")
        assert Decimal(str(factura.tax_total)) == Decimal("70")

        lf = _linea_factura(db, e)
        nota = sales.generate_credit_note(
            db, company_id=mundo.company_a, invoice_id=str(factura.id),
            cause="Devolución de mercancía",
            lines=[{"invoice_line_id": str(lf.id), "quantity": 2}], actor="facturador")
        db.flush()
        # Dos de diez: la quinta parte de la base y la quinta parte del impuesto.
        assert Decimal(str(nota.base_fiscal)) == Decimal("200.00")
        assert Decimal(str(nota.tax_total)) == Decimal("14.00")
        assert Decimal(str(nota.amount)) == Decimal("214.00")
    finally:
        db.close()


def test_la_nota_conserva_la_clasificacion_de_la_factura_aunque_la_regla_cambie(mundo):
    """«Mantener la misma clasificación tributaria de la operación original».

    Es la prueba que ningún recálculo puede pasar: la regla cambia **después**
    de emitir la factura, y la nota tiene que seguir llevando el impuesto que la
    operación llevó, no el que se cobraría hoy.
    """
    db = mundo.factory()
    try:
        marca = uuid4().hex[:6]
        fuente = fiscal.create_legal_source(db, authority="SENIAT", source_type="LEY",
                                            number=f"LC-{marca}", effective_from=date(2020, 1, 1))
        fiscal.activate_legal_source(db, source_id=str(fuente.id))
        codigo = f"IVA_{marca}"
        vieja = fiscal.create_tax_rule(db, tax_code=codigo, legal_source_id=str(fuente.id),
                                       effective_from=date(2020, 1, 1), rate=7.0)
        fiscal.approve_tax_rule(db, rule_id=str(vieja.id))
        db.flush()
        e = _despachado(db, mundo, cantidad=10, precio="100.00", tax_code=codigo)
        assert Decimal(str(e["factura"].tax_total)) == Decimal("70")

        # La alícuota sube después de facturar.
        vieja.effective_to = date(2024, 12, 31)
        db.flush()
        nueva = fiscal.create_tax_rule(db, tax_code=codigo, legal_source_id=str(fuente.id),
                                       effective_from=date(2025, 1, 1), rate=25.0)
        fiscal.approve_tax_rule(db, rule_id=str(nueva.id))
        db.flush()

        lf = _linea_factura(db, e)
        nota = sales.generate_credit_note(
            db, company_id=mundo.company_a, invoice_id=str(e["factura"].id),
            cause="Devolución de mercancía",
            lines=[{"invoice_line_id": str(lf.id), "quantity": 5}], actor="facturador")
        db.flush()
        assert Decimal(str(nota.tax_total)) == Decimal("35.00"), \
            "la nota usó la alícuota de hoy en vez de la de la operación"
        assert Decimal(str(nota.base_fiscal)) == Decimal("500.00")
    finally:
        db.close()


def test_no_se_acredita_por_encima_de_lo_pendiente(mundo):
    """La regla de integridad: «no ajustar por encima de lo pendiente»."""
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=10, precio="50.00")
        lf = _linea_factura(db, e)
        sales.generate_credit_note(db, company_id=mundo.company_a,
                                   invoice_id=str(e["factura"].id), cause="Descuento posterior",
                                   lines=[{"invoice_line_id": str(lf.id), "quantity": 8}],
                                   actor="facturador")
        db.commit()
        elegible = sales.credit_eligibility(db, company_id=mundo.company_a,
                                            invoice_id=str(e["factura"].id))
        assert Decimal(elegible["lines"][0]["creditable_quantity"]) == Decimal("2")
        with pytest.raises(ConflictError) as exc:
            sales.generate_credit_note(db, company_id=mundo.company_a,
                                       invoice_id=str(e["factura"].id), cause="Otra más",
                                       lines=[{"invoice_line_id": str(lf.id), "quantity": 3}],
                                       actor="facturador")
        assert exc.value.code == "CREDIT_EXCEEDS_INVOICE"
    finally:
        db.close()


def test_la_nota_existe_sin_devolucion(mundo):
    """La norma lista causas que no traen mercancía: descuento, corrección…"""
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=4, precio="25.00")
        antes = _por_estado(db, mundo.company_a, e["prod"])
        lf = _linea_factura(db, e)
        nota = sales.generate_credit_note(
            db, company_id=mundo.company_a, invoice_id=str(e["factura"].id),
            cause="Descuento posterior acordado con el cliente",
            lines=[{"invoice_line_id": str(lf.id), "quantity": 1}], actor="facturador")
        sales.issue_credit_note(db, company_id=mundo.company_a, note_id=str(nota.id),
                                series_id=e["fiscal"]["series"]["CREDIT_NOTE"],
                                batch_id=e["fiscal"]["batch"], actor="facturador")
        db.commit()
        assert nota.return_id is None
        assert nota.invoice_number and nota.control_number
        assert _por_estado(db, mundo.company_a, e["prod"]) == antes, \
            "una nota sin devolución movió inventario"
    finally:
        db.close()


def test_la_nota_lleva_consecutivo_y_control_propios(mundo):
    """«Tener consecutivo propio. Tener número de control»."""
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=4, precio="25.00")
        lf = _linea_factura(db, e)
        nota = sales.generate_credit_note(
            db, company_id=mundo.company_a, invoice_id=str(e["factura"].id),
            cause="Corrección de un precio facturado en exceso",
            lines=[{"invoice_line_id": str(lf.id), "quantity": 1}], actor="facturador")
        assert nota.invoice_number is None, "la nota nació numerada sin emitirse"
        sales.issue_credit_note(db, company_id=mundo.company_a, note_id=str(nota.id),
                                series_id=e["fiscal"]["series"]["CREDIT_NOTE"],
                                batch_id=e["fiscal"]["batch"], actor="facturador")
        db.commit()
        assert nota.invoice_number != e["factura"].invoice_number, \
            "la nota reutilizó el número de la factura"
        assert nota.control_number != e["factura"].control_number
        assert nota.fiscal_document_id
    finally:
        db.close()


def test_la_nota_no_se_emite_con_la_serie_de_las_facturas(mundo):
    """Gastar el correlativo de facturas en una nota rompe los dos libros."""
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=4, precio="25.00")
        lf = _linea_factura(db, e)
        nota = sales.generate_credit_note(
            db, company_id=mundo.company_a, invoice_id=str(e["factura"].id),
            cause="Anulación de una operación",
            lines=[{"invoice_line_id": str(lf.id), "quantity": 1}], actor="facturador")
        with pytest.raises(KontrolError) as exc:
            sales.issue_credit_note(db, company_id=mundo.company_a, note_id=str(nota.id),
                                    series_id=e["fiscal"]["series"]["INVOICE"],
                                    batch_id=e["fiscal"]["batch"], actor="facturador")
        assert exc.value.code == "SERIES_DOCUMENT_TYPE_MISMATCH"
    finally:
        db.close()


def test_emitir_dos_veces_no_gasta_dos_numeros(mundo):
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=4, precio="25.00")
        lf = _linea_factura(db, e)
        nota = sales.generate_credit_note(
            db, company_id=mundo.company_a, invoice_id=str(e["factura"].id),
            cause="Devolución de envases",
            lines=[{"invoice_line_id": str(lf.id), "quantity": 1}], actor="facturador")
        uno = sales.issue_credit_note(db, company_id=mundo.company_a, note_id=str(nota.id),
                                      series_id=e["fiscal"]["series"]["CREDIT_NOTE"],
                                      batch_id=e["fiscal"]["batch"], actor="facturador")
        numero, control = uno.invoice_number, uno.control_number
        dos = sales.issue_credit_note(db, company_id=mundo.company_a, note_id=str(nota.id),
                                      series_id=e["fiscal"]["series"]["CREDIT_NOTE"],
                                      batch_id=e["fiscal"]["batch"], actor="facturador")
        db.commit()
        assert (dos.invoice_number, dos.control_number) == (numero, control)
    finally:
        db.close()


def test_la_factura_queda_acreditada_solo_cuando_se_acredita_entera(mundo):
    """`CREDITED` es terminal: ponerlo con una nota parcial mataría la factura."""
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=10, precio="10.00")
        lf = _linea_factura(db, e)
        parcial = sales.generate_credit_note(
            db, company_id=mundo.company_a, invoice_id=str(e["factura"].id),
            cause="Disminución de cantidad",
            lines=[{"invoice_line_id": str(lf.id), "quantity": 4}], actor="facturador")
        sales.issue_credit_note(db, company_id=mundo.company_a, note_id=str(parcial.id),
                                series_id=e["fiscal"]["series"]["CREDIT_NOTE"],
                                batch_id=e["fiscal"]["batch"], actor="facturador")
        db.commit()
        assert e["factura"].status != "CREDITED", "una nota parcial cerró la factura"

        resto = sales.generate_credit_note(
            db, company_id=mundo.company_a, invoice_id=str(e["factura"].id),
            cause="Reversión del resto",
            lines=[{"invoice_line_id": str(lf.id), "quantity": 6}], actor="facturador")
        sales.issue_credit_note(db, company_id=mundo.company_a, note_id=str(resto.id),
                                series_id=e["fiscal"]["series"]["CREDIT_NOTE"],
                                batch_id=e["fiscal"]["batch"], actor="facturador")
        db.commit()
        assert e["factura"].status == "CREDITED"
    finally:
        db.close()


def test_la_nota_reduce_la_cuenta_por_cobrar(mundo):
    """«Ajuste de cuenta por cobrar», con el motor que ya existe."""
    db = mundo.factory()
    try:
        from app.modules.purchasing.models import OpenItem

        e = _despachado(db, mundo, cantidad=10, precio="10.00")
        item = db.execute(select(OpenItem).where(
            OpenItem.company_id == mundo.company_a,
            OpenItem.source_document == f"SALES_INVOICE:{e['factura'].id}")).scalars().first()
        assert item is not None and Decimal(str(item.original)) == Decimal("100")
        lf = _linea_factura(db, e)
        nota = sales.generate_credit_note(
            db, company_id=mundo.company_a, invoice_id=str(e["factura"].id),
            cause="Devolución de mercancía",
            lines=[{"invoice_line_id": str(lf.id), "quantity": 3}], actor="facturador")
        sales.issue_credit_note(db, company_id=mundo.company_a, note_id=str(nota.id),
                                series_id=e["fiscal"]["series"]["CREDIT_NOTE"],
                                batch_id=e["fiscal"]["batch"], actor="facturador")
        db.commit()
        assert Decimal(str(item.applied)) == Decimal("30")
        assert Decimal(str(nota.applied)) == Decimal("30")
    finally:
        db.close()


# =========================================================================== #
# La nota de débito
# =========================================================================== #
def test_la_nota_de_debito_no_toca_el_inventario(mundo):
    """Su flujo no tiene una sola etapa física."""
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=5, precio="20.00")
        antes = _por_estado(db, mundo.company_a, e["prod"])
        nota = sales.generate_debit_note(
            db, company_id=mundo.company_a, invoice_id=str(e["factura"].id),
            cause="Flete posterior gravado",
            lines=[{"concept": "Flete al domicilio del cliente", "base_fiscal": 50}],
            actor="facturador")
        sales.issue_debit_note(db, company_id=mundo.company_a, note_id=str(nota.id),
                               series_id=e["fiscal"]["series"]["DEBIT_NOTE"],
                               batch_id=e["fiscal"]["batch"], actor="facturador")
        db.commit()
        assert _por_estado(db, mundo.company_a, e["prod"]) == antes
        assert nota.invoice_number and nota.control_number
        assert Decimal(str(nota.amount)) == Decimal("50.00")
    finally:
        db.close()


def test_la_nota_de_debito_aumenta_la_cuenta_por_cobrar(mundo):
    """«Aumenta el valor de una operación ya facturada»."""
    db = mundo.factory()
    try:
        from app.modules.purchasing.models import OpenItem

        e = _despachado(db, mundo, cantidad=5, precio="20.00")
        nota = sales.generate_debit_note(
            db, company_id=mundo.company_a, invoice_id=str(e["factura"].id),
            cause="Intereses de mora",
            lines=[{"concept": "Intereses por pago tardío", "base_fiscal": 25}],
            actor="facturador")
        sales.issue_debit_note(db, company_id=mundo.company_a, note_id=str(nota.id),
                               series_id=e["fiscal"]["series"]["DEBIT_NOTE"],
                               batch_id=e["fiscal"]["batch"], actor="facturador")
        db.commit()
        propio = db.execute(select(OpenItem).where(
            OpenItem.company_id == mundo.company_a,
            OpenItem.source_document == f"SALES_DEBIT_NOTE:{nota.id}")).scalars().first()
        assert propio is not None, "la nota de débito no creó su cuenta por cobrar"
        assert Decimal(str(propio.original)) == Decimal("25.00")
        factura_item = db.execute(select(OpenItem).where(
            OpenItem.source_document == f"SALES_INVOICE:{e['factura'].id}")).scalars().first()
        assert Decimal(str(factura_item.original)) == Decimal("100"), \
            "la nota de débito reescribió el documento de la factura"
    finally:
        db.close()


def test_la_nota_de_debito_no_es_una_factura_independiente(mundo):
    """«No puede utilizarse como una factura independiente»: exige el vínculo."""
    db = mundo.factory()
    try:
        with pytest.raises(NotFoundError):
            sales.generate_debit_note(db, company_id=mundo.company_a,
                                      invoice_id=str(uuid4()), cause="Cargo suelto",
                                      lines=[{"concept": "X", "base_fiscal": 10}], actor="x")
    finally:
        db.close()


# =========================================================================== #
# Multiempresa e idempotencia
# =========================================================================== #
def test_no_se_devuelve_una_factura_de_otra_empresa(mundo):
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=5)
        with pytest.raises(NotFoundError):
            sales.return_eligibility(db, company_id=mundo.company_b,
                                     invoice_id=str(e["factura"].id))
        with pytest.raises(NotFoundError):
            sales.credit_eligibility(db, company_id=mundo.company_b,
                                     invoice_id=str(e["factura"].id))
    finally:
        db.close()


def test_recibir_dos_veces_no_devuelve_la_mercancia_dos_veces(mundo):
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=6)
        dev = _solicitar(db, mundo, e, base=6)
        sales.receive_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             location_id=e["devoluciones"], actor="almacenista")
        sales.receive_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             location_id=e["devoluciones"], actor="almacenista")
        db.commit()
        assert _por_estado(db, mundo.company_a, e["prod"]).get("DEVUELTO") == Decimal("6")
    finally:
        db.close()


def test_reingresar_dos_veces_no_crea_existencia_dos_veces(mundo):
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=6)
        dev = _solicitar(db, mundo, e, base=6)
        sales.receive_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             location_id=e["devoluciones"], actor="almacenista")
        linea = sales._lineas_de_devolucion(db, str(dev.id))[0]
        sales.inspect_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             lines=[{"return_line_id": str(linea.id), "disposition": "DISPONIBLE"}],
                             actor="verificador")
        sales.decide_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                            approved=True, actor="jefe")
        sales.reenter_return(db, company_id=mundo.company_a, return_id=str(dev.id), actor="a")
        sales.reenter_return(db, company_id=mundo.company_a, return_id=str(dev.id), actor="a")
        db.commit()
        assert _por_estado(db, mundo.company_a, e["prod"]).get("DISPONIBLE") == Decimal("26")
    finally:
        db.close()


def test_denegar_una_devolucion_exige_motivo_y_deja_la_mercancia_en_custodia(mundo):
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=5)
        dev = _solicitar(db, mundo, e, base=5)
        sales.receive_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             location_id=e["devoluciones"], actor="almacenista")
        linea = sales._lineas_de_devolucion(db, str(dev.id))[0]
        sales.inspect_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             lines=[{"return_line_id": str(linea.id), "disposition": "RECHAZADO"}],
                             actor="verificador")
        with pytest.raises(KontrolError) as exc:
            sales.decide_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                                approved=False, actor="jefe")
        assert exc.value.code == "RETURN_REJECTION_REASON_REQUIRED"
        sales.decide_return(db, company_id=mundo.company_a, return_id=str(dev.id), approved=False,
                            reason="El cliente la usó; no procede", actor="jefe")
        db.commit()
        assert dev.status == "REJECTED"
        # La mercancía sigue donde la dejó la recepción: es custodia de la
        # empresa. Qué hacer con ella no lo decide esta Spec.
        assert _por_estado(db, mundo.company_a, e["prod"]).get("DEVUELTO") == Decimal("5")
    finally:
        db.close()


def test_iso_ven_03_la_devolucion_no_admite_lote_ni_serie_ajenos(mundo):
    """ISO-VEN-03: La devolución no admite lote ni serie ajenos a la empresa."""
    from app.modules.inventory.models import InventoryLot, ProductSerial

    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=10)
        lf = _linea_factura(db, e)

        pb = _producto(db, mundo.company_b, uuid4().hex[:8])
        lote = InventoryLot(company_id=mundo.company_b, product_id=pb,
                            lot_number="ISO-L-" + uuid4().hex[:6])
        serie = ProductSerial(company_id=mundo.company_b, product_id=pb,
                              serial="ISO-S-" + uuid4().hex[:6])
        db.add_all([lote, serie])
        db.flush()

        casos = [
            ("lot_id", str(lote.id), "LOT_NOT_FOUND"),
            ("lot_id", str(uuid4()), "LOT_NOT_FOUND"),
            ("serial_id", str(serie.id), "SERIAL_NOT_FOUND"),
            ("serial_id", str(uuid4()), "SERIAL_NOT_FOUND"),
        ]
        for campo, valor, codigo in casos:
            with pytest.raises(NotFoundError) as exc:
                sales.request_return(
                    db,
                    company_id=mundo.company_a,
                    code=f"DEV-{uuid4().hex[:8]}",
                    invoice_id=str(e["factura"].id),
                    reason="Devolución con referencia ajena",
                    lines=[{"invoice_line_id": str(lf.id),
                            "base_quantity": e["cantidad"],
                            "quantity": float(lf.quantity),
                            campo: valor}],
                    actor="vendedor",
                )
            assert exc.value.code == codigo
    finally:
        db.close()
