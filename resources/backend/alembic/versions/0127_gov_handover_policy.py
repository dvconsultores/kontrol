"""CTL-09-DELIVERY-ACT-POLICY: política de actas de entrega configurable por el ente.

Crea la política con versiones, sus vínculos a los supuestos de N34 (arts. 12-17), requisitos adicionales,
plazos internos e historia inmutable. El acta guarda la política y la regla aplicada; el anexo guarda su origen,
supuesto, fuente y tipo de evidencia. Sin backfill: las actas existentes conservan sus anexos y se leen con su
regla histórica (OD-AE-02).
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0127_gov_handover_policy"
down_revision = "0126_gov_assignment_policy"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_actas": ("configure", "activate")}

ESTADOS_POLITICA_ACTA = ("BORRADOR", "VIGENTE", "CERRADA")
EVENTOS_POLITICA_ACTA = ("CREADA", "EDITADA", "ACTIVADA", "CERRADA", "SUSTITUIDA", "NUEVA_VERSION")
SUPUESTOS_ACTA = ("N34_ART11", "N34_ART12", "N34_ART13", "N34_ART14", "N34_ART15", "N34_ART16", "N34_ART17")
ALCANCES_VINCULO_ACTA = ("ENTE", "UNIDAD")
EVIDENCIAS_REQUISITO_ACTA = ("DOCUMENTO", "CERTIFICACION", "DECLARACION", "DATO")
AMBITOS_REQUISITO_ACTA = ("TODAS", "ENTE", "UNIDAD")
HITOS_PLAZO_ACTA = ("ELABORACION", "REMISION_UAI")
UNIDADES_PLAZO_ACTA = ("DIAS_HABILES", "DIAS_CONTINUOS")

HISTORIA_INMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_politica_acta_historia_inmutable() RETURNS TRIGGER AS $$ "
    "BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_HANDOVER_POLICY_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_handover_policy_history_no_update BEFORE UPDATE ON gov_handover_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_politica_acta_historia_inmutable()",
    "CREATE TRIGGER trg_gov_handover_policy_history_no_delete BEFORE DELETE ON gov_handover_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_politica_acta_historia_inmutable()",
    "CREATE TRIGGER trg_gov_handover_policy_history_no_truncate BEFORE TRUNCATE ON gov_handover_policy_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_politica_acta_historia_inmutable()",
)

_CAMPOS_ACTA = (
    "NEW.motivo IS DISTINCT FROM OLD.motivo OR NEW.fundamento IS DISTINCT FROM OLD.fundamento "
    "OR NEW.lugar IS DISTINCT FROM OLD.lugar OR NEW.fecha_corte IS DISTINCT FROM OLD.fecha_corte "
    "OR NEW.saliente::text IS DISTINCT FROM OLD.saliente::text OR NEW.receptor::text IS DISTINCT FROM OLD.receptor::text "
    "OR NEW.testigos::text IS DISTINCT FROM OLD.testigos::text OR NEW.modalidad IS DISTINCT FROM OLD.modalidad "
    "OR NEW.assignment_id IS DISTINCT FROM OLD.assignment_id OR NEW.receptor_official_id IS DISTINCT FROM OLD.receptor_official_id "
    "OR NEW.auditor_official_id IS DISTINCT FROM OLD.auditor_official_id OR NEW.snapshot::text IS DISTINCT FROM OLD.snapshot::text "
    "OR NEW.snapshot_sha256 IS DISTINCT FROM OLD.snapshot_sha256 OR NEW.informe_storage_key IS DISTINCT FROM OLD.informe_storage_key "
    "OR NEW.informe_sha256 IS DISTINCT FROM OLD.informe_sha256 OR NEW.informe_bytes IS DISTINCT FROM OLD.informe_bytes "
    "OR NEW.fecha_suscripcion IS DISTINCT FROM OLD.fecha_suscripcion OR NEW.errores_deficiencias IS DISTINCT FROM OLD.errores_deficiencias "
    "OR NEW.codigo IS DISTINCT FROM OLD.codigo"
)
_CAMPOS_REGLA = (
    " OR NEW.policy_id IS DISTINCT FROM OLD.policy_id OR NEW.policy_version IS DISTINCT FROM OLD.policy_version"
    " OR NEW.regla::text IS DISTINCT FROM OLD.regla::text"
)


def _acta_inmutable(campos: str) -> str:
    return (
        "CREATE OR REPLACE FUNCTION kontrol_gov_handover_act_immutable() RETURNS TRIGGER AS $$ "
        "BEGIN "
        "IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Las actas de entrega no se pueden eliminar'; "
        "ELSIF TG_OP = 'TRUNCATE' THEN RAISE EXCEPTION 'Las actas de entrega no se pueden truncar'; "
        "ELSIF TG_OP = 'UPDATE' THEN "
        f"IF OLD.snapshot_sha256 IS NOT NULL THEN IF {campos} THEN "
        "RAISE EXCEPTION 'No se pueden modificar campos congelados de un acta suscrita'; END IF; END IF; "
        "END IF; RETURN NEW; END; $$ LANGUAGE plpgsql"
    )


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _tiempos() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def _hija(nombre: str, *columnas: sa.Column, restricciones: tuple = ()) -> None:
    op.create_table(
        nombre,
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        *columnas,
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_handover_policies.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        *restricciones,
    )
    op.create_index(f"ix_{nombre}_policy_id", nombre, ["policy_id"])
    op.create_index(f"ix_{nombre}_company_id", nombre, ["company_id"])


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
        "gov_handover_policies",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("numero_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("fundamento", sa.String(2000), nullable=True),
        sa.Column("act_id", sa.String(36), nullable=True),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("estado", sa.String(10), nullable=False, server_default="BORRADOR"),
        sa.Column("numeracion_patron", sa.String(60), nullable=True),
        sa.Column("testigos_en_entrega", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cargo_maxima_autoridad_codigo", sa.String(30), nullable=True),
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
        sa.ForeignKeyConstraint(["version_anterior_id"], ["gov_handover_policies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", "numero_version", name="uq_gov_handover_policies_version"),
        sa.CheckConstraint(f"estado IN ({_en(*ESTADOS_POLITICA_ACTA)})", name="estado"),
        sa.CheckConstraint("numero_version >= 1", name="numero_version"),
        sa.CheckConstraint("testigos_en_entrega >= 0 AND testigos_en_entrega <= 5", name="testigos_en_entrega"),
        sa.CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        sa.CheckConstraint("estado = 'BORRADOR' OR fundamento IS NOT NULL", name="fundamento"),
        sa.CheckConstraint("estado <> 'CERRADA' OR (cerrada_en IS NOT NULL AND motivo_cierre IS NOT NULL)", name="cerrada"),
    )
    op.create_index("ix_gov_handover_policies_company_id", "gov_handover_policies", ["company_id"])
    op.create_index(
        "uq_gov_handover_policies_vigente",
        "gov_handover_policies",
        ["company_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'VIGENTE'"),
        sqlite_where=sa.text("estado = 'VIGENTE'"),
    )

    _hija(
        "gov_handover_policy_bindings",
        sa.Column("supuesto", sa.String(16), nullable=False),
        sa.Column("alcance", sa.String(8), nullable=False),
        sa.Column("unit_id", sa.String(36), nullable=True),
        restricciones=(
            sa.ForeignKeyConstraint(["unit_id"], ["gov_units.id"]),
            sa.CheckConstraint(f"supuesto IN ({_en(*SUPUESTOS_ACTA)})", name="supuesto"),
            sa.CheckConstraint(f"alcance IN ({_en(*ALCANCES_VINCULO_ACTA)})", name="alcance"),
            sa.CheckConstraint("(alcance = 'UNIDAD') = (unit_id IS NOT NULL)", name="unidad"),
        ),
    )
    _hija(
        "gov_handover_policy_requirements",
        sa.Column("codigo", sa.String(8), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("evidencia", sa.String(16), nullable=False),
        sa.Column("obligatorio", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ambito", sa.String(8), nullable=False, server_default="TODAS"),
        sa.Column("supuesto", sa.String(16), nullable=True),
        sa.Column("document_type_id", sa.String(36), nullable=True),
        sa.Column("fuente", sa.String(500), nullable=True),
        restricciones=(
            sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"]),
            sa.UniqueConstraint("policy_id", "codigo", name="uq_gov_handover_policy_requirements_codigo"),
            sa.CheckConstraint(f"evidencia IN ({_en(*EVIDENCIAS_REQUISITO_ACTA)})", name="evidencia"),
            sa.CheckConstraint(f"ambito IN ({_en(*AMBITOS_REQUISITO_ACTA)})", name="ambito"),
            sa.CheckConstraint(f"supuesto IS NULL OR supuesto IN ({_en(*SUPUESTOS_ACTA)})", name="supuesto"),
        ),
    )
    _hija(
        "gov_handover_policy_deadlines",
        sa.Column("hito", sa.String(16), nullable=False),
        sa.Column("valor", sa.Integer(), nullable=False),
        sa.Column("unidad", sa.String(16), nullable=False),
        sa.Column("fuente", sa.String(500), nullable=True),
        restricciones=(
            sa.UniqueConstraint("policy_id", "hito", name="uq_gov_handover_policy_deadlines_hito"),
            sa.CheckConstraint(f"hito IN ({_en(*HITOS_PLAZO_ACTA)})", name="hito"),
            sa.CheckConstraint(f"unidad IN ({_en(*UNIDADES_PLAZO_ACTA)})", name="unidad"),
            sa.CheckConstraint("valor >= 1", name="valor"),
        ),
    )
    _hija(
        "gov_handover_policy_history",
        sa.Column("evento", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("instantanea", sa.JSON(), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=True),
        restricciones=(sa.CheckConstraint(f"evento IN ({_en(*EVENTOS_POLITICA_ACTA)})", name="evento"),),
    )

    with op.batch_alter_table("gov_handover_acts") as batch:
        batch.add_column(sa.Column("policy_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("policy_version", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("regla", sa.JSON(), nullable=True))
        batch.create_foreign_key("fk_gov_handover_acts_policy_id", "gov_handover_policies", ["policy_id"], ["id"])
    op.create_index("ix_gov_handover_acts_policy_id", "gov_handover_acts", ["policy_id"])

    with op.batch_alter_table("gov_handover_annexes") as batch:
        batch.add_column(sa.Column("origen", sa.String(10), nullable=True))
        batch.add_column(sa.Column("supuesto", sa.String(16), nullable=True))
        batch.add_column(sa.Column("fuente", sa.String(500), nullable=True))
        batch.add_column(sa.Column("evidencia", sa.String(16), nullable=True))
        batch.add_column(sa.Column("declaracion", sa.String(2000), nullable=True))
        batch.add_column(sa.Column("document_type_id", sa.String(36), nullable=True))

    if bind.dialect.name == "postgresql":
        for sentencia in HISTORIA_INMUTABLE_PG:
            op.execute(sentencia)
        op.execute(_acta_inmutable(_CAMPOS_ACTA + _CAMPOS_REGLA))

    _conceder_permisos(bind)


def downgrade() -> None:
    bind = op.get_bind()
    _retirar_permisos(bind)

    if bind.dialect.name == "postgresql":
        op.execute(_acta_inmutable(_CAMPOS_ACTA))

    with op.batch_alter_table("gov_handover_annexes") as batch:
        for columna in ("document_type_id", "declaracion", "evidencia", "fuente", "supuesto", "origen"):
            batch.drop_column(columna)

    op.drop_index("ix_gov_handover_acts_policy_id", table_name="gov_handover_acts")
    with op.batch_alter_table("gov_handover_acts") as batch:
        batch.drop_constraint("fk_gov_handover_acts_policy_id", type_="foreignkey")
        batch.drop_column("regla")
        batch.drop_column("policy_version")
        batch.drop_column("policy_id")

    for tabla in (
        "gov_handover_policy_history",
        "gov_handover_policy_deadlines",
        "gov_handover_policy_requirements",
        "gov_handover_policy_bindings",
    ):
        op.drop_table(tabla)
    op.drop_index("uq_gov_handover_policies_vigente", table_name="gov_handover_policies")
    op.drop_index("ix_gov_handover_policies_company_id", table_name="gov_handover_policies")
    op.drop_table("gov_handover_policies")
