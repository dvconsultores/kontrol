"""BUD-01/BUD-02: ejercicio presupuestario, niveles, categorías, clasificador versionado y partidas (D-GOV-02)."""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0107_gov_bud01_ejercicio"
down_revision = "0106_open_supply_by_warehouse"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_presupuesto": ("view", "manage", "approve", "close")}


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


TIPOS_HISTORIA = _en(
    'CREADO', 'NIVELES_CONFIGURADOS', 'CATEGORIA_CREADA', 'CATEGORIA_MODIFICADA',
    'CATEGORIA_ELIMINADA', 'CLASIFICADOR_REGISTRADO', 'PROCEDENCIA_MODIFICADA',
    'PARTIDA_CREADA', 'PARTIDA_ELIMINADA', 'PARTIDAS_IMPORTADAS', 'APROBADO',
    'RECONDUCIDO', 'CERRADO', 'PRECOMPROMISO_CAMBIADO',
)


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
        "gov_budget_years",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("anio", sa.SmallInteger(), nullable=False),
        sa.Column("moneda_funcional", sa.String(3), nullable=False),
        sa.Column("estado", sa.String(12), nullable=False, server_default="BORRADOR"),
        sa.Column("precompromiso_activo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("precompromiso_desde", sa.Date(), nullable=True),
        sa.Column("fijado_por", sa.String(36), nullable=True),
        sa.Column("fijado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cerrado_por", sa.String(36), nullable=True),
        sa.Column("cerrado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_cierre", sa.String(500), nullable=True),
        sa.UniqueConstraint("company_id", "anio", name="uq_gov_budget_years_company_id_anio"),
        sa.CheckConstraint("anio BETWEEN 2000 AND 2100", name="ck_gov_budget_years_anio"),
        sa.CheckConstraint(f"estado IN ({_en('BORRADOR', 'APROBADO', 'RECONDUCIDO', 'CERRADO')})", name="ck_gov_budget_years_estado"),
        sa.CheckConstraint("length(moneda_funcional) = 3", name="ck_gov_budget_years_moneda"),
        sa.CheckConstraint(
            "estado = 'BORRADOR' OR (fijado_por IS NOT NULL AND fijado_en IS NOT NULL)",
            name="ck_gov_budget_years_fijado",
        ),
        sa.CheckConstraint(
            "estado <> 'CERRADO' OR (cerrado_por IS NOT NULL AND cerrado_en IS NOT NULL)",
            name="ck_gov_budget_years_cerrado",
        ),
    )
    op.create_index("ix_gov_budget_years_tenant_id", "gov_budget_years", ["tenant_id"])
    op.create_index("ix_gov_budget_years_company_id", "gov_budget_years", ["company_id"])

    op.create_table(
        "gov_budget_year_foundations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("year_id", sa.String(36), sa.ForeignKey("gov_budget_years.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("referencia", sa.String(300), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("documento_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("documento_sha256", sa.String(64), nullable=False),
        sa.Column("huella", sa.String(64), nullable=False),
        sa.Column("fotografia", sa.JSON(), nullable=False),
        sa.CheckConstraint(f"tipo IN ({_en('ORDENANZA', 'RECONDUCCION')})", name="ck_gov_budget_year_foundations_tipo"),
    )
    op.create_index("ix_gov_budget_year_foundations_year_id", "gov_budget_year_foundations", ["year_id"])
    op.create_index("ix_gov_budget_year_foundations_company_id", "gov_budget_year_foundations", ["company_id"])
    op.create_index("ix_gov_budget_year_foundations_documento_id", "gov_budget_year_foundations", ["documento_id"])

    op.create_table(
        "gov_budget_program_levels",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("year_id", sa.String(36), sa.ForeignKey("gov_budget_years.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("orden", sa.SmallInteger(), nullable=False),
        sa.Column("nombre", sa.String(80), nullable=False),
        sa.UniqueConstraint("year_id", "orden", name="uq_gov_budget_program_levels_year_id_orden"),
        sa.UniqueConstraint("year_id", "nombre", name="uq_gov_budget_program_levels_year_id_nombre"),
        sa.CheckConstraint("orden BETWEEN 1 AND 8", name="ck_gov_budget_program_levels_orden"),
    )
    op.create_index("ix_gov_budget_program_levels_year_id", "gov_budget_program_levels", ["year_id"])
    op.create_index("ix_gov_budget_program_levels_company_id", "gov_budget_program_levels", ["company_id"])

    op.create_table(
        "gov_budget_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("year_id", sa.String(36), sa.ForeignKey("gov_budget_years.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("level_id", sa.String(36), sa.ForeignKey("gov_budget_program_levels.id"), nullable=False),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("gov_budget_categories.id"), nullable=True),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("codigo_completo", sa.String(200), nullable=False),
        sa.Column("denominacion", sa.String(300), nullable=False),
        sa.UniqueConstraint("year_id", "codigo_completo", name="uq_gov_budget_categories_year_id_codigo_completo"),
    )
    op.create_index("ix_gov_budget_categories_year_id", "gov_budget_categories", ["year_id"])
    op.create_index("ix_gov_budget_categories_company_id", "gov_budget_categories", ["company_id"])
    op.create_index("ix_gov_budget_categories_level_id", "gov_budget_categories", ["level_id"])
    op.create_index("ix_gov_budget_categories_parent_id", "gov_budget_categories", ["parent_id"])

    op.create_table(
        "gov_budget_classifiers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("year_id", sa.String(36), sa.ForeignKey("gov_budget_years.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("edicion", sa.String(200), nullable=False),
        sa.Column("fecha_edicion", sa.Date(), nullable=True),
        sa.Column("procedencia", sa.String(1000), nullable=False),
        sa.Column("documento_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("documento_sha256", sa.String(64), nullable=True),
    )
    op.create_index("ix_gov_budget_classifiers_year_id", "gov_budget_classifiers", ["year_id"], unique=True)
    op.create_index("ix_gov_budget_classifiers_company_id", "gov_budget_classifiers", ["company_id"])
    op.create_index("ix_gov_budget_classifiers_documento_id", "gov_budget_classifiers", ["documento_id"])

    op.create_table(
        "gov_budget_classifier_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("classifier_id", sa.String(36), sa.ForeignKey("gov_budget_classifiers.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("tipo", sa.String(8), nullable=False),
        sa.Column("codigo", sa.String(40), nullable=False),
        sa.Column("denominacion", sa.String(300), nullable=False),
        sa.Column("nivel", sa.SmallInteger(), nullable=False),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("gov_budget_classifier_items.id"), nullable=True),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.UniqueConstraint(
            "classifier_id", "tipo", "codigo",
            name="uq_gov_budget_classifier_items_classifier_id_tipo_codigo",
        ),
        sa.CheckConstraint(f"tipo IN ({_en('RECURSO', 'EGRESO')})", name="ck_gov_budget_classifier_items_tipo"),
        sa.CheckConstraint("nivel BETWEEN 1 AND 12", name="ck_gov_budget_classifier_items_nivel"),
        sa.CheckConstraint(
            "vigente_hasta IS NULL OR vigente_hasta >= vigente_desde",
            name="ck_gov_budget_classifier_items_vigencia",
        ),
    )
    op.create_index("ix_gov_budget_classifier_items_classifier_id", "gov_budget_classifier_items", ["classifier_id"])
    op.create_index("ix_gov_budget_classifier_items_company_id", "gov_budget_classifier_items", ["company_id"])
    op.create_index("ix_gov_budget_classifier_items_parent_id", "gov_budget_classifier_items", ["parent_id"])

    op.create_table(
        "gov_budget_year_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("year_id", sa.String(36), sa.ForeignKey("gov_budget_years.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("detalle", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            f"tipo IN ({TIPOS_HISTORIA})",
            name="ck_gov_budget_year_history_tipo",
        ),
    )
    op.create_index("ix_gov_budget_year_history_year_id", "gov_budget_year_history", ["year_id"])
    op.create_index("ix_gov_budget_year_history_company_id", "gov_budget_year_history", ["company_id"])

    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_no_borrable()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = 'GOV_BUDGET_YEAR_NOT_DELETABLE', DETAIL = TG_OP;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_budget_years_no_delete
        BEFORE DELETE ON gov_budget_years
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_no_borrable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_budget_years_no_truncate
        BEFORE TRUNCATE ON gov_budget_years
        FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_no_borrable();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_fundamento_inmutable()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = 'GOV_BUDGET_FOUNDATION_IMMUTABLE', DETAIL = TG_OP;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_budget_year_foundations_no_update
        BEFORE UPDATE ON gov_budget_year_foundations
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_fundamento_inmutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_budget_year_foundations_no_delete
        BEFORE DELETE ON gov_budget_year_foundations
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_fundamento_inmutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_budget_year_foundations_no_truncate
        BEFORE TRUNCATE ON gov_budget_year_foundations
        FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_fundamento_inmutable();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_historia_inmutable()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = 'GOV_BUDGET_HISTORY_IMMUTABLE', DETAIL = TG_OP;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_budget_year_history_no_update
        BEFORE UPDATE ON gov_budget_year_history
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_budget_year_history_no_delete
        BEFORE DELETE ON gov_budget_year_history
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_budget_year_history_no_truncate
        BEFORE TRUNCATE ON gov_budget_year_history
        FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio()
        RETURNS TRIGGER AS $$
        DECLARE v varchar;
        BEGIN
            IF TG_OP = 'DELETE' THEN v := OLD.year_id; ELSE v := NEW.year_id; END IF;
            IF (SELECT estado FROM gov_budget_years WHERE id = v) <> 'BORRADOR' THEN
                RAISE EXCEPTION USING ERRCODE = 'P0001',
                    MESSAGE = 'GOV_BUDGET_YEAR_FROZEN', DETAIL = TG_TABLE_NAME;
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_budget_program_levels_frozen
        BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_program_levels
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_budget_categories_frozen
        BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_categories
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_budget_classifiers_frozen
        BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_classifiers
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_congelado_por_clasificador()
        RETURNS TRIGGER AS $$
        DECLARE v_clasificador varchar;
        BEGIN
            IF TG_OP = 'DELETE' THEN v_clasificador := OLD.classifier_id;
            ELSE v_clasificador := NEW.classifier_id; END IF;
            IF (SELECT y.estado
                FROM gov_budget_years y
                JOIN gov_budget_classifiers gc ON gc.year_id = y.id
                WHERE gc.id = v_clasificador) <> 'BORRADOR' THEN
                RAISE EXCEPTION USING ERRCODE = 'P0001',
                    MESSAGE = 'GOV_BUDGET_YEAR_FROZEN', DETAIL = TG_TABLE_NAME;
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_budget_classifier_items_frozen
        BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_classifier_items
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_clasificador();
    """)

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

    op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_classifier_items_frozen ON gov_budget_classifier_items")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_presupuesto_congelado_por_clasificador()")

    op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_classifiers_frozen ON gov_budget_classifiers")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_categories_frozen ON gov_budget_categories")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_program_levels_frozen ON gov_budget_program_levels")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_presupuesto_congelado_por_ejercicio()")

    op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_year_history_no_truncate ON gov_budget_year_history")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_year_history_no_delete ON gov_budget_year_history")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_year_history_no_update ON gov_budget_year_history")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_presupuesto_historia_inmutable()")

    op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_year_foundations_no_truncate ON gov_budget_year_foundations")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_year_foundations_no_delete ON gov_budget_year_foundations")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_year_foundations_no_update ON gov_budget_year_foundations")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_presupuesto_fundamento_inmutable()")

    op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_years_no_truncate ON gov_budget_years")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_years_no_delete ON gov_budget_years")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_presupuesto_no_borrable()")

    op.drop_index("ix_gov_budget_year_history_company_id", table_name="gov_budget_year_history")
    op.drop_index("ix_gov_budget_year_history_year_id", table_name="gov_budget_year_history")
    op.drop_table("gov_budget_year_history")

    op.drop_index("ix_gov_budget_classifier_items_parent_id", table_name="gov_budget_classifier_items")
    op.drop_index("ix_gov_budget_classifier_items_company_id", table_name="gov_budget_classifier_items")
    op.drop_index("ix_gov_budget_classifier_items_classifier_id", table_name="gov_budget_classifier_items")
    op.drop_table("gov_budget_classifier_items")

    op.drop_index("ix_gov_budget_classifiers_documento_id", table_name="gov_budget_classifiers")
    op.drop_index("ix_gov_budget_classifiers_company_id", table_name="gov_budget_classifiers")
    op.drop_index("ix_gov_budget_classifiers_year_id", table_name="gov_budget_classifiers")
    op.drop_table("gov_budget_classifiers")

    op.drop_index("ix_gov_budget_categories_parent_id", table_name="gov_budget_categories")
    op.drop_index("ix_gov_budget_categories_level_id", table_name="gov_budget_categories")
    op.drop_index("ix_gov_budget_categories_company_id", table_name="gov_budget_categories")
    op.drop_index("ix_gov_budget_categories_year_id", table_name="gov_budget_categories")
    op.drop_table("gov_budget_categories")

    op.drop_index("ix_gov_budget_program_levels_company_id", table_name="gov_budget_program_levels")
    op.drop_index("ix_gov_budget_program_levels_year_id", table_name="gov_budget_program_levels")
    op.drop_table("gov_budget_program_levels")

    op.drop_index("ix_gov_budget_year_foundations_documento_id", table_name="gov_budget_year_foundations")
    op.drop_index("ix_gov_budget_year_foundations_company_id", table_name="gov_budget_year_foundations")
    op.drop_index("ix_gov_budget_year_foundations_year_id", table_name="gov_budget_year_foundations")
    op.drop_table("gov_budget_year_foundations")

    op.drop_index("ix_gov_budget_years_company_id", table_name="gov_budget_years")
    op.drop_index("ix_gov_budget_years_tenant_id", table_name="gov_budget_years")
    op.drop_table("gov_budget_years")
