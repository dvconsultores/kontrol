# DISPATCH-COST-RELIEF · evidencia

Encargo del 2026-11-11. Delta: `../../spec035-dispatch-cost-relief-delta.md`. Registro de intentos: `ATTEMPT_LOG.md`.

## Estado

| Métrica | Estado |
|---|---|
| TECHNICAL_FOUNDATION_STATUS | COMPLETE. Motor con desglose, instantánea `dispatch_cost_reliefs` (migración `0098_dispatch_cost_relief`), alivio en `confirm_shipment` y reposición en `reenter_return` |
| FUNCTIONAL_PRODUCT_STATUS | COMPLETE. El despacho saca de la valoración lo despachado, landed cost incluido, en Chrome sobre PostgreSQL migrado |
| OWNER_READINESS_STATUS | OWNER_UAT_READY: pasos 85 a 89 de la tarjeta. `OWNER_ACCEPTED`: NO |

## Causa raíz

`confirm_shipment` hacía PREPARADO → DESPACHADO con `reclassify`, que mueve el saldo de estado sin tocar las capas de costo. Por eso `valuation`, que suma las capas con `quantity_remaining > 0`, seguía contando lo despachado.

El picking no consume costo (`consume_on_pick`), así que no había un consumo previo que se pudiera duplicar.

## Corrección (código de DeepSeek, auditado por Claude)

- **`inventory.service._consume_cost_breakdown`.** Es el algoritmo de siempre, el de `_consume_cost`: perfil vigente con `_costing_method`, FIFO por `created_at`, AVERAGE proporcional y costo efectivo con landed cost. Ahora devuelve el desglose por capa y falla cerrado en estos casos:
  - `NO_COST_LAYER`, si las capas cubren solo una parte, con cualquiera de los dos métodos. Antes, AVERAGE dejaba `quantity_remaining` negativo.
  - `COST_LAYER_CURRENCY_MIXED`, si las capas tienen monedas distintas.
- **`_consume_cost`** conserva su firma y su resultado para `record_movement`.
- **`relieve_dispatch_cost`** guarda una fila de instantánea por cada par (línea, capa), con:
  - el despacho, la línea, el movimiento `SHIPMENT:<id>` y la capa;
  - la cantidad, el costo efectivo y el total;
  - la moneda y el método.

  Además fija el costo unitario y la moneda del movimiento. La restricción única `(shipment_line_id, cost_layer_id)` protege contra el doble consumo.
- **`confirm_shipment`:**
  - después del bloqueo del pedido, vuelve a leer el despacho con `FOR UPDATE` y vuelve sin hacer nada si ya salió;
  - el alivio corre en la misma transacción que la reclasificación, las reservas FULFILLED, el estado SHIPPED y la auditoría;
  - `SHIPMENT_CONFIRMED` incluye en `after` un resumen del costo (`method`, `currency`, `total`), y la entrada del catálogo lo admite.
- **`restore_return_cost`.** Lo que vuelve a DISPONIBLE por `reenter_return` recupera una capa con el costo de la instantánea del despacho (0,01, ROUND_HALF_EVEN), en la misma moneda. A RECHAZADO no se le repone capa.

Sin cambios: la máquina de estados, los saldos físicos, la API (OpenAPI idéntico a HEAD), `imports/*` y Government.

## Vectores medidos (PostgreSQL, `tests/test_spec035_dispatch_cost_relief.py`, 11 PASS)

| Prueba | Medido |
|---|---|
| V1 AVERAGE 10 @ 5, se despachan 4 | quedan 6; valoración 50 → 30; 1 fila (4, total 20, AVERAGE, VED); movimiento a 5,00; DESPACHADO 4; reservas FULFILLED |
| V2 AVERAGE 10 @ 5 + 10 @ 7, se despachan 4 | quedan 8 y 8; valoración 120 → 96; 2 filas, suma 4 y total 24, costo efectivo 6 en cada una |
| V3 FIFO 3 @ 5 y luego 10 @ 8, se despachan 5 | quedan 0 (CLOSED) y 8 (OPEN); valoración 95 → 64; filas (3, 15) y (2, 16); movimiento a 6,20 |
| V4 FIFO 10 @ 5, se despachan 4 | quedan 6; 50 → 30 |
| V5 AVERAGE con landed 10 (efectivo 6) | 60 → 36; la capa queda consumida, así que la reversión del landed cost se bloquea |
| V6 FIFO y V7 AVERAGE: 3 con costo + 2 sin costo, se despachan 5 | `NO_COST_LAYER`; tras el rollback: despacho READY, capas intactas, sin instantánea, reservas ACTIVE, PREPARADO 5 |
| V8 doble confirmación, en serie y con dos hilos | se consume una sola vez; 1 fila; valoración 30; DESPACHADO 4 |
| V9 devolución de 2 a DISPONIBLE | capa repuesta 2 @ 5,00 VED; valoración 30 → 40 |
| V9b devolución a RECHAZADO | no se repone capa; valoración 30 |
| Aislamiento | la capa del segundo almacén de A no se toca; la instantánea solo tiene filas de A y del almacén de origen; la empresa B valora 0 |

