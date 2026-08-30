# MODELO DE DATOS — SPEC 011

Toda cantidad y todo factor en `NUMERIC`. Ningún `Float` (FR-011-061). Fechas con
zona horaria. Ningún valor de negocio en el esquema (P8).

---

## 1. `units_of_measure` — extensión de la tabla existente

| Campo | Estado | Notas |
|---|---|---|
| `id`, `code`, `name`, `symbol`, `dimension`, `decimals`, `company_id?`, `status` | **Existen** | Se conservan |
| `rounding_mode` | **Nuevo** `String(16)` def. `HALF_UP` | `HALF_UP` · `HALF_EVEN` · `DOWN` · `UP` |
| `is_global` | **Derivado**, no columna | `company_id IS NULL` ya lo expresa |
| `version` | **Nuevo** `BigInteger` def. 1 | `If-Match` |

**Nuevo:** `UNIQUE (company_id, code)` — admite el mismo código en el ámbito
global y en el de una empresa, que son filas distintas.
**Nuevo:** `CHECK (decimals BETWEEN 0 AND 6)`.
**Nuevo:** `CHECK (dimension IN ('CANTIDAD','PESO','VOLUMEN','LONGITUD','AREA','TIEMPO'))`.

`company_id` nulo = **unidad global de plataforma**, de solo lectura para las
empresas. El catálogo global **nace vacío** (FR-011-004).

## 2. `unit_conversions` — corrección de la tabla existente

| Campo | Estado | Notas |
|---|---|---|
| `from_unit_id`, `to_unit_id` | Existen | — |
| `factor` | **`Float` → `NUMERIC(18,6)`** | Corrección de tipo (FR-011-011) |
| `rounding` | Existe | Se conserva |
| `validity` | Existe | Se conserva como estado |

**Nuevo:** `CHECK (factor > 0)`.
**Nuevo:** `UNIQUE (from_unit_id, to_unit_id)`.
**Nuevo, en servicio:** ambas unidades deben compartir `dimension` (FR-011-010).
No se impone por restricción de base de datos porque exigiría desnormalizar la
dimensión en la tabla de conversión: se valida en el motor y se prueba.

Conversión **física**: sin versionado. Un kilo siempre serán mil gramos.

## 3. `presentations` — extensión de la tabla existente

| Campo | Estado | Notas |
|---|---|---|
| `id`, `product_id`, `unit_id?`, `barcode?`, `buyable`, `sellable`, `storable` | **Existen** | Se conservan |
| `content` | **`Float`** | **Se conserva como dato legado**, no se usa para calcular. El factor autoritativo vive en la versión |
| `code` | **Nuevo** `String(32)` | Identificador legible: `CAJA`, `BOLSA` |
| `name` | Existe | — |
| `dispatchable` | **Nuevo** `Boolean` def. `true` | Distingue presentación comercial de unidad de despacho (§20) |
| `status` | **Nuevo** `String(32)` def. `ACTIVE` | Faltaba: no había forma de desactivar |
| `company_id` | **Nuevo** `String(36)` FK | Derivado del producto; permite filtrar y aislar sin join |
| `version` | **Nuevo** `BigInteger` | `If-Match` |

**Nuevo:** `UNIQUE (product_id, code)`.

> `content` se **conserva y no se borra**: si alguna instalación tuviera filas,
> ese número es la única evidencia de la intención original. Se migra a la
> primera versión de factor cuando es interpretable, y se conserva en todo caso.

## 4. `product_presentation_versions` — **nueva**

El factor y su vigencia. Es el corazón del versionado.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | |
| `presentation_id` | FK `presentations` | |
| `product_id` | FK `catalog_items` | Redundante y deliberado: permite índice y filtro sin join |
| `company_id` | FK `companies` | Aislamiento |
| `factor_to_base` | **`NUMERIC(18,6)`** | Cuántas unidades base contiene una presentación |
| `factor_uom_id` | FK `units_of_measure` | Unidad en que se expresa el factor; normalmente la base del producto |
| `exact_in_base` | `Boolean` def. `true` | `false` si la conversión produce fracciones; debe declararse (R-D0-09-5) |
| `valid_from` | `timestamptz` | |
| `valid_to` | `timestamptz?` | Nulo = versión abierta |
| `status` | `String(32)` | |
| `created_by`, `created_at`, `updated_at` | | |

**Restricciones:**

- `CHECK (factor_to_base > 0)` — FR-011-032
- `CHECK (valid_to IS NULL OR valid_to > valid_from)`
- **Índice único parcial** `(presentation_id) WHERE valid_to IS NULL` — garantiza
  **una sola versión abierta** por presentación (FR-011-035). El solapamiento
  entre rangos cerrados se valida en servicio dentro de la transacción; ver
  `research.md` §8 sobre por qué no se usa `EXCLUDE USING gist`
- `UNIQUE (presentation_id, valid_from)` — impide dos versiones con el mismo inicio

**Inmutabilidad:** una versión con `valid_to` no nulo, o referenciada por algún
snapshot, **no se edita ni se borra**. Corregir un factor crea una versión nueva
(FR-011-036).

