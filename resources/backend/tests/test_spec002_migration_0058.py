"""Spec 002 · la migración 0058 sobre PostgreSQL real.

Instalación limpia, actualización con datos existentes, restricciones de
integridad y downgrade.
"""

from __future__ import annotations

import os
import subprocess
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from tests.alembic_orden import orden_alembic

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif(
    not PG_URL.startswith("postgresql"),
    reason="La migración 0058 solo se verifica sobre PostgreSQL",
)
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRE_058 = "0057_spec047_notifications"
CHECK_VIOLATION = "23514"
UNIQUE_VIOLATION = "23505"


def _postgres_admin_url() -> str:
    return PG_URL.rsplit("/", 1)[0] + "/postgres"


def _db_url(name: str) -> str:
    return PG_URL.rsplit("/", 1)[0] + "/" + name


def _crear_base(name: str) -> None:
    admin = create_engine(
        _postgres_admin_url(), future=True, isolation_level="AUTOCOMMIT"
    )
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    admin.dispose()


def _borrar_base(name: str) -> None:
    admin = create_engine(
        _postgres_admin_url(), future=True, isolation_level="AUTOCOMMIT"
    )
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    admin.dispose()


def _alembic(
    name: str, target: str, comando: str = "upgrade"
) -> subprocess.CompletedProcess:
    env = {**os.environ, "KONTROL_DB_URL": _db_url(name)}
    env.pop("KONTROL_TEST_DB_URL", None)
    proc = subprocess.run(
        orden_alembic(comando, target),
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert proc.returncode == 0, (
        "alembic falló\n"
        f"stdout[-2000:]\n{proc.stdout[-2000:]}\n"
        f"stderr[-2000:]\n{proc.stderr[-2000:]}"
    )
    return proc


def _sql(name: str, statements: list[tuple[str, dict]]) -> None:
    engine = create_engine(_db_url(name), future=True)
    with engine.begin() as conn:
        for statement, params in statements:
            conn.execute(text(statement), params)
    engine.dispose()


def _rows(name: str, statement: str, **params):
    engine = create_engine(_db_url(name), future=True)
    try:
        with engine.connect() as conn:
            return conn.execute(text(statement), params).fetchall()
    finally:
        engine.dispose()


@pytest.fixture(scope="module")
def base_migrada_0058():
    """Base PostgreSQL con la migración 0058 aplicada."""
    name = f"k058_{uuid.uuid4().hex[:8]}"
    _crear_base(name)
    _alembic(name, "head")
    yield name
    _borrar_base(name)


@pytest.fixture(scope="module")
def base_actualizada_0058():
    """Base PostgreSQL con datos previos y la migración 0058 aplicada."""
    name = f"k058b_{uuid.uuid4().hex[:8]}"
    _crear_base(name)
    _alembic(name, PRE_058)

    ids = {
        k: str(uuid.uuid4())
        for k in ("inst", "ten", "co", "usr", "sess", "rol", "perm")
    }
    _sql(name, [
        (
            "INSERT INTO installations (id, installation_uuid, state, created_at, updated_at) "
            "VALUES (:i, :i, 'ACTIVE', now(), now())",
            {"i": ids["inst"]},
        ),
        (
            "INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at, updated_at) "
            "VALUES (:t, :i, 'T058', 'T', 'MONO_COMPANY', 'ACTIVE', now(), now())",
            {"t": ids["ten"], "i": ids["inst"]},
        ),
        (
            "INSERT INTO users (id, tenant_id, username, email, password_hash, status, "
            "must_change_password, failed_attempts, mfa_enabled, created_at, updated_at) "
            "VALUES (:u, :t, 'u058', 'u@example.com', 'x', 'ACTIVE', false, 0, false, now(), now())",
            {"u": ids["usr"], "t": ids["ten"]},
        ),
        (
            "INSERT INTO roles (id, code, name, protected, status, created_at, updated_at) "
            "VALUES (:r, 'ADMIN', 'Admin', true, 'ACTIVE', now(), now())",
            {"r": ids["rol"]},
        ),
        (
            "INSERT INTO permissions (id, resource, action, scope_type, created_at, updated_at) "
            "VALUES (:p, 'users', 'mfa_reset', 'INSTALLATION', now(), now())",
            {"p": ids["perm"]},
        ),
        (
            "INSERT INTO sessions (id, user_id, refresh_token_hash, expires_at, created_at, updated_at) "
            "VALUES (:s, :u, 'hash', now() + interval '1 day', now(), now())",
            {"s": ids["sess"], "u": ids["usr"]},
        ),
    ])
    _alembic(name, "head")
    yield name, ids
    _borrar_base(name)


def test_mfa_m01_instalacion_limpia_tiene_tablas_columnas_indices_y_permiso(
    base_migrada_0058,
):
    """MFA-M01: instalación limpia contiene las tablas, columnas, índices y permiso."""
    name = base_migrada_0058
    tablas = {
        r[0]
        for r in _rows(
            name,
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'",
        )
    }
    assert {"mfa_factors", "mfa_recovery_codes", "mfa_challenges"} <= tablas, tablas

    columnas_sessions = {
        r[0]
        for r in _rows(
            name,
            "SELECT column_name FROM information_schema.columns WHERE table_name='sessions'",
        )
    }
    for columna in ("family_id", "auth_method", "mfa_verified_at", "reauth_at"):
        assert columna in columnas_sessions, columna

    nulos = _rows(
        name,
        "SELECT is_nullable FROM information_schema.columns "
        "WHERE table_name='sessions' AND column_name='family_id'",
    )
    assert nulos[0][0] == "NO", nulos

    auth = _rows(
        name,
        "SELECT is_nullable, column_default FROM information_schema.columns "
        "WHERE table_name='sessions' AND column_name='auth_method'",
    )
    assert auth[0][0] == "NO", auth
    assert "PASSWORD" in (auth[0][1] or ""), auth

    indices = {
        r[0]
        for r in _rows(
            name,
            "SELECT indexname FROM pg_indexes WHERE schemaname='public'",
        )
    }
    assert "uq_mfa_factor_active" in indices, indices
    assert "uq_mfa_factor_pending" in indices, indices

    permisos = _rows(
        name,
        "SELECT p.action FROM permissions p WHERE p.resource='users' AND p.action='mfa_reset'",
    )
    assert permisos, permisos


def test_mfa_m02_actualizacion_rellena_sesiones_y_permisos(base_actualizada_0058):
    """MFA-M02: actualización rellena family_id, auth_method y el permiso ADMIN."""
    name, ids = base_actualizada_0058
    sesion = _rows(
        name,
        "SELECT family_id, auth_method FROM sessions WHERE id = :s",
        s=ids["sess"],
    )[0]
    assert sesion[0] == ids["sess"], sesion
    assert sesion[1] == "PASSWORD", sesion

    permisos = _rows(
        name,
        "SELECT count(*) FROM role_permissions rp "
        "JOIN roles r ON r.id = rp.role_id "
        "JOIN permissions p ON p.id = rp.permission_id "
        "WHERE r.id = :r AND p.resource='users' AND p.action='mfa_reset'",
        r=ids["rol"],
    )
    assert permisos[0][0] == 1, permisos

    mfa_habilitado = _rows(
        name, "SELECT mfa_enabled FROM users WHERE id = :u", u=ids["usr"]
    )
    assert mfa_habilitado[0][0] is False, mfa_habilitado


def test_mfa_m03_restricciones_unicas_y_check(base_migrada_0058):
    """MFA-M03: restricciones UNIQUE y CHECK de mfa_factors y sessions."""
    name = base_migrada_0058
    ids = {k: str(uuid.uuid4()) for k in ("inst", "ten", "usr", "factor")}
    _sql(name, [
        (
            "INSERT INTO installations (id, installation_uuid, state, created_at, updated_at) "
            "VALUES (:i, :i, 'ACTIVE', now(), now())",
            {"i": ids["inst"]},
        ),
        (
            "INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at, updated_at) "
            "VALUES (:t, :i, 'T058C', 'T', 'MONO_COMPANY', 'ACTIVE', now(), now())",
            {"t": ids["ten"], "i": ids["inst"]},
        ),
        (
            "INSERT INTO users (id, tenant_id, username, email, password_hash, status, "
            "must_change_password, failed_attempts, mfa_enabled, created_at, updated_at) "
            "VALUES (:u, :t, 'u058c', 'u@example.com', 'x', 'ACTIVE', false, 0, false, now(), now())",
            {"u": ids["usr"], "t": ids["ten"]},
        ),
    ])

    engine = create_engine(_db_url(name), future=True)
    try:
        # Dos factores ACTIVE del mismo usuario: violación única 23505.
        with pytest.raises(DBAPIError) as info:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO mfa_factors (id, tenant_id, user_id, status, secret_ciphertext, created_at, updated_at) "
                        "VALUES (:i, :t, :u, 'ACTIVE', decode('00', 'hex'), now(), now())"
                    ),
                    {"i": str(uuid.uuid4()), "t": ids["ten"], "u": ids["usr"]},
                )
                conn.execute(
                    text(
                        "INSERT INTO mfa_factors (id, tenant_id, user_id, status, secret_ciphertext, created_at, updated_at) "
                        "VALUES (:i, :t, :u, 'ACTIVE', decode('00', 'hex'), now(), now())"
                    ),
                    {"i": str(uuid.uuid4()), "t": ids["ten"], "u": ids["usr"]},
                )
        assert getattr(info.value.orig, "pgcode", "") == UNIQUE_VIOLATION

        # status inválido: violación CHECK 23514.
        with pytest.raises(DBAPIError) as info:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO mfa_factors (id, tenant_id, user_id, status, secret_ciphertext, created_at, updated_at) "
                        "VALUES (:i, :t, :u, 'INVALIDO', decode('00', 'hex'), now(), now())"
                    ),
                    {"i": str(uuid.uuid4()), "t": ids["ten"], "u": ids["usr"]},
                )
        assert getattr(info.value.orig, "pgcode", "") == CHECK_VIOLATION

        # auth_method inválido: violación CHECK 23514.
        with pytest.raises(DBAPIError) as info:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO sessions (id, user_id, family_id, refresh_token_hash, auth_method, expires_at, created_at, updated_at) "
                        "VALUES (:i, :u, :i, 'hash', 'INVALIDO', now() + interval '1 day', now(), now())"
                    ),
                    {"i": str(uuid.uuid4()), "u": ids["usr"]},
                )
        assert getattr(info.value.orig, "pgcode", "") == CHECK_VIOLATION

    finally:
        engine.dispose()


def test_mfa_m04_downgrade_elimina_tablas_y_columnas(base_actualizada_0058):
    """MFA-M04: downgrade elimina tablas MFA y columnas nuevas de sessions."""
    name, _ = base_actualizada_0058
    _alembic(name, PRE_058, "downgrade")

    tablas = {
        r[0]
        for r in _rows(
            name,
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'",
        )
    }
    assert not {"mfa_factors", "mfa_recovery_codes", "mfa_challenges"} & tablas

    columnas = {
        r[0]
        for r in _rows(
            name,
            "SELECT column_name FROM information_schema.columns WHERE table_name='sessions'",
        )
    }
    assert not {"family_id", "auth_method", "mfa_verified_at", "reauth_at"} & columnas
