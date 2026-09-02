# D0-03 — COMPORTAMIENTO ACTUAL DE LA RESERVA (AUDITORÍA FORENSE)

| Campo | Valor |
|---|---|
| Checkpoint | D0-03 — Reservation Timing Business Decision Checkpoint |
| Fecha | 2026-09-02 |
| Baseline auditada | `740a9d5` (`SPEC 029 — COMPLETE / CONVERGED`) |
| Método | Lectura del código, del modelo, de las pruebas y de los contratos vigentes. Nada de lo que sigue se infiere: cada afirmación cita el archivo que la sostiene |
| Regla del ciclo | **Lo existente no es lo correcto.** Esta auditoría describe; no decide |

## Current trigger

La reserva nace en `transition_order` (`resources/backend/app/modules/sales/service.py`) cuando el
destino es `APPROVED`:

```
if target == "APPROVED":
    approvals_integration.ensure_approved(...)
...
if target == "APPROVED":
    order.approval_ref = approval_ref or order.approval_ref
    _reserve_order(db, order, actor)
    order.status = "RESERVED"
```

Es decir: **después de la aprobación de crédito**, y en la misma llamada el pedido salta a `RESERVED`.
El estado `APPROVED` no es observable: se asigna y se sobrescribe antes del `flush`.

Máquina de estados vigente (`ORDER_TRANSITIONS`, `sales/service.py:76-87`):

```
DRAFT → SUBMITTED → CREDIT_PENDING → APPROVED → RESERVED → PREPARING → SHIPPED → CLOSED
SUBMITTED → REJECTED · CREDIT_PENDING → REJECTED
APPROVED | RESERVED | PREPARING → CANCELLED · DRAFT → CANCELLED
```

Observaciones sobre el disparador:

- No existe camino `SUBMITTED → APPROVED`: todo pedido, a crédito o de contado, pasa por
  `CREDIT_PENDING`. Sin política de aprobación configurada (Spec 045), `require_for_document`
  devuelve `requires_approval: False` y `ensure_approved` no bloquea; el paso es formal.
- Ningún pedido de contado reserva antes que uno a crédito: ambos reservan en `APPROVED`.
- `SUBMITTED` y `CREDIT_PENDING` **no admiten `CANCELLED`**, solo `REJECTED`.
- La ruta `POST /sales/orders/{id}/transition` exige `ventas:approve` para **todas** las
  transiciones, incluida `DRAFT → SUBMITTED`. Emitir un pedido y aprobarlo comparten permiso.
- Nadie decidió este punto. `ADR-D0-003` v1 lo dice textualmente: «es donde quedó».

## Current persistence

Modelo `Reservation` (`resources/backend/app/modules/inventory/models.py:153-175`):

| Columna | Tipo | Observación |
|---|---|---|
| `company_id` | FK `companies` | Entidad directa de alcance COMPANY |
| `source_document` | `String(200)` nullable | Texto libre `SALES_ORDER:{order.id}`; **sin FK, sin línea, sin unicidad** |
| `product_id`, `warehouse_id` | FK | Dimensión mínima |
| `lot_id`, `serial_id` | `String(36)` nullable | Sin FK; el pedido nunca los envía |
| `quantity` | `Numeric(18,6)` | Recibe `line.quantity` **tal como se tecleó** |
| `status` | `ACTIVE / RELEASED / EXPIRED / FULFILLED` | `FULFILLED` está en el comentario y **nadie lo escribe** |
| `expires_at` | nullable | El pedido nunca lo informa |
| `uom_id`, `presentation_id`, `conversion_factor_snapshot`, `base_quantity`, `uom_source` | Spec 011 | Existen desde `R-D0-09-1`; **el camino de ventas no los rellena** |
| `location_id` | — | **No existe** (R-D0-03-5 v1 lo pedía) |

Servicio `reserve` (`inventory/service.py:669-697`):

1. valida `quantity > 0`, almacén y producto de la empresa;
2. lee `available = get_available(...)` sobre el saldo `DISPONIBLE` sin `location_id`;
3. si `quantity > available` y el almacén no tiene `policies.allow_negative` → `409 INSUFFICIENT_AVAILABLE`;
4. inserta la fila `ACTIVE`;
5. `balance.qty_reserved += quantity` y `qty_available = qty_on_hand − qty_reserved`.

Los pasos 2 y 5 son una lectura y una escritura separadas **sin bloqueo de fila**. Dos transacciones
concurrentes leen el mismo disponible y ambas insertan.

