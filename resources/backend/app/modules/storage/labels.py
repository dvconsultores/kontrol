"""Etiqueta operativa interna de almacén (no regulatoria)."""

from __future__ import annotations

import hashlib
import io
from datetime import UTC, datetime
from typing import Any

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.storage import generate_storage_key, get_storage
from app.modules.master_data.models import CatalogItem
from app.modules.organization.models import Company
from app.modules.storage import models as storage_models
from app.modules.storage import service as storage_service
from app.shared.audit import record_audit


def _cut(value: str, limit: int = 60) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "…"


def generate_label(
    db: Session,
    *,
    company_id: str,
    classification_id: str,
    actor_id: str,
    quantity: str | None,
    receipt_code: str | None,
    file_code: str | None,
    location_code: str | None = None,
) -> storage_models.StorageLabel:
    company = db.scalar(
        select(Company)
        .where(Company.id == company_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if company is None:
        raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")

    classification = db.scalar(
        select(storage_models.StorageClassification).where(
            storage_models.StorageClassification.id == classification_id,
            storage_models.StorageClassification.company_id == company_id,
            storage_models.StorageClassification.status == "CURRENT",
        )
    )
    if classification is None:
        raise NotFoundError(
            code="STORAGE_CLASSIFICATION_NOT_FOUND",
            message="Clasificación de almacenamiento no encontrada",
        )
    if classification.result != "CLASSIFIED":
        raise ConflictError(
            code="STORAGE_LABEL_NOT_APPLICABLE",
            message="La mercancía no está clasificada para etiquetar",
        )

    item = db.get(CatalogItem, classification.item_id)
    if item is None:
        raise NotFoundError(code="CATALOG_ITEM_NOT_FOUND", message="Producto no encontrado")

    sequence = (
        db.scalar(
            select(func.max(storage_models.StorageLabel.sequence)).where(
                storage_models.StorageLabel.company_id == company_id
            )
        )
        or 0
    ) + 1
    reference = f"ETQ-{sequence:06d}"

    pdf_bytes, sha256, size = _render_pdf(
        company=company,
        classification=classification,
        item=item,
        reference=reference,
        quantity=quantity,
        receipt_code=receipt_code,
        file_code=file_code,
        location_code=location_code,
    )

    storage = get_storage()
    storage_key = generate_storage_key(company_id)
    stored_size, stored_sha = storage.put(storage_key, io.BytesIO(pdf_bytes))
    if stored_sha != sha256 or stored_size != size:
        storage.delete(storage_key)
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            message="La etiqueta almacenada no coincide con su huella",
            status_code=500,
        )
    if not storage.verify(storage_key, sha256):
        storage.delete(storage_key)
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            message="La etiqueta almacenada no coincide con su huella",
            status_code=500,
        )

    label = storage_models.StorageLabel(
        created_by=actor_id,
        company_id=company_id,
        classification_id=classification_id,
        sequence=sequence,
        reference=reference,
        storage_key=storage_key,
        file_sha256=sha256,
        file_size=size,
        file_name=f"{reference}.pdf",
        generated_at=datetime.now(UTC),
        generated_by=actor_id,
        company_name=company.legal_name,
        product_code=item.code,
        product_name=item.name,
        quantity=quantity,
        receipt_code=receipt_code,
        file_code=file_code,
        zone_label=classification.target_label,
        location_code=location_code,
    )
    db.add(label)
    db.flush()

    record_audit(
        db,
        action="STORAGE_LABEL_GENERATED",
        entity_type="StorageLabel",
        entity_id=str(label.id),
        company_id=company_id,
        user_id=actor_id,
        after={
            "reference": reference,
            "classification_id": classification_id,
            "product_code": item.code,
        },
    )
    return label


def _render_pdf(
    *,
    company: Company,
    classification: storage_models.StorageClassification,
    item: CatalogItem,
    reference: str,
    quantity: str | None,
    receipt_code: str | None,
    file_code: str | None,
    location_code: str | None,
) -> tuple[bytes, str, int]:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(100 * mm, 70 * mm))
    width, height = 100 * mm, 70 * mm

    c.setTitle("Identificación interna de almacén")
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 12 * mm, "Identificación interna de almacén")

    c.setFont("Helvetica", 8)
    y = height - 20 * mm
    lines: list[str] = [
        _cut(company.legal_name),
        f"Producto: {_cut(item.code + ' · ' + item.name)}",
    ]
    if quantity is not None:
        lines.append(f"Cantidad: {_cut(quantity)}")
    if receipt_code:
        lines.append(f"Recepción: {_cut(receipt_code)}")
    if file_code:
        lines.append(f"Expediente: {_cut(file_code)}")
    lines.append(f"Zona: {_cut(classification.target_label or '')}")
    if location_code:
        lines.append(f"Ubicación: {_cut(location_code)}")
    lines.append(f"Referencia: {reference}")
    lines.append(f"Fecha: {datetime.now(UTC).isoformat()}")

    for line in lines:
        c.drawString(6 * mm, y, line)
        y -= 5 * mm

    qr = QrCodeWidget(reference)
    drawing = Drawing(22 * mm, 22 * mm)
    drawing.add(qr)
    renderPDF.draw(drawing, c, width - 26 * mm, height - 28 * mm)

    c.showPage()
    c.save()
    pdf_bytes = buf.getvalue()
    return pdf_bytes, hashlib.sha256(pdf_bytes).hexdigest(), len(pdf_bytes)


def open_label_pdf(db: Session, *, company_id: str, label_id: str) -> tuple[str, Any, int]:
    label = db.scalar(
        select(storage_models.StorageLabel).where(
            storage_models.StorageLabel.id == label_id,
            storage_models.StorageLabel.company_id == company_id,
        )
    )
    if label is None:
        raise NotFoundError(code="STORAGE_LABEL_NOT_FOUND", message="Etiqueta no encontrada")

    storage = get_storage()
    if not storage.verify(label.storage_key, label.file_sha256):
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            message="La etiqueta almacenada no coincide con su huella registrada",
            status_code=500,
        )
    return label.file_name, storage.open(label.storage_key), label.file_size


def label_dict(label: storage_models.StorageLabel) -> dict[str, Any]:
    return {
        "id": str(label.id),
        "reference": label.reference,
        "sequence": label.sequence,
        "file_name": label.file_name,
        "file_size": label.file_size,
        "generated_at": label.generated_at.isoformat(),
        "product_code": label.product_code,
        "product_name": label.product_name,
        "quantity": label.quantity,
        "receipt_code": label.receipt_code,
        "file_code": label.file_code,
        "zone_label": label.zone_label,
        "location_code": label.location_code,
        "classification_id": str(label.classification_id),
    }


def labels_for_classification(
    db: Session, company_id: str, classification_id: str
) -> list[storage_models.StorageLabel]:
    return list(
        db.scalars(
            select(storage_models.StorageLabel)
            .where(
                storage_models.StorageLabel.company_id == company_id,
                storage_models.StorageLabel.classification_id == classification_id,
            )
            .order_by(storage_models.StorageLabel.sequence.desc())
        ).all()
    )
