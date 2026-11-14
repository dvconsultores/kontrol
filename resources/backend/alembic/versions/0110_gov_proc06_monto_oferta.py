"""Monto declarado de la oferta (PROC-06, OMA; OQ-PROC09-01 = A)."""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0110_gov_proc06_monto_oferta"
down_revision = "0109_gov_ctl07_alertas"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_ofertas": ("amount",)}
MONEDAS = ("VES", "USD", "EUR")
SOPORTES = ("DOCUMENTO_OFERTA", "ACTA_APERTURA")


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
        "gov_procurement_offer_amounts",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("offer_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("monto_sin_iva", sa.Numeric(18, 2), nullable=False),
        sa.Column("tributos", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_con_tributos", sa.Numeric(18, 2), nullable=False),
        sa.Column("soporte_tipo", sa.String(16), nullable=False),
        sa.Column("soporte_document_id", sa.String(36), nullable=False),
        sa.Column("soporte_version_id", sa.String(36), nullable=False),
        sa.Column("soporte_sha256", sa.String(64), nullable=False),
        sa.Column("motivo", sa.String(1000), nullable=True),
        sa.Column("reemplaza_id", sa.String(36), nullable=True),
        sa.Column("registrada_por", sa.String(36), nullable=False),
        sa.Column("registrada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["offer_id"], ["gov_procurement_offers.id"]),
        sa.ForeignKeyConstraint(["soporte_document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["soporte_version_id"], ["document_versions.id"]),
        sa.ForeignKeyConstraint(["reemplaza_id"], ["gov_procurement_offer_amounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "offer_id", "version", name="uq_gov_procurement_offer_amounts_version"),
        sa.UniqueConstraint("reemplaza_id", name="uq_gov_procurement_offer_amounts_reemplaza"),
        sa.CheckConstraint("version >= 1", name="version"),
        sa.CheckConstraint(f"moneda IN ({_en(*MONEDAS)})", name="moneda"),
        sa.CheckConstraint("monto_sin_iva >= 0", name="monto_sin_iva"),
        sa.CheckConstraint("tributos >= 0", name="tributos"),
        sa.CheckConstraint("total_con_tributos > 0", name="total_con_tributos"),
        sa.CheckConstraint(f"soporte_tipo IN ({_en(*SOPORTES)})", name="soporte_tipo"),
        sa.CheckConstraint("(version = 1 AND reemplaza_id IS NULL AND motivo IS NULL) OR (version > 1 AND reemplaza_id IS NOT NULL AND motivo IS NOT NULL AND length(motivo) >= 10)", name="correccion"),
    )
    op.create_index("ix_gov_procurement_offer_amounts_company_id", "gov_procurement_offer_amounts", ["company_id"])
    op.create_index("ix_gov_procurement_offer_amounts_offer_id", "gov_procurement_offer_amounts", ["offer_id"])

    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION kontrol_gov_offer_amount_inmutable()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'GOV_OFFER_AMOUNT_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP;
            END;
            $$
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_gov_procurement_offer_amounts_no_update
            BEFORE UPDATE ON gov_procurement_offer_amounts
            FOR EACH ROW EXECUTE FUNCTION kontrol_gov_offer_amount_inmutable()
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_gov_procurement_offer_amounts_no_delete
            BEFORE DELETE ON gov_procurement_offer_amounts
            FOR EACH ROW EXECUTE FUNCTION kontrol_gov_offer_amount_inmutable()
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_gov_procurement_offer_amounts_no_truncate
            BEFORE TRUNCATE ON gov_procurement_offer_amounts
            FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_offer_amount_inmutable()
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
        op.execute("DROP TRIGGER IF EXISTS trg_gov_procurement_offer_amounts_no_update ON gov_procurement_offer_amounts")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_procurement_offer_amounts_no_delete ON gov_procurement_offer_amounts")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_procurement_offer_amounts_no_truncate ON gov_procurement_offer_amounts")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_offer_amount_inmutable()")
    op.drop_index("ix_gov_procurement_offer_amounts_offer_id", table_name="gov_procurement_offer_amounts")
    op.drop_index("ix_gov_procurement_offer_amounts_company_id", table_name="gov_procurement_offer_amounts")
    op.drop_table("gov_procurement_offer_amounts")
