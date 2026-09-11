"""Spec 036 · guardias estructurales de la devolución y las notas.

Leen el código. Defienden el orden que la norma escribe —cuatro actos antes de
tocar el inventario—, los dos únicos destinos que `D0-10` concede, la
proporcionalidad del impuesto y las tres cosas que esta Spec **no** hace:
numerar por su cuenta, resucitar reservas e inventar estados de mercancía.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.spec_blocks import bloque_de_spec, cuerpo_de_simbolo, limpio

RAIZ = Path(__file__).resolve().parents[1] / "app"
SALES = (RAIZ / "modules" / "sales" / "service.py").read_text()
SALES_API = (RAIZ / "modules" / "sales" / "api.py").read_text()
MODELOS = (RAIZ / "modules" / "sales" / "models.py").read_text()
FISCAL = (RAIZ / "modules" / "fiscal" / "service.py").read_text()
MIGRACION = (Path(__file__).resolve().parents[1] / "alembic" / "versions"
             / "0054_spec036_returns_notes.py").read_text()
BLOQUE = bloque_de_spec(SALES, "036")
BLOQUE_API = bloque_de_spec(SALES_API, "036")


# ------------------------------------------------------- los cuatro actos
def test_la_solicitud_no_toca_el_inventario():
    """«Solicitud» es el primer acto y el inventario es el cuarto."""
    cuerpo = cuerpo_de_simbolo(SALES, "def request_return(")
    for prohibido in ("reclassify(", "putaway(", "record_movement("):
        assert prohibido not in cuerpo, f"la solicitud mueve mercancía: {prohibido}"


def test_recibir_no_hace_vendible_la_mercancia():
    """`DESPACHADO → DEVUELTO`, nunca directo a `DISPONIBLE`."""
    cuerpo = cuerpo_de_simbolo(SALES, "def receive_return(")
    # Los estados se le piden a la autoridad única, no se escriben: copiar el
    # catálogo en otro módulo es empezar a tener dos motores (`test_spec023`).
    assert "state_authority.DISPATCHED_STATE" in cuerpo
    assert "state_authority.RETURNED_STATE" in cuerpo
    assert "DISPONIBLE" not in cuerpo and "SELLABLE" not in cuerpo, \
        "la recepción saltó la verificación física que la norma exige"


def test_el_reingreso_respeta_el_dictamen_y_va_despues_de_aprobar():
    cuerpo = cuerpo_de_simbolo(SALES, "def reenter_return(")
    assert "state_authority.RETURNED_STATE" in cuerpo
    assert "target_state=linea.disposition" in cuerpo, "el destino no sale del dictamen"
    assert "accepted_base_quantity" in cuerpo, "reingresa lo recibido y no lo aceptado"
    from app.modules.sales import service as s

    assert s.RETURN_TRANSITIONS["APPROVED"] == {"CLOSED"}
    assert "CLOSED" not in s.RETURN_TRANSITIONS["INSPECTED"], \
        "se puede reingresar sin pasar por la aprobación"


def test_el_orden_de_los_actos_es_el_de_la_norma():
    from app.modules.sales import service as s

    assert s.RETURN_TRANSITIONS["REQUESTED"] == {"RECEIVED", "CANCELLED"}
    assert s.RETURN_TRANSITIONS["RECEIVED"] == {"INSPECTED", "CANCELLED"}
    assert s.RETURN_TRANSITIONS["INSPECTED"] == {"APPROVED", "REJECTED"}
    assert s.RETURN_TRANSITIONS["CLOSED"] == set()


# ------------------------------------------------ los estados de mercancía
def test_los_destinos_son_los_dos_que_d0_10_concede():
    from app.modules.inventory import states
    from app.modules.sales import service as s

    assert s.RETURN_DISPOSITIONS == frozenset({"DISPONIBLE", "RECHAZADO"})
    # Y son los mismos objetos: ventas no tiene una copia propia del conjunto.
    assert s.RETURN_DISPOSITIONS is states.RETURN_DISPOSITIONS
    # `CUARENTENA` y `DESECHO` tienen otra dueña; «reparación» no es un estado.
    for ajeno in ("CUARENTENA", "DESECHO", "REPARACION"):
        assert ajeno not in s.RETURN_DISPOSITIONS


def test_las_aristas_estan_declaradas_con_su_duena():
    from app.modules.inventory import states

    mias = {(t.source, t.target) for t in states.ACTIVE_TRANSITIONS if t.owner_spec == "036"}
    assert mias == {("DESPACHADO", "DEVUELTO"), ("DEVUELTO", "DISPONIBLE"),
                    ("DEVUELTO", "RECHAZADO")}
    for t in states.ACTIVE_TRANSITIONS:
        if t.owner_spec == "036":
            assert t.evidence, "una arista sin evidencia documental"


def test_no_se_inventan_estados_de_mercancia():
    from app.modules.inventory import states

    nuevos = {t.target for t in states.ACTIVE_TRANSITIONS if t.owner_spec == "036"}
    assert nuevos <= set(states.MERCHANDISE_STATES)


def test_la_restriccion_del_destino_esta_en_la_base_y_en_el_orm():
    assert "ck_sales_return_lines_disposition" in MIGRACION
    assert "ck_sales_return_lines_disposition" in MODELOS, \
        "la restricción solo vive en la migración"


# ------------------------------------------------------------- la reserva
def test_la_devolucion_no_toca_ninguna_reserva():
    """`D0-03`: «re-reservar tras liberar = nueva fila, nunca reactivación»."""
    for prohibido in ("release_reservation", "fulfill_reservation", "inv_service.reserve(",
                      "Reservation("):
        assert prohibido not in limpio(BLOQUE), f"la 036 tocó la reserva: {prohibido}"


def test_la_devolucion_no_revierte_el_pedido():
    """La venta ocurrió. `SHIPPED` no se deshace: se compensa con eventos."""
    cuerpo = limpio(BLOQUE)
    for prohibido in ('order.status = "CONFIRMED"', 'order.status = "PREPARED"',
                      'order.status = "RELEASED"', "ORDER_TRANSITIONS"):
        assert prohibido not in cuerpo, f"la devolución reescribió la historia: {prohibido}"


# --------------------------------------------------------------- la nota
def test_la_nota_reparte_el_impuesto_y_no_lo_recalcula():
    """«Recalcular proporcionalmente» y «mantener la misma clasificación»."""
    cuerpo = cuerpo_de_simbolo(SALES, "def generate_credit_note(")
    assert "proporcion" in cuerpo and "linea.tax_amount" in cuerpo
    assert "calculate_tax" not in cuerpo, "la nota volvió a clasificar la operación"
    assert not re.search(r"0\.\d{2}\s*\)", cuerpo.replace("_CENTIMO", "")), \
        "apareció una alícuota escrita a mano"


def test_la_nota_no_numera_por_su_cuenta():
    """La 042 es la dueña del consecutivo y del número de control."""
    for nombre in ("def issue_credit_note(", "def issue_debit_note("):
        cuerpo = cuerpo_de_simbolo(SALES, nombre)
        assert "fiscal_service.emit_document(" in cuerpo, f"{nombre} no usa el motor fiscal"
        for prohibido in ("max(", "count(", "+ 1"):
            assert prohibido not in cuerpo, f"{nombre} inventa numeración: {prohibido}"


def test_el_motor_fiscal_sabe_de_los_tres_documentos():
    """Delta dirigido sobre la 042: emitía solo facturas."""
    assert "EMITTABLE_DOCUMENT_TYPES" in FISCAL
    from app.modules.fiscal import service as f

    assert f.EMITTABLE_DOCUMENT_TYPES == frozenset({"INVOICE", "CREDIT_NOTE", "DEBIT_NOTE"})
    cuerpo = cuerpo_de_simbolo(FISCAL, "def emit_document(")
    assert 'document_type="INVOICE"' not in cuerpo, "el tipo seguía escrito a mano"
    assert "SERIES_DOCUMENT_TYPE_MISMATCH" in cuerpo, \
        "una nota puede gastar el correlativo de las facturas"


def test_el_tope_de_la_nota_es_lo_pendiente_y_no_el_total():
    """«No ajustar por encima de cantidades/base/IVA **pendientes** del original»."""
    cuerpo = cuerpo_de_simbolo(SALES, "def generate_credit_note(")
    assert "CREDIT_EXCEEDS_INVOICE" in cuerpo
    acumulado = cuerpo_de_simbolo(SALES, "def _acreditado_de_linea(")
    assert 'SalesCreditNote.status != "CANCELLED"' in acumulado, \
        "el acumulado no cuenta las notas vivas"


def test_el_tope_de_la_devolucion_es_lo_despachado():
    cuerpo = cuerpo_de_simbolo(SALES, "def request_return(")
    assert "RETURN_EXCEEDS_DISPATCHED" in cuerpo
    acumulado = cuerpo_de_simbolo(SALES, "def _devuelto_acumulado(")
    assert 'SalesReturn.status.notin_(("CANCELLED", "REJECTED"))' in acumulado


def test_la_nota_de_debito_no_toca_inventario():
    """Su flujo no tiene una sola etapa física."""
    for nombre in ("def generate_debit_note(", "def issue_debit_note("):
        cuerpo = cuerpo_de_simbolo(SALES, nombre)
        for prohibido in ("reclassify(", "putaway(", "record_movement("):
            assert prohibido not in cuerpo, f"{nombre} movió mercancía: {prohibido}"


def test_la_nota_de_debito_exige_su_factura():
    """«No puede utilizarse como una factura independiente»."""
    cuerpo = cuerpo_de_simbolo(SALES, "def generate_debit_note(")
    assert "SALES_INVOICE_NOT_FOUND" in cuerpo
    emision = cuerpo_de_simbolo(SALES, "def issue_debit_note(")
    assert "DEBIT_NOTE_WITHOUT_INVOICE" in emision


def test_la_factura_original_no_se_reescribe():
    """La nota referencia; no edita los totales del original."""
    cuerpo = limpio(BLOQUE)
    for prohibido in ("invoice.total =", "invoice.base_fiscal =", "invoice.tax_total =",
                      "invoice.invoice_number =", "invoice.control_number ="):
        assert prohibido not in cuerpo, f"la nota tocó la factura original: {prohibido}"


# ------------------------------------------------------------- fronteras
def test_la_036_no_cobra_ni_devuelve_dinero():
    """El reembolso es de tesorería, no de aquí."""
    cuerpo = limpio(BLOQUE)
    for prohibido in ("Payment(", "CashSession", "refund", "reembolso"):
        assert prohibido not in cuerpo, f"absorbe tesorería: {prohibido}"


def test_la_036_no_despacha_ni_factura():
    cuerpo = limpio(BLOQUE)
    for prohibido in ("create_shipment(", "generate_invoice(", "issue_invoice(",
                      "confirm_shipment("):
        assert prohibido not in cuerpo, f"absorbe otra Spec: {prohibido}"


def test_los_permisos_de_la_devolucion_existen_en_el_catalogo():
    catalogo = (RAIZ / "modules" / "setup" / "api.py").read_text()
    usados = set(re.findall(r'require_permission\("(\w+)", "(\w+)"\)', BLOQUE_API))
    assert usados, "el bloque de devoluciones no declara ningún permiso"
    for recurso, accion in sorted(usados):
        m = re.search(rf'"{recurso}": \[([^\]]+)\]', catalogo)
        assert m and f'"{accion}"' in m.group(1), f"«{recurso}:{accion}» no existe en el catálogo"


def test_el_cliente_no_elige_el_estado_de_la_mercancia():
    """El dictamen lo valida el backend contra `D0-10`, no el navegador."""
    cuerpo = cuerpo_de_simbolo(SALES, "def inspect_return(")
    assert "RETURN_DISPOSITIONS" in cuerpo and "RETURN_DISPOSITION_INVALID" in cuerpo


def test_la_migracion_es_aditiva_y_no_inventa_historia():
    assert "UPDATE sales_returns" not in MIGRACION
    assert "UPDATE sales_credit_notes" not in MIGRACION
    assert "UPDATE sales_debit_notes" not in MIGRACION
    # Lo que no puede nacer obligatorio es una columna **añadida** a una tabla
    # que ya tiene filas: las devoluciones y las notas anteriores no llevan esta
    # procedencia. En una tabla nueva no hay historia que romper.
    upgrade = cuerpo_de_simbolo(MIGRACION, "def upgrade(")
    for anadida in re.findall(r"op\.add_column\(([^\n]*(?:\n[^\n]*)?)", upgrade):
        assert "nullable=False" not in anadida, f"columna añadida obligatoria: {anadida[:80]}"
    # Y las tablas nuevas se crean con su clave y sus no nulas, que es correcto.
    assert "sales_credit_note_lines" in upgrade and "sales_debit_note_lines" in upgrade
