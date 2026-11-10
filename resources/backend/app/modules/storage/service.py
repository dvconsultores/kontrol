from datetime import date, datetime, UTC
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.master_data.models import CatalogItem, TaxonomyNode, UnitOfMeasure
from app.modules.master_data.uom import physical_factor
from app.modules.organization.models import Warehouse, WarehouseZone, ZoneType
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio

from app.modules.storage import models as storage_models


def _warehouse(db: Session, company_id: str, warehouse_id: str) -> Warehouse:
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.company_id != company_id:
        raise NotFoundError(code="WAREHOUSE_NOT_FOUND", message="Almacén no encontrado")
    return warehouse


def _item(db: Session, company_id: str, item_id: str) -> CatalogItem:
    item = db.get(CatalogItem, item_id)
    if item is None or item.company_id != company_id or item.item_type != "PRODUCT":
        raise NotFoundError(code="PRODUCT_NOT_FOUND", message="Producto no encontrado")
    return item


def _taxonomy(db: Session, company_id: str, taxonomy_id: str) -> TaxonomyNode:
    node = db.get(TaxonomyNode, taxonomy_id)
    if node is None or node.company_id != company_id:
        raise NotFoundError(code="TAXONOMY_NOT_FOUND", message="Nodo de taxonomía no encontrado")
    return node


def _condition(db: Session, company_id: str, condition_id: str) -> storage_models.StorageCondition:
    condition = db.get(storage_models.StorageCondition, condition_id)
    if condition is None or condition.company_id != company_id:
        raise NotFoundError(code="STORAGE_CONDITION_NOT_FOUND", message="Condición de almacenamiento no encontrada")
    return condition


def _size_class(db: Session, company_id: str, size_class_id: str) -> storage_models.StorageSizeClass:
    size_class = db.get(storage_models.StorageSizeClass, size_class_id)
    if size_class is None or size_class.company_id != company_id:
        raise NotFoundError(code="STORAGE_SIZE_CLASS_NOT_FOUND", message="Clase de tamaño no encontrada")
    return size_class


def _zone_type(db: Session, company_id: str, zone_type_id: str) -> ZoneType:
    zone_type = db.get(ZoneType, zone_type_id)
    if zone_type is None or zone_type.company_id != company_id:
        raise NotFoundError(code="ZONE_TYPE_NOT_FOUND", message="Tipo de zona no encontrado")
    if zone_type.status != "ACTIVE":
        raise ConflictError(code="ZONE_TYPE_INACTIVE", message="El tipo de zona está inactivo")
    return zone_type


def _zone(db: Session, company_id: str, zone_id: str, warehouse_id: str) -> WarehouseZone:
    zone = db.get(WarehouseZone, zone_id)
    if zone is None or zone.company_id != company_id:
        raise NotFoundError(code="ZONE_NOT_FOUND", message="Zona no encontrada")
    if zone.warehouse_id != warehouse_id:
        raise ConflictError(code="ZONE_OTHER_WAREHOUSE", message="La zona pertenece a otro almacén")
    if zone.status != "ACTIVE":
        raise ConflictError(code="ZONE_INACTIVE", message="La zona está inactiva")
    return zone


def _unit(db: Session, company_id: str, unit_id: str, dimensions: tuple[str, ...]) -> UnitOfMeasure:
    unit = db.get(UnitOfMeasure, unit_id)
    if unit is None or (unit.company_id is not None and unit.company_id != company_id):
        raise NotFoundError(code="UNIT_NOT_FOUND", message="Unidad no encontrada")
    if unit.company_id is None and unit.dimension not in dimensions:
        raise KontrolError(
            code="UOM_DIMENSION_MISMATCH",
            message=f"La unidad {unit.symbol} no corresponde a {', '.join(dimensions)}",
            status_code=422,
        )
    if unit.company_id is not None and unit.dimension not in dimensions:
        raise KontrolError(
            code="UOM_DIMENSION_MISMATCH",
            message=f"La unidad {unit.symbol} no corresponde a {', '.join(dimensions)}",
            status_code=422,
        )
    return unit


def _audit_after_condition(condition: storage_models.StorageCondition) -> dict[str, Any]:
    return {"code": condition.code, "name": condition.name, "status": condition.status}


def create_condition(
    db: Session,
    *,
    company_id: str,
    code: str,
    name: str,
    description: str | None,
    actor_id: str,
) -> storage_models.StorageCondition:
    existing = db.scalars(
        select(storage_models.StorageCondition).where(
            storage_models.StorageCondition.company_id == company_id,
            storage_models.StorageCondition.code == code,
        )
    ).first()
    if existing is not None:
        raise ConflictError(
            code="STORAGE_CONDITION_CODE_TAKEN",
            message="El código de condición ya está en uso",
        )
    condition = storage_models.StorageCondition(
        company_id=company_id,
        code=code,
        name=name,
        description=description,
        status="ACTIVE",
        created_by=actor_id,
    )
    db.add(condition)
    db.flush()
    record_audit(
        db,
        action="STORAGE_CONDITION_CREATED",
        entity_type="StorageCondition",
        entity_id=str(condition.id),
        company_id=company_id,
        user_id=actor_id,
        after=_audit_after_condition(condition),
    )
    return condition


def update_condition(
    db: Session,
    *,
    company_id: str,
    condition_id: str,
    expected_version: int,
    name: str | None = None,
    description: str | None = None,
    status: str | None = None,
    actor_id: str,
) -> storage_models.StorageCondition:
    condition = db.scalars(
        select(storage_models.StorageCondition)
        .where(
            storage_models.StorageCondition.id == condition_id,
            storage_models.StorageCondition.company_id == company_id,
        )
        .with_for_update()
    ).first()
    if condition is None:
        raise NotFoundError(code="STORAGE_CONDITION_NOT_FOUND", message="Condición de almacenamiento no encontrada")
    if condition.version != expected_version:
        raise ConflictError(code="VERSION_CONFLICT", message="La versión no coincide. Recargue e intente de nuevo.")
    if status is not None and status not in ("ACTIVE", "INACTIVE"):
        raise KontrolError(code="INVALID_STATUS", message="Estado inválido", status_code=422)
    before = _audit_after_condition(condition)
    if name is not None:
        condition.name = name
    if description is not None:
        condition.description = description
    if status is not None:
        condition.status = status
    condition.version += 1
    after = _audit_after_condition(condition)
    record_audit(
        db,
        action="STORAGE_CONDITION_UPDATED",
        entity_type="StorageCondition",
        entity_id=str(condition.id),
        company_id=company_id,
        user_id=actor_id,
        before={"name": before["name"], "status": before["status"]},
        after={"name": after["name"], "status": after["status"]},
    )
    return condition


