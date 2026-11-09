"""Servicio de reportes de diferencias de importación."""

from __future__ import annotations

import hashlib
import io
import json
import xml.sax.saxutils
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, BinaryIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.approvals.models import ApprovalRequest
from app.modules.documents.models import Document, DocumentLink, DocumentVersion, StoredFile
from app.modules.documents.storage import generate_storage_key, get_storage
from app.modules.identity_access.models import User
from app.modules.imports import service
from app.modules.imports.models import (
    ImportDifferenceReport,
    ImportDifferenceReportEvidence,
    ImportDifferenceReportIncident,
    ImportDifferenceReportLine,
    ImportFile,
)
from app.modules.master_data.models import CatalogItem, Party, Presentation, UnitOfMeasure
from app.modules.organization.models import Company, Warehouse
from app.modules.purchasing.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
    ReceiptIncident,
)
from app.shared.clock import zona_de_negocio

_DIFFERENCE_LABELS = {
    "FALTANTE": "Faltante",
    "SOBRANTE": "Sobrante",
    "DANO": "Daño",
    "REFERENCIA_INCORRECTA": "Referencia incorrecta",
    "DIFERENCIA_DOCUMENTAL": "Diferencia documental",
}

_INCIDENT_STATUS_LABELS = {
    "REGISTRADA": "Registrada",
    "ESCALADA": "Escalada",
    "PENDIENTE_AUTORIZACION": "Pendiente de autorización",
    "RESUELTA": "Resuelta",
}

_RESOLUTION_LABELS = {
    "AJUSTE_AUTORIZADO": "Ajuste autorizado",
    "RECLAMO_PROVEEDOR": "Reclamo al proveedor",
    "INVESTIGACION_INTERNA": "Investigación interna",
    "CUARENTENA": "Cuarentena",
}

_AUTHORIZATION_LABELS = {
    "NOT_REQUIRED": "No requerida",
}

_RESOURCE_TYPE_LABELS = {
    "GoodsReceipt": "Recepción",
    "ReceiptIncident": "Incidencia",
}

_UNAVAILABLE_USER = "Usuario no disponible"
_USABLE_WIDTH = letter[0] - 30 * mm


def _format_incident_datetime(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.astimezone(zona_de_negocio()).strftime("%d/%m/%Y %H:%M")
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return str(value)
    return parsed.astimezone(zona_de_negocio()).strftime("%d/%m/%Y %H:%M")


def _text(value: Any) -> str:
    if value is None:
        return ""
    return xml.sax.saxutils.escape(str(value))


def _decimal_to_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(Decimal(value).normalize(), "f")


def _to_serializable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return _decimal_to_str(value)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, dict):
        return {key: _to_serializable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_serializable(item) for item in value]
    return value


