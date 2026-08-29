# MODELO DE DATOS — SPEC 008

8 entidades: 6 de jerarquía y 2 catálogos. Todas con `company_id` y filtro de
alcance (ADR-011, P11). Importes y medidas en `Numeric`; fechas con timezone (P21).
Ningún valor de negocio en el esquema (P8).

---

## Catálogos por empresa

### `zone_types`

Tipo **conceptual** de zona, distinto de su nombre (FR-008-012).

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | |
| `company_id` | FK companies | |
| `code` | String(32) | `RECEIVING`, `QUARANTINE`, `HIGH_ROTATION`… lo elige la empresa |
| `name` | String(120) | |
| `description` | Text? | |
| `status` | String(32) | `ACTIVE` / `INACTIVE` |

`UNIQUE (company_id, code)`. **Se crea vacío**: KONTROL no entrega tipos.

### `location_types`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | |
| `company_id` | FK companies | |
| `code` | String(32) | `STORAGE`, `RECEIVING`, `QUARANTINE`, `DISPATCH`, `DAMAGE`, `RETURN`, `INTERNAL_TRANSIT` |
| `name` | String(120) | |
| `is_storable` | Boolean | Si admite existencia disponible para venta |
| `status` | String(32) | |

`UNIQUE (company_id, code)`. Resuelve las ubicaciones especiales del §12 del
encargo **sin duplicar el concepto en la zona** (CL-008-04).

---

## Jerarquía

### `warehouses` — extensión de la tabla existente

| Campo | Estado | Notas |
|---|---|---|
| `id`, `company_id`, `branch_id?`, `code`, `name`, `warehouse_type`, `policies`, `status` | **Existen** | Se conservan |
| `address` | **Nuevo** `Text?` | |
| `manager_id` | **Nuevo** `String(36)?` | Responsable, opcional |
| `description` | **Nuevo** `Text?` | |
| `location_managed` | **Nuevo** `Boolean` def. `false` | `ADR-D0-004` R-D0-04-3 |
| `structure_levels` | **Nuevo** `JSON` | Qué tramos usa: `{"zone":true,"aisle":true,"rack":false,"level":false}`. **No es configuración libremente editable**: su régimen de cambio lo fija `structure-mutability-policy.md` |
| `structure_regime` | **Nuevo** `String(16)` def. `INITIAL` | `INITIAL` mientras no exista ningún nodo ni ubicación; pasa a `OPERATIONAL` con el primero y **no vuelve atrás** (R-008-6) |
| `code_policy` | **Nuevo** `String(16)` def. `GENERATED` | `MANUAL` / `GENERATED` |
| `code_pattern` | **Nuevo** `String(120)?` | Patrón de generación |

**Nuevo:** `UNIQUE (company_id, code)` (FR-008-002).
**Retirado:** `cascade="all, delete-orphan"` de `locations` (FR-008-007).
`branch_id` nulo = **almacén central** de la empresa (FR-008-003).

### `warehouse_zones`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | |
| `company_id` | FK companies | Redundante y deliberado: permite `UNIQUE` y filtro sin join |
| `warehouse_id` | FK warehouses | |
| `zone_type_id` | FK zone_types? | Opcional |
| `code` | String(64) | |
| `name` | String(200) | |
| `sequence` | Integer def. 0 | Orden físico de recorrido |
| `status` | String(32) | `ACTIVE`/`INACTIVE`/`BLOCKED`/`MAINTENANCE` |
| `description` | Text? | |

`UNIQUE (warehouse_id, code)`.

### `warehouse_aisles`

| Campo | Tipo | Notas |
|---|---|---|
| `id`, `company_id`, `warehouse_id` | | |
| `zone_id` | FK warehouse_zones? | **Opcional**: un almacén con pasillos y sin zonas es válido |
| `code`, `name`, `sequence`, `status` | | |

`UNIQUE (warehouse_id, code)`.

### `warehouse_racks`

| Campo | Tipo | Notas |
|---|---|---|
| `id`, `company_id`, `warehouse_id` | | |
| `aisle_id` | FK warehouse_aisles? | Opcional |
| `code`, `name`, `sequence`, `status` | | |

`UNIQUE (warehouse_id, code)`.

### `warehouse_levels`

| Campo | Tipo | Notas |
|---|---|---|
| `id`, `company_id`, `warehouse_id` | | |
| `rack_id` | FK warehouse_racks? | Opcional |
| `code`, `name`, `sequence`, `status` | | |
| `height_order` | Integer? | Orden vertical, distinto de la secuencia de recorrido |

`UNIQUE (warehouse_id, code)`.

### `warehouse_locations` — sustituye a `locations`

La hoja. Es lo que las transacciones referencian.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | **Se conserva el de `locations`**: las FK existentes siguen válidas |
| `company_id` | FK companies | |
| `warehouse_id` | FK warehouses | **Obligatorio** |
| `zone_id`, `aisle_id`, `rack_id`, `level_id` | FK? | **Cadena completa** (CL-008-02); todos opcionales |
| `location_type_id` | FK location_types? | |
| `code` | String(64) | Identificador humano |
| `name` | String(200)? | |
| `sequence` | Integer def. 0 | Desempate final del orden físico |
| `status` | String(32) | |
| `capacity_units` | Numeric(18,3)? | MVP (CL-008-12) |
| `capacity_weight` | Numeric(18,3)? | MVP |
| `capacity_uom` | String(16)? | Unidad declarada de la capacidad |
| `restrictions` | JSON? | MVP: producto o categoría permitidos (CL-008-13) |
| `barcode` | String(120)? | Reservado; sin impresión en 008 (FR-008-028) |
| `legacy_path` | String(200)? | Texto original de `zone`/`aisle`/`rack` (CL-008-15) |
| `created_by`, `created_at`, `updated_at` | | |
| `version` | Integer def. 1 | Control optimista `If-Match` |