def list_conditions(db: Session, company_id: str) -> list[storage_models.StorageCondition]:
    return list(
        db.scalars(
            select(storage_models.StorageCondition)
            .where(storage_models.StorageCondition.company_id == company_id)
            .order_by(storage_models.StorageCondition.code)
        ).all()
    )


def _audit_after_size_class(size_class: storage_models.StorageSizeClass) -> dict[str, Any]:
    return {"code": size_class.code, "name": size_class.name, "status": size_class.status}


def create_size_class(
    db: Session,
    *,
    company_id: str,
    code: str,
    name: str,
    description: str | None,
    actor_id: str,
) -> storage_models.StorageSizeClass:
    existing = db.scalars(
        select(storage_models.StorageSizeClass).where(
            storage_models.StorageSizeClass.company_id == company_id,
            storage_models.StorageSizeClass.code == code,
        )
    ).first()
    if existing is not None:
        raise ConflictError(
            code="STORAGE_SIZE_CLASS_CODE_TAKEN",
            message="El código de clase de tamaño ya está en uso",
        )
    size_class = storage_models.StorageSizeClass(
        company_id=company_id,
        code=code,
        name=name,
        description=description,
        status="ACTIVE",
        created_by=actor_id,
    )
    db.add(size_class)
    db.flush()
    record_audit(
        db,
        action="STORAGE_SIZE_CLASS_CREATED",
        entity_type="StorageSizeClass",
        entity_id=str(size_class.id),
        company_id=company_id,
        user_id=actor_id,
        after=_audit_after_size_class(size_class),
    )
    return size_class


def update_size_class(
    db: Session,
    *,
    company_id: str,
    size_class_id: str,
    expected_version: int,
    name: str | None = None,
    description: str | None = None,
    status: str | None = None,
    actor_id: str,
) -> storage_models.StorageSizeClass:
    size_class = db.scalars(
        select(storage_models.StorageSizeClass)
        .where(
            storage_models.StorageSizeClass.id == size_class_id,
            storage_models.StorageSizeClass.company_id == company_id,
        )
        .with_for_update()
    ).first()
    if size_class is None:
        raise NotFoundError(code="STORAGE_SIZE_CLASS_NOT_FOUND", message="Clase de tamaño no encontrada")
    if size_class.version != expected_version:
        raise ConflictError(code="VERSION_CONFLICT", message="La versión no coincide. Recargue e intente de nuevo.")
    if status is not None and status not in ("ACTIVE", "INACTIVE"):
        raise KontrolError(code="INVALID_STATUS", message="Estado inválido", status_code=422)
    before = _audit_after_size_class(size_class)
    if name is not None:
        size_class.name = name
    if description is not None:
        size_class.description = description
    if status is not None:
        size_class.status = status
    size_class.version += 1
    after = _audit_after_size_class(size_class)
    record_audit(
        db,
        action="STORAGE_SIZE_CLASS_UPDATED",
        entity_type="StorageSizeClass",
        entity_id=str(size_class.id),
        company_id=company_id,
        user_id=actor_id,
        before={"name": before["name"], "status": before["status"]},
        after={"name": after["name"], "status": after["status"]},
    )
    return size_class


def list_size_classes(db: Session, company_id: str) -> list[storage_models.StorageSizeClass]:
    return list(
        db.scalars(
            select(storage_models.StorageSizeClass)
            .where(storage_models.StorageSizeClass.company_id == company_id)
            .order_by(storage_models.StorageSizeClass.code)
        ).all()
    )


def _physical_text(value: Decimal | None, unit: UnitOfMeasure | None) -> str | None:
    if value is None or unit is None:
        return None
    return f"{value} {unit.symbol}"


