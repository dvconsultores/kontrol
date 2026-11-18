"""PROC-07/PROC-08-COMMISSION-POLICY: política de comisión configurable por el ente.

Crea la política con versiones, sus requisitos de integración, documentos por etapa e historia inmutable.
La comisión guarda la política y la regla congelada; el miembro, la presidencia; la inhibición, su expediente.
La apertura y la recomendación admiten el modo sin comisión (responsables del expediente, OD-CP-02).
Sin backfill: las comisiones existentes conservan su regla histórica (OD-CP-04).
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0124_gov_commission_policy"
down_revision = "0123_gov_bud09_causado"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_comisiones": ("configure",)}

ESTADOS_POLITICA_COMISION = ("BORRADOR", "VIGENTE", "CERRADA")
TIPOS_COMISION_POLITICA = ("PERMANENTE", "TEMPORAL", "CUALQUIERA")
BASES_NORMATIVAS_COMISION = ("LCP_ART14", "NINGUNA")
TIPOS_MAYORIA = ("ABSOLUTE_COUNT", "SIMPLE_MAJORITY", "QUALIFIED_MAJORITY", "UNANIMITY")
BASES_DECISION_COMISION = ("MIEMBROS_CON_VOTO", "ASISTENTES_CON_VOTO")
MEDIOS_EFICACIA = ("GACETA", "PERSONAL", "PRENSA")
FUNCIONES_REQUISITO_COMISION = ("MIEMBRO", "SECRETARIO")
CONDICIONES_REQUISITO_COMISION = ("PRINCIPAL", "SUPLENTE", "CUALQUIERA")
TIPOS_REQUISITO_COMISION = ("AREA", "CARGO", "UNIDAD", "COMPETENCIA", "FUNCIONARIO")
AREAS_COMISION = ("JURIDICA", "TECNICA", "ECONOMICO_FINANCIERA")
ACCIONES_COMPETENCIA = ("SOLICITAR", "COMPROMETER", "CAUSAR", "ORDENAR_PAGO", "PAGAR", "REGISTRAR", "CUSTODIAR", "APROBAR", "AUDITAR", "FIRMAR")
MATERIAS_COMPETENCIA = ("PRESUPUESTO", "CONTRATACIONES", "TESORERIA", "CONTABILIDAD", "BIENES", "EXPEDIENTE")
ETAPAS_DOCUMENTO_COMISION = ("CONSTITUCION", "APERTURA", "RECOMENDACION")
EVENTOS_POLITICA_COMISION = ("CREADA", "EDITADA", "ACTIVADA", "CERRADA", "SUSTITUIDA", "NUEVA_VERSION")
MODOS_ACTUACION_COMISION = ("COMISION", "UNIDAD_CONTRATANTE")
ROLES_RESPONSABLE_EXPEDIENTE = ("RESPONSABLE", "REQUIRENTE", "SUSTANCIACION", "CUSTODIA")

HISTORIA_INMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_politica_comision_historia_inmutable() RETURNS TRIGGER AS $$ "
    "BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_COMMISSION_POLICY_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_commission_policy_history_no_update BEFORE UPDATE ON gov_commission_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_politica_comision_historia_inmutable()",
    "CREATE TRIGGER trg_gov_commission_policy_history_no_delete BEFORE DELETE ON gov_commission_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_politica_comision_historia_inmutable()",
    "CREATE TRIGGER trg_gov_commission_policy_history_no_truncate BEFORE TRUNCATE ON gov_commission_policy_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_politica_comision_historia_inmutable()",
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


def _mayoria(prefijo: str) -> list[sa.CheckConstraint]:
    return [
        sa.CheckConstraint(f"{prefijo}_tipo IN ({_en(*TIPOS_MAYORIA)})", name=f"{prefijo}_tipo"),
        sa.CheckConstraint(f"{prefijo}_tipo <> 'ABSOLUTE_COUNT' OR {prefijo}_cantidad >= 1", name=f"{prefijo}_cantidad"),
        sa.CheckConstraint(
            f"{prefijo}_tipo <> 'QUALIFIED_MAJORITY' OR ({prefijo}_numerador >= 1 AND {prefijo}_denominador >= 1 "
            f"AND 2 * {prefijo}_numerador > {prefijo}_denominador AND {prefijo}_numerador <= {prefijo}_denominador)",
            name=f"{prefijo}_fraccion",
        ),
    ]


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "gov_commission_policies",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("numero_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("tipo_comision", sa.String(16), nullable=False, server_default="CUALQUIERA"),
        sa.Column("aplica_apertura", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("aplica_recomendacion", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("base_normativa", sa.String(16), nullable=False, server_default="LCP_ART14"),
        sa.Column("fundamento", sa.String(2000), nullable=True),
        sa.Column("act_id", sa.String(36), nullable=True),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("estado", sa.String(10), nullable=False, server_default="BORRADOR"),
        sa.Column("min_principales", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_principales", sa.Integer(), nullable=True),
        sa.Column("exige_impar", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("suplente_por_principal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("exige_secretario", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("exige_suplente_secretario", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("exige_presidente", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("quorum_tipo", sa.String(20), nullable=False),
        sa.Column("quorum_cantidad", sa.Integer(), nullable=True),
        sa.Column("quorum_numerador", sa.Integer(), nullable=True),
        sa.Column("quorum_denominador", sa.Integer(), nullable=True),
        sa.Column("decision_tipo", sa.String(20), nullable=False),
        sa.Column("decision_cantidad", sa.Integer(), nullable=True),
        sa.Column("decision_numerador", sa.Integer(), nullable=True),
        sa.Column("decision_denominador", sa.Integer(), nullable=True),
        sa.Column("decision_base", sa.String(20), nullable=False, server_default="MIEMBROS_CON_VOTO"),
        sa.Column("presidente_vota", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("presidente_dirimente", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("acto_requerido", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("acto_medio", sa.String(16), nullable=True),
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
        sa.ForeignKeyConstraint(["version_anterior_id"], ["gov_commission_policies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", "numero_version", name="uq_gov_commission_policies_version"),
        sa.CheckConstraint(f"estado IN ({_en(*ESTADOS_POLITICA_COMISION)})", name="estado"),
        sa.CheckConstraint(f"tipo_comision IN ({_en(*TIPOS_COMISION_POLITICA)})", name="tipo_comision"),
        sa.CheckConstraint(f"base_normativa IN ({_en(*BASES_NORMATIVAS_COMISION)})", name="base_normativa"),
        *_mayoria("quorum"),
        *_mayoria("decision"),
        sa.CheckConstraint(f"decision_base IN ({_en(*BASES_DECISION_COMISION)})", name="decision_base"),
        sa.CheckConstraint(f"acto_medio IS NULL OR acto_medio IN ({_en(*MEDIOS_EFICACIA)})", name="acto_medio"),
        sa.CheckConstraint("numero_version >= 1", name="numero_version"),
        sa.CheckConstraint("version >= 1", name="version"),
        sa.CheckConstraint("aplica_apertura OR aplica_recomendacion", name="aplica"),
        sa.CheckConstraint("min_principales >= 1", name="min_principales"),
        sa.CheckConstraint("max_principales IS NULL OR max_principales >= min_principales", name="max_principales"),
        sa.CheckConstraint("presidente_dirimente = false OR exige_presidente", name="dirimente"),
        sa.CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        sa.CheckConstraint("estado = 'BORRADOR' OR fundamento IS NOT NULL", name="fundamento"),
        sa.CheckConstraint("estado <> 'CERRADA' OR (cerrada_en IS NOT NULL AND motivo_cierre IS NOT NULL)", name="cerrada"),
    )
    op.create_index("ix_gov_commission_policies_company_id", "gov_commission_policies", ["company_id"])
    op.create_index(
        "uq_gov_commission_policies_vigente",
        "gov_commission_policies",
        ["company_id", "codigo"],
        unique=True,
        postgresql_where=sa.text("estado = 'VIGENTE'"),
        sqlite_where=sa.text("estado = 'VIGENTE'"),
    )

    referencia = (
        "(tipo = 'AREA' AND area IS NOT NULL AND position_id IS NULL AND unit_id IS NULL AND competencia_accion IS NULL AND official_id IS NULL) OR "
        "(tipo = 'CARGO' AND position_id IS NOT NULL AND area IS NULL AND unit_id IS NULL AND competencia_accion IS NULL AND official_id IS NULL) OR "
        "(tipo = 'UNIDAD' AND unit_id IS NOT NULL AND area IS NULL AND position_id IS NULL AND competencia_accion IS NULL AND official_id IS NULL) OR "
        "(tipo = 'COMPETENCIA' AND competencia_accion IS NOT NULL AND competencia_materia IS NOT NULL AND area IS NULL AND position_id IS NULL AND unit_id IS NULL AND official_id IS NULL) OR "
        "(tipo = 'FUNCIONARIO' AND official_id IS NOT NULL AND area IS NULL AND position_id IS NULL AND unit_id IS NULL AND competencia_accion IS NULL)"
    )
    op.create_table(
        "gov_commission_policy_requirements",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("etiqueta", sa.String(200), nullable=False),
        sa.Column("funcion", sa.String(16), nullable=False),
        sa.Column("condicion", sa.String(16), nullable=False),
        sa.Column("tipo", sa.String(16), nullable=False),
        sa.Column("area", sa.String(24), nullable=True),
        sa.Column("position_id", sa.String(36), nullable=True),
        sa.Column("unit_id", sa.String(36), nullable=True),
        sa.Column("competencia_accion", sa.String(16), nullable=True),
        sa.Column("competencia_materia", sa.String(16), nullable=True),
        sa.Column("official_id", sa.String(36), nullable=True),
        sa.Column("minimo", sa.Integer(), nullable=False),
        sa.Column("maximo", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_commission_policies.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["position_id"], ["gov_positions.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["gov_units.id"]),
        sa.ForeignKeyConstraint(["official_id"], ["gov_officials.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_id", "orden", name="uq_gov_commission_policy_requirements_orden"),
        sa.CheckConstraint(f"funcion IN ({_en(*FUNCIONES_REQUISITO_COMISION)})", name="funcion"),
        sa.CheckConstraint(f"condicion IN ({_en(*CONDICIONES_REQUISITO_COMISION)})", name="condicion"),
        sa.CheckConstraint(f"tipo IN ({_en(*TIPOS_REQUISITO_COMISION)})", name="tipo"),
        sa.CheckConstraint(f"area IS NULL OR area IN ({_en(*AREAS_COMISION)})", name="area"),
        sa.CheckConstraint(f"competencia_accion IS NULL OR competencia_accion IN ({_en(*ACCIONES_COMPETENCIA)})", name="competencia_accion"),
        sa.CheckConstraint(f"competencia_materia IS NULL OR competencia_materia IN ({_en(*MATERIAS_COMPETENCIA)})", name="competencia_materia"),
        sa.CheckConstraint("orden >= 1", name="orden"),
        sa.CheckConstraint("minimo >= 0", name="minimo"),
        sa.CheckConstraint("maximo IS NULL OR maximo >= minimo", name="maximo"),
        sa.CheckConstraint(referencia, name="referencia"),
    )
    op.create_index("ix_gov_commission_policy_requirements_policy_id", "gov_commission_policy_requirements", ["policy_id"])
    op.create_index("ix_gov_commission_policy_requirements_company_id", "gov_commission_policy_requirements", ["company_id"])

    op.create_table(
        "gov_commission_policy_documents",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("document_type_id", sa.String(36), nullable=False),
        sa.Column("etapa", sa.String(14), nullable=False),
        sa.Column("obligatorio", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("condicion", sa.String(300), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_commission_policies.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_id", "document_type_id", "etapa", name="uq_gov_commission_policy_documents_tipo"),
        sa.CheckConstraint(f"etapa IN ({_en(*ETAPAS_DOCUMENTO_COMISION)})", name="etapa"),
    )
    op.create_index("ix_gov_commission_policy_documents_policy_id", "gov_commission_policy_documents", ["policy_id"])
    op.create_index("ix_gov_commission_policy_documents_company_id", "gov_commission_policy_documents", ["company_id"])

    op.create_table(
        "gov_commission_policy_history",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("evento", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("instantanea", sa.JSON(), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_commission_policies.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(f"evento IN ({_en(*EVENTOS_POLITICA_COMISION)})", name="evento"),
    )
    op.create_index("ix_gov_commission_policy_history_policy_id", "gov_commission_policy_history", ["policy_id"])
    op.create_index("ix_gov_commission_policy_history_company_id", "gov_commission_policy_history", ["company_id"])
    if bind.dialect.name == "postgresql":
        for sentencia in HISTORIA_INMUTABLE_PG:
            op.execute(sentencia)

    with op.batch_alter_table("gov_procurement_committees") as batch:
        batch.add_column(sa.Column("policy_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("policy_version", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("regla", sa.JSON(), nullable=True))
        batch.create_foreign_key("fk_gov_procurement_committees_policy_id", "gov_commission_policies", ["policy_id"], ["id"])
    op.create_index("ix_gov_procurement_committees_policy_id", "gov_procurement_committees", ["policy_id"])

    with op.batch_alter_table("gov_procurement_committee_members") as batch:
        batch.add_column(sa.Column("preside", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_check_constraint("preside", "preside = false OR (funcion = 'MIEMBRO' AND condicion = 'PRINCIPAL')")
    op.create_index(
        "uq_gov_committee_presidente",
        "gov_procurement_committee_members",
        ["committee_id"],
        unique=True,
        postgresql_where=sa.text("fin_efectivo IS NULL AND preside"),
        sqlite_where=sa.text("fin_efectivo IS NULL AND preside"),
    )

    with op.batch_alter_table("gov_procurement_committee_conflicts") as batch:
        batch.add_column(sa.Column("file_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_gov_procurement_committee_conflicts_file_id", "gov_procurement_files", ["file_id"], ["id"])
    op.create_index("ix_gov_procurement_committee_conflicts_file_id", "gov_procurement_committee_conflicts", ["file_id"])

    with op.batch_alter_table("gov_procurement_openings") as batch:
        batch.alter_column("committee_id", existing_type=sa.String(36), nullable=True)
        batch.alter_column("miembros_con_voto", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("asistentes_con_voto", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("quorum_requerido", existing_type=sa.Integer(), nullable=True)
        batch.add_column(sa.Column("modo", sa.String(20), nullable=False, server_default="COMISION"))
        batch.add_column(sa.Column("regla", sa.JSON(), nullable=True))
        batch.create_check_constraint("modo", f"modo IN ({_en(*MODOS_ACTUACION_COMISION)})")
        batch.create_check_constraint(
            "modo_comision",
            "(modo = 'COMISION' AND committee_id IS NOT NULL AND miembros_con_voto IS NOT NULL AND asistentes_con_voto IS NOT NULL AND quorum_requerido IS NOT NULL) OR "
            "(modo = 'UNIDAD_CONTRATANTE' AND committee_id IS NULL AND miembros_con_voto IS NULL AND asistentes_con_voto IS NULL AND quorum_requerido IS NULL)",
        )

    with op.batch_alter_table("gov_procurement_recommendations") as batch:
        batch.alter_column("committee_id", existing_type=sa.String(36), nullable=True)
        batch.add_column(sa.Column("modo", sa.String(20), nullable=False, server_default="COMISION"))
        batch.add_column(sa.Column("regla", sa.JSON(), nullable=True))
        batch.create_check_constraint("modo", f"modo IN ({_en(*MODOS_ACTUACION_COMISION)})")
        batch.create_check_constraint("modo_comision", "(modo = 'COMISION') = (committee_id IS NOT NULL)")

    for tabla, padre, columna, unica in (
        ("gov_procurement_opening_responsibles", "gov_procurement_openings", "opening_id", "uq_gov_procurement_opening_responsibles"),
        ("gov_procurement_recommendation_responsibles", "gov_procurement_recommendations", "recommendation_id", "uq_gov_proc_rec_responsibles"),
    ):
        op.create_table(
            tabla,
            sa.Column("id", sa.String(36), nullable=False),
            *_tiempos(),
            sa.Column("company_id", sa.String(36), nullable=False),
            sa.Column(columna, sa.String(36), nullable=False),
            sa.Column("responsible_id", sa.String(36), nullable=False),
            sa.Column("official_id", sa.String(36), nullable=False),
            sa.Column("rol", sa.String(16), nullable=False),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint([columna], [f"{padre}.id"]),
            sa.ForeignKeyConstraint(["responsible_id"], ["gov_procurement_file_responsibles.id"]),
            sa.ForeignKeyConstraint(["official_id"], ["gov_officials.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(columna, "responsible_id", name=unica),
            sa.CheckConstraint(f"rol IN ({_en(*ROLES_RESPONSABLE_EXPEDIENTE)})", name="rol"),
        )
        for col in ("company_id", columna, "responsible_id", "official_id"):
            nombre = f"ix_{tabla}_{col}"
            if nombre == "ix_gov_procurement_recommendation_responsibles_recommendation_id":
                nombre = "ix_gov_procurement_recommendation_responsibles_recommen_0973"
            op.create_index(nombre, tabla, [col])

    for tabla in ("gov_procurement_eval_contributions", "gov_procurement_eval_results"):
        with op.batch_alter_table(tabla) as batch:
            batch.alter_column("member_id", existing_type=sa.String(36), nullable=True)
            batch.add_column(sa.Column("responsible_id", sa.String(36), nullable=True))
            batch.create_foreign_key(f"fk_{tabla}_responsible_id", "gov_procurement_file_responsibles", ["responsible_id"], ["id"])
            batch.create_check_constraint("actor", "(member_id IS NULL) <> (responsible_id IS NULL)")
        op.create_index(f"ix_{tabla}_responsible_id", tabla, ["responsible_id"])
    op.create_index(
        "uq_gov_procurement_eval_contributions_raiz_responsable",
        "gov_procurement_eval_contributions",
        ["company_id", "offer_id", "criterion_id", "responsible_id"],
        unique=True,
        postgresql_where=sa.text("reemplaza_id IS NULL AND responsible_id IS NOT NULL"),
        sqlite_where=sa.text("reemplaza_id IS NULL AND responsible_id IS NOT NULL"),
    )

    _conceder_permisos(bind)


def downgrade() -> None:
    bind = op.get_bind()
    _retirar_permisos(bind)

    op.drop_index("uq_gov_procurement_eval_contributions_raiz_responsable", table_name="gov_procurement_eval_contributions")
    for tabla in ("gov_procurement_eval_results", "gov_procurement_eval_contributions"):
        op.drop_index(f"ix_{tabla}_responsible_id", table_name=tabla)
        with op.batch_alter_table(tabla) as batch:
            batch.drop_constraint("actor", type_="check")
            batch.drop_constraint(f"fk_{tabla}_responsible_id", type_="foreignkey")
            batch.drop_column("responsible_id")
            batch.alter_column("member_id", existing_type=sa.String(36), nullable=False)

    for tabla in ("gov_procurement_recommendation_responsibles", "gov_procurement_opening_responsibles"):
        op.drop_table(tabla)

    with op.batch_alter_table("gov_procurement_recommendations") as batch:
        batch.drop_constraint("modo_comision", type_="check")
        batch.drop_constraint("modo", type_="check")
        batch.drop_column("regla")
        batch.drop_column("modo")
        batch.alter_column("committee_id", existing_type=sa.String(36), nullable=False)

    with op.batch_alter_table("gov_procurement_openings") as batch:
        batch.drop_constraint("modo_comision", type_="check")
        batch.drop_constraint("modo", type_="check")
        batch.drop_column("regla")
        batch.drop_column("modo")
        batch.alter_column("quorum_requerido", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("asistentes_con_voto", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("miembros_con_voto", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("committee_id", existing_type=sa.String(36), nullable=False)

    op.drop_index("ix_gov_procurement_committee_conflicts_file_id", table_name="gov_procurement_committee_conflicts")
    with op.batch_alter_table("gov_procurement_committee_conflicts") as batch:
        batch.drop_constraint("fk_gov_procurement_committee_conflicts_file_id", type_="foreignkey")
        batch.drop_column("file_id")

    op.drop_index("uq_gov_committee_presidente", table_name="gov_procurement_committee_members")
    with op.batch_alter_table("gov_procurement_committee_members") as batch:
        batch.drop_constraint("preside", type_="check")
        batch.drop_column("preside")

    op.drop_index("ix_gov_procurement_committees_policy_id", table_name="gov_procurement_committees")
    with op.batch_alter_table("gov_procurement_committees") as batch:
        batch.drop_constraint("fk_gov_procurement_committees_policy_id", type_="foreignkey")
        batch.drop_column("regla")
        batch.drop_column("policy_version")
        batch.drop_column("policy_id")

    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_gov_commission_policy_history_no_update ON gov_commission_policy_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_commission_policy_history_no_delete ON gov_commission_policy_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_commission_policy_history_no_truncate ON gov_commission_policy_history")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_politica_comision_historia_inmutable()")
    op.drop_table("gov_commission_policy_history")
    op.drop_table("gov_commission_policy_documents")
    op.drop_table("gov_commission_policy_requirements")
    op.drop_index("uq_gov_commission_policies_vigente", table_name="gov_commission_policies")
    op.drop_table("gov_commission_policies")