Autoridad de saldos: `InventoryBalance` (`inventory/models.py:124-150`) es una proyección
reconstruible desde `InventoryMovement` (FR-003-010). `qty_reserved` **no** se reconstruye desde
movimientos: lo mantiene `reserve`/`release_reservation`/`expire_reservations` de forma incremental.
No hay restricción de unicidad sobre la clave del saldo (`company, warehouse, location, product, lot,
serial, state`): `_get_balance` hace *select-then-insert*.

`_reserve_order` (`sales/service.py`):

```
if not order.warehouse_id:
    return
```

Un pedido sin almacén **queda en `RESERVED` sin reservar nada**. Silenciosamente.

Reserva por línea: se reserva `line.quantity` por cada línea con `needs_inventory`, con
`source_document` idéntico para todas las líneas del pedido. No hay vínculo línea → reserva.

## Current release

| Evento | ¿Libera? | Evidencia |
|---|---|---|
| Confirmar despacho | Sí: `release_reservation` sobre toda reserva `ACTIVE` con `source_document == SALES_ORDER:{id}` → **`RELEASED`**, no `FULFILLED` | `sales/service.py:611-619` |
| Cancelar pedido (`→ CANCELLED`) | **No.** La transición cambia el estado y audita; las reservas quedan `ACTIVE` para siempre | `transition_order`: no hay rama de liberación |
| Rechazo de crédito (`→ REJECTED`) | No aplica hoy (la reserva nace después del crédito) | — |
| Expiración | Solo si alguien llama `POST /inventory/reservations/expire`; el pedido nunca fija `expires_at`, así que **ninguna reserva de pedido puede expirar** | `expire_reservations`, `inventory/api.py` |
| Liberación manual | `POST /inventory/reservations/{id}/release` con permiso `inventario:reserve`; **sin motivo, sin auditoría**, y también sobre reservas de pedidos | `inventory/api.py:376` |
| Modificación del pedido | `add_order_line` **no comprueba el estado**: se puede añadir una línea a un pedido `RESERVED` y esa línea no reserva | `sales/service.py:462` |
| Cambio de almacén / cantidad / producto | No existe operación de edición de líneas ni de cabecera tras `DRAFT`; tampoco existe «volver a borrador» | ausencia en `sales/api.py` |

Ninguna operación de reserva, liberación o expiración del módulo de inventario escribe en la
auditoría (`_audit` no aparece entre `inventory/service.py:640-740`). La única traza es
`SALES_ORDER_TRANSITIONED` con `{"target": "RESERVED"}`.

## Current defects

Se listan como hechos del código, no como decisiones. Cuál de ellos es defecto y cuál es
comportamiento a preservar lo determina `d0-03-reservation-decision.md`.

| # | Hecho | Consecuencia |
|---|---|---|
| CD-01 | Reserva tras aprobación de crédito, sin decisión registrada | Ventana `SUBMITTED → APPROVED` con stock libre: dos vendedores pueden comprometer la misma unidad (control explícito del DOCX Pedido §1) |
| CD-02 | `_reserve_order` retorna en silencio sin almacén | Pedido `RESERVED` sin reserva; el almacén asumirá compromiso inexistente |
| CD-03 | `reserve` lee y escribe sin bloqueo | Sobre-reserva por carrera; `reserved` puede superar `on_hand` sin política |
| CD-04 | Sin unicidad en `inventory_balances` | Dos transacciones pueden crear dos filas de saldo para la misma clave |
| CD-05 | Cancelar no libera | Reservas huérfanas `ACTIVE`; disponible reducido de forma permanente |
| CD-06 | Despacho marca `RELEASED` en vez de `FULFILLED` | Imposible distinguir «se liberó» de «se consumió» (contradice R-D0-03-7) |
| CD-07 | Cantidad reservada = cantidad tecleada; campos Spec 011 vacíos | Una línea en presentación (caja ×12) reserva 1 en vez de 12 unidades base |
| CD-08 | `source_document` texto libre, sin línea, sin unicidad | Idempotencia dependiente de la máquina de estados; auditoría por línea imposible |
| CD-09 | `expires_at` nunca informado; sin planificador | R-D0-03-4 v1 («toda reserva tiene vigencia») no se cumple ni puede cumplirse |
| CD-10 | `add_order_line` sin control de estado | Líneas no reservadas en pedidos reservados |
| CD-11 | Liberación manual sin motivo ni auditoría, aplicable a reservas de pedidos | Un pedido vivo puede quedar sin reserva sin rastro |
| CD-12 | `ventas:approve` para toda transición | El vendedor que emite necesita permiso de aprobador |
| CD-13 | Sin evento de auditoría en 003 para reservar/liberar/expirar | No se puede responder quién, cuándo, cuánto, por qué |
| CD-14 | `APPROVED` no observable | Estado declarado en FR-005-011 que nunca existe en datos |

## Current tests