def save_profile(
    db: Session,
    *,
    company_id: str,
    item_id: str,
    weight_value: Decimal | None,
    weight_unit_id: str | None,
    volume_value: Decimal | None,
    volume_unit_id: str | None,
    size_class_id: str | None,
    condition_ids: list[str],
    expected_version: int | None,
    actor_id: str,
) -> storage_models.ProductStorageProfile:
    item = _item(db, company_id, item_id)
    if (weight_value is None) != (weight_unit_id is None):
        raise KontrolError(code="WEIGHT_UNIT_REQUIRED", message="El peso requiere unidad", status_code=422)
    if (volume_value is None) != (volume_unit_id is None):
        raise KontrolError(code="VOLUME_UNIT_REQUIRED", message="El volumen requiere unidad", status_code=422)
    if weight_value is not None and weight_value <= 0:
        raise KontrolError(code="INVALID_PHYSICAL_VALUE", message="El peso debe ser mayor que cero", status_code=422)
    if volume_value is not None and volume_value <= 0:
        raise KontrolError(code="INVALID_PHYSICAL_VALUE", message="El volumen debe ser mayor que cero", status_code=422)
    weight_unit = None
    volume_unit = None
    if weight_unit_id is not None:
        weight_unit = _unit(db, company_id, weight_unit_id, ("MASA", "PESO"))
    if volume_unit_id is not None:
        volume_unit = _unit(db, company_id, volume_unit_id, ("VOLUMEN",))
    if size_class_id is not None:
        _size_class(db, company_id, size_class_id)
    unique_condition_ids = list(dict.fromkeys(condition_ids))
    conditions = []
    for condition_id in unique_condition_ids:
        condition = _condition(db, company_id, condition_id)
        if condition.status != "ACTIVE":
            raise ConflictError(
                code="STORAGE_CONDITION_INACTIVE",
                message="La condición de almacenamiento está inactiva",
            )
        conditions.append(condition)

    profile = db.scalars(
        select(storage_models.ProductStorageProfile)
        .where(storage_models.ProductStorageProfile.company_id == company_id)
        .where(storage_models.ProductStorageProfile.item_id == item_id)
    ).first()

    if profile is None:
        if expected_version is not None:
            raise ConflictError(code="VERSION_CONFLICT", message="El perfil no existe; expected_version debe ser null")
        profile = storage_models.ProductStorageProfile(
            company_id=company_id,
            item_id=item.id,
            weight_value=weight_value,
            weight_unit_id=weight_unit_id,
            volume_value=volume_value,
            volume_unit_id=volume_unit_id,
            size_class_id=size_class_id,
            created_by=actor_id,
        )
        db.add(profile)
        db.flush()
    else:
        db.refresh(profile, with_for_update=True)
        if expected_version is None or profile.version != expected_version:
            raise ConflictError(code="VERSION_CONFLICT", message="Versión del perfil incorrecta")
        profile.weight_value = weight_value
        profile.weight_unit_id = weight_unit_id
        profile.volume_value = volume_value
        profile.volume_unit_id = volume_unit_id
        profile.size_class_id = size_class_id
        profile.version += 1
        db.execute(
            delete(storage_models.ProductStorageCondition).where(
                storage_models.ProductStorageCondition.profile_id == profile.id
            )
        )

    for condition in conditions:
        db.add(
            storage_models.ProductStorageCondition(
                company_id=company_id,
                profile_id=profile.id,
                condition_id=condition.id,
                created_by=actor_id,
            )
        )
    db.flush()

    audit_after = {
        "item_id": item.id,
        "weight": _physical_text(profile.weight_value, weight_unit),
        "volume": _physical_text(profile.volume_value, volume_unit),
        "size_class_id": profile.size_class_id,
        "condition_ids": [c.id for c in conditions],
    }
    record_audit(
        db,
        action="PRODUCT_STORAGE_PROFILE_SAVED",
        entity_type="ProductStorageProfile",
        entity_id=str(profile.id),
        company_id=company_id,
        user_id=actor_id,
        after=audit_after,
    )
    return profile


def profile_dict(db: Session, profile: storage_models.ProductStorageProfile) -> dict[str, Any]:
    weight_unit = db.get(UnitOfMeasure, profile.weight_unit_id) if profile.weight_unit_id else None
    volume_unit = db.get(UnitOfMeasure, profile.volume_unit_id) if profile.volume_unit_id else None
    size_class = db.get(storage_models.StorageSizeClass, profile.size_class_id) if profile.size_class_id else None
    condition_rows = db.scalars(
        select(storage_models.StorageCondition)
        .join(
            storage_models.ProductStorageCondition,
            storage_models.ProductStorageCondition.condition_id == storage_models.StorageCondition.id,
        )
        .where(storage_models.ProductStorageCondition.profile_id == profile.id)
        .order_by(storage_models.StorageCondition.code)
    ).all()
    return {
        "id": str(profile.id),
        "item_id": profile.item_id,
        "version": profile.version,
        "weight_value": str(profile.weight_value) if profile.weight_value is not None else None,
        "weight_unit": (
            {"id": str(weight_unit.id), "symbol": weight_unit.symbol, "name": weight_unit.name}
            if weight_unit
            else None
        ),
        "volume_value": str(profile.volume_value) if profile.volume_value is not None else None,
        "volume_unit": (
            {"id": str(volume_unit.id), "symbol": volume_unit.symbol, "name": volume_unit.name}
            if volume_unit
            else None
        ),
        "size_class": (
            {"id": str(size_class.id), "code": size_class.code, "name": size_class.name}
            if size_class
            else None
        ),
        "conditions": [
            {"id": str(c.id), "code": c.code, "name": c.name} for c in condition_rows
        ],
    }


def get_profile(db: Session, company_id: str, item_id: str) -> dict[str, Any] | None:
    profile = db.scalars(
        select(storage_models.ProductStorageProfile)
        .where(storage_models.ProductStorageProfile.company_id == company_id)
        .where(storage_models.ProductStorageProfile.item_id == item_id)
    ).first()
    return profile_dict(db, profile) if profile else None


def _rule_after_dict(rule: storage_models.StorageRule) -> dict[str, Any]:
    return {
        "code": rule.code,
        "name": rule.name,
        "priority": rule.priority,
        "status": rule.status,
        "label_policy": rule.label_policy,
        "target_zone_id": rule.target_zone_id,
        "target_zone_type_id": rule.target_zone_type_id,
        "version": rule.version,
    }


