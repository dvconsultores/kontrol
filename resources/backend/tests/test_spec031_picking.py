"""Spec 031 · cola, asignación por ubicación y ruta de picking (post `D0-15`).

Lo que estas pruebas defienden es la frontera: **planificar no es recoger**.
Nada de lo que hace la Spec 031 puede mover una unidad, tocar el reservado ni
sacar un pedido de la cola antes de tiempo. Y lo que decide —el orden de la
cola, cuándo se confirma, qué libera una asignación— lo decidió `D0-15`, no
esta implementación.

Multiempresa sobre PostgreSQL real, con el arnés `mundo`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.inventory import service as inv
from app.modules.inventory.models import InventoryBalance, InventoryMovement
from app.modules.organization.models import WarehouseLocation
from app.modules.sales import service as sales
from app.modules.sales.models import PickList, PickListLine, SalesOrder, SalesOrderLine

pytest_plugins = ("tests.conftest_multicompany",)


# --------------------------------------------------------------------------- #
# Mundo mínimo, construido en la base: producto, ubicaciones, pedido y reserva
# --------------------------------------------------------------------------- #
def _producto(db, company_id: str, marca: str) -> str:
    from app.modules.master_data.models import CatalogItem

    item = CatalogItem(company_id=company_id, code=f"PK-{marca}", name=f"Artículo {marca}",
                       item_type="PRODUCT", status="ACTIVE")
    db.add(item)
    db.flush()
    return str(item.id)


def _ubicacion(db, company_id, warehouse_id, code, *, sequence=1, status="ACTIVE") -> str:
    loc = WarehouseLocation(company_id=company_id, warehouse_id=warehouse_id, code=code,
                            name=f"Ubicación {code}", sequence=sequence, status=status)
    db.add(loc)
    db.flush()
    return str(loc.id)


def _entrada(db, *, company_id, warehouse_id, product_id, qty, state=None):
    tipo = inv._get_movement_type_by_code(db, company_id, "ENTRADA_RECEPCION")
    return inv.record_movement(db, company_id=company_id, warehouse_id=warehouse_id,
                               product_id=product_id, movement_type_id=str(tipo.id),
                               quantity=qty, state=state, actor="qa")


def _cliente(db, company_id, marca) -> str:
    from app.modules.master_data.models import Party

    p = Party(company_id=company_id, code=f"CLI-{marca}", name=f"Cliente {marca}", roles=["CLIENTE"])
    db.add(p)
    db.flush()
    return str(p.id)


def _pedido_liberado(db, *, company_id, warehouse_id, marca, released_at=None,
                     submitted_at=None) -> SalesOrder:
    """Un pedido ya en la cola: `RELEASED`, con su sello de entrada."""
    ahora = datetime.now(UTC)
    order = SalesOrder(company_id=company_id, code=f"OV-{marca}", customer_id=_cliente(db, company_id, marca),
                       warehouse_id=warehouse_id, currency="VED", status="RELEASED",
                       submitted_at=submitted_at or ahora, released_at=released_at or ahora)
    db.add(order)
    db.flush()
    return order


def _linea_reservada(db, *, order: SalesOrder, product_id: str, base: Decimal | int,
                     quantity=None, presentation_id=None, factor=None):
    """Línea de pedido con su reserva activa, en cantidad base."""
    linea = SalesOrderLine(order_id=str(order.id), product_id=product_id,
                           quantity=Decimal(str(quantity if quantity is not None else base)),
                           unit_price=Decimal("10"), needs_inventory=True,
                           presentation_id=presentation_id,
                           conversion_factor_snapshot=Decimal(str(factor)) if factor else None,
                           base_quantity=Decimal(str(base)))
    db.add(linea)
    db.flush()
    reserva = inv.reserve(db, company_id=str(order.company_id), source_document=order.code,
                          product_id=product_id, warehouse_id=str(order.warehouse_id),
                          quantity=float(linea.quantity), source_type="SALES_ORDER",
                          source_order_id=str(order.id), source_line_id=str(linea.id),
                          base_quantity=Decimal(str(base)), actor="qa")
    db.flush()
    return linea, reserva


def _plan(db, *, order: SalesOrder, marca) -> PickList:
    plan = PickList(company_id=str(order.company_id), code=f"PL-{marca}", order_id=str(order.id),
                    warehouse_id=str(order.warehouse_id), status="DRAFT")
    db.add(plan)
    db.flush()
    return plan


def _fisico(db, company_id, product_id) -> Decimal:
    return Decimal(str(db.execute(
        select(func.coalesce(func.sum(InventoryBalance.qty_on_hand), 0)).where(
            InventoryBalance.company_id == company_id,
            InventoryBalance.product_id == product_id)).scalar() or 0))


def _reservado(db, company_id, product_id) -> Decimal:
    return Decimal(str(db.execute(
        select(func.coalesce(func.sum(InventoryBalance.qty_reserved), 0)).where(
            InventoryBalance.company_id == company_id,
            InventoryBalance.product_id == product_id)).scalar() or 0))


def _movimientos(db, company_id, product_id) -> int:
    return db.execute(select(func.count(InventoryMovement.id)).where(
        InventoryMovement.company_id == company_id,
        InventoryMovement.product_id == product_id)).scalar() or 0


# =========================================================================== #
# OQ-031-1 · el orden de la cola
# =========================================================================== #
def test_la_cola_ordena_por_entrada_no_por_emision(mundo):
    """El caso canónico de `D0-15`: la retención de crédito no guarda el puesto.

    A se emitió a las 08:00 y se liberó a las 14:00. B se emitió a las 10:00 y
    se liberó a las 10:05. Con `submitted_at` iría antes A, penalizando a B por
    una retención que no le concierne. Con `released_at` va antes B, que llevaba
    casi cuatro horas listo para prepararse.
    """
    db = mundo.factory()
    try:
        base = datetime.now(UTC).replace(microsecond=0)
        a = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                             marca=f"A{uuid4().hex[:6]}",
                             submitted_at=base, released_at=base + timedelta(hours=6))
        b = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                             marca=f"B{uuid4().hex[:6]}",
                             submitted_at=base + timedelta(hours=2),
                             released_at=base + timedelta(hours=2, minutes=5))
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=prod, qty=100)
        _linea_reservada(db, order=a, product_id=prod, base=10)
        _linea_reservada(db, order=b, product_id=prod, base=10)
        db.commit()

        cola = [str(o.id) for o in sales.picking_queue(db, company_id=mundo.company_a)]
        assert cola.index(str(b.id)) < cola.index(str(a.id)), \
            "la cola ordenó por emisión: B llevaba horas liberado y quedó detrás"
    finally:
        db.close()


def test_el_desempate_es_estable_y_no_lo_decide_la_base(mundo):
    """Dos pedidos liberados en el mismo instante salen siempre en el mismo orden.

    Sin desempate total el residuo lo decidiría el orden natural de PostgreSQL,
    que no es un orden. Se desempata por `id`, clave primaria: `code` no tiene
    restricción de unicidad y no lo haría total.
    """
    db = mundo.factory()
    try:
        instante = datetime.now(UTC).replace(microsecond=0)
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=prod, qty=500)
        for _ in range(5):
            ped = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                                   marca=uuid4().hex[:8], released_at=instante)
            _linea_reservada(db, order=ped, product_id=prod, base=5)
        db.commit()

        lecturas = [tuple(str(o.id) for o in sales.picking_queue(db, company_id=mundo.company_a))
                    for _ in range(4)]
        assert len(set(lecturas)) == 1, "la cola cambia entre lecturas idénticas"
    finally:
        db.close()


def test_solo_entra_en_la_cola_lo_liberado_y_con_reserva_viva(mundo):
    """`R-D0-15-1`: la elegibilidad empieza en `RELEASED`, y no basta con eso."""
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=prod, qty=100)
        con_reserva = _pedido_liberado(db, company_id=mundo.company_a,
                                       warehouse_id=mundo.warehouse_a, marca=uuid4().hex[:8])
        _linea_reservada(db, order=con_reserva, product_id=prod, base=10)
        sin_reserva = _pedido_liberado(db, company_id=mundo.company_a,
                                       warehouse_id=mundo.warehouse_a, marca=uuid4().hex[:8])
        borrador = _pedido_liberado(db, company_id=mundo.company_a,
                                    warehouse_id=mundo.warehouse_a, marca=uuid4().hex[:8])
        borrador.status = "DRAFT"
        _linea_reservada(db, order=borrador, product_id=prod, base=10)
        db.commit()

        cola = [str(o.id) for o in sales.picking_queue(db, company_id=mundo.company_a)]
        assert str(con_reserva.id) in cola
        assert str(sin_reserva.id) not in cola, "un pedido sin reserva activa entró en la cola"
        assert str(borrador.id) not in cola, "un pedido no liberado entró en la cola"
    finally:
        db.close()


# =========================================================================== #
# Candidatas: solo lo ubicado y vendible
# =========================================================================== #
def test_solo_lo_ubicado_y_vendible_es_candidato(mundo):
    """`L1` con 40 disponible y `L2` con 100 en cuarentena dan 40, no 140.

    Y la mercancía sin ubicar no es candidata: existe y está comprometida, pero
    nadie puede ir a por ella hasta que el put-away la coloque.
    """
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L1-{uuid4().hex[:6]}", sequence=1)
        l2 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L2-{uuid4().hex[:6]}", sequence=2)
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod, qty=100)
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod,
                 qty=100, state="CUARENTENA")
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=40, actor="qa")
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l2, quantity=100, state="CUARENTENA",
                    actor="qa")
        ped = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                               marca=uuid4().hex[:8])
        linea, _ = _linea_reservada(db, order=ped, product_id=prod, base=30)
        plan = _plan(db, order=ped, marca=uuid4().hex[:8])
        db.commit()

        cands = sales.picking_candidates(db, company_id=mundo.company_a, plan_id=str(plan.id),
                                         order_line_id=str(linea.id))
        total = sum(Decimal(c["allocatable"]) for c in cands)
        assert total == Decimal("40"), f"candidato incorrecto: {total} (cuarentena o sin ubicar coladas)"
        assert all(c["location_id"] == l1 for c in cands)
    finally:
        db.close()


def test_las_candidatas_salen_en_orden_de_recorrido(mundo):
    """La ruta la da la Spec 008; aquí solo se comprueba que se consume."""
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        marca = uuid4().hex[:6]
        tercera = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"C-{marca}", sequence=30)
        primera = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"A-{marca}", sequence=10)
        segunda = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"B-{marca}", sequence=20)
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod, qty=90)
        for loc in (tercera, primera, segunda):
            inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                        product_id=prod, target_location_id=loc, quantity=30, actor="qa")
        ped = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                               marca=uuid4().hex[:8])
        linea, _ = _linea_reservada(db, order=ped, product_id=prod, base=90)
        plan = _plan(db, order=ped, marca=uuid4().hex[:8])
        db.commit()

        cands = sales.picking_candidates(db, company_id=mundo.company_a, plan_id=str(plan.id),
                                         order_line_id=str(linea.id))
        assert [c["location_id"] for c in cands] == [primera, segunda, tercera]
    finally:
        db.close()


# =========================================================================== #
# OQ-031-2 · división, límites y compuerta de confirmación
# =========================================================================== #
def test_la_demanda_se_reparte_entre_ubicaciones(mundo):
    """`R-D0-15-5`: la reserva es de almacén; ninguna ubicación tiene las 70."""
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        marca = uuid4().hex[:6]
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L1-{marca}", sequence=1)
        l2 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L2-{marca}", sequence=2)
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod, qty=100)
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=40, actor="qa")
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l2, quantity=60, actor="qa")
        ped = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                               marca=uuid4().hex[:8])
        linea, _ = _linea_reservada(db, order=ped, product_id=prod, base=70)
        plan = _plan(db, order=ped, marca=uuid4().hex[:8])
        db.commit()

        sales.allocate(db, company_id=mundo.company_a, plan_id=str(plan.id),
                       order_line_id=str(linea.id), location_id=l1, quantity=40, actor="qa")
        sales.allocate(db, company_id=mundo.company_a, plan_id=str(plan.id),
                       order_line_id=str(linea.id), location_id=l2, quantity=30, actor="qa")
        db.commit()

        d = sales.plan_dict(db, plan)
        assert Decimal(d["remaining_base_quantity"]) == 0
        assert {(r["location_id"], Decimal(r["base_quantity"])) for r in d["route"]} == \
            {(l1, Decimal("40")), (l2, Decimal("30"))}
        assert [r["sequence"] for r in d["route"]] == [1, 2], "el recorrido no está numerado"
    finally:
        db.close()


def test_no_se_puede_asignar_mas_de_lo_reservado(mundo):
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L1-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod, qty=100)
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=100, actor="qa")
        ped = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                               marca=uuid4().hex[:8])
        linea, _ = _linea_reservada(db, order=ped, product_id=prod, base=30)
        plan = _plan(db, order=ped, marca=uuid4().hex[:8])
        db.commit()

        with pytest.raises(ConflictError) as e:
            sales.allocate(db, company_id=mundo.company_a, plan_id=str(plan.id),
                           order_line_id=str(linea.id), location_id=l1, quantity=31, actor="qa")
        assert e.value.code == "PICKING_OVER_RESERVATION"
    finally:
        db.close()


def test_dos_planes_no_se_llevan_la_misma_existencia(mundo):
    """`R-D0-15-22`: lo asignable descuenta lo que otros planes vivos ya tomaron."""
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L1-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod, qty=140)
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=100, actor="qa")
        p1 = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                              marca=uuid4().hex[:8])
        p2 = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                              marca=uuid4().hex[:8])
        li1, _ = _linea_reservada(db, order=p1, product_id=prod, base=70)
        li2, _ = _linea_reservada(db, order=p2, product_id=prod, base=70)
        plan1 = _plan(db, order=p1, marca=uuid4().hex[:8])
        plan2 = _plan(db, order=p2, marca=uuid4().hex[:8])
        db.commit()

        sales.allocate(db, company_id=mundo.company_a, plan_id=str(plan1.id),
                       order_line_id=str(li1.id), location_id=l1, quantity=70, actor="qa")
        db.commit()
        with pytest.raises(ConflictError) as e:
            sales.allocate(db, company_id=mundo.company_a, plan_id=str(plan2.id),
                           order_line_id=str(li2.id), location_id=l1, quantity=70, actor="qa")
        assert e.value.code == "PICKING_OVER_LOCATION"

        cands = sales.picking_candidates(db, company_id=mundo.company_a, plan_id=str(plan2.id),
                                         order_line_id=str(li2.id))
        assert sum(Decimal(c["allocatable"]) for c in cands) == Decimal("30")
    finally:
        db.close()


def test_asignar_fija_no_suma(mundo):
    """Idempotencia sin clave de cliente: repetir el envío deja el mismo total."""
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L1-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod, qty=100)
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=100, actor="qa")
        ped = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                               marca=uuid4().hex[:8])
        linea, _ = _linea_reservada(db, order=ped, product_id=prod, base=50)
        plan = _plan(db, order=ped, marca=uuid4().hex[:8])
        db.commit()

        for _ in range(3):
            sales.allocate(db, company_id=mundo.company_a, plan_id=str(plan.id),
                           order_line_id=str(linea.id), location_id=l1, quantity=50, actor="qa")
        db.commit()
        d = sales.plan_dict(db, plan)
        assert len(d["route"]) == 1, "el doble envío duplicó la asignación"
        assert Decimal(d["route"][0]["base_quantity"]) == 50
        assert Decimal(d["remaining_base_quantity"]) == 0
    finally:
        db.close()


def test_no_se_confirma_un_plan_incompleto(mundo):
    """`R-D0-15-8`: 60 de 100 asignado no se confirma, y dice cuánto falta."""
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        marca = uuid4().hex[:6]
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L1-{marca}", sequence=1)
        l2 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L2-{marca}", sequence=2)
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod, qty=100)
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=40, actor="qa")
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l2, quantity=20, actor="qa")
        ped = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                               marca=uuid4().hex[:8])
        linea, _ = _linea_reservada(db, order=ped, product_id=prod, base=100)
        plan = _plan(db, order=ped, marca=uuid4().hex[:8])
        db.commit()

        sales.allocate(db, company_id=mundo.company_a, plan_id=str(plan.id),
                       order_line_id=str(linea.id), location_id=l1, quantity=40, actor="qa")
        sales.allocate(db, company_id=mundo.company_a, plan_id=str(plan.id),
                       order_line_id=str(linea.id), location_id=l2, quantity=20, actor="qa")
        db.commit()

        d = sales.plan_dict(db, plan)
        assert Decimal(d["remaining_base_quantity"]) == 40, "el remanente no se publica"
        assert d["confirmable"] is False
        with pytest.raises(ConflictError) as e:
            sales.confirm_plan(db, company_id=mundo.company_a, plan_id=str(plan.id), actor="qa")
        assert e.value.code == "PICKING_PLAN_INCOMPLETE"
        db.rollback()
        assert db.get(SalesOrder, str(ped.id)).status == "RELEASED", \
            "un plan incompleto sacó el pedido de la cola"
    finally:
        db.close()


# =========================================================================== #
# OQ-031-3 · ciclo de vida, y la frontera con el pedido
# =========================================================================== #
def test_crear_un_borrador_no_saca_el_pedido_de_la_cola(mundo):
    """`R-D0-15-18`, el delta dirigido sobre Ventas.

    Antes, `create_picklist` movía el pedido a `PREPARING` **al crear**. Un
    borrador parcial lo habría sacado de la fila sin que ningún plan pudiera
    ejecutarse: desaparecido de la cola y sin preparar.
    """
    db = mundo.factory()
    try:
        ped = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                               marca=uuid4().hex[:8])
        db.commit()
        sales.create_picklist(db, company_id=mundo.company_a, code=f"PL-{uuid4().hex[:8]}",
                              order_id=str(ped.id), warehouse_id=mundo.warehouse_a, actor="qa")
        db.commit()
        assert db.get(SalesOrder, str(ped.id)).status == "RELEASED"
    finally:
        db.close()


def test_confirmar_completo_mueve_el_pedido_a_preparacion(mundo):
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L1-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod, qty=100)
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=100, actor="qa")
        ped = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                               marca=uuid4().hex[:8])
        linea, _ = _linea_reservada(db, order=ped, product_id=prod, base=25)
        plan = _plan(db, order=ped, marca=uuid4().hex[:8])
        db.commit()

        sales.allocate(db, company_id=mundo.company_a, plan_id=str(plan.id),
                       order_line_id=str(linea.id), location_id=l1, quantity=25, actor="qa")
        sales.confirm_plan(db, company_id=mundo.company_a, plan_id=str(plan.id), actor="qa")
        db.commit()

        assert db.get(PickList, str(plan.id)).status == "CONFIRMED"
        assert db.get(SalesOrder, str(ped.id)).status == "PREPARING"
        assert str(ped.id) not in [str(o.id) for o in sales.picking_queue(db, company_id=mundo.company_a)]
    finally:
        db.close()


def test_cancelar_un_plan_confirmado_devuelve_el_pedido_a_la_cola(mundo):
    """`R-D0-15-19`: sin la arista `PREPARING → RELEASED` el pedido quedaría
    varado con la reserva viva, sin plan y sin camino de vuelta.

    Y `R-D0-15-13`: cancelar **no** libera la reserva comercial.
    """
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L1-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod, qty=60)
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=60, actor="qa")
        ped = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                               marca=uuid4().hex[:8])
        linea, reserva = _linea_reservada(db, order=ped, product_id=prod, base=20)
        plan = _plan(db, order=ped, marca=uuid4().hex[:8])
        db.commit()
        sales.allocate(db, company_id=mundo.company_a, plan_id=str(plan.id),
                       order_line_id=str(linea.id), location_id=l1, quantity=20, actor="qa")
        sales.confirm_plan(db, company_id=mundo.company_a, plan_id=str(plan.id), actor="qa")
        db.commit()
        reservado_antes = _reservado(db, mundo.company_a, prod)

        sales.cancel_plan(db, company_id=mundo.company_a, plan_id=str(plan.id),
                          reason="el cliente cambió la fecha", actor="qa")
        db.commit()

        assert db.get(PickList, str(plan.id)).status == "CANCELLED"
        assert db.get(SalesOrder, str(ped.id)).status == "RELEASED", "el pedido quedó varado"
        assert db.get(type(reserva), str(reserva.id)).status == "ACTIVE", \
            "la 031 liberó una reserva comercial"
        assert _reservado(db, mundo.company_a, prod) == reservado_antes
        # La existencia vuelve a estar asignable: cancelar libera la asignación.
        otro = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                                marca=uuid4().hex[:8])
        li2, _ = _linea_reservada(db, order=otro, product_id=prod, base=20)
        plan2 = _plan(db, order=otro, marca=uuid4().hex[:8])
        db.commit()
        cands = sales.picking_candidates(db, company_id=mundo.company_a, plan_id=str(plan2.id),
                                         order_line_id=str(li2.id))
        assert sum(Decimal(c["allocatable"]) for c in cands) == Decimal("60"), \
            "la asignación del plan cancelado sigue secuestrando existencia"
    finally:
        db.close()


def test_invalidar_exige_que_la_precondicion_este_perdida(mundo):
    """Invalidar no es un sinónimo de cancelar.

    Uno es lo que alguien decidió; el otro, lo que le ocurrió. Confundirlos
    borraría esa diferencia de la auditoría.
    """
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L1-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod, qty=50)
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=50, actor="qa")
        ped = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                               marca=uuid4().hex[:8])
        linea, reserva = _linea_reservada(db, order=ped, product_id=prod, base=10)
        plan = _plan(db, order=ped, marca=uuid4().hex[:8])
        db.commit()

        with pytest.raises(ConflictError) as e:
            sales.invalidate_plan(db, company_id=mundo.company_a, plan_id=str(plan.id),
                                  reason="por si acaso", actor="qa")
        assert e.value.code == "PICKING_PLAN_STILL_VALID"
        db.rollback()

        # Ahora sí: la reserva deja de estar activa aguas arriba.
        inv.release_if_active(db, reservation=db.get(type(reserva), str(reserva.id)),
                              actor="qa", reason="ORDER_CANCELLED")
        db.commit()
        sales.invalidate_plan(db, company_id=mundo.company_a, plan_id=str(plan.id),
                              reason="la reserva se liberó", actor="qa")
        db.commit()
        assert db.get(PickList, str(plan.id)).status == "INVALIDATED"
    finally:
        db.close()


def test_cancelar_e_invalidar_exigen_motivo(mundo):
    db = mundo.factory()
    try:
        ped = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                               marca=uuid4().hex[:8])
        plan = _plan(db, order=ped, marca=uuid4().hex[:8])
        db.commit()
        with pytest.raises(KontrolError) as e:
            sales.cancel_plan(db, company_id=mundo.company_a, plan_id=str(plan.id), actor="qa")
        assert e.value.code == "REASON_REQUIRED"
    finally:
        db.close()


# =========================================================================== #
# La frontera: planificar no mueve nada
# =========================================================================== #
def test_planificar_no_mueve_una_sola_unidad(mundo):
    """`R-D0-15-14`: ningún estado de la 031 toca el inventario físico.

    Se mide antes y después de borrador, confirmación y cancelación: existencia,
    reservado y número de movimientos.
    """
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L1-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod, qty=80)
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=80, actor="qa")
        ped = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                               marca=uuid4().hex[:8])
        linea, _ = _linea_reservada(db, order=ped, product_id=prod, base=30)
        plan = _plan(db, order=ped, marca=uuid4().hex[:8])
        db.commit()

        fisico0, reservado0, movs0 = (_fisico(db, mundo.company_a, prod),
                                      _reservado(db, mundo.company_a, prod),
                                      _movimientos(db, mundo.company_a, prod))

        sales.allocate(db, company_id=mundo.company_a, plan_id=str(plan.id),
                       order_line_id=str(linea.id), location_id=l1, quantity=30, actor="qa")
        db.commit()
        assert (_fisico(db, mundo.company_a, prod), _reservado(db, mundo.company_a, prod),
                _movimientos(db, mundo.company_a, prod)) == (fisico0, reservado0, movs0), "el borrador movió inventario"

        sales.confirm_plan(db, company_id=mundo.company_a, plan_id=str(plan.id), actor="qa")
        db.commit()
        assert (_fisico(db, mundo.company_a, prod), _reservado(db, mundo.company_a, prod),
                _movimientos(db, mundo.company_a, prod)) == (fisico0, reservado0, movs0), "confirmar movió inventario"

        sales.cancel_plan(db, company_id=mundo.company_a, plan_id=str(plan.id),
                          reason="prueba", actor="qa")
        db.commit()
        assert (_fisico(db, mundo.company_a, prod), _reservado(db, mundo.company_a, prod),
                _movimientos(db, mundo.company_a, prod)) == (fisico0, reservado0, movs0), "cancelar movió inventario"
    finally:
        db.close()


def test_la_caja_de_doce_se_asigna_en_veinticuatro(mundo):
    """Dos cajas de doce son veinticuatro unidades base, y el picking asigna 24."""
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L1-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod, qty=50)
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=50, actor="qa")
        ped = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                               marca=uuid4().hex[:8])
        linea, _ = _linea_reservada(db, order=ped, product_id=prod, base=24, quantity=2, factor=12)
        plan = _plan(db, order=ped, marca=uuid4().hex[:8])
        db.commit()

        d0 = sales.plan_dict(db, plan)
        assert Decimal(d0["demand"][0]["required_base_quantity"]) == 24, \
            "el requerido cayó a la unidad de venta"
        with pytest.raises(ConflictError):
            sales.allocate(db, company_id=mundo.company_a, plan_id=str(plan.id),
                           order_line_id=str(linea.id), location_id=l1, quantity=25, actor="qa")
        db.rollback()
        sales.allocate(db, company_id=mundo.company_a, plan_id=str(plan.id),
                       order_line_id=str(linea.id), location_id=l1, quantity=24, actor="qa")
        db.commit()
        assert Decimal(sales.plan_dict(db, plan)["remaining_base_quantity"]) == 0
    finally:
        db.close()


# =========================================================================== #
# Multiempresa
# =========================================================================== #
def test_no_se_asigna_una_ubicacion_de_otra_empresa_ni_de_otro_almacen(mundo):
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        ajena = _ubicacion(db, mundo.company_b, mundo.warehouse_b, f"LB-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod, qty=10)
        ped = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                               marca=uuid4().hex[:8])
        linea, _ = _linea_reservada(db, order=ped, product_id=prod, base=5)
        plan = _plan(db, order=ped, marca=uuid4().hex[:8])
        db.commit()

        with pytest.raises((NotFoundError, ConflictError)):
            sales.allocate(db, company_id=mundo.company_a, plan_id=str(plan.id),
                           order_line_id=str(linea.id), location_id=ajena, quantity=5, actor="qa")
        db.rollback()
        with pytest.raises(NotFoundError):
            sales.get_plan(db, company_id=mundo.company_b, plan_id=str(plan.id))
    finally:
        db.close()


def test_la_cola_no_cruza_empresas(mundo):
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod, qty=20)
        ped = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                               marca=uuid4().hex[:8])
        _linea_reservada(db, order=ped, product_id=prod, base=5)
        db.commit()
        assert str(ped.id) not in [str(o.id) for o in sales.picking_queue(db, company_id=mundo.company_b)]
    finally:
        db.close()


# =========================================================================== #
# Concurrencia real sobre PostgreSQL
# =========================================================================== #
def test_dos_transacciones_no_asignan_la_misma_existencia(mundo):
    """P0: `L1` tiene 100 y dos planes piden 70 a la vez. El total no puede ser 140.

    Es la misma ventana que `D0-03` describió para la reserva: leer el
    disponible antes de bloquear deja exactamente el hueco que dos operarios
    necesitan para llevarse las mismas unidades. Aquí se cierra bloqueando la
    fila de saldo antes de comprobar nada.
    """
    import threading

    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L1-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a, product_id=prod, qty=140)
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=100, actor="qa")
        p1 = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                              marca=uuid4().hex[:8])
        p2 = _pedido_liberado(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                              marca=uuid4().hex[:8])
        li1, _ = _linea_reservada(db, order=p1, product_id=prod, base=70)
        li2, _ = _linea_reservada(db, order=p2, product_id=prod, base=70)
        plan1 = _plan(db, order=p1, marca=uuid4().hex[:8])
        plan2 = _plan(db, order=p2, marca=uuid4().hex[:8])
        db.commit()
        ids = [(str(plan1.id), str(li1.id)), (str(plan2.id), str(li2.id))]
    finally:
        db.close()

    exitos: list[str] = []
    choques: list[str] = []

    def _worker(plan_id: str, linea_id: str) -> None:
        s = mundo.factory()
        try:
            sales.allocate(s, company_id=mundo.company_a, plan_id=plan_id,
                           order_line_id=linea_id, location_id=l1, quantity=70, actor="qa")
            s.commit()
            exitos.append(plan_id)
        except Exception as exc:                                  # noqa: BLE001
            s.rollback()
            choques.append(type(exc).__name__)
        finally:
            s.close()

    hilos = [threading.Thread(target=_worker, args=par) for par in ids]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    db = mundo.factory()
    try:
        total = db.execute(
            select(func.coalesce(func.sum(PickListLine.base_quantity), 0))
            .where(PickListLine.location_id == l1)).scalar()
        assert Decimal(str(total)) <= Decimal("100"), \
            f"se asignaron {total} de una ubicación que solo tiene 100"
        assert len(exitos) == 1 and len(choques) == 1, \
            f"ambas transacciones cupieron: éxitos {exitos}, choques {choques}"
    finally:
        db.close()
