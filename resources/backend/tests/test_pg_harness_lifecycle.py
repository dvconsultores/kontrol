"""PG-LIFE · Lo que la suite crea en PostgreSQL, lo suelta (FR-054-PGLIFE-001..017).

`make_engine` creaba un schema entero y un motor en cada llamada y nadie los soltaba: una
corrida completa dejaba más de trescientos schemas y varios gigas en la base de prueba.
Ahora cada recurso se apunta al ámbito que lo crea —la prueba o el módulo— y se suelta con
él, pase o falle la prueba.

Aquí se mira el servidor: qué schemas existen y qué conexiones siguen abiertas, antes y
después. Parte de las pruebas trabajan en este proceso; otras lanzan `pytest` sobre las
sondas de `tests/sondas_pg/` para ver lo que deja una corrida entera, incluida su red de
seguridad final.

Solo sobre PostgreSQL (`KONTROL_TEST_DB_URL`), salvo las dos que comprueban que SQLite
sigue igual.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pg_harness
import pytest
from conftest import make_engine
from sqlalchemy import text

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
solo_pg = pytest.mark.skipif("postgresql" not in PG_URL, reason="mide recursos de PostgreSQL (KONTROL_TEST_DB_URL)")
BACKEND = Path(__file__).resolve().parent.parent
RAIZ = BACKEND.parent.parent


# --------------------------------------------------------------------------- #
# Lo que hay en el servidor
# --------------------------------------------------------------------------- #
def _consultar(sql: str, **params):
    admin = pg_harness.motor_administrativo(PG_URL)
    try:
        with admin.connect() as conn:
            return conn.execute(text(sql), params).all()
    finally:
        admin.dispose()


def _schemas() -> set[str]:
    return {n for (n,) in _consultar("select nspname from pg_namespace where nspname ~ :p",
                                     p=pg_harness.PATRON_DE_SCHEMA.pattern)}


def _existe(schema: str) -> bool:
    return bool(_consultar("select 1 from pg_namespace where nspname = :n", n=schema))


def _conexiones(schema: str | None = None) -> int:
    """Conexiones del arnés abiertas en el servidor: las de un schema, o todas."""
    patron = pg_harness.PREFIJO_DE_APLICACION + (schema or "%")
    return _consultar("select count(*) from pg_stat_activity where application_name like :a", a=patron)[0][0]


def _existe_la_base(nombre: str) -> bool:
    return bool(_consultar("select 1 from pg_database where datname = :n", n=nombre))


def _correr(*sondas: str, sin_postgresql: bool = False) -> subprocess.CompletedProcess:
    """Lanza `pytest` sobre unas sondas en un proceso aparte, como una corrida más."""
    entorno = dict(os.environ)
    if sin_postgresql:
        entorno.pop("KONTROL_TEST_DB_URL", None)
    return subprocess.run(
        [sys.executable, "-m", "pytest", *(f"tests/sondas_pg/{s}" for s in sondas), "-p", "no:cacheprovider"],
        cwd=BACKEND, env=entorno, capture_output=True, text=True, timeout=300)


# --------------------------------------------------------------------------- #
# PG-LIFE-01/02/03 · al cerrar el ámbito: sin conexiones y sin schema
# --------------------------------------------------------------------------- #
@solo_pg
def test_pglife_01_al_cerrar_el_ambito_el_motor_no_deja_conexiones_en_el_servidor():
    cortadas = len(pg_harness.INFORME.conexiones_cortadas)
    ambito = pg_harness.abrir_ambito("PG-LIFE-01")
    try:
        motor = make_engine()
        schema = ambito.motores[-1][1]
        with motor.connect() as conn:
            conn.execute(text("select 1"))
        # La conexión volvió al pool: sigue abierta en el servidor mientras el motor viva.
        assert _conexiones(schema) == 1
    finally:
        pg_harness.cerrar_ambito(ambito)
    assert _conexiones(schema) == 0
    # Y se cerró por las buenas: liberando el motor, no cortando la conexión desde el servidor.
    assert len(pg_harness.INFORME.conexiones_cortadas) == cortadas


@solo_pg
def test_pglife_02_al_cerrar_el_ambito_el_schema_ya_no_existe():
    ambito = pg_harness.abrir_ambito("PG-LIFE-02")
    try:
        motor = make_engine()
        schema = ambito.motores[-1][1]
        with motor.begin() as conn:
            conn.execute(text("create table cosa (n int)"))
        assert pg_harness.PATRON_DE_SCHEMA.fullmatch(schema)
        assert _existe(schema)
    finally:
        pg_harness.cerrar_ambito(ambito)
    assert not _existe(schema)
    assert ambito.motores == []


@solo_pg
def test_pglife_03_las_conexiones_vuelven_a_la_linea_base():
    antes = _conexiones()
    ambito = pg_harness.abrir_ambito("PG-LIFE-03")
    try:
        motores = [make_engine() for _ in range(3)]
        abiertas = [m.connect() for m in motores]
        assert _conexiones() == antes + 3
        for conexion in abiertas:
            conexion.close()
    finally:
        pg_harness.cerrar_ambito(ambito)
    assert _conexiones() == antes


# --------------------------------------------------------------------------- #
# PG-LIFE-04/08 · repetir una corrida no acumula nada
# --------------------------------------------------------------------------- #
@solo_pg
@pytest.mark.parametrize("sonda", ["sonda_pasa.py", "sonda_modulo.py"])
def test_pglife_04_tres_corridas_seguidas_no_dejan_schemas_ni_conexiones(sonda):
    schemas, conexiones = _schemas(), _conexiones()
    for vuelta in (1, 2, 3):
        hecho = _correr(sonda)
        assert hecho.returncode == 0, hecho.stdout
        assert "se cortaron" not in hecho.stdout and "NO SE PUDO SOLTAR" not in hecho.stdout
        assert _schemas() == schemas, f"vuelta {vuelta}: quedaron schemas huérfanos"
        assert _conexiones() == conexiones, f"vuelta {vuelta}: quedaron conexiones"


@solo_pg
def test_pglife_08_el_schema_de_un_modulo_se_suelta_al_acabar_el_modulo_no_al_acabar_la_corrida():
    schemas = _schemas()
    hecho = _correr("sonda_modulo.py", "sonda_despues.py")
    assert hecho.returncode == 0, hecho.stdout
    assert "3 passed" in hecho.stdout
    assert _schemas() == schemas


# --------------------------------------------------------------------------- #
# PG-LIFE-05 · la limpieza no depende de que la prueba pase
# --------------------------------------------------------------------------- #
@solo_pg
def test_pglife_05_una_prueba_que_falla_y_una_fixture_que_revienta_se_limpian_igual():
    schemas, conexiones = _schemas(), _conexiones()
    hecho = _correr("sonda_falla.py")
    # La sonda falla de verdad: el arnés no convierte un fallo en un verde.
    assert hecho.returncode == 1, hecho.stdout
    assert "1 failed" in hecho.stdout and "1 passed" in hecho.stdout and "1 error" in hecho.stdout
    assert _schemas() == schemas
    assert _conexiones() == conexiones
    assert "NO SE PUDO SOLTAR" not in hecho.stdout


# --------------------------------------------------------------------------- #
# PG-LIFE-09 · lo creado fuera de toda fixture lo suelta la red de seguridad
# --------------------------------------------------------------------------- #
@solo_pg
def test_pglife_09_un_motor_creado_al_importar_el_modulo_se_suelta_al_acabar_la_sesion():
    schemas = _schemas()
    hecho = _correr("sonda_fuera_de_ambito.py")
    assert hecho.returncode == 0, hecho.stdout
    assert _schemas() == schemas


@solo_pg
def test_pglife_09b_la_red_de_seguridad_suelta_lo_que_no_tiene_ambito():
    pila = list(pg_harness._PILA)
    pg_harness._PILA.clear()
    try:
        motor = make_engine()
        url, schema, registrado = pg_harness._SESION.motores[-1]
        assert registrado is motor and _existe(schema)
        pg_harness._liberar(pg_harness._SESION)
    finally:
        pg_harness._PILA.extend(pila)
    assert not _existe(schema)


# --------------------------------------------------------------------------- #
# PG-LIFE-10 · sin una base inequívocamente de prueba, ni se crea ni se destruye
# --------------------------------------------------------------------------- #
@solo_pg
def test_pglife_10_en_un_entorno_que_no_es_de_prueba_no_se_crea_ningun_schema(monkeypatch):
    schemas = _schemas()
    monkeypatch.setenv("KONTROL_ENVIRONMENT", "prod")
    with pytest.raises(pg_harness.BaseNoEsDePrueba):
        make_engine()
    monkeypatch.undo()
    assert _schemas() == schemas


@solo_pg
def test_pglife_10b_en_un_entorno_que_no_es_de_prueba_no_se_elimina_nada(monkeypatch):
    ambito = pg_harness.abrir_ambito("PG-LIFE-10b")
    try:
        motor = make_engine()
        url, schema, _ = ambito.motores[-1]
        monkeypatch.setenv("KONTROL_ENVIRONMENT", "prod")
        with pytest.raises(pg_harness.BaseNoEsDePrueba):
            pg_harness.soltar_schema(url, schema, motor)
        monkeypatch.undo()
        assert _existe(schema), "se eliminó un schema sin poder identificar la base como de prueba"
    finally:
        pg_harness.cerrar_ambito(ambito)
    assert not _existe(schema)


# --------------------------------------------------------------------------- #
# PG-LIFE-11 · SQLite sigue igual
# --------------------------------------------------------------------------- #
def test_pglife_11_en_sqlite_make_engine_devuelve_el_motor_en_memoria_y_no_apunta_nada(monkeypatch):
    monkeypatch.delenv("KONTROL_TEST_DB_URL", raising=False)
    ambito = pg_harness.abrir_ambito("PG-LIFE-11")
    try:
        motor = make_engine()
        assert motor.dialect.name == "sqlite"
        assert ambito.motores == [] and ambito.bases == []
    finally:
        pg_harness.cerrar_ambito(ambito)


def test_pglife_11b_las_sondas_pasan_igual_sobre_sqlite():
    hecho = _correr("sonda_modulo.py", sin_postgresql=True)
    assert hecho.returncode == 0, hecho.stdout
    assert "2 passed" in hecho.stdout


# --------------------------------------------------------------------------- #
# PG-LIFE-12 · el informe de residuos
# --------------------------------------------------------------------------- #
@solo_pg
def test_pglife_12_el_informe_de_residuos_dice_lo_que_hay_en_la_base():
    hecho = subprocess.run([sys.executable, str(RAIZ / "qa" / "pg-test-residuos.py"), "--json"],
                           capture_output=True, text=True, timeout=120)
    assert hecho.returncode == 0, hecho.stdout + hecho.stderr
    informe = json.loads(hecho.stdout)
    assert {"base", "tamano", "schemas_temporales", "con_marca", "conexiones", "conexiones_del_arnes",
            "libre_en_el_volumen_mb"} <= set(informe)
    # Esta misma prueba corre dentro de un módulo sin motor propio: el informe y el servidor coinciden.
    assert set(informe["schemas_temporales"]) == _schemas()
    assert informe["conexiones_del_arnes"] == _conexiones()


# --------------------------------------------------------------------------- #
# PG-LIFE-13 · una conexión que la prueba dejó abierta no deja el schema huérfano
# --------------------------------------------------------------------------- #
@solo_pg
def test_pglife_13_una_conexion_olvidada_se_cuenta_se_corta_y_el_schema_se_suelta():
    schemas = _schemas()
    hecho = _correr("sonda_deja_conexion.py")
    assert hecho.returncode == 0, hecho.stdout
    assert "conexiones que quedaron abiertas y se cortaron: 1" in hecho.stdout
    assert _schemas() == schemas


@solo_pg
def test_pglife_13b_la_conexion_olvidada_ya_no_esta_en_el_servidor():
    ambito = pg_harness.abrir_ambito("PG-LIFE-13b")
    motor = make_engine()
    schema = ambito.motores[-1][1]
    olvidada = motor.connect()
    olvidada.execute(text("create table cosa (n int)"))
    cortadas = len(pg_harness.INFORME.conexiones_cortadas)
    pg_harness.cerrar_ambito(ambito)
    assert not _existe(schema)
    assert _conexiones(schema) == 0
    assert pg_harness.INFORME.conexiones_cortadas[cortadas:] == [("PG-LIFE-13b", schema, 1)]
    # El informe de esta corrida no debe cargar con una conexión que esta prueba dejó a propósito.
    del pg_harness.INFORME.conexiones_cortadas[cortadas:]
    olvidada.invalidate()


# --------------------------------------------------------------------------- #
# PG-LIFE-14 · solo se elimina lo que el arnés creó
# --------------------------------------------------------------------------- #
@solo_pg
@pytest.mark.parametrize("nombre", ["public", "pg_catalog", "t_0123456789AB", "t_corto"])
def test_pglife_14_un_nombre_que_no_es_del_arnes_no_se_elimina(nombre):
    with pytest.raises(pg_harness.ResiduoDePrueba):
        pg_harness.soltar_schema(PG_URL, nombre, None)
    assert _existe("public") and _existe("pg_catalog")


@solo_pg
def test_pglife_14b_un_schema_sin_la_marca_del_arnes_no_se_elimina():
    ajeno = "t_aaaaaaaaaaaa"
    admin = pg_harness.motor_administrativo(PG_URL)
    try:
        with admin.connect() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{ajeno}"'))
            with pytest.raises(pg_harness.ResiduoDePrueba, match="marca"):
                pg_harness.soltar_schema(PG_URL, ajeno, None)
            assert _existe(ajeno)
            conn.execute(text(f'DROP SCHEMA "{ajeno}"'))
    finally:
        admin.dispose()


@solo_pg
def test_pglife_14c_un_schema_que_este_proceso_no_apunto_sobrevive_al_cierre_de_un_ambito():
    de_otro = "t_bbbbbbbbbbbb"
    admin = pg_harness.motor_administrativo(PG_URL)
    try:
        with admin.connect() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{de_otro}"'))
            conn.execute(text(f"COMMENT ON SCHEMA \"{de_otro}\" IS '{pg_harness.PREFIJO_DE_MARCA}pid=0 de otra corrida'"))
            ambito = pg_harness.abrir_ambito("PG-LIFE-14c")
            make_engine()
            pg_harness.cerrar_ambito(ambito)
            assert _existe(de_otro), "se eliminó un schema que no era de este ámbito"
            conn.execute(text(f'DROP SCHEMA "{de_otro}"'))
    finally:
        admin.dispose()


# --------------------------------------------------------------------------- #
# PG-LIFE-15 · las bases enteras de las pruebas de migración
# --------------------------------------------------------------------------- #
@solo_pg
def test_pglife_15_una_base_temporal_registrada_se_elimina_al_cerrar_su_ambito():
    hecho = _correr("sonda_base.py")
    assert hecho.returncode == 0, hecho.stdout
    assert not _existe_la_base("kontrol_test_sonda_base")


@solo_pg
@pytest.mark.parametrize("protegida", ["postgres", "template1", "la base de prueba", "Con Mayúsculas; DROP"])
def test_pglife_15b_no_se_elimina_una_base_del_sistema_ni_la_de_prueba(protegida):
    nombre = pg_harness.make_url(PG_URL).database if protegida == "la base de prueba" else protegida
    with pytest.raises(pg_harness.ResiduoDePrueba):
        pg_harness.soltar_base(nombre)
    assert _existe_la_base("postgres") and _existe_la_base(pg_harness.make_url(PG_URL).database)


@solo_pg
def test_pglife_15c_un_recurso_que_no_se_deja_soltar_es_un_error_con_nombre():
    ambito = pg_harness.abrir_ambito("PG-LIFE-15c")
    pg_harness.registrar_base("postgres")
    residuos = len(pg_harness.INFORME.residuos)
    with pytest.raises(pg_harness.ResiduoDePrueba, match="postgres"):
        pg_harness.cerrar_ambito(ambito)
    assert len(pg_harness.INFORME.residuos) == residuos + 1
    del pg_harness.INFORME.residuos[residuos:]
    assert _existe_la_base("postgres")
