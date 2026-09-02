# D0-03 — MATRIZ DE FLUJOS (A–J)

Convenciones: estado del pedido en mayúsculas; `R:` = reservas de la línea; `S:` = saldo
`DISPONIBLE` del producto en el almacén del pedido como `on_hand / reserved / available`; `A:` =
evento de auditoría. Todos los flujos parten de un pedido con **una línea de 8 unidades base** y
almacén `W1` salvo que se indique. Las máquinas de estado citadas son las **objetivo** que la Spec
030 implementará (Decision §9); donde difieren del código actual se anota.

## FLOW A — Contado + stock suficiente

`S: 10 / 0 / 10`

| Paso | Actor | Acción | Pedido | Reserva | Saldo | Auditoría |
|---|---|---|---|---|---|---|
| 1 | Vendedor | Crea pedido (directo o desde cotización) | DRAFT | — | 10/0/10 | `SALES_ORDER_CREATED` |
| 2 | Vendedor (`ventas:submit`) | Confirma el pedido | **SUBMITTED** | `R: ACTIVE 8` (trigger `ORDER_CONFIRMATION`) | **10/8/2** | `SALES_ORDER_TRANSITIONED` + `RESERVATION_CREATED` |
| 3 | Sistema | 045 no abre solicitud (sin política) | CREDIT_PENDING → **APPROVED** → **RELEASED** en la misma transacción | sin cambio | 10/8/2 | transiciones auditadas |
| 4 | 031 | Entra en cola de picking | RELEASED | sin cambio | 10/8/2 | — (031) |
| 5 | 035 | Despacho confirmado | SHIPPED | `R: FULFILLED` | 2/0/2 (movimiento `SALIDA_DESPACHO` −8) | `RESERVATION_FULFILLED` |

Hoy: la reserva nace en el paso 3 y el despacho marca `RELEASED`.

## FLOW B — Contado + stock insuficiente

`S: 10 / 4 / 6`, pedido de 8.

| Paso | Actor | Acción | Pedido | Reserva | Saldo | Resultado |
|---|---|---|---|---|---|---|
| 1 | Vendedor | Confirma | DRAFT | intento 8 > 6 | 10/4/6 | **`409 INSUFFICIENT_AVAILABLE`** con detalle `{line_id, requested_base: 8, available_base: 6}` |
| 2 | — | Rollback completo | **DRAFT** (sin cambio) | ninguna | 10/4/6 | nada persiste, ni siquiera la transición |
| 3 | Vendedor | Edita el borrador a 6 (o divide en dos pedidos, o cambia de almacén) y confirma | SUBMITTED | `R: ACTIVE 6` | 10/10/0 | Flow A desde el paso 2 |

Si `W1.policies.allow_negative = true`: el paso 1 **sí** reserva 8, la reserva se marca
`oversell = true`, el saldo queda `10/12/−2` y `RESERVATION_CREATED` lleva `available_before: 6`.
No hay reserva parcial (6 de 8) ni pedido sin reserva ni backorder.

## FLOW C — Crédito aprobado

`S: 10 / 0 / 10`, política 045 exige aprobación para el cliente.

| Paso | Actor | Acción | Pedido | Reserva | Saldo | Auditoría |
|---|---|---|---|---|---|---|
| 1 | Vendedor | Confirma | **SUBMITTED** | `R: ACTIVE 8`, `expires_at = now + ttl` si la empresa configuró TTL; si no, `NULL` | 10/8/2 | `RESERVATION_CREATED` |
| 2 | Sistema | 045 abre solicitud `SALES_CREDIT` | **CREDIT_PENDING** | sin cambio | 10/8/2 | 045 |
| 3 | Aprobador (`ventas:approve`) | Aprueba en 045 | CREDIT_PENDING | sin cambio | 10/8/2 | 045 |
| 4 | Sistema | `ensure_approved` pasa | **APPROVED → RELEASED** | `expires_at := NULL` (reserva firme) | 10/8/2 | `SALES_ORDER_TRANSITIONED` |
| 5+ | | Flow A pasos 4-5 | | | | |

