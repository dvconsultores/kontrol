# CONTRATOS DE API — SPEC 008

Prefijo `/api/v1/organization`, siguiendo la convención vigente del módulo.
Todo endpoint exige sesión, permiso y filtra por empresa activa (P11).

## Catálogos

| Método | Ruta | Permiso |
|---|---|---|
| `GET` · `POST` | `/zone-types` | `organization:view` · `organization:create` |
| `PATCH` | `/zone-types/{id}` | `organization:edit` |
| `GET` · `POST` | `/location-types` | `organization:view` · `organization:create` |
| `PATCH` | `/location-types/{id}` | `organization:edit` |

Ambos catálogos se crean **vacíos**: KONTROL no entrega tipos predefinidos.

## Almacenes

| Método | Ruta | Permiso | Notas |
|---|---|---|---|
| `GET` | `/warehouses` | `view` | Filtros: `q`, `branch_id`, `status`; paginado |
| `POST` | `/warehouses` | `create` | |
| `GET` | `/warehouses/{id}` | `view` | Incluye `structure_levels` y `allowed_actions` |
| `PATCH` | `/warehouses/{id}` | `edit` | `If-Match` → 409 |
| `POST` | `/warehouses/{id}/activate` · `/deactivate` | `activate` · `deactivate` | |
| `DELETE` | `/warehouses/{id}` | `delete` | Solo si `can_delete` |

## Estructura (§53)

| Método | Ruta | Permiso |
|---|---|---|
| `GET` | `/warehouses/{id}/structure` | `view` |

Parámetros: `depth` ∈ `zone` · `aisle` · `rack` · `level` · `locations` (por
defecto `level`), `limit`, `offset`, `status`.

> Las ubicaciones **solo** se incluyen con `depth=locations` y siempre paginadas.
> Un almacén con 50.000 ubicaciones nunca devuelve su árbol completo (NFR-008-02).

Respuesta:

```json
{
  "warehouse": { "id": "…", "code": "ALM-01", "structure_levels": {"zone": true, "aisle": true, "rack": false, "level": false} },
  "zones": [
    { "id": "…", "code": "ZA", "name": "Alta rotación", "type": {"code": "HIGH_ROTATION"}, "sequence": 1,
      "aisles": [ { "id": "…", "code": "P03", "sequence": 3, "racks": [] } ] }
  ],
  "locations": { "total": 1240, "items": [ … ], "limit": 50, "offset": 0 },
  "allowed_actions": ["edit", "deactivate", "add_zone"]
}
```

## Nodos intermedios

Mismo juego para `zones`, `aisles`, `racks` y `levels`:

| Método | Ruta |
|---|---|
| `GET` | `/warehouses/{id}/zones` (filtros y orden por `sequence`) |
| `POST` | `/warehouses/{id}/zones` |
| `GET` · `PATCH` | `/zones/{id}` |
| `POST` | `/zones/{id}/activate` · `/deactivate` |
| `DELETE` | `/zones/{id}` |

Análogo en `/aisles`, `/racks`, `/levels`. Cada uno acepta su padre opcional y
valida la coherencia de cadena.

## Ubicaciones

| Método | Ruta | Permiso | Notas |
|---|---|---|---|
| `GET` | `/locations` | `view` | Búsqueda: `warehouse_id`, `q`, `zone_id`, `aisle_id`, `rack_id`, `level_id`, `type`, `status`; paginado |
| `GET` | `/locations/ordered` | `view` | **Orden físico** para 031 |
| `POST` | `/locations` | `create` | |
| `POST` | `/locations/bulk` | `create` | Creación por patrón (FR-008-029) |
| `GET` | `/locations/{id}` | `view` | Con cadena, etiqueta derivada y `allowed_actions` |
| `PATCH` | `/locations/{id}` | `edit` | `If-Match`; cambiar el padre con historial → 409 |
| `POST` | `/locations/{id}/activate` · `/deactivate` · `/block` | `edit` | |
| `DELETE` | `/locations/{id}` | `delete` | Solo si `can_delete` |

### `GET /locations/{id}`

```json
{
  "id": "…", "code": "A-0345", "name": "Posición 5",
  "warehouse": { "id": "…", "code": "ALM-01" },
  "zone": { "id": "…", "code": "ZA", "name": "Alta rotación" },
  "aisle": { "id": "…", "code": "P03" },
  "rack": null, "level": null,
  "type": { "code": "STORAGE", "is_storable": true },
  "display_path": "ALM-01 / Alta rotación / P03 / A-0345",
  "sequence": 5, "status": "ACTIVE", "version": 3,
  "capacity": { "units": 120, "weight": 500.0, "uom": "KG" },
  "can_delete": false,
  "allowed_actions": ["edit", "deactivate", "block"]
}
```

`display_path` es **derivado**, no una columna (CL-008-07). `can_delete` es
`false` porque la ubicación tiene movimientos.

