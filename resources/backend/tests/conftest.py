"""Configuración de pruebas de KONTROL.

Define variables de entorno controladas ANTES de que se instancie
`app.core.config.Settings` (que usa lru_cache). Ningún secreto real se usa.
"""

from __future__ import annotations

import os
import tempfile

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

# Rutas de volúmenes temporales escribibles (no /data en entornos de prueba).
_tmp = tempfile.gettempdir()
os.environ.setdefault("KONTROL_INSTALLATION_VOLUME_PATH", os.path.join(_tmp, "kontrol-test-license"))
os.environ.setdefault("KONTROL_STORAGE_PATH", os.path.join(_tmp, "kontrol-test-storage"))
os.environ.setdefault("KONTROL_BACKUP_PATH", os.path.join(_tmp, "kontrol-test-backups"))

# Limpieza de la caché de settings para entornos repetidos
from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()


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