def _snapshot_hash(content: dict[str, Any]) -> str:
    payload = json.dumps(
        _to_serializable(content),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _resolve_user_names(
    db: Session,
    *,
    tenant_id: str,
    ids: set[str | None],
) -> dict[str, str]:
    valid_ids = {user_id for user_id in ids if user_id}
    if not valid_ids:
        return {}
    stmt = select(User.id, User.username).where(
        User.id.in_(valid_ids),
        User.tenant_id == tenant_id,
    )
    return {row.id: row.username for row in db.execute(stmt).all()}


def _name_for(user_id: str | None, names: dict[str, str]) -> str | None:
    if user_id is None:
        return None
    return names.get(user_id, _UNAVAILABLE_USER)


def _order_quantity_base(line: PurchaseOrderLine | None) -> Decimal | None:
    if line is None:
        return None
    if line.base_quantity_ordered is not None:
        return Decimal(line.base_quantity_ordered)
    if line.quantity_ordered is not None:
        return Decimal(line.quantity_ordered)
    return None


def _receipt_quantity_base(
    value: Decimal | None,
    fallback: Decimal | None,
) -> Decimal | None:
    if value is not None:
        return Decimal(value)
    if fallback is not None:
        return Decimal(fallback)
    return None


def _build_evidence(
    db: Session,
    *,
    company_id: str,
    receipt: GoodsReceipt,
    incidents: list[ReceiptIncident],
) -> list[dict[str, Any]]:
    incident_ids = [incident.id for incident in incidents]
    document_links_stmt = select(DocumentLink).where(
        DocumentLink.company_id == company_id,
        (
            (
                (DocumentLink.resource_type == "GoodsReceipt")
                & (DocumentLink.resource_id == receipt.id)
            )
            | (
                (DocumentLink.resource_type == "ReceiptIncident")
                & (DocumentLink.resource_id.in_(incident_ids))
            )
        ),
    )
    document_links = list(db.scalars(document_links_stmt).all())

    resource_codes: dict[str, str] = {str(receipt.id): receipt.code}
    for incident in incidents:
        resource_codes[str(incident.id)] = incident.code

    document_ids = {link.document_id for link in document_links if link.document_id}
    documents_by_id: dict[str, Document] = {}
    if document_ids:
        documents_stmt = select(Document).where(Document.id.in_(document_ids))
        documents = db.scalars(documents_stmt).all()
        documents_by_id = {str(document.id): document for document in documents}

    version_ids = {
        document.current_version_id
        for document in documents_by_id.values()
        if document.current_version_id
    }
    versions_by_id: dict[str, DocumentVersion] = {}
    stored_file_ids: set[str] = set()
    if version_ids:
        versions_stmt = select(DocumentVersion).where(DocumentVersion.id.in_(version_ids))
        versions = db.scalars(versions_stmt).all()
        versions_by_id = {str(version.id): version for version in versions}
        stored_file_ids = {version.stored_file_id for version in versions if version.stored_file_id}

    stored_files_by_id: dict[str, StoredFile] = {}
    if stored_file_ids:
        stored_files_stmt = select(StoredFile).where(StoredFile.id.in_(stored_file_ids))
        stored_files = db.scalars(stored_files_stmt).all()
        stored_files_by_id = {str(stored_file.id): stored_file for stored_file in stored_files}

    rows: list[dict[str, Any]] = []
    for link in sorted(
        document_links,
        key=lambda item: (
            item.resource_type,
            resource_codes.get(str(item.resource_id) if item.resource_id else "", ""),
            (
                documents_by_id[str(item.document_id)].title
                if item.document_id and str(item.document_id) in documents_by_id
                else ""
            ),
            item.id,
        ),
    ):
        document = documents_by_id.get(str(link.document_id)) if link.document_id else None
        title = document.title if document and document.title else "Documento sin título"
        version_number = None
        sha256 = None
        file_name = None
        version = None
        if document and document.current_version_id:
            version = versions_by_id.get(str(document.current_version_id))
        if version:
            version_number = version.version_number
            sha256 = version.sha256
            stored_file = stored_files_by_id.get(str(version.stored_file_id))
            if stored_file:
                file_name = stored_file.original_name
        rows.append(
            {
                "resource_type": link.resource_type,
                "resource_code": resource_codes.get(str(link.resource_id), str(link.resource_id)),
                "document_title": title,
                "version_number": version_number,
                "file_name": file_name,
                "sha256": sha256,
            }
        )
    return rows


def _build_snapshot(
    db: Session,
    *,
    file: ImportFile,
    receipt: GoodsReceipt,
    tenant_id: str,
) -> dict[str, Any]:
    company_id = file.company_id

    incidents_stmt = select(ReceiptIncident).where(
        ReceiptIncident.receipt_id == receipt.id,
        ReceiptIncident.company_id == company_id,
        ReceiptIncident.status != "ANULADA",
    ).order_by(ReceiptIncident.created_at, ReceiptIncident.code, ReceiptIncident.id)
    incidents = list(db.scalars(incidents_stmt).all())

    lines_stmt = select(GoodsReceiptLine).where(
        GoodsReceiptLine.receipt_id == receipt.id
    ).order_by(GoodsReceiptLine.created_at, GoodsReceiptLine.id)
    receipt_lines = list(db.scalars(lines_stmt).all())

    incident_line_ids = {
        incident.receipt_line_id for incident in incidents if incident.receipt_line_id
    }

    order_line_ids = {
        line.order_line_id for line in receipt_lines if line.order_line_id
    }
    order_lines_by_id: dict[str, PurchaseOrderLine] = {}
    if order_line_ids:
        order_lines_stmt = select(PurchaseOrderLine).where(PurchaseOrderLine.id.in_(order_line_ids))
        order_lines = db.scalars(order_lines_stmt).all()
        order_lines_by_id = {str(line.id): line for line in order_lines}

    product_ids = {line.product_id for line in receipt_lines if line.product_id}
    products_by_id: dict[str, CatalogItem] = {}
    if product_ids:
        products_stmt = select(CatalogItem).where(CatalogItem.id.in_(product_ids))
        products = db.scalars(products_stmt).all()
        products_by_id = {str(product.id): product for product in products}

    base_unit_ids = {
        product.base_unit_id
        for product in products_by_id.values()
        if product.base_unit_id
    }
    units_by_id: dict[str, UnitOfMeasure] = {}
    if base_unit_ids:
        units_stmt = select(UnitOfMeasure).where(UnitOfMeasure.id.in_(base_unit_ids))
        units = db.scalars(units_stmt).all()
        units_by_id = {str(unit.id): unit for unit in units}

    presentation_ids = {
        line.presentation_id for line in receipt_lines if line.presentation_id
    }
    presentations_by_id: dict[str, Presentation] = {}
    if presentation_ids:
        presentations_stmt = select(Presentation).where(Presentation.id.in_(presentation_ids))
        presentations = db.scalars(presentations_stmt).all()
        presentations_by_id = {str(presentation.id): presentation for presentation in presentations}

    user_ids: set[str | None] = set()
    user_ids.update(incident.created_by for incident in incidents)
    user_ids.update(
        incident.escalated_by for incident in incidents if incident.escalated_by
    )
    user_ids.update(
        incident.resolved_by for incident in incidents if incident.resolved_by
    )
    user_names = _resolve_user_names(db, tenant_id=tenant_id, ids=user_ids)

    approval_request_ids = {
        incident.approval_request_id
        for incident in incidents
        if incident.approval_request_id
    }
    approvals_by_id: dict[str, ApprovalRequest] = {}
    if approval_request_ids:
        approvals_stmt = select(ApprovalRequest).where(
            ApprovalRequest.id.in_(approval_request_ids)
        )
        approvals = db.scalars(approvals_stmt).all()
        approvals_by_id = {str(approval.id): approval for approval in approvals}

    snapshot_incidents: list[dict[str, Any]] = []
    for incident in incidents:
        product_name = None
        if incident.receipt_line_id:
            line = next(
                (
                    receipt_line
                    for receipt_line in receipt_lines
                    if receipt_line.id == incident.receipt_line_id
                ),
                None,
            )
            if line and line.product_id:
                product = products_by_id.get(str(line.product_id))
                if product:
                    product_name = product.name
        authorization_status = "NOT_REQUIRED"
        if incident.approval_request_id:
            approval = approvals_by_id.get(str(incident.approval_request_id))
            if approval:
                authorization_status = approval.status
        snapshot_incidents.append(
            {
                "incident_id": str(incident.id),
                "code": incident.code,
                "incident_type": incident.incident_type,
                "receipt_line_id": incident.receipt_line_id,
                "product_name": product_name,
                "affected_base_quantity": (
                    _decimal_to_str(Decimal(incident.affected_base_quantity))
                    if incident.affected_base_quantity is not None
                    else None
                ),
                "description": incident.description,
                "status": incident.status,
                "escalated_at": _to_serializable(incident.escalated_at),
                "escalated_by_name": _name_for(incident.escalated_by, user_names),
                "escalation_notes": incident.escalation_notes,
                "resolution": incident.resolution,
                "resolution_reason": incident.resolution_reason,
                "authorization_status": authorization_status,
                "resolved_at": _to_serializable(incident.resolved_at),
                "resolved_by_name": _name_for(incident.resolved_by, user_names),
                "registered_by_name": _name_for(incident.created_by, user_names),
            }
        )

    snapshot_lines: list[dict[str, Any]] = []
    for line in receipt_lines:
        has_incident = line.id in incident_line_ids
        difference_kinds = (line.count_difference_kinds or "").strip()
        has_observed_difference = bool(difference_kinds)
        has_overage = Decimal(line.overage_base_quantity or 0) > 0
        has_damaged = Decimal(line.damaged_quantity or 0) > 0
        if not (has_incident or has_observed_difference or has_overage or has_damaged):
            continue

        order_line = order_lines_by_id.get(str(line.order_line_id)) if line.order_line_id else None
        product = products_by_id.get(str(line.product_id)) if line.product_id else None
        unit = None
        if product and product.base_unit_id:
            unit = units_by_id.get(str(product.base_unit_id))
        presentation = (
            presentations_by_id.get(str(line.presentation_id))
            if line.presentation_id
            else None
        )

        snapshot_lines.append(
            {
                "receipt_line_id": str(line.id),
                "product_code": product.code if product else None,
                "product_name": product.name if product else None,
                "presentation_code": (
                    presentation.code if presentation else None
                ),
                "base_uom": unit.symbol if unit else None,
                "conversion_factor": (
                    _decimal_to_str(Decimal(line.conversion_factor_snapshot))
                    if line.conversion_factor_snapshot is not None
                    else None
                ),
                "ordered_base": _decimal_to_str(_order_quantity_base(order_line)),
                "received_base": _decimal_to_str(
                    _receipt_quantity_base(
                        line.base_quantity_received,
                        line.quantity_received,
                    )
                ),
                "counted_base": (
                    _decimal_to_str(Decimal(line.counted_base_quantity))
                    if line.counted_base_quantity is not None
                    else None
                ),
                "accepted_base": _decimal_to_str(
                    _receipt_quantity_base(
                        line.base_quantity_accepted,
                        line.quantity_accepted,
                    )
                ),
                "rejected_base": _decimal_to_str(
                    _receipt_quantity_base(
                        line.base_quantity_rejected,
                        line.quantity_rejected,
                    )
                ),
                "damaged_base": (
                    _decimal_to_str(Decimal(line.damaged_quantity))
                    if line.damaged_quantity is not None
                    else None
                ),
                "overage_base": (
                    _decimal_to_str(Decimal(line.overage_base_quantity))
                    if line.overage_base_quantity is not None
                    else None
                ),
                "difference_kinds": difference_kinds or None,
                "physical_condition": line.physical_condition,
                "observation": line.damage_notes,
            }
        )

    evidence_rows = _build_evidence(
        db,
        company_id=company_id,
        receipt=receipt,
        incidents=incidents,
    )

    company = db.get(Company, company_id)
    order = db.get(PurchaseOrder, file.order_id) if file.order_id else None
    supplier = db.get(Party, file.supplier_id) if file.supplier_id else None
    warehouse = db.get(Warehouse, receipt.warehouse_id) if receipt.warehouse_id else None

    header = {
        "company_name": (
            (company.trade_name or company.legal_name) if company else None
        ),
        "file_code": file.code,
        "order_code": order.code if order else None,
        "supplier_name": supplier.name if supplier else None,
        "receipt_code": receipt.code,
        "warehouse_name": warehouse.name if warehouse else None,
    }

    has_differences = bool(snapshot_incidents or snapshot_lines)

    return {
        "header": header,
        "lines": snapshot_lines,
        "incidents": snapshot_incidents,
        "evidence": evidence_rows,
        "has_differences": has_differences,
    }


def _receipt_for_file(
    db: Session,
    *,
    file: ImportFile,
    receipt_id: str,
) -> GoodsReceipt:
    if file.order_id is None:
        raise NotFoundError(
            code="IMPORT_RECEIPT_NOT_IN_FILE",
            message="Recepción no encontrada",
        )
    receipt = db.scalar(
        select(GoodsReceipt).where(
            GoodsReceipt.id == receipt_id,
            GoodsReceipt.company_id == file.company_id,
            GoodsReceipt.order_id == file.order_id,
        )
    )
    if receipt is None:
        raise NotFoundError(
            code="IMPORT_RECEIPT_NOT_IN_FILE",
            message="Recepción no encontrada",
        )
    return receipt


def _report_for_file(
    db: Session,
    *,
    file: ImportFile,
    report_id: str,
) -> ImportDifferenceReport:
    report = db.scalar(
        select(ImportDifferenceReport).where(
            ImportDifferenceReport.id == report_id,
            ImportDifferenceReport.company_id == file.company_id,
            ImportDifferenceReport.import_file_id == file.id,
        )
    )
    if report is None:
        raise NotFoundError(
            code="IMPORT_DIFFERENCE_REPORT_NOT_FOUND",
            message="Reporte de diferencias no encontrado",
        )
    return report


def _report_summary(
    report: ImportDifferenceReport,
    *,
    latest_revision: int | None,
) -> dict[str, Any]:
    return {
        "id": str(report.id),
        "reference": report.reference,
        "revision": report.revision,
        "issued_at": _to_serializable(report.issued_at),
        "issued_by_name": report.issued_by_name,
        "snapshot_hash": report.snapshot_hash,
        "supersedes_id": report.supersedes_id,
        "file_name": report.file_name,
        "file_size": report.file_size,
        "is_latest": (
            latest_revision is not None and report.revision == latest_revision
        ),
    }


def current_state(
    db: Session,
    *,
    file: ImportFile,
    receipt_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    receipt = _receipt_for_file(db, file=file, receipt_id=receipt_id)
    snapshot = _build_snapshot(db, file=file, receipt=receipt, tenant_id=tenant_id)

    reports = list(
        db.scalars(
            select(ImportDifferenceReport)
            .where(
                ImportDifferenceReport.receipt_id == receipt.id,
                ImportDifferenceReport.company_id == file.company_id,
            )
            .order_by(ImportDifferenceReport.revision.desc())
        ).all()
    )

    latest = reports[0] if reports else None
    current_hash: str | None = None

    if not snapshot["has_differences"]:
        state = "NO_DIFFERENCES"
    else:
        current_hash = _snapshot_hash(snapshot)
        if not latest:
            state = "DIFFERENCES_WITHOUT_REPORT"
        else:
            state = "REPORT_ISSUED" if latest.snapshot_hash == current_hash else "NEW_REVISION_AVAILABLE"

    return {
        "receipt_id": str(receipt.id),
        "receipt_code": receipt.code,
        "state": state,
        "has_differences": snapshot["has_differences"],
        "current_snapshot_hash": current_hash,
        "lines": _to_serializable(snapshot["lines"]),
        "incidents": _to_serializable(snapshot["incidents"]),
        "evidence": _to_serializable(snapshot["evidence"]),
        "reports": [
            _report_summary(
                report,
                latest_revision=latest.revision if latest else None,
            )
            for report in reports
        ],
    }


def _label_pairs_line(line: dict[str, Any]) -> list[tuple[str, str]]:
    difference_label = None
    if line.get("difference_kinds"):
        kinds = line["difference_kinds"].split(",")
        difference_label = ", ".join(
            _DIFFERENCE_LABELS.get(kind.strip(), kind.strip())
            for kind in kinds
            if kind.strip()
        )
    return [
        ("Producto", line.get("product_name") or ""),
        ("Código", line.get("product_code") or ""),
        ("Presentación", line.get("presentation_code") or ""),
        ("Unidad base", line.get("base_uom") or ""),
        ("Factor", line.get("conversion_factor") or ""),
        ("Cantidad ordenada", line.get("ordered_base") or ""),
        ("Cantidad recibida", line.get("received_base") or ""),
        ("Cantidad contada", line.get("counted_base") or ""),
        ("Cantidad aceptada", line.get("accepted_base") or ""),
        ("Cantidad rechazada", line.get("rejected_base") or ""),
        ("Cantidad dañada", line.get("damaged_base") or ""),
        ("Cantidad sobrante", line.get("overage_base") or ""),
        ("Diferencias", difference_label or ""),
        ("Condición física", line.get("physical_condition") or ""),
        ("Observación", line.get("observation") or ""),
    ]


def _label_pairs_incident(incident: dict[str, Any]) -> list[tuple[str, str]]:
    incident_type_label = _DIFFERENCE_LABELS.get(
        incident.get("incident_type") or "",
        incident.get("incident_type") or "",
    )
    status_label = _INCIDENT_STATUS_LABELS.get(
        incident.get("status") or "",
        incident.get("status") or "",
    )
    treatment = incident.get("resolution")
    treatment_label = (
        "Pendiente"
        if not treatment
        else _RESOLUTION_LABELS.get(treatment, treatment)
    )
    authorization_label = _AUTHORIZATION_LABELS.get(
        incident.get("authorization_status") or "",
        incident.get("authorization_status") or "",
    )
    return [
        ("Código", incident.get("code") or ""),
        ("Tipo", incident_type_label or ""),
        ("Producto", incident.get("product_name") or ""),
        ("Cantidad afectada", incident.get("affected_base_quantity") or ""),
        ("Descripción", incident.get("description") or ""),
        ("Estado", status_label or ""),
        ("Escalamiento", _format_incident_datetime(incident.get("escalated_at"))),
        ("Escalado por", incident.get("escalated_by_name") or ""),
        ("Notas de escalamiento", incident.get("escalation_notes") or ""),
        ("Tratamiento", treatment_label or ""),
        ("Motivo", incident.get("resolution_reason") or ""),
        ("Autorización", authorization_label or ""),
        ("Resolución", _format_incident_datetime(incident.get("resolved_at"))),
        ("Resuelta por", incident.get("resolved_by_name") or ""),
        ("Registrada por", incident.get("registered_by_name") or ""),
    ]


def _label_pairs_evidence(evidence: dict[str, Any]) -> list[tuple[str, str]]:
    resource_type_label = _RESOURCE_TYPE_LABELS.get(
        evidence.get("resource_type") or "",
        evidence.get("resource_type") or "",
    )
    return [
        ("Tipo de recurso", resource_type_label or ""),
        ("Código", evidence.get("resource_code") or ""),
        ("Título", evidence.get("document_title") or ""),
        ("Versión", evidence.get("version_number") or ""),
        ("Archivo", evidence.get("file_name") or ""),
    ]


def _render_pdf(
    *,
    reference: str,
    revision: int,
    supersedes_reference: str | None,
    issued_at: datetime,
    snapshot: dict[str, Any],
    issuer_name: str,
) -> bytes:
    styles = {
        "title": ParagraphStyle(
            name="TitleStyle",
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
        ),
        "label": ParagraphStyle(
            name="LabelStyle",
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
        ),
        "value": ParagraphStyle(
            name="ValueStyle",
            fontName="Helvetica",
            fontSize=7,
            leading=9,
        ),
        "h2": ParagraphStyle(
            name="Heading2",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            spaceBefore=10,
            spaceAfter=4,
        ),
    }

    def styled(value: str | None, style: str = "value") -> Paragraph:
        return Paragraph(_text(value or ""), styles[style])

    def build_pair_table(
        rows: list[tuple[str, str]],
        *,
        col_widths: list[float] | None = None,
    ) -> Table:
        widths = col_widths or [40 * mm, _USABLE_WIDTH - 40 * mm]
        table_data = [
            [styled(label, "label"), styled(value, "value")]
            for label, value in rows
        ]
        table = Table(table_data, colWidths=widths)
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#999999")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    (
                        "BACKGROUND",
                        (0, 0),
                        (0, -1),
                        colors.HexColor("#F2F2F2"),
                    ),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        return table

    header = snapshot["header"]
    business_date = issued_at.astimezone(zona_de_negocio()).strftime("%d/%m/%Y %H:%M")

    story: list[Any] = [
        Paragraph("Reporte formal de diferencias de importación", styles["title"]),
        Spacer(1, 4 * mm),
    ]

    header_rows: list[tuple[str, str]] = [
        ("Referencia", reference),
        ("Revisión", str(revision)),
    ]
    if supersedes_reference:
        header_rows.append(("Reemplaza a", supersedes_reference))
    header_rows.extend(
        [
            ("Empresa", header.get("company_name") or ""),
            ("Expediente", header.get("file_code") or ""),
            ("Orden", header.get("order_code") or ""),
            ("Proveedor", header.get("supplier_name") or ""),
            ("Recepción", header.get("receipt_code") or ""),
            ("Almacén", header.get("warehouse_name") or ""),
            ("Fecha de emisión", business_date),
            ("Emisor", issuer_name),
        ]
    )
    story.append(build_pair_table(header_rows))
    story.append(Paragraph("Líneas con diferencias", styles["h2"]))
    if snapshot["lines"]:
        for line in snapshot["lines"]:
            story.append(build_pair_table(_label_pairs_line(line)))
            story.append(Spacer(1, 3 * mm))
    else:
        story.append(Paragraph("Sin líneas con diferencias.", styles["value"]))

    document_incidents = [
        incident
        for incident in snapshot["incidents"]
        if incident.get("incident_type") == "DIFERENCIA_DOCUMENTAL"
    ]
    story.append(Paragraph("Diferencias documentales", styles["h2"]))
    if document_incidents:
        for incident in document_incidents:
            pairs = [
                label_value
                for label_value in _label_pairs_incident(incident)
                if label_value[0] in {"Código", "Descripción", "Registrada por"}
            ]
            story.append(build_pair_table(pairs))
            story.append(Spacer(1, 3 * mm))
    else:
        story.append(Paragraph("Sin diferencias documentales", styles["value"]))

    story.append(Paragraph("Incidencias", styles["h2"]))
    if snapshot["incidents"]:
        for incident in snapshot["incidents"]:
            story.append(build_pair_table(_label_pairs_incident(incident)))
            story.append(Spacer(1, 3 * mm))
    else:
        story.append(Paragraph("Sin incidencias registradas.", styles["value"]))

    story.append(Paragraph("Evidencias", styles["h2"]))
    if snapshot["evidence"]:
        for evidence in snapshot["evidence"]:
            story.append(build_pair_table(_label_pairs_evidence(evidence)))
            story.append(Spacer(1, 3 * mm))
    else:
        story.append(Paragraph("Sin evidencias adjuntas", styles["value"]))

    story.extend(
        [
            Spacer(1, 6 * mm),
            Paragraph(
                "Referencia interna. No es un documento fiscal.",
                styles["value"],
            ),
        ]
    )

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=reference,
    )
    document.build(story)
    return buffer.getvalue()


