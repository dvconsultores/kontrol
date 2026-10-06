"""E2ECICLO · La base de una corrida E2E nace, se migra, se siembra y desaparece (FR-054-E2EDB-001..015).

Sobre PostgreSQL de verdad: el servidor es el de `KONTROL_TEST_DB_URL` y el rol, el mismo. Las
bases que se crean aquí son de corrida —`kontrol_e2e_test_<run>`— y cada prueba elimina las
suyas; la base de las pruebas de backend no se toca, y se comprueba.
"""

from __future__ import annotations

import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "qa"))

import e2e_base as b  # noqa: E402
import e2e_nombres as n  # noqa: E402

URL_DE_PRUEBA = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif(not URL_DE_PRUEBA.startswith("postgresql"),
                                reason="el ciclo de vida de una base solo existe en PostgreSQL")


def _mantenimiento() -> str:
    return make_url(URL_DE_PRUEBA).set(database="postgres").render_as_string(hide_password=False)


@pytest.fixture(scope="module")
def servidor() -> b.Servidor:
    return b.Servidor(admin_url=_mantenimiento(), duena_url=_mantenimiento())


@pytest.fixture(scope="module")
def entorno() -> dict[str, str]:
    """El entorno con el que decide la compuerta: QA, y el servidor de pruebas como único permitido."""
    return {"KONTROL_ENVIRONMENT": "local", "KONTROL_TEST_DB_URL": URL_DE_PRUEBA,
            "KONTROL_E2E_PG_HOSTS": (make_url(URL_DE_PRUEBA).host or "localhost").replace("127.0.0.1", "localhost")}


def _nuevo_run() -> str:
    return n.nuevo_run_id(datetime.now(UTC), os.getpid(), secrets.token_hex(3))


def _existe(servidor: b.Servidor, nombre: str) -> bool:
    admin = b.motor_administrativo(servidor)
    try:
        with admin.connect() as c:
            return bool(c.execute(text("select count(*) from pg_database where datname = :n"), {"n": nombre}).scalar())
    finally:
        admin.dispose()


def _sql(servidor: b.Servidor, sentencia: str) -> None:
    admin = b.motor_administrativo(servidor)
    try:
        with admin.connect() as c:
            c.execute(text(sentencia))
    finally:
        admin.dispose()


def _retirar(servidor: b.Servidor, nombre: str) -> None:
    """Limpieza de la propia prueba: solo nombres de corrida que esta prueba acaba de fabricar."""
    assert n.es_base_e2e(nombre)
    _sql(servidor, f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)')


@pytest.fixture
def bases(servidor):
    """Las bases que crea una prueba. Al terminar no queda ninguna, pase o falle."""
    creadas: list[str] = []
    yield creadas
    for nombre in creadas:
        _retirar(servidor, nombre)
    assert not [nombre for nombre in creadas if _existe(servidor, nombre)]


def _crear(servidor, entorno, bases, **kwargs) -> tuple[str, str]:
    run = _nuevo_run()
    bases.append(n.nombre_de_base(run))
    return run, b.crear_base(servidor, run, entorno=entorno, **kwargs)


def _entorno_de_procesos(estado: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in ("KONTROL_DB_URL", "KONTROL_TEST_DB_URL")}
    env.update({
        "KONTROL_SECRET_KEY": "qa-secret-key-0123456789abcdef0123456789abcdef", "KONTROL_ENVIRONMENT": "local",
        "KONTROL_LOG_JSON": "false", "KONTROL_INSTALLATION_VOLUME_PATH": str(estado / "license"),
        "KONTROL_STORAGE_PATH": str(estado / "storage"), "KONTROL_BACKUP_PATH": str(estado / "backups"),
        "KONTROL_QA_IDS_FILE": str(estado / "n6-ids.json"),
    })
    return env