def _validate_rule_data(
    db: Session,
    company_id: str,
    data: dict[str, Any],
) -> None:
    target_zone_id = data.get("target_zone_id")
    target_zone_type_id = data.get("target_zone_type_id")
    if (target_zone_id is None) == (target_zone_type_id is None):
        raise KontrolError(code="RULE_TARGET_REQUIRED", message="Debe indicar exactamente un destino", status_code=422)
    warehouse_id = data.get("warehouse_id")
    if target_zone_id is not None:
        if warehouse_id is None:
            raise KontrolError(code="RULE_ZONE_NEEDS_WAREHOUSE", message="La zona exige almacén", status_code=422)
        _zone(db, company_id, target_zone_id, warehouse_id)
    if target_zone_type_id is not None:
        _zone_type(db, company_id, target_zone_type_id)

    has_criterion = any(
        data.get(k) is not None
        for k in (
            "taxonomy_id",
            "size_class_id",
            "condition_id",
            "min_weight",
            "max_weight",
            "min_volume",
            "max_volume",
        )
    )
    if not has_criterion:
        raise KontrolError(code="RULE_CRITERION_REQUIRED", message="La regla debe tener al menos un criterio", status_code=422)

    priority = data.get("priority")
    if priority is None or priority < 1:
        raise KontrolError(code="INVALID_PRIORITY", message="La prioridad debe ser mayor o igual a 1", status_code=422)

    label_policy = data.get("label_policy")
    if label_policy not in ("REQUIRED", "OPTIONAL", "NOT_REQUIRED"):
        raise KontrolError(
            code="INVALID_LABEL_POLICY",
            message="Política de etiqueta inválida",
            status_code=422,
        )

    status = data.get("status", "ACTIVE")
    if status not in ("ACTIVE", "INACTIVE"):
        raise KontrolError(code="INVALID_STATUS", message="Estado inválido", status_code=422)

    valid_from = data.get("valid_from")
    valid_to = data.get("valid_to")
    if valid_from is not None and valid_to is not None and valid_to < valid_from:
        raise KontrolError(code="INVALID_VALIDITY", message="Rango de vigencia inválido", status_code=422)

    if warehouse_id is not None:
        _warehouse(db, company_id, warehouse_id)
    if data.get("taxonomy_id") is not None:
        _taxonomy(db, company_id, data["taxonomy_id"])
    if data.get("size_class_id") is not None:
        _size_class(db, company_id, data["size_class_id"])
    if data.get("condition_id") is not None:
        _condition(db, company_id, data["condition_id"])

    for prefix, unit_key, dimensions in (
        ("weight", "weight_unit_id", ("MASA", "PESO")),
        ("volume", "volume_unit_id", ("VOLUMEN",)),
    ):
        min_key = f"min_{prefix}"
        max_key = f"max_{prefix}"
        min_val = data.get(min_key)
        max_val = data.get(max_key)
        if min_val is not None or max_val is not None:
            if data.get(unit_key) is None:
                raise KontrolError(
                    code=f"{prefix.upper()}_UNIT_REQUIRED",
                    message=f"El rango de {prefix} requiere unidad",
                    status_code=422,
                )
            _unit(db, company_id, data[unit_key], dimensions)
            if min_val is not None and min_val <= 0:
                raise KontrolError(code="INVALID_RANGE", message=f"{prefix} mínimo inválido", status_code=422)
            if max_val is not None and max_val <= 0:
                raise KontrolError(code="INVALID_RANGE", message=f"{prefix} máximo inválido", status_code=422)
            if min_val is not None and max_val is not None and min_val > max_val:
                raise KontrolError(code="INVALID_RANGE", message="Rango inválido", status_code=422)


def create_rule(
    db: Session,
    *,
    company_id: str,
    data: dict[str, Any],
    actor_id: str,
) -> storage_models.StorageRule:
    _validate_rule_data(db, company_id, data)
    code = data["code"]
    existing = db.scalars(
        select(storage_models.StorageRule).where(
            storage_models.StorageRule.company_id == company_id,
            storage_models.StorageRule.code == code,
        )
    ).first()
    if existing is not None:
        raise ConflictError(code="STORAGE_RULE_CODE_TAKEN", message="El código de regla ya está en uso")
    rule = storage_models.StorageRule(
        company_id=company_id,
        created_by=actor_id,
        code=code,
        name=data["name"],
        priority=data["priority"],
        status=data.get("status", "ACTIVE"),
        valid_from=data.get("valid_from"),
        valid_to=data.get("valid_to"),
        warehouse_id=data.get("warehouse_id"),
        taxonomy_id=data.get("taxonomy_id"),
        size_class_id=data.get("size_class_id"),
        condition_id=data.get("condition_id"),
        min_weight=data.get("min_weight"),
        max_weight=data.get("max_weight"),
        weight_unit_id=data.get("weight_unit_id"),
        min_volume=data.get("min_volume"),
        max_volume=data.get("max_volume"),
        volume_unit_id=data.get("volume_unit_id"),
        target_zone_id=data.get("target_zone_id"),
        target_zone_type_id=data.get("target_zone_type_id"),
        label_policy=data["label_policy"],
    )
    db.add(rule)
    db.flush()
    record_audit(
        db,
        action="STORAGE_RULE_CREATED",
        entity_type="StorageRule",
        entity_id=str(rule.id),
        company_id=company_id,
        user_id=actor_id,
        after=_rule_after_dict(rule),
    )
    return rule


def update_rule(
    db: Session,
    *,
    company_id: str,
    rule_id: str,
    expected_version: int,
    data: dict[str, Any],
    actor_id: str,
) -> storage_models.StorageRule:
    rule = db.scalars(
        select(storage_models.StorageRule)
        .where(storage_models.StorageRule.id == rule_id)
        .where(storage_models.StorageRule.company_id == company_id)
        .with_for_update()
    ).first()
    if rule is None:
        raise NotFoundError(code="RULE_NOT_FOUND", message="Regla no encontrada")
    if rule.version != expected_version:
        raise ConflictError(code="VERSION_CONFLICT", message="Versión de regla incorrecta")

    merged: dict[str, Any] = {
        "code": rule.code,
        "name": rule.name,
        "priority": rule.priority,
        "status": rule.status,
        "warehouse_id": rule.warehouse_id,
        "valid_from": rule.valid_from,
        "valid_to": rule.valid_to,
        "taxonomy_id": rule.taxonomy_id,
        "size_class_id": rule.size_class_id,
        "condition_id": rule.condition_id,
        "min_weight": rule.min_weight,
        "max_weight": rule.max_weight,
        "weight_unit_id": rule.weight_unit_id,
        "min_volume": rule.min_volume,
        "max_volume": rule.max_volume,
        "volume_unit_id": rule.volume_unit_id,
        "target_zone_id": rule.target_zone_id,
        "target_zone_type_id": rule.target_zone_type_id,
        "label_policy": rule.label_policy,
    }
    for key, value in data.items():
        if key != "expected_version":
            merged[key] = value
    _validate_rule_data(db, company_id, merged)
    if "code" in data and data["code"] != rule.code:
        existing = db.scalars(
            select(storage_models.StorageRule).where(
                storage_models.StorageRule.company_id == company_id,
                storage_models.StorageRule.code == data["code"],
            )
        ).first()
        if existing is not None:
            raise ConflictError(code="STORAGE_RULE_CODE_TAKEN", message="El código de regla ya está en uso")

    before = _rule_after_dict(rule)
    for key, value in merged.items():
        setattr(rule, key, value)
    rule.version += 1
    after = _rule_after_dict(rule)
    record_audit(
        db,
        action="STORAGE_RULE_UPDATED",
        entity_type="StorageRule",
        entity_id=str(rule.id),
        company_id=company_id,
        user_id=actor_id,
        before={
            "code": before["code"],
            "name": before["name"],
            "priority": before["priority"],
            "status": before["status"],
            "label_policy": before["label_policy"],
            "target_zone_id": before["target_zone_id"],
            "target_zone_type_id": before["target_zone_type_id"],
            "version": before["version"],
        },
        after={
            "code": after["code"],
            "name": after["name"],
            "priority": after["priority"],
            "status": after["status"],
            "label_policy": after["label_policy"],
            "target_zone_id": after["target_zone_id"],
            "target_zone_type_id": after["target_zone_type_id"],
            "version": after["version"],
        },
    )
    return rule


