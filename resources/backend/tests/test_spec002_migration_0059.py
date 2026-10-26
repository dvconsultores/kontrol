"""Spec 002 · la migración 0059 sobre PostgreSQL real.

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
    reason="La migración 0059 solo se verifica sobre PostgreSQL",
)
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRE_059 = "0058_spec002_mfa"
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
def base_migrada_0059():
    """Base PostgreSQL con la migración 0059 aplicada."""
    name = f"k059_{uuid.uuid4().hex[:8]}"
    _crear_base(name)
    _alembic(name, "head")
    yield name
    _borrar_base(name)


@pytest.fixture(scope="module")
def base_actualizada_0059():
    """Base PostgreSQL con datos previos y la migración 0059 aplicada."""
    name = f"k059b_{uuid.uuid4().hex[:8]}"
    _crear_base(name)
    _alembic(name, PRE_059)

    ids = {
        k: str(uuid.uuid4())
        for k in ("inst", "ten", "usr1", "usr2", "sess", "reset")
    }
    _sql(name, [
        (
            "INSERT INTO installations (id, installation_uuid, state, created_at, updated_at) "
            "VALUES (:i, :i, 'ACTIVE', now(), now())",
            {"i": ids["inst"]},
        ),
        (
            "INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at, updated_at) "
            "VALUES (:t, :i, 'T059', 'T', 'MONO_COMPANY', 'ACTIVE', now(), now())",
            {"t": ids["ten"], "i": ids["inst"]},
        ),
        (
            "INSERT INTO users (id, tenant_id, username, email, password_hash, status, "
            "must_change_password, failed_attempts, mfa_enabled, created_at, updated_at) "
            "VALUES (:u, :t, 'u059a', 'ua@example.com', 'x', 'ACTIVE', false, 0, false, now(), now())",
            {"u": ids["usr1"], "t": ids["ten"]},
        ),
        (
            "INSERT INTO users (id, tenant_id, username, email, password_hash, status, "
            "must_change_password, failed_attempts, mfa_enabled, created_at, updated_at) "
            "VALUES (:u, :t, 'u059b', 'ub@example.com', 'x', 'ACTIVE', false, 0, false, now(), now())",
            {"u": ids["usr2"], "t": ids["ten"]},
        ),
        (
            "INSERT INTO sessions (id, user_id, family_id, refresh_token_hash, auth_method, "
            "expires_at, created_at, updated_at) "
            "VALUES (:s, :u, :s, 'hash', 'PASSWORD', now() + interval '1 day', now(), now())",
            {"s": ids["sess"], "u": ids["usr1"]},
        ),
        (
            "INSERT INTO password_resets (id, user_id, token_hash, expires_at, created_at, updated_at) "
            "VALUES (:r, :u, 'hash', now() + interval '1 day', now(), now())",
            {"r": ids["reset"], "u": ids["usr1"]},
        ),
    ])
    _alembic(name, "head")
    yield name, ids
    _borrar_base(name)


def test_rst_mig_r01_columnas_e_indice_limpio(base_migrada_0059):
    """R01: columnas nuevas e índice único sobre token_hash en instalación limpia."""
    name = base_migrada_0059

    cols = _rows(
        name,
        "SELECT column_name, data_type, character_maximum_length, is_nullable, column_default "
        "FROM information_schema.columns "
        "WHERE table_name = 'users' AND column_name = 'credential_stamp'",
    )
    assert len(cols) == 1
    assert cols[0].data_type == "character varying"
    assert cols[0].character_maximum_length == 32
    assert cols[0].is_nullable == "NO"

    cols = _rows(
        name,
        "SELECT column_name, data_type, character_maximum_length, is_nullable "
        "FROM information_schema.columns "
        "WHERE table_name = 'sessions' AND column_name = 'credential_stamp'",
    )
    assert len(cols) == 1
    assert cols[0].data_type == "character varying"
    assert cols[0].character_maximum_length == 32
    assert cols[0].is_nullable == "YES"

    cols = _rows(
        name,
        "SELECT column_name, data_type, character_maximum_length, is_nullable "
        "FROM information_schema.columns "
        "WHERE table_name = 'mfa_challenges' AND column_name = 'credential_stamp'",
    )
    assert len(cols) == 1
    assert cols[0].data_type == "character varying"
    assert cols[0].character_maximum_length == 32
    assert cols[0].is_nullable == "YES"

    cols = _rows(
        name,
        "SELECT column_name, data_type, is_nullable, column_default "
        "FROM information_schema.columns "
        "WHERE table_name = 'password_resets' AND column_name = 'invalidated_at'",
    )
    assert len(cols) == 1
    assert cols[0].data_type == "timestamp with time zone"
    assert cols[0].is_nullable == "YES"

    cols = _rows(
        name,
        "SELECT column_name, data_type, character_maximum_length, is_nullable, column_default "
        "FROM information_schema.columns "
        "WHERE table_name = 'password_resets' AND column_name = 'source'",
    )
    assert len(cols) == 1
    assert cols[0].data_type == "character varying"
    assert cols[0].character_maximum_length == 16
    assert cols[0].is_nullable == "NO"
    assert "SELF" in cols[0].column_default

    idx = _rows(
        name,
        "SELECT indexdef FROM pg_indexes "
        "WHERE tablename = 'password_resets' AND indexdef LIKE '%token_hash%'",
    )
    assert len(idx) == 1
    assert "UNIQUE" in idx[0].indexdef
    assert "token_hash" in idx[0].indexdef


def test_rst_mig_r02_actualizacion_rellena_sellos_y_source(base_actualizada_0059):
    """R02: la actualización rellena credential_stamp y source en filas existentes."""
    name, ids = base_actualizada_0059

    rows = _rows(
        name,
        "SELECT id, credential_stamp FROM users ORDER BY id",
    )
    assert len(rows) == 2
    sellos = [row.credential_stamp for row in rows]
    assert all(s is not None and len(s) == 32 for s in sellos)
    assert sellos[0] != sellos[1]

    sello_usr1 = _rows(
        name,
        "SELECT credential_stamp FROM users WHERE id = :u",
        u=ids["usr1"],
    )[0].credential_stamp

    sess = _rows(
        name,
        "SELECT credential_stamp FROM sessions WHERE id = :s",
        s=ids["sess"],
    )
    assert len(sess) == 1
    assert sess[0].credential_stamp == sello_usr1

    reset = _rows(
        name,
        "SELECT source, invalidated_at FROM password_resets WHERE id = :r",
        r=ids["reset"],
    )
    assert len(reset) == 1
    assert reset[0].source == "SELF"
    assert reset[0].invalidated_at is None


def test_rst_mig_r03_unicidad_token_hash(base_migrada_0059):
    """R03: token_hash duplicado en password_resets viola la unicidad 23505."""
    name = base_migrada_0059
    ids = {k: str(uuid.uuid4()) for k in ("inst", "ten", "usr", "r1", "r2")}
    _sql(name, [
        (
            "INSERT INTO installations (id, installation_uuid, state, created_at, updated_at) "
            "VALUES (:i, :i, 'ACTIVE', now(), now())",
            {"i": ids["inst"]},
        ),
        (
            "INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at, updated_at) "
            "VALUES (:t, :i, 'T059C', 'T', 'MONO_COMPANY', 'ACTIVE', now(), now())",
            {"t": ids["ten"], "i": ids["inst"]},
        ),
        (
            "INSERT INTO users (id, tenant_id, username, email, password_hash, status, "
            "must_change_password, failed_attempts, mfa_enabled, credential_stamp, created_at, updated_at) "
            "VALUES (:u, :t, 'u059c', 'u@example.com', 'x', 'ACTIVE', false, 0, false, "
            "'00000000000000000000000000000000', now(), now())",
            {"u": ids["usr"], "t": ids["ten"]},
        ),
    ])

    common = {
        "u": ids["usr"],
        "hash": "hash",
    }
    engine = create_engine(_db_url(name), future=True)
    try:
        with pytest.raises(DBAPIError) as info:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO password_resets (id, user_id, token_hash, expires_at, created_at, updated_at) "
                        "VALUES (:i, :u, :hash, now() + interval '1 day', now(), now())"
                    ),
                    {"i": ids["r1"], **common},
                )
                conn.execute(
                    text(
                        "INSERT INTO password_resets (id, user_id, token_hash, expires_at, created_at, updated_at) "
                        "VALUES (:i, :u, :hash, now() + interval '1 day', now(), now())"
                    ),
                    {"i": ids["r2"], **common},
                )
        assert info.value.orig.pgcode == UNIQUE_VIOLATION
    finally:
        engine.dispose()


def test_rst_mig_r04_downgrade_elimina_columnas_e_indice(base_actualizada_0059):
    """R04: el downgrade a 0058 elimina columnas nuevas y el índice único."""
    name, _ = base_actualizada_0059
    _alembic(name, PRE_059, comando="downgrade")

    for table, column in (
        ("users", "credential_stamp"),
        ("sessions", "credential_stamp"),
        ("mfa_challenges", "credential_stamp"),
        ("password_resets", "invalidated_at"),
        ("password_resets", "source"),
    ):
        rows = _rows(
            name,
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c",
            t=table,
            c=column,
        )
        assert rows == []

    idx = _rows(
        name,
        "SELECT indexdef FROM pg_indexes "
        "WHERE tablename = 'password_resets' AND indexdef LIKE '%token_hash%'",
    )
    assert len(idx) == 1
    assert "UNIQUE" not in idx[0].indexdef
    assert "token_hash" in idx[0].indexdef