@pytest.fixture(scope="module")
def sembrada(servidor, entorno):
    """Una base de corrida creada, migrada y sembrada una vez para las pruebas que solo leen."""
    run = _nuevo_run()
    nombre = b.crear_base(servidor, run, entorno=entorno)
    # Ruta corta: la clave de instalación se guarda con su ruta en una columna de 120 caracteres.
    estado = Path(tempfile.mkdtemp(prefix="ke2e-", dir="/tmp"))
    try:
        url = servidor.url_de(nombre)
        env = _entorno_de_procesos(estado)
        migracion = b.migrar(url, env=env, registro=estado / "migracion.log")
        siembra = b.sembrar(url, env=env, registro=estado / "siembra.log")
        yield {"run": run, "nombre": nombre, "url": url, "env": env, "estado": estado,
               "migracion": migracion, "siembra": siembra}
    finally:
        _retirar(servidor, nombre)
        shutil.rmtree(estado, ignore_errors=True)


# ---------------------------------------------------------------- DB-05 · crear
def test_e2eciclo_01_dos_corridas_dos_bases(servidor, entorno, bases):
    run_a, base_a = _crear(servidor, entorno, bases)
    run_b, base_b = _crear(servidor, entorno, bases)
    assert run_a != run_b and base_a != base_b
    assert base_a == "kontrol_e2e_test_" + run_a and base_b == "kontrol_e2e_test_" + run_b
    assert _existe(servidor, base_a) and _existe(servidor, base_b)


def test_e2eciclo_02_la_base_nace_vacia_marcada_y_en_utc(servidor, entorno, bases):
    run, nombre = _crear(servidor, entorno, bases)
    admin = b.motor_administrativo(servidor)
    try:
        with admin.connect() as c:
            comentario = c.execute(text(
                "select shobj_description(oid, 'pg_database') from pg_database where datname = :n"),
                {"n": nombre}).scalar_one()
    finally:
        admin.dispose()
    marca = n.leer_marca(comentario)
    assert marca is not None and marca["run"] == run and marca["pid"] == str(os.getpid())
    motor = create_engine(servidor.url_de(nombre), poolclass=NullPool)
    try:
        with motor.connect() as c:
            assert c.execute(text("show timezone")).scalar_one() == "UTC"
            assert c.execute(text("select current_database()")).scalar_one() == nombre
            assert c.execute(text("select count(*) from pg_tables where schemaname = 'public'")).scalar_one() == 0
            assert c.execute(text("select application_name from pg_stat_activity where pid = pg_backend_pid()")
                             ).scalar_one() == "kontrol-e2e:" + run
    finally:
        motor.dispose()


def test_e2eciclo_03_crear_una_base_que_ya_existe_falla_y_no_la_toca(servidor, entorno, bases):
    run, nombre = _crear(servidor, entorno, bases)
    motor = create_engine(servidor.url_de(nombre), poolclass=NullPool, isolation_level="AUTOCOMMIT")
    try:
        with motor.connect() as c:
            c.execute(text("create table testigo (x int)"))
    finally:
        motor.dispose()
    with pytest.raises(b.CicloDeBaseRoto, match="ya existe"):
        b.crear_base(servidor, run, entorno=entorno)
    motor = create_engine(servidor.url_de(nombre), poolclass=NullPool)
    try:
        with motor.connect() as c:
            assert c.execute(text("select to_regclass('public.testigo') is not null")).scalar_one() is True
    finally:
        motor.dispose()


# ---------------------------------------------------------------- DB-06 · migrar
def test_e2eciclo_04_la_base_migrada_esta_en_la_unica_cabeza(sembrada):
    assert sembrada["migracion"]["cabezas"] == 1
    assert sembrada["migracion"]["actual"] == sembrada["migracion"]["esperada"] == b.cabezas()[0]
    motor = create_engine(sembrada["url"], poolclass=NullPool)
    try:
        with motor.connect() as c:
            assert c.execute(text("select version_num from alembic_version")).scalars().all() == b.cabezas()
            assert c.execute(text("select count(*) from pg_tables where schemaname = 'public'")).scalar_one() > 100
    finally:
        motor.dispose()


