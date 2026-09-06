"""Spec 033 — la confirmación independiente deja de ser una idea y pasa a ser una entidad.

`ADR-D0-012` `R-D0-12-1`: la confirmación es «un evento y una entidad distintos
del picking, con su propio actor, momento, resultado y evidencia. **No es un
campo booleano en el pedido**». Un booleano no dice quién verificó, cuándo,
contra qué preparación ni qué encontró, y sin eso el control no es auditable.

Las tres cifras de cada línea —requerida, preparada y verificada— van en
columnas distintas. Colapsarlas borraría justo lo que hace del control un
control: que alguien contó otra vez y pudo encontrar algo distinto.

`companies.confirmation_same_user_allowed` nace en `false` por `R-D0-12-5`, y el
comentario de esa regla explica por qué: «un control cuyo valor por defecto lo
anula no es un control». Ninguna empresa existente se convierte en insegura al
migrar; se convierten todas en seguras, que es el defecto correcto.

Revision ID: 0051_spec033_confirm
Revises: 0050_spec032_pick
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0051_spec033_confirm"
down_revision = "0050_spec032_pick"
branch_labels = None
depends_on = None

MOTIVOS = ("SKU", "CANTIDAD", "PRESENTACION", "CONDICION", "LINEA_FALTANTE", "LINEA_SOBRANTE")


def upgrade() -> None:
    op.add_column("companies", sa.Column("confirmation_same_user_allowed", sa.Boolean(),
                                         nullable=False, server_default=sa.text("false")))

    op.create_table(
        "order_confirmations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("sales_orders.id"), nullable=False),
        sa.Column("picklist_id", sa.String(36), sa.ForeignKey("pick_lists.id"), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("checked_by", sa.String(36), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('CONFIRMED', 'REJECTED')", name="order_confirmation_status"),
    )
    op.create_index("ix_order_confirmations_company_id", "order_confirmations", ["company_id"])
    op.create_index("ix_order_confirmations_order_id", "order_confirmations", ["order_id"])
    op.create_index("ix_order_confirmations_picklist_id", "order_confirmations", ["picklist_id"])
    op.execute("CREATE UNIQUE INDEX uq_order_confirmations_confirmed "
               "ON order_confirmations (order_id) WHERE status = 'CONFIRMED'")

    op.create_table(
        "order_confirmation_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("confirmation_id", sa.String(36), sa.ForeignKey("order_confirmations.id"), nullable=False),
        sa.Column("order_line_id", sa.String(36), sa.ForeignKey("sales_order_lines.id"), nullable=True),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("required_base_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("prepared_base_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("checked_base_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("presentation_id", sa.String(36), sa.ForeignKey("presentations.id"), nullable=True),
        sa.Column("presentation_ok", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("condition_ok", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("conforms", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("difference_kind", sa.String(32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "difference_kind IS NULL OR difference_kind IN ('" + "', '".join(MOTIVOS) + "')",
            name="order_confirmation_line_difference_kind"),
        # Una línea que no conforma sin decir en qué dimensión no es evidencia.
        sa.CheckConstraint("conforms = true OR difference_kind IS NOT NULL",
                           name="order_confirmation_line_reason"),
    )
    op.create_index("ix_order_confirmation_lines_confirmation_id", "order_confirmation_lines",
                    ["confirmation_id"])


def downgrade() -> None:
    op.drop_index("ix_order_confirmation_lines_confirmation_id", table_name="order_confirmation_lines")
    op.drop_table("order_confirmation_lines")
    op.execute("DROP INDEX IF EXISTS uq_order_confirmations_confirmed")
    for idx in ("ix_order_confirmations_picklist_id", "ix_order_confirmations_order_id",
                "ix_order_confirmations_company_id"):
        op.drop_index(idx, table_name="order_confirmations")
    op.drop_table("order_confirmations")
    op.drop_column("companies", "confirmation_same_user_allowed")
