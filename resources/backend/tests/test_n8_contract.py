"""El contrato de empresa, y lo que ya no debe existir (ARCH-MC-001, fase N8).

Dos cosas distintas se comprueban aquí. Que el contrato publicado describa el
sistema que existe —ni más restrictivo ni más permisivo— y que no quede en el
producto activo ninguna semántica de la etapa en que empresa y tenant eran lo
mismo.
"""

from __future__ import annotations

import ast
import pathlib

import pytest
from sqlalchemy import text

from app.core.company_context import COMPANY_HEADER
from app.main import create_app

pytest_plugins = ("tests.conftest_multicompany",)

RAIZ = pathlib.Path(__file__).resolve().parents[1] / "app"

#: Prefijos que **no** son de empresa: autenticación, la propia lista de
#: empresas, instalación, licencia y salud.
SIN_EMPRESA = ("/api/v1/auth/", "/api/v1/organization/companies",
               "/api/v1/setup", "/api/v1/system", "/api/v1/license",
               "/api/v1/health", "/api/v1/diagnostics")


@pytest.fixture(scope="module")
def contrato():
    return create_app().openapi()


def _operaciones(spec):
    for ruta, ops in spec["paths"].items():
        for metodo, op in ops.items():
            if isinstance(op, dict):
                yield metodo.upper(), ruta, op


def _declara_empresa(op) -> bool:
    return any(p.get("name") == COMPANY_HEADER for p in op.get("parameters", []))


# ------------------------------------------------- el contrato publicado
def test_las_operaciones_de_empresa_declaran_la_cabecera(contrato):
    """Sin esto, quien lea el contrato no sabría que la cabecera existe.

    Funcionaba desde N1 y la usaban 112 pruebas, pero la dependencia la leía del
    `Request` en lugar de declararla, así que FastAPI no podía publicarla.
    """
    con_cabecera = [f"{m} {r}" for m, r, op in _operaciones(contrato) if _declara_empresa(op)]
    assert len(con_cabecera) > 300, (
        f"solo {len(con_cabecera)} operaciones la declaran: el contrato no describe el runtime")


def test_la_cabecera_no_aparece_donde_no_aplica(contrato):
    """Declararla en todas partes sería tan falso como no declararla en ninguna."""
    intrusas = [
        f"{m} {r}" for m, r, op in _operaciones(contrato)
        if _declara_empresa(op) and r.startswith(SIN_EMPRESA)
    ]
    assert intrusas == [], f"la cabecera aparece donde no aplica: {intrusas}"


def test_la_cabecera_se_declara_opcional(contrato):
    """El runtime la resuelve solo cuando el usuario tiene una empresa.

    Declararla obligatoria describiría un sistema distinto, y quien leyera el
    contrato enviaría siempre una cabecera que a veces sobra.
    """
    for m, r, op in _operaciones(contrato):
        for p in op.get("parameters", []):
            if p.get("name") == COMPANY_HEADER:
                assert p.get("required") is not True, (
                    f"{m} {r} declara la cabecera como obligatoria")
                assert p.get("in") == "header"
                assert "COMPANY_CONTEXT_REQUIRED" in (p.get("description") or ""), (
                    f"{m} {r} no explica qué ocurre sin ella")
                return
    pytest.fail("ninguna operación declara la cabecera")


def test_hay_una_sola_lectura_de_la_cabecera():
    """Dos lecturas del mismo dato serían dos autoridades sobre la misma decisión.

    La dependencia declara el parámetro; nadie debe además sacarlo del
    `Request` por su cuenta.
    """
    lecturas = []
    for archivo in RAIZ.rglob("*.py"):
        texto = archivo.read_text()
        if "COMPANY_HEADER" in texto and "request.headers" in texto:
            arbol = ast.parse(texto)
            for nodo in ast.walk(arbol):
                if (isinstance(nodo, ast.Attribute) and nodo.attr == "get"
                        and isinstance(nodo.value, ast.Attribute)
                        and nodo.value.attr == "headers"):
                    lecturas.append(str(archivo.relative_to(RAIZ)))
    assert lecturas == [], f"la cabecera se lee del Request además de declararse: {lecturas}"