def test_e2eciclo_05_si_la_base_no_queda_en_la_cabeza_la_migracion_falla(sembrada, monkeypatch):
    monkeypatch.setattr(b, "cabezas", lambda: ["0000_no_existe"])
    with pytest.raises(b.CicloDeBaseRoto, match="la cabeza es"):
        b.migrar(sembrada["url"], env=sembrada["env"], registro=sembrada["estado"] / "migracion-2.log")


def test_e2eciclo_06_con_dos_cabezas_no_se_migra(sembrada, monkeypatch):
    monkeypatch.setattr(b, "cabezas", lambda: ["a", "b"])
    monkeypatch.setattr(b, "_ejecutar", lambda *a, **k: pytest.fail("no debió ejecutarse alembic"))
    with pytest.raises(b.CicloDeBaseRoto, match="2 cabezas"):
        b.migrar(sembrada["url"], env=sembrada["env"], registro=sembrada["estado"] / "migracion-3.log")


def test_e2eciclo_07_una_migracion_que_falla_se_dice(servidor, entorno, bases, tmp_path):
    _, nombre = _crear(servidor, entorno, bases)
    env = {**_entorno_de_procesos(tmp_path), "KONTROL_SECRET_KEY": ""}
    with pytest.raises(b.CicloDeBaseRoto, match="alembic upgrade head terminó con código"):
        b.migrar(servidor.url_de(nombre), env=env, registro=tmp_path / "migracion.log")


# ---------------------------------------------------------------- DB-07 · sembrar
def test_e2eciclo_08_la_siembra_deja_la_linea_base_exacta(sembrada):
    assert sembrada["siembra"]["linea_base"] == b.LINEA_BASE
    assert b.linea_base(sembrada["url"]) == b.LINEA_BASE
    assert sembrada["siembra"]["version"] == b.version_de_siembra() and len(b.version_de_siembra()) == 16


def test_e2eciclo_09_una_base_ya_sembrada_no_se_siembra_otra_vez(sembrada, monkeypatch):
    monkeypatch.setattr(b, "_ejecutar", lambda *a, **k: pytest.fail("no debió ejecutarse la siembra"))
    with pytest.raises(b.CicloDeBaseRoto, match="dos veces"):
        b.sembrar(sembrada["url"], env=sembrada["env"], registro=sembrada["estado"] / "siembra-2.log")
    assert b.linea_base(sembrada["url"]) == b.LINEA_BASE


def test_e2eciclo_10_una_siembra_que_no_deja_la_linea_base_se_dice(servidor, entorno, bases, sembrada, monkeypatch):
    _, nombre = _crear(servidor, entorno, bases)
    url = servidor.url_de(nombre)
    b.migrar(url, env=sembrada["env"], registro=sembrada["estado"] / "migracion-4.log")
    monkeypatch.setattr(b, "_ejecutar", lambda *a, **k: 0)  # una «siembra» que no escribe nada
    with pytest.raises(b.CicloDeBaseRoto, match="línea base"):
        b.sembrar(url, env=sembrada["env"], registro=sembrada["estado"] / "siembra-3.log")


# ---------------------------------------------------------------- DB-21 · eliminar
def test_e2eciclo_11_eliminar_dos_veces_la_segunda_no_hace_nada(servidor, entorno, bases):
    _, nombre = _crear(servidor, entorno, bases)
    assert b.soltar_base(servidor, nombre, entorno=entorno) == {"estado": "ELIMINADA", "cortadas": 0}
    assert not _existe(servidor, nombre)
    assert b.soltar_base(servidor, nombre, entorno=entorno) == {"estado": "AUSENTE", "cortadas": 0}


