"""Las dos vulnerabilidades cruzadas de las Specs 045 y 046 (ARCH-MC-001, N5).

Ambas se demostraron durante la validación por dominios y ninguna puede esperar
a N9: una permite leer documentos de otra empresa y la otra permite escribir en
ella. Lo que se corrige aquí es exclusivamente eso. El cierre formal de 046 y los
cuatro tipos de recurso que le faltan siguen siendo N9.
"""

from __future__ import annotations

import io

from sqlalchemy import text

pytest_plugins = ("tests.conftest_multicompany",)


# =========================================================== Spec 045
def test_el_cuerpo_no_puede_designar_otra_empresa_que_la_del_contexto(mundo):
    """La vulnerabilidad de escritura, en su forma exacta.

    Operando en la empresa A, declarar la empresa B en el cuerpo hacía que la
    política quedara guardada en B. El cliente elegía dónde escribir.
    """
    r = mundo.post("/approvals/policies", "ua", mundo.company_a, {
        "company_id": mundo.company_b, "process_type": "PURCHASE_ORDER",
        "code": "POL-CRUZADA", "name": "Cruzada", "requires_segregation": False})
    assert r.status_code == 404, f"el cuerpo impuso la empresa B: {r.status_code} {r.text}"

    db = mundo.factory()
    try:
        assert db.execute(text(
            "SELECT count(*) FROM approval_policies WHERE code = 'POL-CRUZADA'"
        )).scalar_one() == 0, "quedó una política escrita en la empresa ajena"
    finally:
        db.close()


def test_la_politica_legitima_se_crea_y_queda_en_su_empresa(mundo):
    """Sin esto, el bloqueo anterior podría deberse a que nada funciona."""
    r = mundo.post("/approvals/policies", "ua", mundo.company_a, {
        "company_id": mundo.company_a, "process_type": "PURCHASE_ORDER",
        "code": "POL-A", "name": "Política de A", "requires_segregation": False})
    assert r.status_code in (200, 201), r.text
    assert mundo.dueño("approval_policies", r.json()["id"]) == mundo.company_a


def test_la_politica_sin_empresa_en_el_cuerpo_toma_la_del_contexto(mundo):
    """El contexto es la autoridad; el cuerpo, como mucho, la confirma."""
    r = mundo.post("/approvals/policies", "ub", mundo.company_b, {
        "process_type": "PURCHASE_ORDER", "code": "POL-B-SIN",
        "name": "Política de B", "requires_segregation": False})
    assert r.status_code in (200, 201), r.text
    assert mundo.dueño("approval_policies", r.json()["id"]) == mundo.company_b


def test_las_politicas_de_cada_empresa_no_se_mezclan(mundo):
    for usuario, empresa, code in (("ua", mundo.company_a, "POL-L-A"),
                                   ("ub", mundo.company_b, "POL-L-B")):
        r = mundo.post("/approvals/policies", usuario, empresa, {
            "process_type": "SALES_ORDER", "code": code, "name": code,
            "requires_segregation": False})
        assert r.status_code in (200, 201), r.text

    de_a = mundo.get("/approvals/policies", "ua", mundo.company_a).json()
    de_b = mundo.get("/approvals/policies", "ub", mundo.company_b).json()
    de_a = de_a["items"] if isinstance(de_a, dict) else de_a
    de_b = de_b["items"] if isinstance(de_b, dict) else de_b
    ids_a, ids_b = {p["id"] for p in de_a}, {p["id"] for p in de_b}
    assert ids_a and ids_b and not (ids_a & ids_b)
    assert all(p["company_id"] == mundo.company_a for p in de_a)


def test_la_politica_de_b_no_se_lee_ni_se_activa_desde_a(mundo):
    r = mundo.post("/approvals/policies", "ub", mundo.company_b, {
        "process_type": "SALES_ORDER", "code": "POL-B-DET", "name": "Detalle de B",
        "requires_segregation": False})
    assert r.status_code in (200, 201), r.text
    pol_b = r.json()["id"]

    assert mundo.get(f"/approvals/policies/{pol_b}", "ua", mundo.company_a).status_code == 404
    r = mundo.post(f"/approvals/policies/{pol_b}/activate", "ua", mundo.company_a, {})
    assert r.status_code == 404, f"A activó la política de B: {r.text}"


def test_el_otro_tenant_no_escribe_politicas_en_t1(mundo):
    r = mundo.post("/approvals/policies", "uc", mundo.company_a, {
        "company_id": mundo.company_a, "process_type": "SALES_ORDER",
        "code": "POL-T2", "name": "Desde T2", "requires_segregation": False}, tenant="T2")
    assert r.status_code == 404, f"T2 escribió una política en T1: {r.text}"


# =========================================================== Spec 046
def _tipo_documental(mundo, usuario, empresa, code):
    return mundo.crear("/documentos/tipos", usuario, empresa, {
        "code": code, "name": f"Tipo {code}",
        "allowed_mime_types": ["application/pdf"], "scan_required": False})


