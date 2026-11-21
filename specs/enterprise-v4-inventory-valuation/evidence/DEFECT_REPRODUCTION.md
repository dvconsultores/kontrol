# DEFECT_REPRODUCTION — V4

Reproducción **antes** de tocar producto, sobre PostgreSQL 16.2 de QA (`qa/pg-provision.sh`, puerto 55432), con
`tests/test_v4_inventory_valuation.py` en el HEAD `29f8fcb9`. Corrida en rojo: 16 fallos, 4 pasos (una de las
fallas era un TEST_DEFECT de la propia prueba: `CostingProfile` no tiene `name`; corregido en la prueba, no en
producto). Salida conservada en el scratchpad del ciclo y resumida aquí.

| Defecto | ¿Reproducido? | Rojo observado | Causa raíz | Autoridad | Corrección | Regresión |
|---|---|---|---|---|---|---|
| D-INV-TRANSFER-COST | Sí | destino `0.0` frente a `40` esperado; FIFO destino sin capas; landed `0.0` frente a `120` | La entrada de transferencia llamaba a `record_movement` sin `unit_cost` → sin capa; la salida consumía capas en el origen | `record_movement` + capas | Registro de consumo por salida (`inventory_cost_consumptions`) y restauración con la composición real en destino | transferencias, FIFO, landed (manual y real por la API de importaciones) |
| D-INV-TRANSFER-RECEIPT | Sí | La API devolvía `RECEIVED` con lo recibido parcial | `transition_transfer` llamaba a la recepción sin `received`; desde PARTIALLY_RECEIVED se reingresaba lo enviado completo | API + `confirm_transfer_receipt` | `received` en `TransitionBody`; recepción acumulativa y validada | recepción parcial y completa por API |
| D-INV-REVERSE-STATE | Sí | revertir la 2.ª entrada FIFO dejaba `100` en vez de `50`; revertir una entrada en CUARENTENA descontaba DISPONIBLE; revertir una salida FIFO restauraba `150.02` | El reverso reinvocaba `record_movement` con estado por defecto, sin presentación, consumiendo FIFO/promedio y recreando una capa a costo promedio redondeado a céntimos | `reverse_movement` | Reverso simétrico en estado, ubicación y presentación; entrada → retira sus capas intactas; salida → restaura su consumo | reversión de entrada, salida, estado, doble reversión, entrada ya consumida |
| D-INV-RECOMPUTE | Sí | `200` sin permiso; reconstrucción reservaba `4` (lo tecleado) frente a `3` pendientes | El endpoint solo exigía `get_current_user`; el recálculo sumaba `Reservation.quantity` | API + `recompute_balances` | `require_permission("inventario","recompute")`, auditoría, `pendiente = base − extraído` | permiso, auditoría, reservas |
| D-INV-ADJ-NO-APPLY | Sí | `allowed_actions("APPROVED")` sin `apply`; ajuste positivo sin costo dejaba valor `100` frente a `120` | Acción ausente; el positivo sin costo no creaba capa | `adjustment_allowed_actions`, `apply_adjustment` | `apply` en APPROVED; costo vigente del almacén si no se declara | ajuste positivo, negativo, auditoría |
| D-INV-COUNT-STUCK | Sí | FROZEN ofrecía `submit`; diferencia positiva sin valor | La máquina exige FROZEN→COUNTING y la UI no lo ofrecía; el conteo positivo entraba sin costo | `count_allowed_actions`, `approve_count` | acción `start`; esperado desde el ledger si se omite; diferencia valorada | ciclo y valoración del conteo |
| Sobretransferencia concurrente | Sí | Sin capas: **dos salidas de 7 sobre 10 pasaban**; con capas, la 2.ª fallaba con `NO_COST_LAYER` (por azar del bloqueo de capas, no por el disponible) | La comprobación de disponible leía la fila sin bloqueo | `record_movement` / envío | Bloqueo de la fila (y del ancla del almacén en la transferencia) antes de leer el disponible | carrera real con dos hilos en PostgreSQL, con y sin costo |
| D-INV-TRANSFER-LOCATED (hallazgo) | Sí (al diseñar la E2E de landed cost) | La transferencia solo sacaba de la fila sin ubicación: la mercancía colocada por put-away daba `INSUFFICIENT_STOCK` | `confirm_transfer_ship` descontaba siempre `location_id=None` | envío | `_origin_pieces`: no ubicado libre de reservas + ubicaciones en orden; reversión a la ubicación de origen | transferencia de mercancía ubicada |
| D-INV-FIFO-SAME-TX-ORDER (hallazgo) | Sí (intermitente en la prueba FIFO) | Capas de la misma transacción empataban en `created_at` y el FIFO las tomaba en orden indeterminado | `server_default=now()` es la hora de inicio de la transacción en PostgreSQL | `_apply_cost_in` | marca de orden estrictamente creciente en capas y consumos | prueba FIFO estable en 3 corridas |
| D-INV-LEDGER-LOT | No corregido | — | El ledger no tiene `lot_id`/`serial_id` | — | DEFERRED (sub-vertical con migración) | — |
| D-APPROVAL-QTY-AS-VED | No es de V4 | — | Contexto de aprobación de incidencias de compra | `purchasing` | Dependencia V5/V10 | — |

## Hallazgo registrado, no corregido

**Capa de recepción en unidad tecleada.** La recepción de compras pasa a `record_movement` la cantidad en su
presentación (p. ej. 2 cajas) y el precio por presentación; la capa nace con 2 unidades mientras el saldo
suma la cantidad base (24). Es previo a V4. Corregirlo cambia la semántica del costo de compras y, con
`unit_cost` a dos decimales, redondearía el costo unitario; V4 conserva la semántica actual y no lo empeora.
