# D0-03 — ESTADO DE LA DECISIÓN AL ABRIR EL CHECKPOINT

| Campo | Valor |
|---|---|
| Fecha | 2026-09-02 |
| Estado declarado de partida | `D0-03 — RESERVATION TIMING — BUSINESS DECISION PENDING` · `SPEC 030 — BLOCKED_BY_BUSINESS_DECISION` |
| Estado documental encontrado | `ADR-D0-003` v1 **APPROVED** · `CLOSED_WITH_CONFIGURATION_PENDING` (2026-08-29) |
| Conclusión de esta sección | Ambos estados eran ciertos a la vez porque describían cosas distintas. Se reconcilian aquí |

## 1. Lo que D0-03 ya había decidido (2026-08-29)

`ADR-D0-003` v1 y `POL-D0-002` cerraron **arquitectura**:

| Regla v1 | Contenido | Estado tras esta auditoría |
|---|---|---|
| R-D0-03-1 | Disparador configurable por empresa ∈ {`ORDER_RELEASED` (defecto), `ORDER_CREATED`, `CREDIT_APPROVED`, `QUOTE_APPROVED`, `MANUAL`} | **Ambigua y no implementable sin decisión adicional** (ver §3) |
| R-D0-03-2 | `disponible = físico − reservado − bloqueado` | Vigente |
| R-D0-03-3 | Bloqueo de fila + restricción contra `reservado > físico` | Vigente; se precisa (la restricción no puede ver la política de almacén) |
| R-D0-03-4 | Toda reserva tiene vigencia; duración por empresa | **Ambigua**: sin defecto ni dueño del planificador |
| R-D0-03-5 | Mínima dimensión conocida | Vigente; se delimita frente a picking |
| R-D0-03-6 | Idempotente por documento origen | Vigente; se precisa a nivel de línea |
| R-D0-03-7 | Consumo en salida física, no en facturación | Vigente |

Y dejó abiertas, como **BUSINESS_VALIDATION_REQUIRED**:

- OQ-03: ¿qué disparador usa el cliente?, ¿cuánto dura una reserva?, ¿cómo se prioriza entre pedidos?
- OQ-04: ¿backorder y sustitución entran en 030? — ya respondida: **FUTURE**.

## 2. Por qué Master 56 la registró como pendiente

El checkpoint maestro (`docs/roadmap/master-56-specs-status.md`, 2026-08-31) clasificó 030 como
`BLOCKED_BY_BUSINESS_DECISION` con la pregunta «¿Se reserva al pedido o al crédito aprobado?».
Tenía razón en el fondo aunque contradijera la etiqueta del registro D0: **un disparador
"configurable" cuyo valor concreto nadie ha elegido no es un contrato implementable**. La Spec 030
no podía escribir una máquina de estados sobre cinco disparadores posibles con semánticas de
liberación distintas cada uno.

La contradicción, por tanto, no era de estado sino de **granularidad**: D0-03 v1 cerró «que exista
política con defecto»; Master 56 exigía «cuál es la política». Este checkpoint cierra lo segundo.

## 3. La ambigüedad material de la v1: qué significa «liberar el pedido»

`ADR-D0-003` v1 define el defecto `ORDER_RELEASED` como «al liberar/emitir el pedido: el primer
punto de la cadena con compromiso comercial formal y documento no editable», y a la vez dice que
«el análisis de crédito ocurre **antes** de liberar, no después de reservar».

En la máquina de estados real (`DRAFT → SUBMITTED → CREDIT_PENDING → APPROVED → RESERVED`)
esas dos frases señalan **estados distintos**:

| Lectura | Estado en KONTROL | Equivale a la opción del checkpoint |
|---|---|---|
| «emitir el pedido, documento no editable» | `SUBMITTED` | **B — Order Confirmation** |
| «después del análisis de crédito, liberado para preparación» | `APPROVED`/`RESERVED` | **C/D — Credit Approval / Release** |

Además, `ADR-D0-012` ya usa «confirmación» para la **confirmación independiente de preparación**
(Spec 033), lo que añade una tercera colisión de nombres.

Esta ambigüedad es exactamente el hueco que Master 56 detectó y que este checkpoint resuelve con
nombres atados a transiciones concretas (ver `d0-03-reservation-decision.md` §0).