def rule_dict(db: Session, rule: storage_models.StorageRule) -> dict[str, Any]:
    taxonomy_name = None
    if rule.taxonomy_id is not None:
        node = db.get(TaxonomyNode, rule.taxonomy_id)
        taxonomy_name = node.name if node else None
    size_class_name = None
    if rule.size_class_id is not None:
        size_class = db.get(storage_models.StorageSizeClass, rule.size_class_id)
        size_class_name = size_class.name if size_class else None
    condition_name = None
    if rule.condition_id is not None:
        condition = db.get(storage_models.StorageCondition, rule.condition_id)
        condition_name = condition.name if condition else None
    weight_unit_symbol = None
    if rule.weight_unit_id is not None:
        weight_unit = db.get(UnitOfMeasure, rule.weight_unit_id)
        weight_unit_symbol = weight_unit.symbol if weight_unit else None
    volume_unit_symbol = None
    if rule.volume_unit_id is not None:
        volume_unit = db.get(UnitOfMeasure, rule.volume_unit_id)
        volume_unit_symbol = volume_unit.symbol if volume_unit else None
    warehouse_code = None
    if rule.warehouse_id is not None:
        warehouse = db.get(Warehouse, rule.warehouse_id)
        warehouse_code = warehouse.code if warehouse else None

    return {
        "id": str(rule.id),
        "code": rule.code,
        "name": rule.name,
        "priority": rule.priority,
        "status": rule.status,
        "valid_from": str(rule.valid_from) if rule.valid_from else None,
        "valid_to": str(rule.valid_to) if rule.valid_to else None,
        "warehouse_id": rule.warehouse_id,
        "warehouse_code": warehouse_code,
        "taxonomy_id": rule.taxonomy_id,
        "taxonomy_name": taxonomy_name,
        "size_class_id": rule.size_class_id,
        "size_class_name": size_class_name,
        "condition_id": rule.condition_id,
        "condition_name": condition_name,
        "min_weight": str(rule.min_weight) if rule.min_weight is not None else None,
        "max_weight": str(rule.max_weight) if rule.max_weight is not None else None,
        "weight_unit_id": rule.weight_unit_id,
        "weight_unit_symbol": weight_unit_symbol,
        "min_volume": str(rule.min_volume) if rule.min_volume is not None else None,
        "max_volume": str(rule.max_volume) if rule.max_volume is not None else None,
        "volume_unit_id": rule.volume_unit_id,
        "volume_unit_symbol": volume_unit_symbol,
        "target_zone_id": rule.target_zone_id,
        "target_zone_type_id": rule.target_zone_type_id,
        "label_policy": rule.label_policy,
        "version": rule.version,
        "target_label": _target_label(db, rule),
    }


def _target_label(db: Session, rule: storage_models.StorageRule) -> str | None:
    if rule.target_zone_id is not None:
        zone = db.get(WarehouseZone, rule.target_zone_id)
        if zone:
            return f"Zona {zone.name} ({zone.code})"
    if rule.target_zone_type_id is not None:
        zone_type = db.get(ZoneType, rule.target_zone_type_id)
        if zone_type:
            return f"Tipo de zona {zone_type.name}"
    return None


def list_rules(
    db: Session,
    company_id: str,
    warehouse_id: str | None = None,
) -> list[storage_models.StorageRule]:
    stmt = select(storage_models.StorageRule).where(storage_models.StorageRule.company_id == company_id)
    if warehouse_id is not None:
        stmt = stmt.where(
            (storage_models.StorageRule.warehouse_id.is_(None))
            | (storage_models.StorageRule.warehouse_id == warehouse_id)
        )
    stmt = stmt.order_by(storage_models.StorageRule.priority, storage_models.StorageRule.code)
    return list(db.scalars(stmt).all())


def save_policy(
    db: Session,
    *,
    company_id: str,
    warehouse_id: str,
    mode: str,
    on_no_rule: str,
    expected_version: int | None,
    actor_id: str,
) -> storage_models.WarehouseStoragePolicy:
    _warehouse(db, company_id, warehouse_id)
    if mode not in ("DISABLED", "ENFORCED") or on_no_rule not in ("BLOCK", "ALLOW_ANY"):
        raise KontrolError(code="INVALID_POLICY", message="Política inválida", status_code=422)
    policy = db.scalars(
        select(storage_models.WarehouseStoragePolicy)
        .where(storage_models.WarehouseStoragePolicy.company_id == company_id)
        .where(storage_models.WarehouseStoragePolicy.warehouse_id == warehouse_id)
    ).first()
    if policy is None:
        if expected_version is not None:
            raise ConflictError(code="VERSION_CONFLICT", message="La política no existe; expected_version debe ser null")
        policy = storage_models.WarehouseStoragePolicy(
            company_id=company_id,
            warehouse_id=warehouse_id,
            mode=mode,
            on_no_rule=on_no_rule,
            created_by=actor_id,
        )
        db.add(policy)
        db.flush()
    else:
        db.refresh(policy, with_for_update=True)
        if expected_version is None or policy.version != expected_version:
            raise ConflictError(code="VERSION_CONFLICT", message="Versión de política incorrecta")
        policy.mode = mode
        policy.on_no_rule = on_no_rule
        policy.version += 1

    record_audit(
        db,
        action="WAREHOUSE_STORAGE_POLICY_SAVED",
        entity_type="WarehouseStoragePolicy",
        entity_id=str(policy.id),
        company_id=company_id,
        user_id=actor_id,
        after={"warehouse_id": warehouse_id, "mode": policy.mode, "on_no_rule": policy.on_no_rule, "version": policy.version},
    )
    return policy


