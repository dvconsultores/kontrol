"""Spec 034 · guardias estructurales de la liberación y la facturación.

Leen el código. Defienden la compuerta —no se factura sin confirmación
independiente, ni dos veces el mismo pedido— y la procedencia: el contenido
comercial sale del pedido congelado y la numeración de la Spec 042. Ni una tasa
de impuesto ni un correlativo nacen aquí.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1] / "app"
SALES = (RAIZ / "modules" / "sales" / "service.py").read_text()
SALES_API = (RAIZ / "modules" / "sales" / "api.py").read_text()
MODELOS = (RAIZ / "modules" / "sales" / "models.py").read_text()
MIGRACION = (Path(__file__).resolve().parents[1] / "alembic" / "versions"
             / "0052_spec034_billing_release.py").read_text()
BLOQUE = SALES[SALES.index("# Spec 034 · liberación y facturación"):SALES.index("def create_shipment(")]


def _bloque(texto: str, inicio: str) -> str:
    trozo = texto[texto.index(inicio):]
    siguiente = trozo.find("\ndef ", 1)
    cuerpo = trozo if siguiente < 0 else trozo[:siguiente]
    cuerpo = re.sub(r'"""..*?"""', "", cuerpo, flags=re.S)
    return "\n".join(x for x in cuerpo.splitlines() if not x.strip().startswith("#"))


def _limpio(texto: str) -> str:
    sin_doc = re.sub(r'"""..*?"""', "", texto, flags=re.S)
    return "\n".join(x for x in sin_doc.splitlines() if not x.strip().startswith("#"))


# ------------------------------------------------------------- la compuerta
def test_no_se_factura_sin_confirmacion_independiente():
    """¶89 y `B-060`: «solo se factura un pedido `CONFIRMED`»."""
    for nombre in ("def request_billing(", "def generate_invoice(", "def issue_invoice("):
        cuerpo = _bloque(BLOQUE, nombre)
        assert "_confirmacion_vigente" in cuerpo, f"{nombre} no exige la confirmación"


def test_la_confirmacion_se_comprueba_por_registro_y_no_por_estado():
    """Un control que se satisface moviendo un estado a mano no es un control."""
    cuerpo = _bloque(BLOQUE, "def _confirmacion_vigente(")
    assert "OrderConfirmation" in cuerpo
    assert 'OrderConfirmation.status == "CONFIRMED"' in cuerpo


def test_un_pedido_no_se_factura_dos_veces_ni_en_la_base():
    """`B-007`. En el servicio **y** en la base: dos peticiones simultáneas
    leerían las dos que no hay factura."""
    assert "ORDER_ALREADY_INVOICED" in BLOQUE
    assert "uq_sales_invoices_order" in MIGRACION
    assert "uq_sales_invoices_order" in MODELOS, "la restricción solo vive en la migración"


def test_la_solicitud_deja_autor_y_momento():
    cuerpo = _bloque(BLOQUE, "def request_billing(")
    assert "billing_requested_by" in cuerpo and "billing_requested_at" in cuerpo


# --------------------------------------------------------- la procedencia
def test_el_precio_es_el_congelado_del_pedido():
    """§32: cambiar una tarifa no reescribe una venta ya cerrada."""
    cuerpo = _bloque(SALES, "def _precio_de(")
    assert "resolved_unit_price" in cuerpo and "linea.unit_price" in cuerpo
    generar = _bloque(BLOQUE, "def generate_invoice(")
    assert "_precio_de(linea)" in generar
    for prohibido in ("resolve_price", "price_list", "CatalogItem", "PriceListItem"):
        assert prohibido not in generar, f"la factura consulta el maestro actual: {prohibido}"


def test_la_factura_conserva_unidad_presentacion_y_base():
    cuerpo = _bloque(BLOQUE, "def generate_invoice(")
    for campo in ("uom_id=linea.uom_id", "presentation_id=linea.presentation_id",
                  "conversion_factor_snapshot=linea.conversion_factor_snapshot",
                  "base_quantity=linea.base_quantity"):
        assert campo in cuerpo, f"la factura pierde {campo}"
    for prohibido in ("to_base(", "uom_engine", "factor_to_base"):
        assert prohibido not in cuerpo, f"la factura recalcula la conversión: {prohibido}"


def test_ninguna_tasa_de_impuesto_nace_aqui():
    """§35: `tax = subtotal * 0.xx` es exactamente lo que no puede existir."""
    limpio = _limpio(BLOQUE)
    assert "fiscal_service.calculate_tax(" in limpio, "no consulta el motor fiscal"
    for prohibido in ("0.16", "16.0", "* 0.1", "IVA_GENERAL", "tax_rate ="):
        assert prohibido not in limpio, f"tasa escrita a mano: {prohibido}"


def test_la_numeracion_no_es_de_esta_spec():
    """§27-28: correlativo y número de control los asigna la Spec 042."""
    cuerpo = _bloque(BLOQUE, "def issue_invoice(")
    assert "fiscal_service.emit_document(" in cuerpo
    for prohibido in ("next_number", "max(", "reserve_number(", "assign_control(",
                      "control_number = str", "+ 1"):
        assert prohibido not in cuerpo, f"la 034 numera por su cuenta: {prohibido}"


def test_la_emision_es_idempotente_por_construccion():
    cuerpo = _bloque(BLOQUE, "def issue_invoice(")
    assert 'if invoice.status == "EMITTED":' in cuerpo
    assert 'business_document=f"INVOICE:{invoice.id}"' in cuerpo


# ------------------------------------------------------------- las fronteras
def test_facturar_no_toca_inventario_ni_reserva():
    limpio = _limpio(BLOQUE)
    for prohibido in ("record_movement", "reclassify", "putaway", "InventoryBalance",
                      "qty_on_hand", "qty_reserved", "inv_service.reserve", "consume_on_pick",
                      "release_picking_shortage", "fulfill_reservation"):
        assert prohibido not in limpio, f"facturar toca inventario o reserva: {prohibido}"


def test_facturar_no_ejecuta_picking_ni_confirma():
    limpio = _limpio(BLOQUE)
    for prohibido in ("execute_pick", "consolidate(", "confirm_order(", "allocate("):
        assert prohibido not in limpio, f"absorbe aguas arriba: {prohibido}"


def test_facturar_no_despacha():
    limpio = _limpio(BLOQUE).lower()
    for prohibido in ("shipment", "despacho", "vehic", "conductor", "transport", "sica",
                      "sigesai"):
        assert not re.search(rf"\b{prohibido}", limpio), f"absorbe la 035: {prohibido}"


def test_no_se_construye_un_segundo_libro_de_cuentas_por_cobrar():
    """`FR-005-040`: el `OpenItem` lo crea `transition_invoice` al emitir."""
    limpio = _limpio(BLOQUE)
    for prohibido in ("OpenItem(", "ap_service.create_open_item", "receivable"):
        assert prohibido not in limpio, f"segundo ledger de cobro: {prohibido}"


# --------------------------------------------------------- estados y permisos
def test_el_pedido_llega_a_facturado_y_no_mas_alla():
    from app.modules.sales import service as sales_service

    t = sales_service.ORDER_TRANSITIONS
    assert "READY_FOR_BILLING" in t["CONFIRMED"]
    assert t["READY_FOR_BILLING"] == {"INVOICED", "CANCELLED"}
    assert "INVOICED" in t
    assert "DISPATCHED" not in t, "la 034 adelantó un estado de la 035"
    for estado in ("READY_FOR_BILLING", "INVOICED"):
        assert estado in sales_service.ORDER_RESERVED_STATES, \
            f"{estado} perdió la reserva antes de despacharse"


def test_los_permisos_de_facturacion_existen_en_el_catalogo():
    catalogo = (RAIZ / "modules" / "setup" / "api.py").read_text()
    bloque = SALES_API[SALES_API.index("class IssueInvoiceBody"):
                       SALES_API.index('@router.post("/shipments"')]
    usados = set(re.findall(r'require_permission\("(\w+)", "(\w+)"\)', bloque))
    assert usados, "el bloque de facturación no declara ningún permiso"
    for recurso, accion in sorted(usados):
        m = re.search(rf'"{recurso}": \[([^\]]+)\]', catalogo)
        assert m and f'"{accion}"' in m.group(1), f"«{recurso}:{accion}» no existe en el catálogo"


def test_la_solicitud_la_firma_quien_verifica():
    """¶83: «El Área de Confirmación autoriza». Por eso exige su mismo permiso."""
    bloque = SALES_API[SALES_API.index('@router.post("/facturacion/{order_id}/solicitar"'):
                       SALES_API.index('@router.post("/facturacion/{order_id}/generar"')]
    assert 'require_permission("ventas", "quality")' in bloque


def test_la_migracion_es_aditiva_y_no_inventa_historia():
    """`B-007`: «migración aditiva con FK nullable». Las facturas anteriores no
    tienen pedido y no se les inventa uno."""
    assert "UPDATE sales_invoices" not in MIGRACION
    assert 'sa.Column("order_id", sa.String(36), nullable=True)' in MIGRACION
    assert "nullable=False" not in MIGRACION.split("def downgrade")[0].replace(
        'nullable=True', ''), "una columna nueva nació obligatoria"
