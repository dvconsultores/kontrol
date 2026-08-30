"""Estructura física de almacén (Spec 008, F1).

Crea los 2 catálogos y los 4 tramos intermedios, extiende `warehouses` y
renombra `locations` a `warehouse_locations` conservando los identificadores:
las claves foráneas existentes siguen apuntando a las mismas filas.

Migración de **esquema pura**. La clasificación de referencias huérfanas y la
imposición de las claves foráneas de inventario van en `0018`, que sí lee datos.
Así `0017` sigue siendo válida en modo offline (`alembic upgrade --sql`).

Ninguna zona, tipo, cantidad de tramos ni profundidad se crea aquí: los
catálogos nacen vacíos y la estructura es dato de cada empresa (P8, R-008-3).

Revision ID: 0017_warehouse_structure
Revises: 0016_approvals_backfill
Create Date: 2026-08-30
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0017_warehouse_structure"
down_revision = "0016_approvals_backfill"
branch_labels = None
depends_on = None

_LEVELS = (
    ("warehouse_zones", "zone_id", None),
    ("warehouse_aisles", "zone_id", "warehouse_zones"),
    ("warehouse_racks", "aisle_id", "warehouse_aisles"),
    ("warehouse_levels", "rack_id", "warehouse_racks"),
)


def _catalog(table: str, extra: list[sa.Column]) -> None:
    op.create_table(
        table,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        *extra,
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(f"ix_{table}_company_id", table, ["company_id"])
    op.create_unique_constraint(f"uq_{table}_company_code", table, ["company_id", "code"])


def upgrade() -> None:
    # --- Catálogos por empresa, ambos vacíos ---
    _catalog("zone_types", [sa.Column("description", sa.Text(), nullable=True)])
    _catalog("location_types", [sa.Column("is_storable", sa.Boolean(), nullable=False, server_default=sa.true())])

    # --- Extensión de warehouses ---
    for column in (
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("manager_id", sa.String(36), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location_managed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("structure_levels", sa.JSON(), nullable=True),
        sa.Column("structure_regime", sa.String(16), nullable=False, server_default="INITIAL"),
        sa.Column("code_policy", sa.String(16), nullable=False, server_default="GENERATED"),
        sa.Column("code_pattern", sa.String(120), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
    ):
        op.add_column("warehouses", column)
    op.create_unique_constraint("uq_warehouses_company_code", "warehouses", ["company_id", "code"])
    op.create_index("ix_warehouses_company_status", "warehouses", ["company_id", "status"])

    # --- Los cuatro tramos intermedios ---
    for table, parent_column, parent_table in _LEVELS:
        columns = [
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
            sa.Column("warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id"), nullable=False),
            sa.Column("code", sa.String(64), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
            sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        ]
        if table == "warehouse_zones":
            columns.insert(3, sa.Column("zone_type_id", sa.String(36), sa.ForeignKey("zone_types.id"), nullable=True))
        else:
            columns.insert(3, sa.Column(parent_column, sa.String(36), sa.ForeignKey(f"{parent_table}.id"), nullable=True))
        if table == "warehouse_levels":
            columns.append(sa.Column("height_order", sa.Integer(), nullable=True))
        op.create_table(table, *columns)
        op.create_index(f"ix_{table}_company_id", table, ["company_id"])
        op.create_index(f"ix_{table}_warehouse_id", table, ["warehouse_id"])
        op.create_index(f"ix_{table}_wh_sequence", table, ["warehouse_id", "sequence"])
        op.create_unique_constraint(f"uq_{table}_wh_code", table, ["warehouse_id", "code"])
        if table != "warehouse_zones":
            op.create_index(f"ix_{table}_{parent_column}", table, [parent_column])

    # --- locations -> warehouse_locations, conservando los id ---
    op.rename_table("locations", "warehouse_locations")
    if op.get_bind().dialect.name == "postgresql":
        # PostgreSQL conserva los nombres de índice y restricción al renombrar
        # la tabla; se renombran explícitamente para que el esquema sea
        # reconocible y para no colisionar con nombres futuros.
        op.execute("ALTER INDEX pk_locations RENAME TO pk_warehouse_locations")
        op.execute("ALTER INDEX ix_locations_warehouse_id RENAME TO ix_warehouse_locations_warehouse_id")

    for column in (
        sa.Column("company_id", sa.String(36), nullable=True),
        sa.Column("zone_id", sa.String(36), sa.ForeignKey("warehouse_zones.id"), nullable=True),
        sa.Column("aisle_id", sa.String(36), sa.ForeignKey("warehouse_aisles.id"), nullable=True),
        sa.Column("rack_id", sa.String(36), sa.ForeignKey("warehouse_racks.id"), nullable=True),
        sa.Column("level_id", sa.String(36), sa.ForeignKey("warehouse_levels.id"), nullable=True),
        sa.Column("location_type_id", sa.String(36), sa.ForeignKey("location_types.id"), nullable=True),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("capacity_units", sa.Numeric(18, 3), nullable=True),
        sa.Column("capacity_weight", sa.Numeric(18, 3), nullable=True),
        sa.Column("capacity_uom", sa.String(16), nullable=True),
        sa.Column("barcode", sa.String(120), nullable=True),
        sa.Column("legacy_path", sa.String(200), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
    ):
        op.add_column("warehouse_locations", column)

    # `company_id` se deriva del almacén: es dato existente, no inventado.
    op.execute(
        "UPDATE warehouse_locations SET company_id = ("
        "  SELECT w.company_id FROM warehouses w WHERE w.id = warehouse_locations.warehouse_id)"
    )
    # `warehouse_id` es obligatorio y con clave foránea, luego el almacén
    # siempre existe y `company_id` siempre resuelve: la columna puede quedar
    # NOT NULL sin riesgo de fila huérfana.
    op.alter_column("warehouse_locations", "company_id", existing_type=sa.String(36), nullable=False)
    op.create_foreign_key("fk_warehouse_locations_company", "warehouse_locations",
                          "companies", ["company_id"], ["id"])
    op.create_index("ix_warehouse_locations_company_id", "warehouse_locations", ["company_id"])
    op.create_unique_constraint("uq_warehouse_locations_wh_code", "warehouse_locations",
                                ["warehouse_id", "code"])
    op.create_index("ix_warehouse_locations_wh_status", "warehouse_locations", ["warehouse_id", "status"])
    op.create_index("ix_warehouse_locations_physical_order", "warehouse_locations",
                    ["warehouse_id", "zone_id", "aisle_id", "rack_id", "level_id", "sequence"])
    op.create_index("ix_warehouse_locations_company_code", "warehouse_locations", ["company_id", "code"])
    op.create_index("ix_warehouse_locations_type", "warehouse_locations", ["location_type_id"])


def downgrade() -> None:
    for index in ("ix_warehouse_locations_type", "ix_warehouse_locations_company_code",
                  "ix_warehouse_locations_physical_order", "ix_warehouse_locations_wh_status",
                  "ix_warehouse_locations_company_id"):
        op.drop_index(index, table_name="warehouse_locations")
    op.drop_constraint("uq_warehouse_locations_wh_code", "warehouse_locations", type_="unique")
    op.drop_constraint("fk_warehouse_locations_company", "warehouse_locations", type_="foreignkey")
    for column in ("version", "legacy_path", "barcode", "capacity_uom", "capacity_weight",
                   "capacity_units", "sequence", "name", "location_type_id", "level_id",
                   "rack_id", "aisle_id", "zone_id", "company_id"):
        op.drop_column("warehouse_locations", column)
    op.rename_table("warehouse_locations", "locations")

    for table, _parent_column, _parent_table in reversed(_LEVELS):
        op.drop_table(table)

    op.drop_index("ix_warehouses_company_status", table_name="warehouses")
    op.drop_constraint("uq_warehouses_company_code", "warehouses", type_="unique")
    for column in ("version", "code_pattern", "code_policy", "structure_regime",
                   "structure_levels", "location_managed", "description", "manager_id", "address"):
        op.drop_column("warehouses", column)

    op.drop_table("location_types")
    op.drop_table("zone_types")
