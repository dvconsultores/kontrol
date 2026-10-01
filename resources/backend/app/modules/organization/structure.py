"""Motor de estructura física de almacén (Spec 008).

Aquí vive el valor de la Spec: la coherencia de la cadena, el régimen de
mutabilidad, el orden físico determinista y las reglas de borrado. Todo se
prueba sin API.

Ninguna zona, cantidad de pasillos, profundidad ni regla de cliente concreto
aparece en este módulo: **la estructura es dato, no código** (P8, R-008-3).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.organization.models import (
    Warehouse,
    WarehouseAisle,
    WarehouseLevel,
    WarehouseLocation,
    WarehouseRack,
    WarehouseZone,
)

# Orden canónico de la cadena. Es la única secuencia admitida; un almacén elige
# qué tramos usa, no en qué orden se anidan.
LEVEL_ORDER: tuple[str, ...] = ("zone", "aisle", "rack", "level")

LEVEL_MODEL: dict[str, Any] = {
    "zone": WarehouseZone,
    "aisle": WarehouseAisle,
    "rack": WarehouseRack,
    "level": WarehouseLevel,
}

# Columna de `WarehouseLocation` que referencia cada tramo.
LEVEL_FK: dict[str, str] = {
    "zone": "zone_id",
    "aisle": "aisle_id",
    "rack": "rack_id",
    "level": "level_id",
}

# Columna con la que cada tramo apunta a su padre inmediato.
LEVEL_PARENT_FK: dict[str, str | None] = {
    "zone": None,
    "aisle": "zone_id",
    "rack": "aisle_id",
    "level": "rack_id",
}

VALID_STATUSES: tuple[str, ...] = ("ACTIVE", "INACTIVE", "BLOCKED", "MAINTENANCE")

REGIME_INITIAL = "INITIAL"
REGIME_OPERATIONAL = "OPERATIONAL"


# --------------------------------------------------------------------------
# structure_levels
# --------------------------------------------------------------------------

def declared_levels(warehouse: Warehouse) -> list[str]:
    """Tramos que este almacén declara, en orden canónico.

    Un almacén sin `structure_levels` es un almacén simple: `Warehouse →
    Location`, y esa es una configuración válida y completa (R-008-1).
    """
    raw = warehouse.structure_levels or {}
    return [level for level in LEVEL_ORDER if raw.get(level) is True]


def normalize_structure_levels(value: dict[str, Any] | None) -> dict[str, bool]:
    """Normaliza a las cuatro claves conocidas. Ignora claves desconocidas en
    lugar de aceptarlas: el vocabulario de tramos es cerrado."""
    raw = value or {}
    return {level: bool(raw.get(level)) for level in LEVEL_ORDER}


def used_levels(db: Session, warehouse_id: str) -> dict[str, int]:
    """Recuento de nodos por tramo. Un tramo con nodos está **utilizado**,
    tenga esos nodos activos o inactivos."""
    counts: dict[str, int] = {}
    for level, model in LEVEL_MODEL.items():
        counts[level] = int(db.execute(
            select(func.count()).select_from(model).where(model.warehouse_id == warehouse_id)
        ).scalar_one())
    return counts


def has_any_structure(db: Session, warehouse_id: str) -> bool:
    """¿Existe algún nodo o alguna ubicación en este almacén?"""
    if any(count > 0 for count in used_levels(db, warehouse_id).values()):
        return True
    return int(db.execute(
        select(func.count()).select_from(WarehouseLocation)
        .where(WarehouseLocation.warehouse_id == warehouse_id)
    ).scalar_one()) > 0


def current_regime(db: Session, warehouse: Warehouse) -> str:
    """Régimen efectivo. Una vez `OPERATIONAL`, no vuelve atrás: el régimen
    refleja que el almacén ha existido operativamente, no cuántas filas tiene
    ahora mismo (R-008-6)."""
    if warehouse.structure_regime == REGIME_OPERATIONAL:
        return REGIME_OPERATIONAL
    return REGIME_OPERATIONAL if has_any_structure(db, warehouse.id) else REGIME_INITIAL


def promote_regime(db: Session, warehouse: Warehouse) -> None:
    """Marca el almacén como operativo. Se invoca al crear el primer nodo o la
    primera ubicación. Es un viaje de ida."""
    if warehouse.structure_regime != REGIME_OPERATIONAL:
        warehouse.structure_regime = REGIME_OPERATIONAL
        db.flush()


def validate_structure_levels_change(
    db: Session, warehouse: Warehouse, new_levels: dict[str, Any]
) -> dict[str, bool]:
    """Aplica el régimen de mutabilidad (Control 2).

    En `INITIAL` el cambio es libre. En `OPERATIONAL` los tramos **utilizados**
    no se eliminan, ni se reordenan, ni se colapsan; un tramo declarado que
    nunca tuvo nodos sí puede retirarse.
    """
    target = normalize_structure_levels(new_levels)
    if current_regime(db, warehouse) == REGIME_INITIAL:
        return target

    counts = used_levels(db, warehouse.id)
    current = normalize_structure_levels(warehouse.structure_levels)

    for level in LEVEL_ORDER:
        if current[level] and not target[level] and counts[level] > 0:
            raise KontrolError(
                code="STRUCTURE_LEVEL_IN_USE",
                message=f"El tramo {level.upper()} ya tiene nodos y no puede retirarse",
                status_code=409,
                details={
                    "reason": f"El tramo {level.upper()} tiene {counts[level]} nodos en este almacén",
                    "dependencies": {"level": level.upper(), "node_count": counts[level]},
                    "allowed_actions": ["deactivate"],
                },
            )

    # Añadir profundidad con ubicaciones existentes dejaría cadenas incompletas
    # que nadie puede completar retroactivamente sin inventar datos (R-008-7).
    added = [level for level in LEVEL_ORDER if target[level] and not current[level]]
    if added:
        location_count = int(db.execute(
            select(func.count()).select_from(WarehouseLocation)
            .where(WarehouseLocation.warehouse_id == warehouse.id)
        ).scalar_one())
        if location_count > 0:
            raise KontrolError(
                code="STRUCTURE_DEPTH_CHANGE_FORBIDDEN",
                message="No se puede añadir profundidad a un almacén con ubicaciones",
                status_code=409,
                details={
                    "reason": f"El almacén ya tiene {location_count} ubicaciones sin ese tramo",
                    "dependencies": {"added_levels": [lv.upper() for lv in added],
                                     "location_count": location_count},
                    "allowed_actions": [],
                },
            )
    return target


# --------------------------------------------------------------------------
# Coherencia de cadena
# --------------------------------------------------------------------------

def _load_node(db: Session, level: str, node_id: str) -> Any:
    node = db.get(LEVEL_MODEL[level], node_id)
    if node is None:
        raise NotFoundError(code=f"{level.upper()}_NOT_FOUND", message=f"{level.capitalize()} no encontrado")
    return node


def validate_chain(
    db: Session, warehouse: Warehouse, chain: dict[str, str | None]
) -> dict[str, str | None]:
    """Valida una cadena `{zone,aisle,rack,level}` contra el almacén.

    Comprueba tres cosas distintas que suelen confundirse:

    1. Que cada tramo referido esté **declarado** por el almacén.
    2. Que cada nodo pertenezca a **este** almacén.
    3. Que cada nodo sea descendiente real del anterior — un rack de otro
       pasillo es incoherente aunque ambos existan en el almacén (R-008-2).
    """
    declared = declared_levels(warehouse)
    resolved: dict[str, str | None] = {level: None for level in LEVEL_ORDER}

    for level in LEVEL_ORDER:
        node_id = chain.get(level)
        if node_id is None:
            continue
        if level not in declared:
            raise KontrolError(
                code="STRUCTURE_LEVEL_DISABLED",
                message=f"El almacén no declara el tramo {level.upper()}",
                status_code=422,
                details={"level": level.upper(), "declared": declared},
            )
        node = _load_node(db, level, node_id)
        if node.warehouse_id != warehouse.id:
            raise KontrolError(
                code="HIERARCHY_CROSS_WAREHOUSE",
                message=f"El {level} pertenece a otro almacén",
                status_code=422,
                details={"level": level.upper()},
            )
        parent_fk = LEVEL_PARENT_FK[level]
        if parent_fk is not None:
            parent_level = LEVEL_ORDER[LEVEL_ORDER.index(level) - 1]
            expected_parent = resolved.get(parent_level)
            actual_parent = getattr(node, parent_fk)
            # Solo se exige el vínculo cuando el almacén declara el tramo padre.
            if parent_level in declared and actual_parent != expected_parent:
                raise KontrolError(
                    code="HIERARCHY_INCOHERENT",
                    message=f"El {level} no pertenece al {parent_level} indicado",
                    status_code=422,
                    details={"level": level.upper(), "parent_level": parent_level.upper(),
                             "expected_parent": expected_parent, "actual_parent": actual_parent},
                )
        resolved[level] = node.id
    return resolved


def ancestors_of(db: Session, level: str, node_id: str) -> dict[str, str | None]:
    """Cadena ascendente completa de un nodo, resuelta desde el propio nodo.

    Necesaria porque una cadena parcial no puede interpretar los tramos
    ausentes como «sin padre»: hay que mirar el nodo, no la petición.
    """
    chain: dict[str, str | None] = {lv: None for lv in LEVEL_ORDER}
    current_level, current_id = level, node_id
    while current_id is not None:
        chain[current_level] = current_id
        parent_fk = LEVEL_PARENT_FK[current_level]
        if parent_fk is None:
            break
        node = db.get(LEVEL_MODEL[current_level], current_id)
        if node is None:
            break
        current_id = getattr(node, parent_fk)
        current_level = LEVEL_ORDER[LEVEL_ORDER.index(current_level) - 1]
    return chain


def validate_node_parent(
    db: Session, warehouse: Warehouse, level: str, parent_id: str | None
) -> str | None:
    """Valida el padre inmediato al crear o editar un nodo intermedio."""
    parent_fk = LEVEL_PARENT_FK[level]
    if parent_fk is None or parent_id is None:
        return None
    parent_level = LEVEL_ORDER[LEVEL_ORDER.index(level) - 1]
    # Se valida la cadena **completa** del padre, no solo el padre suelto: así
    # un pasillo que cuelga de una zona de otro almacén se detecta igual.
    resolved = validate_chain(db, warehouse, ancestors_of(db, parent_level, parent_id))
    return resolved[parent_level]


# --------------------------------------------------------------------------
# Etiqueta derivada y orden físico
# --------------------------------------------------------------------------

def display_path(db: Session, location: WarehouseLocation) -> str:
    """Etiqueta legible **derivada**, nunca persistida.

    Renombrar una zona cambia la etiqueta de todas sus ubicaciones sin tocar
    ninguna fila de ubicación, que es exactamente lo que se busca (CL-008-07).
    """
    parts: list[str] = []
    warehouse = db.get(Warehouse, location.warehouse_id)
    if warehouse is not None:
        parts.append(warehouse.code)
    for level in LEVEL_ORDER:
        node_id = getattr(location, LEVEL_FK[level])
        if node_id is None:
            continue
        node = db.get(LEVEL_MODEL[level], node_id)
        if node is not None:
            parts.append(node.name or node.code)
    parts.append(location.code)
    return " / ".join(parts)


def physical_order_query(warehouse_id: str):
    """Consulta ordenada físicamente, total y determinista.

    El orden es `zona, pasillo, rack, nivel, ubicación, código` con los nulos
    primero. El desempate final por `code` es lo que lo hace **total**: sin él,
    dos ubicaciones con la misma secuencia podrían alternar entre llamadas
    (FR-008-033).
    """
    zone = WarehouseZone
    aisle = WarehouseAisle
    rack = WarehouseRack
    level = WarehouseLevel
    return (
        select(WarehouseLocation, zone.sequence, aisle.sequence, rack.sequence, level.sequence)
        .outerjoin(zone, WarehouseLocation.zone_id == zone.id)
        .outerjoin(aisle, WarehouseLocation.aisle_id == aisle.id)
        .outerjoin(rack, WarehouseLocation.rack_id == rack.id)
        .outerjoin(level, WarehouseLocation.level_id == level.id)
        .where(WarehouseLocation.warehouse_id == warehouse_id)
        .order_by(
            zone.sequence.nulls_first(),
            aisle.sequence.nulls_first(),
            rack.sequence.nulls_first(),
            level.sequence.nulls_first(),
            WarehouseLocation.sequence,
            WarehouseLocation.code,
        )
    )


# --------------------------------------------------------------------------
# Histórico, borrado y desactivación
# --------------------------------------------------------------------------

def _location_ids_under(db: Session, level: str, node_id: str) -> list[str]:
    """Ubicaciones que cuelgan de un nodo, directa o indirectamente."""
    column = getattr(WarehouseLocation, LEVEL_FK[level])
    return list(db.execute(
        select(WarehouseLocation.id).where(column == node_id)
    ).scalars().all())


def location_history(db: Session, location_id: str) -> dict[str, int]:
    """Rastro transaccional de una ubicación.

    Se consulta de forma perezosa para no acoplar `organization` al esquema de
    `inventory` en tiempo de importación.
    """
    from app.modules.inventory.models import InventoryBalance, InventoryMovement, StockCountLine

    def count(model: Any) -> int:
        return int(db.execute(
            select(func.count()).select_from(model).where(model.location_id == location_id)
        ).scalar_one())

    history = {
        "movements": count(InventoryMovement),
        "balances": count(InventoryBalance),
        "count_lines": count(StockCountLine),
    }
    try:
        from app.modules.inventory.models import Reservation

        history["reservations"] = int(db.execute(
            select(func.count()).select_from(Reservation)
            .where(Reservation.location_id == location_id)
        ).scalar_one())
    except (ImportError, AttributeError):
        # El modelo de reservas no expone ubicación en esta versión del
        # esquema; no se inventa el dato.
        pass
    return {key: value for key, value in history.items() if value > 0}


def node_children(db: Session, level: str, node_id: str) -> dict[str, int]:
    """Descendientes directos de un nodo intermedio, por tramo."""
    children: dict[str, int] = {}
    index = LEVEL_ORDER.index(level)
    if index + 1 < len(LEVEL_ORDER):
        child_level = LEVEL_ORDER[index + 1]
        child_model = LEVEL_MODEL[child_level]
        child_fk = LEVEL_PARENT_FK[child_level]
        total = int(db.execute(
            select(func.count()).select_from(child_model)
            .where(getattr(child_model, child_fk) == node_id)
        ).scalar_one())
        if total:
            children[child_level] = total
    locations = len(_location_ids_under(db, level, node_id))
    if locations:
        children["locations"] = locations
    return children


def node_active_children(db: Session, level: str, node_id: str) -> dict[str, int]:
    """Descendientes **activos**. Es lo que impide desactivar sin cascada."""
    active: dict[str, int] = {}
    index = LEVEL_ORDER.index(level)
    if index + 1 < len(LEVEL_ORDER):
        child_level = LEVEL_ORDER[index + 1]
        child_model = LEVEL_MODEL[child_level]
        child_fk = LEVEL_PARENT_FK[child_level]
        total = int(db.execute(
            select(func.count()).select_from(child_model)
            .where(getattr(child_model, child_fk) == node_id, child_model.status == "ACTIVE")
        ).scalar_one())
        if total:
            active[child_level] = total
    column = getattr(WarehouseLocation, LEVEL_FK[level])
    locations = int(db.execute(
        select(func.count()).select_from(WarehouseLocation)
        .where(column == node_id, WarehouseLocation.status == "ACTIVE")
    ).scalar_one())
    if locations:
        active["locations"] = locations
    return active


def node_inherited_history(db: Session, level: str, node_id: str) -> dict[str, Any]:
    """Histórico **heredado**: el de cualquier ubicación que cuelgue del nodo.

    Una zona sin stock propio cuya ubicación tiene movimientos tampoco puede
    borrarse. El histórico se hereda hacia arriba (Control 2 §5).
    """
    for location_id in _location_ids_under(db, level, node_id):
        history = location_history(db, location_id)
        if history:
            return {"location_id": location_id, **history}
    return {}


def warehouse_history(db: Session, warehouse_id: str) -> dict[str, Any]:
    from app.modules.inventory.models import InventoryMovement

    movements = int(db.execute(
        select(func.count()).select_from(InventoryMovement)
        .where(InventoryMovement.warehouse_id == warehouse_id)
    ).scalar_one())
    return {"movements": movements} if movements else {}


def warehouses_dependencies(db: Session, warehouse_ids: list[str]) -> dict[str, dict[str, int]]:
    """Lo que impide borrar cada almacén, para una página entera de una vez.

    `can_delete_warehouse` y `current_regime` lo preguntan almacén por almacén:
    los cuatro tramos, las ubicaciones y los movimientos. En un listado eso son
    seis consultas por fila —y el doble, porque `warehouse_allowed_actions` las
    repite—; aquí es una por tabla, agrupada. Por cada almacén se devuelve el
    mismo diccionario que `can_delete_warehouse` arma en `dependencies`: solo lo
    que tiene algo, y en el mismo orden.
    """
    from app.modules.inventory.models import InventoryMovement

    dependencies: dict[str, dict[str, int]] = {warehouse_id: {} for warehouse_id in warehouse_ids}
    if not dependencies:
        return dependencies
    sources: list[tuple[str, Any]] = [
        *LEVEL_MODEL.items(), ("locations", WarehouseLocation), ("movements", InventoryMovement),
    ]
    for key, model in sources:
        rows = db.execute(
            select(model.warehouse_id, func.count())
            .where(model.warehouse_id.in_(list(dependencies)))
            .group_by(model.warehouse_id)
        ).all()
        for warehouse_id, total in rows:
            dependencies[warehouse_id][key] = int(total)
    return dependencies


def warehouse_view(
    warehouse: Warehouse, dependencies: dict[str, int], permissions: set[str] | None = None
) -> dict[str, Any]:
    """Lo que el listado dice de un almacén, a partir de sus dependencias ya contadas.

    Son las reglas de `can_delete_warehouse`, `current_regime` y
    `warehouse_allowed_actions`, sin volver a la base: no se borra lo que tiene
    algo debajo; el régimen es operativo si se guardó así o si hay algún nodo o
    ubicación —los movimientos no cuentan como estructura—; y las acciones se
    recortan a las que este usuario puede ejecutar.
    """
    has_structure = any(key != "movements" for key in dependencies)
    operational = warehouse.structure_regime == REGIME_OPERATIONAL or has_structure
    regime = REGIME_OPERATIONAL if operational else REGIME_INITIAL
    can_delete = not dependencies
    actions = ["edit", "deactivate" if warehouse.status == "ACTIVE" else "activate"]
    if regime == REGIME_INITIAL:
        actions.append("manage_structure")
    actions.extend(f"add_{level}" for level in declared_levels(warehouse))
    actions.append("add_location")
    if can_delete:
        actions.append("delete")
    return {
        "can_delete": can_delete,
        "delete_blocked_by": dict(dependencies) if dependencies else None,
        "structure_regime": regime,
        "allowed_actions": _filter_by_permission(actions, permissions),
    }


def can_delete_location(db: Session, location: WarehouseLocation) -> tuple[bool, dict[str, Any]]:
    history = location_history(db, location.id)
    return (not history), history


def can_delete_node(db: Session, level: str, node_id: str) -> tuple[bool, dict[str, Any]]:
    children = node_children(db, level, node_id)
    if children:
        return False, {"children": children}
    inherited = node_inherited_history(db, level, node_id)
    if inherited:
        return False, {"history": inherited}
    return True, {}


def can_delete_warehouse(db: Session, warehouse: Warehouse) -> tuple[bool, dict[str, Any]]:
    counts = used_levels(db, warehouse.id)
    blocking = {level: total for level, total in counts.items() if total}
    locations = int(db.execute(
        select(func.count()).select_from(WarehouseLocation)
        .where(WarehouseLocation.warehouse_id == warehouse.id)
    ).scalar_one())
    if locations:
        blocking["locations"] = locations
    history = warehouse_history(db, warehouse.id)
    if history:
        blocking.update(history)
    return (not blocking), ({"dependencies": blocking} if blocking else {})


def assert_can_deactivate_node(db: Session, level: str, node_id: str) -> None:
    """Sin desactivación en cascada silenciosa: se enumera lo que lo impide y
    decide una persona (R-008-9)."""
    active = node_active_children(db, level, node_id)
    if active:
        raise KontrolError(
            code="NODE_HAS_ACTIVE_CHILDREN",
            message="El nodo tiene descendientes activos",
            status_code=409,
            details={
                "reason": "Debe desactivar antes los descendientes activos",
                "dependencies": active,
                "allowed_actions": [],
            },
        )


def assert_can_relocate(db: Session, location: WarehouseLocation) -> None:
    """Mover mercancía es un movimiento, no una edición de maestro. Cambiar el
    padre de una ubicación con historial reescribiría el Kardex (FR-008-056)."""
    history = location_history(db, location.id)
    if history:
        raise ConflictError(
            code="LOCATION_HAS_HISTORY",
            message="La ubicación tiene historial y no puede cambiar de jerarquía",
        )


# --------------------------------------------------------------------------
# Códigos
# --------------------------------------------------------------------------

def generate_location_code(
    db: Session, warehouse: Warehouse, chain: dict[str, str | None]
) -> str:
    """Genera un código a partir del patrón declarado por el almacén.

    El patrón es **dato del almacén**, no una convención codificada: admite los
    marcadores `{warehouse}`, `{zone}`, `{aisle}`, `{rack}`, `{level}` y
    `{seq}`. Sin patrón, se usa un correlativo simple.
    """
    tokens: dict[str, str] = {"warehouse": warehouse.code}
    for level in LEVEL_ORDER:
        node_id = chain.get(level)
        node = db.get(LEVEL_MODEL[level], node_id) if node_id else None
        tokens[level] = node.code if node is not None else ""

    used = int(db.execute(
        select(func.count()).select_from(WarehouseLocation)
        .where(WarehouseLocation.warehouse_id == warehouse.id)
    ).scalar_one())

    pattern = warehouse.code_pattern or "{warehouse}-{seq}"
    for offset in range(1, 10_000):
        tokens["seq"] = f"{used + offset:04d}"
        candidate = pattern.format(**tokens).replace("--", "-").strip("-")
        exists = db.execute(
            select(WarehouseLocation.id).where(
                WarehouseLocation.warehouse_id == warehouse.id,
                WarehouseLocation.code == candidate,
            )
        ).first()
        if exists is None:
            return candidate
    raise ConflictError(code="LOCATION_CODE_EXHAUSTED",
                        message="No se pudo generar un código libre con el patrón del almacén")


# --------------------------------------------------------------------------
# allowed_actions — el backend es la autoridad (P6, FR-008-093)
# --------------------------------------------------------------------------

def _filter_by_permission(actions: list[str], permissions: set[str] | None) -> list[str]:
    """Recorta las acciones a las que el usuario realmente puede ejecutar.

    Sin permisos declarados la lista queda vacía: `allowed_actions` describe lo
    que **este** usuario puede hacer, no lo que la entidad admite en abstracto.
    """
    if permissions is None:
        return actions
    required = {
        "edit": "organization:edit",
        "activate": "organization:activate",
        "deactivate": "organization:deactivate",
        "block": "organization:edit",
        "delete": "organization:delete",
        "manage_structure": "organization:manage_structure",
        "add_zone": "organization:create",
        "add_aisle": "organization:create",
        "add_rack": "organization:create",
        "add_level": "organization:create",
        "add_location": "organization:create",
    }
    return [action for action in actions if required.get(action, "organization:view") in permissions]


def warehouse_allowed_actions(
    db: Session, warehouse: Warehouse, permissions: set[str] | None = None
) -> list[str]:
    actions = ["edit"]
    actions.append("deactivate" if warehouse.status == "ACTIVE" else "activate")
    if current_regime(db, warehouse) == REGIME_INITIAL:
        actions.append("manage_structure")
    for level in declared_levels(warehouse):
        actions.append(f"add_{level}")
    actions.append("add_location")
    deletable, _ = can_delete_warehouse(db, warehouse)
    if deletable:
        actions.append("delete")
    return _filter_by_permission(actions, permissions)


def node_allowed_actions(
    db: Session, level: str, node: Any, permissions: set[str] | None = None
) -> list[str]:
    actions = ["edit"]
    if node.status == "ACTIVE":
        if not node_active_children(db, level, node.id):
            actions.append("deactivate")
    else:
        actions.append("activate")
    deletable, _ = can_delete_node(db, level, node.id)
    if deletable:
        actions.append("delete")
    return _filter_by_permission(actions, permissions)


def location_allowed_actions(
    db: Session, location: WarehouseLocation, permissions: set[str] | None = None
) -> list[str]:
    actions = ["edit"]
    if location.status == "ACTIVE":
        actions.extend(["deactivate", "block"])
    else:
        actions.append("activate")
    deletable, _ = can_delete_location(db, location)
    if deletable:
        actions.append("delete")
    return _filter_by_permission(actions, permissions)


def user_permission_set(db: Session, user: Any) -> set[str]:
    """Permisos efectivos del usuario, como `recurso:acción`."""
    from app.modules.identity_access import service as identity_service

    return set(identity_service.get_user_permissions(db, user))
