"""Fiscal P0 con dos empresas del mismo tenant (ARCH-MC-001, N5).

Este es el bloque donde una confusión de empresa deja de ser un problema de
software. Cada empresa es un contribuyente distinto ante el SENIAT: tiene su
propio RIF, sus propias series de numeración, sus propios rangos de control
autorizados por la imprenta y sus propios libros. Un número de A usado por B no
es un registro mal etiquetado: es una factura que la autoridad no reconoce.

No se toca ningún cálculo. Solo se comprueba de quién es cada cosa.
"""

from __future__ import annotations

from sqlalchemy import text

pytest_plugins = ("tests.conftest_multicompany",)


def _cliente(mundo, usuario, empresa, code):
    return mundo.crear("/maestros/terceros", usuario, empresa,
                       {"code": code, "name": f"Cliente {code}", "roles": ["CLIENTE"]})


def _producto(mundo, usuario, empresa, code):
    return mundo.crear("/maestros/catalogos/items", usuario, empresa,
                       {"code": code, "name": f"Producto {code}", "item_type": "PRODUCT"})


def _serie(mundo, usuario, empresa, prefijo):
    return mundo.crear("/fiscal/number-series", usuario, empresa,
                       {"document_type": "INVOICE", "prefix": prefijo})


def _lote(mundo, usuario, empresa, desde, hasta):
    return mundo.crear("/fiscal/control-batches", usuario, empresa,
                       {"range_from": desde, "range_to": hasta, "printer": "IMP-1"})


def _factura_emitida(mundo, usuario, empresa, marca):
    """Una factura de venta en EMITTED, que es lo que el fiscal puede amparar."""
    cli = _cliente(mundo, usuario, empresa, f"CLF-{marca}")
    prod = _producto(mundo, usuario, empresa, f"PRF-{marca}")
    inv = mundo.crear("/sales/invoices", usuario, empresa,
                      {"customer_id": cli, "base_fiscal_currency": "VED"})
    r = mundo.post(f"/sales/invoices/{inv}/lines", usuario, empresa,
                   {"product_id": prod, "quantity": 1, "unit_price": 1000.0, "tax_amount": 160.0})
    assert r.status_code == 200, r.text
    for destino in ("VALIDATED", "APPROVED", "EMITTED"):
        r = mundo.post(f"/sales/invoices/{inv}/transition", usuario, empresa, {"target": destino})
        assert r.status_code == 200, f"{destino}: {r.text}"
    return inv


# --------------------------------------------------------------- series
def test_cada_empresa_tiene_sus_propias_series(mundo):
    sa = _serie(mundo, "ua", mundo.company_a, "A-")
    sb = _serie(mundo, "ub", mundo.company_b, "B-")
    assert mundo.dueño("fiscal_number_series", sa) == mundo.company_a
    assert mundo.dueño("fiscal_number_series", sb) == mundo.company_b
    assert mundo.dueño("fiscal_number_series", sa) != mundo.t1

    de_a = {s["id"] for s in mundo.get("/fiscal/number-series", "ua", mundo.company_a).json()["items"]}
    de_b = {s["id"] for s in mundo.get("/fiscal/number-series", "ub", mundo.company_b).json()["items"]}
    assert sa in de_a and sb not in de_a
    assert not (de_a & de_b)


def test_los_rangos_de_control_no_se_mezclan(mundo):
    la = _lote(mundo, "ua", mundo.company_a, "010001", "010010")
    lb = _lote(mundo, "ub", mundo.company_b, "020001", "020010")
    assert mundo.dueño("control_number_batches", la) == mundo.company_a
    assert mundo.dueño("control_number_batches", lb) == mundo.company_b

    de_a = {b["id"] for b in mundo.get("/fiscal/control-batches", "ua", mundo.company_a).json()["items"]}
    assert la in de_a and lb not in de_a

    # Los números del rango heredan la empresa del lote que los ampara.
    db = mundo.factory()
    try:
        ajenos = db.execute(text(
            "SELECT count(*) FROM control_numbers n JOIN control_number_batches b "
            "ON b.id = n.batch_id WHERE n.company_id <> b.company_id")).scalar_one()
    finally:
        db.close()
    assert ajenos == 0, "hay números de control bajo un lote de otra empresa"


