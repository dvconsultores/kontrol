"""Migración de DATOS del motor de aprobaciones (Spec 045, F1 permisos + F6 histórico).

Dos cosas, ambas idempotentes:

1. Permisos del recurso `aprobaciones` en instalaciones existentes (lo que el
   seed de setup hace en instalaciones nuevas).
2. Traslado del histórico regulatorio al motor.

Traslada las solicitudes del módulo regulatorio (`regulatory_approval_requests`)
al motor como solicitudes **cerradas**, marcadas `LEGACY_UNVERSIONED`.

Regla de honestidad (FR-045-074, AC-22): esas aprobaciones se tomaron cuando el
motor no existía y **no se sabe qué política se aplicó**. No se inventa una
política retroactiva: se registra explícitamente que se desconoce.

Idempotente: reejecutarla no duplica solicitudes.

Revision ID: 0016_approvals_backfill
Revises: 0015_approvals
Create Date: 2026-08-29
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision = "0016_approvals_backfill"
down_revision = "0015_approvals"
branch_labels = None
depends_on = None

LEGACY_VERSION = "LEGACY_UNVERSIONED"
_STATUS_MAP = {
    "APPROVED": "APPROVED",
    "REJECTED": "REJECTED",
    "PENDING": "CANCELLED",  # sin motor, una pendiente histórica no puede resolverse
    "CANCELLED": "CANCELLED",
}


_PERMISSIONS = ["view", "create", "edit", "approve", "delegate", "configure"]


def upgrade() -> None:
    _seed_permissions()
    _migrate_regulatory_history()


def _seed_permissions() -> None:
    """Añade `aprobaciones:*` al rol ADMIN de instalaciones existentes."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "permissions" not in insp.get_table_names():
        return
    admin = bind.execute(
        sa.text("SELECT id FROM roles WHERE code = 'ADMIN' AND company_id IS NULL")
    ).fetchone()
    for action in _PERMISSIONS:
        row = bind.execute(
            sa.text("SELECT id FROM permissions WHERE resource = 'aprobaciones' AND action = :a"),
            {"a": action},
        ).fetchone()
        if row:
            perm_id = row[0]
        else:
            perm_id = str(uuid.uuid4())
            bind.execute(
                sa.text(
                    "INSERT INTO permissions (id, resource, action, scope_type) "
                    "VALUES (:id, 'aprobaciones', :a, 'COMPANY')"
                ),
                {"id": perm_id, "a": action},
            )
        if not admin:
            continue
        exists = bind.execute(
            sa.text("SELECT 1 FROM role_permissions WHERE role_id = :r AND permission_id = :p"),
            {"r": admin[0], "p": perm_id},
        ).fetchone()
        if not exists:
            bind.execute(
                sa.text("INSERT INTO role_permissions (id, role_id, permission_id) "
                        "VALUES (:id, :r, :p)"),
                {"id": str(uuid.uuid4()), "r": admin[0], "p": perm_id},
            )


def _migrate_regulatory_history() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "regulatory_approval_requests" not in insp.get_table_names():
        return

    rows = bind.execute(sa.text(
        "SELECT id, company_id, object_ref, requester_id, amount, decision, status, created_at "
        "FROM regulatory_approval_requests"
    )).fetchall()
    now = datetime.now(UTC)

    for row in rows:
        legacy_id = str(row[0])
        already = bind.execute(
            sa.text(
                "SELECT 1 FROM approval_requests WHERE document_type = 'RegulatoryApprovalRequest' "
                "AND document_id = :d"
            ),
            {"d": legacy_id},
        ).fetchone()
        if already:
            continue

        decision = (row[5] or "").upper()
        legacy_status = (row[6] or "PENDING").upper()
        status = _STATUS_MAP.get(decision) or _STATUS_MAP.get(legacy_status, "CANCELLED")

        bind.execute(
            sa.text(
                "INSERT INTO approval_requests "
                "(id, company_id, process_type, document_type, document_id, policy_id, "
                " policy_version, policy_snapshot, fingerprint, fingerprint_fields, amount_base, "
                " base_currency, requested_by, requested_at, status, resolution_reason, "
                " created_at, updated_at) "
                "VALUES (:id, :company, 'REGULATORY_APPROVAL', 'RegulatoryApprovalRequest', :doc, "
                " NULL, :ver, :snap, :fp, :fpf, :amount, NULL, :req_by, :req_at, :status, :reason, "
                " :now, :now)"
            ),
            {
                "id": str(uuid.uuid4()),
                "company": row[1],
                "doc": legacy_id,
                "ver": LEGACY_VERSION,
                "snap": json.dumps({
                    "migrated_from": "regulatory_approval_requests",
                    "legacy_object_ref": row[2],
                    "legacy_decision": row[5],
                    "legacy_status": row[6],
                    "policy": "UNKNOWN — el motor no existía cuando se tomó esta decisión",
                }),
                "fp": LEGACY_VERSION,
                "fpf": json.dumps([]),
                "amount": row[4],
                "req_by": row[3],
                "req_at": row[7],
                "status": status,
                "reason": "Migrada desde el módulo regulatorio (Spec 045 F6). "
                          "Política aplicada desconocida.",
                "now": now,
            },
        )


def downgrade() -> None:
    """Retira sólo el histórico migrado. Los permisos no se retiran."""
    op.get_bind().execute(sa.text(
        "DELETE FROM approval_requests WHERE policy_version = :v"
    ), {"v": LEGACY_VERSION})