def get_policy(db: Session, company_id: str, warehouse_id: str) -> dict[str, Any]:
    policy = db.scalars(
        select(storage_models.WarehouseStoragePolicy)
        .where(storage_models.WarehouseStoragePolicy.company_id == company_id)
        .where(storage_models.WarehouseStoragePolicy.warehouse_id == warehouse_id)
    ).first()
    if policy is None:
        return {"warehouse_id": warehouse_id, "mode": "DISABLED", "on_no_rule": "ALLOW_ANY", "version": None}
    return {
        "warehouse_id": policy.warehouse_id,
        "mode": policy.mode,
        "on_no_rule": policy.on_no_rule,
        "version": policy.version,
    }


def _taxonomy_ancestors(db: Session, item: CatalogItem) -> list[str]:
    ancestors: list[str] = []
    visited: set[str] = set()
    current_id = item.category_id
    while current_id is not None and current_id not in visited:
        visited.add(current_id)
        node = db.get(TaxonomyNode, current_id)
        if node is None:
            break
        ancestors.append(str(node.id))
        current_id = node.parent_id
    return ancestors


def _zone_ids_for_rule(db: Session, rule: storage_models.StorageRule, company_id: str, warehouse_id: str) -> list[str]:
    if rule.target_zone_id is not None:
        zone = db.scalars(
            select(WarehouseZone).where(
                WarehouseZone.id == rule.target_zone_id,
                WarehouseZone.company_id == company_id,
                WarehouseZone.status == "ACTIVE",
                WarehouseZone.warehouse_id == warehouse_id,
            )
        ).first()
        return [str(zone.id)] if zone else []
    zone_rows = db.scalars(
        select(WarehouseZone).where(
            WarehouseZone.company_id == company_id,
            WarehouseZone.warehouse_id == warehouse_id,
            WarehouseZone.zone_type_id == rule.target_zone_type_id,
            WarehouseZone.status == "ACTIVE",
        )
    ).all()
    return [str(z.id) for z in zone_rows]


def _label_rank(label_policy: str) -> int:
    if label_policy == "REQUIRED":
        return 3
    if label_policy == "OPTIONAL":
        return 2
    return 1


