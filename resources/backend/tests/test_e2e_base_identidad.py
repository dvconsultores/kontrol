"""E2EID · La compuerta de identidad de las bases de corrida E2E (FR-054-E2EDB-004, 005, 015).

Crear y eliminar bases es lo más destructivo que hace el arnés del E2E. Antes de cualquier
sentencia, la compuerta decide por el nombre, el entorno y el servidor si esa base es de una
corrida. Aquí se prueba lo que deja pasar y, sobre todo, lo que no: `kaud`, `ktest`, la base
del producto, un entorno que sirve a usuarios, un servidor que no es de QA.

No toca ninguna base: las direcciones son inventadas.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "qa"))

import e2e_base as b  # noqa: E402

RUN = "r20261001t213355p4242n3fa9c1"
BASE = "kontrol_e2e_test_" + RUN
ADMIN = "postgresql+psycopg2://user:pass@localhost:5432/postgres"
DUENA = "postgresql+psycopg2://owner:pass@localhost:5432/postgres"
SERVIDOR = b.Servidor(admin_url=ADMIN, duena_url=DUENA)


@pytest.fixture
def sin_sql(monkeypatch):
    """Cualquier intento de abrir una conexión administrativa hace fallar la prueba."""
    def prohibido(*_a, **_k):
        raise AssertionError("se intentó abrir una conexión antes de pasar la compuerta")

    monkeypatch.setattr(b, "motor_administrativo", prohibido)


def test_e2eid_01_una_base_de_corrida_en_qa_pasa_y_devuelve_su_run():
    assert b.exigir_base_e2e(BASE, admin_url=ADMIN, entorno={}) == RUN


@pytest.mark.parametrize("nombre", [
    "", None, 7, "kontrol", "kontrol_e2e_test_", "kontrol_test_" + RUN, "e2e_test_" + RUN, BASE + "x", "x" + BASE,
    BASE + "\n", " " + BASE, BASE.upper(), BASE + "; drop database postgres", "kontrol_e2e_test_proto_173514",
])
def test_e2eid_02_un_nombre_que_no_cumple_el_patron_entero_se_rechaza(nombre):
    with pytest.raises(b.BaseNoEsE2E):
        b.exigir_base_e2e(nombre, admin_url=ADMIN, entorno={})


@pytest.mark.parametrize("nombre", ["kaud", "ktest", "postgres", "template0", "template1"])
def test_e2eid_03_las_bases_de_qa_y_las_del_sistema_se_rechazan(nombre):
    with pytest.raises(b.BaseNoEsE2E):
        b.exigir_base_e2e(nombre, admin_url=ADMIN, entorno={})


@pytest.mark.parametrize("nombre", ["kaud", "ktest", "postgres"])
def test_e2eid_04_eliminar_no_llega_a_abrir_una_conexion_si_el_nombre_no_es_de_corrida(nombre, sin_sql):
    with pytest.raises(b.BaseNoEsE2E):
        b.soltar_base(SERVIDOR, nombre, entorno={})


@pytest.mark.parametrize("variable", ["KONTROL_DB_URL", "KONTROL_TEST_DB_URL"])
def test_e2eid_05_la_base_configurada_para_el_producto_o_para_las_pruebas_esta_protegida(variable, sin_sql):
    entorno = {variable: "postgresql://user:pass@host:5432/" + BASE}
    with pytest.raises(b.BaseNoEsE2E, match="protegida"):
        b.exigir_base_e2e(BASE, admin_url=ADMIN, entorno=entorno)
    with pytest.raises(b.BaseNoEsE2E, match="protegida"):
        b.soltar_base(SERVIDOR, BASE, entorno=entorno)


def test_e2eid_06_una_base_declarada_protegida_lo_esta_aunque_cumpla_el_patron(sin_sql):
    entorno = {"KONTROL_E2E_PROTECTED_DBS": f"otra, {BASE.upper()} ,"}
    with pytest.raises(b.BaseNoEsE2E, match="protegida"):
        b.soltar_base(SERVIDOR, BASE, entorno=entorno)


@pytest.mark.parametrize("ambiente", ["prod", "staging", "uat", "", "PROD", "produccion"])
def test_e2eid_07_un_entorno_que_sirve_a_usuarios_se_rechaza(ambiente, sin_sql):
    entorno = {"KONTROL_ENVIRONMENT": ambiente}
    with pytest.raises(b.BaseNoEsE2E, match="KONTROL_ENVIRONMENT"):
        b.exigir_base_e2e(BASE, admin_url=ADMIN, entorno=entorno)
    with pytest.raises(b.BaseNoEsE2E):
        b.crear_base(SERVIDOR, RUN, entorno=entorno)
    with pytest.raises(b.BaseNoEsE2E):
        b.soltar_base(SERVIDOR, BASE, entorno=entorno)


@pytest.mark.parametrize("ambiente", ["local", "dev", "qa"])
def test_e2eid_08_los_entornos_de_qa_pasan(ambiente):
    assert b.exigir_base_e2e(BASE, admin_url=ADMIN, entorno={"KONTROL_ENVIRONMENT": ambiente}) == RUN


def test_e2eid_09_un_servidor_que_no_esta_en_la_lista_se_rechaza(sin_sql):
    remoto = "postgresql+psycopg2://user:pass@db.example.com:5432/postgres"
    with pytest.raises(b.BaseNoEsE2E, match="permitidos"):
        b.exigir_base_e2e(BASE, admin_url=remoto, entorno={})
    with pytest.raises(b.BaseNoEsE2E):
        b.crear_base(b.Servidor(admin_url=remoto, duena_url=remoto), RUN, entorno={})
    declarado = {"KONTROL_E2E_PG_HOSTS": "localhost, DB.example.com"}
    assert b.exigir_base_e2e(BASE, admin_url=remoto, entorno=declarado) == RUN


def test_e2eid_10_el_bucle_local_es_localhost():
    assert b.exigir_base_e2e(BASE, admin_url="postgresql://user:pass@127.0.0.1:5432/postgres", entorno={}) == RUN


@pytest.mark.parametrize("admin", [
    "sqlite:///qa.db", "mysql://user:pass@localhost:3306/mysql", "esto no es una url", "",
])
def test_e2eid_11_un_servidor_que_no_es_postgresql_se_rechaza(admin):
    with pytest.raises(b.BaseNoEsE2E):
        b.exigir_base_e2e(BASE, admin_url=admin, entorno={})


def test_e2eid_12_las_protegidas_por_defecto_y_las_declaradas():
    assert b.protegidas(ADMIN, {}) == {"postgres", "template0", "template1", "kaud", "ktest"}
    declaradas = b.protegidas(ADMIN, {
        "KONTROL_E2E_PROTECTED_DBS": "uno, DOS ,,",
        "KONTROL_DB_URL": "postgresql://user:pass@host:5432/producto",
        "KONTROL_TEST_DB_URL": "postgresql://user:pass@host:5432/test_db",
    })
    assert declaradas == {"postgres", "template0", "template1", "uno", "dos", "producto", "test_db"}


def test_e2eid_13_la_url_de_la_corrida_apunta_a_su_base_y_lleva_su_nombre_de_aplicacion():
    url = SERVIDOR.url_de(BASE)
    assert url == f"postgresql+psycopg2://owner:pass@localhost:5432/{BASE}?application_name=kontrol-e2e:{RUN}"
    assert "%" not in url
    con_opciones = b.Servidor(admin_url=ADMIN, duena_url=DUENA + "?sslmode=disable").url_de(BASE)
    assert con_opciones.endswith(f"/{BASE}?sslmode=disable&application_name=kontrol-e2e:{RUN}")


@pytest.mark.parametrize("nombre", ["kaud", "ktest", "postgres", BASE + "x"])
def test_e2eid_14_no_se_construye_una_url_hacia_una_base_que_no_es_de_corrida(nombre):
    with pytest.raises(b.BaseNoEsE2E):
        SERVIDOR.url_de(nombre)


def test_e2eid_15_el_rol_dueno_y_el_administrativo_tienen_que_estar_en_el_mismo_servidor():
    partido = b.Servidor(admin_url=ADMIN, duena_url="postgresql+psycopg2://owner:pass@otro-host:5432/postgres")
    with pytest.raises(b.CicloDeBaseRoto, match="servidores distintos"):
        partido.url_de(BASE)


def test_e2eid_16_el_destino_que_se_escribe_en_los_registros_no_lleva_credenciales():
    assert SERVIDOR.destino() == "localhost:5432"


def test_e2eid_17_el_servidor_se_toma_del_entorno_cuando_se_declara():
    servidor = b.Servidor.del_entorno({"KONTROL_E2E_ADMIN_DB_URL": ADMIN, "KONTROL_E2E_OWNER_DB_URL": DUENA})
    assert (servidor.admin_url, servidor.duena_url) == (ADMIN, DUENA)
    assert b.Servidor.del_entorno({"KONTROL_PGPORT": "6543"}).destino() == "localhost:6543"


@pytest.mark.parametrize("duena", [
    "postgresql+psycopg2://localhost:5432/postgres",
    "postgresql+psycopg2://Owner:pass@localhost:5432/postgres",
    "postgresql+psycopg2://1owner:pass@localhost:5432/postgres",
    "postgresql+psycopg2://ow-ner:pass@localhost:5432/postgres",
])
def test_e2eid_18_el_rol_dueno_tiene_que_ser_un_identificador_simple(duena, sin_sql):
    servidor = b.Servidor(admin_url=ADMIN, duena_url=duena)
    with pytest.raises(b.CicloDeBaseRoto, match="identificador simple"):
        servidor.rol_dueno()
    with pytest.raises(b.CicloDeBaseRoto):
        b.crear_base(servidor, RUN, entorno={})
