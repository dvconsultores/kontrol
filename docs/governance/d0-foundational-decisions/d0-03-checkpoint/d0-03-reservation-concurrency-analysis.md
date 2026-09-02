# D0-03 — ANÁLISIS DE CONCURRENCIA, SOBREVENTA E IDEMPOTENCIA

Caso obligatorio: `available = 10`, pedido A pide 8, pedido B pide 8, simultáneos. El sistema jamás
puede terminar con `reserved = 16` salvo sobreventa explícita.

## 1. Por qué el código actual pierde la carrera

`reserve` (`inventory/service.py:669-697`) hace:

```
available = get_available(...)             # SELECT sin bloqueo
if quantity > available and not _allow_negative(warehouse): raise
db.add(Reservation(...)); db.flush()
balance = _get_balance(...)                # SELECT (o INSERT si no existe)
balance.qty_reserved += quantity           # UPDATE
```

PostgreSQL en `READ COMMITTED` (aislamiento por defecto de SQLAlchemy/psycopg): dos transacciones
leen `available = 10` antes de que ninguna escriba. Ambas pasan la comprobación, ambas insertan,
ambas hacen `UPDATE inventory_balances SET qty_reserved = qty_reserved + 8`. La segunda actualización
espera a la primera y **se aplica encima** (el `UPDATE` relee la fila tras el bloqueo): resultado
`reserved = 16`, `available = −6`. La comprobación de negocio se evaluó sobre un valor obsoleto.

Con SQLAlchemy ORM el `UPDATE` es `SET qty_reserved = :valor_calculado_en_python`, no un incremento
SQL: la segunda transacción escribe `8`, no `16`. Peor: **pierde** la reserva de la primera en el
contador, mientras las dos filas `Reservation` existen. El contador y el ledger divergen.

Ninguna de las dos variantes es aceptable. `test_over_reservation_rejected` no lo detecta porque
usa una sola sesión.

## 2. Estrategias evaluadas

| Estrategia | Garantiza «una sola gana» | Coste | Veredicto |
|---|---|---|---|
| `SELECT … FOR UPDATE` sobre la fila de saldo | Sí: serializa todas las reservas del mismo `(empresa, almacén, producto, ubicación, lote, serial, estado)` | Bloqueo corto; contención solo en el mismo producto/almacén | **Elegida** |
| `UPDATE … SET qty_reserved = qty_reserved + :q WHERE qty_available >= :q` (atomic update) | Sí, si la fila existe | Requiere fila previa; no permite reportar el disponible real en el error sin segunda lectura | Complemento válido; no sustituye al bloqueo porque la inserción de la reserva y el pedido van en la misma transacción |
| Ledger de reservas sin contador (sumar filas `ACTIVE` en cada lectura) | Sí, con bloqueo o `SERIALIZABLE` | Lecturas más caras; sigue necesitando serialización para la comprobación | No: cambia la autoridad de 003 sin necesidad |
| `CHECK (qty_reserved <= qty_on_hand)` | Solo como red de seguridad | No puede ver `allow_negative` (política de almacén, fuera de la fila) | **Rechazada como regla**: rompería los almacenes con sobreventa autorizada. Se conserva `CHECK (qty_reserved >= 0)` |
| Concurrencia optimista (`version` en el saldo) | Sí, con reintento | Reintentos en la capa de servicio; más complejo que el bloqueo pesimista con la misma garantía | No |
| `SERIALIZABLE` | Sí | Reintentos por `serialization_failure` en toda la transacción del pedido | No: el bloqueo de fila basta y es local |
| Advisory lock por `(empresa, producto, almacén)` | Sí | Fila de saldo puede no existir → útil precisamente ahí | Alternativa admisible para la creación de la fila; ver §4 |

## 3. Contrato de concurrencia (regla dura)

1. La reserva se crea **dentro de la transacción que confirma el pedido**. No hay `commit`
   intermedio: pedido, reservas, actualización de saldo y auditoría se confirman juntos o ninguno.
2. Antes de leer el disponible, la transacción adquiere `SELECT … FOR UPDATE` sobre la fila de
   `inventory_balances` de la clave `(company, warehouse, location IS NULL, product, lot, serial,
   state = 'DISPONIBLE')`.
3. El disponible se lee **después** del bloqueo y se compara en unidad base.
4. Si no alcanza y el almacén no autoriza sobreventa → `409 INSUFFICIENT_AVAILABLE` y `ROLLBACK` de
   toda la confirmación.
5. Para pedidos con varias líneas, los bloqueos se adquieren en **orden determinista** por
   `product_id` (y `lot_id`, `serial_id`) para que dos pedidos con los mismos productos en distinto
   orden no se bloqueen mutuamente (deadlock).
