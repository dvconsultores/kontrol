"""gov doc02 actos

Crea `gov_acts` y `gov_act_versions` (DOC-02: actos administrativos con tipos, titularidades, caracteres, medios y estados, e historia de cambios) y concede `gobierno_actos:*` al rol protegido FUNCIONAL_COMPLETO de las instalaciones existentes. Sin relleno de datos de negocio.

Revision ID: 0066_gov_doc02_actos
Revises: 0065_gov0_cargos
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0066_gov_doc02_actos"
down_revision = "0065_gov0_cargos"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_actos": ("view", "edit", "issue", "annul")}


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _tiempos() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "gov_acts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("tipo", sa.String(16), nullable=False),
        sa.Column("denominacion_tipo", sa.String(80), nullable=False, server_default=""),
        sa.Column("denominacion_clave", sa.String(80), nullable=False, server_default=""),
        sa.Column("numero", sa.String(60), nullable=False),
        sa.Column("numero_clave", sa.String(60), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("lugar", sa.String(120), nullable=False),
        sa.Column("cargo_id", sa.String(36), sa.ForeignKey("gov_positions.id"), nullable=False),
        sa.Column("competencia_accion", sa.String(16), nullable=False),
        sa.Column("competencia_materia", sa.String(16), nullable=False),
        sa.Column("fundamento_competencia", sa.String(500), nullable=False),
        sa.Column("funcionario", sa.String(200), nullable=False),
        sa.Column("titularidad", sa.String(16), nullable=False),
        sa.Column("delegacion_numero", sa.String(60), nullable=True),
        sa.Column("delegacion_fecha", sa.Date(), nullable=True),
        sa.Column("caracter", sa.String(16), nullable=False),
        sa.Column("simple_tramite", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("destinatario", sa.String(200), nullable=True),
        sa.Column("asunto", sa.String(200), nullable=False),
        sa.Column("hechos", sa.Text(), nullable=True),
        sa.Column("fundamentos", sa.Text(), nullable=True),
        sa.Column("decision", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="BORRADOR"),
        sa.Column("documento_acto_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("medio", sa.String(16), nullable=True),
        sa.Column("referencia_publicacion", sa.String(120), nullable=True),
        sa.Column("fecha_publicacion_notificacion", sa.Date(), nullable=True),
        sa.Column("documento_eficacia_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("fecha_eficacia", sa.Date(), nullable=True),
        sa.Column("revocado_por_id", sa.String(36), sa.ForeignKey("gov_acts.id"), nullable=True),
        sa.Column("anulado_por_id", sa.String(36), sa.ForeignKey("gov_acts.id"), nullable=True),
        sa.Column("emitido_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("emitido_por", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        *_tiempos(),
        sa.UniqueConstraint("cargo_id", "tipo", "denominacion_clave", "numero_clave", name="uq_gov_acts_numero"),
        sa.CheckConstraint(
            f"tipo IN ({_en('DECRETO', 'RESOLUCION', 'ORDEN', 'PROVIDENCIA', 'INSTRUCCION', 'CIRCULAR', 'OTRA_DECISION')})",
            name="tipo",
        ),
        sa.CheckConstraint(
            f"titularidad IN ({_en('TITULAR', 'DELEGACION', 'ENCARGADURIA', 'SUPLENCIA')})",
            name="titularidad",
        ),
        sa.CheckConstraint(
            f"caracter IN ({_en('GENERAL', 'PARTICULAR', 'INTERNO')})",
            name="caracter",
        ),
        sa.CheckConstraint(
            f"medio IS NULL OR medio IN ({_en('GACETA', 'PERSONAL', 'PRENSA')})",
            name="medio",
        ),
        sa.CheckConstraint(
            f"status IN ({_en('BORRADOR', 'EMITIDO', 'EFICAZ', 'REVOCADO', 'NULO')})",
            name="status",
        ),
        sa.CheckConstraint(
            f"competencia_accion IN ({_en('SOLICITAR', 'COMPROMETER', 'CAUSAR', 'ORDENAR_PAGO', 'PAGAR', 'REGISTRAR', 'CUSTODIAR', 'APROBAR', 'AUDITAR', 'FIRMAR')})",
            name="competencia_accion",
        ),
        sa.CheckConstraint(
            f"competencia_materia IN ({_en('PRESUPUESTO', 'CONTRATACIONES', 'TESORERIA', 'CONTABILIDAD', 'BIENES', 'EXPEDIENTE')})",
            name="competencia_materia",
        ),
        sa.CheckConstraint(
            "(tipo = 'OTRA_DECISION' AND denominacion_tipo <> '') OR (tipo <> 'OTRA_DECISION' AND denominacion_tipo = '')",
            name="denominacion",
        ),
        sa.CheckConstraint(
            "(titularidad = 'DELEGACION' AND delegacion_numero IS NOT NULL AND delegacion_fecha IS NOT NULL) OR "
            "(titularidad <> 'DELEGACION' AND delegacion_numero IS NULL AND delegacion_fecha IS NULL)",
            name="delegacion",
        ),
        sa.CheckConstraint("simple_tramite = false OR caracter = 'PARTICULAR'", name="simple_tramite"),
        sa.CheckConstraint("delegacion_fecha IS NULL OR delegacion_fecha <= fecha", name="delegacion_fecha"),
        sa.CheckConstraint(
            "status = 'BORRADOR' OR (documento_acto_id IS NOT NULL AND emitido_en IS NOT NULL)",
            name="emitido_documentado",
        ),
        sa.CheckConstraint("status <> 'EFICAZ' OR fecha_eficacia IS NOT NULL", name="eficaz_fechado"),
        sa.CheckConstraint("fecha_eficacia IS NULL OR fecha_eficacia >= fecha", name="eficacia_no_retroactiva"),
        sa.CheckConstraint("(status = 'REVOCADO') = (revocado_por_id IS NOT NULL)", name="revocado_referenciado"),
        sa.CheckConstraint("(status = 'NULO') = (anulado_por_id IS NOT NULL)", name="nulo_referenciado"),
        sa.CheckConstraint("version >= 1", name="version"),
    )
    op.create_index("ix_gov_acts_company_id", "gov_acts", ["company_id"])
    op.create_index("ix_gov_acts_cargo_id", "gov_acts", ["cargo_id"])
    op.create_index("ix_gov_acts_company_fecha", "gov_acts", ["company_id", "fecha"])
    op.create_index("ix_gov_acts_company_status", "gov_acts", ["company_id", "status"])

    op.create_table(
        "gov_act_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("act_id", sa.String(36), sa.ForeignKey("gov_acts.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("actor_id", sa.String(36), nullable=True),
        *_tiempos(),
        sa.UniqueConstraint("act_id", "version", name="uq_gov_act_versions_act_id_version"),
        sa.CheckConstraint(
            f"status IN ({_en('BORRADOR', 'EMITIDO', 'EFICAZ', 'REVOCADO', 'NULO')})",
            name="status",
        ),
        sa.CheckConstraint("version >= 1", name="version"),
    )
    op.create_index("ix_gov_act_versions_act_id", "gov_act_versions", ["act_id"])
    op.create_index("ix_gov_act_versions_company_id", "gov_act_versions", ["company_id"])

    _conceder_permisos(op.get_bind())


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


def downgrade() -> None:
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

    op.drop_index("ix_gov_act_versions_company_id", table_name="gov_act_versions")
    op.drop_index("ix_gov_act_versions_act_id", table_name="gov_act_versions")
    op.drop_index("ix_gov_acts_company_status", table_name="gov_acts")
    op.drop_index("ix_gov_acts_company_fecha", table_name="gov_acts")
    op.drop_index("ix_gov_acts_cargo_id", table_name="gov_acts")
    op.drop_index("ix_gov_acts_company_id", table_name="gov_acts")
    op.drop_table("gov_act_versions")
    op.drop_table("gov_acts")
