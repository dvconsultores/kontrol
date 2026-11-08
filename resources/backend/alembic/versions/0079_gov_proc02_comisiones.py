"""gobierno comisiones de contrataciones

Revision ID: 0079_gov_proc02_comisiones
Revises: 0078_gov_ctl02_bitacora
Create Date: 2025-01-01 00:00:00
"""
import uuid

import sqlalchemy as sa

from alembic import op

revision = "0079_gov_proc02_comisiones"
down_revision = "0078_gov_ctl02_bitacora"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_comisiones": ("view", "manage", "activate", "close")}


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
        "gov_procurement_committees",
        sa.Column("id", sa.String(36), primary_key=True),
        *_tiempos(),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("tipo", sa.String(16), nullable=False),
        sa.Column("objeto", sa.String(500), nullable=True),
        sa.Column("desde", sa.Date(), nullable=False),
        sa.Column("hasta", sa.Date(), nullable=True),
        sa.Column("act_id", sa.String(36), sa.ForeignKey("gov_acts.id"), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="BORRADOR"),
        sa.Column("regla_version", sa.String(40), nullable=True),
        sa.Column("snc_notificada_en", sa.Date(), nullable=True),
        sa.Column("snc_referencia", sa.String(200), nullable=True),
        sa.Column("motivo_cierre", sa.String(500), nullable=True),
        sa.Column("fin_efectivo", sa.Date(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by", sa.String(36), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.String(36), nullable=True),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_committees_codigo"),
        sa.CheckConstraint(f"status IN ({_en('BORRADOR', 'VIGENTE', 'CERRADA', 'DESCARTADA')})", name="ck_gov_procurement_committees_status"),
        sa.CheckConstraint(f"tipo IN ({_en('PERMANENTE', 'TEMPORAL')})", name="ck_gov_procurement_committees_tipo"),
        sa.CheckConstraint("version >= 1", name="ck_gov_procurement_committees_version"),
        sa.CheckConstraint("hasta IS NULL OR hasta >= desde", name="ck_gov_procurement_committees_vigencia"),
        sa.CheckConstraint("tipo <> 'TEMPORAL' OR status IN ('BORRADOR','DESCARTADA') OR hasta IS NOT NULL", name="ck_gov_procurement_committees_temporal_con_fin"),
        sa.CheckConstraint("status IN ('BORRADOR','DESCARTADA') OR (act_id IS NOT NULL AND activated_at IS NOT NULL AND regla_version IS NOT NULL)", name="ck_gov_procurement_committees_vigente_con_acto"),
        sa.CheckConstraint("status <> 'CERRADA' OR (fin_efectivo IS NOT NULL AND motivo_cierre IS NOT NULL)", name="ck_gov_procurement_committees_cerrada_con_fin"),
    )
    op.create_index("ix_gov_procurement_committees_company_id", "gov_procurement_committees", ["company_id"])

    op.create_table(
        "gov_procurement_committee_members",
        sa.Column("id", sa.String(36), primary_key=True),
        *_tiempos(),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("committee_id", sa.String(36), sa.ForeignKey("gov_procurement_committees.id"), nullable=False),
        sa.Column("official_id", sa.String(36), sa.ForeignKey("gov_officials.id"), nullable=False),
        sa.Column("funcion", sa.String(16), nullable=False),
        sa.Column("area", sa.String(24), nullable=True),
        sa.Column("condicion", sa.String(16), nullable=False),
        sa.Column("suplente_de_id", sa.String(36), sa.ForeignKey("gov_procurement_committee_members.id"), nullable=True),
        sa.Column("desde", sa.Date(), nullable=False),
        sa.Column("act_id", sa.String(36), sa.ForeignKey("gov_acts.id"), nullable=True),
        sa.Column("certificacion_snc", sa.String(200), nullable=True),
        sa.Column("fin_efectivo", sa.Date(), nullable=True),
        sa.Column("causa_fin", sa.String(32), nullable=True),
        sa.Column("motivo_fin", sa.String(500), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_by", sa.String(36), nullable=True),
        sa.CheckConstraint(f"funcion IN ({_en('MIEMBRO', 'SECRETARIO')})", name="ck_gov_procurement_committee_members_funcion"),
        sa.CheckConstraint(f"condicion IN ({_en('PRINCIPAL', 'SUPLENTE')})", name="ck_gov_procurement_committee_members_condicion"),
        sa.CheckConstraint(f"causa_fin IS NULL OR causa_fin IN ({_en('MUERTE_INCAPACIDAD', 'DESPIDO_DESTITUCION', 'RETIRO_RENUNCIA_REMOCION', 'FIN_DESIGNACION')})", name="ck_gov_procurement_committee_members_causa_fin"),
        sa.CheckConstraint("(funcion = 'SECRETARIO' AND area IS NULL) OR (funcion = 'MIEMBRO' AND area IN ('JURIDICA', 'TECNICA', 'ECONOMICO_FINANCIERA'))", name="ck_gov_procurement_committee_members_area"),
        sa.CheckConstraint("condicion = 'PRINCIPAL' OR funcion = 'SECRETARIO' OR suplente_de_id IS NOT NULL", name="ck_gov_procurement_committee_members_suplente_de"),
        sa.CheckConstraint("fin_efectivo IS NULL OR fin_efectivo >= desde", name="ck_gov_procurement_committee_members_fin_tras_inicio"),
        sa.CheckConstraint("(fin_efectivo IS NULL) = (causa_fin IS NULL)", name="ck_gov_procurement_committee_members_fin_con_causa"),
    )
    op.create_index("ix_gov_procurement_committee_members_company_id", "gov_procurement_committee_members", ["company_id"])
    op.create_index("ix_gov_procurement_committee_members_committee_id", "gov_procurement_committee_members", ["committee_id"])
    op.create_index("ix_gov_procurement_committee_members_official_id", "gov_procurement_committee_members", ["official_id"])
    op.create_index("uq_gov_committee_member_official", "gov_procurement_committee_members", ["committee_id", "official_id"], unique=True, postgresql_where=sa.text("fin_efectivo IS NULL"), sqlite_where=sa.text("fin_efectivo IS NULL"))
    op.create_index("uq_gov_committee_member_suplente", "gov_procurement_committee_members", ["suplente_de_id"], unique=True, postgresql_where=sa.text("fin_efectivo IS NULL AND suplente_de_id IS NOT NULL"), sqlite_where=sa.text("fin_efectivo IS NULL AND suplente_de_id IS NOT NULL"))
    op.create_index("uq_gov_committee_secretario", "gov_procurement_committee_members", ["committee_id", "condicion"], unique=True, postgresql_where=sa.text("fin_efectivo IS NULL AND funcion = 'SECRETARIO'"), sqlite_where=sa.text("fin_efectivo IS NULL AND funcion = 'SECRETARIO'"))

    op.create_table(
        "gov_procurement_committee_conflicts",
        sa.Column("id", sa.String(36), primary_key=True),
        *_tiempos(),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("committee_id", sa.String(36), sa.ForeignKey("gov_procurement_committees.id"), nullable=False),
        sa.Column("member_id", sa.String(36), sa.ForeignKey("gov_procurement_committee_members.id"), nullable=False),
        sa.Column("asunto", sa.String(300), nullable=False),
        sa.Column("causal", sa.String(32), nullable=False),
        sa.Column("descripcion", sa.String(1000), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("soporte", sa.String(200), nullable=True),
        sa.Column("estado", sa.String(16), nullable=False, server_default="DECLARADA"),
        sa.Column("motivo_resolucion", sa.String(1000), nullable=True),
        sa.Column("resuelta_por", sa.String(36), nullable=True),
        sa.Column("resuelta_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"causal IN ({_en('INTERES', 'AMISTAD_ENEMISTAD', 'INTERVENCION_PREVIA', 'SERVICIO_SUBORDINACION')})", name="ck_gov_procurement_committee_conflicts_causal"),
        sa.CheckConstraint(f"estado IN ({_en('DECLARADA', 'ACEPTADA', 'RECHAZADA')})", name="ck_gov_procurement_committee_conflicts_estado"),
        sa.CheckConstraint("version >= 1", name="ck_gov_procurement_committee_conflicts_version"),
        sa.CheckConstraint("estado = 'DECLARADA' OR (resuelta_por IS NOT NULL AND resuelta_en IS NOT NULL AND motivo_resolucion IS NOT NULL)", name="ck_gov_procurement_committee_conflicts_resuelta"),
    )
    op.create_index("ix_gov_procurement_committee_conflicts_company_id", "gov_procurement_committee_conflicts", ["company_id"])
    op.create_index("ix_gov_procurement_committee_conflicts_committee_id", "gov_procurement_committee_conflicts", ["committee_id"])
    op.create_index("ix_gov_procurement_committee_conflicts_member_id", "gov_procurement_committee_conflicts", ["member_id"])

    op.create_table(
        "gov_procurement_committee_history",
        sa.Column("id", sa.String(36), primary_key=True),
        *_tiempos(),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("committee_id", sa.String(36), sa.ForeignKey("gov_procurement_committees.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("tipo", sa.String(24), nullable=False),
        sa.Column("detalle", sa.JSON(), nullable=True),
        sa.CheckConstraint(f"tipo IN ({_en('CREADA', 'EDITADA', 'DESCARTADA', 'ACTIVADA', 'CERRADA', 'SNC_NOTIFICADA', 'MIEMBRO_ANADIDO', 'MIEMBRO_RETIRADO', 'MIEMBRO_TERMINADO', 'INHIBICION_DECLARADA', 'INHIBICION_RESUELTA')})", name="ck_gov_procurement_committee_history_tipo"),
    )
    op.create_index("ix_gov_procurement_committee_history_committee_id", "gov_procurement_committee_history", ["committee_id"])
    op.create_index("ix_gov_procurement_committee_history_company_id", "gov_procurement_committee_history", ["company_id"])

    if bind.dialect.name == "postgresql":
        op.execute("CREATE OR REPLACE FUNCTION kontrol_gov_comision_historia_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_COMMITTEE_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql")
        op.execute("CREATE TRIGGER trg_gov_committee_history_no_update BEFORE UPDATE ON gov_procurement_committee_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_comision_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_committee_history_no_delete BEFORE DELETE ON gov_procurement_committee_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_comision_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_committee_history_no_truncate BEFORE TRUNCATE ON gov_procurement_committee_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_comision_historia_inmutable()")

    _proceso_sod(bind, "DOC-02", "CTL-06", "TRE-01", "TRE-02", "CTL-10", "ORG-04", "ORG-06", "PROC-02")
    _conceder_permisos(bind)


def downgrade() -> None:
    bind = op.get_bind()

    _proceso_sod(bind, "DOC-02", "CTL-06", "TRE-01", "TRE-02", "CTL-10", "ORG-04", "ORG-06")

    for recurso, acciones in PERMISOS.items():
        for accion in acciones:
            permiso = bind.execute(sa.text(
                "SELECT id FROM permissions WHERE resource = :r AND action = :a"),
                {"r": recurso, "a": accion}).fetchone()
            if not permiso:
                continue
            bind.execute(sa.text("DELETE FROM role_permissions WHERE permission_id = :p"), {"p": permiso[0]})
            bind.execute(sa.text("DELETE FROM permissions WHERE id = :p"), {"p": permiso[0]})

    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_gov_committee_history_no_update ON gov_procurement_committee_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_committee_history_no_delete ON gov_procurement_committee_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_committee_history_no_truncate ON gov_procurement_committee_history")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_comision_historia_inmutable()")

    op.drop_table("gov_procurement_committee_history")
    op.drop_table("gov_procurement_committee_conflicts")
    op.drop_table("gov_procurement_committee_members")
    op.drop_table("gov_procurement_committees")