def _documento(mundo, usuario, empresa, tipo, titulo):
    return mundo.crear("/documentos", usuario, empresa, {
        "document_type_id": tipo, "title": titulo})


def test_un_documento_de_otra_empresa_no_se_lee(mundo):
    """La vulnerabilidad de lectura, en su forma exacta.

    El usuario de A pedía un documento de la empresa B y recibía 200. La causa
    era que el alcance se resolvía contra todas las empresas del tenant, algo
    que era correcto cuando tenant y empresa eran lo mismo.
    """
    tipo_b = _tipo_documental(mundo, "ub", mundo.company_b, "TDB")
    doc_b = _documento(mundo, "ub", mundo.company_b, tipo_b, "Documento de B")

    r = mundo.get(f"/documentos/{doc_b}", "ua", mundo.company_a)
    assert r.status_code == 404, f"A leyó un documento de B: {r.status_code}"
    # 404 y no 403: confirmar que existe ya sería una filtración.
    assert r.json()["code"] in ("DOCUMENT_NOT_FOUND", "NOT_FOUND")


def test_el_documento_propio_sigue_leyendose(mundo):
    tipo_a = _tipo_documental(mundo, "ua", mundo.company_a, "TDA")
    doc_a = _documento(mundo, "ua", mundo.company_a, tipo_a, "Documento de A")
    r = mundo.get(f"/documentos/{doc_a}", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    assert mundo.dueño("documents", doc_a) == mundo.company_a


def test_los_listados_documentales_no_se_mezclan(mundo):
    tipo_a = _tipo_documental(mundo, "ua", mundo.company_a, "TDLA")
    tipo_b = _tipo_documental(mundo, "ub", mundo.company_b, "TDLB")
    da = _documento(mundo, "ua", mundo.company_a, tipo_a, "Lista A")
    db_ = _documento(mundo, "ub", mundo.company_b, tipo_b, "Lista B")

    lista_a = mundo.get("/documentos", "ua", mundo.company_a).json()
    ids_a = {d["id"] for d in (lista_a["items"] if isinstance(lista_a, dict) else lista_a)}
    assert da in ids_a and db_ not in ids_a


def test_los_tipos_documentales_de_b_no_se_usan_desde_a(mundo):
    tipo_b = _tipo_documental(mundo, "ub", mundo.company_b, "TDX")
    r = mundo.post("/documentos", "ua", mundo.company_a,
                   {"document_type_id": tipo_b, "title": "Con tipo ajeno"})
    assert r.status_code == 404, f"A creó un documento con el tipo de B: {r.text}"


def test_ni_las_versiones_ni_el_archivo_de_b_son_accesibles_desde_a(mundo):
    """§127 a §129: no basta con los metadatos.

    Bloquear el detalle y dejar abierta la descarga sería cerrar la puerta y
    dejar la ventana: el contenido es justamente lo que importa.
    """
    tipo_b = _tipo_documental(mundo, "ub", mundo.company_b, "TDV")
    doc_b = _documento(mundo, "ub", mundo.company_b, tipo_b, "Con archivo")
    r = mundo.client.post(
        f"/api/v1/documentos/{doc_b}/versiones",
        headers=mundo.como("ub", mundo.company_b),
        files={"file": ("prueba.pdf", io.BytesIO(b"%PDF-1.4 contenido de B"), "application/pdf")})
    assert r.status_code in (200, 201), r.text
    version_b = r.json().get("version_id") or r.json().get("id")

    assert mundo.get(f"/documentos/{doc_b}/versiones", "ua", mundo.company_a).status_code == 404
    for ruta in (f"/documentos/{doc_b}/descargar",
                 f"/documentos/{doc_b}/versiones/{version_b}/descargar",
                 f"/documentos/{doc_b}/preview"):
        r = mundo.get(ruta, "ua", mundo.company_a)
        assert r.status_code in (404, 405), f"{ruta} respondió {r.status_code} a otra empresa"


def test_no_se_sube_una_version_a_un_documento_ajeno(mundo):
    tipo_b = _tipo_documental(mundo, "ub", mundo.company_b, "TDU")
    doc_b = _documento(mundo, "ub", mundo.company_b, tipo_b, "Sin tocar")
    r = mundo.client.post(
        f"/api/v1/documentos/{doc_b}/versiones",
        headers=mundo.como("ua", mundo.company_a),
        files={"file": ("intruso.pdf", io.BytesIO(b"%PDF-1.4 intruso"), "application/pdf")})
    assert r.status_code == 404, f"A subió una versión al documento de B: {r.status_code}"


def test_el_otro_tenant_tampoco_alcanza_los_documentos(mundo):
    tipo_a = _tipo_documental(mundo, "ua", mundo.company_a, "TDT")
    doc_a = _documento(mundo, "ua", mundo.company_a, tipo_a, "De T1")
    assert mundo.get(f"/documentos/{doc_a}", "uc", mundo.company_c, tenant="T2").status_code == 404
