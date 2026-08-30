"""API de la estructura física de almacén (Spec 008).

Prefijo `/api/v1/organization`, convención vigente del módulo. Todo endpoint
exige sesión, permiso y filtra por empresa: el aislamiento vive aquí, no en el
frontend (P6).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission, require_write_allowed
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.identity_access.models import User
from app.modules.organization import structure as st
from app.modules.organization.models import (
    Company,
    LocationType,
    Warehouse,
    WarehouseLocation,
    ZoneType,
)
from app.shared.audit import record_audit

router = APIRouter(prefix="/organization", tags=["organization-structure"])


# --------------------------------------------------------------------------
# Alcance
# --------------------------------------------------------------------------

def _company_ids(db: Session, user: User) -> list[str]:
    return list(db.execute(
        select(Company.id).where(Company.tenant_id == user.tenant_id)
    ).scalars().all())


def _get_warehouse(db: Session, user: User, warehouse_id: str) -> Warehouse:
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.company_id not in _company_ids(db, user):
        # Un almacén de otra empresa se responde como inexistente: revelar que
        # existe ya sería una filtración (enumeración).
        raise NotFoundError(code="WAREHOUSE_NOT_FOUND", message="Almacén no encontrado")
    return warehouse


def _get_node(db: Session, user: User, level: str, node_id: str) -> Any:
    node = db.get(st.LEVEL_MODEL[level], node_id)
    if node is None or node.company_id not in _company_ids(db, user):
        raise NotFoundError(code=f"{level.upper()}_NOT_FOUND", message="Nodo no encontrado")
    return node


def _get_location(db: Session, user: User, location_id: str) -> WarehouseLocation:
    location = db.get(WarehouseLocation, location_id)
    if location is None or location.company_id not in _company_ids(db, user):
        raise NotFoundError(code="LOCATION_NOT_FOUND", message="Ubicación no encontrada")
    return location


def _check_version(entity: Any, if_match: str | None) -> None:
    if if_match is None:
        return
    expected = if_match.strip('"')
    if not expected.isdigit() or int(expected) != int(entity.version):
        raise ConflictError(code="VERSION_CONFLICT",
                            message="El registro fue modificado por otra operación")


def _bump(entity: Any) -> None:
    entity.version = int(entity.version) + 1


def _audit(db: Session, user: User, action: str, entity_type: str, entity_id: str,
           before: dict | None = None, after: dict | None = None) -> None:
    record_audit(db, action=action, entity_type=entity_type, entity_id=entity_id,
                 tenant_id=user.tenant_id, user_id=str(user.id), before=before, after=after)


def _integrity(exc: IntegrityError, code: str, message: str) -> KontrolError:
    del exc
    return ConflictError(code=code, message=message)


# --------------------------------------------------------------------------
# Catálogos
# --------------------------------------------------------------------------

class ZoneTypeIn(BaseModel):
    company_id: str
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class LocationTypeIn(BaseModel):
    company_id: str
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    is_storable: bool = True


def _catalog_list(db: Session, user: User, model: Any, company_id: str | None) -> list[dict[str, Any]]:
    query = select(model).where(model.company_id.in_(_company_ids(db, user)))
    if company_id:
        query = query.where(model.company_id == company_id)
    rows = db.execute(query.order_by(model.code)).scalars().all()
    return [{"id": str(r.id), "company_id": r.company_id, "code": r.code, "name": r.name,
             "status": r.status,
             **({"is_storable": r.is_storable} if hasattr(r, "is_storable") else {}),
             **({"description": r.description} if hasattr(r, "description") else {})}
            for r in rows]


def _catalog_create(db: Session, actor: User, model: Any, values: dict[str, Any],
                    entity: str) -> dict[str, Any]:
    if values["company_id"] not in _company_ids(db, actor):
        raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")
    row = model(**values, status="ACTIVE", created_by=str(actor.id))
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _integrity(exc, f"{entity.upper()}_CODE_DUPLICATE",
                         "Ya existe un tipo con ese código en la empresa") from exc
    db.refresh(row)
    _audit(db, actor, "CREATE", entity, str(row.id), after={"code": row.code})
    db.commit()
    return {"id": str(row.id), "code": row.code, "name": row.name}


def _catalog_update(db: Session, actor: User, model: Any, item_id: str,
                    body: dict[str, Any], entity: str) -> dict[str, Any]:
    row = db.get(model, item_id)
    if row is None or row.company_id not in _company_ids(db, actor):
        raise NotFoundError(code="NOT_FOUND", message="Tipo no encontrado")
    before = {"name": row.name, "status": row.status}
    for field in ("name", "description", "is_storable", "status"):
        if field in body and hasattr(row, field):
            setattr(row, field, body[field])
    _audit(db, actor, "UPDATE", entity, str(row.id), before=before,
           after={"name": row.name, "status": row.status})
    db.commit()
    return {"id": str(row.id), "code": row.code, "name": row.name, "status": row.status}


@router.get("/zone-types")
def list_zone_types(company_id: str | None = None, db: Session = Depends(get_db),
                    user: User = Depends(require_permission("organization", "view"))):
    return _catalog_list(db, user, ZoneType, company_id)


@router.post("/zone-types", dependencies=[Depends(require_write_allowed)])
def create_zone_type(body: ZoneTypeIn, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("organization", "create"))):
    return _catalog_create(db, actor, ZoneType, body.model_dump(), "zone_type")


@router.patch("/zone-types/{item_id}", dependencies=[Depends(require_write_allowed)])
def update_zone_type(item_id: str, body: dict[str, Any], db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("organization", "edit"))):
    return _catalog_update(db, actor, ZoneType, item_id, body, "zone_type")


@router.get("/location-types")
def list_location_types(company_id: str | None = None, db: Session = Depends(get_db),
                        user: User = Depends(require_permission("organization", "view"))):
    return _catalog_list(db, user, LocationType, company_id)


@router.post("/location-types", dependencies=[Depends(require_write_allowed)])
def create_location_type(body: LocationTypeIn, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("organization", "create"))):
    return _catalog_create(db, actor, LocationType, body.model_dump(), "location_type")


@router.patch("/location-types/{item_id}", dependencies=[Depends(require_write_allowed)])
def update_location_type(item_id: str, body: dict[str, Any], db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("organization", "edit"))):
    return _catalog_update(db, actor, LocationType, item_id, body, "location_type")


# --------------------------------------------------------------------------
# Almacenes
# --------------------------------------------------------------------------

class WarehouseIn(BaseModel):
    company_id: str
    branch_id: str | None = None
    code: str | None = None
    name: str = Field(min_length=1, max_length=200)
    warehouse_type: str = "PHYSICAL"
    address: str | None = None
    manager_id: str | None = None
    description: str | None = None
    location_managed: bool = False
    structure_levels: dict[str, Any] | None = None
    code_policy: str = "GENERATED"
    code_pattern: str | None = None


class WarehousePatch(BaseModel):
    name: str | None = None
    address: str | None = None
    manager_id: str | None = None
    description: str | None = None
    location_managed: bool | None = None
    code_policy: str | None = None
    code_pattern: str | None = None
    branch_id: str | None = None


class StructureLevelsPatch(BaseModel):
    structure_levels: dict[str, Any]


def _warehouse_dict(db: Session, w: Warehouse, permissions: set[str] | None = None) -> dict[str, Any]:
    can_delete, blocking = st.can_delete_warehouse(db, w)
    return {
        "id": str(w.id), "company_id": w.company_id, "branch_id": w.branch_id,
        "code": w.code, "name": w.name, "warehouse_type": w.warehouse_type,
        "address": w.address, "manager_id": w.manager_id, "description": w.description,
        "location_managed": w.location_managed,
        "structure_levels": st.normalize_structure_levels(w.structure_levels),
        "structure_regime": st.current_regime(db, w),
        "declared_levels": st.declared_levels(w),
        "code_policy": w.code_policy, "code_pattern": w.code_pattern,
        "status": w.status, "version": int(w.version),
        "can_delete": can_delete,
        "delete_blocked_by": blocking.get("dependencies") if blocking else None,
        "allowed_actions": st.warehouse_allowed_actions(db, w, permissions),
    }


@router.get("/warehouses")
def search_warehouses(q: str | None = None, branch_id: str | None = None,
                      status: str | None = None, company_id: str | None = None,
                      limit: int = 50, offset: int = 0,
                      db: Session = Depends(get_db),
                      user: User = Depends(require_permission("organization", "view"))):
    query = select(Warehouse).where(Warehouse.company_id.in_(_company_ids(db, user)))
    if company_id:
        query = query.where(Warehouse.company_id == company_id)
    if branch_id:
        query = query.where(Warehouse.branch_id == branch_id)
    if status:
        query = query.where(Warehouse.status == status)
    if q:
        pattern = f"%{q}%"
        query = query.where(Warehouse.code.ilike(pattern) | Warehouse.name.ilike(pattern))
    total = int(db.execute(select(func.count()).select_from(query.subquery())).scalar_one())
    rows = db.execute(query.order_by(Warehouse.code).limit(limit).offset(offset)).scalars().all()
    permissions = st.user_permission_set(db, user)
    return {"total": total, "limit": limit, "offset": offset,
            "items": [_warehouse_dict(db, w, permissions) for w in rows]}


@router.post("/warehouses", dependencies=[Depends(require_write_allowed)])
def create_warehouse_full(body: WarehouseIn, db: Session = Depends(get_db),
                          actor: User = Depends(require_permission("organization", "create"))):
    if body.company_id not in _company_ids(db, actor):
        raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")
    if not body.code:
        raise KontrolError(code="WAREHOUSE_CODE_REQUIRED",
                           message="El código del almacén es obligatorio", status_code=422)
    warehouse = Warehouse(
        company_id=body.company_id, branch_id=body.branch_id, code=body.code, name=body.name,
        warehouse_type=body.warehouse_type, address=body.address, manager_id=body.manager_id,
        description=body.description, location_managed=body.location_managed,
        structure_levels=st.normalize_structure_levels(body.structure_levels),
        structure_regime=st.REGIME_INITIAL,
        code_policy=body.code_policy, code_pattern=body.code_pattern,
        status="ACTIVE", created_by=str(actor.id),
    )
    db.add(warehouse)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _integrity(exc, "WAREHOUSE_CODE_DUPLICATE",
                         "Ya existe un almacén con ese código en la empresa") from exc
    db.refresh(warehouse)
    _audit(db, actor, "CREATE", "warehouse", str(warehouse.id), after={"code": warehouse.code})
    db.commit()
    return _warehouse_dict(db, warehouse, st.user_permission_set(db, actor))


@router.get("/warehouses/{warehouse_id}")
def get_warehouse(warehouse_id: str, db: Session = Depends(get_db),
                  user: User = Depends(require_permission("organization", "view"))):
    warehouse = _get_warehouse(db, user, warehouse_id)
    return _warehouse_dict(db, warehouse, st.user_permission_set(db, user))


@router.patch("/warehouses/{warehouse_id}", dependencies=[Depends(require_write_allowed)])
def patch_warehouse(warehouse_id: str, body: WarehousePatch,
                    if_match: str | None = Header(default=None, alias="If-Match"),
                    db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("organization", "edit"))):
    warehouse = _get_warehouse(db, actor, warehouse_id)
    _check_version(warehouse, if_match)
    before = {"name": warehouse.name, "location_managed": warehouse.location_managed}
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(warehouse, field, value)
    _bump(warehouse)
    _audit(db, actor, "UPDATE", "warehouse", str(warehouse.id), before=before,
           after={"name": warehouse.name, "location_managed": warehouse.location_managed})
    db.commit()
    db.refresh(warehouse)
    return _warehouse_dict(db, warehouse, st.user_permission_set(db, actor))


@router.patch("/warehouses/{warehouse_id}/structure-levels",
              dependencies=[Depends(require_write_allowed)])
def patch_structure_levels(warehouse_id: str, body: StructureLevelsPatch,
                           db: Session = Depends(get_db),
                           actor: User = Depends(require_permission("organization", "manage_structure"))):
    """Único camino para cambiar `structure_levels`.

    En régimen operativo rechaza eliminar, reordenar o colapsar un tramo
    utilizado. El bloqueo se produce **aquí**: invocar este endpoint saltándose
    el frontend obtiene el mismo rechazo (Control 2).
    """
    warehouse = _get_warehouse(db, actor, warehouse_id)
    before = st.normalize_structure_levels(warehouse.structure_levels)
    try:
        warehouse.structure_levels = st.validate_structure_levels_change(
            db, warehouse, body.structure_levels)
    except KontrolError:
        _audit(db, actor, "STRUCTURE_CHANGE_BLOCKED", "warehouse", str(warehouse.id),
               before=before, after=st.normalize_structure_levels(body.structure_levels))
        db.commit()
        raise
    _bump(warehouse)
    _audit(db, actor, "STRUCTURE_LEVELS_CHANGED", "warehouse", str(warehouse.id),
           before=before, after=warehouse.structure_levels)
    db.commit()
    db.refresh(warehouse)
    return _warehouse_dict(db, warehouse, st.user_permission_set(db, actor))


@router.post("/warehouses/{warehouse_id}/activate", dependencies=[Depends(require_write_allowed)])
def activate_warehouse(warehouse_id: str, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("organization", "activate"))):
    warehouse = _get_warehouse(db, actor, warehouse_id)
    warehouse.status = "ACTIVE"
    _bump(warehouse)
    _audit(db, actor, "ACTIVATE", "warehouse", str(warehouse.id), after={"status": "ACTIVE"})
    db.commit()
    return {"id": str(warehouse.id), "status": warehouse.status}


@router.post("/warehouses/{warehouse_id}/deactivate", dependencies=[Depends(require_write_allowed)])
def deactivate_warehouse(warehouse_id: str, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("organization", "deactivate"))):
    warehouse = _get_warehouse(db, actor, warehouse_id)
    warehouse.status = "INACTIVE"
    _bump(warehouse)
    _audit(db, actor, "DEACTIVATE", "warehouse", str(warehouse.id), after={"status": "INACTIVE"})
    db.commit()
    return {"id": str(warehouse.id), "status": warehouse.status}


@router.delete("/warehouses/{warehouse_id}", dependencies=[Depends(require_write_allowed)])
def delete_warehouse(warehouse_id: str, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("organization", "delete"))):
    """Borrar un almacén **nunca** destruye ubicaciones (R-008-8): si tiene
    estructura, ubicaciones o movimientos, se rechaza y no se toca nada."""
    warehouse = _get_warehouse(db, actor, warehouse_id)
    deletable, blocking = st.can_delete_warehouse(db, warehouse)
    if not deletable:
        _audit(db, actor, "DELETE_BLOCKED", "warehouse", str(warehouse.id), after=blocking)
        db.commit()
        raise KontrolError(
            code="NODE_HAS_HISTORY", message="El almacén tiene dependencias y no puede borrarse",
            status_code=409,
            details={"reason": "Existen nodos, ubicaciones o movimientos asociados",
                     "dependencies": blocking.get("dependencies", {}),
                     "allowed_actions": ["deactivate"]},
        )
    _audit(db, actor, "DELETE", "warehouse", str(warehouse.id), before={"code": warehouse.code})
    db.delete(warehouse)
    db.commit()
    return {"deleted": True}


# --------------------------------------------------------------------------
# Nodos intermedios — mismo juego para zone, aisle, rack y level
# --------------------------------------------------------------------------

class NodeIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    sequence: int = 0
    description: str | None = None
    parent_id: str | None = None
    zone_type_id: str | None = None
    height_order: int | None = None


class NodePatch(BaseModel):
    name: str | None = None
    description: str | None = None
    sequence: int | None = None
    zone_type_id: str | None = None
    height_order: int | None = None
    parent_id: str | None = None
    status: str | None = None


def _node_dict(db: Session, level: str, node: Any, permissions: set[str] | None = None) -> dict[str, Any]:
    can_delete, blocking = st.can_delete_node(db, level, node.id)
    parent_fk = st.LEVEL_PARENT_FK[level]
    return {
        "id": str(node.id), "level": level, "warehouse_id": node.warehouse_id,
        "company_id": node.company_id, "code": node.code, "name": node.name,
        "sequence": node.sequence, "description": node.description,
        "parent_id": getattr(node, parent_fk) if parent_fk else None,
        **({"zone_type_id": node.zone_type_id} if level == "zone" else {}),
        **({"height_order": node.height_order} if level == "level" else {}),
        "status": node.status, "version": int(node.version),
        "can_delete": can_delete, "delete_blocked_by": blocking or None,
        "allowed_actions": st.node_allowed_actions(db, level, node, permissions),
    }


def _node_routes(level: str) -> None:
    model = st.LEVEL_MODEL[level]
    plural = {"zone": "zones", "aisle": "aisles", "rack": "racks", "level": "levels"}[level]

    @router.get(f"/warehouses/{{warehouse_id}}/{plural}", name=f"list_{plural}")
    def _list(warehouse_id: str, status: str | None = None, parent_id: str | None = None,
              db: Session = Depends(get_db),
              user: User = Depends(require_permission("organization", "view"))):
        warehouse = _get_warehouse(db, user, warehouse_id)
        query = select(model).where(model.warehouse_id == warehouse.id)
        if status:
            query = query.where(model.status == status)
        parent_fk = st.LEVEL_PARENT_FK[level]
        if parent_id and parent_fk:
            query = query.where(getattr(model, parent_fk) == parent_id)
        rows = db.execute(query.order_by(model.sequence, model.code)).scalars().all()
        permissions = st.user_permission_set(db, user)
        return [_node_dict(db, level, node, permissions) for node in rows]

    @router.post(f"/warehouses/{{warehouse_id}}/{plural}",
                 dependencies=[Depends(require_write_allowed)], name=f"create_{level}")
    def _create(warehouse_id: str, body: NodeIn, db: Session = Depends(get_db),
                actor: User = Depends(require_permission("organization", "create"))):
        warehouse = _get_warehouse(db, actor, warehouse_id)
        if level not in st.declared_levels(warehouse):
            raise KontrolError(code="STRUCTURE_LEVEL_DISABLED",
                               message=f"El almacén no declara el tramo {level.upper()}",
                               status_code=422,
                               details={"level": level.upper(),
                                        "declared": st.declared_levels(warehouse)})
        parent_id = st.validate_node_parent(db, warehouse, level, body.parent_id)
        values: dict[str, Any] = {
            "company_id": warehouse.company_id, "warehouse_id": warehouse.id,
            "code": body.code, "name": body.name, "sequence": body.sequence,
            "description": body.description, "status": "ACTIVE", "created_by": str(actor.id),
        }
        parent_fk = st.LEVEL_PARENT_FK[level]
        if parent_fk:
            values[parent_fk] = parent_id
        if level == "zone":
            values["zone_type_id"] = body.zone_type_id
        if level == "level":
            values["height_order"] = body.height_order
        node = model(**values)
        db.add(node)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise _integrity(exc, f"{level.upper()}_CODE_DUPLICATE",
                             "Ya existe un nodo con ese código en el almacén") from exc
        db.refresh(node)
        # Crear el primer nodo hace operativo el almacén: viaje de ida (R-008-6).
        st.promote_regime(db, warehouse)
        _audit(db, actor, "CREATE", f"warehouse_{level}", str(node.id), after={"code": node.code})
        db.commit()
        return _node_dict(db, level, node, st.user_permission_set(db, actor))

    @router.get(f"/{plural}/{{node_id}}", name=f"get_{level}")
    def _get(node_id: str, db: Session = Depends(get_db),
             user: User = Depends(require_permission("organization", "view"))):
        node = _get_node(db, user, level, node_id)
        return _node_dict(db, level, node, st.user_permission_set(db, user))

    @router.patch(f"/{plural}/{{node_id}}", dependencies=[Depends(require_write_allowed)],
                  name=f"patch_{level}")
    def _patch(node_id: str, body: NodePatch,
               if_match: str | None = Header(default=None, alias="If-Match"),
               db: Session = Depends(get_db),
               actor: User = Depends(require_permission("organization", "edit"))):
        node = _get_node(db, actor, level, node_id)
        _check_version(node, if_match)
        warehouse = _get_warehouse(db, actor, node.warehouse_id)
        data = body.model_dump(exclude_unset=True)
        before = {"name": node.name, "sequence": node.sequence, "status": node.status}
        # `parent_id` es cambio **estructural**; nombre, descripción y
        # `sequence` entre hermanos son metadata (FR-008-092).
        if "parent_id" in data:
            parent_fk = st.LEVEL_PARENT_FK[level]
            if parent_fk is None:
                raise KontrolError(code="STRUCTURE_LEVEL_DISABLED",
                                   message="Este tramo no tiene padre", status_code=422)
            setattr(node, parent_fk,
                    st.validate_node_parent(db, warehouse, level, data.pop("parent_id")))
        for field, value in data.items():
            if hasattr(node, field):
                setattr(node, field, value)
        _bump(node)
        _audit(db, actor, "UPDATE", f"warehouse_{level}", str(node.id), before=before,
               after={"name": node.name, "sequence": node.sequence, "status": node.status})
        db.commit()
        db.refresh(node)
        return _node_dict(db, level, node, st.user_permission_set(db, actor))

    @router.post(f"/{plural}/{{node_id}}/activate", dependencies=[Depends(require_write_allowed)],
                 name=f"activate_{level}")
    def _activate(node_id: str, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("organization", "activate"))):
        node = _get_node(db, actor, level, node_id)
        node.status = "ACTIVE"
        _bump(node)
        _audit(db, actor, "ACTIVATE", f"warehouse_{level}", str(node.id), after={"status": "ACTIVE"})
        db.commit()
        return {"id": str(node.id), "status": node.status}

    @router.post(f"/{plural}/{{node_id}}/deactivate", dependencies=[Depends(require_write_allowed)],
                 name=f"deactivate_{level}")
    def _deactivate(node_id: str, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("organization", "deactivate"))):
        node = _get_node(db, actor, level, node_id)
        try:
            st.assert_can_deactivate_node(db, level, node.id)
        except KontrolError:
            _audit(db, actor, "DEACTIVATE_BLOCKED", f"warehouse_{level}", str(node.id))
            db.commit()
            raise
        node.status = "INACTIVE"
        _bump(node)
        _audit(db, actor, "DEACTIVATE", f"warehouse_{level}", str(node.id),
               after={"status": "INACTIVE"})
        db.commit()
        return {"id": str(node.id), "status": node.status}

    @router.delete(f"/{plural}/{{node_id}}", dependencies=[Depends(require_write_allowed)],
                   name=f"delete_{level}")
    def _delete(node_id: str, db: Session = Depends(get_db),
                actor: User = Depends(require_permission("organization", "delete"))):
        node = _get_node(db, actor, level, node_id)
        deletable, blocking = st.can_delete_node(db, level, node.id)
        if not deletable:
            _audit(db, actor, "DELETE_BLOCKED", f"warehouse_{level}", str(node.id), after=blocking)
            db.commit()
            raise KontrolError(
                code="NODE_HAS_HISTORY", message="El nodo tiene dependencias y no puede borrarse",
                status_code=409,
                details={"reason": "Existen descendientes o histórico asociados",
                         "dependencies": blocking, "allowed_actions": ["deactivate"]},
            )
        _audit(db, actor, "DELETE", f"warehouse_{level}", str(node.id), before={"code": node.code})
        db.delete(node)
        db.commit()
        return {"deleted": True}


for _level in st.LEVEL_ORDER:
    _node_routes(_level)


# --------------------------------------------------------------------------
# Ubicaciones
# --------------------------------------------------------------------------

class LocationIn(BaseModel):
    warehouse_id: str
    code: str | None = None
    name: str | None = None
    zone_id: str | None = None
    aisle_id: str | None = None
    rack_id: str | None = None
    level_id: str | None = None
    location_type_id: str | None = None
    sequence: int = 0
    capacity_units: float | None = None
    capacity_weight: float | None = None
    capacity_uom: str | None = None
    restrictions: dict[str, Any] | None = None
    barcode: str | None = None


class LocationPatch(BaseModel):
    name: str | None = None
    sequence: int | None = None
    location_type_id: str | None = None
    capacity_units: float | None = None
    capacity_weight: float | None = None
    capacity_uom: str | None = None
    restrictions: dict[str, Any] | None = None
    barcode: str | None = None
    zone_id: str | None = None
    aisle_id: str | None = None
    rack_id: str | None = None
    level_id: str | None = None


class BulkLocationIn(BaseModel):
    warehouse_id: str
    pattern: str = Field(min_length=1, max_length=120)
    count: int = Field(ge=1, le=500)
    start: int = 1
    zone_id: str | None = None
    aisle_id: str | None = None
    rack_id: str | None = None
    level_id: str | None = None
    location_type_id: str | None = None
    preview: bool = True


def _chain_of(location: WarehouseLocation) -> dict[str, str | None]:
    return {level: getattr(location, st.LEVEL_FK[level]) for level in st.LEVEL_ORDER}


def _location_dict(db: Session, loc: WarehouseLocation, permissions: set[str] | None = None,
                   *, full: bool = False) -> dict[str, Any]:
    can_delete, history = st.can_delete_location(db, loc)
    data: dict[str, Any] = {
        "id": str(loc.id), "warehouse_id": loc.warehouse_id, "company_id": loc.company_id,
        "code": loc.code, "name": loc.name, "sequence": loc.sequence, "status": loc.status,
        "version": int(loc.version), "legacy_path": loc.legacy_path,
        "display_path": st.display_path(db, loc),
        "can_delete": can_delete,
        "allowed_actions": st.location_allowed_actions(db, loc, permissions),
    }
    if not full:
        return data
    for level in st.LEVEL_ORDER:
        node_id = getattr(loc, st.LEVEL_FK[level])
        node = db.get(st.LEVEL_MODEL[level], node_id) if node_id else None
        data[level] = ({"id": str(node.id), "code": node.code, "name": node.name}
                       if node is not None else None)
    location_type = db.get(LocationType, loc.location_type_id) if loc.location_type_id else None
    data["type"] = ({"id": str(location_type.id), "code": location_type.code,
                     "is_storable": location_type.is_storable}
                    if location_type is not None else None)
    data["capacity"] = {"units": float(loc.capacity_units) if loc.capacity_units is not None else None,
                        "weight": float(loc.capacity_weight) if loc.capacity_weight is not None else None,
                        "uom": loc.capacity_uom}
    data["restrictions"] = loc.restrictions
    data["barcode"] = loc.barcode
    data["delete_blocked_by"] = history or None
    return data


@router.get("/locations")
def search_locations(warehouse_id: str | None = None, q: str | None = None,
                     zone_id: str | None = None, aisle_id: str | None = None,
                     rack_id: str | None = None, level_id: str | None = None,
                     location_type_id: str | None = None, status: str | None = None,
                     limit: int = 50, offset: int = 0, db: Session = Depends(get_db),
                     user: User = Depends(require_permission("organization", "view"))):
    query = select(WarehouseLocation).where(
        WarehouseLocation.company_id.in_(_company_ids(db, user)))
    for column, value in (("warehouse_id", warehouse_id), ("zone_id", zone_id),
                          ("aisle_id", aisle_id), ("rack_id", rack_id), ("level_id", level_id),
                          ("location_type_id", location_type_id), ("status", status)):
        if value:
            query = query.where(getattr(WarehouseLocation, column) == value)
    if q:
        pattern = f"%{q}%"
        query = query.where(WarehouseLocation.code.ilike(pattern)
                            | WarehouseLocation.name.ilike(pattern))
    total = int(db.execute(select(func.count()).select_from(query.subquery())).scalar_one())
    rows = db.execute(
        query.order_by(WarehouseLocation.code).limit(limit).offset(offset)).scalars().all()
    permissions = st.user_permission_set(db, user)
    return {"total": total, "limit": limit, "offset": offset,
            "items": [_location_dict(db, loc, permissions) for loc in rows]}


@router.get("/locations/ordered")
def ordered_locations(warehouse_id: str, status: str | None = None,
                      location_type_id: str | None = None,
                      limit: int = 100, offset: int = 0, db: Session = Depends(get_db),
                      user: User = Depends(require_permission("organization", "view"))):
    """Orden físico determinista. Contrato para la Spec 031.

    008 entrega **datos ordenables y un orden estable**; el algoritmo de
    picking pertenece a 031 y no se implementa aquí.
    """
    warehouse = _get_warehouse(db, user, warehouse_id)
    query = st.physical_order_query(warehouse.id)
    if status:
        query = query.where(WarehouseLocation.status == status)
    if location_type_id:
        query = query.where(WarehouseLocation.location_type_id == location_type_id)
    total = int(db.execute(select(func.count()).select_from(
        select(WarehouseLocation.id).where(
            WarehouseLocation.warehouse_id == warehouse.id).subquery())).scalar_one())
    rows = db.execute(query.limit(limit).offset(offset)).all()
    items = []
    for location, zone_seq, aisle_seq, rack_seq, level_seq in rows:
        items.append({
            "id": str(location.id), "code": location.code, "status": location.status,
            "display_path": st.display_path(db, location),
            # Las secuencias que producen el orden, para que 031 pueda agrupar
            # por tramo sin recalcular.
            "physical_order": [zone_seq, aisle_seq, rack_seq, level_seq, location.sequence],
        })
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.post("/locations", dependencies=[Depends(require_write_allowed)])
def create_location_full(body: LocationIn, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("organization", "create"))):
    warehouse = _get_warehouse(db, actor, body.warehouse_id)
    chain = st.validate_chain(db, warehouse, {
        level: getattr(body, st.LEVEL_FK[level]) for level in st.LEVEL_ORDER})
    code = body.code
    if not code:
        if warehouse.code_policy == "MANUAL":
            raise KontrolError(code="LOCATION_CODE_REQUIRED",
                               message="El almacén exige código manual", status_code=422)
        code = st.generate_location_code(db, warehouse, chain)
    location = WarehouseLocation(
        company_id=warehouse.company_id, warehouse_id=warehouse.id, code=code, name=body.name,
        zone_id=chain["zone"], aisle_id=chain["aisle"], rack_id=chain["rack"],
        level_id=chain["level"], location_type_id=body.location_type_id,
        sequence=body.sequence, capacity_units=body.capacity_units,
        capacity_weight=body.capacity_weight, capacity_uom=body.capacity_uom,
        restrictions=body.restrictions, barcode=body.barcode,
        status="ACTIVE", created_by=str(actor.id),
    )
    db.add(location)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _integrity(exc, "LOCATION_CODE_DUPLICATE",
                         "Ya existe una ubicación con ese código en el almacén") from exc
    db.refresh(location)
    st.promote_regime(db, warehouse)
    _audit(db, actor, "CREATE", "warehouse_location", str(location.id), after={"code": location.code})
    db.commit()
    return _location_dict(db, location, st.user_permission_set(db, actor), full=True)


@router.post("/locations/bulk", dependencies=[Depends(require_write_allowed)])
def bulk_locations(body: BulkLocationIn, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("organization", "create"))):
    """Creación por patrón **con vista previa obligatoria**.

    Con `preview=true` no se escribe nada: se devuelve lo que se crearía y lo
    que ya existe, para que el usuario lo vea antes de decidir (AC-008-23).
    """
    warehouse = _get_warehouse(db, actor, body.warehouse_id)
    chain = st.validate_chain(db, warehouse, {
        level: getattr(body, st.LEVEL_FK[level]) for level in st.LEVEL_ORDER})
    existing = {code for (code,) in db.execute(
        select(WarehouseLocation.code).where(WarehouseLocation.warehouse_id == warehouse.id))}
    planned, conflicts = [], []
    for index in range(body.start, body.start + body.count):
        try:
            code = body.pattern.format(n=index, seq=f"{index:04d}", warehouse=warehouse.code)
        except (KeyError, IndexError) as exc:
            raise KontrolError(code="LOCATION_PATTERN_INVALID",
                               message="El patrón usa un marcador desconocido",
                               status_code=422) from exc
        (conflicts if code in existing else planned).append(code)
    if body.preview:
        return {"preview": True, "would_create": planned, "already_exists": conflicts,
                "total_planned": len(planned), "total_conflicts": len(conflicts)}
    created = []
    for code in planned:
        location = WarehouseLocation(
            company_id=warehouse.company_id, warehouse_id=warehouse.id, code=code,
            zone_id=chain["zone"], aisle_id=chain["aisle"], rack_id=chain["rack"],
            level_id=chain["level"], location_type_id=body.location_type_id,
            status="ACTIVE", created_by=str(actor.id))
        db.add(location)
        created.append(code)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _integrity(exc, "LOCATION_CODE_DUPLICATE",
                         "Otra operación creó uno de los códigos") from exc
    st.promote_regime(db, warehouse)
    _audit(db, actor, "BULK_CREATE", "warehouse_location", str(warehouse.id),
           after={"count": len(created)})
    db.commit()
    return {"preview": False, "created": created, "skipped": conflicts, "total": len(created)}


@router.get("/locations/{location_id}")
def get_location(location_id: str, db: Session = Depends(get_db),
                 user: User = Depends(require_permission("organization", "view"))):
    location = _get_location(db, user, location_id)
    return _location_dict(db, location, st.user_permission_set(db, user), full=True)


@router.patch("/locations/{location_id}", dependencies=[Depends(require_write_allowed)])
def patch_location(location_id: str, body: LocationPatch,
                   if_match: str | None = Header(default=None, alias="If-Match"),
                   db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("organization", "edit"))):
    location = _get_location(db, actor, location_id)
    _check_version(location, if_match)
    warehouse = _get_warehouse(db, actor, location.warehouse_id)
    data = body.model_dump(exclude_unset=True)
    structural = {field: data.pop(field) for field in
                  ("zone_id", "aisle_id", "rack_id", "level_id") if field in data}
    before = {"name": location.name, "sequence": location.sequence}

    if structural:
        # Reubicar una ubicación con historial reescribiría el Kardex: mover
        # mercancía es un movimiento, no una edición (FR-008-056).
        current = _chain_of(location)
        target = {level: structural.get(st.LEVEL_FK[level], current[level])
                  for level in st.LEVEL_ORDER}
        if target != current:
            try:
                st.assert_can_relocate(db, location)
            except KontrolError:
                _audit(db, actor, "RELOCATE_BLOCKED", "warehouse_location", str(location.id))
                db.commit()
                raise
            chain = st.validate_chain(db, warehouse, target)
            for level in st.LEVEL_ORDER:
                setattr(location, st.LEVEL_FK[level], chain[level])
            _audit(db, actor, "HIERARCHY_CHANGED", "warehouse_location", str(location.id),
                   before=current, after=chain)

    for field, value in data.items():
        setattr(location, field, value)
    _bump(location)
    _audit(db, actor, "UPDATE", "warehouse_location", str(location.id), before=before,
           after={"name": location.name, "sequence": location.sequence})
    db.commit()
    db.refresh(location)
    return _location_dict(db, location, st.user_permission_set(db, actor), full=True)


def _set_location_status(db: Session, actor: User, location_id: str, status: str,
                         action: str) -> dict[str, Any]:
    location = _get_location(db, actor, location_id)
    # El estado de la ubicación **no** determina el de la mercancía: bloquear
    # una ubicación no cambia ningún saldo (ADR-D0-010, FR-008-042).
    location.status = status
    _bump(location)
    _audit(db, actor, action, "warehouse_location", str(location.id), after={"status": status})
    db.commit()
    return {"id": str(location.id), "status": location.status}


@router.post("/locations/{location_id}/activate", dependencies=[Depends(require_write_allowed)])
def activate_location(location_id: str, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("organization", "activate"))):
    return _set_location_status(db, actor, location_id, "ACTIVE", "ACTIVATE")


@router.post("/locations/{location_id}/deactivate", dependencies=[Depends(require_write_allowed)])
def deactivate_location(location_id: str, db: Session = Depends(get_db),
                        actor: User = Depends(require_permission("organization", "deactivate"))):
    return _set_location_status(db, actor, location_id, "INACTIVE", "DEACTIVATE")


@router.post("/locations/{location_id}/block", dependencies=[Depends(require_write_allowed)])
def block_location(location_id: str, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("organization", "edit"))):
    return _set_location_status(db, actor, location_id, "BLOCKED", "BLOCK")


@router.delete("/locations/{location_id}", dependencies=[Depends(require_write_allowed)])
def delete_location(location_id: str, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("organization", "delete"))):
    location = _get_location(db, actor, location_id)
    deletable, history = st.can_delete_location(db, location)
    if not deletable:
        _audit(db, actor, "DELETE_BLOCKED", "warehouse_location", str(location.id), after=history)
        db.commit()
        raise KontrolError(
            code="LOCATION_HAS_HISTORY",
            message="La ubicación tiene historial y no puede borrarse", status_code=409,
            details={"reason": "Existen movimientos, saldos o conteos asociados",
                     "dependencies": history, "allowed_actions": ["deactivate"]},
        )
    _audit(db, actor, "DELETE", "warehouse_location", str(location.id),
           before={"code": location.code})
    db.delete(location)
    db.commit()
    return {"deleted": True}


# --------------------------------------------------------------------------
# Estructura
# --------------------------------------------------------------------------

@router.get("/warehouses/{warehouse_id}/structure")
def warehouse_structure(warehouse_id: str, depth: str = "level", status: str | None = None,
                        limit: int = 50, offset: int = 0, db: Session = Depends(get_db),
                        user: User = Depends(require_permission("organization", "view"))):
    """Árbol con profundidad controlada.

    Las ubicaciones **solo** se incluyen con `depth=locations`, y siempre
    paginadas: un almacén de 50.000 ubicaciones nunca devuelve su árbol entero
    (NFR-008-02).
    """
    if depth not in (*st.LEVEL_ORDER, "locations"):
        raise KontrolError(code="STRUCTURE_DEPTH_INVALID",
                           message="Profundidad no reconocida", status_code=422,
                           details={"allowed": [*st.LEVEL_ORDER, "locations"]})
    warehouse = _get_warehouse(db, user, warehouse_id)
    declared = st.declared_levels(warehouse)
    permissions = st.user_permission_set(db, user)
    wanted = st.LEVEL_ORDER[:st.LEVEL_ORDER.index(depth) + 1] if depth != "locations" else st.LEVEL_ORDER

    def nodes(level: str, parent_id: str | None) -> list[dict[str, Any]]:
        if level not in declared or level not in wanted:
            return []
        model = st.LEVEL_MODEL[level]
        query = select(model).where(model.warehouse_id == warehouse.id)
        parent_fk = st.LEVEL_PARENT_FK[level]
        if parent_fk:
            query = query.where(getattr(model, parent_fk) == parent_id)
        if status:
            query = query.where(model.status == status)
        result = []
        for node in db.execute(query.order_by(model.sequence, model.code)).scalars().all():
            index = st.LEVEL_ORDER.index(level)
            child_key = None
            children: list[dict[str, Any]] = []
            if index + 1 < len(st.LEVEL_ORDER):
                child_level = st.LEVEL_ORDER[index + 1]
                child_key = {"aisle": "aisles", "rack": "racks", "level": "levels"}[child_level]
                children = nodes(child_level, node.id)
            entry = {"id": str(node.id), "code": node.code, "name": node.name,
                     "sequence": node.sequence, "status": node.status}
            if child_key is not None:
                entry[child_key] = children
            result.append(entry)
        return result

    payload: dict[str, Any] = {
        "warehouse": {"id": str(warehouse.id), "code": warehouse.code, "name": warehouse.name,
                      "structure_levels": st.normalize_structure_levels(warehouse.structure_levels),
                      "structure_regime": st.current_regime(db, warehouse)},
        "zones": nodes("zone", None),
        # Un almacén sin zonas puede tener pasillos: la cadena admite huecos.
        "aisles": nodes("aisle", None) if "zone" not in declared else [],
        "allowed_actions": st.warehouse_allowed_actions(db, warehouse, permissions),
    }
    if depth == "locations":
        query = select(WarehouseLocation).where(WarehouseLocation.warehouse_id == warehouse.id)
        if status:
            query = query.where(WarehouseLocation.status == status)
        total = int(db.execute(select(func.count()).select_from(query.subquery())).scalar_one())
        rows = db.execute(
            query.order_by(WarehouseLocation.code).limit(limit).offset(offset)).scalars().all()
        payload["locations"] = {"total": total, "limit": limit, "offset": offset,
                                "items": [_location_dict(db, loc, permissions) for loc in rows]}
    return payload
