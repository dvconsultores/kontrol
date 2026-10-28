"""Migración Spec 001: inmutabilidad de `audit_events` en la base.

Ancla el contrato FR-001-262 y OD-AUD-05: `audit_events` es append-only. Se
crean disparadores que rechazan UPDATE, DELETE y TRUNCATE en PostgreSQL, y
UPDATE y DELETE en SQLite (SQLite no tiene TRUNCATE). Se añade el índice
`ix_audit_events_tenant_event_time`. La migración no reescribe ninguna fila
existente ni hace backfill.

Revision ID: 0061_spec001_audit_immutability
Revises: 0060_spec003_admin_split
"""
from __future__ import annotations

from alembic import op

revision = "0061_spec001_audit_immutability"
down_revision = "0060_spec003_admin_split"
branch_labels = None
depends_on = None

# Copia congelada del SQL de app/modules/audit/models.py. Una migración no importa
# código vivo. Sin el carácter `%` (Alembic/DDL no aplica formato aquí, pero se
# mantiene el mismo texto del contrato).
_AUDIT_IMMUTABLE_PG: tuple[str, ...] = (
    "CREATE OR REPLACE FUNCTION kontrol_audit_events_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'AUDIT_EVENT_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$",
    "CREATE TRIGGER trg_audit_events_no_update BEFORE UPDATE ON audit_events FOR EACH ROW EXECUTE FUNCTION kontrol_audit_events_inmutable()",
    "CREATE TRIGGER trg_audit_events_no_delete BEFORE DELETE ON audit_events FOR EACH ROW EXECUTE FUNCTION kontrol_audit_events_inmutable()",
    "CREATE TRIGGER trg_audit_events_no_truncate BEFORE TRUNCATE ON audit_events FOR EACH STATEMENT EXECUTE FUNCTION kontrol_audit_events_inmutable()",
)

_AUDIT_IMMUTABLE_SQLITE: tuple[str, ...] = (
    "CREATE TRIGGER trg_audit_events_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'AUDIT_EVENT_IMMUTABLE'); END",
    "CREATE TRIGGER trg_audit_events_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'AUDIT_EVENT_IMMUTABLE'); END",
)


def upgrade() -> None:
    op.create_index("ix_audit_events_tenant_event_time", "audit_events", ["tenant_id", "event_time"])
    dialecto = op.get_bind().dialect.name
    if dialecto == "postgresql":
        for sentencia in _AUDIT_IMMUTABLE_PG:
            op.execute(sentencia)
    elif dialecto == "sqlite":
        for sentencia in _AUDIT_IMMUTABLE_SQLITE:
            op.execute(sentencia)
    else:
        raise RuntimeError(f"Dialecto no soportado para la inmutabilidad de audit_events: {dialecto}")


def downgrade() -> None:
    dialecto = op.get_bind().dialect.name
    if dialecto == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_update ON audit_events")
        op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_delete ON audit_events")
        op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_truncate ON audit_events")
        op.execute("DROP FUNCTION IF EXISTS kontrol_audit_events_inmutable()")
    elif dialecto == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_update")
        op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_delete")
    op.drop_index("ix_audit_events_tenant_event_time", table_name="audit_events")
