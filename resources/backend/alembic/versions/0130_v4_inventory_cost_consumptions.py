"""V4 · el costo consumido por una salida queda registrado y puede volver.

Hasta aquí una salida de inventario consumía capas de costo y solo guardaba en el
movimiento el costo unitario promedio. Con eso no se podía:

- dar al almacén destino de una transferencia el valor que salió del origen
  (D-INV-TRANSFER-COST): la entrada no creaba capa y el valor se perdía;
- revertir una salida restaurando las capas que consumió, ni revertir una entrada
  retirando exactamente la capa que creó (D-INV-REVERSE-STATE).

Se añade `inventory_cost_consumptions`: una fila por capa consumida y por movimiento,
con el costo base de la capa y su parte de landed cost. Se añade también
`cost_layers.source_movement_id`, el movimiento de entrada que creó la capa.

Backfill: **ninguno.** Las capas y salidas anteriores no se reinterpretan; revertir
un movimiento sin su registro se rechaza con un error explícito en lugar de adivinar
(`AUTOMATIC_HISTORICAL_RECALCULATION=NO`).

Permiso nuevo `inventario:recompute` (D-INV-RECOMPUTE). Se otorga a los roles que ya
podían aprobar inventario, como hizo la Spec 021 con `inventario:confirm`.

Revision ID: 0130_v4_cost_consumptions
Revises: 0129_gov_tre05_retencion
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0130_v4_cost_consumptions"
down_revision = "0129_gov_tre05_retencion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cost_layers", sa.Column("source_movement_id", sa.String(36),
                                           sa.ForeignKey("inventory_movements.id"), nullable=True))
    op.create_index("ix_cost_layers_source_movement_id", "cost_layers", ["source_movement_id"])

    op.create_table(
        "inventory_cost_consumptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("movement_id", sa.String(36), sa.ForeignKey("inventory_movements.id"), nullable=False),
        sa.Column("cost_layer_id", sa.String(36), sa.ForeignKey("cost_layers.id"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 2), nullable=False),
        sa.Column("landed_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("effective_unit_cost", sa.Numeric(18, 6), nullable=False),
        sa.Column("total_cost", sa.Numeric(18, 6), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="VED"),
        sa.Column("fiscal_rate", sa.Numeric(14, 6), nullable=True),
        sa.Column("method", sa.String(16), nullable=False, server_default="AVERAGE"),
        sa.Column("quantity_restored", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.UniqueConstraint("movement_id", "cost_layer_id", name="uq_inventory_cost_consumption_movement_layer"),
        sa.CheckConstraint("quantity > 0", name="ck_inventory_cost_consumption_quantity_positive"),
        sa.CheckConstraint("quantity_restored >= 0 AND quantity_restored <= quantity",
                           name="ck_inventory_cost_consumption_restored_bounds"),
    )
    op.create_index("ix_inventory_cost_consumptions_company_id", "inventory_cost_consumptions", ["company_id"])
    op.create_index("ix_inventory_cost_consumptions_movement_id", "inventory_cost_consumptions", ["movement_id"])
    op.create_index("ix_inventory_cost_consumptions_cost_layer_id", "inventory_cost_consumptions",
                    ["cost_layer_id"])

    conn = op.get_bind()
    existente = conn.execute(sa.text(
        "SELECT id FROM permissions WHERE resource = 'inventario' AND action = 'recompute'")).first()
    if existente is None:
        permiso_id = str(uuid.uuid4())
        conn.execute(sa.text(
            "INSERT INTO permissions (id, resource, action, scope_type, created_at, updated_at) "
            "VALUES (:i, 'inventario', 'recompute', 'COMPANY', now(), now())"), {"i": permiso_id})
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
    # OD-DEL-10: el rol protegido FUNCIONAL_COMPLETO tiene **toda** capacidad funcional
    # del catálogo; se le otorga aunque en esta base aún no tuviera `inventario:approve`.
    funcional = conn.execute(sa.text(
        "INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at) "
        "SELECT gen_random_uuid()::text, r.id, :p, now(), now() FROM roles r "
        "WHERE r.code = 'FUNCIONAL_COMPLETO' AND r.company_id IS NULL AND r.protected IS TRUE "
        "AND NOT EXISTS (SELECT 1 FROM role_permissions y WHERE y.role_id = r.id AND y.permission_id = :p)"),
        {"p": permiso_id}).rowcount
    print(f"[0130 v4] permiso inventario:recompute otorgado a {otorgados} roles "
          f"(los que ya podían aprobar inventario) y a {funcional} rol FUNCIONAL_COMPLETO")


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE resource = 'inventario' AND action = 'recompute')"))
    conn.execute(sa.text("DELETE FROM permissions WHERE resource = 'inventario' AND action = 'recompute'"))
    op.drop_index("ix_inventory_cost_consumptions_cost_layer_id", table_name="inventory_cost_consumptions")
    op.drop_index("ix_inventory_cost_consumptions_movement_id", table_name="inventory_cost_consumptions")
    op.drop_index("ix_inventory_cost_consumptions_company_id", table_name="inventory_cost_consumptions")
    op.drop_table("inventory_cost_consumptions")
    op.drop_index("ix_cost_layers_source_movement_id", table_name="cost_layers")
    op.drop_column("cost_layers", "source_movement_id")
