"""FR-001-262 · OD-AUD-05: la base rechaza UPDATE, DELETE (y TRUNCATE en PostgreSQL) sobre `audit_events`.

PostgreSQL es la autoridad; SQLite es el equivalente soportado. En bases creadas
con `Base.metadata.create_all` los disparadores se registran como `after_create`;
en bases migradas con Alembic los instala la migración 0061. El índice
(tenant_id, event_time) existe por ambas vías.
"""
from __future__ import annotations

import os
import subprocess
import uuid
from datetime import UTC, datetime

import pytest
import sqlalchemy
from sqlalchemy import create_engine, inspect, text

from app.modules.audit.models import AuditEvent
from tests.alembic_orden import orden_alembic

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")


def _insertar(sesion) -> AuditEvent:
    evento = AuditEvent(
        action="LOGIN_SUCCESS",
        entity_type="User",
        tenant_id=None,
        event_time=datetime.now(UTC),
    )
    sesion.add(evento)
    sesion.commit()
    return evento


def test_imm_01_update_sql_rechazado(sesion_de_prueba):
    """IMM-01: UPDATE por SQL falla con AUDIT_EVENT_IMMUTABLE y la fila conserva su acción."""
    evento = _insertar(sesion_de_prueba)
    with pytest.raises(sqlalchemy.exc.DBAPIError) as exc:
        sesion_de_prueba.execute(text("UPDATE audit_events SET action = 'X' WHERE id = :id"), {"id": evento.id})
    assert "AUDIT_EVENT_IMMUTABLE" in str(exc.value)
    sesion_de_prueba.rollback()
    sesion_de_prueba.expire_all()
    fila = sesion_de_prueba.get(AuditEvent, evento.id)
    assert fila is not None and fila.action == "LOGIN_SUCCESS"


def test_imm_02_delete_sql_rechazado(sesion_de_prueba):
    """IMM-02: DELETE por SQL falla con AUDIT_EVENT_IMMUTABLE y la fila sigue existiendo."""
    evento = _insertar(sesion_de_prueba)
    with pytest.raises(sqlalchemy.exc.DBAPIError) as exc:
        sesion_de_prueba.execute(text("DELETE FROM audit_events WHERE id = :id"), {"id": evento.id})
    assert "AUDIT_EVENT_IMMUTABLE" in str(exc.value)
    sesion_de_prueba.rollback()
    sesion_de_prueba.expire_all()
    assert sesion_de_prueba.get(AuditEvent, evento.id) is not None


def test_imm_03_orm_rechazado(sesion_de_prueba):
    """IMM-03: UPDATE y DELETE por ORM fallan con AUDIT_EVENT_IMMUTABLE y la fila queda intacta."""
    evento = _insertar(sesion_de_prueba)
    original = evento.reason
    evento.reason = "otra"
    with pytest.raises(sqlalchemy.exc.DBAPIError) as exc:
        sesion_de_prueba.commit()
    assert "AUDIT_EVENT_IMMUTABLE" in str(exc.value)
    sesion_de_prueba.rollback()
    sesion_de_prueba.expire_all()

    evento = sesion_de_prueba.get(AuditEvent, evento.id)
    assert evento is not None and evento.reason == original

    sesion_de_prueba.delete(evento)
    with pytest.raises(sqlalchemy.exc.DBAPIError) as exc:
        sesion_de_prueba.commit()
    assert "AUDIT_EVENT_IMMUTABLE" in str(exc.value)
    sesion_de_prueba.rollback()
    sesion_de_prueba.expire_all()
    assert sesion_de_prueba.get(AuditEvent, evento.id) is not None


@pytest.mark.skipif(not PG_URL.startswith("postgresql"), reason="TRUNCATE solo existe en PostgreSQL")
def test_imm_04_truncate_rechazado(sesion_de_prueba):
    """IMM-04: TRUNCATE no vacía audit_events en PostgreSQL; con CASCADE (que salta la clave foránea de las partidas de muestra) falla con AUDIT_EVENT_IMMUTABLE."""
    evento = _insertar(sesion_de_prueba)
    with pytest.raises(sqlalchemy.exc.DBAPIError):
        sesion_de_prueba.execute(text("TRUNCATE audit_events"))
    sesion_de_prueba.rollback()
    sesion_de_prueba.expire_all()
    assert sesion_de_prueba.get(AuditEvent, evento.id) is not None
    with pytest.raises(sqlalchemy.exc.DBAPIError) as exc:
        sesion_de_prueba.execute(text("TRUNCATE audit_events CASCADE"))
    assert "AUDIT_EVENT_IMMUTABLE" in str(exc.value)
    sesion_de_prueba.rollback()
    sesion_de_prueba.expire_all()
    assert sesion_de_prueba.get(AuditEvent, evento.id) is not None


