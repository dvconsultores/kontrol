"""CNT-09: política institucional de preaviso de las alertas de vencimiento (GOV-CNT-010)."""

import sqlalchemy as sa
from alembic import op

revision = "0121_gov_cnt09_alertas"
down_revision = "0120_gov_cnt08_expediente"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gov_contract_alert_policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("fuente", sa.String(12), nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("dias_anticipacion", sa.Integer, nullable=True),
        sa.Column("actualizado_por", sa.String(36), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "fuente", name="uq_gov_contract_alert_policies_company_fuente"),
        sa.CheckConstraint("fuente IN ('CONTRATO', 'HITO', 'ENTREGABLE')", name="fuente"),
        sa.CheckConstraint("dias_anticipacion IS NULL OR (dias_anticipacion >= 1 AND dias_anticipacion <= 365)", name="dias"),
        sa.CheckConstraint("activo = false OR dias_anticipacion IS NOT NULL", name="activo_dias"),
    )
    op.create_index("ix_gov_contract_alert_policies_company_id", "gov_contract_alert_policies", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_gov_contract_alert_policies_company_id", table_name="gov_contract_alert_policies")
    op.drop_table("gov_contract_alert_policies")
