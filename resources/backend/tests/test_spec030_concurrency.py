"""Carrera de dos pedidos sobre la última unidad — Spec 030, R-D0-03-3.

Disponible 10, dos pedidos de 8 confirmados a la vez desde dos conexiones
reales a PostgreSQL. Exactamente uno gana; el otro recibe
`INSUFFICIENT_AVAILABLE`; el reservado termina en 8 y nunca en 16. Con
`allow_negative` los dos entran, ambos marcados `oversell`, y el contador dice
16: sobreventa por política, no por carrera.
"""

from __future__ import annotations

import threading

from sqlalchemy import text

from app.core.errors import ConflictError
from app.modules.sales import service as sales_service

pytest_plugins = ("tests.conftest_multicompany",)


def _cliente(mundo, code):
    return mundo.crear("/maestros/terceros", "ua", mundo.company_a,
                       {"code": code, "name": f"Cliente {code}", "roles": ["CLIENTE"]})


def _producto(mundo, code):
    return mundo.crear("/maestros/catalogos/items", "ua", mundo.company_a,
                       {"code": code, "name": f"Producto {code}", "item_type": "PRODUCT"})


def _stock(mundo, almacen, producto, cantidad):
    tipo = mundo.crear("/inventory/movement-types", "ua", mundo.company_a,
                       {"code": f"ENT-RACE-{producto[:6]}", "name": "Entrada", "direction": "IN"})
    mundo.crear("/inventory/movements", "ua", mundo.company_a, {
        "warehouse_id": almacen, "product_id": producto, "movement_type_id": tipo,
        "quantity": cantidad, "unit_cost": 1.0, "currency": "VED"})


def _pedido(mundo, code, cliente, almacen, producto, cantidad):
    ped = mundo.crear("/sales/orders", "ua", mundo.company_a,
                      {"code": code, "customer_id": cliente, "currency": "VED", "warehouse_id": almacen})
    r = mundo.post(f"/sales/orders/{ped}/lines", "ua", mundo.company_a,
                   {"product_id": producto, "quantity": cantidad, "unit_price": 1})
    assert r.status_code == 200, r.text
    return ped


def _saldo(mundo, almacen, producto):
    db = mundo.factory()
    try:
        return db.execute(text(
            "SELECT qty_on_hand, qty_reserved, qty_available FROM inventory_balances "
            "WHERE warehouse_id = :w AND product_id = :p AND state = 'DISPONIBLE'"),
            {"w": almacen, "p": producto}).fetchone()
    finally:
        db.close()


def _confirmar_en_paralelo(mundo, pedidos):
    """Cada hilo abre su propia sesión (conexión) y confirma tras la barrera."""
    barrera = threading.Barrier(len(pedidos))
    resultados: dict[str, object] = {}

    def correr(order_id: str) -> None:
        db = mundo.factory()
        try:
            barrera.wait(timeout=20)
            try:
                sales_service.confirmar_pedido(db, company_id=mundo.company_a, order_id=order_id, actor="race")
                db.commit()
                resultados[order_id] = "OK"
            except ConflictError as exc:
                db.rollback()
                resultados[order_id] = exc.code
        finally:
            db.close()

    hilos = [threading.Thread(target=correr, args=(p,), name=f"confirmar-{p[:6]}") for p in pedidos]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
    return resultados


def test_dos_pedidos_sobre_la_ultima_unidad_solo_uno_reserva(mundo):
    """§40 — P0. El lock de fila decide; el contador no puede decir 16."""
    cli = _cliente(mundo, "CLI-RACE")
    prod = _producto(mundo, "PRD-RACE")
    _stock(mundo, mundo.warehouse_a, prod, 10)
    a = _pedido(mundo, "OV-RACE-A", cli, mundo.warehouse_a, prod, 8)
    b = _pedido(mundo, "OV-RACE-B", cli, mundo.warehouse_a, prod, 8)

    resultados = _confirmar_en_paralelo(mundo, [a, b])
    assert sorted(resultados.values()) == ["INSUFFICIENT_AVAILABLE", "OK"], resultados

    on_hand, reservado, disponible = _saldo(mundo, mundo.warehouse_a, prod)
    assert (float(on_hand), float(reservado), float(disponible)) == (10.0, 8.0, 2.0)

    ganador = next(p for p, v in resultados.items() if v == "OK")
    perdedor = next(p for p, v in resultados.items() if v != "OK")
    assert mundo.get(f"/sales/orders/{ganador}", "ua", mundo.company_a).json()["status"] == "RELEASED"
    assert mundo.get(f"/sales/orders/{perdedor}", "ua", mundo.company_a).json()["status"] == "DRAFT"
    activas = [r for r in mundo.get("/inventory/reservations?status=ACTIVE", "ua", mundo.company_a).json()["items"]
               if r["product_id"] == prod]
    assert len(activas) == 1 and activas[0]["source_order_id"] == ganador
    db = mundo.factory()
    try:
        eventos = db.execute(text(
            "SELECT after->>'source_order_id' FROM audit_events WHERE action = 'RESERVATION_CREATED' "
            "AND after->>'product_id' = :p"), {"p": prod}).fetchall()
    finally:
        db.close()
    assert [e[0] for e in eventos] == [ganador], "el perdedor no debía dejar rastro de reserva"


def test_con_allow_negative_los_dos_entran_marcados_y_el_contador_no_se_corrompe(mundo):
    """§41: sobreventa por política, transaccional, auditada; nunca contadores rotos."""
    alm = mundo.crear("/organization/warehouses", "ua", mundo.company_a,
                      {"code": "W-RACE-NEG", "name": "Race negativo", "branch_id": mundo.branch_a,
                       "company_id": mundo.company_a})
    db = mundo.factory()
    try:
        db.execute(text("UPDATE warehouses SET policies = CAST(:p AS JSON) WHERE id = :w"),
                   {"p": '{"allow_negative": true}', "w": alm})
        db.commit()
    finally:
        db.close()
    cli = _cliente(mundo, "CLI-RACE-NEG")
    prod = _producto(mundo, "PRD-RACE-NEG")
    _stock(mundo, alm, prod, 10)
    a = _pedido(mundo, "OV-RACENEG-A", cli, alm, prod, 8)
    b = _pedido(mundo, "OV-RACENEG-B", cli, alm, prod, 8)

    resultados = _confirmar_en_paralelo(mundo, [a, b])
    assert sorted(resultados.values()) == ["OK", "OK"], resultados
    on_hand, reservado, disponible = _saldo(mundo, alm, prod)
    assert (float(on_hand), float(reservado), float(disponible)) == (10.0, 16.0, -6.0)
    reservas = [r for r in mundo.get("/inventory/reservations?status=ACTIVE", "ua", mundo.company_a).json()["items"]
                if r["product_id"] == prod]
    assert len(reservas) == 2
    # La primera cabía (8 ≤ 10) y la segunda ya no (8 > 2): una sola es sobreventa
    assert sorted(r["oversell"] for r in reservas) == [False, True]
