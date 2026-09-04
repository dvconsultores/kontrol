"""Spec 021 · guardias estructurales de la confirmación de inventario.

Leen el código, no lo ejecutan. Defienden las tres fronteras que este ciclo
podía romper sin que ninguna prueba funcional se enterase: no ser el motor de
inventario, no absorber el flujo de incidencias de la 020, y no ubicar nada, que
es de la 022.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.modules.inventory import states
from app.modules.purchasing import models as pmodels
from app.modules.purchasing import service as ap

RAIZ = Path(__file__).resolve().parents[1] / "app"
SERVICE = (RAIZ / "modules" / "purchasing" / "service.py").read_text()
API = (RAIZ / "modules" / "purchasing" / "api.py").read_text()


def _bloque(texto: str, inicio: str) -> str:
    """El cuerpo de una función, hasta la siguiente definición de primer nivel."""
    trozo = texto[texto.index(inicio):]
    siguiente = trozo.find("\ndef ", 1)
    return trozo if siguiente < 0 else trozo[:siguiente]


# ------------------------------------------------- no es el motor de inventario
def test_la_confirmacion_no_escribe_saldos_ni_movimientos():
    """Todo pasa por la autoridad canónica de la Spec 023."""
    cuerpo = _bloque(SERVICE, "def confirmar_inventario(")
    assert "inv_service.reclassify(" in cuerpo
    for prohibido in ("InventoryMovement(", "InventoryBalance(", "qty_on_hand", "_get_balance"):
        assert prohibido not in cuerpo, f"la 021 toca el motor directamente: {prohibido}"


def test_la_confirmacion_no_duplica_la_matriz_de_transiciones():
    """Declara qué pide; quién puede es de `ADR-D0-010` v2 y lo aplica la 023."""
    destinos = set(pmodels.CONFIRMATION_TARGET_STATES)
    assert destinos == {"DISPONIBLE", "RECHAZADO"}, destinos
    # Y cada par que la 021 puede pedir tiene que existir en la matriz real.
    for origen in ("RECIBIDO", "CUARENTENA"):
        for destino in destinos:
            assert states.can_transition(origen, destino), f"{origen}→{destino} no está declarada"


def test_la_confirmacion_no_puede_pedir_una_arista_desde_disponible():
    """`R-D0-10-10`: ninguna arista activa sale de lo vendible, y la 021 no la abre."""
    assert "DISPONIBLE" not in {t.source for t in states.ACTIVE_TRANSITIONS}
    cuerpo = _bloque(SERVICE, "def confirmar_inventario(")
    assert 'source_state") or inv_states.RECEIVED_STATE' in cuerpo
    origenes = set(re.findall(r"source_state IN \(([^)]+)\)", SERVICE))
    assert not origenes or "DISPONIBLE" not in "".join(origenes)


# --------------------------------------------------- no absorbe la Spec 020
def test_la_confirmacion_consume_incidencias_pero_no_las_resuelve():
    cuerpo = _bloque(SERVICE, "def confirmar_inventario(")
    assert "resultado_de_incidencias(" in cuerpo, "no consulta el contrato de la 020"
    for prohibido in ("resolver_incidencia", "escalar_incidencia", "registrar_incidencia",
                      "INCIDENT_RESOLUTIONS", "ReceiptIncident("):
        assert prohibido not in cuerpo, f"la 021 está haciendo trabajo de la 020: {prohibido}"


def test_la_confirmacion_no_reinterpreta_texto_libre_de_la_incidencia():
    """Consume el resultado estructurado, no la descripción."""
    cuerpo = _bloque(SERVICE, "def confirmar_inventario(")
    assert "description" not in cuerpo
    assert "escalation_notes" not in cuerpo


# --------------------------------------------------- no absorbe la Spec 022
def test_la_confirmacion_no_ubica_nada():
    cuerpo = _bloque(SERVICE, "def confirmar_inventario(")
    assert "location_id=None" in cuerpo, "la ubicación debe viajar nula: colocar es de la 022"
    for prohibido in ("WarehouseLocation", "put_away", "putaway", "asignar_ubicacion",
                      "location_id=receipt", "zone_id"):
        assert prohibido not in cuerpo, f"la 021 está ubicando: {prohibido}"


def test_no_existe_endpoint_de_put_away_en_compras():
    for prohibido in ("put-away", "putaway", "ubicacion", "/locations"):
        assert prohibido not in API, f"la 021 expuso una ruta de la 022: {prohibido}"


# ------------------------------------------------------------ la unidad base
def test_todo_el_calculo_es_en_cantidad_base():
    """Contar cajas y confirmarlas contra unidades no concilia nada."""
    for nombre in ("def confirmar_inventario(", "def registrar_conteo(", "def _base_recibida("):
        cuerpo = _bloque(SERVICE, nombre)
        assert "quantity_accepted" not in cuerpo, f"{nombre} usa la cantidad tecleada"
    assert "counted_base_quantity" in SERVICE


def test_la_confirmacion_no_recalcula_el_factor():
    """`P23`: cambiar el maestro no puede reinterpretar una recepción histórica."""
    cuerpo = _bloque(SERVICE, "def confirmar_inventario(")
    for prohibido in ("uom_engine", "to_base(", "factor_to_base", "conversion_factor"):
        assert prohibido not in cuerpo, f"la 021 reinterpreta la conversión: {prohibido}"


# --------------------------------------------------------------- las fronteras
def test_la_confirmacion_no_toca_pedidos_ni_reservas():
    cuerpo = _bloque(SERVICE, "def confirmar_inventario(")
    for prohibido in ("SalesOrder", "Reservation", "release_reservation", "reserve("):
        assert prohibido not in cuerpo, f"la 021 toca la autoridad de la 030: {prohibido}"


def test_confirmar_no_es_aceptar():
    """Dos actos distintos con dos campos distintos: `status` y `confirmation_status`."""
    assert "confirmation_status" in SERVICE
    aceptar = _bloque(SERVICE, "def accept_receipt(")
    assert "confirmation_status" not in aceptar, "aceptar no puede confirmar por su cuenta"
    confirmar = _bloque(SERVICE, "def confirmar_inventario(")
    assert 'receipt.status = ' not in confirmar, "confirmar no puede cambiar el estado del documento"


def test_la_aceptacion_deja_la_mercancia_en_recibido():
    aceptar = _bloque(SERVICE, "def accept_receipt(")
    assert "state=inv_states.RECEIVED_STATE" in aceptar
    assert '"DISPONIBLE"' not in aceptar, "la aceptación vuelve a saltar a disponible"


def test_los_permisos_declarados_en_la_matriz_existen_en_el_catalogo():
    """Un permiso inventado en la matriz es un contrato que nadie puede cumplir."""
    catalogo = (RAIZ / "modules" / "setup" / "api.py").read_text()
    declarados = {t.permission for t in states.ACTIVE_TRANSITIONS}
    for permiso in sorted(declarados):
        recurso, accion = permiso.split(":")
        bloque = re.search(rf'"{recurso}": \[([^\]]+)\]', catalogo)
        assert bloque, f"el recurso «{recurso}» no está en el catálogo de permisos"
        assert f'"{accion}"' in bloque.group(1), f"«{permiso}» no existe en el catálogo"


def test_la_confirmacion_exige_su_propio_permiso():
    assert 'require_permission("inventario", "confirm")' in API
    assert API.count('require_permission("inventario", "confirm")') >= 2


def test_el_conteo_solo_admite_las_diferencias_del_proceso():
    """Etapa 6, literal: cantidad, SKU, presentación, referencia, unidad de medida."""
    assert pmodels.COUNT_DIFFERENCE_KINDS == (
        "CANTIDAD", "SKU", "PRESENTACION", "REFERENCIA", "UNIDAD_MEDIDA")
    assert ap.COUNT_DIFFERENCE_KINDS is pmodels.COUNT_DIFFERENCE_KINDS
