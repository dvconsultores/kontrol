"""N7 — la empresa deja de poder faltar donde siempre está.

Revision ID: 0035_n7_not_null
Revises: 0034_n7_tenant_fk

Nueve tablas de configuración de empresa admitían `company_id` nulo. Se revisó
cada punto de creación de las nueve —plantillas, presentaciones, taxonomías,
atributos, perfiles, tipos de movimiento y perfiles de costo— y **todos** fijan
la empresa, tomándola del contexto validado o del artículo padre. La columna era
anulable por inercia, no porque exista un caso legítimo de ausencia.

Cuatro quedan fuera a propósito y con razón escrita:

- `units_of_measure`: Spec 011 y `OQ-MC-01` establecieron que las unidades del
  sistema son globales y las de negocio son de empresa. El nulo **es** esa
  distinción.
- `stored_files`: un archivo existe antes de saber a qué documento pertenecerá.
- `movement_types` y `costing_profiles`: su API expone `global_scope`, un
  interruptor que crea el tipo o el perfil para toda la instalación en vez de
  para una empresa. El nulo es ese interruptor.

Las dos últimas se descubrieron endureciéndolas y viendo romperse las suites de
ventas y compras. La primera lectura fue que los fixtures estaban mal; leyendo
el contrato resultó ser al revés: la restricción lo estaba.

En una instalación limpia no hay filas nulas. En una con datos, esta migración
fallaría en vez de inventarse una empresa, que es el comportamiento correcto.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0035_n7_not_null"
down_revision = "0034_n7_tenant_fk"
branch_labels = None
depends_on = None

TABLAS = [
    "attribute_definitions",
    "presentations",
    "product_presentation_versions",
    "product_templates",
    "profile_versions",
    "service_templates",
    "taxonomy_nodes",
]


def upgrade() -> None:
    for tabla in TABLAS:
        op.alter_column(tabla, "company_id", existing_type=sa.String(36), nullable=False)


def downgrade() -> None:
    for tabla in TABLAS:
        op.alter_column(tabla, "company_id", existing_type=sa.String(36), nullable=True)