def test_imm_05_segundo_insert_funciona(sesion_de_prueba):
    """IMM-05: tras los rechazos, un segundo INSERT funciona (append-only, no solo-lectura)."""
    _insertar(sesion_de_prueba)
    segundo = AuditEvent(
        action="LOGIN_SUCCESS",
        entity_type="User",
        tenant_id=None,
        event_time=datetime.now(UTC),
    )
    sesion_de_prueba.add(segundo)
    sesion_de_prueba.commit()
    assert sesion_de_prueba.get(AuditEvent, segundo.id) is not None


def test_imm_06_indice_existe(sesion_de_prueba):
    """IMM-06: el índice ix_audit_events_tenant_event_time existe."""
    indices = {item["name"] for item in inspect(sesion_de_prueba.bind).get_indexes("audit_events")}
    assert "ix_audit_events_tenant_event_time" in indices


@pytest.mark.skipif(not PG_URL.startswith("postgresql"), reason="la migración 0061 solo se verifica sobre PostgreSQL")
def test_imm_07_migracion_pg_triggers_indice_y_downgrade():
    """IMM-07: sobre PostgreSQL, la migración instala los tres triggers y el índice; el downgrade los revierte; el re-upgrade los reinstala.

    Patrón de base efímera del módulo test_spec003_migration_0060.
    """
    def _postgres_admin_url():
        return PG_URL.rsplit("/", 1)[0] + "/postgres"

    def _db_url(name):
        return PG_URL.rsplit("/", 1)[0] + "/" + name

    def _crear_base(name):
        engine = create_engine(_postgres_admin_url(), isolation_level="AUTOCOMMIT")
        try:
            with engine.connect() as conn:
                conn.execute(text(f'CREATE DATABASE "{name}"'))
        finally:
            engine.dispose()

    def _borrar_base(name):
        engine = create_engine(_postgres_admin_url(), isolation_level="AUTOCOMMIT")
        try:
            with engine.connect() as conn:
                conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        finally:
            engine.dispose()

    BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nombre = f"kimm_{uuid.uuid4().hex[:8]}"
    _crear_base(nombre)
    try:
        def _alembic(target, comando="upgrade"):
            env = {**os.environ, "KONTROL_DB_URL": _db_url(nombre)}
            env.pop("KONTROL_TEST_DB_URL", None)
            result = subprocess.run(
                orden_alembic(comando, target),
                cwd=BACKEND,
                env=env,
                capture_output=True,
                text=True,
                timeout=900,
            )
            assert result.returncode == 0, (
                f"Alembic {comando} {target} falló:\n"
                f"stdout[-2000:]: {result.stdout[-2000:]}\n"
                f"stderr[-2000:]: {result.stderr[-2000:]}"
            )

        def _rows(statement, **params):
            engine = create_engine(_db_url(nombre))
            try:
                with engine.connect() as conn:
                    result = conn.execute(text(statement), params)
                    return result.fetchall()
            finally:
                engine.dispose()

        def _exec(statement, **params):
            engine = create_engine(_db_url(nombre))
            try:
                with engine.begin() as conn:
                    return conn.execute(text(statement), params)
            finally:
                engine.dispose()

        _alembic("head")

        triggers = _rows(
            "SELECT tgname FROM pg_trigger WHERE tgrelid = 'audit_events'::regclass AND NOT tgisinternal"
        )
        nombres = {fila[0] for fila in triggers}
        assert nombres == {
            "trg_audit_events_no_delete",
            "trg_audit_events_no_truncate",
            "trg_audit_events_no_update",
        }, nombres

        indices = _rows(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'audit_events'"
        )
        assert any(fila[0] == "ix_audit_events_tenant_event_time" for fila in indices)

        ahora = datetime.now(UTC).isoformat()
        fila_id = str(uuid.uuid4())
        _exec(
            "INSERT INTO audit_events (id, action, entity_type, source, event_time, created_at, updated_at) "
            "VALUES (:id, :action, :entity_type, :source, :event_time, :created_at, :updated_at)",
            id=fila_id,
            action="LOGIN_SUCCESS",
            entity_type="User",
            source="API",
            event_time=ahora,
            created_at=ahora,
            updated_at=ahora,
        )
        with pytest.raises(sqlalchemy.exc.DBAPIError) as exc:
            _exec("UPDATE audit_events SET action = 'X' WHERE id = :id", id=fila_id)
        assert "AUDIT_EVENT_IMMUTABLE" in str(exc.value)

        _alembic("0060_spec003_admin_split", comando="downgrade")

        triggers = _rows(
            "SELECT tgname FROM pg_trigger WHERE tgrelid = 'audit_events'::regclass AND NOT tgisinternal"
        )
        assert triggers == [], triggers
        indices = _rows(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'audit_events'"
        )
        assert not any(fila[0] == "ix_audit_events_tenant_event_time" for fila in indices)

        _alembic("head")
        triggers = _rows(
            "SELECT tgname FROM pg_trigger WHERE tgrelid = 'audit_events'::regclass AND NOT tgisinternal"
        )
        nombres = {fila[0] for fila in triggers}
        assert nombres == {
            "trg_audit_events_no_delete",
            "trg_audit_events_no_truncate",
            "trg_audit_events_no_update",
        }, nombres
    finally:
        _borrar_base(nombre)
