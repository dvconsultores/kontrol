"""Spec 022 · guardias estructurales del put-away.

Leen el código. Defienden las fronteras que este ciclo podía romper en silencio:
no convertir la reserva en algo de ubicación, no absorber el picking, no
transferir entre almacenes, y no inventar la inteligencia de colocación que
`D0-14` difirió.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.modules.inventory import states

RAIZ = Path(__file__).resolve().parents[1] / "app"
INV = (RAIZ / "modules" / "inventory" / "service.py").read_text()
API = (RAIZ / "modules" / "inventory" / "api.py").read_text()


def _bloque(texto: str, inicio: str) -> str:
    """El cuerpo de una función, **sin comentarios ni docstring**.

    Un guardia que mirase el texto entero fallaría por la explicación de lo que
    prohíbe, que es justo donde esos nombres tienen que aparecer.
    """
    trozo = texto[texto.index(inicio):]
    siguiente = trozo.find("\ndef ", 1)
    cuerpo = trozo if siguiente < 0 else trozo[:siguiente]
    cuerpo = re.sub(r'"""..*?"""', "", cuerpo, flags=re.S)
    return "\n".join(l for l in cuerpo.splitlines() if not l.strip().startswith("#"))


# ------------------------------------------------------ la reserva no se toca
def test_el_putaway_no_toca_el_reservado():
    """`R-D0-14-2`: mover existencia física no altera el compromiso comercial."""
    cuerpo = _bloque(INV, "def putaway(")
    assert "qty_reserved" not in cuerpo, "el put-away escribe el contador de reserva"
    for prohibido in ("Reservation", "reserve(", "release_reservation", "SalesOrder"):
        assert prohibido not in cuerpo, f"el put-away toca la autoridad de la 030: {prohibido}"


def test_el_putaway_no_asigna_una_reserva_a_una_ubicacion():
    """`R-D0-14-4`: eso es de la Spec 031, no de esta."""
    cuerpo = _bloque(INV, "def putaway(")
    for prohibido in ("picking", "pick_list", "PickList", "allocation", "asignar_demanda"):
        assert prohibido not in cuerpo, f"el put-away absorbe la 031: {prohibido}"


def test_el_disponible_del_almacen_no_depende_de_la_fila_de_ubicacion_nula():
    """El defecto que bloqueó la Spec: leer una fila y llamarla disponible."""
    cuerpo = _bloque(INV, "def warehouse_sellable_on_hand(")
    assert "func.sum" in cuerpo, "el disponible sigue leyendo una sola fila"
    assert "location_id" not in cuerpo, "el disponible del almacén filtra por ubicación"
    assert "SELLABLE_STATES" in cuerpo, "suma estados no vendibles"


def test_el_disponible_tras_bloqueo_suma_las_ubicaciones():
    cuerpo = _bloque(INV, "def available_under_lock(")
    assert "warehouse_sellable_on_hand" in cuerpo
    assert "balance.qty_on_hand" not in cuerpo, "vuelve a leer el físico de una sola fila"


# --------------------------------------------------------- el estado no cambia
def test_el_putaway_no_cambia_el_estado_de_mercancia():
    """`R-D0-14-13`: es traslado de ubicación, no transición de estado."""
    cuerpo = _bloque(INV, "def putaway(")
    assert "source_state=estado, target_state=estado" in cuerpo
    assert "assert_transition" not in cuerpo, "el put-away invoca la matriz de D0-10"


def test_no_existe_la_arista_disponible_a_disponible():
    """`R-D0-14-13`: no se creó una transición falsa para poder ubicar."""
    assert not states.can_transition("DISPONIBLE", "DISPONIBLE")
    assert [t for t in states.ACTIVE_TRANSITIONS if t.source == t.target] == []


# ---------------------------------------------------------------- la frontera
def test_el_putaway_no_transfiere_entre_almacenes():
    """`R-D0-14-9`: eso es de la Spec 025."""
    cuerpo = _bloque(INV, "def _require_candidate_location(")
    assert "LOCATION_OTHER_WAREHOUSE" in cuerpo
    ejecutar = _bloque(INV, "def putaway(")
    assert "target_warehouse" not in ejecutar
    assert "_require_candidate_location" in ejecutar


def test_no_hay_slotting_automatico():
    """`R-D0-14-10`: sin recomendación, sin asignación, sin heurística."""
    cuerpo = _bloque(INV, "def putaway_candidates(")
    for prohibido in ("min(", "max(", "score", "recomend", "sugerid", "best", "mejor",
                      "rotation", "rotacion", "volumen", "familia"):
        assert prohibido not in cuerpo.lower(), f"heurística de colocación: {prohibido}"
    # Solo ordena para que la lista sea estable; no puntúa.
    assert "order_by" in cuerpo


def test_la_capacidad_no_filtra_ni_bloquea():
    """`R-D0-14-6`: informativa. Su unidad es texto libre y no puede rechazar."""
    for nombre in ("def putaway_candidates(", "def _require_candidate_location(", "def putaway("):
        cuerpo = _bloque(INV, nombre)
        for prohibido in ("capacity_units", "capacity_weight", "capacity_uom", "occupancy",
                          "ocupacion"):
            assert prohibido not in cuerpo, f"{nombre} usa la capacidad como regla: {prohibido}"
    # La API sí puede exponerla, pero declarando que no se aplica.
    assert '"enforced": False' in API


# ------------------------------------------------------------- la procedencia
def test_el_movimiento_lleva_origen_y_destino_de_ubicacion():
    cuerpo = _bloque(INV, "def putaway(")
    assert "source_location_id=source_location_id" in cuerpo
    assert "target_location_id=target_location_id" in cuerpo


def test_la_reconstruccion_lee_la_ubicacion_del_ledger():
    completo = INV[INV.index("def recompute_balances("):INV.index("def get_available(")]
    movimientos = completo[:completo.index("# 2. Aplicar reservas activas")]
    assert "m.target_location_id" in movimientos and "m.source_location_id" in movimientos
    assert "m.location_id" not in movimientos, "la reconstrucción vuelve a suponer la ubicación"


def test_la_validacion_de_la_ubicacion_precede_al_bloqueo():
    """Una ubicación inválida debe fallar antes de bloquear o mover nada."""
    cuerpo = _bloque(INV, "def putaway(")
    assert cuerpo.index("_require_candidate_location") < cuerpo.index("_lock_balance_at")
    assert cuerpo.index("_lock_balance_at") < cuerpo.index("qty_on_hand =")


def test_el_permiso_del_putaway_existe_en_el_catalogo():
    """La lección de la Spec 021: un permiso declarado y ausente es un contrato roto."""
    catalogo = (RAIZ / "modules" / "setup" / "api.py").read_text()
    usados = set(re.findall(r'require_permission\("(\w+)", "(\w+)"\)', API))
    for recurso, accion in sorted(usados):
        bloque = re.search(rf'"{recurso}": \[([^\]]+)\]', catalogo)
        assert bloque, f"el recurso «{recurso}» no está en el catálogo"
        assert f'"{accion}"' in bloque.group(1), f"«{recurso}:{accion}» no existe en el catálogo"


def test_no_hay_segunda_verdad_fisica():
    """`R-D0-14-5` regla 2: dónde está la mercancía lo dice el saldo, y solo él."""
    for prohibido in ("PutAwayLocation", "StorageLocationInventory", "current_location",
                      "LocationBalance", "PutAwayBalance"):
        assert not any(prohibido in py.read_text() for py in RAIZ.rglob("*.py")), prohibido


def test_la_api_expone_la_procedencia_del_movimiento():
    """Lo que no se expone no se puede auditar.

    El ledger guardaba estado y ubicación de origen y destino desde las Specs
    023 y 022, pero `movement_dict` no los devolvía: ni una prueba de extremo a
    extremo ni un auditor podían comprobar de dónde salió la mercancía. Lo
    encontró la e2e del put-away al no poder verificar su propio traslado.
    """
    cuerpo = _bloque(INV, "def movement_dict(")
    for campo in ("source_state", "target_state", "source_location_id",
                  "target_location_id", "base_quantity"):
        assert f'"{campo}"' in cuerpo, f"la API oculta {campo}"
