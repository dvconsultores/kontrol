# Delta · Validación física de ubicación y reubicación por error

**Spec dueña:** 018 (Importaciones, DOCX §4). **Autoridades que consume:** Spec 003 (ledger `InventoryMovement`, cache `InventoryBalance`), Spec 008 (`WarehouseLocation`, `display_path`), Spec 022 (put-away), Spec 023 (estado de mercancía). **No cambia** Spec 022 ni la estructura de la Spec 008.

**Autorización de implement:** encargo de la dueña del 2026-11-09, que nombra la iniciativa `SPEC018_REUBICACION_ERROR_Y_VALIDACION_FISICA`. `MATERIAL_DECISION_REQUIRED = 0`: cada decisión es `SOURCE_BACKED_RULE` (SBR), con su fuente en el código, o `DERIVED_TECHNICAL_DECISION` (DTD).

## Resultado para la dueña

En Compras → Importaciones → Expediente → Ubicación, en «Ubicación física», la usuaria ve por fila:

- la recepción, el producto, el estado, la cantidad;
- la ubicación registrada, con su ruta física;
- la última validación.

Con eso puede:

- **Validar ubicación física:** elige, entre las ubicaciones reales del almacén, la ubicación donde encontró la mercancía. El resultado es «Coincide» o «No coincide», sin mover nada.
- **Reubicar por error**, si la validación no coincide: confirma origen, destino, producto, cantidad, estado y un motivo obligatorio. El inventario queda en B.
- **Consultar el historial** de validaciones y reubicaciones: fecha, usuario, A → B, resultado y motivo.

## Arqueología (lo que existe)

| Hecho | Fuente | Consecuencia |
|---|---|---|
| El ledger ya expresa un traslado interno: `source_location_id`, `target_location_id`, `source_state = target_state`, y `recompute_balances` lo suma sin suponer | `inventory/models.py` (procedencia de ubicación), `service.py:recompute_balances` | No hace falta otro ledger ni una tabla de reubicaciones |
| `putaway()` mueve existencia entre dos filas de saldo del mismo almacén: bloquea en orden determinista, conserva estado, no toca `qty_reserved` ni capas de costo | `service.py:putaway` | Es el patrón hermano. **No se modifica** |
| El reservado vive en la fila ancla (`location_id` nula); la reserva es de almacén, no de ubicación (`R-D0-14-1`). Las líneas de picking no llevan ubicación | `lock_balance`, `PickListLine` | Reubicar entre ubicaciones concretas no toca reservas: `RESERVATIONS_PRESERVED` por construcción, y se prueba |
| Las transferencias (`TRANSFERENCIA_SALIDA`/`ENTRADA`) pasan por `IN_TRANSIT`, usan `record_movement` OUT/IN, que **consume capas de costo y crea otras**, y van entre almacenes | `service.py:confirm_transfer_ship/receipt`, `record_movement` | **Rechazadas**: no son neutrales en costo y su semántica es otra |
| Importaciones calcula «Ubicado» y la tabla «Ubicaciones» sumando los movimientos `UBICACION` con `document_ref` = código de recepción | `imports/service.py:_logistics_quantities`, `_locations_detail` | Registrar la corrección como `UBICACION` la contaría dos veces: hace falta un tipo propio y que la tabla de ubicaciones neteé origen y destino |
| `InventoryMovement` **no tiene** `lot_id` ni `serial_id`; `record_movement` escribe saldos con lote y serie nulos y `recompute_balances` los colapsa a nulos | `models.py`, `service.py:record_movement` | En la arquitectura vigente, lote y serie no son una dimensión de ubicación en el ledger. La reubicación conserva la identidad de la fila de origen (lote y serie incluidos) y no crea ni altera lotes ni series |
| Los tipos de movimiento base se autoconfiguran por empresa | `BASE_MOVEMENT_TYPES`, `_get_movement_type_by_code` | Un tipo nuevo no necesita migración |
| `display_path` da la ruta legible almacén / zona / pasillo / rack / nivel / código | `organization/structure.py` | Se usa para mostrar ubicaciones, nunca el UUID |
| Permisos del put-away: `inventario:view` para consultar, `inventario:create` para mover | `inventory/api.py` | Se reutilizan, sin permiso nuevo |

