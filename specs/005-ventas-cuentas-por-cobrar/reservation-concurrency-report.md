# SPEC 030 — INFORME DE CONCURRENCIA

| Campo | Valor |
|---|---|
| Regla | `ADR-D0-003` v2 R-D0-03-3 · `d0-03-reservation-concurrency-analysis.md` |
| Implementación | `inventory.lock_balance` (`SELECT … FOR UPDATE`, creación segura bajo savepoint + índice único) · `available_under_lock` · `sales.confirmar_pedido` (bloqueo del pedido, orden determinista por `product_id`, comprobación bajo bloqueo, reserva) |
| Prueba | `tests/test_spec030_concurrency.py` — dos hilos, dos sesiones, dos conexiones reales a PostgreSQL 18.6, barrera antes de confirmar |

## Flujo obligatorio (§38) tal como quedó

```
BEGIN (sesión de la petición)
  SELECT sales_orders … FOR UPDATE                     -- _lock_order
  líneas ordenadas por (product_id, id)                -- IMP-030-023
  por línea: SELECT inventory_balances … FOR UPDATE    -- lock_balance
             available = on_hand − reserved            -- available_under_lock
  si alguna no alcanza y el almacén no permite negativo → 409 + ROLLBACK (nada persiste)
  por línea: INSERT reservations … ; UPDATE balance    -- reserve (vuelve a bloquear la misma fila: no espera)
  UPDATE sales_orders SET status='SUBMITTED' …
  require_for_document (045) → RELEASED o espera
COMMIT
```

Nunca «leer disponible → luego bloquear». `reserve` tampoco lee `get_available`: bloquea y lee
(guardia estructural `test_la_disponibilidad_se_lee_bajo_bloqueo_y_en_orden_determinista`).

## Resultado medido

| Caso | Disponible | A | B | Resultado | Contador final |
|---|---|---|---|---|---|
| sin `allow_negative` | 10 | 8 | 8 | exactamente uno `OK`, el otro `INSUFFICIENT_AVAILABLE`; ganador `RELEASED`, perdedor `DRAFT`; una sola `RESERVATION_CREATED` en auditoría | `on_hand 10 · reserved 8 · available 2` |
| con `allow_negative` | 10 | 8 | 8 | ambos `OK`; la primera cabía y la segunda no → una marcada `oversell` | `10 · 16 · −6` (sobreventa por política, contadores íntegros) |

Deadlocks: el orden determinista de bloqueo por producto evita el abrazo mortal entre pedidos con los
mismos productos en distinto orden. La fila de saldo inexistente se crea bajo `begin_nested`; si dos
transacciones la crean a la vez, la que pierde el índice único relee y se bloquea sobre la fila de la
que ganó.

SQLite ignora `FOR UPDATE`; por eso la prueba de carrera solo se ejecuta sobre PostgreSQL (P21) y
las suites de SQLite cubren únicamente la lógica secuencial.