# ------------------------------------------------- comportamiento real
def test_con_una_sola_empresa_la_cabecera_puede_omitirse(mundo):
    r = mundo.client.get("/api/v1/maestros/terceros",
                         headers={"Authorization": f"Bearer {mundo.token('ua')}"})
    assert r.status_code == 200, f"la auto-resolución dejó de funcionar: {r.text}"


def test_con_varias_empresas_la_ausencia_es_un_error_definido(mundo):
    r = mundo.client.get("/api/v1/maestros/terceros",
                         headers={"Authorization": f"Bearer {mundo.token('uab')}"})
    assert r.status_code == 400
    assert r.json()["code"] == "COMPANY_CONTEXT_REQUIRED"


def test_una_ruta_que_no_es_de_empresa_funciona_sin_cabecera(mundo):
    r = mundo.client.get("/api/v1/organization/companies",
                         headers={"Authorization": f"Bearer {mundo.token('uab')}"})
    assert r.status_code == 200


# ------------------------------------------------- lo que ya no debe existir
def test_no_queda_repliegue_de_empresa_a_tenant():
    """El defecto de origen, buscado por estructura.

    `warehouse_in_tenant_scope` reconciliaba ambos identificadores y su
    docstring lo describía como diseño vigente. Se retiró en N8.
    """
    culpables = []
    for archivo in RAIZ.rglob("*.py"):
        if archivo.parts[-2:] == ("mc", "runner.py") or "core/mc" in str(archivo):
            continue          # el módulo de migración sí habla del legado
        texto = archivo.read_text()
        if "warehouse_in_tenant_scope" in texto and "Sustituye a" not in texto:
            culpables.append(str(archivo.relative_to(RAIZ)))
        for patron in ("company_id = tenant_id", "company_id or tenant_id",
                       "company_id ?? tenant_id"):
            if patron in texto:
                culpables.append(f"{archivo.relative_to(RAIZ)}: {patron}")
    assert culpables == [], f"queda semántica de tenant como empresa: {culpables}"


def test_el_runtime_no_importa_el_modulo_de_migracion():
    """La lógica de legado vive aparte y nadie de producción la usa."""
    culpables = []
    for archivo in (RAIZ / "modules").rglob("*.py"):
        texto = archivo.read_text()
        if "app.core.mc" in texto:
            culpables.append(str(archivo.relative_to(RAIZ)))
    assert culpables == [], f"módulos productivos importan la migración: {culpables}"


def test_las_columnas_de_transicion_no_estan_en_la_base(mundo):
    """`legacy_scope_id` y `scope_backfill_class` nunca llegaron al modelo.

    N3 las añadió por migración como red de seguridad para un backfill que
    resultó no ser necesario. Ningún modelo las declaró y nadie las leyó.
    """
    db = mundo.factory()
    try:
        for col in ("legacy_scope_id", "scope_backfill_class"):
            n = db.execute(text(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND column_name = :c"),
                {"c": col}).scalar_one()
            assert n == 0, f"{col} sigue en {n} tablas del esquema operativo"
    finally:
        db.close()


# ------------------------------------------------- nulos legítimos
def test_el_alcance_global_sigue_siendo_posible(mundo):
    """N7 endureció por error estas dos columnas y hubo que revertirlo.

    Las filas globales existentes se conservan (OD-ISO-10), por eso las
    columnas siguen admitiendo nulo; crearlas desde una empresa ya no se
    permite y da 403 `GLOBAL_SCOPE_FORBIDDEN`. Confundir el nulo con deuda de
    la transición habría eliminado esas filas.
    """
    from app.core.database import Base, init_models

    init_models()
    for tabla in ("movement_types", "costing_profiles"):
        col = Base.metadata.tables[tabla].c["company_id"]
        assert col.nullable, f"{tabla} perdió su alcance global"
        assert col.foreign_keys, f"{tabla} admite nulo pero no referencia a companies"
