"""Configuración de pruebas de KONTROL.

Define variables de entorno controladas ANTES de que se instancie
`app.core.config.Settings` (que usa lru_cache). Ningún secreto real se usa.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

# Clave de prueba (>=32 caracteres). Nunca usar en producción.
os.environ.setdefault(
    "KONTROL_SECRET_KEY",
    "test-secret-key-0123456789abcdef0123456789abcdef",
)
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")
os.environ.setdefault("KONTROL_COOKIE_SECURE", "false")
os.environ.setdefault("KONTROL_DB_URL", "sqlite+pysqlite:///:memory:")

# Rutas de volúmenes temporales escribibles (no /data en entornos de prueba). El volumen de
# instalación NO se fija aquí: lo recibe cada proceso de pytest en `pytest_configure` y cada
# módulo en `volumen_de_instalacion` (más abajo).
_tmp = tempfile.gettempdir()
os.environ.setdefault("KONTROL_STORAGE_PATH", os.path.join(_tmp, "kontrol-test-storage"))
os.environ.setdefault("KONTROL_BACKUP_PATH", os.path.join(_tmp, "kontrol-test-backups"))

# Limpieza de la caché de settings para entornos repetidos
from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()


# --------------------------------------------------------------------------- #
# Volumen de instalación aislado (SPEC054 · TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO)
# --------------------------------------------------------------------------- #
# El producto escribe `installation_private_key.pem` en `KONTROL_INSTALLATION_VOLUME_PATH` cada
# vez que un mundo inicializa su instalación. Con una ruta fija por máquina, dos `pytest` se
# reescribían la clave y la sincronización firmaba con la clave ajena (`SYNC_AUTH_INVALID`).
# Ahora cada proceso recibe una raíz propia, cada módulo un volumen hijo vacío, y los dos se
# eliminan al terminar. La raíz nace en un hook, no al importar: este fichero vive dos veces en
# `sys.modules` (`conftest` y `tests.conftest`) y solo el plugin registrado ejecuta hooks.
VARIABLE_DEL_VOLUMEN = "KONTROL_INSTALLATION_VOLUME_PATH"
PREFIJO_DEL_VOLUMEN = "kontrol-test-license-"
RAIZ_DEL_VOLUMEN = pytest.StashKey[str]()
VOLUMEN_HEREDADO = pytest.StashKey[str | None]()


def _fijar_volumen(ruta: str | None) -> None:
    """Fija (o quita) la variable del volumen y descarta la `Settings` cacheada que apuntaba al anterior."""
    if ruta is None:
        os.environ.pop(VARIABLE_DEL_VOLUMEN, None)
    else:
        os.environ[VARIABLE_DEL_VOLUMEN] = ruta
    get_settings.cache_clear()


def pytest_configure(config):
    """Raíz única de este proceso: nombre aleatorio de `mkdtemp`; nunca una ruta fija ni la heredada del entorno."""
    config.stash[VOLUMEN_HEREDADO] = os.environ.get(VARIABLE_DEL_VOLUMEN)
    raiz = tempfile.mkdtemp(prefix=PREFIJO_DEL_VOLUMEN)
    config.stash[RAIZ_DEL_VOLUMEN] = raiz
    _fijar_volumen(raiz)


def pytest_unconfigure(config):
    """Al cerrar el proceso la raíz desaparece con lo que quedara dentro, y la variable vuelve a su valor previo."""
    raiz = config.stash.get(RAIZ_DEL_VOLUMEN, None)
    if raiz is None:
        return
    shutil.rmtree(raiz)
    _fijar_volumen(config.stash[VOLUMEN_HEREDADO])


@contextmanager
def volumen_de_instalacion_aislado(raiz: str, nombre: str) -> Iterator[str]:
    """Un volumen hijo vacío dentro de `raiz`, visible para `get_settings()` mientras dura. Al salir se
    elimina —pase o falle lo que corrió dentro— y la variable y la caché vuelven a como estaban."""
    anterior = os.environ.get(VARIABLE_DEL_VOLUMEN)
    volumen = tempfile.mkdtemp(prefix=f"{nombre}-", dir=raiz)
    _fijar_volumen(volumen)
    try:
        yield volumen
    finally:
        shutil.rmtree(volumen)
        _fijar_volumen(anterior)


@pytest.fixture(scope="module", autouse=True)
def volumen_de_instalacion(request) -> Iterator[str]:
    """Cada módulo escribe y lee su clave de instalación en un volumen que ningún otro módulo ni proceso ve."""
    with volumen_de_instalacion_aislado(request.config.stash[RAIZ_DEL_VOLUMEN], request.module.__name__) as volumen:
        yield volumen


# --------------------------------------------------------------------------- #
# Motor de pruebas (Constitución P21 · CVG-045-01/02)
# --------------------------------------------------------------------------- #
def make_engine(**kwargs):
    """Motor para los fixtures de prueba.

    Por defecto SQLite en memoria (rápido, para pruebas que no ejercitan el
    dialecto). Si `KONTROL_TEST_DB_URL` apunta a PostgreSQL, cada llamada recibe
    su propio `schema` aislado, de modo que la misma suite se ejecuta sobre el
    motor de producción sin colisiones.

    Ese schema y su motor tienen dueño: se apuntan al ámbito abierto —la prueba o
    el módulo, según la fixture que llame— y las fixtures `_recursos_pg_*` de este
    fichero los sueltan al terminar ese ámbito (`pg_harness`). Quien llama no
    tiene que limpiar nada, y tampoco puede olvidarse.

    Uso:
        KONTROL_TEST_DB_URL=postgresql+psycopg2://... pytest tests/
    """
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    url = os.environ.get("KONTROL_TEST_DB_URL")
    if not url:
        params = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
        params.update(kwargs)
        return create_engine("sqlite+pysqlite:///:memory:", future=True, **params)

    import pg_harness

    return pg_harness.crear_motor_de_prueba(url, **kwargs)


# --------------------------------------------------------------------------- #
# Una sesión con la base limpia por prueba, sin un schema por prueba (SPEC054 · TEST-PG-UN-SCHEMA-POR-PRUEBA)
# --------------------------------------------------------------------------- #
# Doce suites creaban en PostgreSQL un schema entero (203 tablas, 638 índices) por cada prueba:
# ≈1,1 s de DDL por prueba y cientos de miles de relaciones por corrida. Ahora el schema se crea
# una vez por módulo (PGLIFE lo apunta al módulo y lo suelta con él) y cada prueba trabaja en su
# propia conexión dentro de una transacción externa: los `commit` del código —de la prueba o del
# producto— solo sueltan un SAVEPOINT, y al terminar la prueba todo se deshace. Ninguna prueba ve
# filas de otra. En SQLite no cambia nada: base en memoria nueva por prueba (`pysqlite` no sostiene
# la transacción externa con `StaticPool`, y crearla cuesta milisegundos).
@pytest.fixture(scope="module")
def _esquema_del_modulo():
    """PostgreSQL: un schema con todas las tablas, una vez por módulo. SQLite: nada (`None`)."""
    if not os.environ.get("KONTROL_TEST_DB_URL"):
        yield None
        return
    from app.core.database import Base, init_models

    motor = make_engine()
    init_models()
    Base.metadata.create_all(motor)
    yield motor
    motor.dispose()


@pytest.fixture
def sesion_de_prueba(_esquema_del_modulo):
    """Sesión ORM sobre una base limpia que solo esta prueba ve; lo que escriba desaparece al terminar."""
    from sqlalchemy.orm import Session, sessionmaker

    from app.core.database import Base, init_models

    if _esquema_del_modulo is None:
        motor = make_engine()
        init_models()
        Base.metadata.create_all(motor)
        sesion = sessionmaker(bind=motor, class_=Session, expire_on_commit=False)()
        try:
            yield sesion
        finally:
            sesion.close()
            motor.dispose()
        return
    conexion = _esquema_del_modulo.connect()
    externa = conexion.begin()
    sesion = Session(bind=conexion, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield sesion
    finally:
        sesion.close()
        externa.rollback()
        conexion.close()


# --------------------------------------------------------------------------- #
# Ciclo de vida de lo que la suite crea en PostgreSQL (SPEC054 · PGLIFE)
# --------------------------------------------------------------------------- #
# Lo que nace durante una prueba se suelta al acabar la prueba; lo que nace en
# una fixture de módulo, al acabar el módulo. Son `autouse` y se desmontan
# después que las fixtures de cada módulo, es decir, cuando éstas ya cerraron sus
# sesiones; y pytest desmonta una fixture pase o falle la prueba. En SQLite no
# hay nada apuntado y no hacen nada.
@pytest.fixture(scope="module", autouse=True)
def _recursos_pg_del_modulo(request):
    import pg_harness

    ambito = pg_harness.abrir_ambito(f"módulo {request.module.__name__}")
    yield
    pg_harness.cerrar_ambito(ambito)


@pytest.fixture(autouse=True)
def _recursos_pg_de_la_prueba(request):
    import pg_harness

    ambito = pg_harness.abrir_ambito(f"prueba {request.node.nodeid}")
    yield
    pg_harness.cerrar_ambito(ambito)


def pytest_sessionfinish(session, exitstatus):
    """Red de seguridad: lo que quedara sin soltar se suelta aquí, y la corrida dice qué fue."""
    import pg_harness

    pg_harness.cerrar_sesion()
    if pg_harness.INFORME.residuos and session.exitstatus == 0:
        session.exitstatus = 1


def pytest_terminal_summary(terminalreporter):
    import pg_harness

    informe = pg_harness.INFORME
    if not (informe.conexiones_cortadas or informe.residuos):
        return
    terminalreporter.section("recursos de prueba en PostgreSQL")
    terminalreporter.write_line(
        f"schemas creados: {informe.schemas_creados} · soltados: {informe.schemas_soltados} · "
        f"bases soltadas: {informe.bases_soltadas}")
    for ambito, schema, n in informe.conexiones_cortadas:
        terminalreporter.write_line(f"conexiones que quedaron abiertas y se cortaron: {n} · {ambito} · {schema}")
    for residuo in informe.residuos:
        terminalreporter.write_line(f"NO SE PUDO SOLTAR: {residuo}")


def seed_org_chain(session, *company_ids: str) -> None:
    """Crea la cadena installation → tenant → company para los ids indicados.

    PostgreSQL **sí** exige las claves foráneas; SQLite, por defecto, no. Las
    fixtures que insertaban `company_id` de una empresa inexistente pasaban en
    SQLite y fallaban en PostgreSQL con `ForeignKeyViolation`. Sembrar la cadena
    es correcto en ambos motores y es requisito de la Constitución P21.

    Idempotente: no duplica si la empresa ya existe.
    """
    from app.modules.organization.models import Company, Installation, Tenant

    inst = session.get(Installation, "inst-test")
    if inst is None:
        session.add(Installation(id="inst-test", installation_uuid="uuid-test", state="ACTIVE"))
        session.flush()
    for index, company_id in enumerate(company_ids, start=1):
        if session.get(Company, company_id) is not None:
            continue
        tenant_id = f"ten-{index}-{company_id}"[:36]
        if session.get(Tenant, tenant_id) is None:
            session.add(Tenant(id=tenant_id, installation_id="inst-test", code=f"T{index}",
                               name=f"Tenant {index}", plan="MULTI_COMPANY", status="ACTIVE"))
            session.flush()
        session.add(Company(id=company_id, tenant_id=tenant_id, code=f"C{index}",
                            legal_name=f"Empresa {index}", rif=f"J-{index}", legal_type="CA",
                            functional_currency="VED", status="ACTIVE"))
    session.flush()