**Restricciones:**

- `UNIQUE (warehouse_id, code)` (FR-008-021)
- `CHECK`: si `rack_id` no es nulo → `aisle_id` no es nulo cuando el almacén declara pasillos; si `level_id` no es nulo → `rack_id` no es nulo. Verificación completa de la cadena en servicio (R-008-2)
- Coherencia de almacén entre todos los tramos: impuesta por FK compuestas `(warehouse_id, id)` donde el dialecto lo permita, y validada en servicio

**Campos retirados:** `zone`, `aisle`, `rack` como texto libre → su contenido pasa
a `legacy_path`.

**Etiqueta legible:** **no es una columna.** Se deriva en lectura de la cadena
declarada (CL-008-07).

---

## Referencias que pasan a FK real (FR-008-054)

| Tabla | Columna | Antes | Después |
|---|---|---|---|
| `inventory_movements` | `location_id` | FK ✔ | Sin cambio; solo se reapunta al nombre nuevo de la tabla |
| `inventory_balances` | `location_id` | `String(36)` | **FK → warehouse_locations** |
| `stock_count_lines` | `location_id` | `String(36)` | **FK → warehouse_locations** |

**Verificado contra la base real:** estas son las **únicas** tres tablas del esquema
con columna `location_id`. `inventory_adjustments` **no** tiene ninguna, y no existe
`adjustment_lines`. Se convierten por tanto **dos** columnas, no tres.

Ambas tablas convertidas reciben además:

| Campo | Tipo | Propósito |
|---|---|---|
| `legacy_location_id` | `String(36)?` | Valor original de `location_id` cuando `0018` lo repara o lo anula. **Nunca se pierde el rastro** (FR-008-101) |

### Reporte de migración

`0018` persiste su reporte con la cabecera y el detalle definidos en
`migration-0018-policy.md` §5. Solo identificadores técnicos y justificación: sin
nombres de producto, cantidades, importes ni datos de tercero.

---

## Índices — cada uno con su consulta justificante

| Índice | Justifica |
|---|---|
| `warehouses (company_id, status)` | Lista de almacenes por empresa |
| `warehouses (company_id, code)` UNIQUE | FR-008-002 |
| `warehouse_zones (warehouse_id, sequence)` | Recorrido físico y listado por almacén |
| `warehouse_aisles (warehouse_id, sequence)` · `(zone_id)` | Recorrido y navegación por zona |
| `warehouse_racks (warehouse_id, sequence)` · `(aisle_id)` | Ídem |
| `warehouse_levels (warehouse_id, sequence)` · `(rack_id)` | Ídem |
| `warehouse_locations (warehouse_id, code)` UNIQUE | FR-008-021 |
| `warehouse_locations (warehouse_id, status)` | Ubicaciones válidas para 022 |
| `warehouse_locations (warehouse_id, zone_id, aisle_id, rack_id, level_id, sequence)` | **Consulta ordenada físicamente** (FR-008-032) — el índice compuesto evita ordenar en memoria con 50.000 filas (NFR-008-03) |
| `warehouse_locations (company_id, code)` | Búsqueda global por código |
| `warehouse_locations (location_type_id)` | Ubicaciones especiales para 022/036 |

Se rechazan índices sin consulta que los justifique.

---

## Reglas de borrado y desactivación (FR-008-055, §27, §59)

| Nodo | Se puede borrar si… | Se puede desactivar si… |
|---|---|---|
| `Warehouse` | Sin estructura, sin ubicaciones y sin movimientos | Siempre; los hijos activos se advierten |
| `WarehouseZone` | Sin pasillos ni ubicaciones asociadas | Sin hijos activos |
| `WarehouseAisle` | Sin racks ni ubicaciones | Sin hijos activos |
| `WarehouseRack` | Sin niveles ni ubicaciones | Sin hijos activos |
| `WarehouseLevel` | Sin ubicaciones | Sin hijos activos |
| `WarehouseLocation` | **Sin movimientos, sin saldo y sin reservas** | Siempre |

`can_delete` y `allowed_actions` los calcula el backend (FR-008-063). La
desactivación **no** cae en cascada silenciosa (CL-008-11).

**Histórico heredado:** un nodo tiene histórico si lo tiene él **o cualquiera de sus
descendientes**. Una zona sin stock propio pero con una ubicación con movimientos
**no** puede borrarse. La política completa por entidad está en
`structure-mutability-policy.md` §5.

**Sin `cascade` destructivo** en ninguna relación de la jerarquía: el
`cascade="all, delete-orphan"` de `Warehouse.locations` se retira en F1 (R-008-8).

## Reubicación estructural (FR-008-056)

Cambiar `zone_id`, `aisle_id`, `rack_id` o `level_id` de una ubicación:

- **con** saldo, movimientos o reservas → **rechazado** con `LOCATION_HAS_HISTORY`
- **sin** historial → permitido, auditado como cambio de jerarquía

El traslado físico de mercancía es un movimiento de inventario (Specs 023/025),
no una edición de metadatos (CL-008-09).

## Compatibilidad con StockLedger (Spec 023)

008 **no** implementa saldos. Fija el contrato:

- `location_id` es dimensión de `InventoryMovement` e `InventoryBalance`, con FK real
- La proyección de saldo es `(company, warehouse, location?, product, lot?, serial?)`
- La ocupación y el estado `FULL` se **derivan** del saldo; 008 no los persiste
- Si en el futuro se exigiera reconstruir la jerarquía histórica exacta de un
  movimiento, será un snapshot en la Spec 023 (research §6), no una columna de 008
