"""CNT-03: ejecución del contrato (inicio, hitos, entregables, valuaciones, recepciones, facturas
y cierre) y permiso gobierno_contratos:execute (GOV-CNT-003, GOV-CNT-007)."""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0119_gov_cnt03_ejecucion"
down_revision = "0118_gov_cnt02_modificaciones"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_contratos": ("execute",)}

GOV_CONTRACT_EXEC_GUARD_FUNCION_PG = """
CREATE OR REPLACE FUNCTION kontrol_gov_contract_exec_guard()
RETURNS trigger AS $$
BEGIN
    IF TG_OP IN ('DELETE','TRUNCATE') THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_EXEC_IMMUTABLE', DETAIL = TG_TABLE_NAME || ' ' || TG_OP;
    END IF;
    IF TG_NARGS = 3
       AND (to_jsonb(OLD) ->> 'estado') = TG_ARGV[0]
       AND (to_jsonb(NEW) ->> 'estado') = ANY (string_to_array(TG_ARGV[1], ','))
       AND (to_jsonb(OLD) - string_to_array(TG_ARGV[2], ',')) = (to_jsonb(NEW) - string_to_array(TG_ARGV[2], ','))
    THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_EXEC_IMMUTABLE', DETAIL = TG_TABLE_NAME || ' ' || TG_OP;
END;
$$ LANGUAGE plpgsql;
"""

