"""Spec 033 · guardias estructurales del control independiente.

Leen el código. Defienden lo que hace que un control sea un control: que compare
contra el pedido y no contra la preparación, que el veredicto lo calcule el
backend y no llegue del navegador, que lo firme alguien distinto de quien
preparó, y que no toque una sola unidad de inventario.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.modules.sales.models import CONFIRMATION_DIFFERENCE_KINDS, CONFIRMATION_STATUSES

RAIZ = Path(__file__).resolve().parents[1] / "app"
SALES = (RAIZ / "modules" / "sales" / "service.py").read_text()
SALES_API = (RAIZ / "modules" / "sales" / "api.py").read_text()
MODELOS = (RAIZ / "modules" / "sales" / "models.py").read_text()
MIGRACION = (Path(__file__).resolve().parents[1] / "alembic" / "versions"
             / "0051_spec033_order_confirmation.py").read_text()
# El corte es la cabecera de la Spec 034: sin él este bloque se comería la
# facturación, que sí factura, y la guardia afirmaría lo contrario de lo que
# quiere decir. Mismo cuidado que necesitaron la 031 y la 032.
BLOQUE = SALES[SALES.index("# Spec 033 · confirmación independiente"):
               SALES.index("# Spec 034 · liberación y facturación")]


def _bloque(texto: str, inicio: str) -> str:
    """El cuerpo de una función, sin docstring ni comentarios."""
    trozo = texto[texto.index(inicio):]
    siguiente = trozo.find("\ndef ", 1)
    cuerpo = trozo if siguiente < 0 else trozo[:siguiente]
    cuerpo = re.sub(r'"""..*?"""', "", cuerpo, flags=re.S)
    return "\n".join(x for x in cuerpo.splitlines() if not x.strip().startswith("#"))


def _limpio(texto: str) -> str:
    sin_doc = re.sub(r'"""..*?"""', "", texto, flags=re.S)
    return "\n".join(x for x in sin_doc.splitlines() if not x.strip().startswith("#"))


# ----------------------------------------------- se compara contra el pedido
def test_lo_requerido_sale_del_pedido_y_no_de_la_preparacion():
    """`R-D0-12-2`: «comparar la preparación consigo misma no es un control»."""
    cuerpo = _bloque(SALES, "def _requerido_de(")
    assert "linea.base_quantity" in cuerpo and "linea.quantity" in cuerpo
    confirmar = _bloque(BLOQUE, "def confirm_order(")
    assert "requerido = _requerido_de(linea)" in confirmar
    assert "requerido = preparado" not in confirmar, "lo requerido salió de la preparación"


def test_las_tres_cifras_no_se_colapsan():
    for columna in ("required_base_quantity", "prepared_base_quantity", "checked_base_quantity"):
        assert columna in MODELOS, f"falta {columna}"
        assert columna in MIGRACION


def test_el_veredicto_lo_calcula_el_backend():
    """Un control cuyo resultado llega del navegador no es un control."""
    cuerpo = SALES_API[SALES_API.index("class ConfirmationLineBody"):
                       SALES_API.index('@router.post("/shipments"')]
    for prohibido in ("status:", "result:", "conforms:", "difference_kind:"):
        assert prohibido not in cuerpo, f"el cliente envía el veredicto: {prohibido}"
    assert "_dictamen_de_linea" in SALES


def test_el_dictamen_es_determinista_y_ordenado():
    cuerpo = _bloque(SALES, "def _dictamen_de_linea(")
    for motivo in ("LINEA_FALTANTE", "CANTIDAD", "PRESENTACION", "CONDICION"):
        assert motivo in cuerpo, f"el dictamen no contempla {motivo}"
    assert cuerpo.index("LINEA_FALTANTE") < cuerpo.index('"CANTIDAD"')


# ------------------------------------------------------------ independencia
def test_la_segregacion_se_comprueba_en_el_backend():
    cuerpo = _bloque(BLOQUE, "def confirm_order(")
    assert "_segregacion_permitida" in cuerpo
    assert "CONFIRMATION_SEGREGATION_REQUIRED" in cuerpo
    assert "_preparadores(db, plan)" in cuerpo


def test_el_defecto_de_la_politica_es_exigir_separacion():
    """`R-D0-12-5`: «un control cuyo valor por defecto lo anula no es un control»."""
    modelos = (RAIZ / "modules" / "organization" / "models.py").read_text()
    assert "confirmation_same_user_allowed" in modelos
    assert 'server_default=text("false")' in modelos
    assert 'server_default=sa.text("false")' in MIGRACION


def test_los_preparadores_incluyen_a_todos_los_que_tocaron():
    cuerpo = _bloque(SALES, "def _preparadores(")
    assert "picked_by" in cuerpo and "consolidated_by" in cuerpo


# ------------------------------------------------- no toca nada aguas arriba
def test_el_control_no_toca_inventario_ni_reserva():
    limpio = _limpio(BLOQUE)
    for prohibido in ("record_movement", "reclassify", "putaway", "InventoryBalance",
                      "qty_on_hand", "qty_reserved", "reserve(", "release_if_active",
                      "fulfill_reservation", "consume_on_pick"):
        assert prohibido not in limpio, f"el control toca inventario o reserva: {prohibido}"


def test_el_control_no_ejecuta_ni_replanifica_el_picking():
    limpio = _limpio(BLOQUE)
    for prohibido in ("execute_pick", "sales_service.allocate", "_resecuenciar", "consolidate(",
                      "picking_candidates"):
        assert prohibido not in limpio, f"el control absorbe la 031/032: {prohibido}"


def test_el_control_no_factura_ni_despacha():
    limpio = _limpio(BLOQUE).lower()
    for prohibido in ("invoice", "factura", "shipment", "control_number", "tax", "iva",
                      "receivable"):
        assert not re.search(rf"\b{prohibido}\b", limpio), f"absorbe aguas abajo: {prohibido}"


def test_el_control_no_modifica_la_venta():
    cuerpo = _bloque(BLOQUE, "def confirm_order(")
    for prohibido in ("unit_price", "discount", "linea.quantity =", "linea.product_id =",
                      "presentation_id ="):
        assert prohibido not in cuerpo, f"el control renegocia la venta: {prohibido}"


# ------------------------------------------------------ evidencia y esquema
def test_la_confirmacion_es_una_entidad_y_no_un_booleano():
    """`R-D0-12-1`: con actor, momento, resultado y evidencia."""
    assert "class OrderConfirmation(" in MODELOS and "class OrderConfirmationLine(" in MODELOS
    for campo in ("checked_by", "checked_at", "attempt", "picklist_id", "status"):
        assert campo in MODELOS, f"la confirmación no registra {campo}"
    ventas = MODELOS[MODELOS.index("class SalesOrder("):MODELOS.index("class SalesOrderLine(")]
    for prohibido in ("is_confirmed", "confirmed: Mapped[bool]"):
        assert prohibido not in ventas, f"volvió el booleano: {prohibido}"


def test_el_estado_y_los_motivos_estan_restringidos_en_la_base():
    assert CONFIRMATION_STATUSES == ("CONFIRMED", "REJECTED")
    assert "order_confirmation_status" in MIGRACION and "order_confirmation_status" in MODELOS
    for motivo in CONFIRMATION_DIFFERENCE_KINDS:
        assert motivo in MIGRACION, f"{motivo} no está restringido en la base"
    assert "order_confirmation_line_reason" in MIGRACION, \
        "una línea no conforme podría no decir en qué dimensión"


def test_un_pedido_no_se_confirma_dos_veces_ni_en_la_base():
    assert "uq_order_confirmations_confirmed" in MIGRACION
    assert "uq_order_confirmations_confirmed" in MODELOS, "la restricción solo vive en la migración"


def test_los_motivos_son_las_dimensiones_que_el_proceso_verifica():
    """¶65-69, más las dos que solo aparecen al comparar conjuntos."""
    assert CONFIRMATION_DIFFERENCE_KINDS == (
        "SKU", "CANTIDAD", "PRESENTACION", "CONDICION", "LINEA_FALTANTE", "LINEA_SOBRANTE")


def test_la_elegibilidad_para_facturar_tiene_una_sola_autoridad():
    """¶89: Facturación factura «sobre un pedido previamente confirmado»."""
    cuerpo = _bloque(SALES, "def billing_eligibility(")
    assert 'OrderConfirmation.status == "CONFIRMED"' in cuerpo
    assert 'order.status == "CONFIRMED"' in cuerpo


def test_el_pedido_llega_a_confirmado_y_no_mas_alla():
    from app.modules.sales import service as sales_service

    t = sales_service.ORDER_TRANSITIONS
    assert "CONFIRMED" in t["PREPARED"] and "PREPARING" in t["PREPARED"]
    assert "CONFIRMED" in t
    # `READY_FOR_BILLING` ya existe: lo añadió la Spec 034, que es su dueña. Lo
    # que esta guardia sigue defendiendo es que **la 033** no lo escriba.
    assert "READY_FOR_BILLING" not in _bloque(BLOQUE, "def confirm_order("), \
        "el control independiente libera para facturación por su cuenta"
    assert "CONFIRMED" in sales_service.ORDER_RESERVED_STATES, \
        "un pedido confirmado perdió su reserva antes de despacharse"


def test_los_permisos_del_control_existen_en_el_catalogo():
    catalogo = (RAIZ / "modules" / "setup" / "api.py").read_text()
    bloque = SALES_API[SALES_API.index("class ConfirmationLineBody"):
                       SALES_API.index('@router.post("/shipments"')]
    usados = set(re.findall(r'require_permission\("(\w+)", "(\w+)"\)', bloque))
    assert usados, "el bloque de confirmación no declara ningún permiso"
    for recurso, accion in sorted(usados):
        m = re.search(rf'"{recurso}": \[([^\]]+)\]', catalogo)
        assert m and f'"{accion}"' in m.group(1), f"«{recurso}:{accion}» no existe en el catálogo"


def test_no_se_reutiliza_la_incidencia_de_compras():
    limpio = _limpio(BLOQUE)
    assert "ReceiptIncident" not in limpio, "la confirmación de ventas usó la incidencia de compras"


def test_la_migracion_no_inventa_historia():
    assert "UPDATE order_confirmations" not in MIGRACION
    assert "INSERT INTO order_confirmations" not in MIGRACION