def issue_report(
    db: Session,
    *,
    file: ImportFile,
    receipt_id: str,
    expected_snapshot_hash: str | None,
    actor_id: str,
    tenant_id: str,
) -> ImportDifferenceReport:
    company = db.scalar(
        select(Company)
        .where(Company.id == file.company_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if company is None:
        raise NotFoundError(code="IMPORT_NOT_FOUND", message="Importación no encontrada")

    file_locked = db.scalar(
        select(ImportFile)
        .where(
            ImportFile.id == file.id,
            ImportFile.company_id == file.company_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if file_locked is None:
        raise NotFoundError(code="IMPORT_NOT_FOUND", message="Importación no encontrada")
    if file_locked.status == "CANCELLED":
        raise ConflictError(
            code="IMPORT_CANCELLED",
            message="La importación está cancelada",
        )

    receipt = db.scalar(
        select(GoodsReceipt)
        .where(
            GoodsReceipt.id == receipt_id,
            GoodsReceipt.company_id == file.company_id,
            GoodsReceipt.order_id == file.order_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if receipt is None:
        raise NotFoundError(
            code="IMPORT_RECEIPT_NOT_IN_FILE",
            message="Recepción no encontrada",
        )
    if receipt.status == "CANCELLED":
        raise ConflictError(
            code="RECEIPT_CANCELLED",
            message="La recepción está cancelada",
        )

    snapshot = _build_snapshot(db, file=file, receipt=receipt, tenant_id=tenant_id)
    if not snapshot["has_differences"]:
        raise KontrolError(
            code="DIFFERENCE_REPORT_NO_DIFFERENCES",
            message="No hay diferencias que reportar",
            status_code=422,
        )

    current_hash = _snapshot_hash(snapshot)
    if expected_snapshot_hash is not None and expected_snapshot_hash != current_hash:
        raise ConflictError(
            code="DIFFERENCE_REPORT_STALE",
            message="La información cambió; recargue el estado del reporte",
            details={"current_snapshot_hash": current_hash},
        )

    latest = db.scalar(
        select(ImportDifferenceReport)
        .where(
            ImportDifferenceReport.receipt_id == receipt.id,
            ImportDifferenceReport.company_id == file.company_id,
        )
        .order_by(ImportDifferenceReport.revision.desc())
        .limit(1)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if latest and latest.snapshot_hash == current_hash:
        raise ConflictError(
            code="DIFFERENCE_REPORT_UNCHANGED",
            message="No hay cambios en las diferencias desde la última revisión",
            details={"report_id": str(latest.id), "reference": latest.reference},
        )

    if latest:
        revision = latest.revision + 1
        chain_number = latest.chain_number
        supersedes_id = str(latest.id)
        supersedes_reference = latest.reference
    else:
        revision = 1
        max_chain = db.scalar(
            select(func.max(ImportDifferenceReport.chain_number)).where(
                ImportDifferenceReport.company_id == file.company_id
            )
        )
        chain_number = (max_chain or 0) + 1
        supersedes_id = None
        supersedes_reference = None

    reference = f"DIF-{chain_number:06d}-R{revision}"
    issued_at = datetime.now(UTC)

    actor_names = _resolve_user_names(db, tenant_id=tenant_id, ids={actor_id})
    actor_name = actor_names.get(actor_id, _UNAVAILABLE_USER)

    pdf_bytes = _render_pdf(
        reference=reference,
        revision=revision,
        supersedes_reference=supersedes_reference,
        issued_at=issued_at,
        snapshot=snapshot,
        issuer_name=actor_name,
    )

    storage = get_storage()
    storage_key = generate_storage_key(file.company_id)
    size, sha = storage.put(storage_key, io.BytesIO(pdf_bytes))
    if sha != hashlib.sha256(pdf_bytes).hexdigest() or size != len(pdf_bytes):
        storage.delete(storage_key)
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            message="El reporte almacenado no coincide con su huella",
            status_code=500,
        )
    if not storage.verify(storage_key, sha):
        storage.delete(storage_key)
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            message="El reporte almacenado no coincide con su huella",
            status_code=500,
        )

    report = ImportDifferenceReport(
        company_id=file.company_id,
        import_file_id=file.id,
        receipt_id=receipt.id,
        chain_number=chain_number,
        revision=revision,
        reference=reference,
        supersedes_id=supersedes_id,
        issued_at=issued_at,
        issued_by=actor_id,
        issued_by_name=actor_name,
        company_name=snapshot["header"]["company_name"],
        file_code=snapshot["header"]["file_code"],
        order_code=snapshot["header"]["order_code"],
        supplier_name=snapshot["header"]["supplier_name"],
        receipt_code=snapshot["header"]["receipt_code"],
        warehouse_name=snapshot["header"]["warehouse_name"],
        line_count=len(snapshot["lines"]),
        incident_count=len(snapshot["incidents"]),
        evidence_count=len(snapshot["evidence"]),
        snapshot_hash=current_hash,
        storage_key=storage_key,
        file_sha256=sha,
        file_size=size,
        file_name=f"{reference}.pdf",
        created_by=actor_id,
    )
    db.add(report)
    try:
        db.flush()
    except IntegrityError as exc:
        storage.delete(storage_key)
        raise ConflictError(
            code="DIFFERENCE_REPORT_CONCURRENT",
            message="Otra revisión del reporte se emitió al mismo tiempo",
        ) from exc

    for position, line in enumerate(snapshot["lines"], start=1):
        db.add(
            ImportDifferenceReportLine(
                company_id=file.company_id,
                report_id=report.id,
                position=position,
                receipt_line_id=line["receipt_line_id"],
                product_code=line["product_code"],
                product_name=line["product_name"],
                presentation_code=line["presentation_code"],
                base_uom=line["base_uom"],
                conversion_factor=(
                    Decimal(line["conversion_factor"])
                    if line["conversion_factor"] is not None
                    else None
                ),
                ordered_base=(
                    Decimal(line["ordered_base"])
                    if line["ordered_base"] is not None
                    else None
                ),
                received_base=(
                    Decimal(line["received_base"])
                    if line["received_base"] is not None
                    else None
                ),
                counted_base=(
                    Decimal(line["counted_base"])
                    if line["counted_base"] is not None
                    else None
                ),
                accepted_base=(
                    Decimal(line["accepted_base"])
                    if line["accepted_base"] is not None
                    else None
                ),
                rejected_base=(
                    Decimal(line["rejected_base"])
                    if line["rejected_base"] is not None
                    else None
                ),
                damaged_base=(
                    Decimal(line["damaged_base"])
                    if line["damaged_base"] is not None
                    else None
                ),
                overage_base=(
                    Decimal(line["overage_base"])
                    if line["overage_base"] is not None
                    else None
                ),
                difference_kinds=line["difference_kinds"],
                physical_condition=line["physical_condition"],
                observation=line["observation"],
                created_by=actor_id,
            )
        )

    for position, incident in enumerate(snapshot["incidents"], start=1):
        db.add(
            ImportDifferenceReportIncident(
                company_id=file.company_id,
                report_id=report.id,
                position=position,
                incident_id=incident["incident_id"],
                code=incident["code"],
                incident_type=incident["incident_type"],
                receipt_line_id=incident["receipt_line_id"],
                product_name=incident["product_name"],
                affected_base_quantity=(
                    Decimal(incident["affected_base_quantity"])
                    if incident["affected_base_quantity"] is not None
                    else None
                ),
                description=incident["description"],
                status=incident["status"],
                escalated_at=(
                    datetime.fromisoformat(incident["escalated_at"])
                    if incident["escalated_at"] is not None
                    else None
                ),
                escalated_by_name=incident["escalated_by_name"],
                escalation_notes=incident["escalation_notes"],
                resolution=incident["resolution"],
                resolution_reason=incident["resolution_reason"],
                authorization_status=incident["authorization_status"],
                resolved_at=(
                    datetime.fromisoformat(incident["resolved_at"])
                    if incident["resolved_at"] is not None
                    else None
                ),
                resolved_by_name=incident["resolved_by_name"],
                registered_by_name=incident["registered_by_name"],
                created_by=actor_id,
            )
        )

    for position, evidence in enumerate(snapshot["evidence"], start=1):
        db.add(
            ImportDifferenceReportEvidence(
                company_id=file.company_id,
                report_id=report.id,
                position=position,
                resource_type=evidence["resource_type"],
                resource_code=evidence["resource_code"],
                document_title=evidence["document_title"],
                version_number=evidence["version_number"],
                file_name=evidence["file_name"],
                sha256=evidence["sha256"],
                created_by=actor_id,
            )
        )

    db.flush()

    audit_after = {
        "report_id": str(report.id),
        "reference": report.reference,
        "revision": report.revision,
        "receipt_code": receipt.code,
    }
    if revision == 1:
        service._audit(
            db,
            action="IMPORT_DIFFERENCE_REPORT_ISSUED",
            file=file,
            actor_id=actor_id,
            tenant_id=tenant_id,
            after=audit_after,
        )
    else:
        service._audit(
            db,
            action="IMPORT_DIFFERENCE_REPORT_REISSUED",
            file=file,
            actor_id=actor_id,
            tenant_id=tenant_id,
            after=audit_after,
        )

    return report


def report_detail(
    db: Session,
    *,
    file: ImportFile,
    report_id: str,
) -> dict[str, Any]:
    report = _report_for_file(db, file=file, report_id=report_id)

    lines = list(
        db.scalars(
            select(ImportDifferenceReportLine)
            .where(ImportDifferenceReportLine.report_id == report.id)
            .order_by(ImportDifferenceReportLine.position)
        ).all()
    )
    incidents = list(
        db.scalars(
            select(ImportDifferenceReportIncident)
            .where(ImportDifferenceReportIncident.report_id == report.id)
            .order_by(ImportDifferenceReportIncident.position)
        ).all()
    )
    evidence = list(
        db.scalars(
            select(ImportDifferenceReportEvidence)
            .where(ImportDifferenceReportEvidence.report_id == report.id)
            .order_by(ImportDifferenceReportEvidence.position)
        ).all()
    )

    supersedes_reference = None
    if report.supersedes_id:
        supersedes = db.get(ImportDifferenceReport, report.supersedes_id)
        if supersedes:
            supersedes_reference = supersedes.reference

    superseded_by = db.scalar(
        select(ImportDifferenceReport.id).where(
            ImportDifferenceReport.supersedes_id == report.id
        )
    )

    return {
        "id": str(report.id),
        "reference": report.reference,
        "revision": report.revision,
        "chain_number": report.chain_number,
        "supersedes_id": report.supersedes_id,
        "supersedes_reference": supersedes_reference,
        "superseded_by": str(superseded_by) if superseded_by else None,
        "issued_at": _to_serializable(report.issued_at),
        "issued_by": report.issued_by,
        "issued_by_name": report.issued_by_name,
        "company_name": report.company_name,
        "file_code": report.file_code,
        "order_code": report.order_code,
        "supplier_name": report.supplier_name,
        "receipt_code": report.receipt_code,
        "warehouse_name": report.warehouse_name,
        "line_count": report.line_count,
        "incident_count": report.incident_count,
        "evidence_count": report.evidence_count,
        "snapshot_hash": report.snapshot_hash,
        "file_sha256": report.file_sha256,
        "file_size": report.file_size,
        "file_name": report.file_name,
        "lines": [
            {
                "position": line.position,
                "receipt_line_id": line.receipt_line_id,
                "product_code": line.product_code,
                "product_name": line.product_name,
                "presentation_code": line.presentation_code,
                "base_uom": line.base_uom,
                "conversion_factor": _decimal_to_str(line.conversion_factor),
                "ordered_base": _decimal_to_str(line.ordered_base),
                "received_base": _decimal_to_str(line.received_base),
                "counted_base": _decimal_to_str(line.counted_base),
                "accepted_base": _decimal_to_str(line.accepted_base),
                "rejected_base": _decimal_to_str(line.rejected_base),
                "damaged_base": _decimal_to_str(line.damaged_base),
                "overage_base": _decimal_to_str(line.overage_base),
                "difference_kinds": line.difference_kinds,
                "physical_condition": line.physical_condition,
                "observation": line.observation,
            }
            for line in lines
        ],
        "incidents": [
            {
                "position": incident.position,
                "incident_id": incident.incident_id,
                "code": incident.code,
                "incident_type": incident.incident_type,
                "receipt_line_id": incident.receipt_line_id,
                "product_name": incident.product_name,
                "affected_base_quantity": _decimal_to_str(
                    incident.affected_base_quantity
                ),
                "description": incident.description,
                "status": incident.status,
                "escalated_at": _to_serializable(incident.escalated_at),
                "escalated_by_name": incident.escalated_by_name,
                "escalation_notes": incident.escalation_notes,
                "resolution": incident.resolution,
                "resolution_reason": incident.resolution_reason,
                "authorization_status": incident.authorization_status,
                "resolved_at": _to_serializable(incident.resolved_at),
                "resolved_by_name": incident.resolved_by_name,
                "registered_by_name": incident.registered_by_name,
            }
            for incident in incidents
        ],
        "evidence": [
            {
                "position": evidence_item.position,
                "resource_type": evidence_item.resource_type,
                "resource_code": evidence_item.resource_code,
                "document_title": evidence_item.document_title,
                "version_number": evidence_item.version_number,
                "file_name": evidence_item.file_name,
                "sha256": evidence_item.sha256,
            }
            for evidence_item in evidence
        ],
    }


def open_report_pdf(
    db: Session,
    *,
    file: ImportFile,
    report_id: str,
    actor_id: str,
    tenant_id: str,
) -> tuple[str, BinaryIO, int]:
    report = _report_for_file(db, file=file, report_id=report_id)

    storage = get_storage()
    if not storage.verify(report.storage_key, report.file_sha256):
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            message="El reporte almacenado no coincide con su huella registrada",
            status_code=500,
        )

    stream = storage.open(report.storage_key)

    service._audit(
        db,
        action="IMPORT_DIFFERENCE_REPORT_DOWNLOADED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        after={
            "report_id": str(report.id),
            "reference": report.reference,
            "revision": report.revision,
        },
    )

    return report.file_name, stream, report.file_size


def reports_for_receipt(
    db: Session,
    *,
    company_id: str,
    receipt_id: str,
) -> dict[str, Any]:
    receipt = db.scalar(
        select(GoodsReceipt).where(
            GoodsReceipt.id == receipt_id,
            GoodsReceipt.company_id == company_id,
        )
    )
    if receipt is None:
        raise NotFoundError(
            code="RECEIPT_NOT_FOUND",
            message="Recepción no encontrada",
        )

    file = db.scalar(
        select(ImportFile)
        .where(
            ImportFile.company_id == company_id,
            ImportFile.order_id == receipt.order_id,
            ImportFile.status != "CANCELLED",
        )
        .order_by(ImportFile.created_at)
        .limit(1)
    )

    reports = list(
        db.scalars(
            select(ImportDifferenceReport)
            .where(
                ImportDifferenceReport.receipt_id == receipt.id,
                ImportDifferenceReport.company_id == company_id,
            )
            .order_by(ImportDifferenceReport.revision.desc())
        ).all()
    )
    latest = reports[0] if reports else None

    return {
        "receipt_id": str(receipt.id),
        "receipt_code": receipt.code,
        "import_file_id": str(file.id) if file else None,
        "import_file_code": file.code if file else None,
        "reports": [
            _report_summary(
                report,
                latest_revision=latest.revision if latest else None,
            )
            for report in reports
        ],
    }
