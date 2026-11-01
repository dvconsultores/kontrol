"""Los 23 tipos vinculables, uno por uno (ARCH-MC-001, fase N9).

`REM-046-001` cerró con una frase que resume la fase: *el registro existía; la
capacidad, no*. Diecinueve tipos declarados y **una** vinculación ejercitada por
las pruebas — la de `ApprovalRequest`, que además era la única cuyo fixture
usaba una empresa real.

Aquí cada tipo tiene su entidad persistida en PostgreSQL, su documento, su
vínculo y sus tres comprobaciones: que la empresa propia funciona, que otra
empresa no puede, y que otro tenant tampoco. Si un tipo no se puede sembrar, su
caso **falla**: un tipo que no se puede crear tampoco se puede vincular, y
saltarlo lo escondería entre los que sí funcionan.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from app.modules.documents.resources import RESOURCE_KINDS
from tests.n9_resource_seeds import sembrar

pytest_plugins = ("tests.conftest_multicompany",)

TIPOS = sorted(RESOURCE_KINDS)

#: Sin empresa propia: el acto de homologación es de la instalación, no de una
#: empresa, y el registro lo declara así. Su control se apoya en el permiso.
SIN_EMPRESA = {"HomologationRecord"}


def _pg(mundo) -> None:
    if "postgresql" not in os.environ.get("KONTROL_TEST_DB_URL", ""):
        pytest.skip("La vinculación documental se verifica sobre PostgreSQL")


def _tipo_documental(mundo, usuario, empresa, code):
    return mundo.crear("/documentos/tipos", usuario, empresa, {
        "code": code, "name": f"Tipo {code}",
        "allowed_mime_types": ["application/pdf"], "scan_required": False})


def _documento(mundo, usuario, empresa, tipo, titulo):
    return mundo.crear("/documentos", usuario, empresa,
                       {"document_type_id": tipo, "title": titulo})


def _vincular(mundo, usuario, empresa, documento, kind, recurso):
    return mundo.post(f"/documentos/{documento}/vinculos", usuario, empresa,
                      {"resource_type": kind, "resource_id": recurso, "role": "EVIDENCIA"})


# ------------------------------------------------- el registro
def test_el_registro_tiene_la_cardinalidad_esperada():
    """19 antes de N9, más las 4 de `REM-046-001`, más `ReceiptIncident` (020) y `GovernmentEntity` (GOV-0-01) y `GovernmentStructure` (GOV-0-02).

    El número es fijo a propósito: el registro está **cerrado**, y añadir un tipo
    sin semilla ni permiso declarado debe romper aquí y no en producción.
    """
    assert len(RESOURCE_KINDS) == 27, (
        f"se esperaban 27 tipos y hay {len(RESOURCE_KINDS)}: {sorted(RESOURCE_KINDS)}")
    for exigido in ("Payment", "BankTransaction", "CashSession", "Reconciliation"):
        assert exigido in RESOURCE_KINDS, f"{exigido} sigue sin registrarse"


def test_cada_tipo_declara_entidad_clave_y_permiso():
    from app.modules.documents.resources import _load_model

    problemas = []
    for nombre, kind in sorted(RESOURCE_KINDS.items()):
        try:
            modelo = _load_model(kind)
        except Exception as exc:                      # noqa: BLE001
            problemas.append(f"{nombre}: el modelo no carga ({exc})")
            continue
        claves = [c.name for c in modelo.__table__.primary_key]
        if len(claves) != 1:
            problemas.append(f"{nombre}: clave primaria compuesta {claves}")
        if not kind.permission:
            problemas.append(f"{nombre}: sin permiso declarado")
        if not kind.company_attr:
            problemas.append(f"{nombre}: sin columna de empresa declarada")
    assert problemas == [], "\n  ".join(["tipos mal declarados:", *problemas])


def test_un_tipo_inventado_se_rechaza(mundo):
    """El registro es cerrado: no hay texto libre ni resolución por reflexión."""
    _pg(mundo)
    tipo = _tipo_documental(mundo, "ua", mundo.company_a, "N9-DESC")
    doc = _documento(mundo, "ua", mundo.company_a, tipo, "Documento")
    for inventado in ("AnyModel", "parties", "app.modules.master_data.models.Party",
                      "Party; DROP TABLE documents"):
        r = _vincular(mundo, "ua", mundo.company_a, doc, inventado, "x")
        assert r.status_code == 422, f"«{inventado}» fue aceptado: {r.status_code}"
        assert r.json()["code"] == "RESOURCE_TYPE_UNKNOWN"


# ------------------------------------------------- los 23, uno a uno
@pytest.mark.parametrize("kind", TIPOS)
def test_cada_tipo_se_vincula_en_su_empresa_y_no_en_la_ajena(mundo, kind):
    """Alcance propio, cruce entre empresas y cruce entre tenants, por tipo.

    El fallo nombra el tipo: una parametrización que no distinguiera cuál falló
    valdría lo mismo que la prueba genérica que esto viene a sustituir.
    """
    _pg(mundo)
    db = mundo.factory()
    try:
        recurso_a = sembrar(db, kind, mundo.company_a, f"{kind[:8]}A")
        recurso_b = sembrar(db, kind, mundo.company_b, f"{kind[:8]}B")
        db.commit()
    finally:
        db.close()

    # La semilla existe de verdad: sin esto, todo lo que sigue sería aritmética
    # sobre la nada.
    db = mundo.factory()
    try:
        from app.modules.documents.resources import _load_model
        tabla = _load_model(RESOURCE_KINDS[kind]).__tablename__
        n = db.execute(text(f"SELECT count(*) FROM {tabla} WHERE id = :i"),
                       {"i": recurso_a}).scalar_one()
        assert n == 1, f"{kind}: la semilla no se persistió"
    finally:
        db.close()

    tipo = _tipo_documental(mundo, "ua", mundo.company_a, f"N9-{kind[:12]}")
    doc_a = _documento(mundo, "ua", mundo.company_a, tipo, f"Documento de {kind}")

    # 1. Su propia empresa: se vincula.
    r = _vincular(mundo, "ua", mundo.company_a, doc_a, kind, recurso_a)
    assert r.status_code == 200, f"{kind}: no se pudo vincular en su empresa — {r.text}"

    if kind in SIN_EMPRESA:
        # Sin columna de empresa el control es solo de permiso: comprobar un
        # cruce que el contrato no promete daría un falso positivo.
        return

    # 2. Un recurso de otra empresa, desde la empresa A: bloqueado.
    r = _vincular(mundo, "ua", mundo.company_a, doc_a, kind, recurso_b)
    assert r.status_code == 404, (
        f"{kind}: se vinculó un recurso de la empresa B desde la A — {r.status_code}")

    # 3. Y el vínculo cruzado no quedó escrito.
    db = mundo.factory()
    try:
        n = db.execute(text(
            "SELECT count(*) FROM document_links WHERE resource_id = :r"),
            {"r": recurso_b}).scalar_one()
        assert n == 0, f"{kind}: quedó un vínculo hacia el recurso ajeno"
    finally:
        db.close()


@pytest.mark.parametrize("kind", [k for k in TIPOS if k not in SIN_EMPRESA])
def test_ningun_tipo_cruza_la_frontera_entre_tenants(mundo, kind):
    _pg(mundo)
    db = mundo.factory()
    try:
        recurso_c = sembrar(db, kind, mundo.company_c, f"{kind[:8]}C")
        db.commit()
    finally:
        db.close()

    tipo = _tipo_documental(mundo, "ua", mundo.company_a, f"N9T-{kind[:11]}")
    doc_a = _documento(mundo, "ua", mundo.company_a, tipo, f"Documento {kind}")
    r = _vincular(mundo, "ua", mundo.company_a, doc_a, kind, recurso_c)
    assert r.status_code == 404, (
        f"{kind}: se vinculó un recurso de otro tenant — {r.status_code}")
