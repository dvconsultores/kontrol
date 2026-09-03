"""Spec 019 — la recepción deja de ser solo contable.

Revision ID: 0044_spec019_receipt
Revises: 0043_spec030_reservation

El DOCX de procesos §2 describe doce etapas de recepción. Ocho son de esta Spec
y solo tres estaban parcialmente cubiertas: existía la recepción **contable**
—qué orden, qué producto, cuánto— y faltaba la **física**: cuándo llegó, cuántos
bultos, contra qué se comparó, qué se vio al inspeccionar y si fue conforme.

Nada de eso se reconstruye después. Cuando el camión se va, la única fuente es
lo que se anotó (`P23`).

Esta migración añade columnas; no toca ninguna existente. Todas nacen anulables
**a propósito**: las recepciones ya registradas no reciben un arribo, unos
bultos ni una conformidad inventados. Se quedan sin ellos y eso es la verdad.

No se añade ningún campo de conformidad: `quality_status` **ya** es el veredicto
de la etapa 7. Lo que faltaba no era el veredicto sino la inspección que lo
sostiene, y eso es lo que estas columnas registran.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0044_spec019_receipt"
down_revision = "0043_spec030_reservation"
branch_labels = None
depends_on = None


def _log(msg: str) -> None:
    print(f"[0044 spec019] {msg}")


CABECERA = (
    # etapa 1 — confirmar arribo
    ("arrival_at", sa.DateTime(timezone=True)),
    ("arrival_confirmed_by", sa.String(36)),
    # etapa 2 — programar descarga
    ("unloading_scheduled_at", sa.DateTime(timezone=True)),
    # etapa 4 — comparar contra las cuatro fuentes
    ("packing_list_ref", sa.String(120)),
    ("supplier_invoice_ref", sa.String(120)),
    ("packing_list_match", sa.Boolean()),
    ("supplier_invoice_match", sa.Boolean()),
    ("order_match", sa.Boolean()),
    ("documentation_match", sa.Boolean()),
    # etapa 5 — inspección visual
    ("inspected_at", sa.DateTime(timezone=True)),
    ("inspected_by", sa.String(36)),
    ("inspection_notes", sa.Text()),
    # etapa 6 — bultos
    ("packages_declared", sa.Integer()),
    ("packages_received", sa.Integer()),
    # etapa 11 — acta
    ("record_issued_at", sa.DateTime(timezone=True)),
    ("record_issued_by", sa.String(36)),
)

LINEA = (
    # etapa 6 — observación física; la incidencia que derive es de la Spec 020
    ("physical_condition", sa.String(24)),
    ("damaged_quantity", sa.Numeric(18, 6)),
    ("damage_notes", sa.Text()),
    ("identification_ok", sa.Boolean()),
    ("reference_ok", sa.Boolean()),
    ("overage_base_quantity", sa.Numeric(18, 6)),
)


def upgrade() -> None:
    bind = op.get_bind()

    for nombre, tipo in CABECERA:
        op.add_column("goods_receipts", sa.Column(nombre, tipo, nullable=True))
    for nombre, tipo in LINEA:
        op.add_column("goods_receipt_lines", sa.Column(nombre, tipo, nullable=True))

    if bind.dialect.name == "postgresql":
        # La conformidad solo admite los tres valores del contrato. Va como
        # restricción y no como convención: un valor libre aquí volvería
        # inservible la etapa 7.
        # Bultos y daño observado no pueden ser negativos.
        op.execute("ALTER TABLE goods_receipts ADD CONSTRAINT ck_goods_receipts_packages_nonneg "
                   "CHECK ((packages_declared IS NULL OR packages_declared >= 0) "
                   "AND (packages_received IS NULL OR packages_received >= 0))")
        op.execute("ALTER TABLE goods_receipt_lines ADD CONSTRAINT ck_goods_receipt_lines_damage_nonneg "
                   "CHECK (damaged_quantity IS NULL OR damaged_quantity >= 0)")

    # -- medición del histórico, sin inventar nada -------------------------- #
    receipts = bind.execute(sa.text("SELECT count(*) FROM goods_receipts")).scalar() or 0
    lineas = bind.execute(sa.text("SELECT count(*) FROM goods_receipt_lines")).scalar() or 0
    sin_base = bind.execute(sa.text(
        "SELECT count(*) FROM goods_receipt_lines WHERE base_quantity_received IS NULL")).scalar() or 0
    aceptadas = bind.execute(sa.text(
        "SELECT count(*) FROM goods_receipts WHERE status IN ('ACCEPTED', 'PARTIALLY_ACCEPTED', 'CLOSED')")).scalar() or 0
    _log(f"recepciones existentes: {receipts} (aceptadas o cerradas: {aceptadas}); líneas: {lineas}")
    _log(f"líneas sin cantidad base: {sin_base} — quedan como están: el arribo, los bultos y la "
         f"conformidad de una recepción pasada no son reconstruibles (P23)")

    if aceptadas:
        _log(f"{aceptadas} recepciones aceptadas conservan su `quality_status`: el veredicto de "
             f"conformidad ya existía y no se duplica")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for tabla, nombre in (
            ("goods_receipt_lines", "ck_goods_receipt_lines_damage_nonneg"),
            ("goods_receipts", "ck_goods_receipts_packages_nonneg"),
        ):
            op.execute(f"ALTER TABLE {tabla} DROP CONSTRAINT IF EXISTS {nombre}")
    for nombre, _ in reversed(LINEA):
        op.drop_column("goods_receipt_lines", nombre)
    for nombre, _ in reversed(CABECERA):
        op.drop_column("goods_receipts", nombre)
