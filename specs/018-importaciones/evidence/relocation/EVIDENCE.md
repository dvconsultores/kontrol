# Evidencia · Validación física de ubicación y reubicación por error

**Fecha:** 2026-11-09. **Iniciativa:** `SPEC018_REUBICACION_ERROR_Y_VALIDACION_FISICA`. **Datos:** sintéticos.

| Campo | Valor |
|---|---|
| DATABASE_ENGINE | PostgreSQL 16.2 de QA |
| SCHEMA_SOURCE | Alembic, base nueva, cabeza `0091_location_validations` (`alembic heads` = 1) |
| BROWSER | Google Chrome, `qa/e2e-run.py --con-analizador` (base efímera por corrida) |

## Pruebas del backend (`tests/test_importaciones_relocation.py`)

PostgreSQL: 18 de 18. SQLite: 17 de 17, más 1 omitida (la de concurrencia exige PostgreSQL).

| Escenario | Qué demuestra |
|---|---|
| a · Coincide | Resultado MATCH (estado CONFIRMED), sin movimiento `REUBICACION`; saldos sin cambios; `INVENTORY_LOCATION_VALIDATED` |
| b · No coincide | Resultado MISMATCH (estado PENDING), `stale` falso, saldos sin cambios; `INVENTORY_LOCATION_MISMATCH_DETECTED` |
| c · Reubicación | A = 0, B = 10, total igual. El movimiento va A → B con el mismo estado y el mismo almacén, el `document_ref` de la recepción, tipo `REUBICACION` y sin `unit_cost`. Se emite `INVENTORY_RELOCATED_BY_ERROR` con el motivo. La tabla del expediente muestra B. El «Ubicado» sigue en 10 y el historial muestra el nombre de usuario, nunca un UUID |
| d · Costo | Valoración y capas (`quantity_remaining`, `unit_cost`, `landed_cost`) idénticas antes y después |
| e · Reservas | El ancla conserva `qty_reserved = 3`; las filas A y B quedan con `qty_reserved = 0` |
| f · Parcial | Validar 4 y reubicar 4: A = 6, B = 4 |
| g · Cantidades | 11 por el expediente: `IMPORT_LOCATION_NOT_ATTRIBUTED`. 11 por Inventario: `INSUFFICIENT_LOCATION_QUANTITY`. 0: `INVALID_QUANTITY`. Reubicar más de lo validado: `RELOCATION_QUANTITY_EXCEEDS_VALIDATION` |
| h · Vigencia | Si A cambia después de validar, la reubicación se rechaza con `LOCATION_VALIDATION_STALE` y no mueve nada. Una validación nueva deja la anterior `SUPERSEDED`, y reubicar esa anterior se rechaza con `LOCATION_VALIDATION_SUPERSEDED` |
| i · Doble | La segunda reubicación se rechaza con `LOCATION_VALIDATION_ALREADY_RELOCATED` |
| j · A → A | Reubicar una validación MATCH se rechaza con `LOCATION_VALIDATION_NOT_MISMATCH` |
| k · Motivo | Un motivo de solo espacios devuelve 422, y la validación sigue PENDING |
| l · Permisos | Con solo permisos de Compras: consulta 200, validar 403, reubicar 403. Con solo lectura: validar 403 |
| m · Ubicaciones | Inexistente: 404. Otro almacén: `LOCATION_OTHER_WAREHOUSE`. Inactiva: `LOCATION_NOT_ELIGIBLE`. Otra empresa: 404 |
| n · Aislamiento | Validación inexistente: 404. Recepción de otro expediente: `IMPORT_RECEIPT_NOT_IN_FILE`. Expediente de otra empresa: `IMPORT_NOT_FOUND` |
| o · Atribución | Una ubicación sin nada atribuido a la recepción se rechaza con `IMPORT_LOCATION_NOT_ATTRIBUTED` |
| p · Serie | Una cantidad parcial de una fila con serie se rechaza con `SERIAL_INDIVISIBLE` |
| q · Reconstrucción | `recompute_balances` reproduce A = 0 y B = 10 |
| r · Concurrencia | Dos reubicaciones simultáneas: una entra y la otra recibe `LOCATION_VALIDATION_ALREADY_RELOCATED` |

## Resto de puertas

| Puerta | Resultado |
|---|---|
| Alembic | Subida, bajada a `0090_import_difference_report` y subida: PASS en PostgreSQL |
| Regresión mínima en PostgreSQL | 221 de 221: put-away (Spec 022), confirmación (021), multiestado (023), inventario, Importaciones (seguimiento, costos, landed cost, reporte de diferencias, reubicación), catálogo (425), cabeza, migraciones, instantáneas |
| Convergencia ORM/base | `inventory_location_validations` converge. `test_n10_convergence` sigue fallando solo por las 6 tablas de importaciones de la deuda conocida |
| E2E Chrome (`importaciones.spec.ts`, paso 6.5) | PASS a 1280, 390 y 320 px; limpieza LIMPIA. Recorre: ubicada en A → coincide → no coincide (sin mover) → reubicar A → B con motivo → fila en B → saldos (A = 0, B = cantidad, total igual, estados iguales) → valoración igual → historial |
| Axe WCAG 2.2 AA | 0 violaciones en 5 estados (sin validar, coincide, no coincide, diálogo de confirmación, historial) a 1280, 390 y 320 px. Sonda local, fuera del repositorio |
| Desborde horizontal | Ninguno en esos 5 estados a 390 y 320 px |
| Frontend | TSC, ESLint (0 avisos), Vitest 1854 de 1854 (8 nuevos), build |
| Backend estático | Ruff limpio; mypy en 154, igual que la línea base |

## Hallazgos

- **Defecto preexistente (Spec 003, fuera de alcance).** `recompute_balances(..., warehouse_id=X)` filtra movimientos y saldos por almacén, pero suma las reservas activas de todos los almacenes. Con reservas en otro almacén, en PostgreSQL choca con `uq_inventory_balances_key`. La reconstrucción por empresa funciona. No se corrigió.
- **Nombres de CHECK duplicados.** La convención de nombres antepone `ck_<tabla>_` también a los nombres que ya traen el prefijo, como ya ocurría en `0090`. El modelo y la base coinciden; es cosmético.
- **Teclado.** El foco y el teclado del diálogo los da el `ConfirmationDialog` existente. No hay una prueba de teclado propia de este ciclo.
- **Lote y serie.** El ledger no guarda lote ni serie por ubicación (`InventoryMovement` no tiene esas columnas). La reubicación conserva la identidad de la fila de origen, y la regla de serie indivisible se prueba sobre el saldo.
