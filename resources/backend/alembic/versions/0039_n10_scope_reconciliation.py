"""N10 — se retira una expansión que se quedó a medias, y dos columnas se ajustan.

Revision ID: 0039_n10_scope_reconciliation
Revises: 0038_n8_drop_legacy_scope

La migración `0032` añadió `tenant_id` a cinco tablas afirmando que eran del
tenant, y anunció que el traslado del valor y la retirada de la columna falsa
llegarían «en el backfill y en la contracción». No llegaron, y no por descuido:
N7 revisó la clasificación y **la corrigió**. `currencies`, `exchange_rates` y
`report_definitions` son de empresa —`create_currency` exige empresa, la API
lista por empresa y una prueba de N5 ya demostraba que una moneda de A no sirve
en B—, de modo que el plan de `0032` perdió su motivo para tres de ellas.

Para las otras dos el motivo tampoco se sostuvo: `idempotency_records` guarda
usuario y empresa y su clave es única en toda la instalación;
`legacy_document_references` anota el legado antes de saber de quién es la fila.
Ninguna de las dos tiene por dónde llegar a un tenant.

Resultado: cinco columnas con clave foránea real, vacías, que ningún código
escribe ni lee, y que el ORM nunca declaró. Es exactamente la diferencia entre
lo que KONTROL dice que es y lo que hace, que es lo que N10 existe para cerrar.
Se retiran. La historia no se borra: `0032` sigue en el árbol y su `downgrade`
las devuelve.

Y dos columnas de licenciamiento que el ORM declara obligatorias desde `0010`
mientras la base las dejaba nulas. Se ajusta la base al contrato, que es el que
el código da por cierto: ambas son objetos JSON con valor por defecto.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0039_n10_scope_reconciliation"
down_revision = "0038_n8_drop_legacy_scope"
branch_labels = None
depends_on = None

#: Las cinco de `0032`. La clave foránea se llama igual que allí la creó.
TABLAS = (
    "currencies",
    "exchange_rates",
    "idempotency_records",
    "legacy_document_references",
    "report_definitions",
)

#: Tabla, columna y valor con el que se rellena lo que hubiera quedado nulo.
OBLIGATORIAS = (
    ("license_central_config", "sync_policy"),
    ("license_entitlement_snapshots", "modules"),
)


def upgrade() -> None:
    for tabla in TABLAS:
        op.drop_constraint(f"fk_{tabla}_tenant_id", tabla, type_="foreignkey")
        op.drop_column(tabla, "tenant_id")

    for tabla, columna in OBLIGATORIAS:
        # Vacías en una instalación nueva; en una existente, un objeto vacío es
        # lo que el ORM habría escrito con su `default=dict`.
        op.execute(f"UPDATE {tabla} SET {columna} = '{{}}' WHERE {columna} IS NULL")
        op.alter_column(tabla, columna, existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    for tabla, columna in OBLIGATORIAS:
        op.alter_column(tabla, columna, existing_type=sa.JSON(), nullable=True)
    for tabla in TABLAS:
        op.add_column(tabla, sa.Column("tenant_id", sa.String(36), nullable=True))
        op.create_foreign_key(f"fk_{tabla}_tenant_id", tabla, "tenants", ["tenant_id"], ["id"])
