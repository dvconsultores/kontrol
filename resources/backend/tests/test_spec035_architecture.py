"""Spec 035 · guardias estructurales del despacho.

Leen el código. Defienden la compuerta del ¶103 —que hasta este ciclo era una
función que aprobaba siempre mientras su docstring prometía bloquear— y la
salida física: en cantidad base, desde `PREPARADO`, sin emitir permisos ni
simular verificaciones que nadie puede hacer sin API oficial.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.spec_blocks import bloque_de_spec, cuerpo_de_simbolo, limpio

RAIZ = Path(__file__).resolve().parents[1] / "app"
SALES = (RAIZ / "modules" / "sales" / "service.py").read_text()
SALES_API = (RAIZ / "modules" / "sales" / "api.py").read_text()
MODELOS = (RAIZ / "modules" / "sales" / "models.py").read_text()
MIGRACION = (Path(__file__).resolve().parents[1] / "alembic" / "versions"
             / "0053_spec035_dispatch_gate.py").read_text()
# El bloque se pide por su marcador de Spec: ver `tests/spec_blocks.py`.
BLOQUE = bloque_de_spec(SALES, "035")
BLOQUE_API = bloque_de_spec(SALES_API, "035")


_bloque = cuerpo_de_simbolo



# --------------------------------------------------------- la compuerta ¶103
def test_la_compuerta_comprueba_las_tres_cosas():
    """«Pedido preparado + Pedido confirmado + Factura emitida»."""
    cuerpo = _bloque(SALES, "def validate_shipment(")
    assert "OrderConfirmation" in cuerpo, "no comprueba la confirmación independiente"
    assert "SalesInvoice" in cuerpo, "no comprueba la factura"
    assert 'factura.status != "EMITTED"' in cuerpo, "acepta una factura solo generada"
    assert "regulatory_service.evaluate_shipment(" in cuerpo, "no consulta la regulación"


def test_la_compuerta_ya_no_aprueba_sin_mirar():
    """El defecto que este ciclo encontró: aprobar siempre."""
    cuerpo = _bloque(SALES, "def validate_shipment(")
    aprobacion = cuerpo.index('shipment.validation_status = "APPROVED"')
    for comprobacion in ("DISPATCH_NOT_CONFIRMED", "DISPATCH_NOT_INVOICED",
                         "DISPATCH_REGULATORY_BLOCKED", "DISPATCH_TRANSPORT_REQUIRED"):
        assert comprobacion in cuerpo, f"falta la comprobación {comprobacion}"
        assert cuerpo.index(comprobacion) < aprobacion, f"{comprobacion} se comprueba tras aprobar"


def test_la_regulacion_bloquea_de_verdad():
    cuerpo = _bloque(SALES, "def validate_shipment(")
    assert 'evaluacion["status"] == "BLOCKED"' in cuerpo
    assert "raise ConflictError(" in cuerpo[cuerpo.index('evaluacion["status"] == "BLOCKED"'):]


def test_solo_un_pedido_facturado_pasa_a_despacho():
    """¶101. Y la deuda que este tramo dejó anotada, cerrada en la máquina."""
    from app.modules.sales import service as s

    assert {k for k, v in s.ORDER_TRANSITIONS.items() if "SHIPPED" in v} == {"INVOICED"}
    creacion = _bloque(SALES, "def create_shipment(")
    assert '"INVOICED"' in creacion and "ORDER_NOT_SHIPPABLE" in creacion


# ------------------------------------------------------- la salida física
def test_la_salida_es_en_cantidad_base():
    """Despachar dos cajas de doce saca veinticuatro unidades, no dos."""
    cuerpo = _bloque(SALES, "def confirm_shipment(")
    assert "line.base_quantity" in cuerpo
    assert "quantity=-line.quantity" not in cuerpo, "volvió la cantidad comercial con signo"


def test_la_salida_sale_de_preparado():
    """La Spec 032 dejó la mercancía en `PREPARADO`, no en `DISPONIBLE`."""
    cuerpo = _bloque(SALES, "def confirm_shipment(")
    assert 'source_state="PREPARADO"' in cuerpo and 'target_state="DESPACHADO"' in cuerpo
    assert "consolidation_location_id" in cuerpo, "no sale del Área de Confirmación"
    assert "SALIDA_DESPACHO" not in cuerpo, "sigue descontando de la fila equivocada"


def test_la_arista_de_despacho_esta_declarada_con_su_dueña():
    from app.modules.inventory import states

    assert states.can_transition("PREPARADO", "DESPACHADO")
    t = next(x for x in states.ACTIVE_TRANSITIONS
             if x.source == "PREPARADO" and x.target == "DESPACHADO")
    assert t.owner_spec == "035" and t.evidence
    assert not states.can_transition("DESPACHADO", "VENDIDO"), \
        "se activó una arista que ningún evento del proceso escribe"


def test_la_salida_consume_la_reserva_y_no_la_libera():
    cuerpo = _bloque(SALES, "def confirm_shipment(")
    assert "fulfill_reservation" in cuerpo
    assert "release_if_active" not in cuerpo, "el despacho libera en vez de consumir"


def test_el_despacho_es_idempotente():
    cuerpo = _bloque(SALES, "def confirm_shipment(")
    assert cuerpo.index("shipment.dispatched_at is not None") < cuerpo.index("SHIPMENT_NOT_VALIDATED")


# ------------------------------------------------------------- las fronteras
def test_el_despacho_no_emite_permisos_ni_verifica_en_linea():
    """Spec 044 v1: registra, valida, adjunta y bloquea. **No emite.**"""
    sin_comentarios = limpio(BLOQUE)
    for prohibido in ("requests.", "httpx.", "urlopen", "emit_permit", "issue_permit",
                      "verificado_en_linea", "sica_api", "sigesai_api"):
        assert prohibido not in sin_comentarios, \
            f"el despacho inventa emisión o verificación: {prohibido}"


def test_el_despacho_no_factura_ni_devuelve():
    sin_comentarios = limpio(BLOQUE)
    for prohibido in ("emit_document", "generate_invoice", "SalesReturn", "CreditNote",
                      "devolucion"):
        assert prohibido not in sin_comentarios, f"absorbe otra Spec: {prohibido}"


def test_un_pedido_no_se_despacha_dos_veces_ni_en_la_base():
    assert "uq_shipments_live_order" in MIGRACION
    assert "uq_shipments_live_order" in MODELOS, "la restricción solo vive en la migración"


def test_el_despacho_guarda_con_que_factura_sale():
    """¶106: «la mercancía sale del almacén **con su factura**»."""
    assert "invoice_id" in cuerpo_de_simbolo(MODELOS, "class Shipment(")
    assert "shipment.invoice_id = str(factura.id)" in SALES


def test_los_permisos_del_despacho_existen_en_el_catalogo():
    catalogo = (RAIZ / "modules" / "setup" / "api.py").read_text()
    usados = set(re.findall(r'require_permission\("(\w+)", "(\w+)"\)', BLOQUE_API))
    assert usados, "el bloque de despacho no declara ningún permiso"
    for recurso, accion in sorted(usados):
        m = re.search(rf'"{recurso}": \[([^\]]+)\]', catalogo)
        assert m and f'"{accion}"' in m.group(1), f"«{recurso}:{accion}» no existe en el catálogo"


def test_la_migracion_es_aditiva_y_no_inventa_historia():
    assert "UPDATE shipments" not in MIGRACION
    assert 'sa.Column("invoice_id", sa.String(36), nullable=True)' in MIGRACION


def test_el_transporte_se_valida_por_empresa():
    """El ¶105 admite transportista, cliente o responsable; ninguno ajeno."""
    creacion = _bloque(SALES, "def create_shipment(")
    assert "_require_vehicle(" in creacion and "_require_driver(" in creacion
    for helper in ("def _require_vehicle(", "def _require_driver("):
        cuerpo = _bloque(SALES, helper)
        assert "company_id" in cuerpo and "NotFoundError" in cuerpo, (
            f"{helper} no comprueba el dueño")


def test_lo_que_sale_no_se_escribe_a_mano():
    """§21: sin autoridad para el despacho parcial, la cantidad no se teclea."""
    creacion = _bloque(SALES, "def create_shipment(")
    assert "_lineas_consolidadas(" in creacion, "el despacho ya no deriva sus líneas"
    derivadas = _bloque(SALES, "def _lineas_consolidadas(")
    assert "picked_base_quantity" in derivadas, "no deriva de lo que se recogió de verdad"
    assert 'PickList.status == "CLOSED"' in derivadas, "deriva de un plan sin consolidar"
    # Y no cuelga una presentación a una cifra que es de unidades base: ese
    # desajuste es el que produjo la salida equivocada que este ciclo corrigió.
    assert '"presentation_id": p.presentation_id' in derivadas
