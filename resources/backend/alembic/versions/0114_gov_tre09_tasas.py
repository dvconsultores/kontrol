"""TRE-09: tasas oficiales BCV de Gobierno y permisos gobierno_tasas (GOV-TRE-011; N39)."""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0114_gov_tre09_tasas"
down_revision = "0113_gov_bud08_compromiso"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_tasas": ("view", "manage", "approve")}


def _conceder_permisos(bind) -> None:
    funcional = bind.execute(sa.text(
        "SELECT id FROM roles WHERE code = 'FUNCIONAL_COMPLETO' AND company_id IS NULL LIMIT 1")).fetchone()
    for recurso, acciones in PERMISOS.items():
        for accion in acciones:
            fila = bind.execute(sa.text(
                "SELECT id FROM permissions WHERE resource = :r AND action = :a"),
                {"r": recurso, "a": accion}).fetchone()
            if fila:
                permiso = fila[0]
            else:
                permiso = str(uuid.uuid4())
                bind.execute(sa.text(
                    "INSERT INTO permissions (id, resource, action, scope_type) VALUES (:id, :r, :a, 'COMPANY')"),
                    {"id": permiso, "r": recurso, "a": accion})
            if not funcional:
                continue
            ya = bind.execute(sa.text(
                "SELECT 1 FROM role_permissions WHERE role_id = :rol AND permission_id = :p"),
                {"rol": funcional[0], "p": permiso}).fetchone()
            if not ya:
                bind.execute(sa.text(
                    "INSERT INTO role_permissions (id, role_id, permission_id) VALUES (:id, :rol, :p)"),
                    {"id": str(uuid.uuid4()), "rol": funcional[0], "p": permiso})


