"""Aislamiento entre empresas del mismo tenant (ARCH-MC-001, fase N5).

El aislamiento entre tenants ya existía. Lo que aquí se prueba es lo que faltaba:
que dos empresas **del mismo tenant** no se vean ni se mezclen.

Se comprueban dos cosas distintas y ambas importan:

- **Fuga**: que A pueda leer lo de B.
- **Mezcla**: que la base no sepa de quién es una fila.

Que la API filtre bien no basta si en la base el dato sigue guardando el tenant:
eso sería un filtro correcto sobre un dato equivocado.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

#: El fixture se registra como plugin; importarlo lo redefiniría en cada prueba.
pytest_plugins = ("tests.conftest_multicompany",)


# --------------------------------------------------------------- contexto
def test_una_empresa_ajena_no_existe_para_quien_no_accede(mundo):
    """`UA` pidiendo la empresa B: 404, sin confirmar que existe."""
    r = mundo.client.get("/api/v1/maestros/terceros",
                         headers=mundo.como("ua", mundo.company_b))
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "COMPANY_NOT_FOUND"


def test_una_empresa_de_otro_tenant_tampoco(mundo):
    r = mundo.client.get("/api/v1/maestros/terceros",
                         headers=mundo.como("uc", mundo.company_a, tenant="T2"))
    assert r.status_code == 404


def test_con_varias_empresas_y_sin_cabecera_no_se_adivina(mundo):
    """`UAB` accede a dos: el sistema no elige por él."""
    r = mundo.client.get("/api/v1/maestros/terceros", headers=mundo.como("uab"))
    assert r.status_code == 400, r.text
    assert r.json()["code"] == "COMPANY_CONTEXT_REQUIRED"


def test_con_una_sola_empresa_se_resuelve_sola(mundo):
    r = mundo.client.get("/api/v1/maestros/terceros", headers=mundo.como("ua"))
    assert r.status_code == 200


def test_una_cabecera_inventada_no_abre_nada(mundo):
    r = mundo.client.get("/api/v1/maestros/terceros",
                         headers=mundo.como("ua", "00000000-0000-0000-0000-000000000000"))
    assert r.status_code == 404


# --------------------------------------------------------------- maestros
def _tercero(mundo, usuario, empresa, code):
    return mundo.client.post("/api/v1/maestros/terceros",
                             headers=mundo.como(usuario, empresa),
                             json={"code": code, "name": f"Tercero {code}",
                                   "roles": ["CLIENTE"]})


def test_el_dato_guarda_la_empresa_no_el_tenant(mundo):
    """La comprobación que no se puede sustituir por «la API filtra bien».

    Se mira la base, no la respuesta: si `company_id` guardase el tenant, el
    filtro seguiría funcionando y el dato seguiría siendo indistinguible.
    """
    r = _tercero(mundo, "ua", mundo.company_a, "T-DB-A")
    assert r.status_code == 200, r.text
    db = mundo.factory()
    try:
        guardado = db.execute(text(
            "SELECT company_id FROM parties WHERE id = :i"),
            {"i": r.json()["id"]}).scalar_one()
    finally:
        db.close()
    assert guardado == mundo.company_a
    assert guardado != mundo.t1, "guardó el tenant, no la empresa"


def test_la_lista_de_a_no_contiene_lo_de_b(mundo):
    a = _tercero(mundo, "ua", mundo.company_a, "T-LISTA-A")
    b = _tercero(mundo, "ub", mundo.company_b, "T-LISTA-B")
    assert a.status_code == b.status_code == 200

    en_a = mundo.client.get("/api/v1/maestros/terceros",
                            headers=mundo.como("ua", mundo.company_a)).json()
    en_b = mundo.client.get("/api/v1/maestros/terceros",
                            headers=mundo.como("ub", mundo.company_b)).json()
    ids_a = {x["id"] for x in en_a.get("items", en_a if isinstance(en_a, list) else [])}
    ids_b = {x["id"] for x in en_b.get("items", en_b if isinstance(en_b, list) else [])}

    assert a.json()["id"] in ids_a
    assert b.json()["id"] in ids_b
    assert a.json()["id"] not in ids_b
    assert b.json()["id"] not in ids_a
    assert not (ids_a & ids_b), "hay filas visibles desde las dos empresas"


def test_el_detalle_ajeno_responde_no_encontrado(mundo):
    b = _tercero(mundo, "ub", mundo.company_b, "T-DET-B")
    r = mundo.client.get(f"/api/v1/maestros/terceros/{b.json()['id']}",
                         headers=mundo.como("ua", mundo.company_a))
    assert r.status_code == 404, r.text


def test_no_se_puede_editar_lo_de_la_otra_empresa(mundo):
    b = _tercero(mundo, "ub", mundo.company_b, "T-UPD-B")
    # `maestros` no expone PATCH; la mutación es desactivar.
    r = mundo.client.post(f"/api/v1/maestros/terceros/{b.json()['id']}/deactivate",
                          headers=mundo.como("ua", mundo.company_a))
    assert r.status_code in (403, 404), r.text


# --------------------------------------------------- el usuario con dos
def test_el_usuario_con_dos_empresas_ve_una_cada_vez(mundo):
    a = _tercero(mundo, "uab", mundo.company_a, "T-AB-A")
    b = _tercero(mundo, "uab", mundo.company_b, "T-AB-B")
    assert a.status_code == b.status_code == 200

    en_a = mundo.client.get("/api/v1/maestros/terceros",
                            headers=mundo.como("uab", mundo.company_a)).json()
    en_b = mundo.client.get("/api/v1/maestros/terceros",
                            headers=mundo.como("uab", mundo.company_b)).json()
    ids_a = {x["id"] for x in en_a["items"]}
    ids_b = {x["id"] for x in en_b["items"]}
    assert a.json()["id"] in ids_a and a.json()["id"] not in ids_b
    assert b.json()["id"] in ids_b and b.json()["id"] not in ids_a


def test_el_cuerpo_no_puede_contradecir_al_contexto(mundo):
    """Enviar la empresa B operando en A no debe colar la fila en B."""
    r = mundo.client.post("/api/v1/maestros/terceros",
                          headers=mundo.como("ua", mundo.company_a),
                          json={"code": "T-FORJA", "name": "Forjado",
                                "roles": ["CLIENTE"],
                                "company_id": mundo.company_b})
    if r.status_code == 200:
        db = mundo.factory()
        try:
            guardado = db.execute(text(
                "SELECT company_id FROM parties WHERE id = :i"),
                {"i": r.json()["id"]}).scalar_one()
        finally:
            db.close()
        assert guardado == mundo.company_a, "el cuerpo del cliente decidió la empresa"
    else:
        assert r.status_code in (409, 422), r.text


# ------------------------------------- fronteras con las Specs ya cerradas
def test_documentos_acota_por_tenant_no_por_la_empresa_activa(mundo):
    """Hallazgo comprobado por comportamiento, no corregido aquí.

    La Spec 046 resuelve el alcance con un ayudante propio que admite
    **cualquier empresa del tenant**, no la del contexto activo. Era coherente
    cuando se escribió —tenant y empresa eran lo mismo— y deja de serlo con dos.

    Su corrección pertenece a N9, junto con el resto de `REM-046-001`. Tocarla
    aquí reabriría una Spec cerrada sin autorización, así que se fija el hecho
    para que no se pierda entre las que sí quedaron normalizadas.
    """
    tipo_b = mundo.client.post("/api/v1/documentos/tipos",
                               headers=mundo.como("ub", mundo.company_b),
                               json={"company_id": mundo.company_b, "code": "TB",
                                     "name": "Tipo de B",
                                     "allowed_mime_types": ["application/pdf"],
                                     "scan_required": False})
    if tipo_b.status_code != 200:
        pytest.skip(f"no se pudo sembrar el tipo documental: {tipo_b.status_code}")

    doc_b = mundo.client.post("/api/v1/documentos",
                              headers=mundo.como("ub", mundo.company_b),
                              json={"company_id": mundo.company_b,
                                    "document_type_id": tipo_b.json()["id"],
                                    "title": "Documento de B"})
    assert doc_b.status_code == 200, doc_b.text

    visto_por_a = mundo.client.get(f"/api/v1/documentos/{doc_b.json()['id']}",
                                   headers=mundo.como("ua", mundo.company_a))
    assert visto_por_a.status_code == 200, (
        "Si esto ya responde 404, el hallazgo se corrigió: "
        "actualizar la prueba y cerrarlo en N9")


def test_aprobaciones_recibe_la_empresa_del_cliente_sin_contrastarla(mundo):
    """Mismo caso en la Spec 045, por otra vía.

    045 toma la empresa del cuerpo de la petición. Con una sola empresa era
    equivalente a tomarla del contexto; con dos, permite declarar una empresa
    que no es en la que se está operando.

    También es N9: 045 está `COMPLETE_100` y su modelo no se degrada aquí.
    """
    r = mundo.client.post("/api/v1/approvals/policies",
                          headers=mundo.como("ua", mundo.company_a),
                          json={"company_id": mundo.company_b,
                                "process_type": "PURCHASE_ORDER",
                                "code": "POL-CRUZADA", "name": "Cruzada",
                                "requires_segregation": False})
    if r.status_code not in (200, 201):
        pytest.skip(f"la ruta de políticas respondió {r.status_code}")
    db = mundo.factory()
    try:
        guardada = db.execute(text(
            "SELECT company_id FROM approval_policies WHERE id = :i"),
            {"i": r.json()["id"]}).scalar_one()
    finally:
        db.close()
    assert guardada == mundo.company_b, (
        "Si ya guarda la empresa del contexto, el hallazgo se corrigió")
