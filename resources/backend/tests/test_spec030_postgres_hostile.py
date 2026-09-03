"""Pruebas hostiles sobre PostgreSQL — Spec 030, §77.

Lo que el servicio promete lo tiene que sostener la base: claves foráneas,
una sola reserva ACTIVE por línea, cantidad positiva y reservado nunca
negativo. Se verifica el SQLSTATE, no solo que «falla».
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

pytest_plugins = ("tests.conftest_multicompany",)

FK_VIOLATION = "23503"
UNIQUE_VIOLATION = "23505"
CHECK_VIOLATION = "23514"


def _sqlstate(exc: IntegrityError) -> str:
    return getattr(exc.orig, "pgcode", None) or getattr(getattr(exc.orig, "diag", None), "sqlstate", "")


def _insertar_reserva(mundo, **campos):
    base = {"id": str(uuid.uuid4()), "company_id": mundo.company_a, "product_id": None,
            "warehouse_id": mundo.warehouse_a, "quantity": 1, "status": "ACTIVE",
            "source_type": None, "source_order_id": None, "source_line_id": None, "oversell": False}
    base.update(campos)
    db = mundo.factory()
    try:
        with pytest.raises(IntegrityError) as info:
            db.execute(text(
                "INSERT INTO reservations (id, company_id, product_id, warehouse_id, quantity, status, "
                "source_type, source_order_id, source_line_id, oversell, created_at, updated_at) "
                "VALUES (:id, :company_id, :product_id, :warehouse_id, :quantity, :status, "
                ":source_type, :source_order_id, :source_line_id, :oversell, now(), now())"), base)
            db.commit()
        db.rollback()
        return _sqlstate(info.value)
    finally:
        db.close()


def _producto(mundo, code):
    return mundo.crear("/maestros/catalogos/items", "ua", mundo.company_a,
                       {"code": code, "name": f"Producto {code}", "item_type": "PRODUCT"})


def _pedido_confirmado(mundo, marca):
    cli = mundo.crear("/maestros/terceros", "ua", mundo.company_a,
                      {"code": f"CLI-{marca}", "name": "Cliente", "roles": ["CLIENTE"]})
    prod = _producto(mundo, f"PRD-{marca}")
    tipo = mundo.crear("/inventory/movement-types", "ua", mundo.company_a,
                       {"code": f"ENT-{marca}", "name": "Entrada", "direction": "IN"})
    mundo.crear("/inventory/movements", "ua", mundo.company_a, {
        "warehouse_id": mundo.warehouse_a, "product_id": prod, "movement_type_id": tipo,
        "quantity": 10, "unit_cost": 1.0, "currency": "VED"})
    ped = mundo.crear("/sales/orders", "ua", mundo.company_a,
                      {"code": f"OV-{marca}", "customer_id": cli, "currency": "VED",
                       "warehouse_id": mundo.warehouse_a})
    r = mundo.post(f"/sales/orders/{ped}/lines", "ua", mundo.company_a,
                   {"product_id": prod, "quantity": 2, "unit_price": 1})
    linea = r.json()["id"]
    r = mundo.post(f"/sales/orders/{ped}/submit", "ua", mundo.company_a, {})
    assert r.status_code == 200, r.text
    return {"pedido": ped, "linea": linea, "producto": prod}


def test_1_empresa_inexistente(mundo):
    prod = _producto(mundo, "H1")
    assert _insertar_reserva(mundo, product_id=prod, company_id="no-existe") == FK_VIOLATION


def test_2_pedido_inexistente(mundo):
    prod = _producto(mundo, "H2")
    assert _insertar_reserva(mundo, product_id=prod, source_type="SALES_ORDER",
                             source_order_id="no-existe") == FK_VIOLATION


def test_3_linea_inexistente(mundo):
    prod = _producto(mundo, "H3")
    assert _insertar_reserva(mundo, product_id=prod, source_type="SALES_ORDER",
                             source_line_id="no-existe") == FK_VIOLATION


def test_4_almacen_inexistente(mundo):
    prod = _producto(mundo, "H4")
    assert _insertar_reserva(mundo, product_id=prod, warehouse_id="no-existe") == FK_VIOLATION


def test_5_segunda_reserva_activa_para_la_misma_linea(mundo):
    """IMP-030-018/058: el índice parcial, no el servicio, impide el duplicado."""
    m = _pedido_confirmado(mundo, "H5")
    assert _insertar_reserva(mundo, product_id=m["producto"], source_type="SALES_ORDER",
                             source_order_id=m["pedido"], source_line_id=m["linea"]) == UNIQUE_VIOLATION
    # Cerrada la primera, una nueva ACTIVE para la misma línea sí cabe
    db = mundo.factory()
    try:
        db.execute(text("UPDATE reservations SET status = 'RELEASED' WHERE source_line_id = :l"), {"l": m["linea"]})
        db.execute(text(
            "INSERT INTO reservations (id, company_id, product_id, warehouse_id, quantity, status, source_type, "
            "source_order_id, source_line_id, oversell, created_at, updated_at) VALUES (:id, :c, :p, :w, 1, 'ACTIVE', "
            "'SALES_ORDER', :o, :l, false, now(), now())"),
            {"id": str(uuid.uuid4()), "c": mundo.company_a, "p": m["producto"], "w": mundo.warehouse_a,
             "o": m["pedido"], "l": m["linea"]})
        db.commit()
    finally:
        db.close()


def test_6_reservado_negativo_por_actualizacion_directa(mundo):
    m = _pedido_confirmado(mundo, "H6")
    db = mundo.factory()
    try:
        with pytest.raises(IntegrityError) as info:
            db.execute(text("UPDATE inventory_balances SET qty_reserved = -1 WHERE product_id = :p"), {"p": m["producto"]})
            db.commit()
        db.rollback()
        assert _sqlstate(info.value) == CHECK_VIOLATION
    finally:
        db.close()


def test_7_liberar_de_mas_no_puede_dejar_saldo_negativo(mundo):
    """IMP-030-059: ni restando por debajo de cero desde SQL."""
    m = _pedido_confirmado(mundo, "H7")
    db = mundo.factory()
    try:
        with pytest.raises(IntegrityError) as info:
            db.execute(text("UPDATE inventory_balances SET qty_reserved = qty_reserved - 1000 WHERE product_id = :p"),
                       {"p": m["producto"]})
            db.commit()
        db.rollback()
        assert _sqlstate(info.value) == CHECK_VIOLATION
    finally:
        db.close()


def test_8_cantidad_cero_o_negativa(mundo):
    prod = _producto(mundo, "H8")
    assert _insertar_reserva(mundo, product_id=prod, quantity=0) == CHECK_VIOLATION
    assert _insertar_reserva(mundo, product_id=prod, quantity=-3) == CHECK_VIOLATION


def test_9_la_linea_pertenece_al_pedido_que_la_reserva(mundo):
    """La base no tiene clave compuesta línea→pedido; el servicio lo garantiza y aquí se mide."""
    m = _pedido_confirmado(mundo, "H9")
    db = mundo.factory()
    try:
        cruzadas = db.execute(text(
            "SELECT count(*) FROM reservations r JOIN sales_order_lines l ON l.id = r.source_line_id "
            "WHERE r.source_order_id IS NOT NULL AND l.order_id <> r.source_order_id")).scalar()
        propias = db.execute(text(
            "SELECT count(*) FROM reservations r JOIN sales_order_lines l ON l.id = r.source_line_id "
            "WHERE r.source_order_id = :o AND l.order_id = :o"), {"o": m["pedido"]}).scalar()
    finally:
        db.close()
    assert cruzadas == 0 and propias == 1


def test_10_la_clave_del_saldo_es_unica(mundo):
    m = _pedido_confirmado(mundo, "H10")
    db = mundo.factory()
    try:
        with pytest.raises(IntegrityError) as info:
            db.execute(text(
                "INSERT INTO inventory_balances (id, company_id, warehouse_id, product_id, state, qty_on_hand, "
                "qty_reserved, qty_available, created_at, updated_at) VALUES (:id, :c, :w, :p, 'DISPONIBLE', 0, 0, 0, now(), now())"),
                {"id": str(uuid.uuid4()), "c": mundo.company_a, "w": mundo.warehouse_a, "p": m["producto"]})
            db.commit()
        db.rollback()
        assert _sqlstate(info.value) == UNIQUE_VIOLATION
    finally:
        db.close()