def evaluate(
    db: Session,
    *,
    company_id: str,
    warehouse_id: str,
    item_id: str,
) -> dict[str, Any]:
    item = _item(db, company_id, item_id)
    _warehouse(db, company_id, warehouse_id)
    profile = db.scalars(
        select(storage_models.ProductStorageProfile)
        .where(storage_models.ProductStorageProfile.company_id == company_id)
        .where(storage_models.ProductStorageProfile.item_id == item_id)
    ).first()

    profile_condition_ids: set[str] = set()
    profile_condition_names: list[str] = []
    if profile is not None:
        rows = db.scalars(
            select(storage_models.StorageCondition)
            .join(
                storage_models.ProductStorageCondition,
                storage_models.ProductStorageCondition.condition_id == storage_models.StorageCondition.id,
            )
            .where(storage_models.ProductStorageCondition.profile_id == profile.id)
            .order_by(storage_models.StorageCondition.code)
        ).all()
        profile_condition_ids = {str(c.id) for c in rows}
        profile_condition_names = [c.name for c in rows]

    taxonomy_ids = _taxonomy_ancestors(db, item)
    today = hoy_de_negocio()

    stmt = select(storage_models.StorageRule).where(
        storage_models.StorageRule.company_id == company_id,
        storage_models.StorageRule.status == "ACTIVE",
        (
            (storage_models.StorageRule.warehouse_id.is_(None))
            | (storage_models.StorageRule.warehouse_id == warehouse_id)
        ),
    )
    rules = db.scalars(stmt).all()
    vigentes = []
    missing_criteria: list[str] = []
    for rule in rules:
        valid_from = rule.valid_from
        valid_to = rule.valid_to
        if valid_from is not None and valid_from > today:
            continue
        if valid_to is not None and valid_to < today:
            continue
        vigentes.append(rule)

    matching: list[tuple[storage_models.StorageRule, list[str], int]] = []
    discarded: list[str] = []
    for rule in vigentes:
        reasons: list[str] = []
        criteria_count = 0
        ok = True
        if rule.taxonomy_id is not None:
            criteria_count += 1
            node = db.get(TaxonomyNode, rule.taxonomy_id)
            node_name = node.name if node else "desconocido"
            if str(rule.taxonomy_id) in taxonomy_ids:
                reasons.append(f"Familia/categoría: {node_name}")
            else:
                reasons.append(f"No pertenece a {node_name}")
                ok = False
            if node is None:
                ok = False
        if rule.size_class_id is not None:
            criteria_count += 1
            if profile is None or profile.size_class_id is None:
                missing_criteria.append("Clase de tamaño")
                ok = False
            elif str(profile.size_class_id) != str(rule.size_class_id):
                size_class = db.get(storage_models.StorageSizeClass, profile.size_class_id)
                size_class_name = size_class.name if size_class else profile.size_class_id
                reasons.append(f"Clase de tamaño: {size_class_name}")
                ok = False
            else:
                size_class = db.get(storage_models.StorageSizeClass, rule.size_class_id)
                reasons.append(f"Clase de tamaño: {size_class.name if size_class else rule.size_class_id}")
        if rule.condition_id is not None:
            criteria_count += 1
            if str(rule.condition_id) not in profile_condition_ids:
                condition = db.get(storage_models.StorageCondition, rule.condition_id)
                reasons.append(f"Sin condición {condition.name if condition else rule.condition_id}")
                ok = False
            else:
                condition = db.get(storage_models.StorageCondition, rule.condition_id)
                reasons.append(f"Condición {condition.name if condition else rule.condition_id}")

        def _check_measure(
            prefix: str,
            min_val: Decimal | None,
            max_val: Decimal | None,
            unit_id: str | None,
            profile_value: Decimal | None,
            profile_unit_id: str | None,
        ) -> bool:
            nonlocal ok, missing_criteria, reasons, criteria_count
            if min_val is None and max_val is None:
                return True
            criteria_count += 1
            if profile is None or profile_value is None or profile_unit_id is None:
                missing_criteria.append(prefix.capitalize())
                ok = False
                return False
            rule_unit = db.get(UnitOfMeasure, unit_id) if unit_id else None
            profile_unit = db.get(UnitOfMeasure, profile_unit_id)
            if rule_unit is None or profile_unit is None:
                missing_criteria.append(f"Conversión de {prefix} {profile_unit.symbol if profile_unit else ''} → {rule_unit.symbol if rule_unit else ''}")
                ok = False
                return False
            try:
                factor = physical_factor(db, profile_unit_id, str(rule_unit.id))
                converted = profile_value * factor
            except KontrolError:
                missing_criteria.append(
                    f"Conversión de {prefix} {profile_unit.symbol} → {rule_unit.symbol}"
                )
                ok = False
                return False
            if min_val is not None and converted < min_val:
                reasons.append(f"{prefix.capitalize()} {converted} fuera de rango")
                ok = False
                return False
            if max_val is not None and converted > max_val:
                reasons.append(f"{prefix.capitalize()} {converted} fuera de rango")
                ok = False
                return False
            reasons.append(f"{prefix.capitalize()} {converted} {rule_unit.symbol}")
            return True

        weight_ok = _check_measure(
            "peso",
            rule.min_weight,
            rule.max_weight,
            rule.weight_unit_id,
            profile.weight_value if profile else None,
            profile.weight_unit_id if profile else None,
        )
        volume_ok = _check_measure(
            "volumen",
            rule.min_volume,
            rule.max_volume,
            rule.volume_unit_id,
            profile.volume_value if profile else None,
            profile.volume_unit_id if profile else None,
        )
        if rule.target_zone_id is not None:
            zone_ids = _zone_ids_for_rule(db, rule, company_id, warehouse_id)
            if not zone_ids:
                zone = db.get(WarehouseZone, rule.target_zone_id)
                discarded.append(f"{rule.code}: Zona {zone.code if zone else 'desconocida'} inactiva o de otro almacén")
                ok = False
        if rule.target_zone_type_id is not None:
            zone_ids = _zone_ids_for_rule(db, rule, company_id, warehouse_id)
            if not zone_ids:
                zone_type = db.get(ZoneType, rule.target_zone_type_id)
                discarded.append(f"{rule.code}: Sin zonas del tipo {zone_type.name if zone_type else 'desconocido'} en el almacén")
                ok = False
        if ok and weight_ok and volume_ok:
            matching.append((rule, reasons, criteria_count))

    if not matching:
        return {
            "result": "NO_RULE",
            "rule": None,
            "label_policy": None,
            "label_required": False,
            "target_zone_id": None,
            "target_zone_type_id": None,
            "target_label": None,
            "zone_ids": [],
            "reasons": ["No existe una regla de almacenamiento aplicable"] + discarded,
            "missing_criteria": list(dict.fromkeys(missing_criteria)),
            "candidate_rules": [],
            "inputs": _inputs_dict(db, item, profile, profile_condition_names),
        }

    matching.sort(key=lambda x: (x[0].priority, -x[2], x[0].code))
    first = matching[0]
    best_specificity = first[2]
    best_priority = first[0].priority
    winners = [
        (rule, reasons, specificity)
        for rule, reasons, specificity in matching
        if rule.priority == best_priority and specificity == best_specificity
    ]
    destinations = {(rule.target_zone_id, rule.target_zone_type_id) for rule, _, _ in winners}

    if len(destinations) > 1:
        codes = ", ".join(rule.code for rule, _, _ in winners)
        return {
            "result": "AMBIGUOUS",
            "rule": None,
            "label_policy": None,
            "label_required": False,
            "target_zone_id": None,
            "target_zone_type_id": None,
            "target_label": None,
            "zone_ids": [],
            "reasons": [f"Reglas en empate: {codes}"],
            "missing_criteria": list(dict.fromkeys(missing_criteria)),
            "candidate_rules": [rule.code for rule, _, _ in winners],
            "inputs": _inputs_dict(db, item, profile, profile_condition_names),
        }

    winning_rule, winning_reasons, _ = winners[0]
    label_policy = max((rule.label_policy for rule, _, _ in winners), key=_label_rank)
    target_zone_id = winning_rule.target_zone_id
    target_zone_type_id = winning_rule.target_zone_type_id
    target_label = _target_label(db, winning_rule)
    zone_ids = _zone_ids_for_rule(db, winning_rule, company_id, warehouse_id)
    return {
        "result": "CLASSIFIED",
        "rule": rule_dict(db, winning_rule),
        "label_policy": label_policy,
        "label_required": label_policy == "REQUIRED",
        "target_zone_id": target_zone_id,
        "target_zone_type_id": target_zone_type_id,
        "target_label": target_label,
        "zone_ids": zone_ids,
        "reasons": winning_reasons,
        "missing_criteria": list(dict.fromkeys(missing_criteria)),
        "candidate_rules": [rule.code for rule, _, _ in winners],
        "inputs": _inputs_dict(db, item, profile, profile_condition_names),
    }


def _inputs_dict(
    db: Session,
    item: CatalogItem,
    profile: storage_models.ProductStorageProfile | None,
    profile_condition_names: list[str],
) -> dict[str, Any]:
    taxonomy_name = None
    if item.category_id is not None:
        node = db.get(TaxonomyNode, item.category_id)
        taxonomy_name = node.name if node else None
    size_class_name = None
    if profile is not None and profile.size_class_id is not None:
        size_class = db.get(storage_models.StorageSizeClass, profile.size_class_id)
        size_class_name = size_class.name if size_class else None
    weight_text = None
    volume_text = None
    if profile is not None:
        if profile.weight_value is not None and profile.weight_unit_id is not None:
            unit = db.get(UnitOfMeasure, profile.weight_unit_id)
            weight_text = f"{profile.weight_value} {unit.symbol}" if unit else str(profile.weight_value)
        if profile.volume_value is not None and profile.volume_unit_id is not None:
            unit = db.get(UnitOfMeasure, profile.volume_unit_id)
            volume_text = f"{profile.volume_value} {unit.symbol}" if unit else str(profile.volume_value)
    return {
        "taxonomy_name": taxonomy_name,
        "weight": weight_text,
        "volume": volume_text,
        "size_class": size_class_name,
        "conditions": profile_condition_names,
    }


