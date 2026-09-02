# D0-03 — DECISIÓN: POLÍTICA COMPLETA DE RESERVA DE INVENTARIO

| Campo | Valor |
|---|---|
| Fecha | 2026-09-02 |
| Estado | **DECIDIDA** — formalizada en `ADR-D0-003` v2 (ACTIVE) y `POL-D0-002` v2 |
| Base | `current-reservation-behavior.md` · `d0-03-reservation-current-state.md` · `d0-03-reservation-options.md` · `d0-03-reservation-flow-matrix.md` · `d0-03-reservation-concurrency-analysis.md` |
| Propietaria de la implementación | **Spec 030** (crédito / aprobación / reserva) sobre el motor de **003/023** |

## 0. Vocabulario fijado

| Término | Definición en KONTROL |
|---|---|
| **Stock físico** (`on_hand`) | Unidades presentes en el almacén en cualquier estado de custodia |
| **Stock disponible** (`available`) | `on_hand − reserved` de la fila de saldo en estado `DISPONIBLE`. Equivale a `físico − reservado − bloqueado` porque los estados no vendibles (ADR-D0-010) viven en otras filas |
| **Stock reservado** (`reserved`) | Unidades base comprometidas a líneas de pedido emitidas y aún no extraídas. Es un **contador** sobre `DISPONIBLE`, no un estado de custodia |
| **Stock en preparación** | Unidades cuyo estado de custodia pasó a `PICKING`/`PREPARADO` por 031/032. Fuera de 030 |
| **Stock despachado** | Salió físicamente (`DESPACHADO`/`VENDIDO`); la reserva quedó `FULFILLED` |
| **Stock en tránsito** | `TRANSITO` entre almacenes (Spec 025). **No reservable** en 030 |
| **Emisión / confirmación comercial del pedido** | Transición `DRAFT → SUBMITTED`. No confundir con la confirmación independiente de preparación (ADR-D0-012, Spec 033) |
| **Liberación a preparación** | Transición `APPROVED → RELEASED` (el actual `RESERVED`, renombrado). Entrada a la cola de 031 |

## 1. Decisión

> **RESERVATION TRIGGER = ORDER_CONFIRMATION**
>
> La reserva de inventario nace en la transición `DRAFT → SUBMITTED` del `SalesOrder`, de forma
> síncrona y dentro de la misma transacción. Es un disparador **fijo** del producto, idéntico para
> pedidos de contado, a crédito y sin evaluación de crédito. No es configurable por empresa.

Por qué (resumen de `options.md`): es el punto que el negocio señala («al emitir el pedido», DOCX
Pedido §1); es el primer estado con compromiso formal y documento no editable; el vendedor conoce la
insuficiencia **antes** de comprometer al cliente y la resuelve editando el borrador, lo que hace
innecesario el backorder en 030; para contado coincide en el tiempo con las demás opciones; para
crédito protege el stock durante la evaluación y el rechazo libera; es un único punto, una regla,
un evento. La opción del código actual (crédito aprobado) se rechaza por dejar abierta exactamente
la ventana que el control quiere cerrar y por no tener salida cuando el crédito se aprueba sin
stock.

## 2. Política completa

### A. Momento de creación
`DRAFT → SUBMITTED`. Ni antes (creación, conversión de cotización) ni después (crédito, liberación).
Las líneas con `needs_inventory = false` (servicios, SU-005-04) no reservan. La cotización nunca
reserva (FR-005-001). Las reservas **manuales** del motor de 003 (`POST /inventory/reservations`)
siguen existiendo con `trigger = MANUAL` y no están atadas a pedidos.

### B. Precondiciones de la confirmación
| Condición | Fallo |
|---|---|
| Pedido en `DRAFT` con al menos una línea | `409` máquina de estados / `422 ORDER_EMPTY` |
| Contexto de empresa = empresa del pedido | `404` (anti-divulgación, ARCH-MC-001) |
| `warehouse_id` informado si alguna línea necesita inventario | `422 WAREHOUSE_REQUIRED` — **el silencio actual desaparece** |
| Almacén pertenece a la empresa y está activo | `404 WAREHOUSE_NOT_FOUND` |
| Cada línea de inventario tiene `base_quantity` y `conversion_factor_snapshot` (Spec 011) | `422 UOM_NOT_RESOLVED` |
| Producto vendible y activo en la empresa | `422`/`404` según 002 |
| Actor con permiso de emisión (`ventas:submit`, que 030 separa del actual `ventas:approve`) | `403` |
| Disponible suficiente en base para **todas** las líneas, o almacén con `allow_negative` | `409 INSUFFICIENT_AVAILABLE` con detalle por línea |

