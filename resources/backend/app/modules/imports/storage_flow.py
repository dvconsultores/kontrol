"""Flujo de clasificación, etiquetado y put-away desde el expediente de importación."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.modules.identity_access.models import User
from app.modules.imports import physical_locations, service
from app.modules.imports.models import ImportFile
from app.modules.inventory import location_validation
from app.modules.inventory import service as inv_service
from app.modules.organization.models import WarehouseLocation
from app.modules.storage import labels
from app.modules.storage import models as storage_models
from app.modules.storage import service as storage_service


def _pending_rows(db: Session, file: ImportFile) -> list[dict[str, Any]]:
    logistics = service._logistics_detail(db, file)
    if logistics is None:
        return []
    return logistics["putaway_pending"] or []


def _current_classification(
    db: Session,
    company_id: str,
    warehouse_id: str,
    item_id: str,
    receipt_id: str | None,
) -> storage_models.StorageClassification | None:
    return db.scalar(
        select(storage_models.StorageClassification)
        .where(
            storage_models.StorageClassification.company_id == company_id,
            storage_models.StorageClassification.warehouse_id == warehouse_id,
            storage_models.StorageClassification.item_id == item_id,
            storage_models.StorageClassification.receipt_id.is_(None)
            if receipt_id is None
            else storage_models.StorageClassification.receipt_id == receipt_id,
            storage_models.StorageClassification.status == "CURRENT",
        )
        .order_by(storage_models.StorageClassification.classified_at.desc())
        .limit(1)
    )


def _candidates(
    db: Session,
    file: ImportFile,
    row: dict[str, Any],
    classification: storage_models.StorageClassification | None,
    policy: dict[str, Any],
) -> tuple[list[dict[str, Any]], bool, str | None]:
    all_locations = [
        {**location_validation.location_ref(db, str(loc.id)), "zone_id": loc.zone_id}
        for loc in inv_service.putaway_candidates(
            db, company_id=file.company_id, warehouse_id=row["warehouse_id"]
        )
    ]

    if policy["mode"] == "DISABLED":
        return all_locations, True, None

    if classification is None:
        return [], False, "Clasifique la mercancía antes de ubicar"

    if classification.result == "CLASSIFIED":
        class_dict = storage_service.classification_dict(db, classification)
        current_rule = db.get(storage_models.StorageRule, classification.rule_id) if classification.rule_id else None
        stale = (
            current_rule is None
            or current_rule.version != classification.rule_version
        )
        if stale:
            return [], False, "La regla de almacenamiento cambió: vuelva a clasificar"

        zone_ids = class_dict["zone_ids"]
        filtered = [loc for loc in all_locations if loc.get("zone_id") in zone_ids]
        if classification.label_policy == "REQUIRED":
            existing_labels = labels.labels_for_classification(
                db, file.company_id, str(classification.id)
            )
            if not existing_labels:
                return filtered, False, "Genere la etiqueta antes de ubicar"
        return filtered, True, None

    if classification.result == "AMBIGUOUS":
        return [], False, "Clasificación ambigua: revise las reglas de almacenamiento"

    if classification.result == "NO_RULE":
        if policy["on_no_rule"] == "ALLOW_ANY":
            return all_locations, True, None
        return (
            [],
            False,
            "No existe una regla de almacenamiento aplicable y la política del almacén no permite ubicar",
        )

    return all_locations, True, None


def file_storage_view(db: Session, file: ImportFile) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    receipts_by_code = {r.code: r for r in physical_locations.file_receipts(db, file)}

    for row in _pending_rows(db, file):
        receipt = receipts_by_code.get(row["receipt_code"])
        receipt_id = str(receipt.id) if receipt is not None else None
        policy = storage_service.get_policy(db, file.company_id, row["warehouse_id"])
        profile = storage_service.get_profile(db, file.company_id, row["product_id"])
        classification = _current_classification(
            db,
            file.company_id,
            row["warehouse_id"],
            row["product_id"],
            receipt_id,
        )
        classification_data: dict[str, Any] | None = None
        if classification is not None:
            classification_data = storage_service.classification_dict(db, classification)
            user = db.get(User, classification.classified_by)
            classification_data["classified_by_name"] = user.username if user is not None else None
            classification_labels = labels.labels_for_classification(
                db, file.company_id, str(classification.id)
            )
        else:
            classification_labels = []

        candidates, can_putaway, blocking_reason = _candidates(
            db, file, row, classification, policy
        )
        label_required = bool(
            classification is not None
            and classification.result == "CLASSIFIED"
            and classification.label_policy == "REQUIRED"
        )

        rows.append(
            {
                "receipt_id": receipt_id,
                "receipt_code": row["receipt_code"],
                "warehouse_id": row["warehouse_id"],
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "state": row["state"],
                "pending_base": row["pending_base"],
                "policy": policy,
                "profile": profile,
                "classification": classification_data,
                "labels": [labels.label_dict(lbl) for lbl in classification_labels],
                "label_required": label_required,
                "candidates": candidates,
                "can_putaway": can_putaway,
                "blocking_reason": blocking_reason,
            }
        )

    return {"rows": rows}


def classify_for_file(
    db: Session,
    *,
    file: ImportFile,
    receipt_id: str,
    product_id: str,
    state: str,
    actor_id: str,
) -> storage_models.StorageClassification:
    receipt = next((r for r in physical_locations.file_receipts(db, file) if str(r.id) == receipt_id), None)
    if receipt is None:
        raise NotFoundError(
            code="IMPORT_RECEIPT_NOT_IN_FILE",
            message="La recepción no pertenece al expediente",
        )

    pending = next(
        (
            row
            for row in _pending_rows(db, file)
            if row["receipt_code"] == receipt.code
            and row["product_id"] == product_id
            and row["state"] == state
        ),
        None,
    )
    if pending is None:
        raise ConflictError(
            code="STORAGE_NOTHING_PENDING",
            message="No hay mercancía pendiente de ubicar para clasificar",
        )

    return storage_service.classify(
        db,
        company_id=file.company_id,
        warehouse_id=str(receipt.warehouse_id),
        item_id=product_id,
        state=state,
        actor_id=actor_id,
        import_file_id=str(file.id),
        receipt_id=str(receipt.id),
        document_ref=receipt.code,
    )


def label_for_file(
    db: Session,
    *,
    file: ImportFile,
    classification_id: str,
    actor_id: str,
) -> storage_models.StorageLabel:
    classification = db.scalar(
        select(storage_models.StorageClassification).where(
            storage_models.StorageClassification.id == classification_id,
            storage_models.StorageClassification.company_id == file.company_id,
            storage_models.StorageClassification.import_file_id == str(file.id),
        )
    )
    if classification is None:
        raise NotFoundError(
            code="STORAGE_CLASSIFICATION_NOT_FOUND",
            message="Clasificación no encontrada para el expediente",
        )
    if classification.label_policy == "NOT_REQUIRED":
        raise ConflictError(
            code="STORAGE_LABEL_NOT_REQUIRED",
            message="La política de almacenamiento no requiere etiqueta",
        )

    quantity = None
    for row in _pending_rows(db, file):
        if row["receipt_code"] == classification.document_ref and row["product_id"] == classification.item_id:
            quantity = row["pending_base"]
            break

    return labels.generate_label(
        db,
        company_id=file.company_id,
        classification_id=classification_id,
        actor_id=actor_id,
        quantity=quantity,
        receipt_code=classification.document_ref,
        file_code=file.code,
    )


def putaway_for_file(
    db: Session,
    *,
    file: ImportFile,
    receipt_id: str,
    product_id: str,
    state: str,
    target_location_id: str,
    quantity: Decimal,
    actor_id: str,
) -> Any:
    receipt = next((r for r in physical_locations.file_receipts(db, file) if str(r.id) == receipt_id), None)
    if receipt is None:
        raise NotFoundError(
            code="IMPORT_RECEIPT_NOT_IN_FILE",
            message="La recepción no pertenece al expediente",
        )

    policy = storage_service.get_policy(db, file.company_id, str(receipt.warehouse_id))
    classification = _current_classification(
        db, file.company_id, str(receipt.warehouse_id), product_id, receipt_id
    )

    if policy["mode"] == "ENFORCED":
        if classification is None:
            raise ConflictError(
                code="STORAGE_CLASSIFICATION_REQUIRED",
                message="Clasifique la mercancía antes de ubicar",
            )
        if classification.result == "AMBIGUOUS":
            raise ConflictError(
                code="STORAGE_CLASSIFICATION_AMBIGUOUS",
                message="Clasificación ambigua: revise las reglas de almacenamiento",
            )
        if classification.result == "NO_RULE" and policy["on_no_rule"] == "BLOCK":
            raise ConflictError(
                code="STORAGE_NO_RULE_BLOCKED",
                message="No existe una regla de almacenamiento aplicable y la política no permite ubicar",
            )
        if classification.result == "CLASSIFIED":
            current_rule = db.get(storage_models.StorageRule, classification.rule_id) if classification.rule_id else None
            if current_rule is None or current_rule.version != classification.rule_version:
                raise ConflictError(
                    code="STORAGE_CLASSIFICATION_STALE",
                    message="La regla de almacenamiento cambió: vuelva a clasificar",
                )
            location = db.scalar(
                select(WarehouseLocation).where(
                    WarehouseLocation.id == target_location_id,
                    WarehouseLocation.company_id == file.company_id,
                )
            )
            if location is None:
                raise NotFoundError(code="LOCATION_NOT_FOUND", message="Ubicación no encontrada")
            class_dict = storage_service.classification_dict(db, classification)
            if location.zone_id not in class_dict["zone_ids"]:
                raise ConflictError(
                    code="LOCATION_OUTSIDE_DETERMINED_ZONE",
                    message="La ubicación no está en la zona determinada por la regla",
                )
            if classification.label_policy == "REQUIRED":
                existing_labels = labels.labels_for_classification(
                    db, file.company_id, str(classification.id)
                )
                if not existing_labels:
                    raise ConflictError(
                        code="STORAGE_LABEL_REQUIRED",
                        message="Genere la etiqueta antes de ubicar",
                    )

    return inv_service.putaway(
        db,
        company_id=file.company_id,
        warehouse_id=str(receipt.warehouse_id),
        product_id=product_id,
        target_location_id=target_location_id,
        quantity=quantity,
        state=state,
        document_ref=receipt.code,
        actor=actor_id,
    )
