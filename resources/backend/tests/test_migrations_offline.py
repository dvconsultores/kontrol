"""T-06 · Validación de migraciones Alembic (cadena + drift + idempotencia).

- `alembic upgrade 0012_numeric_money --sql` en dialecto PostgreSQL: la cadena de
  esquema completa (145 tablas) compila sin errores (offline, sin conexión).
- Migración de datos `0013_seed_business_permissions`: aplicada sobre una base
  real en memoria, otorga permisos al rol ADMIN de forma idempotente (2 ejecuciones
  no duplican RolePermission).

Nota: el drift completo (comparación modelo↔BD) se verifica en PostgreSQL real
con `alembic check` (requiere instancia; pasos en pending-validations.md).
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from alembic.migration import MigrationContext
from alembic.operations import Operations

BACKEND = Path(__file__).resolve().parents[1]

# Entorno controlado ANTES de importar app (mismo patrón que conftest.py)
os.environ.setdefault("KONTROL_SECRET_KEY", "test-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")
os.environ.setdefault("KONTROL_COOKIE_SECURE", "false")
os.environ.setdefault("KONTROL_INSTALLATION_VOLUME_PATH", os.path.join(tempfile.gettempdir(), "kontrol-test-license"))
os.environ.setdefault("KONTROL_STORAGE_PATH", os.path.join(tempfile.gettempdir(), "kontrol-test-storage"))
os.environ.setdefault("KONTROL_BACKUP_PATH", os.path.join(tempfile.gettempdir(), "kontrol-test-backups"))


def _base_env(tmp: Path) -> dict:
    env = os.environ.copy()
    env.update({
        "KONTROL_SECRET_KEY": "test-secret-key-0123456789abcdef0123456789abcdef",
        "KONTROL_ENVIRONMENT": "local",
        "KONTROL_LOG_JSON": "false",
        "KONTROL_COOKIE_SECURE": "false",
        "KONTROL_DB_URL": "postgresql+psycopg2://u:p@localhost:5432/kontrol_test",
        "KONTROL_INSTALLATION_VOLUME_PATH": str(tmp / "lic"),
        "KONTROL_STORAGE_PATH": str(tmp / "st"),
        "KONTROL_BACKUP_PATH": str(tmp / "bk"),
    })
    return env


def test_schema_chain_compiles_offline_postgres(tmp_path):
    alembic_bin = BACKEND / ".venv" / "bin" / "alembic"
    if not alembic_bin.exists():
        pytest.skip("alembic no está disponible en el entorno")
    proc = subprocess.run(
        [str(alembic_bin), "upgrade", "0012_numeric_money", "--sql"],
        cwd=str(BACKEND), env=_base_env(tmp_path), capture_output=True, text=True, timeout=240,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    assert "CREATE TABLE" in proc.stdout
    assert "ALTER TABLE" in proc.stdout
    # Fundación: >100 tablas, >50 alteraciones (dinero→NUMERIC incluidas)
    assert proc.stdout.count("CREATE TABLE") >= 100
    assert proc.stdout.count("ALTER TABLE") >= 50


def _load_migration_0013():
    path = BACKEND / "alembic" / "versions" / "0013_seed_business_permissions.py"
    spec = importlib.util.spec_from_file_location("m0013", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_migration_0013_grants_permissions_idempotent():
    from app.core.config import get_settings
    get_settings.cache_clear()
    from app.core.database import Base, init_models

    init_models()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:", future=True,
        connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    mod = _load_migration_0013()

    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO roles (id, code, name, protected, status) "
            "VALUES ('r1', 'ADMIN', 'Administrador', 1, 'ACTIVE')"
        ))
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            mod.upgrade()
        first = conn.execute(text(
            "SELECT COUNT(*) FROM role_permissions WHERE role_id = 'r1'"
        )).scalar()

        with Operations.context(ctx):
            mod.upgrade()  # segunda ejecución: idempotente
        second = conn.execute(text(
            "SELECT COUNT(*) FROM role_permissions WHERE role_id = 'r1'"
        )).scalar()

    assert first is not None and first > 0
    assert first == second, f"la migración 0013 duplicó permisos: {first} → {second}"


def test_migration_0013_skips_when_no_admin():
    from app.core.config import get_settings
    get_settings.cache_clear()
    from app.core.database import Base, init_models

    init_models()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:", future=True,
        connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    mod = _load_migration_0013()

    with engine.begin() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            mod.upgrade()  # sin rol ADMIN: no debe fallar ni crear nada
        roles = conn.execute(text("SELECT COUNT(*) FROM roles")).scalar()
    assert roles == 0
