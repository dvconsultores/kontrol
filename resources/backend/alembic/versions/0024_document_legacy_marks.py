"""Anotación del legado documental (Spec 046, F9).

Gobernada por `legacy-document-migration-matrix.md`, que es normativa.

**Esta migración no crea ni un solo `Document`.** Una URL, una ruta o un hash
sueltos no bastan para afirmar que existe un archivo: crear un documento por
cada texto dejaría un repositorio lleno de documentos que nadie puede abrir, con
apariencia de completitud (R-046-5, FR-046-111).

Lo único que hace es **anotar**: qué columna heredada contiene una referencia
documental, con qué valor y cómo se clasifica. El texto original permanece
intacto en su tabla; ninguna columna heredada se modifica ni se borra (§144).

Lee datos: **no** es válida en modo offline (`--sql`).

Revision ID: 0024_document_legacy_marks
Revises: 0023_document_model
Create Date: 2026-08-30
"""

from __future__ import annotations

import json
import uuid

import sqlalchemy as sa

from alembic import op

revision = "0024_document_legacy_marks"
down_revision = "0023_document_model"
branch_labels = None
depends_on = None

VALID_MANAGED_FILE = "VALID_MANAGED_FILE"
EXTERNAL_REFERENCE = "EXTERNAL_REFERENCE"
MISSING_FILE = "MISSING_FILE"
UNVERIFIED_LEGACY = "UNVERIFIED_LEGACY"
HASH_WITHOUT_FILE = "LEGACY_HASH_WITHOUT_FILE"

#: (tabla, columna, columna de empresa o None, clasificación base, nota)
#: Derivada de la matriz aprobada, no de una búsqueda ciega de nombres.
LEGACY_COLUMNS: tuple[tuple[str, str, str | None, str, str], ...] = (
    ("official_documents", "file_ref", "company_id", UNVERIFIED_LEGACY,
     "Evidencia regulatoria: texto sin binario verificable"),
    ("permit_instances", "file_ref", "company_id", UNVERIFIED_LEGACY,
     "Permiso: texto sin binario verificable"),
    ("official_registrations", "file_ref", "company_id", UNVERIFIED_LEGACY,
     "Registro oficial: texto sin binario verificable"),
    ("transport_vehicles", "documents", "company_id", UNVERIFIED_LEGACY,
     "Texto libre; su estructura la decidirá la Spec 035"),
    ("transport_drivers", "documents", "company_id", UNVERIFIED_LEGACY,
     "Texto libre; su estructura la decidirá la Spec 035"),
    ("homologation_records", "evidence_sha256", None, HASH_WITHOUT_FILE,
     "Hash sin binario: no se convierte en documento (R-046-5)"),
    ("license_renewal_requests", "payment_proof_ref", None, UNVERIFIED_LEGACY,
     "Comprobante de pago: la Spec 040 vinculará el archivo real"),
    ("party_bank_accounts", "evidence", None, UNVERIFIED_LEGACY,
     "Soporte de cuenta bancaria"),
    ("inventory_adjustments", "evidence_ref", "company_id", UNVERIFIED_LEGACY,
     "Soporte del ajuste"),
    ("legal_sources", "file_id", None, UNVERIFIED_LEGACY,
     "Puede referirse a una fuente externa, no a un archivo administrado"),
    ("report_exports", "file_ref", "company_id", VALID_MANAGED_FILE,
     "Exportación generada por el servidor; la Spec 050 conserva su mecanismo"),
    ("report_jobs", "result_ref", "company_id", VALID_MANAGED_FILE,
     "Resultado de trabajo; la Spec 050 conserva su mecanismo"),
)

#: Permisos que 046 añade. Recurso nuevo `documentos`, con la convención vigente
#: `recurso:acción` de la Spec 003. No se crea un RBAC paralelo.
PERMISSIONS = ("view", "create", "edit", "upload", "download", "link",
               "deactivate", "delete", "manage_types")


def _emit(report: dict) -> None:
    print("\n===== REPORTE DE ANOTACIÓN DOCUMENTAL LEGADA (0024) =====")
    print(json.dumps({k: v for k, v in report.items() if k != "details"},
                     indent=2, ensure_ascii=False))
    for row in report["details"][:200]:
        print(f"  [{row['classification']}] {row['table']}.{row['column']} "
              f"id={row['row_id']} · {row['note']}")
    if len(report["details"]) > 200:
        print(f"  … y {len(report['details']) - 200} más")
    print("===== FIN DEL REPORTE =====\n")


