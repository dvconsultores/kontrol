"""Spec 035 · despacho, transporte y regulación.

Lo que estas pruebas defienden es la compuerta del ¶103 —«Pedido preparado +
Pedido confirmado + Factura emitida»— y la salida física correcta. Hasta este
ciclo `validate_shipment` aprobaba siempre mientras su docstring prometía
bloquear, y la salida descontaba la cantidad comercial de un estado equivocado.

Multiempresa sobre PostgreSQL real, con el arnés `mundo`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.fiscal import service as fiscal
from app.modules.inventory import service as inv
from app.modules.inventory.models import InventoryBalance
from app.modules.organization.models import WarehouseLocation
from app.modules.regulatory import service as reg
from app.modules.sales import service as sales
from app.modules.sales.models import PickList, SalesOrder, SalesOrderLine, Shipment, ShipmentLine
from app.shared.clock import hoy_de_negocio

pytest_plugins = ("tests.conftest_multicompany",)


# --------------------------------------------------------------------------- #
# La cadena entera hasta facturado
# --------------------------------------------------------------------------- #
def _producto(db, company_id, marca) -> str:
    from app.modules.master_data.models import CatalogItem

    item = CatalogItem(company_id=company_id, code=f"PD-{marca}", name=f"Artículo {marca}",
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
    marca = uuid4().hex[:6]
    fuente = fiscal.create_legal_source(db, authority="SENIAT", source_type="LEY",
                                        number=f"LD-{marca}", effective_from=date(2020, 1, 1))
    fiscal.activate_legal_source(db, source_id=str(fuente.id))
    serie = fiscal.create_number_series(db, company_id=mundo.company_a, document_type="INVOICE",
                                        prefix="D")
    desde = 200000 + int(uuid4().int % 500000)
    lote = fiscal.create_control_batch(db, company_id=mundo.company_a,
                                       range_from=str(desde), range_to=str(desde + 49))
    db.flush()
    return {"series": str(serie.id), "batch": str(lote.id)}


def _hasta_facturado(db, mundo, *, cantidad=10, precio="20.00", quantity=None, factor=None):
    """Preparado, confirmado y facturado: lo que el despacho debe recibir."""
    marca = uuid4().hex[:8]
    f = _fiscal_listo(db, mundo)
    prod = _producto(db, mundo.company_a, marca)
    l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"D1-{marca}", sequence=1)
    area = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"DC-{marca}", sequence=99)
    tipo = inv._get_movement_type_by_code(db, mundo.company_a, "ENTRADA_RECEPCION")
    inv.record_movement(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                        product_id=prod, movement_type_id=str(tipo.id), quantity=cantidad + 20,
                        actor="qa")
    inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod,
                target_location_id=l1, quantity=cantidad + 20, actor="qa")

    from app.modules.master_data.models import Party

    p = Party(company_id=mundo.company_a, code=f"CLD-{marca}", name=f"Cliente {marca}",
              roles=["CLIENTE"])
    db.add(p)
    db.flush()
    ahora = datetime.now(UTC)
    ped = SalesOrder(company_id=mundo.company_a, code=f"OVD-{marca}", customer_id=str(p.id),
                     warehouse_id=mundo.warehouse_a, currency="VED", status="RELEASED",
                     submitted_at=ahora, released_at=ahora)
    db.add(ped)
    db.flush()
    ln = SalesOrderLine(order_id=str(ped.id), product_id=prod,
                        quantity=Decimal(str(quantity if quantity is not None else cantidad)),
                        unit_price=Decimal(precio), needs_inventory=True,
                        conversion_factor_snapshot=Decimal(str(factor)) if factor else None,
                        base_quantity=Decimal(str(cantidad)))
    db.add(ln)
    db.flush()
    inv.reserve(db, company_id=mundo.company_a, source_document=ped.code, product_id=prod,
                warehouse_id=mundo.warehouse_a, quantity=float(ln.quantity),
                source_type="SALES_ORDER", source_order_id=str(ped.id), source_line_id=str(ln.id),
                base_quantity=Decimal(str(cantidad)), actor="qa")
    db.flush()

    plan = PickList(company_id=mundo.company_a, code=f"PLD-{marca}", order_id=str(ped.id),
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
    db.commit()
    return {"prod": prod, "l1": l1, "area": area, "pedido": ped, "linea": ln, "plan": plan,
            "factura": factura, "fiscal": f, "cantidad": Decimal(str(cantidad))}


def _emitir(db, mundo, e):
    f = sales.issue_invoice(db, company_id=mundo.company_a, invoice_id=str(e["factura"].id),
                            series_id=e["fiscal"]["series"], batch_id=e["fiscal"]["batch"],
                            actor="facturador")
    db.commit()
    return f


def _despacho(db, mundo, e, *, destino="Caracas", transporte="Transportista X"):
    sh = sales.create_shipment(db, company_id=mundo.company_a, code=f"SHD-{uuid4().hex[:8]}",
                               order_id=str(e["pedido"].id),
                               origin_warehouse_id=mundo.warehouse_a,
                               lines=[{"product_id": e["prod"],
                                       "quantity": float(e["linea"].quantity),
                                       "base_quantity": e["cantidad"],
                                       "conversion_factor_snapshot": e["linea"].conversion_factor_snapshot}],
                               actor="despachador")
    sh.destination = destino
    sh.transport = transporte
    db.flush()
    return sh


def _saldos(db, company_id, product_id) -> dict:
    filas = db.execute(select(InventoryBalance).where(
        InventoryBalance.company_id == company_id,
        InventoryBalance.product_id == product_id)).scalars().all()
    return {(f.location_id, f.state): Decimal(str(f.qty_on_hand)) for f in filas if f.qty_on_hand}


# =========================================================================== #
# La compuerta del ¶103
# =========================================================================== #
def test_no_se_despacha_sin_factura_emitida(mundo):
    """¶103: «Pedido preparado + Pedido confirmado + **Factura emitida**».

    La factura está generada pero no emitida: el ¶95 y el ¶97 son dos actos.
    """
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo)
        # Con la factura solo generada el pedido está en `READY_FOR_BILLING` y
        # el despacho ni siquiera se crea: el ¶101 dice «el pedido **facturado**
        # pasa a despacho».
        with pytest.raises(ConflictError) as sin_estado:
            _despacho(db, mundo, e)
        assert sin_estado.value.code == "ORDER_NOT_SHIPPABLE"
        db.rollback()

        # Y aunque alguien pusiera el estado a mano, la compuerta mira la
        # factura: el ¶95 la genera y el ¶97 la emite, y el ¶103 exige la emitida.
        pedido = db.get(SalesOrder, str(e["pedido"].id))
        pedido.status = "INVOICED"
        db.flush()
        sh = _despacho(db, mundo, e)
        with pytest.raises(ConflictError) as exc:
            sales.validate_shipment(db, shipment=sh, actor="despachador")
        assert exc.value.code == "DISPATCH_NOT_INVOICED"
    finally:
        db.close()


def test_no_se_despacha_sin_confirmacion_independiente(mundo):
    db = mundo.factory()
    try:
        marca = uuid4().hex[:8]
        from app.modules.master_data.models import Party

        p = Party(company_id=mundo.company_a, code=f"CS-{marca}", name="C", roles=["CLIENTE"])
        db.add(p)
        db.flush()
        ped = SalesOrder(company_id=mundo.company_a, code=f"OVS-{marca}", customer_id=str(p.id),
                         warehouse_id=mundo.warehouse_a, currency="VED", status="INVOICED")
        db.add(ped)
        db.commit()
        sh = sales.create_shipment(db, company_id=mundo.company_a, code=f"SHS-{marca}",
                                   order_id=str(ped.id), origin_warehouse_id=mundo.warehouse_a,
                                   lines=[], actor="qa")
        sh.destination, sh.transport = "Caracas", "X"
        db.flush()
        with pytest.raises(ConflictError) as exc:
            sales.validate_shipment(db, shipment=sh, actor="qa")
        assert exc.value.code == "DISPATCH_NOT_CONFIRMED"
    finally:
        db.close()


def test_hay_que_decir_a_donde_va_y_quien_se_la_lleva(mundo):
    """¶105: «se entrega al transportista, cliente o responsable del traslado»."""
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo)
        _emitir(db, mundo, e)
        sh = _despacho(db, mundo, e, destino="", transporte="")
        with pytest.raises(KontrolError) as exc:
            sales.validate_shipment(db, shipment=sh, actor="despachador")
        assert exc.value.code == "DISPATCH_TRANSPORT_REQUIRED"
    finally:
        db.close()


def test_un_requisito_regulatorio_faltante_bloquea_la_salida(mundo):
    """El módulo regulatorio ya sabía decidir; hasta ahora nadie le preguntaba."""
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo)
        _emitir(db, mundo, e)
        reg.create_profile(db, company_id=mundo.company_a, operation="DESPACHO",
                           product_id=e["prod"], required_documents=["SICA"], actor="qa")
        db.commit()
        sh = _despacho(db, mundo, e)
        with pytest.raises(ConflictError) as exc:
            sales.validate_shipment(db, shipment=sh, actor="despachador")
        assert exc.value.code == "DISPATCH_REGULATORY_BLOCKED"
        db.rollback()
        assert db.get(SalesOrder, str(e["pedido"].id)).status == "INVOICED", \
            "el pedido salió sin su permiso"
    finally:
        db.close()


def test_un_requisito_vencido_tambien_bloquea(mundo):
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo)
        _emitir(db, mundo, e)
        reg.create_profile(db, company_id=mundo.company_a, operation="DESPACHO",
                           product_id=e["prod"], required_documents=["SIGESAI"], actor="qa")
        reg.register_official_document(db, company_id=mundo.company_a, kind="SIGESAI",
                                       number=f"SG-{uuid4().hex[:6]}",
                                       issued_at=hoy_de_negocio() - timedelta(days=400),
                                       expires_at=hoy_de_negocio() - timedelta(days=1), actor="qa")
        db.commit()
        sh = _despacho(db, mundo, e)
        with pytest.raises(ConflictError) as exc:
            sales.validate_shipment(db, shipment=sh, actor="despachador")
        assert exc.value.code == "DISPATCH_REGULATORY_BLOCKED"
    finally:
        db.close()


def test_cada_requisito_se_evalua_por_separado(mundo):
    """Tener SICA no exime de SIGESAI: son concurrentes, no alternativos."""
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo)
        _emitir(db, mundo, e)
        reg.create_profile(db, company_id=mundo.company_a, operation="DESPACHO",
                           product_id=e["prod"], required_documents=["SICA", "SIGESAI"], actor="qa")
        reg.register_official_document(db, company_id=mundo.company_a, kind="SICA",
                                       number=f"SC-{uuid4().hex[:6]}",
                                       expires_at=hoy_de_negocio() + timedelta(days=200), actor="qa")
        db.commit()
        sh = _despacho(db, mundo, e)
        with pytest.raises(ConflictError) as exc:
            sales.validate_shipment(db, shipment=sh, actor="despachador")
        assert exc.value.code == "DISPATCH_REGULATORY_BLOCKED"
    finally:
        db.close()


# =========================================================================== #
# La salida física
# =========================================================================== #
def test_la_cadena_completa_despacha_y_la_mercancia_sale(mundo):
    """¶104-107: se autoriza, sale con su factura y se registra la salida."""
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo, cantidad=10)
        factura = _emitir(db, mundo, e)
        sh = _despacho(db, mundo, e)
        sales.validate_shipment(db, shipment=sh, actor="despachador")
        assert sh.status == "READY" and sh.regulatory_status == "CLEARED"
        assert str(sh.invoice_id) == str(factura.id), "el despacho no sabe con qué factura sale"
        sales.confirm_shipment(db, shipment=sh, actor="despachador")
        db.commit()

        assert sh.status == "SHIPPED" and sh.dispatched_at is not None
        assert db.get(SalesOrder, str(e["pedido"].id)).status == "SHIPPED"
        saldos = _saldos(db, mundo.company_a, e["prod"])
        assert saldos.get((e["area"], "DESPACHADO")) == Decimal("10"), "la mercancía no salió"
        assert (e["area"], "PREPARADO") not in saldos, "quedó preparada después de salir"
        reservas = inv.order_reservations(db, company_id=mundo.company_a,
                                          order_id=str(e["pedido"].id), only_active=False)
        assert all(r.status == "FULFILLED" for r in reservas), "la salida no consumió la reserva"
    finally:
        db.close()


def test_la_salida_es_en_cantidad_base_y_desde_preparado(mundo):
    """Los dos defectos que este ciclo encontró en la salida física.

    Despachar dos cajas de doce saca **veinticuatro** unidades, no dos. Y las
    saca de `PREPARADO`, que es donde la Spec 032 dejó la mercancía, no de
    `DISPONIBLE`, que ya no las tiene.
    """
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo, cantidad=24, quantity=2, factor=12)
        _emitir(db, mundo, e)
        sh = _despacho(db, mundo, e)
        sales.validate_shipment(db, shipment=sh, actor="despachador")
        sales.confirm_shipment(db, shipment=sh, actor="despachador")
        db.commit()
        saldos = _saldos(db, mundo.company_a, e["prod"])
        assert saldos.get((e["area"], "DESPACHADO")) == Decimal("24"), \
            f"salieron {saldos.get((e['area'], 'DESPACHADO'))} en vez de 24"
    finally:
        db.close()


def test_despachar_dos_veces_no_saca_dos_veces(mundo):
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo, cantidad=5)
        _emitir(db, mundo, e)
        sh = _despacho(db, mundo, e)
        sales.validate_shipment(db, shipment=sh, actor="despachador")
        sales.confirm_shipment(db, shipment=sh, actor="despachador")
        db.commit()
        sales.confirm_shipment(db, shipment=sh, actor="despachador")
        db.commit()
        assert _saldos(db, mundo.company_a, e["prod"]).get((e["area"], "DESPACHADO")) == Decimal("5")
    finally:
        db.close()


def test_un_pedido_no_se_despacha_dos_veces(mundo):
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo, cantidad=5)
        _emitir(db, mundo, e)
        _despacho(db, mundo, e)
        db.commit()
        # Dos guardias, y las dos hacen falta. El servicio da un conflicto
        # legible al que pulsa dos veces:
        with pytest.raises(ConflictError) as exc:
            _despacho(db, mundo, e)
        assert exc.value.code == "ORDER_ALREADY_SHIPPED"
        db.rollback()

        # ...y quien de verdad lo impide es la base, que es lo único que
        # resiste a dos transacciones simultáneas. Se salta el servicio a
        # propósito para comprobar que el índice existe y no es decorativo.
        pedido = db.get(SalesOrder, str(e["pedido"].id))
        db.add(Shipment(company_id=mundo.company_a, code=f"SHX-{uuid4().hex[:8]}",
                        order_id=str(pedido.id), origin_warehouse_id=mundo.warehouse_a,
                        status="DRAFT", validation_status="PENDING"))
        with pytest.raises(IntegrityError) as dup:
            db.flush()
        assert "uq_shipments_live_order" in str(dup.value.orig)
    finally:
        db.close()


def test_no_se_despacha_bajo_otra_empresa(mundo):
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo)
        _emitir(db, mundo, e)
        sh = _despacho(db, mundo, e)
        db.commit()
        with pytest.raises(NotFoundError):
            sales.get_plan(db, company_id=mundo.company_b, plan_id=str(e["plan"].id))
        ajeno = db.get(Shipment, str(sh.id))
        assert str(ajeno.company_id) == mundo.company_a
    finally:
        db.close()


def test_solo_se_despacha_lo_facturado(mundo):
    """La deuda que este tramo dejó anotada: `CONFIRMED → SHIPPED` sin factura."""
    from app.modules.sales import service as s

    assert {k for k, v in s.ORDER_TRANSITIONS.items() if "SHIPPED" in v} == {"INVOICED"}, \
        "algún estado sin factura sigue pudiendo despachar"


def test_dos_despachadores_no_sacan_la_mercancia_dos_veces(mundo):
    """P0 sobre PostgreSQL real: una salida física, un efecto."""
    import threading

    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo, cantidad=8)
        _emitir(db, mundo, e)
        sh = _despacho(db, mundo, e)
        sales.validate_shipment(db, shipment=sh, actor="despachador")
        db.commit()
        sh_id, prod, area = str(sh.id), e["prod"], e["area"]
    finally:
        db.close()

    exitos: list[int] = []
    choques: list[str] = []

    def _worker() -> None:
        s = mundo.factory()
        try:
            envio = s.get(Shipment, sh_id)
            sales.confirm_shipment(s, shipment=envio, actor="despachador")
            s.commit()
            exitos.append(1)
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
        salido = _saldos(db, mundo.company_a, prod).get((area, "DESPACHADO"), Decimal(0))
        assert salido == Decimal("8"), f"salieron {salido} de 8: {exitos} {choques}"
    finally:
        db.close()


# =========================================================================== #
# Lo que sale es lo que se consolidó (§21 del ciclo)
# =========================================================================== #
def test_el_despacho_sin_lineas_toma_las_que_se_consolidaron(mundo):
    """Nadie escribe la cantidad que sale: sale lo que hay en el Área.

    Es el caso P0 del tramo —dos cajas de doce— y la razón de que la pantalla no
    tenga campo de cantidad. Escribir «2» aquí sacaría dos unidades del almacén
    y dejaría veintidós preparadas para siempre.
    """
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo, cantidad=24, quantity=2, factor=12)
        _emitir(db, mundo, e)
        sh = sales.create_shipment(db, company_id=mundo.company_a,
                                   code=f"SHA-{uuid4().hex[:8]}",
                                   order_id=str(e["pedido"].id),
                                   destination="Maracay", transport="Cliente",
                                   actor="despachador")
        db.flush()
        lineas = db.execute(select(ShipmentLine).where(
            ShipmentLine.shipment_id == str(sh.id))).scalars().all()
        assert len(lineas) == 1
        assert Decimal(str(lineas[0].base_quantity)) == Decimal("24"), "salió en cajas, no en unidades"
        # Sin presentación colgada: la cifra es de unidades base y decir lo
        # contrario es el error que este ciclo vino a corregir.
        assert lineas[0].presentation_id is None
        assert lineas[0].conversion_factor_snapshot is None

        # Y el almacén de origen tampoco se escribe: es el del pedido.
        assert str(sh.origin_warehouse_id) == mundo.warehouse_a

        sales.validate_shipment(db, shipment=sh, actor="despachador")
        sales.confirm_shipment(db, shipment=sh, actor="despachador")
        db.commit()
        assert _saldos(db, mundo.company_a, e["prod"]).get((e["area"], "DESPACHADO")) == Decimal("24")
    finally:
        db.close()


def test_no_se_despacha_con_el_vehiculo_de_otra_empresa(mundo):
    """El transporte sale de un maestro con dueño, y el dueño se comprueba."""
    db = mundo.factory()
    try:
        ajeno = reg.create_vehicle(db, company_id=mundo.company_b, plate=f"XX-{uuid4().hex[:4]}",
                                   actor="qa")
        db.flush()
        e = _hasta_facturado(db, mundo)
        _emitir(db, mundo, e)
        with pytest.raises(NotFoundError) as exc:
            sales.create_shipment(db, company_id=mundo.company_a, code=f"SHV-{uuid4().hex[:8]}",
                                  order_id=str(e["pedido"].id), destination="Valencia",
                                  transport="Transportista", vehicle_id=str(ajeno.id),
                                  actor="despachador")
        assert exc.value.code == "VEHICLE_NOT_FOUND"
    finally:
        db.close()


def test_la_cola_de_despacho_solo_trae_pedidos_facturados(mundo):
    """La cola no es «todo lo que hay»: es lo que el ¶101 deja pasar."""
    db = mundo.factory()
    try:
        pendiente = _hasta_facturado(db, mundo, cantidad=4)   # factura generada, no emitida
        listo = _hasta_facturado(db, mundo, cantidad=6)
        _emitir(db, mundo, listo)
        db.commit()

        cola = {f["order_id"]: f for f in sales.dispatch_queue(db, company_id=mundo.company_a)}
        assert str(listo["pedido"].id) in cola
        assert str(pendiente["pedido"].id) not in cola, "un pedido sin factura emitida entró en la cola"
        fila = cola[str(listo["pedido"].id)]
        assert fila["invoice_status"] == "EMITTED"
        assert fila["shipment_id"] is None

        # Y la empresa B no ve la cola de A.
        assert sales.dispatch_queue(db, company_id=mundo.company_b) == []

        sh = _despacho(db, mundo, listo)
        db.commit()
        fila = next(f for f in sales.dispatch_queue(db, company_id=mundo.company_a)
                    if f["order_id"] == str(listo["pedido"].id))
        assert fila["shipment_status"] == "DRAFT"

        sales.validate_shipment(db, shipment=sh, actor="despachador")
        sales.confirm_shipment(db, shipment=sh, actor="despachador")
        db.commit()
        # Despachado, sale de la cola: ya no espera nada.
        assert str(listo["pedido"].id) not in {
            f["order_id"] for f in sales.dispatch_queue(db, company_id=mundo.company_a)}
        detalle = sales.order_dispatch_dict(db, company_id=mundo.company_a,
                                            order_id=str(listo["pedido"].id))
        assert detalle["order_status"] == "SHIPPED"
        assert detalle["shipment"]["dispatched_at"] is not None
        assert detalle["shipment"]["regulatory_status"] == "CLEARED"
    finally:
        db.close()
