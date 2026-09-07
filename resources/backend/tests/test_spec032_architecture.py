"""Spec 032 · guardias estructurales de la preparación física.

Leen el código. Defienden las fronteras que este ciclo podía romper en silencio:
no sacar mercancía del almacén —eso es del despacho—, no confirmar por su cuenta
—eso es el control independiente de la 033—, no inventar motivos de diferencia ni
política de selección, y no dejar que el mismo compromiso se reste dos veces.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.modules.inventory import states
from app.modules.sales.models import PICK_DISCREPANCY_KINDS
from tests.spec_blocks import bloque_de_spec, cuerpo_de_simbolo

RAIZ = Path(__file__).resolve().parents[1] / "app"
SALES = (RAIZ / "modules" / "sales" / "service.py").read_text()
SALES_API = (RAIZ / "modules" / "sales" / "api.py").read_text()
INV = (RAIZ / "modules" / "inventory" / "service.py").read_text()
MIGRACION = (Path(__file__).resolve().parents[1] / "alembic" / "versions"
             / "0050_spec032_pick_execution.py").read_text()
# El bloque se pide por su marcador de Spec, no se recorta por la función
# siguiente: ver `tests/spec_blocks.py` y la invariante que documenta.
BLOQUE_032 = bloque_de_spec(SALES, "032")
BLOQUE_API_032 = bloque_de_spec(SALES_API, "032")


_bloque = cuerpo_de_simbolo



def _limpio(texto: str) -> str:
    """Sin docstrings **ni comentarios**.

    Un guardia que mirase el texto entero fallaría por la explicación de lo que
    prohíbe, que es justo donde esos nombres tienen que aparecer.
    """
    sin_doc = re.sub(r'"""..*?"""', "", texto, flags=re.S)
    return "\n".join(x for x in sin_doc.splitlines() if not x.strip().startswith("#"))


# ------------------------------------------------- las aristas que se activan
def test_las_dos_aristas_del_picking_estan_declaradas_con_su_dueña():
    """La matriz de `D0-10` las declaró para 031/032 y las dejó denegadas."""
    for origen, destino in (("DISPONIBLE", "PICKING"), ("PICKING", "PREPARADO")):
        assert states.can_transition(origen, destino), f"{origen} → {destino} no está activa"
        t = next(x for x in states.ACTIVE_TRANSITIONS if x.source == origen and x.target == destino)
        assert t.owner_spec == "032", f"{origen} → {destino} tiene otra dueña"
        assert t.evidence, "una arista sin evidencia documental no entra en la tabla"


def test_ni_picking_ni_preparado_son_vendibles():
    """Lo que está en preparación no se puede volver a vender."""
    assert not states.is_sellable("PICKING") and not states.is_sellable("PREPARADO")
    assert not states.is_reservable("PICKING") and not states.is_reservable("PREPARADO")


# ------------------------------------------------------- nada sale del almacén
def test_preparar_no_saca_mercancia_del_almacen():
    """La salida física es del despacho (`POL-D0-002` §8). Aquí solo cambia
    de estado de custodia y de ubicación."""
    for nombre in ("def execute_pick(", "def consolidate("):
        cuerpo = _bloque(BLOQUE_032, nombre)
        for prohibido in ("SALIDA_DESPACHO", "record_movement", "qty_on_hand =", "ship(",
                          "fulfill_reservation"):
            assert prohibido not in cuerpo, f"{nombre} saca mercancía: {prohibido}"


def test_la_extraccion_pasa_por_el_motor_canonico():
    """`R-D0-10`: nadie más que `reclassify` toca `InventoryBalance.state`."""
    cuerpo = _bloque(BLOQUE_032, "def execute_pick(")
    assert "inv_service.reclassify(" in cuerpo
    assert 'target_state="PICKING"' in cuerpo
    assert "InventoryBalance" not in cuerpo, "escribe el saldo por fuera del motor"


def test_la_consolidacion_reclasifica_y_traslada():
    cuerpo = _bloque(BLOQUE_032, "def consolidate(")
    assert 'source_state="PICKING"' in cuerpo and 'target_state="PREPARADO"' in cuerpo
    assert "inv_service.putaway(" in cuerpo, "el pedido no se traslada al área"
    assert "source_location_id=str(linea.location_id)" in cuerpo, "se pierde de dónde salió"


# --------------------------------------------- la 032 no confirma ni factura
def test_la_032_no_hace_el_control_independiente():
    """¶61: es un control **independiente** después del picking. Es de la 033."""
    limpio = _limpio(BLOQUE_032)
    for prohibido in ("OrderConfirmation", "confirmar_pedido", "second_check", "verificacion",
                      "aprobar", "certif"):
        assert prohibido not in limpio, f"la 032 se autocertifica: {prohibido}"


def test_la_032_no_factura_ni_despacha():
    limpio = _limpio(BLOQUE_032).lower()
    for prohibido in ("invoice", "factura", "shipment", "despacho", "control_number", "tax"):
        assert prohibido not in limpio, f"absorbe aguas abajo: {prohibido}"


def test_la_032_no_crea_ni_libera_reservas_por_su_cuenta():
    """Solo llama a las dos operaciones que `POL-D0-002` §8 autoriza."""
    cuerpo = _bloque(BLOQUE_032, "def execute_pick(")
    assert "inv_service.reserve(" not in cuerpo, "la 032 crea reservas"
    assert "release_if_active" not in cuerpo, "la 032 libera reservas enteras"
    assert "inv_service.consume_on_pick(" in cuerpo
    assert "inv_service.release_picking_shortage(" in cuerpo


# ------------------------------------------------------- no se inventa nada
def test_los_motivos_son_los_cinco_del_proceso():
    """¶48-52. Ni uno más, ni uno menos, ni con otro nombre."""
    assert PICK_DISCREPANCY_KINDS == (
        "PRODUCTO_NO_LOCALIZADO", "CANTIDAD_INSUFICIENTE", "UBICACION_INCORRECTA",
        "DIFERENCIA_SISTEMA_FISICO", "MERCANCIA_DANADA")
    for motivo in PICK_DISCREPANCY_KINDS:
        assert motivo in MIGRACION, f"{motivo} no está restringido en la base"


def test_no_hay_seleccion_inventada_ni_sustitucion():
    limpio = _limpio(BLOQUE_032).lower()
    for prohibido in ("fefo", "fifo", "expiry", "sustitu", "substitute", "alternativ"):
        assert prohibido not in limpio, f"política inventada: {prohibido}"


def test_no_se_replanifica_al_encontrar_diferencia():
    """Ninguna autoridad lo permite; lo que sí manda `POL-D0-002` §8 es liberar
    la diferencia con evidencia."""
    cuerpo = _bloque(BLOQUE_032, "def execute_pick(")
    for prohibido in ("allocate(", "picking_candidates(", "_resecuenciar(", "location_id="):
        assert prohibido not in cuerpo or "linea.location_id" in cuerpo, prohibido
    assert "sales_service.allocate" not in cuerpo


def test_la_identidad_de_lote_y_serial_se_preserva():
    """No se recoge de un lote distinto del asignado."""
    for nombre in ("def execute_pick(", "def consolidate("):
        cuerpo = _bloque(BLOQUE_032, nombre)
        assert "lot_id=linea.lot_id" in cuerpo and "serial_id=linea.serial_id" in cuerpo


# ------------------------------------------------------- lo planificado vive
def test_lo_recogido_no_pisa_lo_planificado():
    """Sin las dos cifras no hay diferencia que registrar (¶47, ¶53)."""
    cuerpo = _bloque(BLOQUE_032, "def execute_pick(")
    assert "linea.picked_base_quantity = recogido" in cuerpo
    assert "linea.base_quantity =" not in cuerpo, "la ejecución sobrescribió la intención"


def test_recoger_de_menos_sin_motivo_esta_prohibido_tambien_en_la_base():
    assert "pick_list_line_shortfall_reason" in MIGRACION
    modelos = (RAIZ / "modules" / "sales" / "models.py").read_text()
    assert "pick_list_line_shortfall_reason" in modelos, "la restricción solo vive en la migración"


def test_solo_la_consolidacion_cierra_el_plan():
    """`D0-15`: `CLOSED` es ejecución física terminada, no planificación."""
    assert '"CLOSED"' in _bloque(BLOQUE_032, "def consolidate(")
    assert '"CLOSED"' not in _bloque(BLOQUE_032, "def execute_pick(")


def test_el_pedido_llega_a_preparado_y_no_mas_alla():
    """`ADR-D0-012`: `PREPARING → PREPARED`. `CONFIRMED` es de la 033."""
    from app.modules.sales import service as sales_service

    assert "PREPARED" in sales_service.ORDER_TRANSITIONS["PREPARING"]
    assert "PREPARED" in sales_service.ORDER_TRANSITIONS
    # `CONFIRMED` ya existe: lo añadió la Spec 033, que es su dueña. Lo que esta
    # guardia sigue defendiendo es que **la 032** no lo escriba.
    assert '"CONFIRMED"' not in _bloque(BLOQUE_032, "def consolidate("), "la 032 confirma el pedido"
    assert "PREPARED" in sales_service.ORDER_RESERVED_STATES, \
        "un pedido preparado perdió su reserva antes de despacharse"


def test_los_permisos_de_la_preparacion_existen_en_el_catalogo():
    catalogo = (RAIZ / "modules" / "setup" / "api.py").read_text()
    bloque = BLOQUE_API_032
    usados = set(re.findall(r'require_permission\("(\w+)", "(\w+)"\)', bloque))
    assert usados, "el bloque de preparación no declara ningún permiso"
    for recurso, accion in sorted(usados):
        m = re.search(rf'"{recurso}": \[([^\]]+)\]', catalogo)
        assert m and f'"{accion}"' in m.group(1), f"«{recurso}:{accion}» no existe en el catálogo"


def test_la_migracion_no_inventa_historia():
    assert "UPDATE pick_list_lines" not in MIGRACION
    assert "UPDATE reservations SET picked" not in MIGRACION
    # `picked_base_quantity` de las reservas nace en cero por defecto del motor,
    # que es cierto: nada se había extraído antes de que esta Spec existiera.
    assert 'server_default="0"' in MIGRACION


def test_el_contador_solo_resta_lo_aun_no_extraido():
    """El defecto que borraría el compromiso de otro pedido al despachar."""
    cuerpo = _bloque(INV, "def _close_reservation(")
    assert "reservation.picked_base_quantity" in cuerpo
    assert "balance.qty_reserved = max(_dec(balance.qty_reserved) - _base_qty(reservation)" not in cuerpo