## Decisiones

| ID | Decisión | Tipo |
|---|---|---|
| RL-01 | La validación física es una entidad propia e inmutable en lo observado: `InventoryLocationValidation` (`inventory_location_validations`), en el módulo de inventario, con referencias opcionales a `ImportFile` y `GoodsReceipt` | DTD (§6, §33) |
| RL-02 | `MATCH` si la ubicación observada es la registrada: no hay movimiento, no se toca el saldo y queda `status = CONFIRMED`. `MISMATCH` en otro caso: `status = PENDING`, y no se mueve nada | SBR (§9, §10) |
| RL-03 | La ubicación observada se resuelve con `location_in_warehouse`. Otra empresa: 404. Otro almacén: 409 `LOCATION_OTHER_WAREHOUSE`. Inactiva: 409 `LOCATION_NOT_ELIGIBLE`. No se admite texto libre | SBR (§8) |
| RL-04 | La reubicación es un movimiento nuevo, inmutable, de tipo **`REUBICACION`** («Reubicación por error de ubicación», `INTERNAL`), con origen A, destino B, el mismo estado y el mismo almacén. No usa `UBICACION`, para no alterar el «Ubicado» del put-away inicial ni confundir colocación con corrección | SBR + DTD (§12, §13) |
| RL-05 | La reubicación no llama a `_consume_cost` ni a `_apply_cost_in`, y el movimiento va sin `unit_cost`: costo, capa FIFO, promedio y valoración no cambian | SBR (§16) |
| RL-06 | Solo cambia `qty_on_hand` de las filas A y B; `qty_reserved` no se toca | SBR (§17) |
| RL-07 | Cantidad: mayor que 0, menor o igual que lo observado en la validación y que la existencia actual en A. Se admite reubicación parcial, porque la fila de saldo es fungible. Si la fila tiene `serial_id`, la cantidad debe ser la fila entera (indivisible) | DTD (§18, §19) |
| RL-08 | **Validación vigente:** la validación guarda `registered_qty_snapshot`, la existencia en A al validar. Al reubicar, con A y B bloqueadas, si la existencia actual en A difiere, el resultado es 409 `LOCATION_VALIDATION_STALE` y no se mueve nada. Una validación nueva sobre la misma fila marca `SUPERSEDED` las `PENDING` anteriores. La lectura expone `stale` | DTD (§21, §22) |
| RL-09 | Concurrencia: la fila de validación se bloquea `FOR UPDATE` y los saldos A y B en orden determinista, como en `putaway`. La segunda reubicación ve `RELOCATED` y recibe 409 `LOCATION_VALIDATION_ALREADY_RELOCATED` | SBR (§21) |
| RL-10 | Trazabilidad: la validación hecha desde el expediente guarda `import_file_id`, `receipt_id` y `document_ref` (código de recepción), y el movimiento `REUBICACION` lleva ese `document_ref`. Solo se valida lo que el ledger atribuye a esa recepción: la suma neta de `UBICACION` y `REUBICACION` con ese `document_ref`; si no, 409 `IMPORT_LOCATION_NOT_ATTRIBUTED`. No se atribuye nada en retrospectiva | SBR (§24) |
| RL-11 | La tabla «Ubicaciones» del expediente pasa a netear los traslados (+ destino, − origen) con la misma función. El «Ubicado» del resumen sigue contando solo `UBICACION` | DTD |
| RL-12 | Permisos: leer la sección del expediente con `compras:view`, como el detalle; validar y reubicar con `inventario:create`. Un usuario con solo permisos de Compras no mueve existencias | SBR (§30) |
| RL-13 | Auditoría con `record_audit` (catálogo de 422 a 425): `INVENTORY_LOCATION_VALIDATED` (MATCH), `INVENTORY_LOCATION_MISMATCH_DETECTED` (MISMATCH) e `INVENTORY_RELOCATED_BY_ERROR` | SBR (§32) |
| RL-14 | Una sola autoridad: el servicio `inventory/location_validation.py`. Inventario expone `POST/GET /inventory/location-validations` y `POST /inventory/location-validations/{id}/relocate`. El expediente expone `GET /importaciones/{id}/physical-locations` y `POST /importaciones/{id}/physical-locations/validate`, que comprueba la atribución y llama al mismo servicio | DTD (§29) |

