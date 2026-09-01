"""N7 — la empresa y el almacén dejan de poder contradecirse.

Revision ID: 0036_n7_consistency
Revises: 0035_n7_not_null

Las cinco tablas de estructura de almacén —zonas, pasillos, estanterías,
niveles y ubicaciones— guardan `company_id` **y** `warehouse_id`. Cada columna
tiene su clave foránea y las dos son válidas por separado, así que hoy nada
impide que una zona diga pertenecer a la empresa A y colgar de un almacén de la
B. Ninguna de las dos referencias está mal; lo que está mal es la combinación.

Se resuelve con una clave foránea **compuesta**: el par (empresa, almacén) tiene
que existir tal cual en `warehouses`. No añade columnas —ambas ya estaban— y no
usa disparadores, que serían lógica escondida en la base para algo que el modelo
relacional expresa por sí solo.

Requiere una clave única `(company_id, id)` en `warehouses` como destino. Es
redundante con la clave primaria en cuanto a unicidad, pero es la que permite
referenciar el par completo.
"""
from __future__ import annotations

from alembic import op

revision = "0036_n7_consistency"
down_revision = "0035_n7_not_null"
branch_labels = None
depends_on = None

#: Estructura interna del almacén, con el nombre real de su clave simple actual.
#: Los nombres se toman del catálogo, no se deducen del patrón: `warehouse_locations`
#: no sigue la misma convención que las otras cuatro.
TABLAS = [
    ("warehouse_zones", "fk_warehouse_zones_warehouse_id_warehouses"),
    ("warehouse_aisles", "fk_warehouse_aisles_warehouse_id_warehouses"),
    ("warehouse_racks", "fk_warehouse_racks_warehouse_id_warehouses"),
    ("warehouse_levels", "fk_warehouse_levels_warehouse_id_warehouses"),
    ("warehouse_locations", "fk_locations_warehouse_id_warehouses"),
]


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_warehouses_company_id", "warehouses", ["company_id", "id"],
    )
    for tabla, clave_simple in TABLAS:
        # La clave simple a `warehouses` se sustituye por la del par: mantener
        # ambas dejaría dos verdades sobre la misma relación.
        op.drop_constraint(clave_simple, tabla, type_="foreignkey")
        op.create_foreign_key(
            f"fk_{tabla}_company_warehouse", tabla, "warehouses",
            ["company_id", "warehouse_id"], ["company_id", "id"],
        )


def downgrade() -> None:
    for tabla, clave_simple in TABLAS:
        op.drop_constraint(f"fk_{tabla}_company_warehouse", tabla, type_="foreignkey")
        op.create_foreign_key(
            clave_simple, tabla, "warehouses", ["warehouse_id"], ["id"],
        )
    op.drop_constraint("uq_warehouses_company_id", "warehouses", type_="unique")