def test_e2eciclo_12_si_alguien_sigue_conectado_se_cortan_solo_las_sesiones_de_esa_base(servidor, entorno, bases):
    _, nombre = _crear(servidor, entorno, bases)
    _, vecina = _crear(servidor, entorno, bases)
    rezagada = create_engine(servidor.url_de(nombre), poolclass=NullPool).connect()
    testigo = create_engine(servidor.url_de(vecina), poolclass=NullPool).connect()
    try:
        assert b.conexiones(servidor, nombre) == 1
        assert b.soltar_base(servidor, nombre, entorno=entorno, espera=0.5) == {"estado": "ELIMINADA", "cortadas": 1}
        assert not _existe(servidor, nombre)
        # La sesión de la base vecina sigue viva: no se cortó nada fuera de la base eliminada.
        assert testigo.execute(text("select current_database()")).scalar_one() == vecina
        assert b.conexiones(servidor, vecina) == 1
    finally:
        testigo.close()
        rezagada.invalidate()


def test_e2eciclo_13_la_base_de_las_pruebas_de_backend_no_se_elimina(servidor, entorno):
    de_prueba = make_url(URL_DE_PRUEBA).database
    with pytest.raises(b.BaseNoEsE2E):
        b.soltar_base(servidor, de_prueba, entorno=entorno)
    assert _existe(servidor, de_prueba)


# ---------------------------------------------------------------- DB-15 · marca
def test_e2eciclo_14_una_base_con_nombre_de_corrida_pero_sin_marca_no_se_elimina(servidor, entorno, bases):
    nombre = n.nombre_de_base(_nuevo_run())
    bases.append(nombre)
    _sql(servidor, f'CREATE DATABASE "{nombre}"')
    with pytest.raises(b.BaseNoEsE2E, match="marca"):
        b.soltar_base(servidor, nombre, entorno=entorno)
    assert _existe(servidor, nombre)
    assert [x.estado for x in b.listar_bases(servidor) if x.nombre == nombre] == ["SIN_MARCA"]
    assert [(x.nombre, hecho) for x, hecho in b.purgar(servidor, confirmar=True, solo=nombre, entorno=entorno)
            ] == [(nombre, "CONSERVADA")]
    assert _existe(servidor, nombre)


def test_e2eciclo_15_la_marca_de_otra_corrida_no_vale(servidor, entorno, bases):
    nombre = n.nombre_de_base(_nuevo_run())
    bases.append(nombre)
    ajena = n.marca(_nuevo_run(), 1, "h", datetime.now(UTC))
    _sql(servidor, f'CREATE DATABASE "{nombre}"')
    _sql(servidor, f"COMMENT ON DATABASE \"{nombre}\" IS '{ajena}'")
    with pytest.raises(b.BaseNoEsE2E, match="marca"):
        b.soltar_base(servidor, nombre, entorno=entorno)
    assert _existe(servidor, nombre)


# ---------------------------------------------------------------- DB-14 · huérfanas
def _pid_muerto() -> int:
    proceso = subprocess.Popen([sys.executable, "-c", "pass"])
    proceso.wait()
    return proceso.pid


def test_e2eciclo_16_la_base_de_un_lanzador_muerto_es_huerfana_y_la_de_uno_vivo_no(servidor, entorno, bases):
    _, viva = _crear(servidor, entorno, bases)
    _, huerfana = _crear(servidor, entorno, bases, pid=_pid_muerto())
    estados = {x.nombre: x.estado for x in b.listar_bases(servidor)}
    assert estados[viva] == "VIVA" and estados[huerfana] == "HUERFANA"


def test_e2eciclo_17_un_numero_de_proceso_reciclado_no_hace_viva_una_base(servidor, entorno, bases):
    # La base «se creó» antes de que arrancara este proceso: quien tiene hoy ese número no es su lanzador.
    ayer = datetime.now(UTC) - timedelta(days=1)
    _, nombre = _crear(servidor, entorno, bases, pid=os.getpid(), ahora=ayer)
    assert {x.nombre: x.estado for x in b.listar_bases(servidor)}[nombre] == "HUERFANA"
    assert b.lanzador_vivo({"pid": str(os.getpid()), "creado": datetime.now(UTC).isoformat()}) is True
    assert b.lanzador_vivo({"pid": str(os.getpid()), "creado": ayer.isoformat()}) is False
    assert b.lanzador_vivo({"pid": str(_pid_muerto()), "creado": datetime.now(UTC).isoformat()}) is False


