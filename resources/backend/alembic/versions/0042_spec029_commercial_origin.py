"""Spec 029 — el precio deja de ser un número sin origen.

Revision ID: 0042_spec029_origin
Revises: 0041_spec012_exclusions

La Spec 012 construyó la autoridad de precio: `resolve_price` devuelve el precio
**y la versión que lo produjo**. Ninguna línea de venta la llamaba, así que la
deuda que la 012 existía para cerrar seguía abierta: `unit_price` era un número
que alguien tecleó.

`P23` — captura temprana. El origen del precio no se pierde: **no se captura**.
Ninguna migración posterior puede repararlo, así que se captura ahora, mientras
todavía se sabe.

Todas las columnas nacen anulables **a propósito**. Las líneas que ya existen no
reciben un origen inventado: se quedan sin él y `pricing_source` lo dice. Elegir
una versión actual solo para rellenar la clave foránea sería falsificar
evidencia histórica, que es peor que no tenerla.

Y `sales_quotes.price_list` —el texto libre— **no se borra**. Es el único rastro
que dejó quien escribió esa cotización.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0042_spec029_origin"
down_revision = "0041_spec012_exclusions"
branch_labels = None
depends_on = None

LINEAS = ("sales_quote_lines", "sales_order_lines")


def upgrade() -> None:
    # -- el precio de la línea deja de truncar el del maestro ---------------- #
    #
    # `price_list_items.unit_price` es `Numeric(18,4)` y la línea de venta era
    # `Numeric(18,2)`: copiar un precio de la lista lo redondeaba en silencio.
    # No es un detalle estético — el origen apuntaría a una versión cuyo precio
    # no coincide con el de la línea, y la evidencia dejaría de cuadrar.
    for tabla in LINEAS:
        op.alter_column(tabla, "unit_price",
                        existing_type=sa.Numeric(18, 2), type_=sa.Numeric(18, 4),
                        existing_nullable=False)

    # -- la lista de precios pasa a ser una referencia ----------------------- #
    op.add_column("sales_quotes",
                  sa.Column("price_list_id", sa.String(36), nullable=True))
    op.create_foreign_key("fk_sales_quotes_price_list_id", "sales_quotes",
                          "price_lists", ["price_list_id"], ["id"])

    # -- el pedido recuerda de qué cotización nació -------------------------- #
    op.add_column("sales_orders",
                  sa.Column("quote_id", sa.String(36), nullable=True))
    op.create_foreign_key("fk_sales_orders_quote_id", "sales_orders",
                          "sales_quotes", ["quote_id"], ["id"])
    # Una cotización produce **un** pedido. Convertir dos veces devuelve el
    # mismo; no crea otro. El índice único parcial es lo que lo garantiza
    # cuando dos peticiones llegan a la vez: una comprobación en Python pierde
    # esa carrera.
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE UNIQUE INDEX uq_sales_orders_quote
            ON sales_orders (quote_id) WHERE quote_id IS NOT NULL
        """)

    # -- el origen comercial, en las dos líneas ------------------------------ #
    for tabla in LINEAS:
        op.add_column(tabla, sa.Column("price_source_version_id", sa.String(36), nullable=True))
        op.add_column(tabla, sa.Column("price_source_item_id", sa.String(36), nullable=True))
        op.add_column(tabla, sa.Column("pricing_source", sa.String(32), nullable=True))
        op.add_column(tabla, sa.Column("resolved_unit_price", sa.Numeric(18, 4), nullable=True))
        op.add_column(tabla, sa.Column("manual_reason", sa.Text(), nullable=True))
        op.add_column(tabla, sa.Column("discount_policy_id", sa.String(36), nullable=True))
        op.add_column(tabla, sa.Column("discount_policy_version", sa.Integer(), nullable=True))
        op.add_column(tabla, sa.Column("discount_approval_request_id", sa.String(36), nullable=True))
        op.add_column(tabla, sa.Column("payment_term_snapshot", sa.JSON(), nullable=True))

        op.create_foreign_key(f"fk_{tabla}_price_source_version", tabla,
                              "price_list_versions", ["price_source_version_id"], ["id"])
        op.create_foreign_key(f"fk_{tabla}_price_source_item", tabla,
                              "price_list_items", ["price_source_item_id"], ["id"])
        op.create_foreign_key(f"fk_{tabla}_discount_policy", tabla,
                              "discount_policies", ["discount_policy_id"], ["id"])
        op.create_foreign_key(f"fk_{tabla}_discount_approval", tabla,
                              "approval_requests", ["discount_approval_request_id"], ["id"])
        op.create_check_constraint(
            f"ck_{tabla}_pricing_source", tabla,
            "pricing_source IS NULL OR pricing_source IN "
            "('RESOLVED','MANUAL_JUSTIFIED','LEGACY_FREETEXT')")
        # Un precio manual sin motivo es un precio sin explicación.
        op.create_check_constraint(
            f"ck_{tabla}_manual_reason", tabla,
            "pricing_source <> 'MANUAL_JUSTIFIED' OR manual_reason IS NOT NULL")
        op.create_index(f"ix_{tabla}_price_source_version", tabla, ["price_source_version_id"])


def downgrade() -> None:
    for tabla in LINEAS:
        op.drop_index(f"ix_{tabla}_price_source_version", tabla)
        op.drop_constraint(f"ck_{tabla}_manual_reason", tabla, type_="check")
        op.drop_constraint(f"ck_{tabla}_pricing_source", tabla, type_="check")
        for fk in ("price_source_version", "price_source_item", "discount_policy",
                   "discount_approval"):
            op.drop_constraint(f"fk_{tabla}_{fk}", tabla, type_="foreignkey")
        for col in ("payment_term_snapshot", "discount_approval_request_id",
                    "discount_policy_version", "discount_policy_id", "manual_reason",
                    "resolved_unit_price", "pricing_source", "price_source_item_id",
                    "price_source_version_id"):
            op.drop_column(tabla, col)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS uq_sales_orders_quote")
    op.drop_constraint("fk_sales_orders_quote_id", "sales_orders", type_="foreignkey")
    op.drop_column("sales_orders", "quote_id")
    op.drop_constraint("fk_sales_quotes_price_list_id", "sales_quotes", type_="foreignkey")
    op.drop_column("sales_quotes", "price_list_id")
    for tabla in LINEAS:
        op.alter_column(tabla, "unit_price",
                        existing_type=sa.Numeric(18, 4), type_=sa.Numeric(18, 2),
                        existing_nullable=False)