6. El frontend nunca es autoridad sobre disponibilidad (P6): puede mostrar `available`, no decidirlo.

## 4. La fila de saldo que no existe

Si el producto nunca tuvo saldo en ese almacén, no hay fila que bloquear y `_get_balance` haría
*select-then-insert* en las dos transacciones → dos filas para la misma clave. Hoy no hay
restricción que lo impida.

Contrato:

- `inventory_balances` recibe **unicidad** sobre la clave completa, con `COALESCE` para las
  dimensiones nulas (`location_id`, `lot_id`, `serial_id`) — índice único PostgreSQL declarado en
  ORM con `ddl_if(dialect="postgresql")` y en la migración (lección N7). Propietaria del cambio: la
  Spec 030 como consumidora que lo exige, con nota en 023.
- Sin fila de saldo el disponible es 0: sin `allow_negative` la confirmación falla antes de
  insertar nada. Con `allow_negative`, la inserción usa `INSERT … ON CONFLICT DO NOTHING` seguida de
  `SELECT … FOR UPDATE`, o un advisory lock transaccional sobre `hashtext(company||warehouse||product)`
  durante la creación. Cualquiera de las dos es válida; 030 elige y lo prueba.

## 5. Prueba obligatoria (criterio de aceptación)

Sobre PostgreSQL (no SQLite): dos sesiones/conexiones reales, una barrera que garantice que ambas
han leído la cabecera del pedido antes de que ninguna confirme, y la aserción:

- exactamente **una** confirmación devuelve `SUBMITTED` y la otra `409 INSUFFICIENT_AVAILABLE`;
- `qty_reserved == 8` y `qty_available == 2` en la fila de saldo;
- existe exactamente **una** fila `Reservation ACTIVE` para ese producto/almacén;
- la auditoría contiene un `RESERVATION_CREATED` y ningún `RESERVATION_CREATED` para el pedido perdedor.

Segunda prueba, con `allow_negative = true`: ambas confirman, `qty_reserved == 16`,
`qty_available == −6`, ambas reservas llevan `oversell = true` y sus eventos registran
`available_before`.

## 6. Idempotencia

| Operación repetida | Comportamiento exigido | Mecanismo |
|---|---|---|
| Confirmar dos veces el mismo pedido (doble clic, reintento de red) | Una sola reserva por línea | Máquina de estados (`SUBMITTED` no admite `SUBMITTED`) **y** índice único parcial `(source_line_id) WHERE status = 'ACTIVE'` en `reservations`: el segundo intento, si por cualquier camino llega a insertar, falla en BD |
| Liberar dos veces (cancelación reintentada, rechazo + cancelación) | Sin segunda resta | `release_reservation` exige `ACTIVE`; el camino de cancelación itera solo filas `ACTIVE`; `qty_reserved` nunca baja de 0 (`CHECK`) |
| Expirar dos veces | No-op | `expire_reservations` filtra `ACTIVE` |
| Consumir (despacho) dos veces | No-op | filas ya `FULFILLED` no se tocan; el movimiento de salida tiene su propia idempotencia (ADR-013) |
| Reservar por reintento de la misma llamada HTTP | Sin duplicado | `Idempotency-Key` ya vigente en las rutas de escritura (ADR-013) |

## 7. Sobreventa

- **Prohibida por defecto.** Nunca por carrera: el bloqueo la impide.
- **Permitida solo** en almacenes con `policies.allow_negative = true` (JSON gobernado, P8, autoridad
  única y ya existente para movimientos y reservas). No se crea una segunda llave.
- Toda reserva en sobreventa se marca `oversell = true` y su evento registra `available_before`. La
  consulta de reservas de la empresa puede filtrarlas.
- Un almacén con sobreventa permitida puede tener `qty_available < 0`; **la cadena de preparación
  (031/032) trata el faltante como incidencia**, nunca como ajuste silencioso.

## 8. Orden temporal y prioridad

La única prioridad en 030 es el **orden de compromiso**: la transacción que obtiene el bloqueo
primero reserva primero. Es determinista, auditable (timestamp de `RESERVATION_CREATED`) y no
requiere configuración. Prioridad por cliente, manual o por antigüedad de cotización es
**FUTURE** y solo tiene sentido con backorder (cola de pedidos esperando stock), que está fuera de
alcance. Propietaria futura: la extensión de 030 que introduzca backorder; sin ella no hay «cola»
que priorizar.

## 9. Lo que este análisis no decide

La implementación concreta (bloqueo de fila vs. advisory lock para la creación de la fila; `ON
CONFLICT`; forma del índice con `COALESCE`) la fija la Spec 030 en su `/speckit.plan`. Lo que sí
queda fijado aquí es la garantía observable (§3, §5) y que la garantía vive en PostgreSQL, dentro
de la transacción, y nunca en el cliente.