**Mutaciones**, aplicadas sobre el fichero y restauradas (byte a byte, verificado con `cmp`):
- M1, el despacho no consume costo: fallan las 11 pruebas.
- M2, sin el fallo cerrado de AVERAGE parcial: falla V7.

## Navegador (E2E `resources/frontend/e2e/importaciones.spec.ts`)

Chrome, PostgreSQL efímero migrado a `0098` y analizador real ClamAV 1.4.3.

Recorrido medido:
1. Importación de 10 unidades a 5 USD.
2. Flete capitalizable de 10 USD: se aplica, se revierte y se vuelve a aplicar. El costo efectivo queda en 6 y la capa en 60.
3. Confirmación, ubicación, pedido de 4, picking, confirmación independiente, factura y despacho.

Resultado:
- la valoración de la API baja exactamente 4 × 6 = 24;
- la capa queda con 6 unidades por un valor de 36,00;
- la reversión del flete responde 409 `IMPORT_COST_REVERSAL_BLOCKED`;
- la pestaña «Costos» del expediente muestra «36,00 USD».

| Puerta | Resultado |
|---|---|
| E2E a 1280 / 390 / 320 | PASS / PASS / PASS |
| Axe (WCAG 2.0/2.1 A y AA) en expediente → Costos tras el despacho | 1280: 0 graves o críticas. 390 y 320: una grave previa, `scrollable-region-focusable` en las tablas desplazables del expediente (`#diferencias` y costos). El ciclo no cambió `src`, así que la pantalla es la misma que en HEAD: deuda A11Y-IMPORT-SCROLL-REGIONS |
| Desbordamiento horizontal de la página en Costos | 1280, 390 y 320: no |
| typecheck · lint (frontend) | limpio · limpio |

## QA

| Puerta | Resultado |
|---|---|
| Regresión dirigida PostgreSQL: 44 ficheros (Specs 021 a 023 y 030 a 036, inventario, landed cost, catálogo de auditoría, migraciones y guardias) | 614 PASS, 0 fallos |
| Pruebas nuevas | 11 PASS |
| Alembic en PostgreSQL nuevo | `upgrade head` → `downgrade -1` → `upgrade head`; una sola cabeza: `0098_dispatch_cost_relief`; 5 índices y la restricción única |
| OpenAPI | idéntico a HEAD (mismo SHA-256) |
| ruff | limpio en los ficheros tocados. El I001 de `app/main.py` ya estaba en HEAD |
| mypy | 0 errores nuevos frente a HEAD en los ficheros tocados |
| Suite completa de backend en PostgreSQL, con analizador real | 5311 PASS, 5 fallos, 18 omitidas (1 h 48 min). Los 5 fallos son la línea base de P1: `gobierno_integridad_runner`; `n10` (solo los `created_by` de `import_*`; la tabla nueva está alineada con el ORM); `naive_datetime` (una ruta de Government); dos de `spec019_receipt`. NEW_FAILURES = 0 |

## Impacto en devoluciones (Spec 036)

Antes, la devolución reingresaba sin costo, pero como el despacho tampoco lo consumía, la valoración cuadraba por accidente. Ahora el despacho consume costo, así que el reingreso a DISPONIBLE repone la capa desde la instantánea. Si no lo hiciera, el siguiente despacho de esa mercancía fallaría con `NO_COST_LAYER`.

## Deudas registradas

- **DISPATCH-COST-RELIEF-HISTORICO.** Los despachos anteriores a `0098` no consumieron costo. Corregirlos es un backfill de datos y necesita la autorización de la dueña.
- **RETURN-REJECTED-VALUATION.** Lo que se reingresa a RECHAZADO no se valora.
- **COST-UI-SHIPMENT-SNAPSHOT (PRODUCT_UI_GAP).** El costo de cada salida queda en la instantánea y en la auditoría, pero ninguna pantalla lo muestra por despacho. La dueña lo comprueba con la capa del expediente y con la valoración.
- **COGS.** `COGS_ACCOUNTING_ENTRY_IMPLEMENTED = NO`: no hay módulo contable.

- **A11Y-IMPORT-SCROLL-REGIONS.** Las tablas desplazables del expediente no se pueden enfocar con el teclado a 390 y 320. Es previa a este ciclo.

## Cierre

`DISPATCH_COST_RELIEF_COMPLETE = 1`, `NEW_FAILURES = 0`. La matriz de la Spec 018 sigue en 32 de 42 COMPLETE: esta deuda era transversal y no era una fila.
