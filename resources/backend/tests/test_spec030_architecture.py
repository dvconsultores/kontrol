"""Guardias estructurales de la Spec 030 — `RESERVATION TRIGGER = ORDER_CONFIRMATION`.

Fallan en construcción. Existen para que un refactor no devuelva la reserva al
punto de aprobación del crédito, no la haga configurable, no la deje sin
identidad de línea, no la lea sin bloqueo ni le cuelgue un planificador.
"""

from __future__ import annotations

import ast
import pathlib
import re

from sqlalchemy import CheckConstraint

from app.core.database import Base, init_models
from app.modules.inventory import service as inv_service
from app.modules.sales import service as sales_service

init_models()

BACKEND = pathlib.Path(__file__).resolve().parents[1]
SALES = BACKEND / "app" / "modules" / "sales" / "service.py"
INVENTORY = BACKEND / "app" / "modules" / "inventory" / "service.py"


def _funciones_que_llaman(modulo: pathlib.Path, nombre: str) -> set[str]:
    arbol = ast.parse(modulo.read_text(encoding="utf-8"))
    salida = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.FunctionDef):
            for sub in ast.walk(nodo):
                if isinstance(sub, ast.Call):
                    f = sub.func
                    if (isinstance(f, ast.Attribute) and f.attr == nombre) or (isinstance(f, ast.Name) and f.id == nombre):
                        salida.add(nodo.name)
    return salida


def test_el_disparador_es_la_confirmacion_y_no_es_configurable():
    """R-D0-03-1: fijo. Ninguna función lo lee de configuración."""
    assert sales_service.RESERVATION_TRIGGER == "ORDER_CONFIRMATION"
    fuente = SALES.read_text(encoding="utf-8")
    assert "reservation_trigger" not in fuente.replace('"reservation_trigger": RESERVATION_TRIGGER', ""), (
        "el disparador aparece como dato configurable")


def test_solo_la_confirmacion_reserva():
    """El único camino que llama a `reserve` en ventas es `confirmar_pedido`."""
    assert _funciones_que_llaman(SALES, "reserve") == {"confirmar_pedido"}
    assert not hasattr(sales_service, "_reserve_order"), "volvió la reserva en la aprobación"


def test_la_maquina_de_estados_es_la_de_d0_03():
    t = sales_service.ORDER_TRANSITIONS
    for viejo in ("CREDIT_PENDING", "APPROVED", "RESERVED"):
        assert viejo not in t, f"estado superado presente: {viejo}"
        assert all(viejo not in destinos for destinos in t.values())
    assert t["DRAFT"] == {"SUBMITTED", "CANCELLED"}
    assert t["SUBMITTED"] == {"RELEASED", "REJECTED", "CANCELLED", "EXPIRED", "DRAFT"}
    assert t["RELEASED"] == {"PREPARING", "SHIPPED", "CANCELLED", "DRAFT"}
    # `RELEASED` se añadió como salida de `PREPARING` por `R-D0-15-19`, delta
    # dirigido de la Spec 031 sobre esta máquina. Cancelar un plan de picking
    # confirmado antes de cualquier efecto físico devuelve el pedido a la cola;
    # sin esta arista quedaba varado con la reserva viva, sin plan y sin camino
    # de vuelta. No cambia nada de `D0-03`: la reserva no se toca.
    # `PREPARED` lo añadió la Spec 032 y lo declara `ADR-D0-012`: «`RESERVED →
    # PREPARING → PREPARED → CONFIRMED → …`». Es el estado de entrada que la
    # confirmación independiente de la 033 necesita para ser distinguible.
    assert t["PREPARING"] == {"SHIPPED", "CANCELLED", "RELEASED", "PREPARED"}
    assert t["PREPARED"] == {"SHIPPED", "CANCELLED"}
    assert "CONFIRMED" not in t, "la 032 adelantó un estado de la 033"
    assert sales_service.ORDER_HANDOFF_STATE == "RELEASED"
    assert all(t[x] == set() for x in ("CLOSED", "CANCELLED", "REJECTED", "EXPIRED"))


def test_la_reserva_tiene_identidad_unicidad_y_checks_en_el_orm():
    """IMP-030-016..018, 058..060: el esquema de pruebas nace del ORM."""
    r = Base.metadata.tables["reservations"]
    for col in ("source_type", "source_order_id", "source_line_id", "trigger", "oversell",
                "released_at", "released_by", "release_reason", "base_quantity"):
        assert col in r.c, f"falta {col}"
    assert {fk.column.table.name for fk in r.c.source_order_id.foreign_keys} == {"sales_orders"}
    assert {fk.column.table.name for fk in r.c.source_line_id.foreign_keys} == {"sales_order_lines"}
    idx = {i.name: i for i in r.indexes}
    assert "uq_reservations_active_line" in idx and idx["uq_reservations_active_line"].unique
    where = str(idx["uq_reservations_active_line"].dialect_options["postgresql"]["where"])
    assert "ACTIVE" in where and "source_line_id" in where
    checks = {c.name for c in r.constraints if isinstance(c, CheckConstraint)}
    assert "ck_reservations_quantity_positive" in checks

    b = Base.metadata.tables["inventory_balances"]
    bidx = {i.name: i for i in b.indexes}
    assert "uq_inventory_balances_key" in bidx and bidx["uq_inventory_balances_key"].unique
    bchecks = {c.name for c in b.constraints if isinstance(c, CheckConstraint)}
    assert "ck_inventory_balances_reserved_nonneg" in bchecks