| Prueba | Qué cubre | Qué no cubre |
|---|---|---|
| `tests/test_sales.py::test_order_state_machine_and_reserve` | Stock 100, línea 30, `SUBMITTED → CREDIT_PENDING → APPROVED`, disponible 70, estado `RESERVED` | Cancelación, insuficiencia, sin almacén, presentación, carrera |
| `tests/test_inventory.py::test_reserve_reduces_available_without_physical_change` | Reserva no mueve físico | — |
| `tests/test_inventory.py::test_over_reservation_rejected` | `409` por encima del disponible **en una sola sesión** | Carrera entre sesiones |
| `tests/test_spec029_quote_order.py::test_convertir_no_reserva_inventario` | Convertir cotización no reserva (frontera 029) | — |
| `tests/test_idempotency_concurrency.py` (6 casos) | Idempotencia de pagos, movimientos, transiciones dobles | **Ninguno reserva de forma concurrente** |

No existe prueba de: dos transacciones sobre la última unidad; cancelación libera; rechazo de
crédito; expiración de reserva de pedido; cantidad base en presentación; pedido sin almacén;
reserva entre empresas por la ruta de ventas.

## Contract alignment

| Contrato | Dice | Código | Alineación |
|---|---|---|---|
| FR-003-013 | Disponible = físico − reservas (salvo política de sobreadjudicación) | `qty_available = on_hand − reserved`; `allow_negative` por almacén | ✔ (sin «bloqueado»: los estados no disponibles viven en otras filas de saldo, así que la fórmula sobre la fila `DISPONIBLE` es equivalente) |
| FR-003-040 | `Reservation`: documento origen, producto, almacén, lote/serial, cantidad, estado, vencimiento | Modelo | ✔ estructural, ✘ semántico (origen texto libre) |
| FR-003-041 | «Reserva: orden aprobada → cantidad reservada» | Reserva en `APPROVED` | ✔ literal — **pero FR-003-041 recogía el estado del código, no una decisión**; queda superado por este checkpoint |
| FR-003-042 | No superar disponible salvo política | Comprobación sin bloqueo | △ verdadero en serie, falso bajo concurrencia |
| FR-003-043 | Liberación por cancelación, vencimiento, política | Solo despacho y manual | ✘ |
| FR-005-001 | Cotización no reserva | `convertir_en_pedido` y cotización no reservan | ✔ (probado en 029) |
| FR-005-011 | Máquina `DRAFT → … → RESERVED → …` | Idéntica | ✔ literal, con `APPROVED` fantasma |
| FR-005-020 | Aprobar la OV → reservar vía 003 | Idéntico | ✔ literal — mismo caso que FR-003-041: **describe, no decide** |
| SU-005-04 | Líneas de servicio no reservan | `needs_inventory` | ✔ |
| ADR-D0-003 v1 R-D0-03-1 | Disparador configurable, defecto `ORDER_RELEASED` | Fijo en `APPROVED`, sin configuración | ✘ |
| R-D0-03-3 | Bloqueo de fila + restricción | Ninguno | ✘ |
| R-D0-03-4 | Toda reserva tiene vigencia | Ninguna la tiene | ✘ |
| R-D0-03-5 | Mínima dimensión conocida (lote/serial/ubicación) | Solo almacén | △ (el pedido no conoce más) |
| R-D0-03-6 | Idempotente por documento origen | Solo por máquina de estados | △ |
| R-D0-03-7 | Consumo en salida física | Despacho «libera» | ✘ semántico |
| POL-D0-002 §6 | Cancelación libera | No | ✘ |
| ARCH-MC-001 | Contexto de empresa es la autoridad | `reserve` recibe `company_id` del pedido cargado por contexto; la ruta manual usa `ctx.company_id` | ✔ |
| Spec 011 / R-D0-09-1 | Cantidad base con factor snapshot | La ruta de ventas no la usa | ✘ |
| FR-029-035/036 | 029 no reserva ni decide D0-03 | Cumplido | ✔ |

## Clasificación

**Legacy, parcial, no contractual.** La lógica actual reserva en un punto que nadie decidió, sin
concurrencia, sin liberación por cancelación, sin cantidad base, sin vigencia, sin auditoría y sin
vínculo con la línea. Es una capacidad del motor de 003 (`reserve`/`release`/`expire`) invocada desde
ventas en el lugar equivocado y sin las garantías que sus propios contratos exigen.

Lo que **sí** es contractual y se preserva: el motor de reservas vive en 003 (CL-005-03), la
disponibilidad es `on_hand − reserved` sobre `DISPONIBLE` (FR-003-013, R-D0-10-3), la cotización
no reserva (FR-005-001), la conversión no reserva (FR-029-035) y la sobreadjudicación solo existe
por política explícita de almacén (FR-003-042).