## 4. Autoridad de inventario vigente

| Magnitud | Autoridad | Dónde | Observación |
|---|---|---|---|
| `on_hand` (físico) | `InventoryMovement` (ledger) → proyección `InventoryBalance.qty_on_hand` | `inventory/service.py::record_movement`, `recompute_balances` | Reconstruible (FR-003-010/011) |
| `reserved` | Filas `Reservation` `ACTIVE` → contador `InventoryBalance.qty_reserved` | `reserve`, `release_reservation`, `expire_reservations` | **No reconstruible hoy**: el contador se mantiene a mano; las filas son el ledger de hecho |
| `available` | `InventoryBalance.qty_available = on_hand − reserved` de la fila `state = DISPONIBLE` | `get_available`, `_refresh_available` | Los estados no vendibles (ADR-D0-010) son otras filas: no entran en la resta y por eso la fórmula equivale a `físico − reservado − bloqueado` |
| Warehouse | `SalesOrder.warehouse_id` (nullable) | `sales/models.py:113` | Un almacén por pedido; empresa del almacén validada por `_require_warehouse` |
| Location | `InventoryBalance.location_id` FK (Spec 008) | siempre `None` en reserva | La reserva ignora la ubicación; nadie la conoce al vender |
| Lot / serial | `Reservation.lot_id/serial_id` texto | nunca informados desde ventas | Selección específica no existe antes del picking |
| Estados de mercancía | catálogo ADR-D0-010 (15 estados) | `InventoryBalance.state` | Solo `DISPONIBLE` es vendible (R-D0-10-3). `RESERVADO` como **estado** existe en el catálogo pero **nadie lo escribe**: hoy la reserva es un contador sobre `DISPONIBLE` |

Hay un solo motor de inventario (003). Este checkpoint no crea otro: precisa cómo 030 lo invoca.

## 5. Integración de crédito vigente

- Proceso `SALES_CREDIT` en el motor de aprobaciones (Spec 045, FR-045-071, R-D0-02-10).
- `require_for_document` abre solicitud **solo si una política la exige**; sin política:
  `requires_approval: False`, y `ensure_approved` no bloquea.
- No existe atributo «contado/crédito» en el pedido: lo que hay es `payment_term_snapshot` en las
  líneas (Spec 029) y la política de 045 evaluada sobre `_order_credit_context` (monto, moneda,
  cliente, lista). **«Pedido de contado» en KONTROL = pedido para el que 045 no abre solicitud.**
- El rechazo (`REJECTED`) es terminal y hoy no libera nada porque nada hay reservado en ese punto.

## 6. Qué entrega 029 y qué espera 031

- 029: `SalesOrder` nace en `DRAFT` con origen comercial completo; ni la cotización ni la conversión
  reservan (probado). Este límite se preserva.
- 031/032 (bloqueadas por 022): asumen **reserva firme** al entrar en cola. `pick_list_lines`
  carece de ubicación y secuencia. Nada de eso es de 030.

## 7. Lo que sigue siendo material al abrir el ciclo

| Pregunta | ¿Material? | Cómo se resuelve |
|---|---|---|
| ¿Cuál es el disparador? | **Sí** | Análisis de opciones A–F sobre evidencia (`d0-03-reservation-options.md`) |
| ¿Único o configurable? | **Sí** | Ídem; §8 del prompt |
| ¿Vigencia: defecto y dueño? | **Sí** | Decisión de producto con defecto; dueño del planificador identificado |
| ¿Prioridad entre pedidos? | **Sí** | Criterio determinista o dueño explícito |
| ¿Parcial / backorder / sobreventa? | **Sí** | Decisión explícita |
| ¿Modificación / cancelación / rechazo? | **Sí** | Reglas por evento |
| ¿Qué cliente concreto lo usa? | **No** | Es configuración de implantación **solo** si el disparador es configurable; si es fijo, la pregunta desaparece |

Todas se cierran en `d0-03-reservation-decision.md`. Ninguna requiere a un tercero: la evidencia
(DOCX Pedido §1, contratos 003/005/011/045, cadena 031–033, riesgo de carrera) es suficiente para
que el producto decida su semántica, igual que decidió la de cotizaciones, aprobaciones o estados de
mercancía.
