"""CNT-04: supervisor o responsable del contrato y permiso gobierno_contratos:assign_supervisor (GOV-CNT-004)."""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0117_gov_cnt04_supervisor"
down_revision = "0116_gov_proc08_conversion"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_contratos": ("assign_supervisor",)}


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
                sa.text(
                    "SELECT 1 FROM role_permissions WHERE role_id = :rol AND permission_id = :p"
                ),
                {"rol": funcional[0], "p": permiso},
            ).fetchone()
            if not ya:
                bind.execute(
                    sa.text(
                        "INSERT INTO role_permissions (id, role_id, permission_id) VALUES (:id, :rol, :p)"
                    ),
                    {"id": str(uuid.uuid4()), "rol": funcional[0], "p": permiso},
                )


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        "gov_contract_supervisors",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("contract_id", sa.String(36), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(12), nullable=False, server_default="VIGENTE"),
        sa.Column("official_id", sa.String(36), nullable=False),
        sa.Column("assignment_id", sa.String(36), nullable=False),
        sa.Column("position_id", sa.String(36), nullable=False),
        sa.Column("unit_id", sa.String(36), nullable=False),
        sa.Column("act_id", sa.String(36), nullable=False),
        sa.Column("funcionario_nombre", sa.String(200), nullable=False),
        sa.Column("funcionario_documento", sa.String(40), nullable=False),
        sa.Column("figura", sa.String(24), nullable=False),
        sa.Column("cargo_codigo", sa.String(30), nullable=False),
        sa.Column("cargo_nombre", sa.String(200), nullable=False),
        sa.Column("unidad_nombre", sa.String(250), nullable=False),
        sa.Column("acto_etiqueta", sa.String(400), nullable=False),
        sa.Column("acto_emisor_cargo", sa.String(200), nullable=False),
        sa.Column("desde", sa.Date(), nullable=False),
        sa.Column("hasta", sa.Date(), nullable=True),
        sa.Column("motivo", sa.String(500), nullable=True),
        sa.Column("sustituye_id", sa.String(36), nullable=True),
        sa.Column("sustituida_por_id", sa.String(36), nullable=True),
        sa.Column("registrado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registrado_por", sa.String(36), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["contract_id"], ["gov_contracts.id"]),
        sa.ForeignKeyConstraint(["official_id"], ["gov_officials.id"]),
        sa.ForeignKeyConstraint(["assignment_id"], ["gov_assignments.id"]),
        sa.ForeignKeyConstraint(["position_id"], ["gov_positions.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["gov_units.id"]),
        sa.ForeignKeyConstraint(["act_id"], ["gov_acts.id"]),
        sa.ForeignKeyConstraint(["sustituye_id"], ["gov_contract_supervisors.id"]),
        sa.ForeignKeyConstraint(["sustituida_por_id"], ["gov_contract_supervisors.id"], deferrable=True, initially="DEFERRED"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contract_id", "numero", name="uq_gov_contract_supervisors_numero"),
        sa.CheckConstraint("estado IN ('VIGENTE', 'SUSTITUIDA')", name="estado"),
        sa.CheckConstraint("numero >= 1", name="numero"),
        sa.CheckConstraint("hasta IS NULL OR hasta >= desde", name="vigencia"),
        sa.CheckConstraint("(estado = 'VIGENTE') = (hasta IS NULL AND sustituida_por_id IS NULL)", name="vigente_abierta"),
        sa.CheckConstraint("sustituye_id IS NULL OR motivo IS NOT NULL", name="sustitucion_motivada"),
    )
    op.create_index("ix_gov_contract_supervisors_company_id", "gov_contract_supervisors", ["company_id"])
    op.create_index("ix_gov_contract_supervisors_contract_id", "gov_contract_supervisors", ["contract_id"])
    op.create_index("ix_gov_contract_supervisors_act_id", "gov_contract_supervisors", ["act_id"])
    op.create_index(
        "uq_gov_contract_supervisors_vigente",
        "gov_contract_supervisors",
        ["contract_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'VIGENTE'"),
        sqlite_where=sa.text("estado = 'VIGENTE'"),
    )
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION kontrol_gov_contract_supervisor_guard()
            RETURNS trigger AS $$
            BEGIN
                IF TG_OP IN ('DELETE','TRUNCATE') THEN
                    RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_SUPERVISOR_IMMUTABLE', DETAIL = TG_OP;
                END IF;
                IF TG_OP = 'UPDATE' THEN
                    IF OLD.estado = 'VIGENTE' AND NEW.estado = 'SUSTITUIDA'
                       AND NEW.hasta IS NOT NULL AND NEW.sustituida_por_id IS NOT NULL
                       AND OLD.company_id IS NOT DISTINCT FROM NEW.company_id
                       AND OLD.contract_id IS NOT DISTINCT FROM NEW.contract_id
                       AND OLD.numero IS NOT DISTINCT FROM NEW.numero
                       AND OLD.official_id IS NOT DISTINCT FROM NEW.official_id
                       AND OLD.assignment_id IS NOT DISTINCT FROM NEW.assignment_id
                       AND OLD.position_id IS NOT DISTINCT FROM NEW.position_id
                       AND OLD.unit_id IS NOT DISTINCT FROM NEW.unit_id
                       AND OLD.act_id IS NOT DISTINCT FROM NEW.act_id
                       AND OLD.funcionario_nombre IS NOT DISTINCT FROM NEW.funcionario_nombre
                       AND OLD.funcionario_documento IS NOT DISTINCT FROM NEW.funcionario_documento
                       AND OLD.figura IS NOT DISTINCT FROM NEW.figura
                       AND OLD.cargo_codigo IS NOT DISTINCT FROM NEW.cargo_codigo
                       AND OLD.cargo_nombre IS NOT DISTINCT FROM NEW.cargo_nombre
                       AND OLD.unidad_nombre IS NOT DISTINCT FROM NEW.unidad_nombre
                       AND OLD.acto_etiqueta IS NOT DISTINCT FROM NEW.acto_etiqueta
                       AND OLD.acto_emisor_cargo IS NOT DISTINCT FROM NEW.acto_emisor_cargo
                       AND OLD.desde IS NOT DISTINCT FROM NEW.desde
                       AND OLD.motivo IS NOT DISTINCT FROM NEW.motivo
                       AND OLD.sustituye_id IS NOT DISTINCT FROM NEW.sustituye_id
                       AND OLD.registrado_en IS NOT DISTINCT FROM NEW.registrado_en
                       AND OLD.registrado_por IS NOT DISTINCT FROM NEW.registrado_por
                       AND OLD.created_at IS NOT DISTINCT FROM NEW.created_at
                       AND OLD.created_by IS NOT DISTINCT FROM NEW.created_by
                    THEN
                        RETURN NEW;
                    ELSE
                        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_SUPERVISOR_IMMUTABLE', DETAIL = TG_OP;
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE OR REPLACE TRIGGER trg_gov_contract_supervisors_guard
            BEFORE UPDATE OR DELETE ON gov_contract_supervisors
            FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_supervisor_guard();
            """
        )
        op.execute(
            """
            CREATE OR REPLACE TRIGGER trg_gov_contract_supervisors_no_truncate
            BEFORE TRUNCATE ON gov_contract_supervisors
            FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_supervisor_guard();
            """
        )
    _conceder_permisos(bind)


def downgrade() -> None:
    bind = op.get_bind()
    permisos = bind.execute(
        sa.text("SELECT id FROM permissions WHERE resource = :r AND action = :a"),
        {"r": "gobierno_contratos", "a": "assign_supervisor"},
    ).fetchall()
    for permiso in permisos:
        bind.execute(sa.text("DELETE FROM role_permissions WHERE permission_id = :p"), {"p": permiso[0]})
        bind.execute(sa.text("DELETE FROM permissions WHERE id = :p"), {"p": permiso[0]})
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_gov_contract_supervisors_guard ON gov_contract_supervisors")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_contract_supervisors_no_truncate ON gov_contract_supervisors")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_contract_supervisor_guard()")
    op.drop_index("uq_gov_contract_supervisors_vigente", table_name="gov_contract_supervisors")
    op.drop_index("ix_gov_contract_supervisors_act_id", table_name="gov_contract_supervisors")
    op.drop_index("ix_gov_contract_supervisors_contract_id", table_name="gov_contract_supervisors")
    op.drop_index("ix_gov_contract_supervisors_company_id", table_name="gov_contract_supervisors")
    op.drop_table("gov_contract_supervisors")
