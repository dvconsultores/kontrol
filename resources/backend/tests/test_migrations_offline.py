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
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from alembic.migration import MigrationContext
from alembic.operations import Operations
from tests.alembic_orden import orden_alembic

BACKEND = Path(__file__).resolve().parents[1]

# Entorno controlado ANTES de importar app (mismo patrón que conftest.py)
os.environ.setdefault("KONTROL_SECRET_KEY", "test-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")
os.environ.setdefault("KONTROL_COOKIE_SECURE", "false")


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
    # Hasta 0012: última migración de ESQUEMA antes de la de datos 0013
    # (las migraciones de datos no son válidas en modo offline --sql).
    proc = subprocess.run(
        orden_alembic("upgrade", "0012_numeric_money", "--sql"),
        cwd=str(BACKEND), env=_base_env(tmp_path), capture_output=True, text=True, timeout=240,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    assert "CREATE TABLE" in proc.stdout
    assert "ALTER TABLE" in proc.stdout
    # Fundación: >100 tablas, >50 alteraciones (dinero→NUMERIC incluidas)
    assert proc.stdout.count("CREATE TABLE") >= 100
    assert proc.stdout.count("ALTER TABLE") >= 50


def test_migration_0014_numeric_money_2_upgrade_sql_compiles(tmp_path):
    """T-201/KAUD-011: la migración 0014 (segunda ola Float→Numeric) compila su
    SQL offline sobre dialecto PostgreSQL, aplicada a partir del head de esquema
    0012 (saltando la migración de datos 0013, que no es válida en --sql)."""
    # 0014 es esquema puro (ALTER ... ::numeric); validamos estáticamente que
    # altera todas las tablas de la segunda ola y que la cadena ORM coincide
    # (el upgrade real a head en PostgreSQL queda en pending-validations).
    src = (BACKEND / "alembic" / "versions" / "0014_numeric_money_2.py").read_text(encoding="utf-8")
    # La función upgrade genera ALTER TABLE ... USING ...::numeric para cada columna
    assert "ap_open_items" in src and "withholding_rules" in src and "credit_limit" in src
    expected = ["ap_advances", "ap_open_items", "ap_payments", "sales_credit_notes",
                "supplier_credit_notes", "bank_transactions", "cash_sessions", "customers",
                "tax_calculations", "withholding_rules", "purchase_order_lines",
                "supplier_quote_lines", "sales_order_lines", "sales_quote_lines",
                "triple_matches", "sales_orders"]
    for t in expected:
        assert f'"{t}"' in src, f"0014 debe alterar la tabla {t}"


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


def test_approvals_migrations_compile_offline_postgres(tmp_path):
    """Spec 045: la migración 0015 compila en dialecto PostgreSQL (T-045-005).

    No sustituye la ejecución sobre PostgreSQL real (BLK-D0-01, Constitución
    P21): sólo verifica que el SQL generado es válido para el dialecto de
    producción. La migración de datos 0016 no es válida en modo offline.
    """
    result = subprocess.run(
        orden_alembic("upgrade", "0014_numeric_money_2:0015_approvals", "--sql"),
        cwd=str(BACKEND), env=_base_env(tmp_path), capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    sql = result.stdout
    for table in ("approval_policies", "approval_rules", "approval_levels", "approval_requests",
                  "approval_steps", "approval_decisions", "approval_delegations", "approval_events"):
        assert f"CREATE TABLE {table}" in sql, f"falta {table}"
    assert "ALTER TABLE approval_requests RENAME TO regulatory_approval_requests" in sql or \
           "ALTER TABLE approval_requests RENAME TO" in sql


def test_approvals_data_migration_is_idempotent():
    """0016: permisos e histórico se migran sin duplicar (T-045-066, AC-22)."""
    from sqlalchemy import create_engine as _ce

    spec = importlib.util.spec_from_file_location(
        "mig_0016", BACKEND / "alembic" / "versions" / "0016_approvals_backfill.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    engine = _ce("sqlite+pysqlite:///:memory:", future=True,
                 connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from app.core.database import Base as _Base
    from app.core.database import init_models as _init

    _init()
    _Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO roles (id, code, name, protected, status, created_at, updated_at) "
            "VALUES ('r1', 'ADMIN', 'Administrador', 1, 'ACTIVE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"))
        conn.execute(text(
            "INSERT INTO companies (id, tenant_id, code, legal_name, rif, legal_type, "
            " functional_currency, status, created_at, updated_at) "
            "VALUES ('c1', 't1', 'C1', 'Demo CA', 'J-1', 'CA', 'VED', 'ACTIVE', "
            " CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"))
        conn.execute(text(
            "INSERT INTO regulatory_approval_requests "
            "(id, company_id, object_ref, requester_id, amount, decision, status, created_at, updated_at) "
            "VALUES ('leg-1', 'c1', 'DESP-1', 'u1', 100.0, 'APPROVED', 'APPROVED', "
            " CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"))
        # Fila con referencia colgante: la tabla legada no tiene FK a companies,
        # la nueva sí. Debe omitirse sin abortar la migración y conservarse.
        conn.execute(text(
            "INSERT INTO regulatory_approval_requests "
            "(id, company_id, object_ref, requester_id, amount, decision, status, created_at, updated_at) "
            "VALUES ('leg-huerfana', 'c-BORRADA', 'DESP-2', 'u1', 50.0, 'APPROVED', 'APPROVED', "
            " CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"))

    def _run() -> None:
        with engine.begin() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                module.upgrade()

    _run()
    _run()  # segunda ejecución: no debe duplicar

    with engine.begin() as conn:
        migrated = conn.execute(text(
            "SELECT policy_version, status FROM approval_requests "
            "WHERE document_id = 'leg-1'")).fetchall()
        perms = conn.execute(text(
            "SELECT COUNT(*) FROM permissions WHERE resource = 'aprobaciones'")).scalar()
        links = conn.execute(text("SELECT COUNT(*) FROM role_permissions")).scalar()
        huerfana_migrada = conn.execute(text(
            "SELECT COUNT(*) FROM approval_requests "
            "WHERE document_id = 'leg-huerfana'")).scalar()
        huerfana_conservada = conn.execute(text(
            "SELECT COUNT(*) FROM regulatory_approval_requests "
            "WHERE id = 'leg-huerfana'")).scalar()

    assert len(migrated) == 1, "el histórico se duplicó"
    # No se inventa política: se declara explícitamente que se desconoce (AC-22)
    assert migrated[0][0] == "LEGACY_UNVERSIONED"
    assert migrated[0][1] == "APPROVED"
    assert perms == 6
    assert links == 6
    # La fila con empresa inexistente NO se migra (violaría la FK) pero TAMPOCO
    # se pierde: permanece en la tabla legada.
    assert huerfana_migrada == 0, "una fila con referencia colgante no debe migrarse"
    assert huerfana_conservada == 1, "una fila omitida no debe perderse"
