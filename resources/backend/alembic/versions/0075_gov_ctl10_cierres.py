"""gov ctl10 cierres

Crea las políticas de controles de cierre, sus controles y su historia (CTL-10, GOV-CTL-012),
registra `gobierno_cierre:view`, `gobierno_cierre:manage` y `gobierno_cierre:activate` y los concede al rol protegido
FUNCIONAL_COMPLETO de las instalaciones existentes.

Revision ID: 0075_gov_ctl10_cierres
Revises: 0074_gov_tre02_caja
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0075_gov_ctl10_cierres"
down_revision = "0074_gov_tre02_caja"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_cierre": ("view", "manage", "activate")}


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _tiempos() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


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


def _proceso_sod(bind, *procesos: str) -> None:
    """SQL directo en PostgreSQL: `create_check_constraint` duplicaría el prefijo de la convención de nombres."""
    valores = _en(*procesos)
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE gov_sod_rules DROP CONSTRAINT ck_gov_sod_rules_proceso")
        op.execute(f"ALTER TABLE gov_sod_rules ADD CONSTRAINT ck_gov_sod_rules_proceso CHECK (proceso IN ({valores}))")
        return
    with op.batch_alter_table("gov_sod_rules") as batch:
        batch.drop_constraint("ck_gov_sod_rules_proceso", type_="check")
        batch.create_check_constraint("proceso", f"proceso IN ({valores})")


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "gov_closure_policies",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("codigo", sa.String(10), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("accion_cierre", sa.String(32), nullable=False),
        sa.Column("fundamento", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(10), nullable=False, server_default="BORRADOR"),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("activada_por", sa.String(36), nullable=True),
        sa.Column("activada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retirada_por", sa.String(36), nullable=True),
        sa.Column("retirada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_retiro", sa.String(500), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_closure_policies_company_id_codigo"),
        sa.CheckConstraint(f"estado IN ({_en('BORRADOR', 'VIGENTE', 'RETIRADA')})", name="estado"),
        sa.CheckConstraint(
            f"accion_cierre IN ({_en('ORG02_CERRAR_ESTRUCTURA', 'TRE02_CERRAR_PROGRAMA')})",
            name="accion_cierre",
        ),
        sa.CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        sa.CheckConstraint(
            "(estado <> 'VIGENTE' OR (activada_por IS NOT NULL AND activada_en IS NOT NULL))",
            name="vigente_exige_activacion",
        ),
        sa.CheckConstraint(
            "(estado <> 'RETIRADA' OR "
            "(retirada_por IS NOT NULL AND retirada_en IS NOT NULL AND motivo_retiro IS NOT NULL))",
            name="retirada_exige_retiro",
        ),
    )
    op.create_index("ix_gov_closure_policies_tenant_id", "gov_closure_policies", ["tenant_id"])
    op.create_index("ix_gov_closure_policies_company_id", "gov_closure_policies", ["company_id"])
    if bind.dialect.name == "postgresql":
        op.create_index(
            "uq_gov_closure_policies_company_accion_vigente",
            "gov_closure_policies",
            ["company_id", "accion_cierre"],
            unique=True,
            postgresql_where=sa.text("estado = 'VIGENTE'"),
        )
    else:
        op.create_index(
            "uq_gov_closure_policies_company_accion_vigente",
            "gov_closure_policies",
            ["company_id", "accion_cierre"],
            unique=True,
            sqlite_where=sa.text("estado = 'VIGENTE'"),
        )

    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION kontrol_gov_cierre_politica_no_editable() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF OLD.estado IN ('VIGENTE', 'RETIRADA') THEN
                    IF NEW.estado <> 'RETIRADA' OR OLD.estado = 'RETIRADA' OR
                       NEW.nombre IS DISTINCT FROM OLD.nombre OR
                       NEW.fundamento IS DISTINCT FROM OLD.fundamento OR
                       NEW.accion_cierre IS DISTINCT FROM OLD.accion_cierre OR
                       NEW.vigente_desde IS DISTINCT FROM OLD.vigente_desde OR
                       NEW.vigente_hasta IS DISTINCT FROM OLD.vigente_hasta THEN
                        RAISE EXCEPTION 'GOV_CLOSURE_POLICY_NOT_EDITABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP;
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $$
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_closure_policies_no_editar
            BEFORE UPDATE ON gov_closure_policies
            FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cierre_politica_no_editable()
        """)
        op.execute("""
            CREATE OR REPLACE FUNCTION kontrol_gov_cierre_politica_no_borrable() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF OLD.estado <> 'BORRADOR' THEN
                    RAISE EXCEPTION 'GOV_CLOSURE_POLICY_NOT_DELETABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP;
                END IF;
                RETURN OLD;
            END;
            $$
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_closure_policies_no_delete
            BEFORE DELETE ON gov_closure_policies
            FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cierre_politica_no_borrable()
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_closure_policies_no_truncate
            BEFORE TRUNCATE ON gov_closure_policies
            FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_cierre_politica_no_borrable()
        """)

    op.create_table(
        "gov_closure_controls",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("tipo", sa.String(24), nullable=False),
        sa.Column("riesgo_minimo", sa.String(6), nullable=True),
        sa.Column("materialidad", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_closure_policies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_id", "tipo", name="uq_gov_closure_controls_policy_id_tipo"),
        sa.CheckConstraint(
            f"tipo IN ({_en('HALLAZGOS_ABIERTOS', 'ACTOS_SIN_EFICACIA')})",
            name="tipo",
        ),
        sa.CheckConstraint(
            "(tipo = 'ACTOS_SIN_EFICACIA' OR (riesgo_minimo IS NOT NULL "
            "AND riesgo_minimo IN ('ALTO', 'MEDIO', 'BAJO')))",
            name="riesgo_minimo_hallazgos",
        ),
        sa.CheckConstraint(
            "(tipo <> 'ACTOS_SIN_EFICACIA' OR riesgo_minimo IS NULL)",
            name="riesgo_minimo_nulo_actos",
        ),
    )
    op.create_index("ix_gov_closure_controls_tenant_id", "gov_closure_controls", ["tenant_id"])
    op.create_index("ix_gov_closure_controls_company_id", "gov_closure_controls", ["company_id"])
    op.create_index("ix_gov_closure_controls_policy_id", "gov_closure_controls", ["policy_id"])

    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION kontrol_gov_cierre_control_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$
            DECLARE politica_estado TEXT;
            BEGIN
                IF TG_OP = 'UPDATE' OR TG_OP = 'DELETE' THEN
                    SELECT estado INTO politica_estado FROM gov_closure_policies WHERE id = OLD.policy_id;
                ELSE
                    SELECT estado INTO politica_estado FROM gov_closure_policies WHERE id = NEW.policy_id;
                END IF;
                IF politica_estado IS DISTINCT FROM 'BORRADOR' THEN
                    RAISE EXCEPTION 'GOV_CLOSURE_CONTROL_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP;
                END IF;
                IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
                RETURN NEW;
            END;
            $$
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_closure_controls_no_insert
            BEFORE INSERT ON gov_closure_controls
            FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cierre_control_inmutable()
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_closure_controls_no_update
            BEFORE UPDATE ON gov_closure_controls
            FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cierre_control_inmutable()
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_closure_controls_no_delete
            BEFORE DELETE ON gov_closure_controls
            FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cierre_control_inmutable()
        """)

    op.create_table(
        "gov_closure_policy_history",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("evento", sa.String(24), nullable=False),
        sa.Column("detalle", sa.JSON(), nullable=True),
        sa.Column("usuario", sa.String(36), nullable=True),
        sa.Column("instante", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_closure_policies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            f"evento IN ({_en('CREADA', 'ACTUALIZADA', 'CONTROL_ANADIDO', 'CONTROL_RETIRADO', 'ACTIVADA', 'RETIRADA')})",
            name="evento",
        ),
    )
    op.create_index("ix_gov_closure_policy_history_tenant_id", "gov_closure_policy_history", ["tenant_id"])
    op.create_index("ix_gov_closure_policy_history_company_id", "gov_closure_policy_history", ["company_id"])
    op.create_index("ix_gov_closure_policy_history_policy_id", "gov_closure_policy_history", ["policy_id"])

    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION kontrol_gov_cierre_historia_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'GOV_CLOSURE_HISTORY_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP;
            END;
            $$
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_closure_policy_history_no_update
            BEFORE UPDATE ON gov_closure_policy_history
            FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cierre_historia_inmutable()
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_closure_policy_history_no_delete
            BEFORE DELETE ON gov_closure_policy_history
            FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cierre_historia_inmutable()
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_closure_policy_history_no_truncate
            BEFORE TRUNCATE ON gov_closure_policy_history
            FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_cierre_historia_inmutable()
        """)

    _conceder_permisos(bind)
    _proceso_sod(op.get_bind(), "DOC-02", "CTL-06", "TRE-01", "TRE-02", "CTL-10")


