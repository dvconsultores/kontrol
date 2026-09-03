"""Spec 020 — las diferencias de recepción dejan de ser un número suelto.

Revision ID: 0045_spec020_incidents
Revises: 0044_spec019_receipt

La etapa 8 del proceso manda **registrar** las diferencias —faltantes,
sobrantes, daños, referencias incorrectas y diferencias documentales—, la 9
generar su evidencia y la 10 escalarlas a Compras. Hasta ahora no existía nada:
una recepción con diez unidades dañadas solo podía decir `quantity_rejected =
10`, sin tipo, sin evidencia, sin responsable y sin tratamiento.

Esta migración crea `receipt_incidents` y no toca ninguna tabla existente. No
hay datos que migrar: no había incidencias que migrar.

Las restricciones no son adorno. La más importante es la que impide filas a
medio camino: una diferencia documental es del documento y no lleva línea ni
cantidad; las otras cuatro son de mercancía y exigen ambas. Y una incidencia
resuelta sin tratamiento sería una resolución que no dice qué se decidió, que es
justo lo que el contrato prohíbe.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0045_spec020_incidents"
down_revision = "0044_spec019_receipt"
branch_labels = None
depends_on = None


def _log(msg: str) -> None:
    print(f"[0045 spec020] {msg}")


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        "receipt_incidents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("receipt_id", sa.String(36), sa.ForeignKey("goods_receipts.id"), nullable=False),
        sa.Column("receipt_line_id", sa.String(36), sa.ForeignKey("goods_receipt_lines.id"), nullable=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("incident_type", sa.String(32), nullable=False),
        sa.Column("affected_base_quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="REGISTRADA"),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated_by", sa.String(36), nullable=True),
        sa.Column("escalation_notes", sa.Text(), nullable=True),
        sa.Column("resolution", sa.String(32), nullable=True),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(36), nullable=True),
        sa.Column("approval_request_id", sa.String(36), sa.ForeignKey("approval_requests.id"), nullable=True),
        sa.Column("cancelled_reason", sa.Text(), nullable=True),
        # `TimestampMixin` no pone default en Python: lo pone la base. Sin
        # `server_default` la tabla creada por migración rechaza todo insert de
        # la aplicación, aunque la creada por `create_all` funcione.
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
    )
    op.create_index("ix_receipt_incidents_company_id", "receipt_incidents", ["company_id"])
    op.create_index("ix_receipt_incidents_receipt", "receipt_incidents", ["receipt_id"])
    op.create_index("ix_receipt_incidents_line_type", "receipt_incidents",
                    ["receipt_line_id", "incident_type"])
    op.create_unique_constraint("uq_receipt_incidents_company_code", "receipt_incidents",
                                ["company_id", "code"])

    if bind.dialect.name == "postgresql":
        # SQL directo y no `create_check_constraint`: la convención de nombres
        # del metadata duplicaría el prefijo y el nombre dejaría de coincidir
        # con el que declara el ORM (lección de la Spec 030).
        op.execute("ALTER TABLE receipt_incidents ADD CONSTRAINT ck_receipt_incidents_type "
                   "CHECK (incident_type IN ('FALTANTE', 'SOBRANTE', 'DANO', "
                   "'REFERENCIA_INCORRECTA', 'DIFERENCIA_DOCUMENTAL'))")
        op.execute("ALTER TABLE receipt_incidents ADD CONSTRAINT ck_receipt_incidents_status "
                   "CHECK (status IN ('REGISTRADA', 'ESCALADA', 'PENDIENTE_AUTORIZACION', "
                   "'RESUELTA', 'ANULADA'))")
        op.execute("ALTER TABLE receipt_incidents ADD CONSTRAINT ck_receipt_incidents_resolution "
                   "CHECK (resolution IS NULL OR resolution IN ('AJUSTE_AUTORIZADO', "
                   "'RECLAMO_PROVEEDOR', 'INVESTIGACION_INTERNA', 'CUARENTENA'))")
        op.execute("ALTER TABLE receipt_incidents ADD CONSTRAINT "
                   "ck_receipt_incidents_line_and_quantity_by_type CHECK ("
                   "(incident_type = 'DIFERENCIA_DOCUMENTAL' AND receipt_line_id IS NULL "
                   " AND affected_base_quantity IS NULL) "
                   "OR (incident_type <> 'DIFERENCIA_DOCUMENTAL' AND receipt_line_id IS NOT NULL "
                   " AND affected_base_quantity IS NOT NULL))")
        op.execute("ALTER TABLE receipt_incidents ADD CONSTRAINT ck_receipt_incidents_quantity_positive "
                   "CHECK (affected_base_quantity IS NULL OR affected_base_quantity > 0)")
        op.execute("ALTER TABLE receipt_incidents ADD CONSTRAINT "
                   "ck_receipt_incidents_resolved_has_resolution "
                   "CHECK (status <> 'RESUELTA' OR resolution IS NOT NULL)")

    existentes = bind.execute(sa.text("SELECT count(*) FROM goods_receipts")).scalar() or 0
    rechazos = bind.execute(sa.text(
        "SELECT count(*) FROM goods_receipt_lines WHERE quantity_rejected > 0")).scalar() or 0
    _log(f"recepciones existentes: {existentes}; líneas con cantidad rechazada: {rechazos}")
    _log("no se crea ninguna incidencia retroactiva: una cantidad rechazada no dice de qué tipo "
         "fue la diferencia, quién la vio ni cómo se trató. Inventarlo sería falsificar historia")


def downgrade() -> None:
    op.drop_table("receipt_incidents")