def classify(
    db: Session,
    *,
    company_id: str,
    warehouse_id: str,
    item_id: str,
    state: str,
    actor_id: str,
    import_file_id: str | None = None,
    receipt_id: str | None = None,
    document_ref: str | None = None,
) -> storage_models.StorageClassification:
    _item(db, company_id, item_id)
    _warehouse(db, company_id, warehouse_id)
    db.execute(
        select(CatalogItem)
        .where(CatalogItem.id == item_id, CatalogItem.company_id == company_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalars().first()
    previous_rows = db.scalars(
        select(storage_models.StorageClassification)
        .where(storage_models.StorageClassification.company_id == company_id)
        .where(storage_models.StorageClassification.warehouse_id == warehouse_id)
        .where(storage_models.StorageClassification.item_id == item_id)
        .where(
            storage_models.StorageClassification.receipt_id.is_(None)
            if receipt_id is None
            else storage_models.StorageClassification.receipt_id == receipt_id
        )
        .where(storage_models.StorageClassification.status == "CURRENT")
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()
    for previous in previous_rows:
        previous.status = "SUPERSEDED"

    evaluation = evaluate(db, company_id=company_id, warehouse_id=warehouse_id, item_id=item_id)
    rule = evaluation["rule"]
    classification = storage_models.StorageClassification(
        company_id=company_id,
        warehouse_id=warehouse_id,
        item_id=item_id,
        state=state,
        import_file_id=import_file_id,
        receipt_id=receipt_id,
        document_ref=document_ref,
        result=evaluation["result"],
        status="CURRENT",
        rule_id=rule["id"] if rule else None,
        rule_version=rule["version"] if rule else None,
        rule_code=rule["code"] if rule else None,
        rule_name=rule["name"] if rule else None,
        label_policy=evaluation["label_policy"],
        target_zone_id=evaluation["target_zone_id"],
        target_zone_type_id=evaluation["target_zone_type_id"],
        target_label=evaluation["target_label"],
        input_taxonomy_name=evaluation["inputs"]["taxonomy_name"],
        input_weight=evaluation["inputs"]["weight"],
        input_volume=evaluation["inputs"]["volume"],
        input_size_class=evaluation["inputs"]["size_class"],
        input_conditions=evaluation["inputs"]["conditions"],
        reasons=evaluation["reasons"],
        missing_criteria=evaluation["missing_criteria"],
        candidate_rules=evaluation["candidate_rules"],
        classified_at=datetime.now(UTC),
        classified_by=actor_id,
        created_by=actor_id,
    )
    db.add(classification)
    db.flush()

    action = "STORAGE_CLASSIFIED" if not previous_rows else "STORAGE_RECLASSIFIED"
    record_audit(
        db,
        action=action,
        entity_type="StorageClassification",
        entity_id=str(classification.id),
        company_id=company_id,
        user_id=actor_id,
        after={
            "item_id": item_id,
            "warehouse_id": warehouse_id,
            "result": classification.result,
            "rule_code": classification.rule_code,
            "rule_version": classification.rule_version,
            "target_label": classification.target_label,
            "label_policy": classification.label_policy,
            "receipt_id": receipt_id,
        },
    )
    return classification


def is_stale(db: Session, classification: storage_models.StorageClassification) -> bool:
    if classification.result != "CLASSIFIED" or classification.rule_id is None:
        return False
    rule = db.get(storage_models.StorageRule, classification.rule_id)
    if rule is None or rule.status != "ACTIVE" or rule.version != classification.rule_version:
        return True
    return False


def classification_dict(db: Session, classification: storage_models.StorageClassification) -> dict[str, Any]:
    zone_ids: list[str] = []
    if classification.status == "CURRENT" and classification.result == "CLASSIFIED":
        if classification.target_zone_id is not None:
            zone = db.scalars(
                select(WarehouseZone).where(
                    WarehouseZone.id == classification.target_zone_id,
                    WarehouseZone.company_id == classification.company_id,
                    WarehouseZone.warehouse_id == classification.warehouse_id,
                    WarehouseZone.status == "ACTIVE",
                )
            ).first()
            if zone:
                zone_ids = [str(zone.id)]
        elif classification.target_zone_type_id is not None:
            zones = db.scalars(
                select(WarehouseZone).where(
                    WarehouseZone.company_id == classification.company_id,
                    WarehouseZone.warehouse_id == classification.warehouse_id,
                    WarehouseZone.zone_type_id == classification.target_zone_type_id,
                    WarehouseZone.status == "ACTIVE",
                )
            ).all()
            zone_ids = [str(z.id) for z in zones]
    return {
        "id": str(classification.id),
        "company_id": classification.company_id,
        "warehouse_id": classification.warehouse_id,
        "item_id": classification.item_id,
        "state": classification.state,
        "import_file_id": classification.import_file_id,
        "receipt_id": classification.receipt_id,
        "document_ref": classification.document_ref,
        "result": classification.result,
        "status": classification.status,
        "rule_id": classification.rule_id,
        "rule_version": classification.rule_version,
        "rule_code": classification.rule_code,
        "rule_name": classification.rule_name,
        "label_policy": classification.label_policy,
        "target_zone_id": classification.target_zone_id,
        "target_zone_type_id": classification.target_zone_type_id,
        "target_label": classification.target_label,
        "input_taxonomy_name": classification.input_taxonomy_name,
        "input_weight": classification.input_weight,
        "input_volume": classification.input_volume,
        "input_size_class": classification.input_size_class,
        "input_conditions": classification.input_conditions,
        "reasons": classification.reasons,
        "missing_criteria": classification.missing_criteria,
        "candidate_rules": classification.candidate_rules,
        "classified_at": str(classification.classified_at),
        "classified_by": classification.classified_by,
        "stale": is_stale(db, classification),
        "zone_ids": zone_ids,
    }