### `GET /locations/ordered` — contrato para la Spec 031

Parámetros: `warehouse_id` (obligatorio), `status`, `type`, `limit`, `offset`.

Orden: `zone.sequence, aisle.sequence, rack.sequence, level.sequence,
location.sequence, location.code` con `NULLS FIRST`. **Total, estable y
determinista** (FR-008-033).

```json
{ "total": 1240,
  "items": [ { "id": "…", "code": "A-0001", "display_path": "…",
               "physical_order": [1, 1, null, null, 1] } ] }
```

`physical_order` expone las secuencias que producen el orden, para que 031 pueda
agrupar por tramo sin recalcular.

## Códigos de error

| Código | HTTP | Cuándo |
|---|---|---|
| `WAREHOUSE_CODE_DUPLICATE` | 409 | Código repetido en la empresa |
| `LOCATION_CODE_DUPLICATE` | 409 | Código repetido en el almacén |
| `HIERARCHY_INCOHERENT` | 422 | La cadena declarada no encaja (R-008-2) |
| `HIERARCHY_CROSS_WAREHOUSE` | 422 | Un tramo pertenece a otro almacén |
| `CROSS_COMPANY_REFERENCE` | 403 | Referencia a otra empresa |
| `LOCATION_HAS_HISTORY` | 409 | Borrado o reubicación con movimientos, saldo o reservas |
| `NODE_HAS_ACTIVE_CHILDREN` | 409 | Desactivar un padre con hijos activos |
| `WAREHOUSE_NOT_LOCATION_MANAGED` | 422 | Operación de ubicación en almacén que no las gestiona |
| `STRUCTURE_LEVEL_DISABLED` | 422 | Usar un tramo que el almacén no declara |
| `VERSION_CONFLICT` | 409 | `If-Match` obsoleto |
| `STRUCTURE_LEVEL_IN_USE` | 409 | Eliminar un tramo que ya tiene nodos (R-008-6) |
| `STRUCTURE_REORDER_FORBIDDEN` | 409 | Reordenar o resemantizar tramos utilizados |
| `STRUCTURE_DEPTH_CHANGE_FORBIDDEN` | 409 | Añadir profundidad con ubicaciones existentes |
| `NODE_HAS_HISTORY` | 409 | Borrado físico de un nodo con histórico propio o heredado |

### Forma de las respuestas de bloqueo estructural

Todo rechazo de los cuatro códigos estructurales devuelve, además del `code`:

```
{
  "code": "STRUCTURE_LEVEL_IN_USE",
  "message": "...",
  "reason": "El tramo RACK tiene 42 nodos en este almacén",
  "dependencies": {
    "level": "RACK",
    "node_count": 42,
    "sample": ["rack-001", "rack-002", "rack-003"]
  },
  "allowed_actions": ["deactivate"]
}
```

`dependencies` enumera lo que concretamente impide la operación, acotado a una
muestra. `allowed_actions` dice qué **sí** puede hacerse en su lugar. El frontend
**refleja** este bloqueo; no lo produce: invocar el endpoint directamente obtiene
el mismo rechazo (FR-008-093, AC-008-39).

## `allowed_actions`

Calculado en backend para cada nodo (FR-008-063). Un usuario sin permiso recibe
`[]`; una ubicación con historial nunca ofrece `delete`. El frontend representa;
no decide.

## Contratos declarados para Specs futuras

| Spec | Contrato |
|---|---|
| **019 / 022** | `GET /locations?warehouse_id&status=ACTIVE&type=…` devuelve destinos válidos. `GoodsReceiptLine.destination_location_id` referenciará `warehouse_locations.id` |
| **023** | `location_id` es dimensión de movimiento y saldo con FK real; la ocupación se deriva |
| **025** | `source_location_id` y `destination_location_id` sobre `warehouse_locations.id` |
| **031** | `GET /locations/ordered` |
| **032** | `PickListLine.location_id` referenciará `warehouse_locations.id` |
| **036** | Ubicaciones de devolución y cuarentena identificables por `location_type` |
| **046** | Adjuntos vinculables al almacén por `AttachmentLink`, sin cambio de modelo |

## Régimen de mutabilidad de `structure_levels`

`GET /organization/warehouses/{id}` devuelve `structure_regime` (`INITIAL` o
`OPERATIONAL`) y, en `allowed_actions`, si `structure_levels` es editable.

`PATCH /organization/warehouses/{id}/structure-levels` es el **único** camino para
cambiarlo. En régimen `OPERATIONAL` rechaza toda eliminación, reordenamiento,
resemantización o colapso de un tramo **utilizado**; permite retirar un tramo
declarado que no tenga ningún nodo.

La reestructuración —fusionar zonas, mover racks, cambiar la profundidad de un
almacén operativo— **no tiene endpoint en 008** y es deliberado: pertenece a un
proceso controlado posterior (`structure-mutability-policy.md` §6).