Durante 2-3 otro vendedor ve `available = 2`: **no puede comprometer las 8 unidades** (E1).

## FLOW D — Crédito rechazado

Desde Flow C paso 2.

| Paso | Actor | Acción | Pedido | Reserva | Saldo | Auditoría |
|---|---|---|---|---|---|---|
| 3 | Aprobador | Rechaza en 045 | CREDIT_PENDING | sin cambio | 10/8/2 | 045 |
| 4 | Sistema | Transición | **REJECTED** (terminal) | `R: RELEASED` (`release_reason = CREDIT_REJECTED`) | **10/0/10** | `RESERVATION_RELEASED` en la **misma transacción** que la transición |

Rechazo y liberación son atómicos: no existe un instante con pedido `REJECTED` y reserva `ACTIVE`.
Reintentar la transición → `409` por máquina de estados; no hay segunda liberación.

## FLOW E — Pedido modificado

Desde Flow C paso 2 (pedido `CREDIT_PENDING` con reserva de 8; el cliente ahora quiere 12).

| Paso | Actor | Acción | Pedido | Reserva | Saldo | Auditoría |
|---|---|---|---|---|---|---|
| 3 | Vendedor (`ventas:submit`, con motivo) | **Revertir a borrador** | **DRAFT** | `R: RELEASED` (`release_reason = ORDER_REVERTED`) | 10/0/10 | `RESERVATION_RELEASED` + `SALES_ORDER_REVERTED{reason}` |
| 3' | Sistema | 045 `document_changed` → solicitud `OBSOLETE` | DRAFT | — | — | 045 |
| 4 | Vendedor | Edita: cantidad 12, o quita línea, o cambia producto, o cambia almacén | DRAFT | — | 10/0/10 | — |
| 5 | Vendedor | Confirma de nuevo | SUBMITTED o `409 INSUFFICIENT_AVAILABLE` (12 > 10) | `R: ACTIVE` nueva | según disponibilidad **actual** | `RESERVATION_CREATED` |

Reglas derivadas (todas por el mismo camino, sin deltas):

| Cambio | Efecto |
|---|---|
| Aumenta cantidad | libera todo, re-reserva la nueva cantidad al reemitir; puede fallar |
| Disminuye | libera todo, re-reserva la menor |
| Elimina línea | libera todo, re-reserva las restantes |
| Cambia producto | libera todo, re-reserva el nuevo |
| Cambia almacén | libera todo en `W1`, re-reserva en `W2` al reemitir |
| Modificación tras aprobación | mismo camino; la aprobación queda `OBSOLETE` y se vuelve a solicitar (045) |
| Modificación en `PREPARING` o posterior | **no permitida**: el pedido está en manos del almacén (031/032 definen incidencia) |

No existe `PATCH` de líneas sobre pedidos no `DRAFT`: `add_order_line` sobre otro estado → `409 ORDER_NOT_EDITABLE`.

## FLOW F — Pedido cancelado

Desde cualquier estado vivo (`SUBMITTED`, `CREDIT_PENDING`, `APPROVED`, `RELEASED`, `PREPARING`).

| Paso | Actor | Acción | Pedido | Reserva | Saldo | Auditoría |
|---|---|---|---|---|---|---|
| 1 | Vendedor/supervisor (`ventas:submit` o `ventas:approve`, con motivo) | Cancela | **CANCELLED** | toda `R: ACTIVE` → `RELEASED` (`release_reason = ORDER_CANCELLED`) | reservado −8 | `RESERVATION_RELEASED` × línea + `SALES_ORDER_TRANSITIONED{reason}` |
| 2 | Cualquiera | Cancela otra vez | `409` (terminal) | sin cambio | sin cambio | — |

Atomicidad: transición y liberaciones en una transacción. Idempotencia: la liberación ignora filas
que ya no están `ACTIVE`; `qty_reserved` nunca baja de 0. En `PREPARING`, las cantidades ya en
estado de custodia `PICKING` las devuelve 032 con su propio movimiento; 030 libera solo lo `ACTIVE`.
Hoy: cancelar **no libera** (CD-05) y no está permitido desde `SUBMITTED`/`CREDIT_PENDING`.

