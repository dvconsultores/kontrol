"""API de la estructura física de almacén (Spec 008).

Prefijo `/api/v1/organization`, convención vigente del módulo. Todo endpoint
exige sesión, permiso y filtra por empresa: el aislamiento vive aquí, no en el
frontend (P6).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import (
    require_permission,
    require_recent_reauth,
    require_write_allowed,
)
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.core.integrity import es_violacion_unica_de, restriccion_unica
from app.modules.identity_access.models import User
from app.modules.organization import structure as st
from app.modules.organization.models import (
    Branch,
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

def _alcance(ctx: CompanyContext) -> list[str]:
    """La empresa en la que se está operando, y solo esa.

    Antes esto devolvía todas las empresas del tenant. Con una sola empresa por
    tenant daba igual; con dos, un almacén de la empresa B aparecía en el
    listado de la empresa A y se dejaba leer y modificar desde ella. El
    comentario de `_get_warehouse` ya describía la intención correcta —«un
    almacén de otra empresa se responde como inexistente»— y la implementación
    se había quedado en el mundo anterior.
    """
    return [ctx.company_id]


def _get_warehouse(db: Session, ctx: CompanyContext, warehouse_id: str) -> Warehouse:
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.company_id not in _alcance(ctx):
        # Un almacén de otra empresa se responde como inexistente: revelar que
        # existe ya sería una filtración (enumeración).
        raise NotFoundError(code="WAREHOUSE_NOT_FOUND", message="Almacén no encontrado")
    return warehouse


def _exige_sucursal_propia(db: Session, ctx: CompanyContext, branch_id: str | None) -> None:
    """La sucursal del almacén es de la empresa activa (ADR-D0-014); ajena, de otro tenant o
    inexistente se responde igual, como inexistente, para no revelar sucursales de otras empresas;
    mismo contrato que `create_establishment`."""
    if branch_id is None:
        return
    sucursal = db.get(Branch, branch_id)
    if sucursal is None or sucursal.company_id != ctx.company_id:
        raise NotFoundError(code="BRANCH_NOT_FOUND", message="Sucursal no encontrada")


def _exige_tipo_propio(db: Session, ctx: CompanyContext, modelo: type[LocationType] | type[ZoneType],
                       tipo_id: str | None, code: str, message: str) -> None:
    """El tipo de catálogo es de la empresa activa (ADR-D0-014); ajeno, de otro tenant o
    inexistente se responden igual, como inexistentes; mismo patrón que `_exige_sucursal_propia`."""
    if tipo_id is None:
        return
    empresa = db.scalar(select(modelo.company_id).where(modelo.id == tipo_id))
    if empresa != ctx.company_id:
        raise NotFoundError(code=code, message=message)


def _get_node(db: Session, ctx: CompanyContext, level: str, node_id: str) -> Any:
    node = db.get(st.LEVEL_MODEL[level], node_id)
    if node is None or node.company_id not in _alcance(ctx):
        raise NotFoundError(code=f"{level.upper()}_NOT_FOUND", message="Nodo no encontrado")
    return node


def _get_location(db: Session, ctx: CompanyContext, location_id: str) -> WarehouseLocation:
    location = db.get(WarehouseLocation, location_id)
    if location is None or location.company_id not in _alcance(ctx):
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


def _audit(db: Session, user: User, ctx: CompanyContext, action: str, entity_type: str,
           entity_id: str, before: dict | None = None, after: dict | None = None) -> None:
    """El rastro guarda también la empresa.

    Antes solo anotaba el tenant, así que crear un almacén en la empresa A y
    crearlo en la B dejaban registros indistinguibles: el rastro sabía en qué
    instalación había pasado algo, pero no en cuál de las empresas.
    """
    record_audit(db, action=action, entity_type=entity_type, entity_id=entity_id,
                 tenant_id=user.tenant_id, company_id=ctx.company_id,
                 user_id=str(user.id), before=before, after=after)


# OBS-01: solo la violación única de la restricción del código se traduce al
# 409 de dominio; cualquier otro IntegrityError se relanza y el manejador
# genérico lo convierte en el 500 INTERNAL_ERROR saneado.
_UQ_CATALOGO = {
    ZoneType: restriccion_unica(ZoneType.__table__, "uq_zone_types_company_code"),
    LocationType: restriccion_unica(LocationType.__table__, "uq_location_types_company_code"),
}
_UQ_ALMACEN = restriccion_unica(Warehouse.__table__, "uq_warehouses_company_code")
_UQ_NODO = {
    "zone": restriccion_unica(st.LEVEL_MODEL["zone"].__table__, "uq_warehouse_zones_wh_code"),
    "aisle": restriccion_unica(st.LEVEL_MODEL["aisle"].__table__, "uq_warehouse_aisles_wh_code"),
    "rack": restriccion_unica(st.LEVEL_MODEL["rack"].__table__, "uq_warehouse_racks_wh_code"),
    "level": restriccion_unica(st.LEVEL_MODEL["level"].__table__, "uq_warehouse_levels_wh_code"),
}
_UQ_UBICACION = restriccion_unica(WarehouseLocation.__table__, "uq_warehouse_locations_wh_code")


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


def _catalog_list(db: Session, ctx: CompanyContext, model: Any, company_id: str | None) -> list[dict[str, Any]]:
    query = select(model).where(model.company_id.in_(_alcance(ctx)))
    if company_id:
        query = query.where(model.company_id == company_id)
    rows = db.execute(query.order_by(model.code)).scalars().all()
    return [{"id": str(r.id), "company_id": r.company_id, "code": r.code, "name": r.name,
             "status": r.status,
             **({"is_storable": r.is_storable} if hasattr(r, "is_storable") else {}),
             **({"description": r.description} if hasattr(r, "description") else {})}
            for r in rows]


def _catalog_create(db: Session, actor: User, ctx: CompanyContext, model: Any,
                    values: dict[str, Any], entity: str) -> dict[str, Any]:
    # La empresa la decide el contexto validado, no el cuerpo de la petición.
    values = {**values, "company_id": ctx.company_id}
    row = model(**values, status="ACTIVE", created_by=str(actor.id))
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if not es_violacion_unica_de(exc, _UQ_CATALOGO[model]):
            raise
        raise ConflictError(code=f"{entity.upper()}_CODE_DUPLICATE",
                            message="Ya existe un tipo con ese código en la empresa") from exc
    db.refresh(row)
    _audit(db, actor, ctx, "CREATE", entity, str(row.id), after={"code": row.code})
    db.commit()
    return {"id": str(row.id), "code": row.code, "name": row.name}


def _catalog_update(db: Session, actor: User, ctx: CompanyContext, model: Any,
                    item_id: str, body: dict[str, Any], entity: str) -> dict[str, Any]:
    row = db.get(model, item_id)
    if row is None or row.company_id not in _alcance(ctx):
        raise NotFoundError(code="NOT_FOUND", message="Tipo no encontrado")
    before = {"name": row.name, "status": row.status}
    for field in ("name", "description", "is_storable", "status"):
        if field in body and hasattr(row, field):
            setattr(row, field, body[field])
    _audit(db, actor, ctx, "UPDATE", entity, str(row.id), before=before,
           after={"name": row.name, "status": row.status})
    db.commit()
    return {"id": str(row.id), "code": row.code, "name": row.name, "status": row.status}


@router.get("/zone-types")
def list_zone_types(company_id: str | None = None, db: Session = Depends(get_db),
                    user: User = Depends(require_permission("organization", "view")),
    ctx: CompanyContext = Depends(get_company_context)):
    return _catalog_list(db, ctx, ZoneType, company_id)


@router.post("/zone-types", dependencies=[Depends(require_write_allowed)])
def create_zone_type(body: ZoneTypeIn, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("organization", "create")),
    ctx: CompanyContext = Depends(get_company_context)):
    return _catalog_create(db, actor, ctx, ZoneType, body.model_dump(), "zone_type")


@router.patch("/zone-types/{item_id}", dependencies=[Depends(require_write_allowed)])
def update_zone_type(item_id: str, body: dict[str, Any], db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("organization", "edit")),
    ctx: CompanyContext = Depends(get_company_context)):
    return _catalog_update(db, actor, ctx, ZoneType, item_id, body, "zone_type")


@router.get("/location-types")
def list_location_types(company_id: str | None = None, db: Session = Depends(get_db),
                        user: User = Depends(require_permission("organization", "view")),
    ctx: CompanyContext = Depends(get_company_context)):
    return _catalog_list(db, ctx, LocationType, company_id)


@router.post("/location-types", dependencies=[Depends(require_write_allowed)])
def create_location_type(body: LocationTypeIn, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("organization", "create")),
    ctx: CompanyContext = Depends(get_company_context)):
    return _catalog_create(db, actor, ctx, LocationType, body.model_dump(), "location_type")


@router.patch("/location-types/{item_id}", dependencies=[Depends(require_write_allowed)])
def update_location_type(item_id: str, body: dict[str, Any], db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("organization", "edit")),
    ctx: CompanyContext = Depends(get_company_context)):
    return _catalog_update(db, actor, ctx, LocationType, item_id, body, "location_type")


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


def _warehouse_dict(db: Session, w: Warehouse, permissions: set[str] | None = None, *,
                    dependencies: dict[str, int] | None = None) -> dict[str, Any]:
    # Un almacén suelto se pregunta a la base. Una página entera trae sus
    # dependencias ya contadas (`st.warehouses_dependencies`) y no vuelve a
    # preguntar fila por fila: eran una docena de consultas por almacén.
    if dependencies is None:
        can_delete, blocking = st.can_delete_warehouse(db, w)
        view = {
            "can_delete": can_delete,
            "delete_blocked_by": blocking.get("dependencies") if blocking else None,
            "structure_regime": st.current_regime(db, w),
            "allowed_actions": st.warehouse_allowed_actions(db, w, permissions),
        }
    else:
        view = st.warehouse_view(w, dependencies, permissions)
    return {
        "id": str(w.id), "company_id": w.company_id, "branch_id": w.branch_id,
        "code": w.code, "name": w.name, "warehouse_type": w.warehouse_type,
        "address": w.address, "manager_id": w.manager_id, "description": w.description,
        "location_managed": w.location_managed,
        "structure_levels": st.normalize_structure_levels(w.structure_levels),
        "structure_regime": view["structure_regime"],
        "declared_levels": st.declared_levels(w),
        "code_policy": w.code_policy, "code_pattern": w.code_pattern,
        "status": w.status, "version": int(w.version),
        "can_delete": view["can_delete"],
        "delete_blocked_by": view["delete_blocked_by"],
        "allowed_actions": view["allowed_actions"],
    }


@router.get("/warehouses")
def search_warehouses(q: str | None = None, branch_id: str | None = None,
                      status: str | None = None, company_id: str | None = None,
                      limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                      db: Session = Depends(get_db),
                      user: User = Depends(require_permission("organization", "view")),
    ctx: CompanyContext = Depends(get_company_context)):
    query = select(Warehouse).where(Warehouse.company_id.in_(_alcance(ctx)))
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
    dependencies = st.warehouses_dependencies(db, [str(w.id) for w in rows])
    return {"total": total, "limit": limit, "offset": offset,
            "items": [_warehouse_dict(db, w, permissions, dependencies=dependencies[str(w.id)])
                      for w in rows]}


@router.post("/warehouses", dependencies=[Depends(require_write_allowed)])
def create_warehouse_full(body: WarehouseIn, db: Session = Depends(get_db),
                          actor: User = Depends(require_permission("organization", "create")),
    ctx: CompanyContext = Depends(get_company_context)):
    if body.company_id and body.company_id != ctx.company_id:
        # El cuerpo no puede designar otra empresa que la del contexto validado.
        raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")
    if not body.code:
        raise KontrolError(code="WAREHOUSE_CODE_REQUIRED",
                           message="El código del almacén es obligatorio", status_code=422)
    _exige_sucursal_propia(db, ctx, body.branch_id)
    warehouse = Warehouse(
        company_id=ctx.company_id, branch_id=body.branch_id, code=body.code, name=body.name,
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
        if not es_violacion_unica_de(exc, _UQ_ALMACEN):
            raise
        raise ConflictError(code="WAREHOUSE_CODE_DUPLICATE",
                            message="Ya existe un almacén con ese código en la empresa") from exc
    db.refresh(warehouse)
    _audit(db, actor, ctx, "CREATE", "warehouse", str(warehouse.id), after={"code": warehouse.code})
    db.commit()
    return _warehouse_dict(db, warehouse, st.user_permission_set(db, actor))


@router.get("/warehouses/{warehouse_id}")
def get_warehouse(warehouse_id: str, db: Session = Depends(get_db),
                  user: User = Depends(require_permission("organization", "view")),
    ctx: CompanyContext = Depends(get_company_context)):
    warehouse = _get_warehouse(db, ctx, warehouse_id)
    return _warehouse_dict(db, warehouse, st.user_permission_set(db, user))


@router.patch("/warehouses/{warehouse_id}", dependencies=[Depends(require_write_allowed)])
def patch_warehouse(warehouse_id: str, body: WarehousePatch,
                    if_match: str | None = Header(default=None, alias="If-Match"),
                    db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("organization", "edit")),
    ctx: CompanyContext = Depends(get_company_context)):
    warehouse = _get_warehouse(db, ctx, warehouse_id)
    _check_version(warehouse, if_match)
    if "branch_id" in body.model_fields_set:
        _exige_sucursal_propia(db, ctx, body.branch_id)
    before = {"name": warehouse.name, "location_managed": warehouse.location_managed}
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(warehouse, field, value)
    _bump(warehouse)
    _audit(db, actor, ctx, "UPDATE", "warehouse", str(warehouse.id), before=before,
           after={"name": warehouse.name, "location_managed": warehouse.location_managed})
    db.commit()
    db.refresh(warehouse)
    return _warehouse_dict(db, warehouse, st.user_permission_set(db, actor))


@router.patch("/warehouses/{warehouse_id}/structure-levels",
              dependencies=[Depends(require_write_allowed)])
def patch_structure_levels(warehouse_id: str, body: StructureLevelsPatch,
                           db: Session = Depends(get_db),
                           actor: User = Depends(require_permission("organization", "manage_structure")),
    ctx: CompanyContext = Depends(get_company_context)):
    """Único camino para cambiar `structure_levels`.

    En régimen operativo rechaza eliminar, reordenar o colapsar un tramo
    utilizado. El bloqueo se produce **aquí**: invocar este endpoint saltándose
    el frontend obtiene el mismo rechazo (Control 2).
    """
    warehouse = _get_warehouse(db, ctx, warehouse_id)
    before = st.normalize_structure_levels(warehouse.structure_levels)
    try:
        warehouse.structure_levels = st.validate_structure_levels_change(
            db, warehouse, body.structure_levels)
    except KontrolError:
        _audit(db, actor, ctx, "STRUCTURE_CHANGE_BLOCKED", "warehouse", str(warehouse.id),
               before=before, after=st.normalize_structure_levels(body.structure_levels))
        db.commit()
        raise
    _bump(warehouse)
    _audit(db, actor, ctx, "STRUCTURE_LEVELS_CHANGED", "warehouse", str(warehouse.id),
           before=before, after=warehouse.structure_levels)
    db.commit()
    db.refresh(warehouse)
    return _warehouse_dict(db, warehouse, st.user_permission_set(db, actor))


@router.post("/warehouses/{warehouse_id}/activate", dependencies=[Depends(require_write_allowed)])
def activate_warehouse(warehouse_id: str, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("organization", "activate")),
    ctx: CompanyContext = Depends(get_company_context)):
    warehouse = _get_warehouse(db, ctx, warehouse_id)
    warehouse.status = "ACTIVE"
    _bump(warehouse)
    _audit(db, actor, ctx, "ACTIVATE", "warehouse", str(warehouse.id), after={"status": "ACTIVE"})
    db.commit()
    return {"id": str(warehouse.id), "status": warehouse.status}


@router.post(
    "/warehouses/{warehouse_id}/deactivate",
    dependencies=[Depends(require_write_allowed), Depends(require_recent_reauth)],
)
def deactivate_warehouse(warehouse_id: str, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("organization", "deactivate")),
    ctx: CompanyContext = Depends(get_company_context)):
    warehouse = _get_warehouse(db, ctx, warehouse_id)
    warehouse.status = "INACTIVE"
    _bump(warehouse)
    _audit(db, actor, ctx, "DEACTIVATE", "warehouse", str(warehouse.id), after={"status": "INACTIVE"})
    db.commit()
    return {"id": str(warehouse.id), "status": warehouse.status}


@router.delete(
    "/warehouses/{warehouse_id}",
    dependencies=[Depends(require_write_allowed), Depends(require_recent_reauth)],
)
def delete_warehouse(warehouse_id: str, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("organization", "delete")),
    ctx: CompanyContext = Depends(get_company_context)):
    """Borrar un almacén **nunca** destruye ubicaciones (R-008-8): si tiene
    estructura, ubicaciones o movimientos, se rechaza y no se toca nada."""
    warehouse = _get_warehouse(db, ctx, warehouse_id)
    deletable, blocking = st.can_delete_warehouse(db, warehouse)
    if not deletable:
        _audit(db, actor, ctx, "DELETE_BLOCKED", "warehouse", str(warehouse.id), after=blocking)
        db.commit()
        raise KontrolError(
            code="NODE_HAS_HISTORY", message="El almacén tiene dependencias y no puede borrarse",
            status_code=409,
            details={"reason": "Existen nodos, ubicaciones o movimientos asociados",
                     "dependencies": blocking.get("dependencies", {}),
                     "allowed_actions": ["deactivate"]},
        )
    _audit(db, actor, ctx, "DELETE", "warehouse", str(warehouse.id), before={"code": warehouse.code})
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
              user: User = Depends(require_permission("organization", "view")),
        ctx: CompanyContext = Depends(get_company_context)):
        warehouse = _get_warehouse(db, ctx, warehouse_id)
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
                actor: User = Depends(require_permission("organization", "create")),
        ctx: CompanyContext = Depends(get_company_context)):
        warehouse = _get_warehouse(db, ctx, warehouse_id)
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
            _exige_tipo_propio(db, ctx, ZoneType, body.zone_type_id,
                               "ZONE_TYPE_NOT_FOUND", "Tipo de zona no encontrado")
            values["zone_type_id"] = body.zone_type_id
        if level == "level":
            values["height_order"] = body.height_order
        node = model(**values)
        db.add(node)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            if not es_violacion_unica_de(exc, _UQ_NODO[level]):
                raise
            raise ConflictError(code=f"{level.upper()}_CODE_DUPLICATE",
                                message="Ya existe un nodo con ese código en el almacén") from exc
        db.refresh(node)
        # Crear el primer nodo hace operativo el almacén: viaje de ida (R-008-6).
        st.promote_regime(db, warehouse)
        _audit(db, actor, ctx, "CREATE", f"warehouse_{level}", str(node.id), after={"code": node.code})
        db.commit()
        return _node_dict(db, level, node, st.user_permission_set(db, actor))

    @router.get(f"/{plural}/{{node_id}}", name=f"get_{level}")
    def _get(node_id: str, db: Session = Depends(get_db),
             user: User = Depends(require_permission("organization", "view")),
        ctx: CompanyContext = Depends(get_company_context)):
        node = _get_node(db, ctx, level, node_id)
        return _node_dict(db, level, node, st.user_permission_set(db, user))

    @router.patch(f"/{plural}/{{node_id}}", dependencies=[Depends(require_write_allowed)],
                  name=f"patch_{level}")
    def _patch(node_id: str, body: NodePatch,
               if_match: str | None = Header(default=None, alias="If-Match"),
               db: Session = Depends(get_db),
               actor: User = Depends(require_permission("organization", "edit")),
        ctx: CompanyContext = Depends(get_company_context)):
        node = _get_node(db, ctx, level, node_id)
        _check_version(node, if_match)
        warehouse = _get_warehouse(db, ctx, node.warehouse_id)
        if level == "zone" and "zone_type_id" in body.model_fields_set:
            _exige_tipo_propio(db, ctx, ZoneType, body.zone_type_id,
                               "ZONE_TYPE_NOT_FOUND", "Tipo de zona no encontrado")
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
        _audit(db, actor, ctx, "UPDATE", f"warehouse_{level}", str(node.id), before=before,
               after={"name": node.name, "sequence": node.sequence, "status": node.status})
        db.commit()
        db.refresh(node)
        return _node_dict(db, level, node, st.user_permission_set(db, actor))

    @router.post(f"/{plural}/{{node_id}}/activate", dependencies=[Depends(require_write_allowed)],
                 name=f"activate_{level}")
    def _activate(node_id: str, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("organization", "activate")),
        ctx: CompanyContext = Depends(get_company_context)):
        node = _get_node(db, ctx, level, node_id)
        node.status = "ACTIVE"
        _bump(node)
        _audit(db, actor, ctx, "ACTIVATE", f"warehouse_{level}", str(node.id), after={"status": "ACTIVE"})
        db.commit()
        return {"id": str(node.id), "status": node.status}

    @router.post(
        f"/{plural}/{{node_id}}/deactivate",
        dependencies=[Depends(require_write_allowed), Depends(require_recent_reauth)],
                 name=f"deactivate_{level}")
    def _deactivate(node_id: str, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("organization", "deactivate")),
        ctx: CompanyContext = Depends(get_company_context)):
        node = _get_node(db, ctx, level, node_id)
        try:
            st.assert_can_deactivate_node(db, level, node.id)
        except KontrolError:
            _audit(db, actor, ctx, "DEACTIVATE_BLOCKED", f"warehouse_{level}", str(node.id))
            db.commit()
            raise
        node.status = "INACTIVE"
        _bump(node)
        _audit(db, actor, ctx, "DEACTIVATE", f"warehouse_{level}", str(node.id),
               after={"status": "INACTIVE"})
        db.commit()
        return {"id": str(node.id), "status": node.status}

    @router.delete(
        f"/{plural}/{{node_id}}",
        dependencies=[Depends(require_write_allowed), Depends(require_recent_reauth)],
                   name=f"delete_{level}")
    def _delete(node_id: str, db: Session = Depends(get_db),
                actor: User = Depends(require_permission("organization", "delete")),
        ctx: CompanyContext = Depends(get_company_context)):
        node = _get_node(db, ctx, level, node_id)
        deletable, blocking = st.can_delete_node(db, level, node.id)
        if not deletable:
            _audit(db, actor, ctx, "DELETE_BLOCKED", f"warehouse_{level}", str(node.id), after=blocking)
            db.commit()
            raise KontrolError(
                code="NODE_HAS_HISTORY", message="El nodo tiene dependencias y no puede borrarse",
                status_code=409,
                details={"reason": "Existen descendientes o histórico asociados",
                         "dependencies": blocking, "allowed_actions": ["deactivate"]},
            )
        _audit(db, actor, ctx, "DELETE", f"warehouse_{level}", str(node.id), before={"code": node.code})
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
                     user: User = Depends(require_permission("organization", "view")),
    ctx: CompanyContext = Depends(get_company_context)):
    query = select(WarehouseLocation).where(
        WarehouseLocation.company_id.in_(_alcance(ctx)))
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
                      user: User = Depends(require_permission("organization", "view")),
    ctx: CompanyContext = Depends(get_company_context)):
    """Orden físico determinista. Contrato para la Spec 031.

    008 entrega **datos ordenables y un orden estable**; el algoritmo de
    picking pertenece a 031 y no se implementa aquí.
    """
    warehouse = _get_warehouse(db, ctx, warehouse_id)
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
                         actor: User = Depends(require_permission("organization", "create")),
    ctx: CompanyContext = Depends(get_company_context)):
    warehouse = _get_warehouse(db, ctx, body.warehouse_id)
    chain = st.validate_chain(db, warehouse, {
        level: getattr(body, st.LEVEL_FK[level]) for level in st.LEVEL_ORDER})
    code = body.code
    if not code:
        if warehouse.code_policy == "MANUAL":
            raise KontrolError(code="LOCATION_CODE_REQUIRED",
                               message="El almacén exige código manual", status_code=422)
        code = st.generate_location_code(db, warehouse, chain)
    _exige_tipo_propio(db, ctx, LocationType, body.location_type_id,
                       "LOCATION_TYPE_NOT_FOUND", "Tipo de ubicación no encontrado")
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
        if not es_violacion_unica_de(exc, _UQ_UBICACION):
            raise
        raise ConflictError(code="LOCATION_CODE_DUPLICATE",
                            message="Ya existe una ubicación con ese código en el almacén") from exc
    db.refresh(location)
    st.promote_regime(db, warehouse)
    _audit(db, actor, ctx, "CREATE", "warehouse_location", str(location.id), after={"code": location.code})
    db.commit()
    return _location_dict(db, location, st.user_permission_set(db, actor), full=True)


@router.post("/locations/bulk", dependencies=[Depends(require_write_allowed)])
def bulk_locations(body: BulkLocationIn, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("organization", "create")),
    ctx: CompanyContext = Depends(get_company_context)):
    """Creación por patrón **con vista previa obligatoria**.

    Con `preview=true` no se escribe nada: se devuelve lo que se crearía y lo
    que ya existe, para que el usuario lo vea antes de decidir (AC-008-23).
    """
    warehouse = _get_warehouse(db, ctx, body.warehouse_id)
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
    _exige_tipo_propio(db, ctx, LocationType, body.location_type_id,
                       "LOCATION_TYPE_NOT_FOUND", "Tipo de ubicación no encontrado")
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
        if not es_violacion_unica_de(exc, _UQ_UBICACION):
            raise
        raise ConflictError(code="LOCATION_CODE_DUPLICATE",
                            message="Otra operación creó uno de los códigos") from exc
    st.promote_regime(db, warehouse)
    _audit(db, actor, ctx, "BULK_CREATE", "warehouse_location", str(warehouse.id),
           after={"count": len(created)})
    db.commit()
    return {"preview": False, "created": created, "skipped": conflicts, "total": len(created)}


@router.get("/locations/{location_id}")
def get_location(location_id: str, db: Session = Depends(get_db),
                 user: User = Depends(require_permission("organization", "view")),
    ctx: CompanyContext = Depends(get_company_context)):
    location = _get_location(db, ctx, location_id)
    return _location_dict(db, location, st.user_permission_set(db, user), full=True)


@router.patch("/locations/{location_id}", dependencies=[Depends(require_write_allowed)])
def patch_location(location_id: str, body: LocationPatch,
                   if_match: str | None = Header(default=None, alias="If-Match"),
                   db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("organization", "edit")),
    ctx: CompanyContext = Depends(get_company_context)):
    location = _get_location(db, ctx, location_id)
    _check_version(location, if_match)
    warehouse = _get_warehouse(db, ctx, location.warehouse_id)
    if "location_type_id" in body.model_fields_set:
        _exige_tipo_propio(db, ctx, LocationType, body.location_type_id,
                           "LOCATION_TYPE_NOT_FOUND", "Tipo de ubicación no encontrado")
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
                _audit(db, actor, ctx, "RELOCATE_BLOCKED", "warehouse_location", str(location.id))
                db.commit()
                raise
            chain = st.validate_chain(db, warehouse, target)
            for level in st.LEVEL_ORDER:
                setattr(location, st.LEVEL_FK[level], chain[level])
            _audit(db, actor, ctx, "HIERARCHY_CHANGED", "warehouse_location", str(location.id),
                   before=current, after=chain)

    for field, value in data.items():
        setattr(location, field, value)
    _bump(location)
    _audit(db, actor, ctx, "UPDATE", "warehouse_location", str(location.id), before=before,
           after={"name": location.name, "sequence": location.sequence})
    db.commit()
    db.refresh(location)
    return _location_dict(db, location, st.user_permission_set(db, actor), full=True)


def _set_location_status(db: Session, actor: User, ctx: CompanyContext, location_id: str,
                         status: str, action: str) -> dict[str, Any]:
    location = _get_location(db, ctx, location_id)
    # El estado de la ubicación **no** determina el de la mercancía: bloquear
    # una ubicación no cambia ningún saldo (ADR-D0-010, FR-008-042).
    location.status = status
    _bump(location)
    _audit(db, actor, ctx, action, "warehouse_location", str(location.id), after={"status": status})
    db.commit()
    return {"id": str(location.id), "status": location.status}


@router.post("/locations/{location_id}/activate", dependencies=[Depends(require_write_allowed)])
def activate_location(location_id: str, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("organization", "activate")),
                      ctx: CompanyContext = Depends(get_company_context)):
    return _set_location_status(db, actor, ctx, location_id, "ACTIVE", "ACTIVATE")


@router.post(
    "/locations/{location_id}/deactivate",
    dependencies=[Depends(require_write_allowed), Depends(require_recent_reauth)],
)
def deactivate_location(location_id: str, db: Session = Depends(get_db),
                        actor: User = Depends(require_permission("organization", "deactivate")),
                      ctx: CompanyContext = Depends(get_company_context)):
    return _set_location_status(db, actor, ctx, location_id, "INACTIVE", "DEACTIVATE")


@router.post("/locations/{location_id}/block", dependencies=[Depends(require_write_allowed)])
def block_location(location_id: str, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("organization", "edit")),
                      ctx: CompanyContext = Depends(get_company_context)):
    return _set_location_status(db, actor, ctx, location_id, "BLOCKED", "BLOCK")


@router.delete(
    "/locations/{location_id}",
    dependencies=[Depends(require_write_allowed), Depends(require_recent_reauth)],
)
def delete_location(location_id: str, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("organization", "delete")),
    ctx: CompanyContext = Depends(get_company_context)):
    location = _get_location(db, ctx, location_id)
    deletable, history = st.can_delete_location(db, location)
    if not deletable:
        _audit(db, actor, ctx, "DELETE_BLOCKED", "warehouse_location", str(location.id), after=history)
        db.commit()
        raise KontrolError(
            code="LOCATION_HAS_HISTORY",
            message="La ubicación tiene historial y no puede borrarse", status_code=409,
            details={"reason": "Existen movimientos, saldos o conteos asociados",
                     "dependencies": history, "allowed_actions": ["deactivate"]},
        )
    _audit(db, actor, ctx, "DELETE", "warehouse_location", str(location.id),
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
                        user: User = Depends(require_permission("organization", "view")),
    ctx: CompanyContext = Depends(get_company_context)):
    """Árbol con profundidad controlada.

    Las ubicaciones **solo** se incluyen con `depth=locations`, y siempre
    paginadas: un almacén de 50.000 ubicaciones nunca devuelve su árbol entero
    (NFR-008-02).
    """
    if depth not in (*st.LEVEL_ORDER, "locations"):
        raise KontrolError(code="STRUCTURE_DEPTH_INVALID",
                           message="Profundidad no reconocida", status_code=422,
                           details={"allowed": [*st.LEVEL_ORDER, "locations"]})
    warehouse = _get_warehouse(db, ctx, warehouse_id)
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
