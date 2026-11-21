# V4 · Integridad del ledger y de la valoración del inventario

| Campo | Valor |
|---|---|
| Programa | P3 · KONTROL Enterprise |
| Vertical | `V4-INVENTORY-LEDGER-VALUATION-INTEGRITY` (DAG Enterprise, nodo V4) |
| Spec dueña | `specs/003-inventario-logistica` (puntero: `spec003-v4-inventory-valuation-delta.md`) |
| Autorización | Prompt de ChatGPT/dueña del 2026-11-20 que nombra V4 (Constitución P2) |
| Base | `origin/develop` `29f8fcb9` |

## Pregunta de producto

¿Puede una unidad de inventario entrar, existir, transferirse, ajustarse, revertirse y salir sin perder
cantidad, valor, trazabilidad ni autorización?

## Requisitos

| ID | Requisito | Fuente | Defecto que cierra |
|---|---|---|---|
| V4-FR-01 | Una transferencia preserva la cantidad total de la empresa: lo que sale de A entra en B (o queda en tránsito, visible) | Vol. 2 §8; FR-003-060/061 | — |
| V4-FR-02 | Una transferencia preserva el valor total: el destino recibe el costo realmente consumido en el origen, capa por capa, con su landed cost. Nunca cero, precio maestro ni promedio redondeado | Vol. 3 §5; FR-003-080..083 | D-INV-TRANSFER-COST |
| V4-FR-03 | La recepción de transferencia es por línea y acumulativa; lo pendiente queda en tránsito con su valor; las diferencias siguen FR-003-062 (cuarentena, decisión de la Spec 023) | FR-003-062 | D-INV-TRANSFER-RECEIPT |
| V4-FR-04 | Se transfiere mercancía ubicada: sale de lo no ubicado libre de reservas y de las ubicaciones vendibles, en orden de secuencia | Vol. 2 §8 | D-INV-TRANSFER-LOCATED (hallazgo del ciclo) |
| V4-FR-05 | Revertir un movimiento lo compensa exactamente: mismo estado, ubicación y presentación; una entrada retira **sus** capas intactas; una salida restaura las capas que consumió | FR-003-022; Vol. 1 §5 | D-INV-REVERSE-STATE |
| V4-FR-06 | Una transferencia recibida se revierte con motivo: B → A con el mismo valor y a las mismas ubicaciones; no se revierte dos veces | FR-003-022 | — |
| V4-FR-07 | Un ajuste aprobado se aplica desde la pantalla y mueve el ledger; el positivo sin costo declarado entra al costo vigente del almacén (capas) | FR-003-072 | D-INV-ADJ-NO-APPLY |
| V4-FR-08 | Un conteo recorre DRAFT → FROZEN → COUNTING → SUBMITTED → APPROVED; lo esperado puede salir del ledger; la diferencia positiva entra valorada | FR-003-070/071 | D-INV-COUNT-STUCK |
| V4-FR-09 | Reconstruir saldos exige `inventario:recompute`, queda auditado y reserva solo lo pendiente de extraer | FR-003-010/011; Vol. 5 §4 | D-INV-RECOMPUTE |
| V4-FR-10 | Dos salidas concurrentes no sacan más de lo disponible (bloqueo de fila en PostgreSQL) | Vol. 5 §6 | sobretransferencia concurrente |
| V4-FR-11 | Aislamiento: ninguna transferencia ni movimiento cruza empresa o tenant | Vol. 5 §5 | — |
| V4-FR-12 | Cada operación material deja auditoría (envío, recepción, reversión, ajuste aplicado, recálculo) en el catálogo cerrado | Vol. 1 §3 | — |
| V4-FR-13 | Las pantallas muestran almacén, producto y tipo por nombre, estado en español y valor de la transferencia | Vol. 4 §2 | — |

## Fuera de alcance (decidido o dependiente)

| Tema | Estado | Motivo |
|---|---|---|
| D-INV-LEDGER-LOT (lote y serial en el ledger) | DEFERRED | Migración de `inventory_movements` y de todos los consumidores (recepción, picking, despacho); sub-vertical propia |
| D-APPROVAL-QTY-AS-VED | NOT_V4 | El defecto está en el contexto de aprobación de **incidencias de recepción de compras** (`purchasing/service.py:1536`); pertenece a V5/V10 |
| DISPATCH-COST-RELIEF-HISTORICO | OPEN | `AUTOMATIC_HISTORICAL_RECALCULATION=NO` |
| RETURN-REJECTED-VALUATION | OPEN, sin incoherencia nueva | V4 no cambia el reingreso de devoluciones |
| Congelamiento del conteo que bloquee movimientos | Decisión de la dueña | Política de congelamiento (rebaseline, INV-08) |
| Pérdida en tránsito (dar por perdido lo no recibido) | Decisión de la dueña | FR-003-062 pide destino y aprobación; hoy lo pendiente queda en tránsito, visible |
| Presentación en capas de recepción de compras (capa en unidad tecleada) | Hallazgo, no corregido | Cambio de semántica del costo de compras; ver `evidence/DEFECT_REPRODUCTION.md` |
