"""PG-LIFE-10 · La compuerta de identidad del arnés (FR-054-PGLIFE-011).

El arnés de pruebas crea y elimina schemas en PostgreSQL, y eso es destructivo: un error
de apuntado borraría datos reales. Antes de crear o destruir nada, exige varias señales,
todas necesarias, de que la base indicada es de prueba. Estas pruebas no tocan ninguna
base de datos: solo ejercen la función pura y las variables de entorno que la gobiernan.
"""

from __future__ import annotations

import pg_harness
import pytest

URL = "postgresql+psycopg2://qa@localhost:55432/ktest"
OTRA = "postgresql+psycopg2://qa@localhost:55432/kontrol_test_2"


@pytest.fixture
def entorno(monkeypatch):
    """Un entorno de prueba válido: la URL declarada, entorno local y el producto en SQLite."""
    monkeypatch.setenv("KONTROL_TEST_DB_URL", URL)
    monkeypatch.setenv("KONTROL_ENVIRONMENT", "local")
    monkeypatch.setenv("KONTROL_DB_URL", "sqlite+pysqlite:///:memory:")
    return monkeypatch


def test_gate_01_una_base_de_prueba_declarada_pasa(entorno):
    assert pg_harness.exigir_base_de_prueba(URL) is None


def test_gate_02_una_url_que_no_es_la_declarada_se_rechaza(entorno):
    with pytest.raises(pg_harness.BaseNoEsDePrueba, match="KONTROL_TEST_DB_URL"):
        pg_harness.exigir_base_de_prueba(OTRA)


def test_gate_03_sin_url_declarada_se_rechaza(entorno):
    entorno.delenv("KONTROL_TEST_DB_URL")
    with pytest.raises(pg_harness.BaseNoEsDePrueba, match="KONTROL_TEST_DB_URL"):
        pg_harness.exigir_base_de_prueba(URL)


def test_gate_04_una_base_que_no_es_postgresql_se_rechaza(entorno):
    sqlite = "sqlite+pysqlite:///test.db"
    entorno.setenv("KONTROL_TEST_DB_URL", sqlite)
    with pytest.raises(pg_harness.BaseNoEsDePrueba, match="PostgreSQL"):
        pg_harness.exigir_base_de_prueba(sqlite)


@pytest.mark.parametrize("base", ["kontrol", "kaud", "produccion", "erp_cliente"])
def test_gate_05_un_nombre_que_no_dice_prueba_se_rechaza(entorno, base):
    url = f"postgresql+psycopg2://qa@localhost:55432/{base}"
    entorno.setenv("KONTROL_TEST_DB_URL", url)
    with pytest.raises(pg_harness.BaseNoEsDePrueba, match="test"):
        pg_harness.exigir_base_de_prueba(url)


@pytest.mark.parametrize("base", ["ktest", "kontrol_test", "TEST_qa", "pruebas_test_1"])
def test_gate_06_un_nombre_de_prueba_se_acepta(entorno, base):
    url = f"postgresql+psycopg2://qa@localhost:55432/{base}"
    entorno.setenv("KONTROL_TEST_DB_URL", url)
    assert pg_harness.exigir_base_de_prueba(url) is None


@pytest.mark.parametrize("valor", ["prod", "staging", "uat", "produccion", ""])
def test_gate_07_un_entorno_que_sirve_a_usuarios_se_rechaza(entorno, valor):
    entorno.setenv("KONTROL_ENVIRONMENT", valor)
    with pytest.raises(pg_harness.BaseNoEsDePrueba, match="KONTROL_ENVIRONMENT"):
        pg_harness.exigir_base_de_prueba(URL)


@pytest.mark.parametrize("valor", ["local", "dev", "qa"])
def test_gate_08_los_entornos_de_prueba_se_aceptan(entorno, valor):
    entorno.setenv("KONTROL_ENVIRONMENT", valor)
    assert pg_harness.exigir_base_de_prueba(URL) is None


def test_gate_08b_sin_entorno_declarado_vale_local(entorno):
    entorno.delenv("KONTROL_ENVIRONMENT")
    assert pg_harness.exigir_base_de_prueba(URL) is None


def test_gate_08c_la_lista_de_entornos_es_la_escrita():
    assert pg_harness.ENTORNOS_DE_PRUEBA == ("local", "dev", "qa")


@pytest.mark.parametrize(
    "producto",
    [
        "postgresql+psycopg2://qa@localhost:55432/ktest",
        "postgresql://otro@127.0.0.1:55432/ktest",
        "postgresql+psycopg2://app@LOCALHOST:55432/ktest",
    ],
)
def test_gate_09_la_base_del_producto_no_puede_ser_la_de_prueba(entorno, producto):
    entorno.setenv("KONTROL_DB_URL", producto)
    with pytest.raises(pg_harness.BaseNoEsDePrueba, match="KONTROL_DB_URL"):
        pg_harness.exigir_base_de_prueba(URL)


@pytest.mark.parametrize(
    "producto",
    [
        "postgresql+psycopg2://app@localhost:55432/kontrol",
        "postgresql+psycopg2://app@localhost:5432/ktest",
        "postgresql+psycopg2://app@db.interna:55432/ktest",
        "sqlite+pysqlite:///:memory:",
    ],
)
def test_gate_10_un_producto_en_otra_base_otro_puerto_u_otro_servidor_no_bloquea(entorno, producto):
    entorno.setenv("KONTROL_DB_URL", producto)
    assert pg_harness.exigir_base_de_prueba(URL) is None


def test_gate_11_el_puerto_por_defecto_es_el_5432(entorno):
    url = "postgresql+psycopg2://qa@localhost/ktest"
    entorno.setenv("KONTROL_TEST_DB_URL", url)
    entorno.setenv("KONTROL_DB_URL", "postgresql+psycopg2://app@127.0.0.1:5432/ktest")
    with pytest.raises(pg_harness.BaseNoEsDePrueba, match="KONTROL_DB_URL"):
        pg_harness.exigir_base_de_prueba(url)


# El nombre de un schema temporal: lo único que el arnés llega a eliminar.
@pytest.mark.parametrize("nombre", ["t_0123456789ab", "t_abcdefabcdef", "t_000000000000"])
def test_gate_12_el_patron_reconoce_los_schemas_del_arnes(nombre):
    assert pg_harness.PATRON_DE_SCHEMA.fullmatch(nombre)


@pytest.mark.parametrize(
    "nombre",
    [
        "public",
        "t_",
        "t_0123456789a",
        "t_0123456789abc",
        "t_0123456789AB",
        "t_0123456789ag",
        "x_0123456789ab",
        "t_0123456789ab; DROP SCHEMA public",
        "pg_catalog",
        "",
    ],
)
def test_gate_13_el_patron_no_reconoce_nada_mas(nombre):
    assert not pg_harness.PATRON_DE_SCHEMA.fullmatch(nombre)