# --------------------------------------------------------------- emisión
def test_no_se_emite_con_la_serie_de_otra_empresa(mundo):
    """§81 y §84: la serie y el rango son autorizaciones nominales.

    Que existan en el mismo sistema no los hace utilizables: fueron concedidos a
    un RIF concreto.
    """
    serie_b = _serie(mundo, "ub", mundo.company_b, "SB-")
    lote_a = _lote(mundo, "ua", mundo.company_a, "110001", "110010")
    inv_a = _factura_emitida(mundo, "ua", mundo.company_a, "SER")

    r = mundo.post("/fiscal/documents/emit", "ua", mundo.company_a, {
        "business_document": f"INVOICE:{inv_a}", "series_id": serie_b, "batch_id": lote_a})
    assert r.status_code == 404, f"A emitió con la serie de B: {r.text}"


def test_no_se_emite_con_el_rango_de_control_de_otra_empresa(mundo):
    serie_a = _serie(mundo, "ua", mundo.company_a, "SA-")
    lote_b = _lote(mundo, "ub", mundo.company_b, "220001", "220010")
    inv_a = _factura_emitida(mundo, "ua", mundo.company_a, "RNG")

    r = mundo.post("/fiscal/documents/emit", "ua", mundo.company_a, {
        "business_document": f"INVOICE:{inv_a}", "series_id": serie_a, "batch_id": lote_b})
    assert r.status_code == 404, f"A emitió con el rango de control de B: {r.text}"


def test_no_se_ampara_fiscalmente_una_factura_de_otra_empresa(mundo):
    serie_a = _serie(mundo, "ua", mundo.company_a, "SC-")
    lote_a = _lote(mundo, "ua", mundo.company_a, "310001", "310010")
    inv_b = _factura_emitida(mundo, "ub", mundo.company_b, "AJENA")

    r = mundo.post("/fiscal/documents/emit", "ua", mundo.company_a, {
        "business_document": f"INVOICE:{inv_b}", "series_id": serie_a, "batch_id": lote_a})
    assert r.status_code == 404, f"A amparó fiscalmente una venta de B: {r.text}"


def test_la_emision_legitima_funciona_y_queda_de_su_empresa(mundo):
    serie_a = _serie(mundo, "ua", mundo.company_a, "OK-")
    lote_a = _lote(mundo, "ua", mundo.company_a, "410001", "410010")
    inv_a = _factura_emitida(mundo, "ua", mundo.company_a, "OK")

    r = mundo.post("/fiscal/documents/emit", "ua", mundo.company_a, {
        "business_document": f"INVOICE:{inv_a}", "series_id": serie_a, "batch_id": lote_a})
    assert r.status_code == 200, r.text
    doc = r.json()
    assert mundo.dueño("fiscal_documents", doc["id"]) == mundo.company_a
    assert doc["invoice_number"].startswith("OK-")


def test_la_numeracion_de_una_empresa_no_avanza_la_de_la_otra(mundo):
    """§82: dos contribuyentes, dos correlativos independientes."""
    serie_a = _serie(mundo, "ua", mundo.company_a, "NA-")
    serie_b = _serie(mundo, "ub", mundo.company_b, "NB-")
    lote_a = _lote(mundo, "ua", mundo.company_a, "510001", "510010")

    def siguiente(sid):
        db = mundo.factory()
        try:
            return db.execute(text("SELECT next_number FROM fiscal_number_series WHERE id = :i"),
                              {"i": sid}).scalar_one()
        finally:
            db.close()

    antes_b = siguiente(serie_b)
    inv_a = _factura_emitida(mundo, "ua", mundo.company_a, "NUM")
    r = mundo.post("/fiscal/documents/emit", "ua", mundo.company_a, {
        "business_document": f"INVOICE:{inv_a}", "series_id": serie_a, "batch_id": lote_a})
    assert r.status_code == 200, r.text
    assert siguiente(serie_b) == antes_b, "emitir en A movió el correlativo de B"