### C. Prioridad
Orden de compromiso: la transacción que obtiene el bloqueo de la fila de saldo reserva primero.
Sin prioridad por cliente, sin prioridad manual, sin cola. Ambas son **FUTURE** y dependen de
backorder.

### D. Cantidad
- **Todo-o-nada por pedido.** Si una línea no alcanza, nada se reserva y el pedido sigue `DRAFT`.
- La cantidad comparada y reservada es la **cantidad base** de la línea (Spec 011). La reserva
  persiste además `quantity` tecleada, `uom_id`, `presentation_id`, `conversion_factor_snapshot`
  y `uom_source`, copiados de la línea; **no recalcula** con el factor vigente del catálogo.
- No hay reserva parcial: no existen `reserved_quantity < requested_quantity` ni `pending_quantity`.

### E. Almacén, ubicación, lote y serial
- Dimensión de la reserva: `(empresa, almacén del pedido, producto)`.
- **Un almacén por pedido** (`SalesOrder.warehouse_id`). Sin abastecimiento automático desde otro
  almacén: si `W1` no tiene y `W2` sí, la confirmación falla y el vendedor cambia el almacén del
  borrador (o divide el pedido). Pedido multi-almacén: FUTURE.
- La reserva **no** fija ubicación. Nunca. 031 asigna ubicaciones; 032 extrae.
- La reserva **no** elige lote ni serial, **salvo** que la línea del pedido los exija
  explícitamente (requisito del cliente): entonces la reserva lleva `lot_id`/`serial_id` y la
  disponibilidad se comprueba en esa dimensión. FEFO/FIFO y selección de serial son de 032/024.
- Solo consume saldo en estado `DISPONIBLE` (R-D0-10-3). Mercancía `RECIBIDO`,
  `PENDIENTE_CONFIRMACION`, `CUARENTENA`, `BLOQUEADO`, `TRANSITO` no es reservable.
- La reserva no cambia el estado de custodia. `RESERVADO` como estado del catálogo ADR-D0-010 queda
  para apartado físico (031/032), no para 030.

### F. Duración
La vida de la reserva es la vida del pedido. No existe vencimiento por reloj **por defecto**.
Configuración por empresa `reservation_ttl_days` (entero, `NULL` = desactivado, **defecto
`NULL`**): cuando está definida, las reservas de pedidos en `SUBMITTED`/`CREDIT_PENDING` nacen con
`expires_at = confirmación + N días`. Al pasar a `APPROVED`, `expires_at := NULL` (reserva firme).

### G. Expiración
Solo con TTL configurado. Efecto: reserva `EXPIRED` **y** pedido a estado terminal `EXPIRED` en la
misma transacción, con `RESERVATION_EXPIRED` y `SALES_ORDER_TRANSITIONED`. Invariante: nunca un
pedido vivo sin reserva. Ejecución: el endpoint existente `POST /inventory/reservations/expire`
(operador), que 030 hace consciente del pedido; ejecución periódica = **planificador de plataforma,
propietaria Spec 047 (Notificaciones y tareas)**. 030 no implementa worker. Con TTL desactivado
(defecto) no hay dependencia pendiente.

### H. Liberación
| Disparador | Efecto | Estado final de la reserva |
|---|---|---|
| Cancelación del pedido | libera todo lo `ACTIVE` | `RELEASED` (`ORDER_CANCELLED`) |
| Rechazo de crédito | libera todo | `RELEASED` (`CREDIT_REJECTED`) |
| Reversión a borrador | libera todo | `RELEASED` (`ORDER_REVERTED`) |
| Expiración (TTL) | libera todo + pedido `EXPIRED` | `EXPIRED` |
| Picking parcial (032) | libera la diferencia + incidencia | `RELEASED` parcial por nueva fila (032 define) |
| Despacho físico (035) | **consume** | `FULFILLED` — no `RELEASED` |
| Facturación (034) | ninguno | — |
| Cambio de almacén | vía reversión a borrador | `RELEASED` |
| Fallo de pago / pago no confirmado | **no aplica en 030** (tesorería 006 no condiciona la reserva) | — |

