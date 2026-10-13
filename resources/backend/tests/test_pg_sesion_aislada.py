"""PGS · Una sesión con la base limpia por prueba, sin un schema por prueba (SPEC054 ·
TEST-PG-UN-SCHEMA-POR-PRUEBA; FR-PGS-001…011).

Doce suites creaban en PostgreSQL un schema entero (203 tablas, 638 índices, ≈1,1 s de DDL) por
cada prueba. `sesion_de_prueba` (conftest) crea el schema una vez por módulo —PGLIFE lo apunta al
módulo— y da a cada prueba una conexión propia dentro de una transacción externa: los `commit`
del código, de la prueba o del producto, solo sueltan un SAVEPOINT, y al terminar la prueba todo
se deshace. En SQLite sigue habiendo una base en memoria nueva por prueba.

Aquí, dentro de un mismo módulo: A escribe, confirma, actualiza y borra; B y C deben partir de
cero. Las sondas de `tests/sondas_pg/sonda_sesion_*.py` repiten la prueba en procesos aparte: en
serie, en paralelo, en orden inverso, de una en una y con una prueba que falla.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pg_harness
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.modules.organization.models import Installation
from app.modules.setup.api import SetupRequest, initialize
from tests.test_system_access import PASSWORD

BACKEND = Path(__file__).resolve().parent.parent
PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
PG = PG_URL.startswith("postgresql")
SUITES = ["test_services", "test_approvals", "test_treasury", "test_fiscal", "test_inventory", "test_sales", "test_maestros",
          "test_homologation", "test_purchasing", "test_reporting", "test_licensing_central", "test_regulatory"]
VISTO: dict[str, object] = {}


def _instalaciones(db: Session) -> set[str]:
    return {i.id for i in db.execute(select(Installation)).scalars()}


def _schema(db: Session) -> str | None:
    return db.execute(text("select current_schema()")).scalar_one() if PG else None


def _marcador(db: Session, nombre: str) -> None:
    db.add(Installation(id=nombre, installation_uuid=f"uuid-{nombre}", state="ACTIVE"))
    db.commit()


# ---------------------------------------------------------------- PGS-02/03/04/05 · mismo módulo, nada pasa de una prueba a otra
def test_pgs_02_a_escribe_confirma_y_actualiza(sesion_de_prueba):
    db = sesion_de_prueba
    assert _instalaciones(db) == set()
    _marcador(db, "marcador-a")
    _marcador(db, "marcador-a2")
    db.execute(text("update installations set state = 'PENDING' where id = 'marcador-a'"))
    db.commit()
    db.rollback()  # un rollback del código tampoco deshace lo ya «confirmado» dentro del ámbito
    assert _instalaciones(db) == {"marcador-a", "marcador-a2"}
    db.expire_all()
    assert db.get(Installation, "marcador-a").state == "PENDING"
    VISTO.update(schema_a=_schema(db), motor_a=id(db.get_bind().engine), creados_a=pg_harness.INFORME.schemas_creados)


def test_pgs_03_b_no_ve_las_filas_ni_la_actualizacion_de_a_y_borra_lo_suyo(sesion_de_prueba):
    db = sesion_de_prueba
    assert _instalaciones(db) == set(), "las filas que A confirmó siguen ahí: el aislamiento no se sostiene"
    _marcador(db, "marcador-b")
    db.delete(db.get(Installation, "marcador-b"))
    db.commit()
    assert _instalaciones(db) == set()
    VISTO.update(schema_b=_schema(db), motor_b=id(db.get_bind().engine))


def test_pgs_04_el_commit_del_producto_queda_dentro_del_ambito(sesion_de_prueba):
    db = sesion_de_prueba
    assert _instalaciones(db) == set()
    initialize(db, SetupRequest(tenant_code="DEMO", tenant_name="Demo", company_code="D1", company_legal_name="Demo C.A.",
                                company_rif="J-12345678-9", admin_username="admin", admin_password=PASSWORD))  # hace commit por dentro
    assert len(_instalaciones(db)) == 1


def test_pgs_05_c_parte_de_cero_tras_el_borrado_y_tras_el_producto(sesion_de_prueba):
    assert _instalaciones(sesion_de_prueba) == set()


# ---------------------------------------------------------------- PGS-06 · una segunda sesión del mismo ámbito ve lo del ámbito, y nada más
def test_pgs_06_una_segunda_sesion_del_ambito_ve_lo_confirmado_en_el_ambito(sesion_de_prueba):
    db = sesion_de_prueba
    _marcador(db, "marcador-d")
    otra = Session(bind=db.get_bind(), join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        assert _instalaciones(otra) == {"marcador-d"}
    finally:
        otra.close()


def test_pgs_06b_y_la_prueba_siguiente_tampoco_ve_lo_de_la_segunda_sesion(sesion_de_prueba):
    assert _instalaciones(sesion_de_prueba) == set()


# ---------------------------------------------------------------- PGS-08 · secuencias: no hay ninguna que aislar
def test_pgs_08_el_schema_no_tiene_secuencias_ni_identidades(sesion_de_prueba):
    db = sesion_de_prueba
    if PG:
        assert db.execute(text("select count(*) from pg_sequences where schemaname = current_schema()")).scalar_one() == 0
    else:
        assert db.execute(text("select count(*) from sqlite_master where name = 'sqlite_sequence'")).scalar_one() == 0


# ---------------------------------------------------------------- PGS-09 / PGS-12 · PostgreSQL: un schema por módulo; SQLite: base nueva por prueba
def test_pgs_09_postgresql_un_schema_por_modulo_y_sqlite_una_base_por_prueba(sesion_de_prueba):
    db = sesion_de_prueba
    motor = id(db.get_bind().engine)
    if PG:
        assert VISTO["schema_a"] == VISTO["schema_b"] == _schema(db)
        assert re.fullmatch(pg_harness.PATRON_DE_SCHEMA.pattern, str(_schema(db)))
        assert VISTO["motor_a"] == VISTO["motor_b"] == motor
        assert pg_harness.INFORME.schemas_creados == VISTO["creados_a"], "una prueba de este módulo creó otro schema"
    else:
        assert len({VISTO["motor_a"], VISTO["motor_b"], motor}) == 3
        assert db.get_bind().engine.url.database in (None, ":memory:")


# ---------------------------------------------------------------- sondas en procesos aparte
def _entorno(informe: Path) -> dict[str, str]:
    return {**os.environ, "KONTROL_SONDA_INFORME": str(informe), "PYTHONDONTWRITEBYTECODE": "1"}


def _orden(*objetivos: str) -> list[str]:
    return [sys.executable, "-m", "pytest", *(f"tests/sondas_pg/{o}" for o in objetivos), "-p", "no:cacheprovider", "-q"]


def _correr(informe: Path, *objetivos: str) -> subprocess.CompletedProcess:
    return subprocess.run(_orden(*objetivos), cwd=BACKEND, env=_entorno(informe), capture_output=True, text=True, timeout=600)


def _registros(informe: Path) -> list[dict]:
    return [json.loads(linea) for linea in informe.read_text(encoding="utf-8").splitlines() if linea.strip()]


def _schemas_del_proceso(pid: int) -> int:
    """Schemas del arnés que siguen en el servidor con la marca de ese proceso."""
    if not PG:
        return 0
    admin = pg_harness.motor_administrativo(PG_URL)
    try:
        with admin.connect() as conn:
            return conn.execute(text("select count(*) from pg_namespace where obj_description(oid, 'pg_namespace') like :m"),
                                {"m": f"{pg_harness.PREFIJO_DE_MARCA}pid={pid} %"}).scalar_one()
    finally:
        admin.dispose()


def _comprobar_sonda(registros: list[dict], modulo: str) -> list[dict]:
    propios = [r for r in registros if r["modulo"] == modulo]
    assert [r["prueba"] for r in propios] == [1, 2]
    assert all(r["instalaciones_al_empezar"] == [] for r in propios), "una prueba arrancó viendo filas de otra"
    assert all(r["conexiones_cortadas"] == 0 for r in propios)
    if PG:
        assert propios[0]["schema"] == propios[1]["schema"] and propios[0]["motor"] == propios[1]["motor"]
        assert propios[0]["schemas_creados"] == propios[1]["schemas_creados"]
    else:
        assert propios[0]["motor"] != propios[1]["motor"]
    return propios


def test_pgs_11_una_sonda_entera_no_deja_schema_y_cada_prueba_parte_de_cero(tmp_path):
    hecho = _correr(tmp_path / "a.jsonl", "sonda_sesion_a.py")
    assert hecho.returncode == 0, hecho.stdout
    propios = _comprobar_sonda(_registros(tmp_path / "a.jsonl"), "sonda_sesion_a")
    assert _schemas_del_proceso(propios[0]["pid"]) == 0


def test_pgs_10_cuando_una_prueba_falla_el_schema_del_modulo_se_suelta_igual(tmp_path):
    hecho = _correr(tmp_path / "f.jsonl", "sonda_sesion_falla.py")
    assert hecho.returncode != 0 and "fallo deliberado de la sonda" in hecho.stdout
    propios = _comprobar_sonda(_registros(tmp_path / "f.jsonl"), "sonda_sesion_falla")
    assert "NO SE PUDO SOLTAR" not in hecho.stdout and "residuos" not in hecho.stdout.lower()
    assert _schemas_del_proceso(propios[0]["pid"]) == 0


def test_pgs_07_dos_modulos_del_mismo_proceso_no_comparten_schema(tmp_path):
    hecho = _correr(tmp_path / "ab.jsonl", "sonda_sesion_a.py", "sonda_sesion_b.py")
    assert hecho.returncode == 0, hecho.stdout
    registros = _registros(tmp_path / "ab.jsonl")
    a, b = _comprobar_sonda(registros, "sonda_sesion_a"), _comprobar_sonda(registros, "sonda_sesion_b")
    if PG:
        assert a[0]["schema"] != b[0]["schema"]
        assert b[0]["schemas_creados"] == a[0]["schemas_creados"] + 1  # exactamente un schema nuevo por módulo
    assert _schemas_del_proceso(a[0]["pid"]) == 0


def test_pgs_23_el_orden_inverso_y_una_prueba_sola_dan_lo_mismo(tmp_path):
    inverso = _correr(tmp_path / "inv.jsonl", "sonda_sesion_a.py::test_2_parte_de_cero", "sonda_sesion_a.py::test_1_escribe_y_confirma")
    assert inverso.returncode == 0, inverso.stdout
    registros = _registros(tmp_path / "inv.jsonl")
    assert [r["prueba"] for r in registros] == [2, 1] and all(r["instalaciones_al_empezar"] == [] for r in registros)
    sola = _correr(tmp_path / "sola.jsonl", "sonda_sesion_a.py::test_2_parte_de_cero")
    assert sola.returncode == 0, sola.stdout
    assert [r["prueba"] for r in _registros(tmp_path / "sola.jsonl")] == [2]


def test_pgs_26_dos_procesos_a_la_vez_trabajan_en_schemas_distintos(tmp_path):
    pa = subprocess.Popen(_orden("sonda_sesion_a.py"), cwd=BACKEND, env=_entorno(tmp_path / "a.jsonl"), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    pb = subprocess.Popen(_orden("sonda_sesion_b.py"), cwd=BACKEND, env=_entorno(tmp_path / "b.jsonl"), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    salida_a, _ = pa.communicate(timeout=600)
    salida_b, _ = pb.communicate(timeout=600)
    assert pa.returncode == 0 and pb.returncode == 0, salida_a + salida_b
    a = _comprobar_sonda(_registros(tmp_path / "a.jsonl"), "sonda_sesion_a")
    b = _comprobar_sonda(_registros(tmp_path / "b.jsonl"), "sonda_sesion_b")
    assert a[0]["pid"] != b[0]["pid"]
    if PG:
        assert a[0]["schema"] != b[0]["schema"]
    assert _schemas_del_proceso(a[0]["pid"]) == 0 and _schemas_del_proceso(b[0]["pid"]) == 0


# ---------------------------------------------------------------- invariantes estáticos
def test_pgs_27_las_doce_suites_usan_la_sesion_del_arnes_y_ninguna_crea_un_schema_por_prueba():
    for suite in SUITES:
        fuente = (BACKEND / "tests" / f"{suite}.py").read_text(encoding="utf-8")
        assert "def db_session(sesion_de_prueba)" in fuente, suite
        assert "make_engine(" not in fuente and "create_all(" not in fuente, suite
        assert "pytest.mark.skip" not in fuente and "pytest.skip(" not in fuente and "xfail" not in fuente, suite


def test_pgs_28_nada_de_esto_se_sostiene_reordenando_pruebas_ni_tocando_el_producto():
    conftest = (BACKEND / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert "pytest_collection_modifyitems" not in conftest
    assert "scope=\"session\"" not in conftest  # el schema compartido es de módulo, nunca de sesión
    producto = "\n".join(p.read_text(encoding="utf-8") for p in (BACKEND / "app").rglob("*.py"))
    assert "join_transaction_mode" not in producto and "create_savepoint" not in producto
