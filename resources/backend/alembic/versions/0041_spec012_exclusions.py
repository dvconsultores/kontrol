"""Spec 012 — lo que la base debe impedir por sí sola.

Revision ID: 0041_spec012_exclusions
Revises: 0040_spec012_commercial_masters

Dos invariantes que una comprobación en Python no puede sostener.

**Dos versiones `ACTIVE` de la misma lista no pueden solapar vigencia**
(`FR-012-005`). Comprobarlo en el servicio pierde ante dos peticiones
simultáneas, y esta casa ya sabe —por la Spec 046— que dos subidas concurrentes
producen dos versiones si nada en la base lo impide. Se resuelve con una
restricción de exclusión sobre el rango de fechas.

El `WHERE status = 'ACTIVE'` es esencial: dos **borradores** sí pueden solapar,
porque un borrador todavía no compite con nadie.

**La unicidad de los ítems** lleva columnas anulables dentro de la clave, y en
SQL `NULL` no es igual a `NULL`: una `UNIQUE` ingenua permitiría duplicados
exactos. Se resuelve con índices únicos parciales, uno por variante —artículo o
categoría—, normalizando los nulos.
"""
from __future__ import annotations

from alembic import op

revision = "0041_spec012_exclusions"
down_revision = "0040_spec012_commercial_masters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conexion = op.get_bind()
    if conexion.dialect.name != "postgresql":
        # SQLite no tiene exclusión ni índices parciales con expresiones
        # equivalentes. Las suites que corren ahí no verifican esta invariante,
        # y la prueba que la comprueba se salta explícitamente: es preferible a
        # fingir que la restricción existe.
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute("""
        ALTER TABLE price_list_versions
        ADD CONSTRAINT ex_price_list_versions_no_overlap
        EXCLUDE USING gist (
            price_list_id WITH =,
            daterange(valid_from, COALESCE(valid_to, 'infinity'::date), '[)') WITH &&
        ) WHERE (status = 'ACTIVE')
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_price_list_items_by_item
        ON price_list_items (
            version_id, item_id,
            COALESCE(presentation_id, ''),
            COALESCE(min_quantity, -1)
        ) WHERE item_id IS NOT NULL
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_price_list_items_by_category
        ON price_list_items (
            version_id, category_id,
            COALESCE(presentation_id, ''),
            COALESCE(min_quantity, -1)
        ) WHERE category_id IS NOT NULL
    """)


def downgrade() -> None:
    conexion = op.get_bind()
    if conexion.dialect.name != "postgresql":
        return
    op.execute("DROP INDEX IF EXISTS uq_price_list_items_by_category")
    op.execute("DROP INDEX IF EXISTS uq_price_list_items_by_item")
    op.execute("ALTER TABLE price_list_versions DROP CONSTRAINT IF EXISTS ex_price_list_versions_no_overlap")