Liberación manual: **no permitida** sobre reservas de pedido (romperían el invariante); para dejar
un pedido sin reserva se cancela o se revierte el pedido. Permitida sobre reservas `MANUAL` con
permiso `inventario:reserve`, **motivo obligatorio** y auditoría. Re-reservar tras liberar = nueva
fila, nunca reactivación.

### I. Modificación
Un pedido es editable **solo en `DRAFT`**. Para cambiar cantidad, línea, producto o almacén de un
pedido emitido: transición `REVERT_TO_DRAFT` (desde `SUBMITTED`, `CREDIT_PENDING`, `APPROVED`,
`RELEASED`; **no** desde `PREPARING` o posteriores), con motivo, que libera toda la reserva y
declara obsoleta la solicitud de crédito (045 `document_changed`). Reemitir vuelve a reservar con la
disponibilidad de ese momento y vuelve a solicitar crédito si la política lo exige. La prioridad
anterior se pierde: es explícito y aceptado. No hay ajuste por diferencias. `add_order_line` sobre
un pedido no `DRAFT` → `409 ORDER_NOT_EDITABLE`.

### J. Cancelación
Permitida desde `DRAFT` (sin reserva), `SUBMITTED`, `CREDIT_PENDING`, `APPROVED`, `RELEASED` y
`PREPARING` (en este último, 032 deshace lo apartado con su movimiento; 030 libera lo `ACTIVE`).
Atómica con la transición; idempotente (segundo intento `409` terminal; liberación ignora filas no
`ACTIVE`); auditada con motivo.

### K. Insuficiencia y sobreventa
`available_base < requested_base` → **rechazo completo** (`409`). Sin parcial, sin backorder, sin
pedido sin reserva. Única excepción: almacén con `policies.allow_negative = true` (autoridad ya
existente, P8), en cuyo caso se reserva íntegramente, la fila lleva `oversell = true` y el evento
registra `available_before`. La sobreventa nunca es consecuencia de una carrera.

### L. Concurrencia e idempotencia
Contrato de `d0-03-reservation-concurrency-analysis.md` §3-§6: bloqueo de fila
`SELECT … FOR UPDATE` dentro de la transacción de confirmación; unicidad en la clave del saldo;
índice único parcial `(source_line_id) WHERE status = 'ACTIVE'`; `CHECK (qty_reserved >= 0)`;
prueba de carrera obligatoria en PostgreSQL; liberar dos veces es no-op.

### M. Backorder
**OUT_OF_SCOPE** en 030 (OQ-04 → FUTURE). El modelo lo admite sin rediseño: reserva por línea con
`base_quantity` permite calcular `pendiente = solicitado − reservado` cuando exista. 030 **no** debe
inventar estados ni colas de espera.

### N. Auditoría
Contrato en §7.

### O. Permisos y aislamiento
- Emitir/revertir/cancelar el pedido: `ventas:submit` (030 lo introduce separándolo de
  `ventas:approve`, que queda para crédito). La reserva es un **efecto del sistema** de esa
  transición: el vendedor no necesita `inventario:reserve`.
- Reserva y liberación manual: `inventario:reserve` (existente).
- El permiso nunca sustituye al contexto: la empresa de la reserva es la del pedido cargado bajo
  `CompanyContext`; el almacén se valida como perteneciente a esa empresa. Ver §6.

### P. Interacción con crédito (Spec 045)
La reserva **precede** al crédito. La aprobación no toca la reserva (solo limpia `expires_at`). El
rechazo la libera atómicamente. La obsolescencia de la aprobación solo ocurre por reversión a
borrador (que ya liberó). 030 integra `SALES_CREDIT` como hoy; no crea motor ni estados de
aprobación propios. El estado de pago no condiciona la reserva en 030.

### Q. Handoff a picking
El pedido en `RELEASED` (tras aprobación, o inmediatamente tras confirmación cuando 045 no abre
solicitud) es elegible para la cola de 031. 030 entrega: pedido, almacén, líneas con cantidad
base/presentación/lote-serial exigidos, y filas `Reservation ACTIVE` vinculadas por
`source_line_id`. 030 no crea `PickList` ni toca estados de custodia.

## 3. Tabla de decisión por tipo de operación

