"""Spec 031 · guardias estructurales de la cola y la ruta de picking.

Leen el código. Defienden las fronteras que este ciclo podía romper en silencio:
no inventar prioridad ni política de lote, no recrear la ruta que ya es de la
Spec 008, no mover inventario al planificar y no absorber la ejecución física de
la Spec 032.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.spec_blocks import bloque_de_spec, cuerpo_de_simbolo

RAIZ = Path(__file__).resolve().parents[1] / "app"
SALES = (RAIZ / "modules" / "sales" / "service.py").read_text()
SALES_API = (RAIZ / "modules" / "sales" / "api.py").read_text()
MODELS = (RAIZ / "modules" / "sales" / "models.py").read_text()
MIGRACION = (Path(__file__).resolve().parents[1] / "alembic" / "versions"
             / "0049_spec031_picking_plan.py").read_text()


_bloque = cuerpo_de_simbolo



# ------------------------------------------------------------------ la cola
def test_la_cola_ordena_por_el_sello_de_entrada():
    """`R-D0-15-2/3`: `released_at` y desempate por `id`. Nunca `code`."""
    cuerpo = _bloque(SALES, "def picking_queue(")
    assert "SalesOrder.released_at.asc()" in cuerpo
    assert "SalesOrder.id.asc()" in cuerpo
    assert "submitted_at" not in cuerpo, "la cola volvió a ordenar por emisión"
    assert "SalesOrder.code" not in cuerpo, "desempate por un campo sin unicidad"
    assert "ORDER_HANDOFF_STATE" in cuerpo, "la elegibilidad dejó de ser RELEASED"


def test_no_hay_prioridad_inventada():
    """`R-D0-15-4`: cliente, manual, SLA y ruta siguen siendo `FUTURE` (`D0-03` §8)."""
    for prohibido in ("priority", "prioridad", "rush", "sla", "ranking", "urgent"):
        assert prohibido not in _bloque(SALES, "def picking_queue(").lower(), prohibido
    # El cuerpo de las dos clases, no «los 2000 caracteres siguientes a
    # `class PickList`»: esa ventana tapaba o destapaba campos según creciera el
    # fichero, que es la misma clase de frontera accidental que corregimos aquí.
    plan = cuerpo_de_simbolo(MODELS, "class PickList(").lower()
    linea = cuerpo_de_simbolo(MODELS, "class PickListLine(").lower()
    for prohibido in ("priority", "rush", "sla_"):
        assert prohibido not in plan and prohibido not in linea, \
            f"apareció un campo de prioridad: {prohibido}"


# ------------------------------------------------------------------ la ruta
def test_la_ruta_es_la_de_la_spec_008():
    """`R-D0-15-20`: se consume `physical_order_query`, no se recrea."""
    cuerpo = _bloque(SALES, "def _orden_fisico(")
    assert "physical_order_query" in cuerpo
    for prohibido in ("zone", "aisle", "rack", "level", "distance", "distancia", "nearest",
                      "shortest", "tsp"):
        assert prohibido not in cuerpo.lower(), f"segundo algoritmo de recorrido: {prohibido}"


def test_el_recorrido_es_estable():
    """Sin desempate final el orden de dos asignaciones en la misma ubicación
    lo decidiría la base, y el almacenista vería una ruta distinta cada vez."""
    cuerpo = _bloque(SALES, "def _resecuenciar(")
    assert "str(ln.id)" in cuerpo, "el recorrido no tiene desempate total"


# --------------------------------------------------- no se inventa selección
def test_no_hay_politica_de_lote_ni_de_serial():
    """`R-D0-15-21`: el ¶30 llega a producto; elegir entre lotes no se inventa."""
    # El alcance es el tramo entero de salida, no solo la 031: ninguna de las
    # cinco puede inventar una política de lote que el ¶30 no declara. Antes se
    # conseguía recortando «desde mi cabecera hasta el final del fichero», que
    # cubría también lo que no era de ventas.
    tramo = "\n".join(bloque_de_spec(SALES, n) for n in ("031", "032", "033", "034", "035"))
    tramo = re.sub(r'"""..*?"""', "", tramo, flags=re.S)
    for prohibido in ("fefo", "fifo", "expiry_date", "vencimiento", "lot_priority"):
        assert prohibido not in tramo.lower(), f"política inventada: {prohibido}"


# ------------------------------------------- planificar no toca el inventario
def test_planificar_no_escribe_inventario():
    """`R-D0-15-14`: ni existencia, ni reservado, ni movimiento."""
    for nombre in ("def allocate(", "def confirm_plan(", "def _cerrar_plan("):
        cuerpo = _bloque(SALES, nombre)
        for prohibido in ("qty_on_hand =", "qty_reserved =", "record_movement", "InventoryMovement(",
                          "putaway(", "reclassify("):
            assert prohibido not in cuerpo, f"{nombre} escribe inventario: {prohibido}"


def test_la_031_no_libera_la_reserva_comercial():
    """`R-D0-15-13`: liberar una reserva es de la Spec 030 y solo de ella."""
    for nombre in ("def _cerrar_plan(", "def cancel_plan(", "def invalidate_plan("):
        cuerpo = _bloque(SALES, nombre)
        for prohibido in ("release_if_active", "release_reservation", "_liberar_reservas",
                          "fulfill_reservation"):
            assert prohibido not in cuerpo, f"{nombre} toca la reserva comercial: {prohibido}"


def test_la_031_no_ejecuta_el_picking_fisico():
    """La Spec 032 es la dueña del efecto físico; aquí no se simula."""
    # El bloque se pide por su marcador: sin frontera propia se comería la
    # ejecución física, que sí escribe `CLOSED` y sí es picking, y la guardia
    # afirmaría lo contrario de lo que quiere decir.
    bloque_031 = bloque_de_spec(SALES, "031")
    bloque_031 = re.sub(r'"""..*?"""', "", bloque_031, flags=re.S)
    assert '"CLOSED"' not in bloque_031, "la 031 cierra un plan que nadie ejecutó"
    for prohibido in ("consolidar", "empacar", "shipment", "invoice"):
        assert prohibido not in bloque_031.lower(), f"absorbe aguas abajo: {prohibido}"


# ---------------------------------------------- la frontera con el pedido
def test_crear_un_plan_no_mueve_el_pedido():
    """`R-D0-15-18`: solo `confirm_plan` lo lleva a `PREPARING`."""
    creacion = _bloque(SALES, "def create_picklist(")
    assert 'order.status = "PREPARING"' not in creacion, \
        "crear el borrador vuelve a sacar el pedido de la cola"
    assert 'order.status = "PREPARING"' in _bloque(SALES, "def confirm_plan(")


def test_existe_la_vuelta_a_la_cola():
    """`R-D0-15-19`: sin esta arista un plan cancelado vararía el pedido."""
    from app.modules.sales import service as sales_service

    assert "RELEASED" in sales_service.ORDER_TRANSITIONS["PREPARING"]


# ------------------------------------------------------ esquema y permisos
def test_el_estado_del_plan_esta_restringido_en_la_base():
    """Un `String(32)` sin `CHECK` acepta cualquier cosa, y el ciclo de vida
    dejaría de ser un ciclo de vida en cuanto alguien escribiera otra palabra."""
    assert "pick_list_status" in MIGRACION
    assert "'DRAFT', 'CONFIRMED', 'CLOSED', 'CANCELLED', 'INVALIDATED'" in MIGRACION
    assert "pick_list_status" in MODELS, "la restricción solo vive en la migración"
    assert "uq_pick_lists_active_order" in MIGRACION and "uq_pick_lists_active_order" in MODELS


def test_la_asignacion_no_admite_forma_a_medias():
    assert "pick_list_line_allocation_shape" in MIGRACION
    assert "pick_list_line_allocation_shape" in MODELS


def test_los_permisos_del_picking_existen_en_el_catalogo():
    """La lección de la Spec 021: un permiso declarado y ausente es un contrato
    roto que solo se descubre cuando alguien intenta usar la pantalla."""
    catalogo = (RAIZ / "modules" / "setup" / "api.py").read_text()
    # Solo el bloque de la 031. Antes llegaba hasta `/shipments` y auditaba de
    # paso los permisos de la 032, la 033, la 034 y la 035; cada una tiene hoy
    # su propia guardia igual a esta, así que no se pierde cobertura.
    picking = bloque_de_spec(SALES_API, "031")
    usados = set(re.findall(r'require_permission\("(\w+)", "(\w+)"\)', picking))
    assert usados, "el bloque de picking no declara ningún permiso"
    for recurso, accion in sorted(usados):
        bloque = re.search(rf'"{recurso}": \[([^\]]+)\]', catalogo)
        assert bloque, f"el recurso «{recurso}» no está en el catálogo"
        assert f'"{accion}"' in bloque.group(1), f"«{recurso}:{accion}» no existe en el catálogo"


def test_la_migracion_no_inventa_historia():
    """No hay backfill: no existe dato del que deducir de qué ubicación salió
    una línea que nunca tuvo ubicación."""
    assert "UPDATE pick_list_lines" not in MIGRACION
    for col in ("location_id", "order_line_id", "state", "sequence"):
        assert f'sa.Column("{col}"' in MIGRACION
    assert MIGRACION.count("nullable=True") >= 8, "una columna nueva nació obligatoria"