def test_el_documento_fiscal_de_b_no_se_lee_ni_se_imprime_desde_a(mundo):
    serie_b = _serie(mundo, "ub", mundo.company_b, "PB-")
    lote_b = _lote(mundo, "ub", mundo.company_b, "620001", "620010")
    inv_b = _factura_emitida(mundo, "ub", mundo.company_b, "PRN")
    r = mundo.post("/fiscal/documents/emit", "ub", mundo.company_b, {
        "business_document": f"INVOICE:{inv_b}", "series_id": serie_b, "batch_id": lote_b})
    assert r.status_code == 200, r.text
    doc_b = r.json()["id"]

    assert mundo.get(f"/fiscal/documents/{doc_b}", "ua", mundo.company_a).status_code == 404
    r = mundo.post(f"/fiscal/documents/{doc_b}/print", "ua", mundo.company_a,
                   {"copy_type": "COPIA", "reason": "prueba"})
    assert r.status_code == 404, f"A imprimió un documento fiscal de B: {r.text}"

    de_a = {d["id"] for d in mundo.get("/fiscal/documents", "ua", mundo.company_a).json()["items"]}
    assert doc_b not in de_a


# --------------------------------------------------------------- notas
def test_las_notas_de_credito_y_debito_no_cruzan_empresas(mundo):
    """§87 y §88: la nota corrige un documento propio, no uno ajeno."""
    serie_b = _serie(mundo, "ub", mundo.company_b, "NB2-")
    lote_b = _lote(mundo, "ub", mundo.company_b, "720001", "720010")
    inv_b = _factura_emitida(mundo, "ub", mundo.company_b, "NOTA")
    r = mundo.post("/fiscal/documents/emit", "ub", mundo.company_b, {
        "business_document": f"INVOICE:{inv_b}", "series_id": serie_b, "batch_id": lote_b})
    assert r.status_code == 200, r.text

    for tipo in ("CREDIT", "DEBIT"):
        r = mundo.post("/fiscal/credit-debit-notes", "ua", mundo.company_a, {
            "original_document": f"INVOICE:{inv_b}", "note_type": tipo,
            "cause": "Corrección cruzada", "amount": 10.0})
        assert r.status_code == 404, f"A emitió una nota {tipo} sobre el documento de B: {r.text}"