def test_la_migracion_0043_declara_lo_mismo_que_el_orm():
    m = (BACKEND / "alembic" / "versions" / "0043_spec030_reservation.py").read_text(encoding="utf-8")
    assert 'revision = "0043_spec030_reservation"' in m and len("0043_spec030_reservation") <= 32
    assert 'down_revision = "0042_spec029_origin"' in m
    for token in ("uq_reservations_active_line", "ck_reservations_quantity_positive",
                  "uq_inventory_balances_key", "ck_inventory_balances_reserved_nonneg",
                  "reservation_ttl_days", "'ventas', 'submit'", "LEGACY_CREDIT_APPROVAL"):
        assert token in m, f"la migración no declara {token}"


def test_la_disponibilidad_se_lee_bajo_bloqueo_y_en_orden_determinista():
    """IMP-030-021/023: `lock_balance` bloquea y `confirmar_pedido` ordena antes de bloquear."""
    inv = INVENTORY.read_text(encoding="utf-8")
    assert "with_for_update()" in inv
    assert "def lock_balance" in inv and "def available_under_lock" in inv
    ventas = SALES.read_text(encoding="utf-8")
    cuerpo = ventas[ventas.index("def confirmar_pedido"):ventas.index("def liberar_pedido")]
    assert "sorted(" in cuerpo and "lock_balance(" in cuerpo
    assert cuerpo.index("sorted(") < cuerpo.index("lock_balance("), "bloquea antes de ordenar"
    assert "get_available(" not in cuerpo, "leyó disponible sin bloqueo"
    # `_reserve_order` leía y luego reservaba; ahora `reserve` bloquea por sí misma
    reserva = inv[inv.index("def reserve("):inv.index("def _close_reservation")]
    assert "lock_balance(" in reserva and "get_available(" not in reserva


def test_no_hay_planificador_local():
    """§60: sin cron, bucle, hilo ni APScheduler en ventas ni inventario."""
    for modulo in (SALES, INVENTORY, BACKEND / "app" / "modules" / "sales" / "api.py",
                   BACKEND / "app" / "modules" / "inventory" / "api.py"):
        texto = modulo.read_text(encoding="utf-8")
        for prohibido in ("apscheduler", "threading.Timer", "while True", "schedule.every",
                          "asyncio.create_task", "BackgroundTasks", "celery"):
            assert prohibido.lower() not in texto.lower(), f"{modulo.name}: {prohibido}"


def test_el_despacho_consume_y_no_libera():
    """R-D0-03-7: `confirm_shipment` marca FULFILLED, no RELEASED."""
    assert "confirm_shipment" in _funciones_que_llaman(SALES, "fulfill_reservation"), (
        "el despacho ya no consume la reserva")
    assert "confirm_shipment" not in _funciones_que_llaman(SALES, "release_reservation"), (
        "el despacho volvió a liberar en vez de consumir")


def test_el_permiso_de_emitir_existe_y_es_distinto_del_de_aprobar():
    setup = (BACKEND / "app" / "modules" / "setup" / "api.py").read_text(encoding="utf-8")
    assert re.search(r'"ventas":\s*\[[^\]]*"submit"', setup), "ventas:submit no está en el catálogo"
    api = (BACKEND / "app" / "modules" / "sales" / "api.py").read_text(encoding="utf-8")
    assert 'require_permission("ventas", "submit")' in api
    submit = api[api.index('"/orders/{order_id}/submit"'):api.index('"/orders/{order_id}/release"')]
    assert 'require_permission("ventas", "submit")' in submit
    release = api[api.index('"/orders/{order_id}/release"'):api.index('"/orders/{order_id}/reject"')]
    assert 'require_permission("ventas", "approve")' in release


def test_ningun_estado_superado_sobrevive_en_ventas():
    """`RESERVED` como estado de pedido desapareció del servicio y de la API."""
    for modulo in (SALES, BACKEND / "app" / "modules" / "sales" / "api.py"):
        texto = modulo.read_text(encoding="utf-8")
        codigo = "\n".join(linea for linea in texto.splitlines() if not linea.strip().startswith("#"))
        assert '"RESERVED"' not in codigo, f"{modulo.name} sigue usando RESERVED como estado"
        assert '"CREDIT_PENDING"' not in codigo, f"{modulo.name} sigue usando CREDIT_PENDING"


def test_las_reservas_manuales_y_las_de_pedido_se_distinguen():
    assert inv_service.RESERVATION_SOURCE_ORDER == "SALES_ORDER"
    assert inv_service.RESERVATION_SOURCE_MANUAL == "MANUAL"
    assert inv_service.RESERVATION_TRIGGER_ORDER == "ORDER_CONFIRMATION"
