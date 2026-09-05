# SPEC 031 — COLA Y RUTA DE PICKING · CICLO DE IMPLEMENTACIÓN POST `D0-15`

> 2026-09-05, sobre `5bb2f8f`. Reanudación productiva de la **misma** Spec 031 tras el cierre de
> `D0-15`. Consume las 22 reglas `R-D0-15-*` sin reabrirlas.

## 1. `/speckit.specify` — qué construye este ciclo

La Spec 031 planifica: decide **de qué ubicación** se recoge **cuánto** de cada línea de un pedido
liberado, y **en qué orden se recorre el almacén**. No recoge nada: eso es la Spec 032.

| Capacidad | Estado antes | Este ciclo |
|---|---|---|
| Cola de preparación | no existe | `GET /sales/picking/cola` |
| Asignación por ubicación | no existe | `PickListLine` con `location_id`, `state` y `sequence` |
| Cantidad asignable localizada | no existe | ubicado vendible − asignaciones activas |
| Ruta | Spec 008 la tiene | se **consume**, no se reimplementa |
| Ciclo de vida del plan | solo `DRAFT` escrito | cinco estados con `CHECK` |
| Compuerta de confirmación | no existe | remanente 0 obligatorio |
| Cancelación / invalidación | no existe | con liberación de asignaciones |

## 2. `/speckit.clarify` — lo medido antes de escribir código

| # | Pregunta | Respuesta medida |
|---|---|---|
| 1 | ¿Qué entidad de plan existe? | `PickList` (`sales/models.py:191`) y `PickListLine` (`:201`), creadas en `0005_ventas.py` |
| 2 | ¿Tiene ubicación o secuencia? | **No**. Por eso hoy no puede expresar «recoge esto de aquí» |
| 3 | ¿Vincula la línea del pedido? | **No**. Solo `product_id` suelto |
| 4 | ¿Quién llama `create_picklist`? | Únicamente `POST /sales/pick-lists`. **Ninguna prueba** |
| 5 | ¿Qué estados escribe alguien? | Solo `DRAFT`. Nadie escribe `CONFIRMED` ni `CLOSED` |
| 6 | ¿Hay `CHECK` de estado? | No |
| 7 | ¿Cómo se identifica la demanda de una línea? | `Reservation` con `source_line_id`, `status='ACTIVE'`, con `base_quantity` |
| 8 | ¿Cuál es la identidad física? | `InventoryBalance`: empresa, almacén, **ubicación**, producto, lote, serial, estado |
| 9 | ¿Existe disponible por almacén? | Sí, `warehouse_sellable_on_hand` (Spec 022). Falta el equivalente **por ubicación** |
| 10 | ¿Quién escribe `released_at`? | `_a_released` (`sales/service.py:599-607`), en la misma transacción que hace firme la reserva |
| 11 | ¿`create_picklist` mueve el pedido? | Sí, a `PREPARING`, **al crear el `DRAFT`**. Contradice `R-D0-15-18` |
| 12 | ¿Existe `PREPARING → RELEASED`? | **No**. `PREPARING → {SHIPPED, CANCELLED}` |
| 13 | ¿Hay frontend? | `DespachoPage.tsx` lista planes y crea uno sin líneas. No planifica |
| 14 | ¿Permisos necesarios? | `ventas:view` y `ventas:create`, **ambos ya en el catálogo**. Cero permisos nuevos |
| 15 | ¿Autoridad de ruta? | `physical_order_query()` (Spec 008, `FR-008-033`) |
| 16 | ¿Nueva pregunta material? | **No** |

### Por qué no se crea una tabla de asignaciones

`PickListLine` **es** la asignación en cuanto se le añaden ubicación, estado y secuencia: una línea
de pedido repartida entre dos ubicaciones son dos `PickListLine`. Crear una tabla aparte duplicaría
la identidad sin añadir nada, y `§29` pide auditar antes de crear.

### Por qué el remanente se deriva y no se persiste

`requerido − asignado` es aritmética sobre datos que ya existen —la reserva activa y las líneas del
plan—. Persistirlo crearía una tercera cifra capaz de discrepar de las otras dos. Se expone en la
API, no se guarda.

### Por qué la asignación activa se deriva del estado del plan

Una asignación está activa **si y solo si** su plan está en `DRAFT` o `CONFIRMED`. Un estado propio
por línea sería una segunda verdad que podría contradecir al plan que la contiene.

## 3. `/speckit.plan` — modelo de datos

**Migración `0049_spec031_picking_plan`.**

`pick_lists`:

| Columna | Tipo | Nota |
|---|---|---|
| `status` | — | `CHECK` en `DRAFT, CONFIRMED, CLOSED, CANCELLED, INVALIDATED` |
| `confirmed_at` · `cancelled_at` · `invalidated_at` | timestamptz null | |
| `confirmed_by` | varchar(36) null | |
| `status_reason` | text null | exigido al cancelar e invalidar |
| índice único parcial | — | **un solo plan activo por pedido**: `(order_id) WHERE status IN ('DRAFT','CONFIRMED')` |

`pick_list_lines`:

| Columna | Tipo | Nota |
|---|---|---|
| `order_line_id` | FK `sales_order_lines` null | la demanda que satisface |
| `location_id` | FK `warehouse_locations` null | **nunca nula en una asignación real** |
| `state` | varchar(32) null | estado de mercancía; parea con el saldo |
| `sequence` | integer null | posición en el recorrido |
| `CHECK allocation_shape` | — | o los cuatro campos de asignación están, o ninguno |

Las columnas nacen anulables porque el esqueleto pudo crear líneas sin ubicación y **no se fabrica
historia en una migración**. El `CHECK` impide la forma a medias, y el servicio nunca crea una
asignación sin ubicación: `R-D0-15` y `§36` prohíben `location_id` nula como candidata.

## 4. Contratos

### Cola

```
GET /sales/picking/cola?warehouse_id=…
```

Elegibles: pedido `RELEASED` **y** con al menos una reserva `ACTIVE`.
Orden: `released_at ASC, id ASC`. Total, determinista, calculado en backend.
Nunca orden natural de PostgreSQL. Sin dimensión de prioridad.

### Candidatas

```
GET /sales/picking/{plan_id}/candidatas?order_line_id=…
```

Ubicaciones del almacén del pedido con existencia **vendible** (`SELLABLE_STATES`, `D0-10`),
`location_id` **no nula**, y `asignable > 0`, en orden físico de la Spec 008.

`asignable(ubicación) = qty_on_hand vendible en esa identidad − asignaciones activas en ella`

No se descuenta `qty_reserved`: el compromiso comercial es de almacén y ya está representado; restarlo
aquí lo contaría dos veces (`§33`).

### Asignar y desasignar

```
POST   /sales/picking/{plan_id}/asignaciones
DELETE /sales/picking/{plan_id}/asignaciones/{line_id}
```

Invariantes, verificados con la fila bloqueada:

1. `Σ asignaciones activas de la línea ≤ base_quantity de su reserva ACTIVE`
2. `Σ asignaciones activas de una identidad física ≤ existencia vendible localizada`
3. La ubicación pertenece al almacén del pedido y a la empresa del contexto
4. Cantidades en **unidad base**

### Confirmar

```
POST /sales/picking/{plan_id}/confirmar
```

Compuerta: remanente 0 en **todas** las líneas · pedido aún `RELEASED` · reservas aún `ACTIVE` ·
ubicaciones aún elegibles · ruta resuelta. Efecto: plan `CONFIRMED`, pedido `RELEASED → PREPARING`.

### Cancelar e invalidar

```
POST /sales/picking/{plan_id}/cancelar     (motivo obligatorio)
POST /sales/picking/{plan_id}/invalidar    (motivo obligatorio)
```

Ambos: plan terminal, asignaciones liberadas, **reserva comercial intacta**, existencia física
intacta. Si el plan estaba `CONFIRMED`, el pedido vuelve `PREPARING → RELEASED`.

`CLOSED` **no se escribe en este ciclo**: significa ejecución física terminada y su dueña es la
Spec 032. No se simula.

## 5. Deltas dirigidos sobre Ventas / Spec 030

Decididos por `D0-15`, no requieren un D0 nuevo. Trazados aquí antes del código.

| Delta | Defecto | Regla |
|---|---|---|
| **A** | `create_picklist` mueve el pedido a `PREPARING` al crear el `DRAFT` | `R-D0-15-18`: solo `CONFIRMED` lo mueve |
| **B** | `ORDER_TRANSITIONS` no tiene `PREPARING → RELEASED` | `R-D0-15-19`: cancelar antes de efecto físico devuelve el pedido a la cola |

No se declara la Spec 030 reabierta ni globalmente reconvergida: son dos deltas dirigidos con
convergencia dirigida.

## 6. Fuera de alcance, explícitamente

- Picking físico, consolidación, empaque: Spec 032.
- `CLOSED` por planificación: prohibido.
- FIFO, FEFO, prioridad de lote o serial: `R-D0-15-21`.
- Prioridad por cliente, manual, SLA o ruta: `D0-03` §8, siguen `FUTURE`.
- Algoritmo de ruta propio: la Spec 008 es la autoridad.
- La deuda de `uom.py` sobre estados inexistentes de `sales_orders`: **dueña Spec 011**, no se toca.

## 7. Invariantes que las pruebas deben ejercer

| Invariante | Qué se mide |
|---|---|
| Deriva física | `qty_on_hand` idéntico antes y después de `DRAFT`, `CONFIRMED`, `CANCELLED`, `INVALIDATED` |
| Deriva de reserva | `qty_reserved` idéntico; la 031 nunca lo escribe |
| Sin movimiento | cero `InventoryMovement` por planificar |
| Caja ×12 | 2 BOX → 24 base en reserva, asignación y traspaso. Nunca 2 |
| Solo vendible | `L1 DISPONIBLE 40` + `L2 CUARENTENA 100` → candidato 40 |
| Ubicación nula | nunca candidata |
| División | reserva 70 con `L1` 40 y `L2` 60 → 40 + 30 |
| Compuerta | 60 de 100 asignado → `CONFIRMED` rechazado |
| Concurrencia | dos transacciones asignando 70 sobre 100 → total ≤ 100 |
| TOCTOU | candidatas obsoletas revalidadas al enviar |
| Idempotencia | doble envío, un efecto |
| Multiempresa | usuario AB, matriz hostil de cadenas cruzadas |