## 5. `catalog_items` — ajuste

| Campo | Estado | Cambio |
|---|---|---|
| `base_unit_id` | Existe, *nullable* | **Obligatoria** para `item_type = 'PRODUCT'`; sigue opcional para servicios (FR-011-020, FR-011-021) |
| `billing_unit_id` | Existe | Se conserva: es la vía de los servicios |
| `base_unit_locked` | **Nuevo** `Boolean` def. `false` | Pasa a `true` con el primer movimiento; **no vuelve atrás** (R-011-3) |

`base_unit_locked` es el análogo directo de `structure_regime` en la Spec 008: un
estado que refleja que el producto ya ha existido operativamente.

Se impone con `CHECK (item_type <> 'PRODUCT' OR base_unit_id IS NOT NULL)`, y
solo **después** de que el backfill demuestre que todos los productos tienen
unidad base.

## 6. Las cuatro columnas transaccionales

Sobre cada una de las **17** tablas `MUST_HAVE_NOW`:

| Campo | Tipo | Notas |
|---|---|---|
| `uom_id` | FK `units_of_measure` | Unidad en que se expresó la cantidad |
| `presentation_id` | FK `presentations`, *nullable* | Nulo = unidad base directa |
| `conversion_factor_snapshot` | **`NUMERIC(18,6)`** | Factor congelado al emitir (R-D0-09-2) |
| `base_quantity` | **`NUMERIC(18,6)`** | Calculada al escribir y almacenada |
| `uom_source` | `String(24)` | `CAPTURED` · `LEGACY_ASSUMED_BASE` · `LEGACY_RECONSTRUCTED` · `LEGACY_UNRESOLVED` · `LEGACY_UNVERSIONED` |

En documentos **emitidos** se añaden, para reimpresión fiel (FR-011-057,
CL-011-17):

| Campo | Tipo |
|---|---|
| `uom_symbol_snapshot` | `String(16)` |
| `presentation_label_snapshot` | `String(120)` |

Solo en `sales_invoice_lines`, `supplier_invoice_lines`, `sales_return_lines` y
`shipment_lines`. En el resto sería duplicación sin valor.

**Una unidad y una presentación por línea**, no por cantidad (CL-011-14). Las
tablas con varias cantidades —`goods_receipt_lines` con tres,
`purchase_order_lines` y `transfer_lines` con dos— tienen una `base_quantity` por
cada cantidad, con nombres derivados (`base_quantity_received`,
`base_quantity_accepted`…), pero **un solo** `uom_id` y `presentation_id`.

## 7. Conversión de tipo — las 31 columnas

Todas las columnas de cantidad y factor pasan de `Float` a `NUMERIC(18,6)`, con
reporte de cualquier fila cuyo valor cambie al convertir (FR-011-063).

`inventory_balances.qty_on_hand`, `qty_reserved` y `qty_available` se convierten
igualmente **aunque la tabla sea `NOT_APPLICABLE`** para las columnas de
presentación: la corrección de tipo es independiente de la semántica de unidad.

## 8. Índices — cada uno con su consulta

| Índice | Justifica |
|---|---|
| `units_of_measure (company_id, status)` | Lista de unidades de la empresa más las globales |
| `units_of_measure (company_id, code)` UNIQUE | FR-011-005 |
| `presentations (product_id, status)` | Presentaciones de un producto en su ficha |
| `presentations (product_id, code)` UNIQUE | Unicidad legible |
| `product_presentation_versions (presentation_id, valid_from, valid_to)` | **Resolución del factor por fecha** — es la consulta del motor |
| `product_presentation_versions (presentation_id) WHERE valid_to IS NULL` UNIQUE | Una sola versión abierta |
| `product_presentation_versions (product_id, company_id)` | Resolución **masiva** por documento (NFR-011-01) |
| `<línea> (uom_id)` en las 17 tablas | Reportes por unidad y verificación de integridad |

Se rechaza cualquier índice sin consulta que lo justifique.

## 9. Borrado y desactivación

| Entidad | Se puede borrar si… | Se desactiva |
|---|---|---|
| `UnitOfMeasure` | Sin presentaciones, sin conversiones y **sin líneas que la referencien** | Siempre |
| `UnitConversion` | Nunca fue aplicada | Siempre |
| `Presentation` | Sin versiones y **sin líneas que la referencien** | Siempre |
| `ProductPresentationVersion` | Solo la versión **abierta y nunca usada** | Se cierra con `valid_to`, no se desactiva |

`can_delete` y `allowed_actions` los calcula el backend (FR-011-083). Ninguna
relación con `cascade` destructivo.

## 10. Compatibilidad con el StockLedger (Spec 023)

011 **no** implementa saldos. Fija el contrato:

- Todo movimiento se registra en `base_quantity`; la cantidad comercial se
  conserva junto a su unidad y presentación.
- `inventory_balances` es proyección en unidad base y **no** recibe presentación
  (CL-011-18, R-D0-09-3).
- La coherencia entre `base_quantity` y el número de seriales, cuando el producto
  sea serializado, la verifica la Spec 024; 011 solo declara la dependencia.