| Tipo de pedido | ¿045 abre solicitud de crédito? | Estado de pago | Trigger de reserva | Camino posterior |
|---|---|---|---|---|
| Contado / sin política de crédito aplicable | No | no evaluado en 030 | `ORDER_CONFIRMATION` | `SUBMITTED → APPROVED → RELEASED` en la misma transacción |
| A crédito con política aplicable | Sí | n/a | `ORDER_CONFIRMATION` | `SUBMITTED → CREDIT_PENDING`; aprobado → `APPROVED → RELEASED`; rechazado → `REJECTED` + liberación |
| Con política pero sin evaluación exigida (monto bajo umbral, etc.) | No (045 decide) | n/a | `ORDER_CONFIRMATION` | como contado |
| Solo líneas de servicio | cualquiera | — | **ninguno** | misma máquina, sin reserva |
| Cotización (029) | — | — | **nunca** | — |
| Reserva manual (003) | — | — | `MANUAL` | independiente del pedido |

## 4. Fijo vs. configurable

| Elemento | ¿Configurable? | Por quién | Defecto |
|---|---|---|---|
| Disparador | **No** | — | `ORDER_CONFIRMATION` |
| Reserva parcial | No | — | prohibida |
| Backorder | No | — | fuera de alcance |
| Prioridad | No | — | orden de compromiso |
| Dimensión | No | — | almacén (+ lote/serial si la línea lo exige) |
| Vigencia mientras se evalúa crédito | **Sí** | empresa (`reservation_ttl_days`) | `NULL` (sin expiración) |
| Sobreventa | **Sí** | almacén (`policies.allow_negative`) | `false` |
| Si un pedido requiere crédito | **Sí** | políticas de 045 | sin política = contado |

Esto **supera** R-D0-03-1 v1 («disparador configurable»). Un sistema recién instalado reserva al
confirmar, sin expiración, sin sobreventa, sin crédito: comportamiento determinado.

## 5. Histórico y migración (contrato para 030)

- Toda reserva persiste `trigger` (`ORDER_CONFIRMATION` · `MANUAL` · `LEGACY_CREDIT_APPROVAL`).
  Las existentes al migrar se marcan `LEGACY_CREDIT_APPROVAL` y **conservan su semántica**: no se
  reinterpretan ni se liberan.
- Pedidos en `RESERVED` → `RELEASED` (mismo significado: aprobados y reservados). `SAFE_MIGRATION`.
- Pedidos en `SUBMITTED`/`CREDIT_PENDING` en el momento de migrar **no tienen reserva** bajo la
  semántica antigua y la tendrían bajo la nueva: quedan listados para **`MANUAL_REVIEW`** (revertir a
  borrador y reemitir, o cancelar). La migración no reserva por ellos.
- `source_document` texto se conserva; se añaden `source_type/source_id/source_line_id` con
  backfill desde el texto `SALES_ORDER:{id}` (línea `NULL` en legado).
- Un cambio futuro de política (si alguna vez el trigger se hiciera configurable) no reinterpreta
  reservas: el `trigger` persistido es la versión de la política con la que nació.

## 6. Multiempresa (ARCH-MC-001)

| Caso | Resultado |
|---|---|
| Usuario A, contexto A, pedido A | reserva en la empresa A |
| Usuario A, contexto A, pedido de B | `404` (el pedido no existe bajo A) |
| Usuario AB, contexto A, pedido de B | `404` — tener acceso a B no permite operar B bajo A |
| Cross-tenant | `404` |
| Pedido A con `warehouse_id` de B | `404 WAREHOUSE_NOT_FOUND` bajo A; la reserva nunca se intenta |
| Permiso `ventas:submit`/`inventario:reserve` en una empresa | no otorga nada en otra |
| Cuerpo con `company_id` | ignorado; nunca autoridad |

`Reservation.company_id` es directo (entidad de 003) y **siempre** igual al `company_id` del pedido
y del almacén; 030 lo asevera en prueba.

## 7. Contrato de auditoría

Eventos en el módulo de inventario (hoy inexistentes): `RESERVATION_CREATED`,
`RESERVATION_RELEASED`, `RESERVATION_EXPIRED`, `RESERVATION_FULFILLED`. Carga mínima:

| Campo | Contenido |
|---|---|
| actor | usuario o `system` |
| tenant / company | del contexto |
| order / line | `source_type`, `source_id`, `source_line_id` (null en `MANUAL`) |
| warehouse / product | ids |
| quantity | `quantity` tecleada + `uom_id`/`presentation_id` + `base_quantity` + `conversion_factor_snapshot` |
| trigger | `ORDER_CONFIRMATION` · `MANUAL` · `LEGACY_CREDIT_APPROVAL` |
| reason | `release_reason` (`ORDER_CANCELLED` · `CREDIT_REJECTED` · `ORDER_REVERTED` · `EXPIRED` · `MANUAL:{texto}` · `PICKING_SHORTAGE`) |
| before / after | estado anterior y posterior de la reserva; `available_before` en creación; `oversell` |
| timestamp | UTC |

Además de los eventos del pedido (`SALES_ORDER_TRANSITIONED` con motivo cuando lo haya).
Eventos de dominio/outbox y notificaciones al usuario: **no se inventan**; si 047 los introduce, la
auditoría anterior es la fuente. La decisión no depende de ello.

## 8. Contratos que este checkpoint enmienda

| Contrato | Antes | Ahora |
|---|---|---|
| FR-003-041 | «Reserva: orden aprobada → cantidad reservada» | «Reserva: pedido **confirmado** (`SUBMITTED`) → cantidad base reservada → disponible reducido, físico sin cambio» |
| FR-003-043 | Liberación por cancelación, vencimiento, política (P1) | P0 para 030: cancelación, rechazo de crédito, reversión, expiración por TTL; consumo en despacho |
| FR-005-011 | `… → APPROVED → RESERVED → PREPARING …` | `DRAFT → SUBMITTED[reserva] → CREDIT_PENDING → APPROVED → RELEASED → PREPARING → SHIPPED → CLOSED`; terminales `CANCELLED`, `REJECTED`, `EXPIRED`; `REVERT_TO_DRAFT` |
| FR-005-020 | «Aprobar la OV → reservar inventario vía 003» | «Confirmar el pedido → reservar vía 003; aprobar → liberar a preparación» |
| ADR-D0-003 R-D0-03-1 | disparador configurable, defecto `ORDER_RELEASED` | disparador fijo `ORDER_CONFIRMATION` |
| ADR-D0-003 R-D0-03-4 | toda reserva tiene vigencia | vigencia opcional por TTL solo durante crédito; defecto sin expiración; invariante pedido-vivo-con-reserva |
| POL-D0-002 §2, §4 | ídem | ídem |
| CL-013-06 | pendiente | resuelta |
| OQ-03 | BUSINESS | resuelta por producto; residuo CONFIG (`reservation_ttl_days`) |

## 9. Contrato implementable por la Spec 030 (resumen)

Detalle en `specs/005-ventas-cuentas-por-cobrar/spec.md` §SPEC 030. Lo esencial:

1. Mover el disparo a `DRAFT → SUBMITTED`; retirar la reserva de `APPROVED`; renombrar `RESERVED`
   → `RELEASED`; añadir `REVERT_TO_DRAFT`, `CANCELLED` desde `SUBMITTED`/`CREDIT_PENDING`, y
   `EXPIRED` (solo con TTL).
2. `warehouse_id` obligatorio para confirmar con líneas de inventario; `add_order_line` solo en `DRAFT`.
3. Reserva por línea en cantidad base con los campos Spec 011; `source_type/source_id/
   source_line_id`, `trigger`, `oversell`, `released_at/by`, `release_reason`.
4. Bloqueo de fila, unicidad del saldo, índice único parcial por línea activa, `CHECK ≥ 0`.
5. Liberación atómica en cancelación, rechazo, reversión y expiración; `FULFILLED` en despacho.
6. `reservation_ttl_days` por empresa (defecto `NULL`); `expire` consciente del pedido.
7. Permiso `ventas:submit`; auditoría de 003 según §7.
8. Pruebas: carrera en PostgreSQL; sobreventa autorizada; cancelación libera; rechazo libera;
   reversión libera y obsoleta la aprobación; presentación reserva base; sin almacén → 422;
   cross-company/tenant/AB → 404; idempotencia doble confirmación/doble liberación; conversión
   sigue sin reservar; despacho consume.
9. Migración: `SAFE_MIGRATION` (columnas nuevas, backfill, rename de estado) +
   `MANUAL_REVIEW_REQUIRED` (pedidos en vuelo sin reserva).

## 10. Opciones rechazadas (registro)

A Creación · C Crédito aprobado (código actual) · D Liberación a preparación · E Configurable por
empresa · F Contado/crédito con triggers distintos. Razones en `d0-03-reservation-options.md` §4.
