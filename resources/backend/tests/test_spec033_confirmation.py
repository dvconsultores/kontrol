"""Spec 033 · confirmación independiente del pedido.

Lo que estas pruebas defienden es que el control sea un control. Que compare
contra el **pedido** y no contra la preparación —comparar la preparación consigo
misma no verifica nada—, que lo haga alguien distinto de quien preparó, que no
toque una sola unidad de inventario, y que un pedido no conforme no pueda llegar
a facturación por ningún camino.

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
from app.modules.organization.models import Company, WarehouseLocation
from app.modules.sales import service as sales
from app.modules.sales.models import (
    OrderConfirmation,
    PickList,
    SalesOrder,
    SalesOrderLine,
)

pytest_plugins = ("tests.conftest_multicompany",)


# --------------------------------------------------------------------------- #
# Un pedido preparado y consolidado, listo para el control
# --------------------------------------------------------------------------- #
def _producto(db, company_id, marca) -> str:
    from app.modules.master_data.models import CatalogItem

    item = CatalogItem(company_id=company_id, code=f"PC-{marca}", name=f"Artículo {marca}",
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

    p = Party(company_id=company_id, code=f"CLC-{marca}", name=f"Cliente {marca}", roles=["CLIENTE"])
    db.add(p)
    db.flush()
    ahora = datetime.now(UTC)
    o = SalesOrder(company_id=company_id, code=f"OVC-{marca}", customer_id=str(p.id),
                   warehouse_id=warehouse_id, currency="VED", status="RELEASED",
                   submitted_at=ahora, released_at=ahora)
    db.add(o)
    db.flush()
    return o


def _linea(db, *, order, product_id, base, quantity=None, factor=None):
    ln = SalesOrderLine(order_id=str(order.id), product_id=product_id,
                        quantity=Decimal(str(quantity if quantity is not None else base)),
                        unit_price=Decimal("10"), needs_inventory=True,
                        conversion_factor_snapshot=Decimal(str(factor)) if factor else None,
                        base_quantity=Decimal(str(base)))
    db.add(ln)
    db.flush()
    r = inv.reserve(db, company_id=str(order.company_id), source_document=order.code,
                    product_id=product_id, warehouse_id=str(order.warehouse_id),
                    quantity=float(ln.quantity), source_type="SALES_ORDER",
                    source_order_id=str(order.id), source_line_id=str(ln.id),
                    base_quantity=Decimal(str(base)), actor="qa")
    db.flush()
    return ln, r


def _preparado(db, mundo, *, requerido=70, recogido=None, picker="almacenista",
               quantity=None, factor=None):
    """Pedido `PREPARED` con su plan `CLOSED` en el Área de Confirmación."""
    marca = uuid4().hex[:8]
    prod = _producto(db, mundo.company_a, marca)
    l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"P1-{marca}", sequence=1)
    area = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"AC-{marca}", sequence=99)
    _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
             product_id=prod, qty=requerido + 50)
    inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                product_id=prod, target_location_id=l1, quantity=requerido + 50, actor="qa")
    ped = _pedido(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, marca=marca)
    ln, res = _linea(db, order=ped, product_id=prod, base=requerido, quantity=quantity, factor=factor)

    plan = PickList(company_id=mundo.company_a, code=f"PLC-{marca}", order_id=str(ped.id),
                    warehouse_id=mundo.warehouse_a, status="DRAFT")
    db.add(plan)
    db.flush()
    sales.allocate(db, company_id=mundo.company_a, plan_id=str(plan.id),
                   order_line_id=str(ln.id), location_id=l1, quantity=requerido, actor="qa")
    sales.confirm_plan(db, company_id=mundo.company_a, plan_id=str(plan.id), actor="planificador")
    parada = next(x for x in sales._lineas_del_plan(db, plan) if x.location_id)
    real = requerido if recogido is None else recogido
    sales.execute_pick(db, company_id=mundo.company_a, plan_id=str(plan.id),
                       line_id=str(parada.id), quantity=real,
                       discrepancy_kind=None if real == requerido else "CANTIDAD_INSUFICIENTE",
                       actor=picker)
    sales.consolidate(db, company_id=mundo.company_a, plan_id=str(plan.id),
                      location_id=area, actor=picker)
    db.commit()
    return {"prod": prod, "l1": l1, "area": area, "pedido": ped, "linea": ln, "reserva": res,
            "plan": plan, "requerido": Decimal(str(requerido)), "recogido": Decimal(str(real))}


def _conforme(e, **extra) -> list[dict]:
    return [{"order_line_id": str(e["linea"].id), "checked_base_quantity": e["requerido"], **extra}]


def _movimientos(db, company_id, product_id) -> int:
    return db.execute(select(func.count(InventoryMovement.id)).where(
        InventoryMovement.company_id == company_id,
        InventoryMovement.product_id == product_id)).scalar() or 0


def _saldos(db, company_id, product_id) -> dict:
    filas = db.execute(select(InventoryBalance).where(
        InventoryBalance.company_id == company_id,
        InventoryBalance.product_id == product_id)).scalars().all()
    return {(f.location_id, f.state): (Decimal(str(f.qty_on_hand)), Decimal(str(f.qty_reserved)))
            for f in filas}


# =========================================================================== #
# El camino conforme
# =========================================================================== #
def test_el_pedido_conforme_queda_formalmente_confirmado(mundo):
    """¶81 y `R-D0-12-4`: conforme → `CONFIRMED`, y eso habilita facturación."""
    db = mundo.factory()
    try:
        e = _preparado(db, mundo)
        antes = sales.billing_eligibility(db, company_id=mundo.company_a,
                                          order_id=str(e["pedido"].id))
        assert antes["eligible_for_billing"] is False

        c = sales.confirm_order(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                                lines=_conforme(e), actor="verificador")
        db.commit()

        assert c.status == "CONFIRMED" and c.attempt == 1
        assert db.get(SalesOrder, str(e["pedido"].id)).status == "CONFIRMED"
        despues = sales.billing_eligibility(db, company_id=mundo.company_a,
                                            order_id=str(e["pedido"].id))
        assert despues["eligible_for_billing"] is True
        assert despues["checked_by"] == "verificador"
    finally:
        db.close()


def test_el_control_guarda_las_tres_cifras(mundo):
    """Requerido, preparado y verificado. Colapsarlas borraría el control."""
    db = mundo.factory()
    try:
        e = _preparado(db, mundo)
        c = sales.confirm_order(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                                lines=_conforme(e), actor="verificador")
        db.commit()
        d = sales.confirmation_dict(db, c)
        linea = d["lines"][0]
        assert Decimal(linea["required_base_quantity"]) == Decimal("70")
        assert Decimal(linea["prepared_base_quantity"]) == Decimal("70")
        assert Decimal(linea["checked_base_quantity"]) == Decimal("70")
    finally:
        db.close()


# =========================================================================== #
# La comparación es contra el pedido
# =========================================================================== #
def test_se_compara_contra_el_pedido_y_no_contra_la_preparacion(mundo):
    """`R-D0-12-2`: «comparar la preparación consigo misma no es un control».

    El picking encontró 65 de 70 y la reserva encogió. El verificador cuenta 65,
    que es exactamente lo que hay preparado. Contra la preparación eso
    coincidiría; contra el pedido no, y el pedido pedía 70.
    """
    db = mundo.factory()
    try:
        e = _preparado(db, mundo, requerido=70, recogido=65)
        hoja = sales.confirmation_worksheet(db, company_id=mundo.company_a,
                                            order_id=str(e["pedido"].id))
        assert Decimal(hoja["lines"][0]["required_base_quantity"]) == Decimal("70")
        assert Decimal(hoja["lines"][0]["prepared_base_quantity"]) == Decimal("65")

        c = sales.confirm_order(
            db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
            lines=[{"order_line_id": str(e["linea"].id), "checked_base_quantity": 65}],
            actor="verificador")
        db.commit()
        assert c.status == "REJECTED", "un pedido incompleto pasó el control"
        assert sales.confirmation_dict(db, c)["lines"][0]["difference_kind"] == "CANTIDAD"
    finally:
        db.close()


def test_el_pedido_no_conforme_regresa_a_preparacion(mundo):
    """¶77: «El pedido regresa a preparación/corrección según corresponda»."""
    db = mundo.factory()
    try:
        e = _preparado(db, mundo)
        c = sales.confirm_order(
            db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
            lines=[{"order_line_id": str(e["linea"].id), "checked_base_quantity": 68}],
            notes="faltan dos cajas", actor="verificador")
        db.commit()
        assert c.status == "REJECTED"
        assert db.get(SalesOrder, str(e["pedido"].id)).status == "PREPARING"
        assert sales.billing_eligibility(
            db, company_id=mundo.company_a, order_id=str(e["pedido"].id))["eligible_for_billing"] is False
    finally:
        db.close()


def test_la_presentacion_y_la_condicion_forman_parte_del_control(mundo):
    """¶68 y ¶69: presentación o unidad correspondiente, y condición de despacho."""
    db = mundo.factory()
    try:
        for campo, motivo in (("presentation_ok", "PRESENTACION"), ("condition_ok", "CONDICION")):
            e = _preparado(db, mundo)
            c = sales.confirm_order(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                                    lines=_conforme(e, **{campo: False}), actor="verificador")
            db.commit()
            assert c.status == "REJECTED", f"{campo} no bloqueó el control"
            assert sales.confirmation_dict(db, c)["lines"][0]["difference_kind"] == motivo
    finally:
        db.close()


def test_el_control_es_completo_o_no_es_control(mundo):
    """`R-D0-12-3`: la confirmación tras corrección es completa, no parcial."""
    db = mundo.factory()
    try:
        e = _preparado(db, mundo)
        with pytest.raises(KontrolError) as exc:
            sales.confirm_order(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                                lines=[], actor="verificador")
        assert exc.value.code == "CONFIRMATION_INCOMPLETE"
    finally:
        db.close()


def test_una_linea_no_pedida_no_pasa_inadvertida(mundo):
    db = mundo.factory()
    try:
        e = _preparado(db, mundo)
        c = sales.confirm_order(
            db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
            lines=_conforme(e) + [{"order_line_id": str(uuid4()), "checked_base_quantity": 5,
                                   "product_id": e["prod"]}],
            actor="verificador")
        db.commit()
        assert c.status == "REJECTED"
        motivos = {ln["difference_kind"] for ln in sales.confirmation_dict(db, c)["lines"]}
        assert "LINEA_SOBRANTE" in motivos
    finally:
        db.close()


# =========================================================================== #
# Independencia
# =========================================================================== #
def test_quien_preparo_no_puede_confirmar(mundo):
    """¶90: «Almacén prepara. Confirmación verifica». `R-D0-12-5`, defecto `false`."""
    db = mundo.factory()
    try:
        e = _preparado(db, mundo, picker="almacenista")
        with pytest.raises(ConflictError) as exc:
            sales.confirm_order(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                                lines=_conforme(e), actor="almacenista")
        assert exc.value.code == "CONFIRMATION_SEGREGATION_REQUIRED"
        db.rollback()
        assert db.get(SalesOrder, str(e["pedido"].id)).status == "PREPARED"
    finally:
        db.close()


def test_la_empresa_puede_permitirlo_a_conciencia(mundo):
    """`R-D0-12-5`: configurable, y la decisión queda auditada en el dato."""
    db = mundo.factory()
    try:
        e = _preparado(db, mundo, picker="almacenista")
        empresa = db.get(Company, mundo.company_a)
        empresa.confirmation_same_user_allowed = True
        db.commit()
        c = sales.confirm_order(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                                lines=_conforme(e), actor="almacenista")
        db.commit()
        assert c.status == "CONFIRMED"
        empresa.confirmation_same_user_allowed = False
        db.commit()
    finally:
        db.close()


def test_el_defecto_de_la_empresa_exige_separacion(mundo):
    """«Un control cuyo valor por defecto lo anula no es un control»."""
    db = mundo.factory()
    try:
        assert db.get(Company, mundo.company_a).confirmation_same_user_allowed is False
    finally:
        db.close()


# =========================================================================== #
# Reintento
# =========================================================================== #
def test_el_rechazo_se_conserva_cuando_hay_segundo_intento(mundo):
    """`R-D0-12-3`: el rechazo anterior es la evidencia de por qué hubo otro."""
    db = mundo.factory()
    try:
        e = _preparado(db, mundo)
        primero = sales.confirm_order(
            db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
            lines=[{"order_line_id": str(e["linea"].id), "checked_base_quantity": 68}],
            actor="verificador")
        db.commit()
        assert primero.status == "REJECTED"

        # La preparación corrige y devuelve el pedido al control.
        pedido = db.get(SalesOrder, str(e["pedido"].id))
        pedido.status = "PREPARED"
        db.commit()

        segundo = sales.confirm_order(db, company_id=mundo.company_a,
                                      order_id=str(e["pedido"].id), lines=_conforme(e),
                                      actor="verificador")
        db.commit()
        assert segundo.status == "CONFIRMED" and segundo.attempt == 2
        historicos = db.execute(select(OrderConfirmation).where(
            OrderConfirmation.order_id == str(e["pedido"].id))).scalars().all()
        assert len(historicos) == 2, "se borró el intento fallido"
        assert {h.status for h in historicos} == {"REJECTED", "CONFIRMED"}
    finally:
        db.close()


def test_no_se_confirma_dos_veces(mundo):
    db = mundo.factory()
    try:
        e = _preparado(db, mundo)
        sales.confirm_order(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                            lines=_conforme(e), actor="verificador")
        db.commit()
        with pytest.raises(ConflictError) as exc:
            sales.confirm_order(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                                lines=_conforme(e), actor="verificador")
        assert exc.value.code == "CONFIRMATION_ORDER_NOT_PREPARED"
    finally:
        db.close()


# =========================================================================== #
# La frontera: verificar no toca nada
# =========================================================================== #
def test_verificar_no_mueve_una_sola_unidad(mundo):
    """Delta de inventario 0 en todo, confirme o rechace."""
    db = mundo.factory()
    try:
        e = _preparado(db, mundo)
        saldos0 = _saldos(db, mundo.company_a, e["prod"])
        movs0 = _movimientos(db, mundo.company_a, e["prod"])
        reserva0 = db.get(Reservation, str(e["reserva"].id)).status

        sales.confirm_order(db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
                            lines=_conforme(e), actor="verificador")
        db.commit()
        assert _saldos(db, mundo.company_a, e["prod"]) == saldos0, "el control movió inventario"
        assert _movimientos(db, mundo.company_a, e["prod"]) == movs0, "el control creó un movimiento"
        assert db.get(Reservation, str(e["reserva"].id)).status == reserva0, "el control tocó la reserva"

        otro = _preparado(db, mundo)
        s0, m0 = _saldos(db, mundo.company_a, otro["prod"]), _movimientos(db, mundo.company_a, otro["prod"])
        sales.confirm_order(
            db, company_id=mundo.company_a, order_id=str(otro["pedido"].id),
            lines=[{"order_line_id": str(otro["linea"].id), "checked_base_quantity": 1}],
            actor="verificador")
        db.commit()
        assert _saldos(db, mundo.company_a, otro["prod"]) == s0, "el rechazo movió inventario"
        assert _movimientos(db, mundo.company_a, otro["prod"]) == m0
    finally:
        db.close()


def test_la_caja_de_doce_se_verifica_en_veinticuatro(mundo):
    db = mundo.factory()
    try:
        e = _preparado(db, mundo, requerido=24, quantity=2, factor=12)
        hoja = sales.confirmation_worksheet(db, company_id=mundo.company_a,
                                            order_id=str(e["pedido"].id))
        assert Decimal(hoja["lines"][0]["required_base_quantity"]) == Decimal("24")
        assert hoja["lines"][0]["conversion_factor_snapshot"] is not None
        c = sales.confirm_order(
            db, company_id=mundo.company_a, order_id=str(e["pedido"].id),
            lines=[{"order_line_id": str(e["linea"].id), "checked_base_quantity": 2}],
            actor="verificador")
        db.commit()
        assert c.status == "REJECTED", "verificar 2 cajas como 2 unidades pasó el control"
    finally:
        db.close()


def test_no_se_confirma_un_pedido_que_no_esta_preparado(mundo):
    db = mundo.factory()
    try:
        marca = uuid4().hex[:8]
        ped = _pedido(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, marca=marca)
        db.commit()
        with pytest.raises(ConflictError) as exc:
            sales.confirm_order(db, company_id=mundo.company_a, order_id=str(ped.id),
                                lines=[], actor="verificador")
        assert exc.value.code == "CONFIRMATION_ORDER_NOT_PREPARED"
    finally:
        db.close()


# =========================================================================== #
# Multiempresa y concurrencia
# =========================================================================== #
def test_el_control_no_cruza_empresas(mundo):
    db = mundo.factory()
    try:
        e = _preparado(db, mundo)
        with pytest.raises(NotFoundError):
            sales.confirmation_worksheet(db, company_id=mundo.company_b,
                                         order_id=str(e["pedido"].id))
        pendientes = sales.pending_confirmations(db, company_id=mundo.company_b)
        assert str(e["pedido"].id) not in [str(o.id) for o in pendientes]
    finally:
        db.close()


def test_dos_verificadores_no_dejan_dos_veredictos(mundo):
    """P0: uno confirma y otro rechaza a la vez. El estado final es uno solo."""
    import threading

    db = mundo.factory()
    try:
        e = _preparado(db, mundo)
        order_id, linea_id, requerido = str(e["pedido"].id), str(e["linea"].id), e["requerido"]
    finally:
        db.close()

    resultados: list[str] = []
    choques: list[str] = []

    def _worker(cantidad) -> None:
        s = mundo.factory()
        try:
            c = sales.confirm_order(s, company_id=mundo.company_a, order_id=order_id,
                                    lines=[{"order_line_id": linea_id,
                                            "checked_base_quantity": cantidad}],
                                    actor="verificador")
            s.commit()
            resultados.append(c.status)
        except Exception as exc:                                   # noqa: BLE001
            s.rollback()
            choques.append(type(exc).__name__)
        finally:
            s.close()

    hilos = [threading.Thread(target=_worker, args=(q,)) for q in (requerido, requerido - 5)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    db = mundo.factory()
    try:
        assert len(resultados) == 1, f"dos veredictos terminales: {resultados} {choques}"
        confirmaciones = db.execute(select(OrderConfirmation).where(
            OrderConfirmation.order_id == order_id)).scalars().all()
        assert len(confirmaciones) == 1
        estado = db.get(SalesOrder, order_id).status
        assert estado in ("CONFIRMED", "PREPARING")
        assert (estado == "CONFIRMED") == (confirmaciones[0].status == "CONFIRMED")
    finally:
        db.close()
