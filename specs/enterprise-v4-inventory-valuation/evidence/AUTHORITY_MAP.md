# AUTHORITY_MAP — quién decide cantidad y valor del inventario (HEAD tras V4)

Ficheros: `resources/backend/app/modules/inventory/service.py` (SVC), `.../inventory/api.py` (API),
`.../inventory/models.py`, `alembic/versions/0130_v4_inventory_cost_consumptions.py`.

## Cantidad — una sola autoridad

| Operación | Entra por | Notas |
|---|---|---|
| Entrada / salida / ajuste / conteo / transferencia / reversión | `record_movement` (SVC) | Única que escribe movimientos de un solo lado y el saldo. V4: bloquea la fila que descuenta (`lock_balance`) antes de comprobar el disponible |
| Reclasificación de estado (recepción, confirmación, despacho, devolución) | `reclassify` (SVC) | Dos lados, mismo almacén; ya bloqueaba. Sin cambios en V4 |
| Put-away y reubicación | `putaway` (SVC), `location_validation` | Dos ubicaciones, mismo estado; sin cambios |
| Reserva | `reserve` / `_close_reservation` / `consume_on_pick` (SVC) | Contador sobre la fila ancla; sin cambios |
| Saldo (proyección) | `_get_balance` + `recompute_balances` (SVC) | V4: el recálculo reserva solo lo pendiente de extraer |

`QUANTITY_LEDGER_AUTHORITIES = 1`: todo cambio de cantidad pasa por `inventory/service.py`. Compras
(`purchasing/service.py:1282`), ventas (`sales/service.py` vía `reclassify`) e importaciones usan esas
primitivas; ninguno escribe `inventory_movements` ni `inventory_balances` por su cuenta (comprobado con
`grep "InventoryMovement("`: solo `inventory/service.py` y `inventory/location_validation.py`).

## Valor — una sola autoridad

| Primitiva (SVC) | Hace |
|---|---|
| `_apply_cost_in` | Crea capa (desde V4 con `source_movement_id` y marca de orden propia) |
| `_consume_cost_breakdown` | Único algoritmo de consumo (FIFO o promedio), con `FOR UPDATE` sobre las capas |
| `_record_consumption` / `_persist_consumption` | V4: registra capa por capa lo consumido (`inventory_cost_consumptions`) |
| `_restore_from_consumptions` / `_restore_from_sources` | V4: devuelve a capas, en otro almacén o en el mismo, el costo consumido (costo base + landed) |
| `_own_layers_for_reversal` / `_retire_layers` | V4: retira exactamente las capas que creó una entrada revertida |
| `current_unit_cost` | V4: costo vigente del almacén para lo encontrado (ajuste/conteo) |
| `relieve_dispatch_cost` / `restore_return_cost` | Spec 035 (despacho y devolución); usan `_consume_cost_breakdown` |
| `valuation` / `valuation_by_currency` / `layer_value` / `effective_unit_cost` | Consulta |

Landed cost: `imports/landed_cost.py` escribe `cost_layers.landed_cost` (Spec 018); V4 lo lee al consumir y lo
traslada proporcionalmente. `VALUATION_AUTHORITIES = 1`.

Dos testigos de consumo coexisten: `dispatch_cost_reliefs` (Spec 035, despacho de ventas) e
`inventory_cost_consumptions` (V4, salidas por `record_movement`). No son autoridades: ambos los escribe la
misma primitiva de consumo. Unificarlos exige tocar ventas y queda anotado como deuda menor.

## Transferencia

| Paso | Función | Valor |
|---|---|---|
| Envío | `confirm_transfer_ship` → `_origin_pieces` → `record_movement` (una salida por ubicación, `TRANSFER-OUT:{línea}:{n}`) | consumo registrado; en tránsito |
| Recepción | `confirm_transfer_receipt` → `record_movement` (`TRANSFER-IN:{línea}:{n}`, sin costo propio) → `_restore_from_sources` | capas en destino con la composición del origen |
| Reversión | `reverse_transfer` → `reverse_movement` de cada entrada → entrada en origen por cada salida + `_restore_from_sources` | mismo valor, mismas ubicaciones |
| Resumen | `transfer_cost_summary` | enviado / recibido / en tránsito |

## Autorización

| Operación | Permiso |
|---|---|
| Crear transferencia, movimiento, reversión de movimiento | `inventario:create` |
| Transiciones de transferencia y conteo | `inventario:transition` |
| Ajustes y reversión de transferencia | `inventario:approve` |
| Recalcular saldos | `inventario:recompute` (nuevo; migración 0129 lo otorga a quien ya aprobaba inventario) |
