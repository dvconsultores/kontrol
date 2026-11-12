"""PROC-11: funciones incompatibles del procedimiento de contratación (GOV-PROC-017)."""

import sqlalchemy as sa

from alembic import op

down_revision = "0102_gov_ctl09_actas"
revision = "0103_gov_proc11_sod_funciones"


def upgrade() -> None:
    op.create_table(
        "gov_sod_role_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("proceso", sa.String(10), nullable=False),
        sa.Column("rol_a", sa.String(16), nullable=False),
        sa.Column("rol_b", sa.String(16), nullable=False),
        sa.Column("fundamento", sa.String(1000), nullable=False),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("estado", sa.String(10), nullable=False, server_default="BORRADOR"),
        sa.Column("activada_por", sa.String(36), nullable=True),
        sa.Column("activada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cerrada_por", sa.String(36), nullable=True),
        sa.Column("cerrada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_cierre", sa.String(500), nullable=True),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_sod_role_rules_company_id_codigo"),
        sa.CheckConstraint("estado IN ('BORRADOR', 'VIGENTE', 'CERRADA')", name="ck_gov_sod_role_rules_estado"),
        sa.CheckConstraint("proceso = 'PROC-03'", name="ck_gov_sod_role_rules_proceso"),
        sa.CheckConstraint(
            "rol_a IN ('SOLICITANTE', 'RECEPTOR', 'EVALUADOR', 'ADJUDICADOR')", name="ck_gov_sod_role_rules_rol_a"
        ),
        sa.CheckConstraint(
            "rol_b IN ('SOLICITANTE', 'RECEPTOR', 'EVALUADOR', 'ADJUDICADOR')", name="ck_gov_sod_role_rules_rol_b"
        ),
        sa.CheckConstraint("rol_a <> rol_b", name="ck_gov_sod_role_rules_funciones_distintas"),
        sa.CheckConstraint(
            "vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="ck_gov_sod_role_rules_vigencia"
        ),
        sa.CheckConstraint(
            "estado <> 'VIGENTE' OR (activada_por IS NOT NULL AND activada_en IS NOT NULL)",
            name="ck_gov_sod_role_rules_vigente_con_activacion",
        ),
        sa.CheckConstraint(
            "estado <> 'CERRADA' OR (cerrada_por IS NOT NULL AND cerrada_en IS NOT NULL AND motivo_cierre IS NOT NULL)",
            name="ck_gov_sod_role_rules_cerrada_con_motivo",
        ),
    )
    op.create_index("ix_gov_sod_role_rules_tenant_id", "gov_sod_role_rules", ["tenant_id"])
    op.create_index("ix_gov_sod_role_rules_company_id", "gov_sod_role_rules", ["company_id"])
    op.create_index(
        "uq_gov_sod_role_rules_par_vigente",
        "gov_sod_role_rules",
        ["company_id", "rol_a", "rol_b"],
        unique=True,
        postgresql_where=sa.text("estado = 'VIGENTE'"),
    )

    op.create_table(
        "gov_sod_role_rule_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("rule_id", sa.String(36), sa.ForeignKey("gov_sod_role_rules.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("detalle", sa.JSON(), nullable=True),
        sa.CheckConstraint("tipo IN ('CREADA', 'ACTIVADA', 'CERRADA')", name="ck_gov_sod_role_rule_history_tipo"),
    )
    op.create_index("ix_gov_sod_role_rule_history_rule_id", "gov_sod_role_rule_history", ["rule_id"])
    op.create_index("ix_gov_sod_role_rule_history_company_id", "gov_sod_role_rule_history", ["company_id"])

    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_sod_funcion_no_borrable()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = 'GOV_SOD_ROLE_RULE_NOT_DELETABLE', DETAIL = TG_OP;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_sod_role_rules_no_delete
        BEFORE DELETE ON gov_sod_role_rules
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_sod_funcion_no_borrable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_sod_role_rules_no_truncate
        BEFORE TRUNCATE ON gov_sod_role_rules
        FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_sod_funcion_no_borrable();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_sod_funcion_historia_inmutable()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = 'GOV_SOD_ROLE_RULE_HISTORY_IMMUTABLE', DETAIL = TG_OP;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_sod_role_rule_history_no_update
        BEFORE UPDATE ON gov_sod_role_rule_history
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_sod_funcion_historia_inmutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_sod_role_rule_history_no_delete
        BEFORE DELETE ON gov_sod_role_rule_history
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_sod_funcion_historia_inmutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_sod_role_rule_history_no_truncate
        BEFORE TRUNCATE ON gov_sod_role_rule_history
        FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_sod_funcion_historia_inmutable();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_gov_sod_role_rule_history_no_truncate ON gov_sod_role_rule_history")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_sod_role_rule_history_no_delete ON gov_sod_role_rule_history")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_sod_role_rule_history_no_update ON gov_sod_role_rule_history")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_sod_funcion_historia_inmutable()")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_sod_role_rules_no_truncate ON gov_sod_role_rules")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_sod_role_rules_no_delete ON gov_sod_role_rules")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_sod_funcion_no_borrable()")

    op.drop_index("ix_gov_sod_role_rule_history_company_id", table_name="gov_sod_role_rule_history")
    op.drop_index("ix_gov_sod_role_rule_history_rule_id", table_name="gov_sod_role_rule_history")
    op.drop_table("gov_sod_role_rule_history")
    op.drop_index("uq_gov_sod_role_rules_par_vigente", table_name="gov_sod_role_rules")
    op.drop_index("ix_gov_sod_role_rules_company_id", table_name="gov_sod_role_rules")
    op.drop_index("ix_gov_sod_role_rules_tenant_id", table_name="gov_sod_role_rules")
    op.drop_table("gov_sod_role_rules")