def test_e2eciclo_18_la_base_de_otra_maquina_no_se_juzga(servidor, entorno, bases):
    run = _nuevo_run()
    nombre = n.nombre_de_base(run)
    bases.append(nombre)
    _sql(servidor, f'CREATE DATABASE "{nombre}"')
    _sql(servidor, f"COMMENT ON DATABASE \"{nombre}\" IS '{n.marca(run, 1, 'otra-maquina', datetime.now(UTC))}'")
    assert {x.nombre: x.estado for x in b.listar_bases(servidor)}[nombre] == "AJENA"
    assert b.purgar(servidor, confirmar=True, solo=nombre, entorno=entorno)[0][1] == "CONSERVADA"
    assert _existe(servidor, nombre)


def test_e2eciclo_19_purgar_sin_confirmar_no_elimina_nada(servidor, entorno, bases):
    _, huerfana = _crear(servidor, entorno, bases, pid=_pid_muerto())
    hecho = {x.nombre: h for x, h in b.purgar(servidor, confirmar=False, entorno=entorno)}
    assert hecho[huerfana] == "PENDIENTE"
    assert _existe(servidor, huerfana)


def test_e2eciclo_20_purgar_elimina_las_huerfanas_y_solo_las_huerfanas(servidor, entorno, bases, tmp_path):
    _, viva = _crear(servidor, entorno, bases)
    run, huerfana = _crear(servidor, entorno, bases, pid=_pid_muerto())
    (tmp_path / run / "license").mkdir(parents=True)
    hecho = {x.nombre: h for x, h in b.purgar(servidor, confirmar=True, entorno=entorno, estado=tmp_path)}
    assert hecho[huerfana] == "ELIMINADA" and hecho[viva] == "CONSERVADA"
    assert not _existe(servidor, huerfana) and _existe(servidor, viva)
    assert not (tmp_path / run).exists()


def test_e2eciclo_21_purgar_una_sola(servidor, entorno, bases):
    _, una = _crear(servidor, entorno, bases, pid=_pid_muerto())
    _, otra = _crear(servidor, entorno, bases, pid=_pid_muerto())
    assert [(x.nombre, h) for x, h in b.purgar(servidor, confirmar=True, solo=una, entorno=entorno)
            ] == [(una, "ELIMINADA")]
    assert not _existe(servidor, una) and _existe(servidor, otra)


def test_e2eciclo_22_lo_que_una_corrida_muerta_dejo_en_marcha_se_detiene(servidor, entorno, bases):
    run, huerfana = _crear(servidor, entorno, bases, pid=_pid_muerto())
    ajeno = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"],
                             env={**os.environ, "KONTROL_E2E_RUN_ID": _nuevo_run()})
    resto = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"],
                             env={**os.environ, "KONTROL_E2E_RUN_ID": run})
    try:
        assert b.procesos_de(run) == [resto.pid]
        b.purgar(servidor, confirmar=True, solo=huerfana, entorno=entorno)
        assert resto.wait(timeout=20) != 0
        assert b.procesos_de(run) == []
        assert ajeno.poll() is None, "se detuvo un proceso de otra corrida"
    finally:
        for proceso in (ajeno, resto):
            if proceso.poll() is None:
                proceso.kill()
            proceso.wait()


# ---------------------------------------------------------------- DB-17/18 · huella
def test_e2eciclo_23_la_huella_se_lee_sin_conectarse_y_no_cambia_si_nadie_toca_la_base(servidor, entorno, bases):
    _, nombre = _crear(servidor, entorno, bases)
    antes = b.huella(servidor, [nombre, "no_existe_esta_base"])
    assert antes["no_existe_esta_base"] is None and set(antes[nombre]) == {"sesiones", "escrituras"}
    assert b.huella(servidor, [nombre, "no_existe_esta_base"]) == antes
    assert b.conexiones(servidor, nombre) == 0
