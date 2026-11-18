"""ORG-04-AUTHORITY-ASSIGNMENT-POLICY: política de asignación configurable por el ente.

Crea la política por figura con versiones, sus competencias permitidas, documentos por etapa e historia inmutable.
La asignación guarda la política y la regla congelada al activarse; `autorizacion_concejo` pasa a
`autorizacion_especial` (la etiqueta la da la regla aplicada). Sin backfill: las asignaciones existentes
conservan su regla histórica (OD-AP-03).
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0125_gov_assignment_policy"
down_revision = "0124_gov_commission_policy"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_ocupacion": ("configure",)}

FIGURAS_ASIGNACION = ("TITULAR", "ENCARGADURIA", "SUPLENCIA", "COMISION_SERVICIO", "DELEGACION_ATRIBUCIONES", "DELEGACION_FIRMA")
ESTADOS_POLITICA_ASIGNACION = ("BORRADOR", "VIGENTE", "CERRADA")
TIPOS_EMISOR_ASIGNACION = ("CUALQUIERA", "CARGO", "COMPETENCIA")
AMBITOS_AUTORIZACION_ASIGNACION = ("TODAS", "MAXIMA_AUTORIDAD")
ETAPAS_DOCUMENTO_ASIGNACION = ("ACTIVACION", "REVOCACION")
EVENTOS_POLITICA_ASIGNACION = ("CREADA", "EDITADA", "ACTIVADA", "CERRADA", "SUSTITUIDA", "NUEVA_VERSION")
MEDIOS_EFICACIA = ("GACETA", "PERSONAL", "PRENSA")
ACCIONES_COMPETENCIA = ("SOLICITAR", "COMPROMETER", "CAUSAR", "ORDENAR_PAGO", "PAGAR", "REGISTRAR", "CUSTODIAR", "APROBAR", "AUDITAR", "FIRMAR")
MATERIAS_COMPETENCIA = ("PRESUPUESTO", "CONTRATACIONES", "TESORERIA", "CONTABILIDAD", "BIENES", "EXPEDIENTE")

HISTORIA_INMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_politica_asignacion_historia_inmutable() RETURNS TRIGGER AS $$ "
    "BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_ASSIGNMENT_POLICY_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_assignment_policy_history_no_update BEFORE UPDATE ON gov_assignment_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_politica_asignacion_historia_inmutable()",
    "CREATE TRIGGER trg_gov_assignment_policy_history_no_delete BEFORE DELETE ON gov_assignment_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_politica_asignacion_historia_inmutable()",
    "CREATE TRIGGER trg_gov_assignment_policy_history_no_truncate BEFORE TRUNCATE ON gov_assignment_policy_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_politica_asignacion_historia_inmutable()",
)

_CAMPOS_FIJOS = (
    "NEW.official_id IS DISTINCT FROM OLD.official_id OR NEW.position_id IS DISTINCT FROM OLD.position_id OR "
    "NEW.figura IS DISTINCT FROM OLD.figura OR NEW.grupo IS DISTINCT FROM OLD.grupo OR "
    "NEW.cargo_origen_id IS DISTINCT FROM OLD.cargo_origen_id OR NEW.act_id IS DISTINCT FROM OLD.act_id OR "
    "NEW.desde IS DISTINCT FROM OLD.desde OR NEW.hasta IS DISTINCT FROM OLD.hasta OR "
    "NEW.fundamento IS DISTINCT FROM OLD.fundamento OR NEW.rendicion IS DISTINCT FROM OLD.rendicion OR "
    "NEW.company_id IS DISTINCT FROM OLD.company_id"
)
_CAMPOS_REGLA = (
    " OR NEW.policy_id IS DISTINCT FROM OLD.policy_id OR NEW.policy_version IS DISTINCT FROM OLD.policy_version"
    " OR NEW.regla::text IS DISTINCT FROM OLD.regla::text"
)


def _no_editable(campos: str) -> str:
    return (
        "CREATE OR REPLACE FUNCTION kontrol_gov_asignacion_no_editable() RETURNS TRIGGER AS $$ "
        f"BEGIN IF OLD.status <> 'BORRADOR' AND ({campos}) THEN "
        "RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_ASSIGNMENT_NOT_EDITABLE'; END IF; "
        "IF OLD.status IN ('REVOCADO','FINALIZADO','DESCARTADO') AND "
        "(NEW.status IS DISTINCT FROM OLD.status OR NEW.fin_efectivo IS DISTINCT FROM OLD.fin_efectivo) THEN "
        "RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_ASSIGNMENT_NOT_EDITABLE'; END IF; "
        "RETURN NEW; END; $$ LANGUAGE plpgsql"
    )


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


def _retirar_permisos(bind) -> None:
    for recurso, acciones in PERMISOS.items():
        for accion in acciones:
            fila = bind.execute(
                sa.text("SELECT id FROM permissions WHERE resource = :r AND action = :a"),
                {"r": recurso, "a": accion},
            ).fetchone()
            if not fila:
                continue
            bind.execute(sa.text("DELETE FROM role_permissions WHERE permission_id = :p"), {"p": fila[0]})
            bind.execute(sa.text("DELETE FROM permissions WHERE id = :p"), {"p": fila[0]})


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "gov_assignment_policies",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("numero_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("figura", sa.String(24), nullable=False),
        sa.Column("fundamento", sa.String(2000), nullable=True),
        sa.Column("act_id", sa.String(36), nullable=True),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("estado", sa.String(10), nullable=False, server_default="BORRADOR"),
        sa.Column("exige_fin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("max_dias", sa.Integer(), nullable=True),
        sa.Column("acto_medio", sa.String(16), nullable=True),
        sa.Column("emisor_tipo", sa.String(12), nullable=False, server_default="CUALQUIERA"),
        sa.Column("emisor_position_id", sa.String(36), nullable=True),
        sa.Column("emisor_competencia_accion", sa.String(16), nullable=True),
        sa.Column("emisor_competencia_materia", sa.String(16), nullable=True),
        sa.Column("autorizacion_requerida", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("autorizacion_etiqueta", sa.String(120), nullable=True),
        sa.Column("autorizacion_ambito", sa.String(16), nullable=True),
        sa.Column("autorizacion_mas_de_dias", sa.Integer(), nullable=True),
        sa.Column("prohibe_avocacion", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("version_anterior_id", sa.String(36), nullable=True),
        sa.Column("activada_por", sa.String(36), nullable=True),
        sa.Column("activada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cerrada_por", sa.String(36), nullable=True),
        sa.Column("cerrada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_cierre", sa.String(500), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["act_id"], ["gov_acts.id"]),
        sa.ForeignKeyConstraint(["emisor_position_id"], ["gov_positions.id"]),
        sa.ForeignKeyConstraint(["version_anterior_id"], ["gov_assignment_policies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", "numero_version", name="uq_gov_assignment_policies_version"),
        sa.CheckConstraint(f"estado IN ({_en(*ESTADOS_POLITICA_ASIGNACION)})", name="estado"),
        sa.CheckConstraint(f"figura IN ({_en(*FIGURAS_ASIGNACION)})", name="figura"),
        sa.CheckConstraint(f"acto_medio IS NULL OR acto_medio IN ({_en(*MEDIOS_EFICACIA)})", name="acto_medio"),
        sa.CheckConstraint(f"emisor_tipo IN ({_en(*TIPOS_EMISOR_ASIGNACION)})", name="emisor_tipo"),
        sa.CheckConstraint(
            f"emisor_competencia_accion IS NULL OR emisor_competencia_accion IN ({_en(*ACCIONES_COMPETENCIA)})",
            name="emisor_accion",
        ),
        sa.CheckConstraint(
            f"emisor_competencia_materia IS NULL OR emisor_competencia_materia IN ({_en(*MATERIAS_COMPETENCIA)})",
            name="emisor_materia",
        ),
        sa.CheckConstraint(
            "(emisor_tipo = 'CUALQUIERA' AND emisor_position_id IS NULL AND emisor_competencia_accion IS NULL AND emisor_competencia_materia IS NULL) OR "
            "(emisor_tipo = 'CARGO' AND emisor_position_id IS NOT NULL AND emisor_competencia_accion IS NULL AND emisor_competencia_materia IS NULL) OR "
            "(emisor_tipo = 'COMPETENCIA' AND emisor_position_id IS NULL AND emisor_competencia_accion IS NOT NULL AND emisor_competencia_materia IS NOT NULL)",
            name="emisor",
        ),
        sa.CheckConstraint(
            f"autorizacion_ambito IS NULL OR autorizacion_ambito IN ({_en(*AMBITOS_AUTORIZACION_ASIGNACION)})",
            name="autorizacion_ambito",
        ),
        sa.CheckConstraint(
            "autorizacion_requerida = false OR (autorizacion_etiqueta IS NOT NULL AND autorizacion_ambito IS NOT NULL)",
            name="autorizacion",
        ),
        sa.CheckConstraint("autorizacion_mas_de_dias IS NULL OR autorizacion_mas_de_dias >= 0", name="autorizacion_dias"),
        sa.CheckConstraint("max_dias IS NULL OR max_dias >= 1", name="max_dias"),
        sa.CheckConstraint("numero_version >= 1", name="numero_version"),
        sa.CheckConstraint("version >= 1", name="version"),
        sa.CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        sa.CheckConstraint("estado = 'BORRADOR' OR fundamento IS NOT NULL", name="fundamento"),
        sa.CheckConstraint("estado <> 'CERRADA' OR (cerrada_en IS NOT NULL AND motivo_cierre IS NOT NULL)", name="cerrada"),
    )
    op.create_index("ix_gov_assignment_policies_company_id", "gov_assignment_policies", ["company_id"])
    op.create_index(
        "uq_gov_assignment_policies_vigente",
        "gov_assignment_policies",
        ["company_id", "codigo"],
        unique=True,
        postgresql_where=sa.text("estado = 'VIGENTE'"),
        sqlite_where=sa.text("estado = 'VIGENTE'"),
    )

    op.create_table(
        "gov_assignment_policy_competencies",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("accion", sa.String(16), nullable=False),
        sa.Column("materia", sa.String(16), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_assignment_policies.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_id", "accion", "materia", name="uq_gov_assignment_policy_competencies_par"),
        sa.CheckConstraint(f"accion IN ({_en(*ACCIONES_COMPETENCIA)})", name="accion"),
        sa.CheckConstraint(f"materia IN ({_en(*MATERIAS_COMPETENCIA)})", name="materia"),
    )
    op.create_index("ix_gov_assignment_policy_competencies_policy_id", "gov_assignment_policy_competencies", ["policy_id"])
    op.create_index("ix_gov_assignment_policy_competencies_company_id", "gov_assignment_policy_competencies", ["company_id"])

    op.create_table(
        "gov_assignment_policy_documents",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("document_type_id", sa.String(36), nullable=False),
        sa.Column("etapa", sa.String(12), nullable=False),
        sa.Column("obligatorio", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_assignment_policies.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_id", "document_type_id", "etapa", name="uq_gov_assignment_policy_documents_tipo"),
        sa.CheckConstraint(f"etapa IN ({_en(*ETAPAS_DOCUMENTO_ASIGNACION)})", name="etapa"),
    )
    op.create_index("ix_gov_assignment_policy_documents_policy_id", "gov_assignment_policy_documents", ["policy_id"])
    op.create_index("ix_gov_assignment_policy_documents_company_id", "gov_assignment_policy_documents", ["company_id"])

    op.create_table(
        "gov_assignment_policy_history",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("evento", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("instantanea", sa.JSON(), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_assignment_policies.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(f"evento IN ({_en(*EVENTOS_POLITICA_ASIGNACION)})", name="evento"),
    )
    op.create_index("ix_gov_assignment_policy_history_policy_id", "gov_assignment_policy_history", ["policy_id"])
    op.create_index("ix_gov_assignment_policy_history_company_id", "gov_assignment_policy_history", ["company_id"])

    with op.batch_alter_table("gov_assignments") as batch:
        batch.alter_column("autorizacion_concejo", new_column_name="autorizacion_especial", existing_type=sa.String(200), existing_nullable=True)
        batch.add_column(sa.Column("policy_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("policy_version", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("regla", sa.JSON(), nullable=True))
        batch.create_foreign_key("fk_gov_assignments_policy_id", "gov_assignment_policies", ["policy_id"], ["id"])
    op.create_index("ix_gov_assignments_policy_id", "gov_assignments", ["policy_id"])

    if bind.dialect.name == "postgresql":
        for sentencia in HISTORIA_INMUTABLE_PG:
            op.execute(sentencia)
        op.execute(_no_editable(_CAMPOS_FIJOS + _CAMPOS_REGLA))

    _conceder_permisos(bind)


def downgrade() -> None:
    bind = op.get_bind()
    _retirar_permisos(bind)

    if bind.dialect.name == "postgresql":
        op.execute(_no_editable(_CAMPOS_FIJOS))

    op.drop_index("ix_gov_assignments_policy_id", table_name="gov_assignments")
    with op.batch_alter_table("gov_assignments") as batch:
        batch.drop_constraint("fk_gov_assignments_policy_id", type_="foreignkey")
        batch.drop_column("regla")
        batch.drop_column("policy_version")
        batch.drop_column("policy_id")
        batch.alter_column("autorizacion_especial", new_column_name="autorizacion_concejo", existing_type=sa.String(200), existing_nullable=True)

    for tabla in (
        "gov_assignment_policy_history",
        "gov_assignment_policy_documents",
        "gov_assignment_policy_competencies",
    ):
        op.drop_table(tabla)
    op.drop_index("uq_gov_assignment_policies_vigente", table_name="gov_assignment_policies")
    op.drop_index("ix_gov_assignment_policies_company_id", table_name="gov_assignment_policies")
    op.drop_table("gov_assignment_policies")