# --------------------------------------------------------------- libros
def test_el_libro_de_ventas_de_una_empresa_no_contiene_a_la_otra(mundo):
    """§90: la prueba de contaminación.

    Se emiten documentos en las dos empresas a propósito y luego se pide el
    libro de cada una. Un libro que incluyera facturas ajenas declararía ante el
    SENIAT ventas de otro contribuyente.
    """
    for usuario, empresa, marca, desde, hasta in (
            ("ua", mundo.company_a, "LIBA", "810001", "810010"),
            ("ub", mundo.company_b, "LIBB", "820001", "820010")):
        serie = _serie(mundo, usuario, empresa, f"L{marca}-")
        lote = _lote(mundo, usuario, empresa, desde, hasta)
        inv = _factura_emitida(mundo, usuario, empresa, marca)
        r = mundo.post("/fiscal/documents/emit", usuario, empresa, {
            "business_document": f"INVOICE:{inv}", "series_id": serie, "batch_id": lote})
        assert r.status_code == 200, r.text

    libro_a = mundo.get("/fiscal/books/VENTAS", "ua", mundo.company_a).json()
    libro_b = mundo.get("/fiscal/books/VENTAS", "ub", mundo.company_b).json()

    # Sin esta comprobación la prueba pasaría en vacío: dos libros sin filas no
    # se contaminan, y el aislamiento quedaría demostrado por no haber datos.
    assert libro_a["count"] > 0 and libro_b["count"] > 0, "los libros salieron vacíos"

    na = {f["number"] for f in libro_a["rows"]}
    nb = {f["number"] for f in libro_b["rows"]}
    assert na and nb
    assert not (na & nb), f"el libro de una empresa contiene documentos de la otra: {na & nb}"

    # La comprobación exacta: cada número del libro se resuelve contra
    # PostgreSQL y tiene que pertenecer a la empresa que pidió el libro.
    db = mundo.factory()
    try:
        for numero in na:
            dueño = db.execute(text(
                "SELECT company_id FROM fiscal_documents WHERE invoice_number = :n"),
                {"n": numero}).scalar_one()
            assert dueño == mundo.company_a, f"{numero} figura en el libro de A y es de otra empresa"
        for numero in nb:
            dueño = db.execute(text(
                "SELECT company_id FROM fiscal_documents WHERE invoice_number = :n"),
                {"n": numero}).scalar_one()
            assert dueño == mundo.company_b, f"{numero} figura en el libro de B y es de otra empresa"
    finally:
        db.close()


# --------------------------------------------------------------- retenciones
def test_las_retenciones_pertenecen_al_agente_que_las_practica(mundo):
    """§91: el agente de retención es una empresa concreta, no el grupo."""
    ra = mundo.crear("/fiscal/withholding-rules", "ua", mundo.company_a,
                     {"tax_type": "IVA", "code": "RET-A", "rate": 75.0})
    rb = mundo.crear("/fiscal/withholding-rules", "ub", mundo.company_b,
                     {"tax_type": "IVA", "code": "RET-B", "rate": 75.0})
    assert mundo.dueño("withholding_rules", ra) == mundo.company_a
    assert mundo.dueño("withholding_rules", rb) == mundo.company_b

    de_a = {x["id"] for x in mundo.get("/fiscal/withholding-rules", "ua", mundo.company_a).json()["items"]}
    assert ra in de_a and rb not in de_a


# --------------------------------------------------------------- periodos
def test_los_periodos_fiscales_son_de_cada_empresa(mundo):
    pa = mundo.crear("/fiscal/periods", "ua", mundo.company_a,
                     {"tax_type": "IVA", "period_key": "2026-08"})
    pb = mundo.crear("/fiscal/periods", "ub", mundo.company_b,
                     {"tax_type": "IVA", "period_key": "2026-08"})
    assert pa != pb, "las dos empresas comparten el mismo periodo fiscal"
    assert mundo.dueño("fiscal_periods", pa) == mundo.company_a
    assert mundo.dueño("fiscal_periods", pb) == mundo.company_b

    r = mundo.post(f"/fiscal/periods/{pb}/transition", "ua", mundo.company_a, {"target": "CLOSED"})
    assert r.status_code == 404, f"A cerró el periodo fiscal de B: {r.text}"


# --------------------------------------------------------------- la base
def test_ninguna_fila_fiscal_pertenece_a_una_empresa_inexistente(mundo):
    tablas = ["fiscal_number_series", "control_number_batches", "control_numbers",
              "tax_calculations", "tax_profiles", "fiscal_documents", "print_events",
              "credit_debit_notes", "withholding_rules", "fiscal_periods",
              "tax_return_batches"]
    db = mundo.factory()
    try:
        for tabla in tablas:
            malas = db.execute(text(
                f"SELECT count(*) FROM {tabla} t WHERE t.company_id IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM companies c WHERE c.id = t.company_id)"
            )).scalar_one()
            assert malas == 0, f"{tabla}: {malas} filas sin contribuyente real"
    finally:
        db.close()