## Modelo (una migración, `0091_location_validations`, sobre `0090_import_difference_report`)

`inventory_location_validations`:

- Identidad y alcance: `id`, `created_at`, `updated_at`, `created_by` (no nulo), `company_id`, `warehouse_id`, `product_id`, `lot_id` (nulo), `serial_id` (nulo), `state`.
- Observación: `quantity`, `registered_qty_snapshot`, `registered_location_id`, `observed_location_id`, `result`, `status`, `validated_at`, `validated_by`.
- Trazabilidad: `import_file_id` (nulo), `receipt_id` (nulo), `document_ref` (nulo).
- Reubicación: `movement_id` (nulo, único), `relocated_quantity`, `relocation_reason`, `relocated_at`, `relocated_by`.
- Restricciones:
  - `quantity > 0`;
  - `result` coherente con la igualdad de ubicaciones;
  - `status` coherente con `result`;
  - `movement_id` presente si y solo si `status = RELOCATED`.

No se crea tabla de reubicaciones: el hecho lo expresan el movimiento, la validación y la auditoría (§34).

## Tareas

| ID | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T-RL-A | Modelo, migración, servicio, APIs, tipo `REUBICACION`, neteo de ubicaciones, catálogo y pruebas del backend | DEEPSEEK | deepseek-v4-pro | SÍ (permisos y aislamiento, con contrato fijado aquí) | SÍ | 2 | `inventory/models.py`, `inventory/service.py`, `inventory/location_validation.py`, `inventory/api.py`, `imports/physical_locations.py`, `imports/service.py`, `imports/api.py`, migración, catálogo, guardas de cabeza, `tests/test_importaciones_relocation.py` | Pruebas nuevas en PostgreSQL y SQLite | MATCH, MISMATCH, reubicación, conservación, costo, reservas, vigencia, concurrencia, permisos, aislamiento y auditoría |
| T-RL-B | Sección «Ubicación física» del expediente y Vitest | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | `ImportacionUbicacion.tsx`, `UbicacionFisica.tsx`, `tipos.ts`, prueba Vitest | Vitest dirigido | Estados, validación, reubicación e historial |
| T-RL-C | E2E de usuario en Chrome (paso 6.5 de `importaciones.spec.ts`) | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | `e2e/importaciones.spec.ts` | E2E sobre PostgreSQL de Alembic | Flujo §39 |
| T-RL-D | Certificación, documentos y publicación | CLAUDE | n-a | NO | SÍ | 0 | Evidencia, tarjeta y matrices | Cierre técnico | `HEAD == origin/develop` |

T-RL-A es `SECURITY_SENSITIVE` porque toca permisos y aislamiento. Se delega porque este documento fija el contrato completo (permisos existentes, códigos de error, 404 o 409), sin decisión abierta. `LOCAL_RULE_CONFLICT = 1`: `CLAUDE.md` reserva las migraciones a Claude, y la regla permanente de la dueña (`OWNER_ORCHESTRATION_OVERRIDE`, §53) manda que las escriba DeepSeek.

## Fuera de alcance

- Clasificación, zonas A a E, etiquetado y *slotting*.
- Recomendación automática de ubicación.
- IMPORT-PUTAWAY-ATRIBUCION completa.
- Rotación.
- Pantalla propia en Inventario: la API queda expuesta, pero esta entrega es la del expediente.
- Escáner o hardware.
- Lote y serie como dimensión de ubicación en el ledger: no existe en la arquitectura vigente y no se inventa.

## Cierre

`CONVERGED` en el commit de cierre del ciclo en `develop`. Evidencia: `evidence/relocation/EVIDENCE.md`. Intentos: `evidence/relocation/ATTEMPT_LOG.md`. `OWNER_ACCEPTED` lo concede solo la dueña.
