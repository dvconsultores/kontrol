"""Alertas de operaciones atípicas y su revisión por Control Interno (CTL-07)."""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0109_gov_ctl07_alertas"
down_revision = "0108_gov_bud03_04_plan_fuentes"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_alertas": ("view", "review")}
TIPOS_ALERTA = ("DUPLICIDAD", "PROVEEDOR_RELACIONADO", "AUTOAPROBACION", "FRACCIONAMIENTO", "OVERRIDE_FRECUENTE")
RESULTADOS_REVISION = ("SIN_OBSERVACION", "REQUIERE_SEGUIMIENTO")


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _tiempos() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def _conceder_permisos(bind) -> None:
    funcional = bind.execute(
        sa.text("SELECT id FROM roles WHERE code = 'FUNCIONAL_COMPLETO' AND company_id IS NULL LIMIT 1")
    ).fetchone()
    for recurso, acciones in PERMISOS.items():
        for accion in acciones:
            fila = bind.execute(
                sa.text("SELECT id FROM permissions WHERE resource = :r AND action = :a"),
                {"r": recurso, "a": accion},
            ).fetchone()
            if fila:
                permiso = fila[0]
            else:
                permiso = str(uuid.uuid4())
                bind.execute(
                    sa.text(
                        "INSERT INTO permissions (id, resource, action, scope_type) VALUES (:id, :r, :a, 'COMPANY')"
                    ),
                    {"id": permiso, "r": recurso, "a": accion},
                )
            if not funcional:
                continue
            ya = bind.execute(
                sa.text("SELECT 1 FROM role_permissions WHERE role_id = :rol AND permission_id = :p"),
                {"rol": funcional[0], "p": permiso},
            ).fetchone()
            if not ya:
                bind.execute(
                    sa.text("INSERT INTO role_permissions (id, role_id, permission_id) VALUES (:id, :rol, :p)"),
                    {"id": str(uuid.uuid4()), "rol": funcional[0], "p": permiso},
                )


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        "gov_atypical_alert_reviews",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("clave", sa.String(200), nullable=False),
        sa.Column("tipo", sa.String(24), nullable=False),
        sa.Column("resultado", sa.String(24), nullable=False),
        sa.Column("observacion", sa.Text(), nullable=False),
        sa.Column("resumen", sa.String(1000), nullable=False),
        sa.Column("revisada_por", sa.String(36), nullable=False),
        sa.Column("revisada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "clave", name="uq_gov_atypical_alert_reviews_clave"),
        sa.CheckConstraint(f"tipo IN ({_en(*TIPOS_ALERTA)})", name="tipo"),
        sa.CheckConstraint(f"resultado IN ({_en(*RESULTADOS_REVISION)})", name="resultado"),
        sa.CheckConstraint("length(observacion) >= 10", name="observacion"),
    )
    op.create_index("ix_gov_atypical_alert_reviews_company_id", "gov_atypical_alert_reviews", ["company_id"])

    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION kontrol_gov_atypical_alert_review_inmutable()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'GOV_ATYPICAL_ALERT_REVIEW_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP;
            END;
            $$
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_gov_atypical_alert_reviews_no_update
            BEFORE UPDATE ON gov_atypical_alert_reviews
            FOR EACH ROW EXECUTE FUNCTION kontrol_gov_atypical_alert_review_inmutable()
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_gov_atypical_alert_reviews_no_delete
            BEFORE DELETE ON gov_atypical_alert_reviews
            FOR EACH ROW EXECUTE FUNCTION kontrol_gov_atypical_alert_review_inmutable()
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_gov_atypical_alert_reviews_no_truncate
            BEFORE TRUNCATE ON gov_atypical_alert_reviews
            FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_atypical_alert_review_inmutable()
            """
        )

    _conceder_permisos(bind)


def downgrade() -> None:
    bind = op.get_bind()
    for recurso, acciones in PERMISOS.items():
        for accion in acciones:
            permiso = bind.execute(
                sa.text("SELECT id FROM permissions WHERE resource = :r AND action = :a"),
                {"r": recurso, "a": accion},
            ).fetchone()
            if not permiso:
                continue
            bind.execute(
                sa.text("DELETE FROM role_permissions WHERE permission_id = :p"),
                {"p": permiso[0]},
            )
            bind.execute(
                sa.text("DELETE FROM permissions WHERE id = :p"),
                {"p": permiso[0]},
            )
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_gov_atypical_alert_reviews_no_update ON gov_atypical_alert_reviews")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_atypical_alert_reviews_no_delete ON gov_atypical_alert_reviews")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_atypical_alert_reviews_no_truncate ON gov_atypical_alert_reviews")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_atypical_alert_review_inmutable()")
    op.drop_index("ix_gov_atypical_alert_reviews_company_id", table_name="gov_atypical_alert_reviews")
    op.drop_table("gov_atypical_alert_reviews")
