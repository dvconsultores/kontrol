"""Spec 021 — recibir deja de significar disponible.

Hasta aquí, aceptar una recepción escribía el saldo en `DISPONIBLE` y la
mercancía quedaba a la venta sin que nadie la hubiera contado. `R-D0-10-4` lo
prohíbe —«el paso a `DISPONIBLE` desde la cadena de recepción exige liberación
formal»— y el propio `ADR-D0-010` reservó el cambio de comportamiento para esta
Spec. A partir de ahora la aceptación escribe `RECIBIDO` y solo la confirmación
libera.

Backfill: **no se toca el histórico.** Los saldos y movimientos ya escritos en
`DISPONIBLE` lo fueron legítimamente bajo la regla vigente entonces;
reinterpretarlos como `RECIBIDO` inventaría una confirmación que nadie hizo. Las
recepciones anteriores quedan `CONFIRMADA` porque su mercancía **ya está**
disponible: decir lo contrario sería afirmar que hay stock a la venta sin
confirmar, que es justamente lo que esta Spec impide hacia adelante.

Revision ID: 0047_spec021_confirm
Revises: 0046_spec023_state
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0047_spec021_confirm"
down_revision = "0046_spec023_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("goods_receipts", sa.Column("confirmation_status", sa.String(24),
                                              nullable=False, server_default="PENDIENTE"))
    op.add_column("goods_receipts", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("goods_receipts", sa.Column("confirmed_by", sa.String(36), nullable=True))

    for nombre, tipo in (("counted_base_quantity", sa.Numeric(18, 6)),
                         ("counted_at", sa.DateTime(timezone=True)),
                         ("counted_by", sa.String(36)),
                         ("count_difference_kinds", sa.String(200))):
        op.add_column("goods_receipt_lines", sa.Column(nombre, tipo, nullable=True))

    op.create_table(
        "receipt_confirmations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("receipt_id", sa.String(36), sa.ForeignKey("goods_receipts.id"), nullable=False),
        sa.Column("receipt_line_id", sa.String(36), sa.ForeignKey("goods_receipt_lines.id"), nullable=False),
        sa.Column("source_state", sa.String(32), nullable=False),
        sa.Column("target_state", sa.String(32), nullable=False),
        sa.Column("base_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("movement_id", sa.String(36), sa.ForeignKey("inventory_movements.id"), nullable=True),
        sa.Column("incident_id", sa.String(36), sa.ForeignKey("receipt_incidents.id"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_receipt_confirmations_receipt", "receipt_confirmations", ["receipt_id"])
    op.create_index("ix_receipt_confirmations_line", "receipt_confirmations", ["receipt_line_id"])
    op.execute("ALTER TABLE receipt_confirmations ADD CONSTRAINT "
               "ck_receipt_confirmations_quantity_positive CHECK (base_quantity > 0)")
    op.execute("ALTER TABLE receipt_confirmations ADD CONSTRAINT "
               "ck_receipt_confirmations_target_state CHECK (target_state IN ('DISPONIBLE', 'RECHAZADO'))")
    op.execute("ALTER TABLE receipt_confirmations ADD CONSTRAINT "
               "ck_receipt_confirmations_source_state CHECK (source_state IN ('RECIBIDO', 'CUARENTENA'))")

    conn = op.get_bind()

    previas = conn.execute(sa.text(
        "UPDATE goods_receipts SET confirmation_status = 'CONFIRMADA' "
        "WHERE status IN ('ACCEPTED', 'PARTIALLY_ACCEPTED', 'CLOSED')")).rowcount
    print(f"[0047 spec021] recepciones ya aceptadas marcadas como confirmadas: {previas}")
    print("[0047 spec021] su mercancía ya está en DISPONIBLE bajo la regla vigente entonces; "
          "dejarlas pendientes afirmaría que hay stock a la venta sin confirmar")

    # El permiso nuevo, para que las instalaciones existentes puedan confirmar.
    # Se otorga a quien ya podía aprobar inventario: confirmar es de ese rol, y
    # crear un rol nuevo sería una decisión de negocio que nadie tomó.
    existente = conn.execute(sa.text(
        "SELECT id FROM permissions WHERE resource = 'inventario' AND action = 'confirm'")).first()
    if existente is None:
        permiso_id = str(uuid.uuid4())
        conn.execute(sa.text(
            "INSERT INTO permissions (id, resource, action, scope_type, created_at, updated_at) "
            "VALUES (:i, 'inventario', 'confirm', 'COMPANY', now(), now())"), {"i": permiso_id})
    else:
        permiso_id = existente[0]

    otorgados = conn.execute(sa.text(
        "INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at) "
        "SELECT gen_random_uuid()::text, rp.role_id, :p, now(), now() FROM role_permissions rp "
        "JOIN permissions x ON x.id = rp.permission_id "
        "WHERE x.resource = 'inventario' AND x.action = 'approve' "
        "AND NOT EXISTS (SELECT 1 FROM role_permissions y "
        "                WHERE y.role_id = rp.role_id AND y.permission_id = :p)"),
        {"p": permiso_id}).rowcount
    print(f"[0047 spec021] permiso inventario:confirm otorgado a {otorgados} roles "
          "(los que ya podían aprobar inventario)")


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE resource = 'inventario' AND action = 'confirm')"))
    conn.execute(sa.text("DELETE FROM permissions WHERE resource = 'inventario' AND action = 'confirm'"))
    op.drop_table("receipt_confirmations")
    for nombre in ("count_difference_kinds", "counted_by", "counted_at", "counted_base_quantity"):
        op.drop_column("goods_receipt_lines", nombre)
    for nombre in ("confirmed_by", "confirmed_at", "confirmation_status"):
        op.drop_column("goods_receipts", nombre)
