# Spec 018 §4 · De la importación al despacho: evidencia

Encargo `SPEC018_RELEASE_TO_PREPARATION_AND_DISPATCH`, del 2026-11-10. Delta: `../../spec018-release-to-dispatch-delta.md`.

## Estado

| Métrica | Estado |
|---|---|
| TECHNICAL_FOUNDATION_STATUS | COMPLETE, sin cambios de producto: los contratos de las Specs 021, 022, 023 y 030 a 035 ya hacían el traspaso |
| FUNCTIONAL_PRODUCT_STATUS | COMPLETE para el traspaso, en Chrome sobre PostgreSQL migrado. Deuda abierta: DISPATCH-COST-RELIEF |
| OWNER_READINESS_STATUS | OWNER_UAT_READY (pasos 77 a 84 de la tarjeta). `OWNER_ACCEPTED`: NO |

## Traspaso medido (E2E `resources/frontend/e2e/importaciones.spec.ts`)

| SOURCE | CONSUMER | IDENTITY_KEYS | STATE | QUANTITY | WAREHOUSE | LOCATION | EXPECTED (medido) |
|---|---|---|---|---|---|---|---|
| Recepción de la importación (019) | Confirmación (021) | empresa, almacén, producto | RECIBIDO | 10 | almacén del expediente | nula | DISPONIBLE = 0: no es vendible |
| Confirmación (021) + put-away (022) + reubicación | Disponibilidad (023) | ídem | DISPONIBLE | 10 | ídem | `ubicacionB` | 10 disponibles en la ubicación final |
| Disponibilidad | Pedido y reserva (030) | ídem + pedido | reserva ACTIVE; pedido RELEASED | 4 | ídem | — | reserva del producto y del almacén por 4 |
| Pedido RELEASED | Picking (031/032) | plan, línea | DISPONIBLE → PICKING → PREPARADO | 4 | ídem | sale de `ubicacionB` y se consolida en el área | movimientos `PICKLIST:<plan>` desde `ubicacionB` |
| Preparado | Confirmación independiente (033) | pedido, verificador distinto | confirmado | 4 | ídem | área | lo confirma el verificador, no quien preparó |
| Confirmado | Facturación (034) | pedido, serie, lote | factura EMITTED | 4 | — | — | emitida |
| Facturado | Despacho (035) | shipment | PREPARADO → DESPACHADO; pedido SHIPPED | 4 | ídem | área | DISPONIBLE 6, DESPACHADO 4, PREPARADO 0; ninguna reserva activa; movimiento `SHIPMENT:<id>` de 4 |

**Identidad del stock:** el producto y el almacén se crean en el escenario y no se siembra nada más. Un segundo pedido de 7, cuando quedan 6, recibe 409 `INSUFFICIENT_AVAILABLE`: lo vendido salió de lo importado.

**Negativas (3):**
1. Lo recibido y sin confirmar no es vendible.
2. Un pedido mayor que lo que queda se rechaza con 409.
3. Aislamiento: desde la empresa B, los saldos del producto salen vacíos o se rechazan, y un pedido contra el almacén de A se rechaza.

**Costo:** la valoración es 50 (10 × 5) antes y después del despacho. El despacho no destruye la valoración, pero tampoco consume capas de costo, y la salida no tiene costo propio. Queda la deuda DISPATCH-COST-RELIEF, por decisión de la dueña del 2026-11-10.

## Pruebas

| Puerta | Resultado |
|---|---|
| E2E `importaciones.spec.ts` extendida (Chrome, PostgreSQL efímero migrado, analizador real) | PASS a 1280, 390 y 320 |
| Responsive | `/ventas/despacho` sin desbordamiento a 390. La E2E completa pasa a 320 |
| Axe (WCAG 2.0/2.1 A y AA) en `/ventas/despacho` con el pedido pendiente | 0 graves o críticas |
| Teclado | Sin acciones nuevas: el ciclo no cambia pantallas |
| Regresión E2E de la cadena: receipts, inventory-confirmation, putaway, sales-orders, picking, pick-execution, order-confirmation, billing, dispatch | 63 de 64 pasan. Falla `inventory-confirmation.spec.ts`; sola, sobre una base nueva, falla en sus 3 casos (ver Hallazgos) |
| typecheck · lint | limpio · limpio |
| Mutaciones | No hay código de producto que mutar. Las negativas 1 y 2 hacen de controles: con el filtro de estado quitado, N1 falla (medido: 10 en RECIBIDO) |
| Suite completa de backend y Vitest | No se repitieron: el ciclo no cambia código de backend ni de `src`. La referencia es la de `f69bd69` (`../../../015-planificacion-abastecimiento/evidence/replenishment-detection/EVIDENCE.md`) |
| Alembic | Sin migración; la cabeza sigue en `0097_fusion_gov_replenishment` |
| OpenAPI | Sin cambios de API |

## Hallazgos

1. **DISPATCH-COST-RELIEF (deuda abierta, decisión material).** La salida 035 es un cambio de estado sin costo, y la valoración suma las capas con `quantity_remaining > 0` sea cual sea el estado. Lo despachado sigue valorado y no hay costo de ventas.
2. **Defecto previo de prueba: E2E-INVCONF-ALMACEN-SEMBRADO.** `inventory-confirmation.spec.ts` toma el primer almacén existente y no crea el suyo. En una base nueva solo pasa si otra prueba creó antes un almacén. El fichero y el producto son los mismos que en `f69bd69`, así que no es una regresión de este ciclo.
3. **Disponibilidad por estado.** `qty_available` es un campo de cada saldo, sea cual sea su estado; lo vendible es solo `DISPONIBLE`. La primera versión de la prueba sumaba todos los estados y daba un falso «vendible».