def upgrade() -> None:
    op.create_table(
        "gov_official_exchange_rates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("moneda_cotizacion", sa.String(3), server_default="VES", nullable=False),
        sa.Column("fecha_efectiva", sa.Date(), nullable=False),
        sa.Column("valor", sa.Numeric(28, 12), nullable=False),
        sa.Column("fuente", sa.String(10), server_default="BCV", nullable=False),
        sa.Column("fuente_referencia", sa.String(300), nullable=False),
        sa.Column("publicada_en", sa.Date(), nullable=True),
        sa.Column("estado", sa.String(12), server_default="BORRADOR", nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("sustituye_id", sa.String(36), sa.ForeignKey("gov_official_exchange_rates.id"), nullable=True),
        sa.Column("motivo_correccion", sa.String(500), nullable=True),
        sa.Column("capturada_por", sa.String(36), nullable=False),
        sa.Column("capturada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("aprobada_por", sa.String(36), nullable=True),
        sa.Column("aprobada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidencia_documento_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("evidencia_sha256", sa.String(64), nullable=True),
        sa.Column("sustituida_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anulada_por", sa.String(36), nullable=True),
        sa.Column("anulada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_anulacion", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.CheckConstraint("moneda IN ('USD', 'EUR')", name="ck_gov_official_exchange_rates_moneda"),
        sa.CheckConstraint("moneda_cotizacion = 'VES'", name="ck_gov_official_exchange_rates_cotizacion"),
        sa.CheckConstraint("fuente = 'BCV'", name="ck_gov_official_exchange_rates_fuente"),
        sa.CheckConstraint("valor > 0", name="ck_gov_official_exchange_rates_valor"),
        sa.CheckConstraint("estado IN ('BORRADOR', 'APROBADA', 'SUSTITUIDA', 'ANULADA')", name="ck_gov_official_exchange_rates_estado"),
        sa.CheckConstraint("version >= 1", name="ck_gov_official_exchange_rates_version"),
        sa.CheckConstraint("publicada_en IS NULL OR publicada_en <= fecha_efectiva", name="ck_gov_official_exchange_rates_publicacion"),
        sa.CheckConstraint("(sustituye_id IS NULL) = (motivo_correccion IS NULL)", name="ck_gov_official_exchange_rates_correccion"),
        sa.CheckConstraint(
            "(estado = 'BORRADOR' AND aprobada_por IS NULL AND aprobada_en IS NULL AND evidencia_documento_id IS NULL AND evidencia_sha256 IS NULL) OR "
            "(estado IN ('APROBADA', 'SUSTITUIDA') AND aprobada_por IS NOT NULL AND aprobada_en IS NOT NULL AND evidencia_documento_id IS NOT NULL AND evidencia_sha256 IS NOT NULL) OR "
            "estado = 'ANULADA'",
            name="ck_gov_official_exchange_rates_aprobacion",
        ),
        sa.CheckConstraint("(estado = 'SUSTITUIDA') = (sustituida_en IS NOT NULL)", name="ck_gov_official_exchange_rates_sustitucion"),
        sa.CheckConstraint(
            "(estado = 'ANULADA' AND anulada_por IS NOT NULL AND anulada_en IS NOT NULL AND motivo_anulacion IS NOT NULL) OR "
            "(estado <> 'ANULADA' AND anulada_por IS NULL AND anulada_en IS NULL AND motivo_anulacion IS NULL)",
            name="ck_gov_official_exchange_rates_anulacion",
        ),
        sa.Index("ix_gov_official_exchange_rates_company_id", "company_id"),
        sa.Index("ix_gov_official_exchange_rates_sustituye_id", "sustituye_id"),
        sa.Index("ix_gov_official_exchange_rates_evidencia_documento_id", "evidencia_documento_id"),
        sa.Index("ix_gov_official_exchange_rates_clave", "company_id", "moneda", "fecha_efectiva"),
    )
    op.create_index(
        "uq_gov_official_exchange_rates_aprobada",
        "gov_official_exchange_rates",
        ["company_id", "moneda", "fecha_efectiva"],
        unique=True,
        postgresql_where=sa.text("estado = 'APROBADA'"),
        sqlite_where=sa.text("estado = 'APROBADA'"),
    )
    op.create_index(
        "uq_gov_official_exchange_rates_borrador",
        "gov_official_exchange_rates",
        ["company_id", "moneda", "fecha_efectiva"],
        unique=True,
        postgresql_where=sa.text("estado = 'BORRADOR'"),
        sqlite_where=sa.text("estado = 'BORRADOR'"),
    )

    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE OR REPLACE FUNCTION kontrol_gov_tasa_oficial_inmutable() RETURNS TRIGGER AS $$ BEGIN IF TG_OP = 'DELETE' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_OFFICIAL_RATE_IMMUTABLE', DETAIL = TG_OP; END IF; IF NEW.company_id IS DISTINCT FROM OLD.company_id OR NEW.moneda IS DISTINCT FROM OLD.moneda OR NEW.moneda_cotizacion IS DISTINCT FROM OLD.moneda_cotizacion OR NEW.fecha_efectiva IS DISTINCT FROM OLD.fecha_efectiva OR NEW.valor IS DISTINCT FROM OLD.valor OR NEW.fuente IS DISTINCT FROM OLD.fuente OR NEW.fuente_referencia IS DISTINCT FROM OLD.fuente_referencia OR NEW.publicada_en IS DISTINCT FROM OLD.publicada_en OR NEW.version IS DISTINCT FROM OLD.version OR NEW.sustituye_id IS DISTINCT FROM OLD.sustituye_id OR NEW.motivo_correccion IS DISTINCT FROM OLD.motivo_correccion OR NEW.capturada_por IS DISTINCT FROM OLD.capturada_por OR NEW.capturada_en IS DISTINCT FROM OLD.capturada_en OR NOT ((OLD.estado = 'BORRADOR' AND NEW.estado IN ('APROBADA', 'ANULADA')) OR (OLD.estado = 'APROBADA' AND NEW.estado IN ('SUSTITUIDA', 'ANULADA'))) OR (OLD.estado <> 'BORRADOR' AND (NEW.aprobada_por IS DISTINCT FROM OLD.aprobada_por OR NEW.aprobada_en IS DISTINCT FROM OLD.aprobada_en OR NEW.evidencia_documento_id IS DISTINCT FROM OLD.evidencia_documento_id OR NEW.evidencia_sha256 IS DISTINCT FROM OLD.evidencia_sha256)) THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_OFFICIAL_RATE_IMMUTABLE', DETAIL = TG_OP; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql")
        op.execute("CREATE TRIGGER trg_gov_official_exchange_rates_inmutable BEFORE UPDATE OR DELETE ON gov_official_exchange_rates FOR EACH ROW EXECUTE FUNCTION kontrol_gov_tasa_oficial_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_official_exchange_rates_no_truncate BEFORE TRUNCATE ON gov_official_exchange_rates FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()")

    _conceder_permisos(op.get_bind())


def downgrade() -> None:
    bind = op.get_bind()

    for recurso, acciones in PERMISOS.items():
        for accion in acciones:
            fila = bind.execute(sa.text(
                "SELECT id FROM permissions WHERE resource = :r AND action = :a"),
                {"r": recurso, "a": accion}).fetchone()
            if fila:
                permiso = fila[0]
                bind.execute(sa.text("DELETE FROM role_permissions WHERE permission_id = :p"), {"p": permiso})
                bind.execute(sa.text("DELETE FROM permissions WHERE id = :p"), {"p": permiso})

    op.execute("DROP TRIGGER IF EXISTS trg_gov_official_exchange_rates_inmutable ON gov_official_exchange_rates")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_official_exchange_rates_no_truncate ON gov_official_exchange_rates")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_tasa_oficial_inmutable()")

    op.drop_index("uq_gov_official_exchange_rates_borrador", table_name="gov_official_exchange_rates")
    op.drop_index("uq_gov_official_exchange_rates_aprobada", table_name="gov_official_exchange_rates")
    op.drop_table("gov_official_exchange_rates")