def downgrade() -> None:
    _proceso_sod(op.get_bind(), "DOC-02", "CTL-06", "TRE-01", "TRE-02")
    bind = op.get_bind()

    for recurso, acciones in PERMISOS.items():
        for accion in acciones:
            permiso = bind.execute(sa.text(
                "SELECT id FROM permissions WHERE resource = :r AND action = :a"),
                {"r": recurso, "a": accion}).fetchone()
            if not permiso:
                continue
            bind.execute(sa.text(
                "DELETE FROM role_permissions WHERE permission_id = :p"),
                {"p": permiso[0]})
            bind.execute(sa.text(
                "DELETE FROM permissions WHERE id = :p"),
                {"p": permiso[0]})

    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_gov_closure_policy_history_no_update ON gov_closure_policy_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_closure_policy_history_no_delete ON gov_closure_policy_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_closure_policy_history_no_truncate ON gov_closure_policy_history")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_cierre_historia_inmutable()")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_closure_controls_no_insert ON gov_closure_controls")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_closure_controls_no_update ON gov_closure_controls")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_closure_controls_no_delete ON gov_closure_controls")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_cierre_control_inmutable()")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_closure_policies_no_editar ON gov_closure_policies")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_closure_policies_no_delete ON gov_closure_policies")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_closure_policies_no_truncate ON gov_closure_policies")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_cierre_politica_no_editable()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_cierre_politica_no_borrable()")

    op.drop_index("ix_gov_closure_policy_history_policy_id", table_name="gov_closure_policy_history")
    op.drop_index("ix_gov_closure_policy_history_company_id", table_name="gov_closure_policy_history")
    op.drop_index("ix_gov_closure_policy_history_tenant_id", table_name="gov_closure_policy_history")
    op.drop_table("gov_closure_policy_history")

    op.drop_index("ix_gov_closure_controls_policy_id", table_name="gov_closure_controls")
    op.drop_index("ix_gov_closure_controls_company_id", table_name="gov_closure_controls")
    op.drop_index("ix_gov_closure_controls_tenant_id", table_name="gov_closure_controls")
    op.drop_table("gov_closure_controls")

    op.drop_index("uq_gov_closure_policies_company_accion_vigente", table_name="gov_closure_policies")
    op.drop_index("ix_gov_closure_policies_company_id", table_name="gov_closure_policies")
    op.drop_index("ix_gov_closure_policies_tenant_id", table_name="gov_closure_policies")
    op.drop_table("gov_closure_policies")