GOV_CONTRACT_EXEC_GUARDS: tuple[tuple[str, str], ...] = (
    ("gov_contract_execution_acts", ""),
    ("gov_contract_milestones", "'VIGENTE', 'ANULADO', 'estado,motivo_anulacion,anulado_en,anulado_por,version,updated_at'"),
    ("gov_contract_deliverables", "'VIGENTE', 'ANULADO', 'estado,motivo_anulacion,anulado_en,anulado_por,version,updated_at'"),
    (
        "gov_contract_deliverable_submissions",
        "'ENTREGADA', 'CONFORME,RECHAZADA', 'estado,fecha_revision,observacion_revision,supervisor_assignment_id,supervisor_official_id,supervisor_nombre,revisado_en,revisado_por,version,updated_at'",
    ),
    (
        "gov_contract_valuations",
        "'PRESENTADA', 'CONFORMADA,REPARADA,ANULADA', 'estado,fecha_conformidad,acumulado,reparos,motivo_anulacion,supervisor_assignment_id,supervisor_official_id,supervisor_nombre,resuelto_en,resuelto_por,version,updated_at'",
    ),
    ("gov_contract_receipts", "'CONFORME', 'ANULADA', 'estado,motivo_anulacion,anulado_en,anulado_por,version,updated_at'"),
    ("gov_contract_receipt_milestones", ""),
    ("gov_contract_invoices", "'CONFORME', 'ANULADA', 'estado,motivo_anulacion,anulado_en,anulado_por,version,updated_at'"),
)


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
        "gov_contract_execution_acts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("contract_id", sa.String(36), sa.ForeignKey("gov_contracts.id"), nullable=False),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("observacion", sa.String(1000), nullable=True),
        sa.Column("supervisor_assignment_id", sa.String(36), sa.ForeignKey("gov_contract_supervisors.id"), nullable=False),
        sa.Column("supervisor_official_id", sa.String(36), sa.ForeignKey("gov_officials.id"), nullable=False),
        sa.Column("supervisor_nombre", sa.String(200), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=False),
        sa.Column("documento_sha256", sa.String(64), nullable=False),
        sa.Column("documento_titulo", sa.String(300), nullable=False),
        sa.Column("aprobacion_document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("aprobacion_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=True),
        sa.Column("aprobacion_sha256", sa.String(64), nullable=True),
        sa.Column("aprobacion_titulo", sa.String(300), nullable=True),
        sa.Column("evaluacion_document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("evaluacion_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=True),
        sa.Column("evaluacion_sha256", sa.String(64), nullable=True),
        sa.Column("evaluacion_titulo", sa.String(300), nullable=True),
        sa.Column("aprobador_tipo", sa.String(20), nullable=True),
        sa.Column("aprobador_nombre", sa.String(250), nullable=True),
        sa.Column("registrado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registrado_por", sa.String(36), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger, nullable=False, server_default="1"),
        *_tiempos(),
        sa.UniqueConstraint("contract_id", "tipo", name="uq_gov_contract_execution_acts_tipo"),
        sa.CheckConstraint("tipo IN ('INICIO', 'TERMINACION', 'CIERRE')", name="tipo"),
        sa.CheckConstraint("aprobador_tipo IS NULL OR aprobador_tipo IN ('COMISION', 'UNIDAD_CONTRATANTE')", name="aprobador"),
        sa.CheckConstraint(
            "(tipo = 'CIERRE') = (aprobacion_document_id IS NOT NULL AND evaluacion_document_id IS NOT NULL "
            "AND aprobador_tipo IS NOT NULL AND aprobador_nombre IS NOT NULL)",
            name="cierre_completo",
        ),
        sa.CheckConstraint(
            "aprobacion_document_id IS NULL OR aprobacion_document_id <> evaluacion_document_id",
            name="cierre_documentos_distintos",
        ),
    )
    op.create_index("ix_gov_contract_execution_acts_company_id", "gov_contract_execution_acts", ["company_id"])
    op.create_index("ix_gov_contract_execution_acts_contract_id", "gov_contract_execution_acts", ["contract_id"])

    op.create_table(
        "gov_contract_milestones",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("contract_id", sa.String(36), sa.ForeignKey("gov_contracts.id"), nullable=False),
        sa.Column("numero", sa.Integer, nullable=False),
        sa.Column("descripcion", sa.String(500), nullable=False),
        sa.Column("fecha_prevista", sa.Date, nullable=False),
        sa.Column("monto_previsto", sa.Numeric(18, 2), nullable=True),
        sa.Column("porcentaje_previsto", sa.Numeric(5, 2), nullable=True),
        sa.Column("obligatorio", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("estado", sa.String(10), nullable=False, server_default="VIGENTE"),
        sa.Column("motivo_anulacion", sa.String(500), nullable=True),
        sa.Column("anulado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anulado_por", sa.String(36), nullable=True),
        sa.Column("registrado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registrado_por", sa.String(36), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger, nullable=False, server_default="1"),
        *_tiempos(),
        sa.UniqueConstraint("contract_id", "numero", name="uq_gov_contract_milestones_numero"),
        sa.CheckConstraint("numero >= 1", name="numero"),
        sa.CheckConstraint("estado IN ('VIGENTE', 'ANULADO')", name="estado"),
        sa.CheckConstraint("monto_previsto IS NULL OR monto_previsto > 0", name="monto"),
        sa.CheckConstraint(
            "porcentaje_previsto IS NULL OR (porcentaje_previsto > 0 AND porcentaje_previsto <= 100)",
            name="porcentaje",
        ),
        sa.CheckConstraint(
            "(estado = 'ANULADO') = (motivo_anulacion IS NOT NULL AND anulado_en IS NOT NULL)",
            name="anulacion_motivada",
        ),
    )
    op.create_index("ix_gov_contract_milestones_company_id", "gov_contract_milestones", ["company_id"])
    op.create_index("ix_gov_contract_milestones_contract_id", "gov_contract_milestones", ["contract_id"])

    op.create_table(
        "gov_contract_deliverables",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("contract_id", sa.String(36), sa.ForeignKey("gov_contracts.id"), nullable=False),
        sa.Column("milestone_id", sa.String(36), sa.ForeignKey("gov_contract_milestones.id"), nullable=True),
        sa.Column("numero", sa.Integer, nullable=False),
        sa.Column("descripcion", sa.String(500), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date, nullable=False),
        sa.Column("obligatorio", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("estado", sa.String(10), nullable=False, server_default="VIGENTE"),
        sa.Column("motivo_anulacion", sa.String(500), nullable=True),
        sa.Column("anulado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anulado_por", sa.String(36), nullable=True),
        sa.Column("registrado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registrado_por", sa.String(36), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger, nullable=False, server_default="1"),
        *_tiempos(),
        sa.UniqueConstraint("contract_id", "numero", name="uq_gov_contract_deliverables_numero"),
        sa.CheckConstraint("numero >= 1", name="numero"),
        sa.CheckConstraint("estado IN ('VIGENTE', 'ANULADO')", name="estado"),
        sa.CheckConstraint(
            "(estado = 'ANULADO') = (motivo_anulacion IS NOT NULL AND anulado_en IS NOT NULL)",
            name="anulacion_motivada",
        ),
    )
    op.create_index("ix_gov_contract_deliverables_company_id", "gov_contract_deliverables", ["company_id"])
    op.create_index("ix_gov_contract_deliverables_contract_id", "gov_contract_deliverables", ["contract_id"])
    op.create_index("ix_gov_contract_deliverables_milestone_id", "gov_contract_deliverables", ["milestone_id"])

    op.create_table(
        "gov_contract_deliverable_submissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("contract_id", sa.String(36), sa.ForeignKey("gov_contracts.id"), nullable=False),
        sa.Column("deliverable_id", sa.String(36), sa.ForeignKey("gov_contract_deliverables.id"), nullable=False),
        sa.Column("numero", sa.Integer, nullable=False),
        sa.Column("fecha_entrega", sa.Date, nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=False),
        sa.Column("documento_sha256", sa.String(64), nullable=False),
        sa.Column("documento_titulo", sa.String(300), nullable=False),
        sa.Column("observacion_entrega", sa.String(1000), nullable=True),
        sa.Column("estado", sa.String(10), nullable=False, server_default="ENTREGADA"),
        sa.Column("fecha_revision", sa.Date, nullable=True),
        sa.Column("observacion_revision", sa.String(1000), nullable=True),
        sa.Column("supervisor_assignment_id", sa.String(36), sa.ForeignKey("gov_contract_supervisors.id"), nullable=True),
        sa.Column("supervisor_official_id", sa.String(36), sa.ForeignKey("gov_officials.id"), nullable=True),
        sa.Column("supervisor_nombre", sa.String(200), nullable=True),
        sa.Column("revisado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revisado_por", sa.String(36), nullable=True),
        sa.Column("registrado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registrado_por", sa.String(36), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger, nullable=False, server_default="1"),
        *_tiempos(),
        sa.UniqueConstraint("deliverable_id", "numero", name="uq_gov_contract_submissions_numero"),
        sa.CheckConstraint("estado IN ('ENTREGADA', 'CONFORME', 'RECHAZADA')", name="estado"),
        sa.CheckConstraint("numero >= 1", name="numero"),
        sa.CheckConstraint(
            "(estado = 'ENTREGADA') = (fecha_revision IS NULL AND supervisor_assignment_id IS NULL AND revisado_en IS NULL)",
            name="revision",
        ),
        sa.CheckConstraint("estado <> 'RECHAZADA' OR observacion_revision IS NOT NULL", name="rechazo_motivado"),
        sa.CheckConstraint("fecha_revision IS NULL OR fecha_revision >= fecha_entrega", name="fechas"),
    )
    op.create_index("ix_gov_contract_deliverable_submissions_company_id", "gov_contract_deliverable_submissions", ["company_id"])
    op.create_index("ix_gov_contract_deliverable_submissions_contract_id", "gov_contract_deliverable_submissions", ["contract_id"])
    op.create_index("ix_gov_contract_deliverable_submissions_deliverable_id", "gov_contract_deliverable_submissions", ["deliverable_id"])
    op.create_index(
        "uq_gov_contract_submissions_abierta",
        "gov_contract_deliverable_submissions",
        ["deliverable_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'ENTREGADA'"),
        sqlite_where=sa.text("estado = 'ENTREGADA'"),
    )
    op.create_index(
        "uq_gov_contract_submissions_conforme",
        "gov_contract_deliverable_submissions",
        ["deliverable_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'CONFORME'"),
        sqlite_where=sa.text("estado = 'CONFORME'"),
    )

    op.create_table(
        "gov_contract_valuations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("contract_id", sa.String(36), sa.ForeignKey("gov_contracts.id"), nullable=False),
        sa.Column("milestone_id", sa.String(36), sa.ForeignKey("gov_contract_milestones.id"), nullable=False),
        sa.Column("numero", sa.Integer, nullable=False),
        sa.Column("periodo_desde", sa.Date, nullable=False),
        sa.Column("periodo_hasta", sa.Date, nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=False),
        sa.Column("documento_sha256", sa.String(64), nullable=False),
        sa.Column("documento_titulo", sa.String(300), nullable=False),
        sa.Column("estado", sa.String(12), nullable=False, server_default="PRESENTADA"),
        sa.Column("fecha_conformidad", sa.Date, nullable=True),
        sa.Column("acumulado", sa.Numeric(18, 2), nullable=True),
        sa.Column("reparos", sa.String(1000), nullable=True),
        sa.Column("motivo_anulacion", sa.String(500), nullable=True),
        sa.Column("supervisor_assignment_id", sa.String(36), sa.ForeignKey("gov_contract_supervisors.id"), nullable=True),
        sa.Column("supervisor_official_id", sa.String(36), sa.ForeignKey("gov_officials.id"), nullable=True),
        sa.Column("supervisor_nombre", sa.String(200), nullable=True),
        sa.Column("resuelto_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resuelto_por", sa.String(36), nullable=True),
        sa.Column("registrado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registrado_por", sa.String(36), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger, nullable=False, server_default="1"),
        *_tiempos(),
        sa.UniqueConstraint("contract_id", "numero", name="uq_gov_contract_valuations_numero"),
        sa.CheckConstraint("estado IN ('PRESENTADA', 'CONFORMADA', 'REPARADA', 'ANULADA')", name="estado"),
        sa.CheckConstraint("numero >= 1", name="numero"),
        sa.CheckConstraint("monto > 0", name="monto"),
        sa.CheckConstraint("length(moneda) = 3", name="moneda"),
        sa.CheckConstraint("periodo_desde <= periodo_hasta AND periodo_hasta <= fecha", name="periodo"),
        sa.CheckConstraint(
            "estado <> 'PRESENTADA' OR (fecha_conformidad IS NULL AND supervisor_assignment_id IS NULL)",
            name="presentada",
        ),
        sa.CheckConstraint(
            "estado <> 'CONFORMADA' OR (fecha_conformidad IS NOT NULL AND acumulado IS NOT NULL "
            "AND supervisor_assignment_id IS NOT NULL)",
            name="conformada",
        ),
        sa.CheckConstraint(
            "estado <> 'REPARADA' OR (reparos IS NOT NULL AND fecha_conformidad IS NOT NULL "
            "AND supervisor_assignment_id IS NOT NULL)",
            name="reparada",
        ),
        sa.CheckConstraint("estado <> 'ANULADA' OR motivo_anulacion IS NOT NULL", name="anulada"),
        sa.CheckConstraint("fecha_conformidad IS NULL OR fecha_conformidad >= fecha", name="conformidad"),
    )
    op.create_index("ix_gov_contract_valuations_company_id", "gov_contract_valuations", ["company_id"])
    op.create_index("ix_gov_contract_valuations_contract_id", "gov_contract_valuations", ["contract_id"])
    op.create_index("ix_gov_contract_valuations_milestone_id", "gov_contract_valuations", ["milestone_id"])

    op.create_table(
        "gov_contract_receipts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("contract_id", sa.String(36), sa.ForeignKey("gov_contracts.id"), nullable=False),
        sa.Column("numero", sa.Integer, nullable=False),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=False),
        sa.Column("documento_sha256", sa.String(64), nullable=False),
        sa.Column("documento_titulo", sa.String(300), nullable=False),
        sa.Column("observacion", sa.String(1000), nullable=True),
        sa.Column("supervisor_assignment_id", sa.String(36), sa.ForeignKey("gov_contract_supervisors.id"), nullable=False),
        sa.Column("supervisor_official_id", sa.String(36), sa.ForeignKey("gov_officials.id"), nullable=False),
        sa.Column("supervisor_nombre", sa.String(200), nullable=False),
        sa.Column("representante_cargo_id", sa.String(36), sa.ForeignKey("gov_positions.id"), nullable=True),
        sa.Column("representante_cargo_nombre", sa.String(200), nullable=True),
        sa.Column("fin_garantia", sa.Date, nullable=True),
        sa.Column("estado", sa.String(10), nullable=False, server_default="CONFORME"),
        sa.Column("motivo_anulacion", sa.String(500), nullable=True),
        sa.Column("anulado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anulado_por", sa.String(36), nullable=True),
        sa.Column("registrado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registrado_por", sa.String(36), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger, nullable=False, server_default="1"),
        *_tiempos(),
        sa.UniqueConstraint("contract_id", "numero", name="uq_gov_contract_receipts_numero"),
        sa.CheckConstraint("tipo IN ('PARCIAL', 'PROVISIONAL', 'DEFINITIVA')", name="tipo"),
        sa.CheckConstraint("estado IN ('CONFORME', 'ANULADA')", name="estado"),
        sa.CheckConstraint("numero >= 1", name="numero"),
        sa.CheckConstraint("(tipo = 'PROVISIONAL') = (fin_garantia IS NOT NULL)", name="garantia"),
        sa.CheckConstraint("fin_garantia IS NULL OR fin_garantia >= fecha", name="garantia_fecha"),
        sa.CheckConstraint(
            "(representante_cargo_id IS NULL) = (representante_cargo_nombre IS NULL)", name="representante"
        ),
        sa.CheckConstraint(
            "(estado = 'ANULADA') = (motivo_anulacion IS NOT NULL AND anulado_en IS NOT NULL)",
            name="anulacion_motivada",
        ),
    )
    op.create_index("ix_gov_contract_receipts_company_id", "gov_contract_receipts", ["company_id"])
    op.create_index("ix_gov_contract_receipts_contract_id", "gov_contract_receipts", ["contract_id"])
    op.create_index(
        "uq_gov_contract_receipts_definitiva",
        "gov_contract_receipts",
        ["contract_id"],
        unique=True,
        postgresql_where=sa.text("tipo = 'DEFINITIVA' AND estado = 'CONFORME'"),
        sqlite_where=sa.text("tipo = 'DEFINITIVA' AND estado = 'CONFORME'"),
    )
    op.create_index(
        "uq_gov_contract_receipts_provisional",
        "gov_contract_receipts",
        ["contract_id"],
        unique=True,
        postgresql_where=sa.text("tipo = 'PROVISIONAL' AND estado = 'CONFORME'"),
        sqlite_where=sa.text("tipo = 'PROVISIONAL' AND estado = 'CONFORME'"),
    )

    op.create_table(
        "gov_contract_receipt_milestones",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("contract_id", sa.String(36), sa.ForeignKey("gov_contracts.id"), nullable=False),
        sa.Column("receipt_id", sa.String(36), sa.ForeignKey("gov_contract_receipts.id"), nullable=False),
        sa.Column("milestone_id", sa.String(36), sa.ForeignKey("gov_contract_milestones.id"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        *_tiempos(),
        sa.UniqueConstraint("receipt_id", "milestone_id", name="uq_gov_contract_receipt_milestones"),
    )
    op.create_index("ix_gov_contract_receipt_milestones_company_id", "gov_contract_receipt_milestones", ["company_id"])
    op.create_index("ix_gov_contract_receipt_milestones_contract_id", "gov_contract_receipt_milestones", ["contract_id"])
    op.create_index("ix_gov_contract_receipt_milestones_receipt_id", "gov_contract_receipt_milestones", ["receipt_id"])
    op.create_index("ix_gov_contract_receipt_milestones_milestone_id", "gov_contract_receipt_milestones", ["milestone_id"])

    op.create_table(
        "gov_contract_invoices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("contract_id", sa.String(36), sa.ForeignKey("gov_contracts.id"), nullable=False),
        sa.Column("numero", sa.Integer, nullable=False),
        sa.Column("numero_documento", sa.String(40), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("milestone_id", sa.String(36), sa.ForeignKey("gov_contract_milestones.id"), nullable=False),
        sa.Column("receipt_id", sa.String(36), sa.ForeignKey("gov_contract_receipts.id"), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=False),
        sa.Column("documento_sha256", sa.String(64), nullable=False),
        sa.Column("documento_titulo", sa.String(300), nullable=False),
        sa.Column("fecha_conformidad", sa.Date, nullable=False),
        sa.Column("supervisor_assignment_id", sa.String(36), sa.ForeignKey("gov_contract_supervisors.id"), nullable=False),
        sa.Column("supervisor_official_id", sa.String(36), sa.ForeignKey("gov_officials.id"), nullable=False),
        sa.Column("supervisor_nombre", sa.String(200), nullable=False),
        sa.Column("estado", sa.String(10), nullable=False, server_default="CONFORME"),
        sa.Column("motivo_anulacion", sa.String(500), nullable=True),
        sa.Column("anulado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anulado_por", sa.String(36), nullable=True),
        sa.Column("registrado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registrado_por", sa.String(36), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger, nullable=False, server_default="1"),
        *_tiempos(),
        sa.UniqueConstraint("contract_id", "numero", name="uq_gov_contract_invoices_numero"),
        sa.CheckConstraint("estado IN ('CONFORME', 'ANULADA')", name="estado"),
        sa.CheckConstraint("numero >= 1", name="numero"),
        sa.CheckConstraint("monto > 0", name="monto"),
        sa.CheckConstraint("length(moneda) = 3", name="moneda"),
        sa.CheckConstraint("fecha_conformidad >= fecha", name="conformidad"),
        sa.CheckConstraint(
            "(estado = 'ANULADA') = (motivo_anulacion IS NOT NULL AND anulado_en IS NOT NULL)",
            name="anulacion_motivada",
        ),
    )
    op.create_index("ix_gov_contract_invoices_company_id", "gov_contract_invoices", ["company_id"])
    op.create_index("ix_gov_contract_invoices_contract_id", "gov_contract_invoices", ["contract_id"])
    op.create_index("ix_gov_contract_invoices_milestone_id", "gov_contract_invoices", ["milestone_id"])
    op.create_index("ix_gov_contract_invoices_receipt_id", "gov_contract_invoices", ["receipt_id"])
    op.create_index(
        "uq_gov_contract_invoices_documento",
        "gov_contract_invoices",
        ["contract_id", "numero_documento"],
        unique=True,
        postgresql_where=sa.text("estado = 'CONFORME'"),
        sqlite_where=sa.text("estado = 'CONFORME'"),
    )

    if bind.dialect.name == "postgresql":
        op.execute(GOV_CONTRACT_EXEC_GUARD_FUNCION_PG)
        for tabla, argumentos in GOV_CONTRACT_EXEC_GUARDS:
            op.execute(
                f"CREATE OR REPLACE TRIGGER trg_{tabla}_guard BEFORE UPDATE OR DELETE ON {tabla} "
                f"FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_exec_guard({argumentos});"
            )
            op.execute(
                f"CREATE OR REPLACE TRIGGER trg_{tabla}_no_truncate BEFORE TRUNCATE ON {tabla} "
                f"FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_exec_guard();"
            )

    _conceder_permisos(bind)


def downgrade() -> None:
    bind = op.get_bind()
    permisos = bind.execute(
        sa.text("SELECT id FROM permissions WHERE resource = :r AND action = :a"),
        {"r": "gobierno_contratos", "a": "execute"},
    ).fetchall()
    for permiso in permisos:
        bind.execute(sa.text("DELETE FROM role_permissions WHERE permission_id = :p"), {"p": permiso[0]})
        bind.execute(sa.text("DELETE FROM permissions WHERE id = :p"), {"p": permiso[0]})

    if bind.dialect.name == "postgresql":
        for tabla, _ in GOV_CONTRACT_EXEC_GUARDS:
            op.execute(f"DROP TRIGGER IF EXISTS trg_{tabla}_guard ON {tabla}")
            op.execute(f"DROP TRIGGER IF EXISTS trg_{tabla}_no_truncate ON {tabla}")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_contract_exec_guard()")

    op.drop_index("uq_gov_contract_invoices_documento", table_name="gov_contract_invoices")
    op.drop_index("ix_gov_contract_invoices_receipt_id", table_name="gov_contract_invoices")
    op.drop_index("ix_gov_contract_invoices_milestone_id", table_name="gov_contract_invoices")
    op.drop_index("ix_gov_contract_invoices_contract_id", table_name="gov_contract_invoices")
    op.drop_index("ix_gov_contract_invoices_company_id", table_name="gov_contract_invoices")
    op.drop_table("gov_contract_invoices")

    op.drop_index("ix_gov_contract_receipt_milestones_milestone_id", table_name="gov_contract_receipt_milestones")
    op.drop_index("ix_gov_contract_receipt_milestones_receipt_id", table_name="gov_contract_receipt_milestones")
    op.drop_index("ix_gov_contract_receipt_milestones_contract_id", table_name="gov_contract_receipt_milestones")
    op.drop_index("ix_gov_contract_receipt_milestones_company_id", table_name="gov_contract_receipt_milestones")
    op.drop_table("gov_contract_receipt_milestones")

    op.drop_index("uq_gov_contract_receipts_provisional", table_name="gov_contract_receipts")
    op.drop_index("uq_gov_contract_receipts_definitiva", table_name="gov_contract_receipts")
    op.drop_index("ix_gov_contract_receipts_contract_id", table_name="gov_contract_receipts")
    op.drop_index("ix_gov_contract_receipts_company_id", table_name="gov_contract_receipts")
    op.drop_table("gov_contract_receipts")

    op.drop_index("ix_gov_contract_valuations_milestone_id", table_name="gov_contract_valuations")
    op.drop_index("ix_gov_contract_valuations_contract_id", table_name="gov_contract_valuations")
    op.drop_index("ix_gov_contract_valuations_company_id", table_name="gov_contract_valuations")
    op.drop_table("gov_contract_valuations")

    op.drop_index("uq_gov_contract_submissions_conforme", table_name="gov_contract_deliverable_submissions")
    op.drop_index("uq_gov_contract_submissions_abierta", table_name="gov_contract_deliverable_submissions")
    op.drop_index("ix_gov_contract_deliverable_submissions_deliverable_id", table_name="gov_contract_deliverable_submissions")
    op.drop_index("ix_gov_contract_deliverable_submissions_contract_id", table_name="gov_contract_deliverable_submissions")
    op.drop_index("ix_gov_contract_deliverable_submissions_company_id", table_name="gov_contract_deliverable_submissions")
    op.drop_table("gov_contract_deliverable_submissions")

    op.drop_index("ix_gov_contract_deliverables_milestone_id", table_name="gov_contract_deliverables")
    op.drop_index("ix_gov_contract_deliverables_contract_id", table_name="gov_contract_deliverables")
    op.drop_index("ix_gov_contract_deliverables_company_id", table_name="gov_contract_deliverables")
    op.drop_table("gov_contract_deliverables")

    op.drop_index("ix_gov_contract_milestones_contract_id", table_name="gov_contract_milestones")
    op.drop_index("ix_gov_contract_milestones_company_id", table_name="gov_contract_milestones")
    op.drop_table("gov_contract_milestones")

    op.drop_index("ix_gov_contract_execution_acts_contract_id", table_name="gov_contract_execution_acts")
    op.drop_index("ix_gov_contract_execution_acts_company_id", table_name="gov_contract_execution_acts")
    op.drop_table("gov_contract_execution_acts")