def _table_exists(bind, table: str) -> bool:
    return bind.dialect.has_table(bind, table)


def _column_exists(bind, table: str, column: str) -> bool:
    try:
        return column in {c["name"] for c in sa.inspect(bind).get_columns(table)}
    except Exception:  # noqa: BLE001
        return False


def upgrade() -> None:
    bind = op.get_bind()
    report: dict = {
        "migration_id": revision,
        "references_scanned": 0,
        "valid_managed_file": 0,
        "external_reference": 0,
        "missing_file": 0,
        "unverified_legacy": 0,
        "hash_without_file": 0,
        "documents_created": 0,      # debe ser 0 · R-046-5
        "columns_modified": 0,       # debe ser 0 · §144
        "details": [],
    }

    for table, column, company_col, classification, note in LEGACY_COLUMNS:
        if not _table_exists(bind, table) or not _column_exists(bind, table, column):
            continue
        select_company = f", {company_col}" if company_col and _column_exists(bind, table, company_col) else ", NULL"
        rows = bind.execute(sa.text(
            f"SELECT id, {column}{select_company} FROM {table} "
            f"WHERE {column} IS NOT NULL AND {column} <> ''"
        )).fetchall()

        for row_id, raw_value, company_id in rows:
            report["references_scanned"] += 1
            value = str(raw_value)
            final = classification
            # Una URL absoluta es una referencia externa, no un archivo nuestro.
            if final == UNVERIFIED_LEGACY and value.lower().startswith(("http://", "https://")):
                final = EXTERNAL_REFERENCE

            key = {
                VALID_MANAGED_FILE: "valid_managed_file",
                EXTERNAL_REFERENCE: "external_reference",
                MISSING_FILE: "missing_file",
                UNVERIFIED_LEGACY: "unverified_legacy",
                HASH_WITHOUT_FILE: "hash_without_file",
            }[final]
            report[key] += 1
            report["details"].append({
                "table": table, "column": column, "row_id": str(row_id),
                "classification": final, "note": note})

            bind.execute(sa.text(
                "INSERT INTO legacy_document_references "
                "(id, source_table, source_column, source_row_id, company_id, raw_value, "
                " classification, notes, created_at, updated_at) "
                "VALUES (:id,:t,:c,:r,:co,:v,:cl,:n,now(),now())"
            ), {"id": str(uuid.uuid4()), "t": table, "c": column, "r": str(row_id),
                "co": company_id, "v": value[:500], "cl": final, "n": note})

    _grant_permissions(bind)
    _emit(report)

    # Invariantes de la Spec, comprobadas en la propia migración.
    created = bind.execute(sa.text(
        "SELECT count(*) FROM legacy_document_references WHERE document_id IS NOT NULL")).scalar_one()
    if created:
        raise RuntimeError(
            f"{created} anotaciones crearon documento. La migración solo anota (R-046-5).")


def _grant_permissions(bind) -> None:
    admin = bind.execute(sa.text(
        "SELECT id FROM roles WHERE code = 'ADMIN' AND company_id IS NULL LIMIT 1")).fetchone()
    if not admin:
        return
    for action in PERMISSIONS:
        row = bind.execute(sa.text(
            "SELECT id FROM permissions WHERE resource = 'documentos' AND action = :a"),
            {"a": action}).fetchone()
        if row:
            permission_id = row[0]
        else:
            permission_id = str(uuid.uuid4())
            bind.execute(sa.text(
                "INSERT INTO permissions (id, resource, action, scope_type) "
                "VALUES (:id,'documentos',:a,'COMPANY')"), {"id": permission_id, "a": action})
        granted = bind.execute(sa.text(
            "SELECT 1 FROM role_permissions WHERE role_id = :r AND permission_id = :p"),
            {"r": admin[0], "p": permission_id}).fetchone()
        if not granted:
            bind.execute(sa.text(
                "INSERT INTO role_permissions (id, role_id, permission_id) VALUES (:id,:r,:p)"),
                {"id": str(uuid.uuid4()), "r": admin[0], "p": permission_id})


def downgrade() -> None:
    # Solo se borran las anotaciones: ninguna columna heredada se tocó.
    op.execute("DELETE FROM legacy_document_references")