## FLOW G — Dos pedidos concurrentes

`S: 10 / 0 / 10`. Pedido A (8) y pedido B (8) confirmados en el mismo instante por dos vendedores.

| t | Transacción A | Transacción B | Saldo (comprometido) |
|---|---|---|---|
| 1 | `SELECT … FOR UPDATE` fila `(W1, producto, DISPONIBLE)` → **obtiene el bloqueo** | `SELECT … FOR UPDATE` → **espera** | 10/0/10 |
| 2 | lee `available = 10`; 8 ≤ 10 | (esperando) | |
| 3 | inserta `R_A ACTIVE 8`; `reserved = 8`; pedido A `SUBMITTED`; **COMMIT** | (esperando) | 10/8/2 |
| 4 | | obtiene el bloqueo; **relee** `available = 2`; 8 > 2 | |
| 5 | | `409 INSUFFICIENT_AVAILABLE`; **ROLLBACK**; pedido B sigue `DRAFT` | 10/8/2 |

Resultado: `reserved = 8`, nunca 16. Quién gana lo decide el orden de adquisición del bloqueo
(orden de compromiso). Ver `d0-03-reservation-concurrency-analysis.md` para la fila inexistente, el
orden de bloqueo con varias líneas y la prueba obligatoria.

## FLOW H — Reserva parcial

**No aplica: prohibida.** Un pedido con dos líneas (8 de P1 con disponible 10, 5 de P2 con
disponible 3) **no** confirma: `409` con detalle de la línea P2, y P1 no queda reservada. La
atomicidad es por pedido, no por línea.

## FLOW I — Reserva expirada

Solo si la empresa configuró `reservation_ttl_days = N`. Desde Flow C paso 2, sin resolución de
crédito durante N días.

| Paso | Actor | Acción | Pedido | Reserva | Saldo | Auditoría |
|---|---|---|---|---|---|---|
| 1 | Operador (`POST /inventory/reservations/expire`, existente) o planificador (Spec 047 cuando exista) | Ejecuta expiración de la empresa | **EXPIRED** (terminal, nuevo valor introducido por 030) | `R: EXPIRED` | 10/0/10 | `RESERVATION_EXPIRED` + `SALES_ORDER_TRANSITIONED{EXPIRED}` en la misma transacción |
| 2 | Vendedor | Quiere retomar | crea un pedido nuevo (o 030 ofrece «duplicar como borrador») | — | — | — |

Invariante: **nunca queda un pedido vivo sin reserva**. Por eso expirar la reserva expira el pedido.
Un pedido `APPROVED`/`RELEASED` no expira: al aprobarse, `expires_at := NULL`.
Con TTL desactivado (defecto) este flujo no existe y no hay planificador que echar en falta.

## FLOW J — Handoff a picking

| Paso | Spec | Qué ocurre | Estado del pedido | Datos que 031 recibe |
|---|---|---|---|---|
| 1 | 030 | `APPROVED → RELEASED` | **RELEASED** | pedido, almacén, líneas con `base_quantity`, `presentation`, lote/serial si la línea los fijó; filas `Reservation ACTIVE` con `source_line_id` |
| 2 | 031 | Encola y ordena por ubicación; asigna ubicaciones | RELEASED → (031 define) | — |
| 3 | 032 | Extrae; mueve custodia `DISPONIBLE → PICKING` por ubicación/lote; faltante → libera diferencia y abre incidencia (**nunca ajusta el pedido en silencio**) | PREPARING | — |
| 4 | 033 | Confirmación independiente | CONFIRMED → READY_FOR_BILLING (ADR-D0-012) | — |
| 5 | 035 | Salida física; reserva `FULFILLED` | SHIPPED | — |

030 **no** crea `PickList`, **no** elige ubicación, **no** elige lote/serial, **no** cambia el estado
de custodia de la mercancía. La reserva es un contador sobre `DISPONIBLE`; el estado de custodia
`RESERVADO`/`PICKING` del catálogo ADR-D0-010 lo escribe la cadena de preparación cuando la mercancía
se aparta físicamente.
