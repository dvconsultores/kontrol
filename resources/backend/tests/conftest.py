"""Configuración de pruebas de KONTROL.

Define variables de entorno controladas ANTES de que se instancie
`app.core.config.Settings` (que usa lru_cache). Ningún secreto real se usa.
"""

from __future__ import annotations

import os
import tempfile

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
    dialecto). Si `KONTROL_TEST_DB_URL` apunta a PostgreSQL, cada módulo de
    prueba recibe su propio `schema` aislado, de modo que la misma suite se
    ejecuta sobre el motor de producción sin colisiones.

    Uso:
        KONTROL_TEST_DB_URL=postgresql+psycopg2://... pytest tests/
    """
    import uuid as _uuid

    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import StaticPool

    url = os.environ.get("KONTROL_TEST_DB_URL")
    if not url:
        params = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
        params.update(kwargs)
        return create_engine("sqlite+pysqlite:///:memory:", future=True, **params)

    schema = f"t_{_uuid.uuid4().hex[:12]}"
    # El schema se fija en `connect_args`, no con un listener de evento: si se
    # registra el listener después de abrir la primera conexión, ésta queda en
    # el pool SIN `search_path` y todas las pruebas acaban compartiendo
    # `public`. Detectado al ejecutar la suite sobre PostgreSQL real.
    admin = create_engine(url, future=True)
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    admin.dispose()

    connect_args = dict(kwargs.pop("connect_args", {}))
    connect_args["options"] = f"-csearch_path={schema}"
    return create_engine(url, future=True, connect_args=connect_args, **kwargs)


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
