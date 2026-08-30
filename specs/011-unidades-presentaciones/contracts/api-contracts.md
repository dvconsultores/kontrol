# CONTRATOS DE API — SPEC 011

Prefijo `/api/v1/maestros`, siguiendo la convención vigente del módulo, donde ya
viven `/maestros/catalogos/unidades`. Todo endpoint exige sesión, permiso y
filtra por empresa.

## 1. Unidades de medida

| Método | Ruta | Permiso | Notas |
|---|---|---|---|
| `GET` | `/catalogos/unidades` | `maestros:view` | Devuelve las globales **y** las de la empresa; filtros `q`, `dimension`, `status`, `scope`; paginado |
| `POST` | `/catalogos/unidades` | `maestros:create` | Crea unidad **de empresa**; el ámbito global exige autoridad de plataforma |
| `GET` | `/catalogos/unidades/{id}` | `view` | Con `allowed_actions` y `can_delete` |
| `PATCH` | `/catalogos/unidades/{id}` | `maestros:edit` | `If-Match`; una unidad global no es editable por una empresa |
| `POST` | `/catalogos/unidades/{id}/activate` · `/deactivate` | `edit` | |
| `DELETE` | `/catalogos/unidades/{id}` | `maestros:delete` | Solo si `can_delete` |

## 2. Conversión física

| Método | Ruta | Notas |
|---|---|---|
| `GET` · `POST` | `/catalogos/unidades/{id}/conversiones` | **Ya existe el `POST`**; se corrige el tipo del factor y se añade validación de dimensión |
| `DELETE` | `/catalogos/conversiones/{id}` | Solo si nunca se aplicó |

Rechaza con `UOM_DIMENSION_MISMATCH` si las unidades no comparten dimensión.

## 3. Presentaciones del producto

| Método | Ruta | Permiso |
|---|---|---|
| `GET` | `/catalogos/items/{item_id}/presentaciones` | `view` |
| `POST` | `/catalogos/items/{item_id}/presentaciones` | `create` |
| `GET` · `PATCH` | `/catalogos/presentaciones/{id}` | `view` · `edit` |
| `POST` | `/catalogos/presentaciones/{id}/activate` · `/deactivate` | `edit` |
| `DELETE` | `/catalogos/presentaciones/{id}` | `delete` — solo si `can_delete` |

## 4. Versiones del factor

| Método | Ruta | Notas |
|---|---|---|
| `GET` | `/catalogos/presentaciones/{id}/versiones` | Historial completo, más reciente primero |
| `POST` | `/catalogos/presentaciones/{id}/versiones` | **Crea versión nueva**; cierra la abierta con `valid_to`. No existe `PATCH` de versión |

> No hay endpoint para editar una versión. Es deliberado: corregir un factor
> **es** crear una versión (FR-011-036).

### Respuesta

```json
{
  "id": "…",
  "presentation": { "id": "…", "code": "CAJA", "name": "Caja" },
  "product": { "id": "…", "code": "TOR-X" },
  "factor_to_base": "100.000000",
  "factor_uom": { "id": "…", "code": "UND", "symbol": "und" },
  "exact_in_base": true,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_to": null,
  "status": "ACTIVE",
  "in_use": true,
  "allowed_actions": ["close"]
}
```

`in_use` es `true` cuando algún snapshot la referencia: entonces no se borra ni
se edita, solo se cierra.

## 5. Previsualización de conversión

| Método | Ruta | Permiso |
|---|---|---|
| `POST` | `/catalogos/conversion/preview` | `view` |

Cuerpo: `product_id`, `presentation_id?`, `quantity`, `date?`.

```json
{
  "quantity": "10",
  "presentation": { "code": "CAJA", "label": "Caja × 100" },
  "factor_applied": "100.000000",
  "version_id": "…",
  "base_quantity": "1000.000000",
  "base_uom": { "code": "UND", "symbol": "und" },
  "exact": true,
  "explanation": "10 CAJAS = 1.000 UND"
}
```

> **Informativo.** El frontend lo muestra; **no** vincula. Al guardar, el backend
> recalcula (FR-011-043, FR-011-044).

## 6. Códigos de error

| Código | HTTP | Cuándo |
|---|---|---|
| `UOM_CODE_DUPLICATE` | 409 | Código repetido en el ámbito |
| `UOM_DIMENSION_MISMATCH` | 422 | Conversión entre dimensiones distintas |
| `UOM_GLOBAL_READ_ONLY` | 403 | Una empresa intenta editar una unidad global |
| `UOM_IN_USE` | 409 | Borrar una unidad referenciada |
| `PRESENTATION_CODE_DUPLICATE` | 409 | Código repetido en el producto |
| `PRESENTATION_IN_USE` | 409 | Borrar una presentación usada; ofrece `deactivate` |
| `PRESENTATION_VERSION_OVERLAP` | 409 | Dos versiones vigentes solapadas |
| `PRESENTATION_VERSION_IMMUTABLE` | 409 | Editar una versión cerrada o en uso |
| `FACTOR_INVALID` | 422 | `factor <= 0` |
| `BASE_UNIT_REQUIRED` | 422 | Producto inventariable sin unidad base |
| `BASE_UNIT_LOCKED` | 409 | Cambiar la unidad base de un producto con movimientos |
| `CONVERSION_NOT_RESOLVABLE` | 422 | No hay versión vigente para esa fecha |
| `CONVERSION_NOT_EXACT` | 422 | Fracciones en unidad base sin `exact_in_base = false` declarado |
| `SNAPSHOT_IMMUTABLE` | 409 | Cambiar unidad o presentación en una línea emitida |
| `VERSION_CONFLICT` | 409 | `If-Match` obsoleto |

Todo rechazo de bloqueo incluye `reason`, `dependencies` y `allowed_actions`,
como fijó la Spec 008.

## 7. Contrato interno de conversión (§65)

Reutilizable por las Specs consumidoras **sin acoplarse a las tablas**:

```
resolve_conversion(product_id, presentation_id?, on_date) -> Version | None
to_base(quantity, product_id, presentation_id?, on_date)  -> (base_quantity, factor, version_id)
to_base_bulk(lines, on_date)                              -> [(…)]   # sin N+1
freeze(line)                                              -> escribe el snapshot al emitir
```

`to_base_bulk` existe porque un documento de mil líneas no puede hacer mil
consultas (NFR-011-01).

## 8. Contratos declarados para Specs futuras

| Spec | Contrato |
|---|---|
| 015-017 | La línea de requisición, oferta y orden acepta `presentation_id` y devuelve `base_quantity` |
| 019, 021 | La recepción compara su `base_quantity` con la de la orden, no las cantidades comerciales |
| 023 | Todo movimiento se registra en `base_quantity`; `location_id` ya es FK real desde la Spec 008 |
| 025 | Transferencia y conteo conservan la unidad en que se operó |
| 026 | Las capas de costo consumen `base_quantity` |
| 027, 034 | Reimprimir usa `uom_symbol_snapshot` y `presentation_label_snapshot`; **nunca** el maestro vigente |
| 029 | El pedido conserva la presentación comercial |
| 031, 032 | El picking conoce lo pedido y puede operar en otra unidad física |
| 035 | El despacho declara empaque desacoplado de la presentación comercial |
| 036 | La devolución hereda unidad y presentación del documento original |
| 043 | `permit_instances` recibe `uom_id`, sin presentación comercial |
| 012 | La línea conserva qué unidad o presentación sustentó el precio; la política de precios es de 012 |
| 050 | Los reportes disponen de cantidad original con su unidad y de cantidad base |
