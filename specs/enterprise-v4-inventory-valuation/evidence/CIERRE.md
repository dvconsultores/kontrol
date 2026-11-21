# CIERRE · V4-INVENTORY-LEDGER-VALUATION-INTEGRITY

Fecha: 2026-11-20/21 · P3 Enterprise · árbol integrado `f6bce8e1` (V4 `f277ee2c` + P1 TRE-05/BUD-02 `da91a606`).

## Criterio de producto V4

| Criterio | Resultado | Evidencia |
|---|---|---|
| TRANSFER_QUANTITY_INTEGRITY | PASS | parcial, FIFO, ubicada; E2E-V4-01 |
| TRANSFER_VALUE_INTEGRITY | PASS | 40 en destino, 60 en origen, 100 total; FIFO 5@10 + 2@20; M1/M2/M3/M11 |
| TRANSFER_LANDED_COST_INTEGRITY | PASS | manual (120), real por la API de importaciones (24 de 60) y corrida diagnóstica del flujo de importación por interfaz; M4 |
| REVERSAL_QUANTITY_INTEGRITY | PASS | entrada, salida, estado, transferencia, ubicación de origen |
| REVERSAL_VALUE_INTEGRITY | PASS | 150 exacto (antes 150,02); M5 |
| DOUBLE_REVERSAL_BLOCKED | YES | `ALREADY_REVERSED` en entrada y salida; transferencia revertida → 409; M6 |
| ADJUSTMENT_LEDGER_INTEGRITY | PASS | +2 → 12 y 120; −3 → 7 y 70; M10/M10b |
| COUNT_LIFECYCLE | PASS | FROZEN→COUNTING (`start`), diferencia valorada; M13 |
| TRANSFER_RECEIPT_INTEGRITY | PASS | 3 + 1 acumulado por la API; M14 |
| BALANCE_RECALC_PERMISSION | PASS | 403 sin `inventario:recompute`; auditoría; reservas pendientes; M7/M15 |
| TENANT_ISOLATION / COMPANY_ISOLATION | PASS | otra empresa y otro tenant reciben 404; M8 |
| WAREHOUSE_SCOPE | PASS | almacén de otra empresa → 404; origen = destino → 422. El alcance de usuario por almacén no existe en el producto (SEG-03, fuera de V4) |
| OVER_TRANSFER_CONCURRENCY_BLOCKED | YES | dos hilos reales en PostgreSQL, con y sin costo: 1 éxito, 1 `INSUFFICIENT_STOCK`; M9 |
| QUANTITY_LEDGER_AUTHORITIES / VALUATION_AUTHORITIES | 1 / 1 | `AUTHORITY_MAP.md` |
| MUTATIONS | PASS 16/16 | `MUTATIONS.md` |

## Pruebas

| Gate | Resultado |
|---|---|
| PG del ciclo | `test_v4_inventory_valuation.py` 30/30 + landed real 1/1 (PostgreSQL 16.2) |
| PG dirigida (catálogos, permisos, migraciones, MFA, delegación, auditoría) | 218 pruebas; los únicos fallos eran constantes que V4 cambia legítimamente (cabeza, tamaños) y un defecto propio de la migración (permiso no otorgado a FUNCIONAL_COMPLETO), corregidos |
| Suite completa PG (3 tandas, árbol integrado) | 5 699 pasan, 147 fallan; **0 nuevos de V4**: 38 BASELINE reproducidos en `29f8fcb9` y 109 TIME_WINDOW (la corrida cruzó la medianoche): 107 pasan al repetir y 2 pasan con su módulo |
| Migración | `0130_v4_cost_consumptions` sobre `0129_gov_tre05_retencion`: upgrade → downgrade → upgrade en PostgreSQL vacío; cabeza única; rama de otorgamiento probada |
| E2E-V4-01 | PASS en Chrome real sobre PostgreSQL efímero, dos veces (antes y después de integrar P1) |
| E2E landed → transferencia | PASS en corrida diagnóstica (copia temporal que solo relaja la aserción de impresión del BASELINE); la E2E canónica de importaciones falla en la línea 515 por un BASELINE ajeno, reproducido en `29f8fcb9` con chromium y firefox |
| Axe 1280 / 390 / 320 | PASS (0 faltas graves o críticas, sin desbordamiento horizontal) en Transferencias |
| Vitest (Node 20) | 234/234 ficheros, 2 567 pruebas |
| tsc / eslint / build | PASS |
| ruff | PASS |
| mypy (ficheros tocados) | 0 errores nuevos (12 en la base → 1) |
| OpenAPI | Diferencia esperada: `POST /inventory/transfers/{id}/reverse`; `inventario:recompute` en el recálculo; campos aditivos en listados de transferencias, movimientos, ajustes y conteos. Diferencia inesperada: 0 |

## Rebaseline Enterprise

| Métrica | Antes | Después |
|---|---|---|
| COMPLETE | 52 | 52 |
| PRODUCT_DEFECT (filas) | 70 | 63 |
| PARTIAL | 132 | 139 |
| Defectos únicos abiertos | 60 | 55 (−6 corregidos, +1 hallazgo abierto D-INV-PRESENTATION-LAYER) |
| OWNER_UAT_READY (filas) | 1 | 1 |

Ninguna fila sube a COMPLETE: INV-01, 05, 06, 07, 08, 17 y TRV-08 conservan huecos fuera de V4.

## Estados que se mantienen

- `RETURN_REJECTED_VALUATION_STATUS=OPEN_UNCHANGED`: V4 no toca el reingreso de devoluciones ni crea incoherencia
  nueva; RECHAZADO sigue sin valorarse en devoluciones y no se vuelve vendible.
- `DISPATCH_COST_RELIEF_HISTORICO_STATUS=OPEN`: `AUTOMATIC_HISTORICAL_RECALCULATION=NO`.

## Decisiones abiertas (dueña / ChatGPT)

1. Pérdida en tránsito: destino y aprobación de lo enviado que no llega (FR-003-062).
2. Política de congelamiento del conteo: ¿bloquea movimientos?
3. Reserva al aprobar la transferencia (hoy se protege el disponible al enviar).
4. Sub-vertical D-INV-LEDGER-LOT (lote y serial en el ledger, con migración).
5. D-INV-PRESENTATION-LAYER: semántica de la capa de compras con presentación.
