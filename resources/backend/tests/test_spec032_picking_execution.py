"""Spec 032 · preparación física y consolidación.

Lo que estas pruebas defienden es la frontera y la aritmética. La frontera: la
032 ejecuta, no confirma —el control independiente es de la 033— y no despacha,
así que **nada sale del almacén aquí**. La aritmética: cuando la mercancía deja
`DISPONIBLE`, el contador de reservado tiene que bajar con ella, o el mismo
compromiso se resta dos veces y ventas deja de poder vender lo que sí tiene.

Multiempresa sobre PostgreSQL real, con el arnés `mundo`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.inventory import service as inv
from app.modules.inventory.models import InventoryBalance, InventoryMovement, Reservation
from app.modules.organization.models import WarehouseLocation
from app.modules.sales import service as sales
from app.modules.sales.models import PickList, PickListLine, SalesOrder, SalesOrderLine

pytest_plugins = ("tests.conftest_multicompany",)


# --------------------------------------------------------------------------- #
# Un pedido liberado, planificado y confirmado, listo para recogerse
# --------------------------------------------------------------------------- #
def _producto(db, company_id, marca) -> str:
    from app.modules.master_data.models import CatalogItem

    item = CatalogItem(company_id=company_id, code=f"PX-{marca}", name=f"Artículo {marca}",
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


def _entrada(db, *, company_id, warehouse_id, product_id, qty):
    tipo = inv._get_movement_type_by_code(db, company_id, "ENTRADA_RECEPCION")
    return inv.record_movement(db, company_id=company_id, warehouse_id=warehouse_id,
                               product_id=product_id, movement_type_id=str(tipo.id),
                               quantity=qty, actor="qa")


def _pedido(db, *, company_id, warehouse_id, marca) -> SalesOrder:
    from app.modules.master_data.models import Party

    p = Party(company_id=company_id, code=f"CLX-{marca}", name=f"Cliente {marca}", roles=["CLIENTE"])
    db.add(p)
    db.flush()
    ahora = datetime.now(UTC)
    o = SalesOrder(company_id=company_id, code=f"OVX-{marca}", customer_id=str(p.id),
                   warehouse_id=warehouse_id, currency="VED", status="RELEASED",
                   submitted_at=ahora, released_at=ahora)
    db.add(o)
    db.flush()
    return o


def _linea(db, *, order, product_id, base, quantity=None, factor=None, lot_id=None):
    ln = SalesOrderLine(order_id=str(order.id), product_id=product_id,
                        quantity=Decimal(str(quantity if quantity is not None else base)),
                        unit_price=Decimal("10"), needs_inventory=True,
                        conversion_factor_snapshot=Decimal(str(factor)) if factor else None,
                        base_quantity=Decimal(str(base)))
    db.add(ln)
    db.flush()
    r = inv.reserve(db, company_id=str(order.company_id), source_document=order.code,
                    product_id=product_id, warehouse_id=str(order.warehouse_id),
                    quantity=float(ln.quantity), lot_id=lot_id, source_type="SALES_ORDER",
                    source_order_id=str(order.id), source_line_id=str(ln.id),
                    base_quantity=Decimal(str(base)), actor="qa")
    db.flush()
    return ln, r


def _plan_confirmado(db, *, company_id, warehouse_id, order, linea, reparto) -> PickList:
    """Plan con las asignaciones de `reparto` = [(ubicación, cantidad), …]."""
    plan = PickList(company_id=company_id, code=f"PLX-{uuid4().hex[:8]}", order_id=str(order.id),
                    warehouse_id=warehouse_id, status="DRAFT")
    db.add(plan)
    db.flush()
    for loc, qty in reparto:
        if qty:
            sales.allocate(db, company_id=company_id, plan_id=str(plan.id),
                           order_line_id=str(linea.id), location_id=loc, quantity=qty, actor="qa")
    sales.confirm_plan(db, company_id=company_id, plan_id=str(plan.id), actor="qa")
    db.flush()
    return plan


def _escenario(db, mundo, *, total=100, reparto=(40, 30), reservado=70, factor=None, quantity=None):
    """Existencia repartida en dos ubicaciones y un plan confirmado sobre ella."""
    marca = uuid4().hex[:8]
    prod = _producto(db, mundo.company_a, marca)
    l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"A1-{marca}", sequence=1)
    l2 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"B2-{marca}", sequence=2)
    area = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"CONF-{marca}", sequence=99)
    _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod, qty=total)
    for loc, qty in ((l1, reparto[0]), (l2, reparto[1])):
        if qty:
            inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                        product_id=prod, target_location_id=loc, quantity=qty, actor="qa")
    ped = _pedido(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, marca=marca)
    ln, res = _linea(db, order=ped, product_id=prod, base=reservado, quantity=quantity, factor=factor)
    plan = _plan_confirmado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                            order=ped, linea=ln, reparto=((l1, reparto[0]), (l2, reparto[1])))
    db.commit()
    return {"prod": prod, "l1": l1, "l2": l2, "area": area, "pedido": ped, "linea": ln,
            "reserva": res, "plan": plan}


def _paradas(db, plan) -> list[PickListLine]:
    return sorted((ln for ln in sales._lineas_del_plan(db, plan) if ln.location_id is not None),
                  key=lambda ln: (ln.sequence or 0, str(ln.id)))


def _saldos(db, company_id, product_id) -> dict[tuple[str | None, str], Decimal]:
    filas = db.execute(select(InventoryBalance).where(
        InventoryBalance.company_id == company_id,
        InventoryBalance.product_id == product_id)).scalars().all()
    return {(f.location_id, f.state): Decimal(str(f.qty_on_hand)) for f in filas if f.qty_on_hand}


def _fisico(db, company_id, product_id) -> Decimal:
    return Decimal(str(db.execute(select(func.coalesce(func.sum(InventoryBalance.qty_on_hand), 0))
                                  .where(InventoryBalance.company_id == company_id,
                                         InventoryBalance.product_id == product_id)).scalar() or 0))


def _reservado(db, company_id, product_id) -> Decimal:
    return Decimal(str(db.execute(select(func.coalesce(func.sum(InventoryBalance.qty_reserved), 0))
                                  .where(InventoryBalance.company_id == company_id,
                                         InventoryBalance.product_id == product_id)).scalar() or 0))


def _disponible(db, company_id, warehouse_id, product_id) -> Decimal:
    ancla = inv.lock_balance(db, company_id=company_id, warehouse_id=warehouse_id, product_id=product_id)
    return inv.available_under_lock(db, ancla)


# =========================================================================== #
# El caso canónico de la aritmética
# =========================================================================== #
def test_recoger_no_resta_dos_veces_el_mismo_compromiso(mundo):
    """Existencia 100, reservado 30, disponible 70. Se recogen las 30.

    Si al salir de `DISPONIBLE` el contador se quedara en 30, el disponible
    pasaría a `70 − 30 = 40` y ventas dejaría de poder vender 30 unidades que sí
    tiene. El contador cuenta «comprometidas y **aún no extraídas**» (`D0-03`
    §0): extraer es dejar de estarlo.
    """
    db = mundo.factory()
    try:
        e = _escenario(db, mundo, total=100, reparto=(30, 0), reservado=30)
        assert _disponible(db, mundo.company_a, mundo.warehouse_a, e["prod"]) == Decimal("70")
        assert _reservado(db, mundo.company_a, e["prod"]) == Decimal("30")

        parada = _paradas(db, e["plan"])[0]
        sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                           line_id=str(parada.id), quantity=30, actor="qa")
        db.commit()

        assert _reservado(db, mundo.company_a, e["prod"]) == Decimal("0"), \
            "el contador siguió reservando mercancía ya extraída"
        assert _disponible(db, mundo.company_a, mundo.warehouse_a, e["prod"]) == Decimal("70"), \
            "el mismo compromiso se restó dos veces"
        assert _fisico(db, mundo.company_a, e["prod"]) == Decimal("100"), \
            "recoger sacó mercancía del almacén: eso es del despacho"
        saldos = _saldos(db, mundo.company_a, e["prod"])
        assert saldos[(e["l1"], "PICKING")] == Decimal("30")
    finally:
        db.close()


def test_despachar_no_borra_el_compromiso_del_otro_pedido(mundo):
    """Delta B. Dos pedidos sobre el mismo producto; el primero recoge y despacha.

    Si el despacho volviera a restar del contador lo que el picking ya restó, el
    compromiso del segundo pedido desaparecería y su mercancía se vendería otra
    vez.
    """
    db = mundo.factory()
    try:
        marca = uuid4().hex[:8]
        prod = _producto(db, mundo.company_a, marca)
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L1-{marca}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod, qty=100)
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=100, actor="qa")
        p1 = _pedido(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, marca=f"{marca}A")
        p2 = _pedido(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, marca=f"{marca}B")
        li1, r1 = _linea(db, order=p1, product_id=prod, base=30)
        li2, r2 = _linea(db, order=p2, product_id=prod, base=40)
        plan1 = _plan_confirmado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                                 order=p1, linea=li1, reparto=((l1, 30),))
        db.commit()
        assert _reservado(db, mundo.company_a, prod) == Decimal("70")

        parada = _paradas(db, plan1)[0]
        sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(plan1.id),
                           line_id=str(parada.id), quantity=30, actor="qa")
        db.commit()
        assert _reservado(db, mundo.company_a, prod) == Decimal("40"), "solo queda lo no extraído"

        inv.fulfill_reservation(db, reservation=db.get(Reservation, str(r1.id)), actor="qa")
        db.commit()
        assert _reservado(db, mundo.company_a, prod) == Decimal("40"), \
            "el despacho volvió a restar lo ya extraído y borró el compromiso del otro pedido"
    finally:
        db.close()


# =========================================================================== #
# Camino feliz completo
# =========================================================================== #
def test_recorrido_completo_y_consolidacion(mundo):
    """¶33-41 y ¶55-59: se recorre, se recoge, se concentra y se traslada."""
    db = mundo.factory()
    try:
        e = _escenario(db, mundo)
        for parada in _paradas(db, e["plan"]):
            sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                               line_id=str(parada.id), quantity=parada.base_quantity, actor="qa")
        db.commit()
        prep = sales.preparation_dict(db, db.get(PickList, str(e["plan"].id)))
        assert prep["route_complete"] is True and prep["has_discrepancy"] is False

        sales.consolidate(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                          location_id=e["area"], actor="qa")
        db.commit()

        plan = db.get(PickList, str(e["plan"].id))
        assert plan.status == "CLOSED"
        assert str(plan.consolidation_location_id) == e["area"]
        assert db.get(SalesOrder, str(e["pedido"].id)).status == "PREPARED"
        saldos = _saldos(db, mundo.company_a, e["prod"])
        assert saldos[(e["area"], "PREPARADO")] == Decimal("70"), "el pedido no quedó concentrado"
        assert _fisico(db, mundo.company_a, e["prod"]) == Decimal("100"), "nada debía salir del almacén"
    finally:
        db.close()


# =========================================================================== #
# Discrepancias — el punto de decisión del ¶43
# =========================================================================== #
def test_recoger_de_menos_exige_motivo_y_libera_la_diferencia(mundo):
    """¶47 y `POL-D0-002` §8: «libera la diferencia y genera incidencia»."""
    db = mundo.factory()
    try:
        e = _escenario(db, mundo)
        parada = _paradas(db, e["plan"])[0]           # 40 planificadas en L1
        with pytest.raises(KontrolError) as sin_motivo:
            sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                               line_id=str(parada.id), quantity=35, actor="qa")
        assert sin_motivo.value.code == "PICKING_DISCREPANCY_REASON_REQUIRED"
        db.rollback()

        reservado_antes = _reservado(db, mundo.company_a, e["prod"])
        sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                           line_id=str(parada.id), quantity=35,
                           discrepancy_kind="CANTIDAD_INSUFICIENTE",
                           discrepancy_note="faltaban cinco en el rack", actor="qa")
        db.commit()

        linea = db.get(PickListLine, str(parada.id))
        assert Decimal(str(linea.base_quantity)) == Decimal("40"), "se perdió lo planificado"
        assert Decimal(str(linea.picked_base_quantity)) == Decimal("35")
        assert linea.discrepancy_kind == "CANTIDAD_INSUFICIENTE"
        # 35 extraídas + 5 liberadas = 40 salen del contador.
        assert _reservado(db, mundo.company_a, e["prod"]) == reservado_antes - Decimal("40")
        assert db.get(Reservation, str(e["reserva"].id)).release_reason == "PICKING_SHORTAGE"
        prep = sales.preparation_dict(db, db.get(PickList, str(e["plan"].id)))
        assert prep["has_discrepancy"] is True
        assert Decimal(prep["picking"][0]["difference"]) == -5
    finally:
        db.close()


def test_no_se_puede_recoger_de_mas(mundo):
    """Sin autoridad que lo permita, y `R-D0-10-7` deniega por defecto."""
    db = mundo.factory()
    try:
        e = _escenario(db, mundo)
        parada = _paradas(db, e["plan"])[0]
        with pytest.raises(ConflictError) as exc:
            sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                               line_id=str(parada.id), quantity=45, actor="qa")
        assert exc.value.code == "PICKING_OVER_PICK"
    finally:
        db.close()


def test_el_motivo_solo_puede_ser_uno_de_los_cinco_del_proceso(mundo):
    db = mundo.factory()
    try:
        e = _escenario(db, mundo)
        parada = _paradas(db, e["plan"])[0]
        with pytest.raises(KontrolError) as exc:
            sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                               line_id=str(parada.id), quantity=35,
                               discrepancy_kind="PORQUE_SI", actor="qa")
        assert exc.value.code == "PICKING_DISCREPANCY_REASON_REQUIRED"
        db.rollback()
        with pytest.raises(KontrolError) as sobra:
            sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                               line_id=str(parada.id), quantity=40,
                               discrepancy_kind="MERCANCIA_DANADA", actor="qa")
        assert sobra.value.code == "PICKING_DISCREPANCY_WITHOUT_DIFFERENCE"
    finally:
        db.close()


def test_recoger_cero_es_explicito_y_no_cierra_nada(mundo):
    """No hay «completado» silencioso: cero recogido es cero, con su motivo."""
    db = mundo.factory()
    try:
        e = _escenario(db, mundo)
        parada = _paradas(db, e["plan"])[0]
        sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                           line_id=str(parada.id), quantity=0,
                           discrepancy_kind="PRODUCTO_NO_LOCALIZADO", actor="qa")
        db.commit()
        linea = db.get(PickListLine, str(parada.id))
        assert Decimal(str(linea.picked_base_quantity)) == 0
        assert db.get(PickList, str(e["plan"].id)).status == "CONFIRMED", "cero recogido cerró el plan"
        saldos = _saldos(db, mundo.company_a, e["prod"])
        assert (e["l1"], "PICKING") not in saldos, "se movió mercancía que nadie recogió"
    finally:
        db.close()


def test_no_se_admite_cantidad_negativa(mundo):
    db = mundo.factory()
    try:
        e = _escenario(db, mundo)
        parada = _paradas(db, e["plan"])[0]
        with pytest.raises(KontrolError) as exc:
            sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                               line_id=str(parada.id), quantity=-1, actor="qa")
        assert exc.value.code == "PICKING_QUANTITY_INVALID"
    finally:
        db.close()


# =========================================================================== #
# Idempotencia y fronteras
# =========================================================================== #
def test_una_parada_se_recoge_una_vez(mundo):
    db = mundo.factory()
    try:
        e = _escenario(db, mundo)
        parada = _paradas(db, e["plan"])[0]
        sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                           line_id=str(parada.id), quantity=40, actor="qa")
        db.commit()
        movs = db.execute(select(func.count(InventoryMovement.id)).where(
            InventoryMovement.company_id == mundo.company_a,
            InventoryMovement.product_id == e["prod"])).scalar()
        with pytest.raises(ConflictError) as exc:
            sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                               line_id=str(parada.id), quantity=40, actor="qa")
        assert exc.value.code == "PICKING_ALREADY_PICKED"
        db.rollback()
        assert db.execute(select(func.count(InventoryMovement.id)).where(
            InventoryMovement.company_id == mundo.company_a,
            InventoryMovement.product_id == e["prod"])).scalar() == movs
    finally:
        db.close()


def test_no_se_consolida_un_recorrido_a_medias(mundo):
    """¶41: se termina cuando se han recorrido **todas** las posiciones."""
    db = mundo.factory()
    try:
        e = _escenario(db, mundo)
        parada = _paradas(db, e["plan"])[0]
        sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                           line_id=str(parada.id), quantity=40, actor="qa")
        db.commit()
        with pytest.raises(ConflictError) as exc:
            sales.consolidate(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                              location_id=e["area"], actor="qa")
        assert exc.value.code == "PICKING_ROUTE_INCOMPLETE"
        db.rollback()
        assert db.get(SalesOrder, str(e["pedido"].id)).status == "PREPARING"
    finally:
        db.close()


def test_se_consolida_con_diferencia_y_no_se_certifica_nada(mundo):
    """¶45: el pedido continúa al área de confirmación. Comparar es de la 033."""
    db = mundo.factory()
    try:
        e = _escenario(db, mundo)
        paradas = _paradas(db, e["plan"])
        sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                           line_id=str(paradas[0].id), quantity=35,
                           discrepancy_kind="DIFERENCIA_SISTEMA_FISICO", actor="qa")
        sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                           line_id=str(paradas[1].id), quantity=30, actor="qa")
        sales.consolidate(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                          location_id=e["area"], actor="qa")
        db.commit()

        prep = sales.preparation_dict(db, db.get(PickList, str(e["plan"].id)))
        assert prep["has_discrepancy"] is True
        assert Decimal(prep["demand"][0]["prepared_base_quantity"]) == Decimal("65"), \
            "lo preparado se tomó de lo planificado y no de lo recogido"
        assert db.get(SalesOrder, str(e["pedido"].id)).status == "PREPARED"
        saldos = _saldos(db, mundo.company_a, e["prod"])
        assert saldos[(e["area"], "PREPARADO")] == Decimal("65")
    finally:
        db.close()


def test_la_caja_de_doce_llega_preparada_en_veinticuatro(mundo):
    db = mundo.factory()
    try:
        e = _escenario(db, mundo, total=50, reparto=(24, 0), reservado=24, quantity=2, factor=12)
        parada = _paradas(db, e["plan"])[0]
        sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                           line_id=str(parada.id), quantity=24, actor="qa")
        sales.consolidate(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                          location_id=e["area"], actor="qa")
        db.commit()
        prep = sales.preparation_dict(db, db.get(PickList, str(e["plan"].id)))
        assert Decimal(prep["demand"][0]["prepared_base_quantity"]) == Decimal("24")
        saldos = _saldos(db, mundo.company_a, e["prod"])
        assert saldos[(e["area"], "PREPARADO")] == Decimal("24")
    finally:
        db.close()


def test_no_se_prepara_un_plan_que_no_esta_confirmado(mundo):
    db = mundo.factory()
    try:
        e = _escenario(db, mundo)
        sales.cancel_plan(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                          reason="prueba", actor="qa")
        db.commit()
        parada = _paradas(db, e["plan"])[0]
        with pytest.raises(ConflictError) as exc:
            sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                               line_id=str(parada.id), quantity=40, actor="qa")
        assert exc.value.code == "PICKING_PLAN_NOT_EXECUTABLE"
    finally:
        db.close()


def test_no_se_prepara_bajo_otra_empresa(mundo):
    db = mundo.factory()
    try:
        e = _escenario(db, mundo)
        parada = _paradas(db, e["plan"])[0]
        with pytest.raises(NotFoundError):
            sales.execute_pick(db, company_id=mundo.company_b, plan_id=str(e["plan"].id),
                               line_id=str(parada.id), quantity=40, actor="qa")
    finally:
        db.close()


def test_el_area_de_confirmacion_es_del_mismo_almacen(mundo):
    db = mundo.factory()
    try:
        e = _escenario(db, mundo)
        ajena = _ubicacion(db, mundo.company_b, mundo.warehouse_b, f"AJ-{uuid4().hex[:6]}")
        db.commit()
        for parada in _paradas(db, e["plan"]):
            sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                               line_id=str(parada.id), quantity=parada.base_quantity, actor="qa")
        db.commit()
        with pytest.raises((NotFoundError, ConflictError)):
            sales.consolidate(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                              location_id=ajena, actor="qa")
    finally:
        db.close()


def test_dos_operarios_no_recogen_la_misma_parada(mundo):
    """P0 sobre PostgreSQL real: una parada, un efecto físico."""
    import threading

    db = mundo.factory()
    try:
        e = _escenario(db, mundo)
        plan_id, prod = str(e["plan"].id), e["prod"]
        parada_id = str(_paradas(db, e["plan"])[0].id)
    finally:
        db.close()

    exitos: list[int] = []
    choques: list[str] = []

    def _worker() -> None:
        s = mundo.factory()
        try:
            sales.execute_pick(s, company_id=mundo.company_a, plan_id=plan_id,
                               line_id=parada_id, quantity=40, actor="qa")
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
        assert len(exitos) == 1, f"dos operarios recogieron la misma parada: {exitos} {choques}"
        total = sum(v for (_, st), v in _saldos(db, mundo.company_a, prod).items() if st == "PICKING")
        assert total == Decimal("40"), f"se extrajo dos veces: {total}"
        assert _fisico(db, mundo.company_a, prod) == Decimal("100")
    finally:
        db.close()


def test_no_se_retira_un_plan_cuya_preparacion_ya_empezo(mundo):
    """`R-D0-15-16` dejó a esta Spec definir el primer efecto irreversible.

    Es la primera recogida: después hay mercancía en `PICKING` y el contador ya
    bajó. Retirar el plan la dejaría en un estado de custodia sin dueño, porque
    devolverla a `DISPONIBLE` exigiría una arista que nadie declaró.
    """
    db = mundo.factory()
    try:
        e = _escenario(db, mundo)
        parada = _paradas(db, e["plan"])[0]
        sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                           line_id=str(parada.id), quantity=40, actor="qa")
        db.commit()
        with pytest.raises(ConflictError) as exc:
            sales.cancel_plan(db, company_id=mundo.company_a, plan_id=str(e["plan"].id),
                              reason="me arrepentí", actor="qa")
        assert exc.value.code == "PICKING_ALREADY_STARTED"
        db.rollback()
        assert db.get(PickList, str(e["plan"].id)).status == "CONFIRMED"
        saldos = _saldos(db, mundo.company_a, e["prod"])
        assert saldos[(e["l1"], "PICKING")] == Decimal("40"), "la mercancía extraída se perdió"
    finally:
        db.close()
