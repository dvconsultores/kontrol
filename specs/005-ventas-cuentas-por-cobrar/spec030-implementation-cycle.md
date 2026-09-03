# SPEC 030 — CICLO DE IMPLEMENTACIÓN · ETAPAS SPECKIT PREVIAS AL CÓDIGO

| Campo | Valor |
|---|---|
| Autorización | `SPEC 030 — IMPLEMENTATION CYCLE AUTHORIZED` (2026-09-02) |
| Decisión inmutable | `RESERVATION TRIGGER = ORDER_CONFIRMATION` · `DRAFT → SUBMITTED` · FIXED (`ADR-D0-003` v2) |
| Baseline remedida | `83946f8` · PostgreSQL 18.6 · modelos 177 · tablas 177 · migraciones 42 (head `0042_spec029_origin`) · rutas 311 · operaciones 429 · operaciones con contrato de empresa 367 · FK (referencias de columna, instrumento ORM) 371 |
| Nota de instrumento | El checkpoint 029 publicó 366 claves foráneas con otro instrumento. Aquí se mide con `sum(len(t.foreign_keys))` sobre el metadata del ORM y se usará el **mismo** instrumento al cerrar, de modo que el delta sea comparable |

---

## `/speckit.specify` — delta productivo exacto

**Entrada.** `SalesOrder` en `DRAFT` con origen comercial (029). Motor de reservas de 003 (`reserve`,
`release_reservation`, `expire_reservations`, `get_available`). Motor de aprobaciones de 045 con
proceso `SALES_CREDIT`. Contrato FR-030-001..063 (documental, D0-03).

**Salida.** Pedido confirmable con reserva atómica en cantidad base, crédito por 045, liberación a
preparación (`RELEASED`), rechazo, reversión a borrador, cancelación con motivo, expiración opcional
por TTL, concurrencia real en PostgreSQL, idempotencia en base de datos, aislamiento multiempresa,
auditoría de reservas, API/OpenAPI y frontend coherentes, migración con clasificación del legado.

**Fuera.** Picking, ubicación, ruta, consolidación, confirmación independiente, facturación, despacho
(salvo marcar `FULFILLED`, que es la semántica ya decidida del consumo), CxC, backorder,
abastecimiento cruzado, FEFO/FIFO, planificador.

### Reconciliación de FR-030-001..063 (sin renumerar)

Todos se mantienen. Precisiones descubiertas al auditar el código (se registran como IMP, no cambian
el número del FR):

| FR | Precisión de implementación |
|---|---|
| FR-030-002 | El estado `CREDIT_PENDING` **desaparece de la máquina** (IMP-030-025: el pedido a crédito espera en `SUBMITTED`). `APPROVED` tampoco existe como estado observable (hoy ya no lo era). Filas históricas: `RESERVED → RELEASED`, `APPROVED → RELEASED`, `CREDIT_PENDING → SUBMITTED` (revisión manual: carecen de reserva) |
| FR-030-003 | `SUBMITTED → RELEASED` la ejecuta la propia confirmación cuando 045 no abre solicitud; con solicitud, la ejecuta la acción `release` tras `ensure_approved` (patrón vigente de 015/017: el dominio avanza cuando 045 resolvió; el motor no llama al dominio) |
| FR-030-007 | `reject` con motivo: si hay solicitud viva en 045, se cancela con ese motivo (el motor registra la resolución); si 045 ya la rechazó, `reject` cierra el pedido; en ambos casos libera |
| FR-030-015 | Las líneas nacen con su semántica de unidad (`to_base` de Spec 011) en cotización y pedido directo; una línea previa sin base la recibe **en la confirmación** (primera captura, no recálculo) |
| FR-030-024 | `reservation_ttl_days` vive en `companies` (columna nullable); se administra por `GET/PUT /sales/settings/reservation` bajo contexto de empresa |
| FR-030-025 | La expiración de reservas de pedido la ejecuta `POST /sales/orders/expire-reservations` (consciente del pedido); el endpoint de inventario `POST /inventory/reservations/expire` deja de tocar reservas de pedido |
| FR-030-027 | `POST /inventory/reservations/{id}/release` exige `reason` y rechaza reservas de pedido con `409 RESERVATION_ORDER_BOUND` |
| FR-030-035 | `ventas:submit` se añade al catálogo (`_bootstrap_roles`) y se concede a `ADMIN` por migración de datos (patrón 0013) |
| FR-030-062 | `Reservation.quantity` conserva la semántica de movimiento (cantidad tecleada); `base_quantity` es la que afecta al saldo; las filas legadas reciben `base_quantity = quantity`, `uom_source = LEGACY_ASSUMED_BASE` |

### Requisitos de implementación

IMP-030-001..063 tal como los enumera la autorización. Se trazan uno a uno en
`traceability-matrix.md` §SPEC 030 al cerrar; ninguno se omite ni se reinterpreta.

---

## `/speckit.clarify` — 30 detalles con evidencia

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | Modelo `Reservation` actual | `inventory/models.py:153-176`: `company_id`, `source_document` texto, `product_id`, `warehouse_id`, `lot_id`/`serial_id` texto, `quantity`, `status`, `expires_at`, + `uom_id`, `presentation_id`, `conversion_factor_snapshot`, `base_quantity`, `uom_source` (Spec 011, nunca rellenados por ventas) |
| 2 | Campos a añadir | `source_type`, `source_order_id` (FK `sales_orders`), `source_line_id` (FK `sales_order_lines`), `trigger`, `oversell`, `released_at`, `released_by`, `release_reason`; índice único parcial `(source_line_id) WHERE status='ACTIVE'`; `CHECK quantity > 0` |
| 3 | ¿`source_document` queda? | Sí, por compatibilidad y como único rastro de las filas legadas; se sigue escribiendo `SALES_ORDER:{id}` |
| 4 | ¿`source_order_id` FK explícita? | Sí, nullable (las manuales no tienen pedido) |
| 5 | ¿`source_line_id` FK explícita? | Sí, nullable; única entre activas |
| 6 | Representación de `trigger` | `String(32)`: `ORDER_CONFIRMATION` · `MANUAL` · `LEGACY_CREDIT_APPROVAL` |
| 7 | Representación de `release_reason` | `String(120)`: `ORDER_CANCELLED` · `CREDIT_REJECTED` · `ORDER_REVERTED` · `EXPIRED` · `MANUAL:{texto}` · `DISPATCHED` (consumo) · `PICKING_SHORTAGE` (032, reservado) |
| 8 | Enum de estado de la reserva | `ACTIVE` · `RELEASED` · `EXPIRED` · `FULFILLED` (los cuatro ya declarados en el comentario del modelo; `FULFILLED` pasa a escribirse) |
| 9 | ¿`RELEASED` y `FULFILLED` distintos? | Sí: liberada (vuelve al disponible) vs consumida (salió físicamente) |
| 10 | ¿Qué consume? | `confirm_shipment` (035): movimiento `SALIDA_DESPACHO` + reserva `FULFILLED` (antes `RELEASED`) |
| 11 | Estados actuales del pedido | `DRAFT, SUBMITTED, CREDIT_PENDING, APPROVED, RESERVED, PREPARING, SHIPPED, CLOSED, CANCELLED, REJECTED` (`sales/service.py:76-87`) |
| 12 | Estados a migrar | `RESERVED → RELEASED` (equivalen: aprobado y reservado), `APPROVED → RELEASED` (nunca observable; si existe alguno, revisión manual), `CREDIT_PENDING → SUBMITTED` (emitido a la espera de crédito; revisión manual por carecer de reserva) |
| 13 | ¿`RESERVED` se renombra? | Sí, en enum, datos, `allowed_actions`, API, frontend (`OrdenesVentasPage`, `DespachoPage`, `ReservasPage`), pruebas e informes |
| 14 | ¿Datos que requieran migración? | Reservas existentes (clasificar y marcar `trigger`), saldos (unicidad), pedidos (estados), empresas (TTL), permisos (`ventas:submit`) |
| 15 | ¿Cómo identificar reservas legadas? | `source_document LIKE 'SALES_ORDER:%'` cuyo pedido existe → `ORDER_RECONSTRUCTIBLE` (`trigger = LEGACY_CREDIT_APPROVAL`; `source_line_id` solo si el pedido tiene **exactamente una** línea con ese producto); pedido inexistente → `LEGACY_UNVERIFIED`; sin patrón → `MANUAL`; varias líneas candidatas → `CRITICAL_AMBIGUOUS` (línea `NULL`, listado en el informe) |
| 16 | ¿Cómo modelar `reservation_ttl_days`? | `companies.reservation_ttl_days` `Integer` nullable, defecto `NULL` |
| 17 | ¿En qué maestro? | `Company` (organización, alcance TENANT); se lee bajo `CompanyContext` |
| 18 | Permiso que confirma | `ventas:submit` (nuevo) |
| 19 | ¿Existe `ventas:submit`? | No: el catálogo (`setup/api.py::_bootstrap_roles`, migración 0013) tiene `ventas: view/create/approve/quality/apply`. Se añade |
| 20 | Permiso que revierte | `ventas:submit` |
| 21 | Permiso que cancela | `ventas:submit` (el vendedor) — `ventas:approve` también puede |
| 22 | Permiso de reserva manual | `inventario:reserve` (existente) |
| 23 | Cómo funciona `SALES_CREDIT` | `require_for_document` evalúa la política activa con `_order_credit_context` (monto, moneda, cliente, lista); sin política → `requires_approval: False`; con política → `ApprovalRequest` `PENDING/IN_REVIEW`; `ensure_approved` bloquea mientras viva y rechaza si `REJECTED/OBSOLETE` |
| 24 | Cómo invalidar por `document_changed` | `notify_document_changed` recalcula huella; para reversión a borrador se usa además `approvals_service.cancel` de la solicitud viva con motivo, porque el documento deja de existir como propuesta (la huella podría no cambiar si se reemite igual, y una aprobación previa no debe sobrevivir a la reversión) |
| 25 | Cómo se resuelve `need_credit` | Lo decide 045 (política activa + reglas). Sin política = contado. No hay `if payment_term == CREDIT` |
| 26 | Qué regla pertenece a 012/013 | Precio, descuento y condición de pago (012, ya capturados en 029); tasa BCV (013). 030 no las toca |
| 27 | Comportamiento a eliminar | Reserva en `APPROVED`; salto a `RESERVED`; `_reserve_order` con retorno silencioso; `add_order_line` sin control de estado; liberación en despacho como `RELEASED`; liberación manual sin motivo sobre reservas de pedido; `ventas:approve` para emitir |
| 28 | Endpoint de compatibilidad | `POST /sales/orders/{id}/transition` se conserva: `SUBMITTED/RELEASED/REJECTED/CANCELLED/DRAFT` delegan en los nuevos servicios (con las mismas reglas), `PREPARING/CLOSED` siguen como antes |
| 29 | Errores | `404`: pedido/almacén/producto fuera de la empresa · `409`: `INSUFFICIENT_AVAILABLE`, transición inválida, `APPROVAL_PENDING`, `APPROVAL_NOT_GRANTED`, `ORDER_NOT_EDITABLE`, `RESERVATION_NOT_ACTIVE`, `RESERVATION_ORDER_BOUND` · `422`: `WAREHOUSE_REQUIRED`, `UOM_NOT_RESOLVED`/`CONVERSION_*`, `ORDER_EMPTY`, `REASON_REQUIRED`, cuerpo con campos desconocidos |
| 30 | Frontend actual | `OrdenesVentasPage` (crear sin almacén, líneas sin presentación, botones `submit/credit/approve/reject/cancel/close` sobre `/transition`), `DespachoPage` (filtra `RESERVED`), `ReservasPage` (libera sin motivo, muestra `RESERVED` como estado), tipos sin campos de 030 |

**Nueva decisión material: ninguna.** La única duda de diseño (quién mueve el pedido a `RELEASED`
tras la decisión de 045) se resuelve por el patrón ya vigente en compras (el dominio avanza con
`ensure_approved`), no por una decisión nueva.

---

## `/speckit.plan` — 22 olas

| Ola | Contenido | Entregable |
|---|---|---|
| 1 | Baseline + auditoría forense | esta sección · `current-reservation-behavior.md` (D0-03) |
| 2 | Reconciliación de máquina de estados | `ORDER_TRANSITIONS` v2, `order_allowed_actions` |
| 3 | Modelo de reserva | `Reservation` + columnas, índice parcial, checks; `InventoryBalance` unicidad + check; `SalesOrder` `status_reason/submitted_at/released_at`; `Company.reservation_ttl_days` |
| 4 | Migración | `0043_spec030_reservation` (esquema + datos + permisos) |
| 5 | Restricciones PostgreSQL | ORM = Alembic = PostgreSQL (`ddl_if`), prueba N7 de paridad |
| 6 | Primitivas de inventario | `reserve` con bloqueo y semántica de unidad; `release_reservation` con motivo; `fulfill_reservation`; `expire_reservations` sin tocar pedidos; auditoría |
| 7 | Confirmación del pedido | `confirmar_pedido`: validaciones, orden determinista, todo-o-nada, `SUBMITTED`, crédito, `RELEASED` |
| 8 | Integración de crédito | `SALES_CREDIT` vía 045; `liberar_pedido` con `ensure_approved` |
| 9 | Revert / cancel / reject | tres servicios con motivo y liberación atómica; cancelación de solicitud viva |
| 10 | TTL / expiración | `expires_at` al confirmar; `expirar_reservas_de_pedidos`; endpoint |
| 11 | Auditoría | eventos de reserva en 003 con el contrato D0-03 §7 |
| 12 | Permisos / seguridad | `ventas:submit`; rutas con permiso correcto; cuerpos estrictos |
| 13 | API / OpenAPI | `/submit`, `/release`, `/reject`, `/revert`, `/cancel`, `/expire-reservations`, `/settings/reservation`; `order_dict` con reservas; fixture OpenAPI del frontend |
| 14 | Frontend | pedidos (almacén, presentación, acciones con motivo, detalle de insuficiencia, estados), despacho (`RELEASED`), reservas (origen, trigger, motivo), tipos |
| 15 | Concurrencia | prueba de carrera con dos sesiones PostgreSQL; variante `allow_negative` |
| 16 | Idempotencia | doble confirmación, doble liberación, doble expiración |
| 17 | Multiempresa | AB/contexto, cross-tenant, almacén ajeno, cuerpo con empresa |
| 18 | Handoff 031 | `order_dict` expone reservas por línea; prueba de elegibilidad y de no-efectos (picklist/factura/CxC) |
| 19 | Pruebas hostiles PostgreSQL | FK, índice parcial, checks, SQLSTATE |
| 20 | Instalación limpia | PostgreSQL 18.6 vacío → `alembic upgrade head` → bootstrap → flujo completo |
| 21 | Regresiones | backend completo sobre PostgreSQL + ClamAV; frontend `vitest`, `tsc`, `eslint`, `build`; Playwright |
| 22 | Convergencia | informes §2, trazabilidad, Master 56, veredicto |

Arquitectura preservada: un motor de inventario, un motor de aprobaciones, `CompanyContext`
autoridad, rutas anidadas validando el padre, `__scope__`, sin worker.

---

## CONSTITUTION GATE

| Validación | Resultado | Cómo se comprueba |
|---|---|---|
| Constitución KONTROL (P5, P8, P21, P23) | PASS | histórico intacto (reservas legadas conservadas y marcadas); ninguna política de cliente codificada (TTL y sobreventa son configuración; crédito lo decide 045); PostgreSQL autoridad (bloqueo, índices parciales, prueba de carrera real); captura temprana (unidad y base al crear la línea, origen de la reserva al nacer) |
| ARCH-MC-001 | PASS | rutas nuevas bajo `CompanyContext` + `_owned`; cuerpos sin `company_id`; pruebas AB/cross-tenant/almacén ajeno; guardia estructural existente |
| ADR-D0-003 v2 | PASS | trigger en `DRAFT → SUBMITTED`, fijo; R-D0-03-1..12 trazadas |
| Spec 011 | PASS | `to_base` es la única autoridad; sin recálculo |
| Spec 012 | PASS | origen comercial intacto (029) |
| Spec 023 | PASS | reserva sobre `InventoryBalance` de 003; sin motor paralelo |
| Spec 029 | PASS | conversión sigue sin reservar (prueba existente) |
| Spec 045 | PASS | `SALES_CREDIT` por `require_for_document`/`ensure_approved`/`cancel`; sin tablas ni estados propios |
| Frontend | PASS | cliente central, contexto de empresa, `allowed_actions` del backend, sin estado inventado |
| Sin `Tenant → Company` fallback | PASS | ninguna consulta por tenant |
| Sin parcial / backorder / ubicación / picking / factura / CxC / planificador | PASS | pruebas de no-efecto y guardia estructural (sin `APScheduler`, `threading.Timer`, bucles) |

**CONSTITUTION GATE: PASS**

---

## `/speckit.checklist` (previo a implementar)

Los 35 ítems de la autorización quedan cubiertos por las olas 1–19: comportamiento y modelo
auditados (ola 1), máquina y `RESERVED` legado (ola 2, clarify 11-13), trigger fijo (ola 7), flujos
contado/crédito/rechazo/aprobación (olas 7-9), almacén y base (ola 7), identidad y unicidad de la
reserva (ola 3), todo-o-nada y `allow_negative` (olas 6-7), bloqueo y orden determinista (ola 6),
idempotencia (ola 16), cancelación y reversión (ola 9), TTL sin planificador (ola 10), aislamiento,
AB y cross-tenant (ola 17), permisos (ola 12), auditoría (ola 11), 045 (ola 8), handoff 031 y
no-efectos (ola 18), migración (ola 4), pruebas hostiles (ola 19), regresión completa (ola 21).
Se marcan como hechos en `checklist.md` §SPEC 030 al cerrar, con evidencia.

---

## `/speckit.tasks`

T-030-I-001..063 según la autorización, con estos ajustes a los FR reales:

- T-030-I-029 (eventos/outbox): la arquitectura actual emite eventos de dominio **solo** en el motor
  de aprobaciones (`approval_events`); no existe outbox transversal. Ventas e inventario registran en
  auditoría (`audit_events`), que es la fuente que D0-03 §7 fija. **No se crea outbox** en 030; la
  tarea queda satisfecha por la auditoría y se documenta.
- T-030-I-057..060 (Playwright, cross-browser, responsive/a11y, route crawl): se ejecutan con los
  navegadores ya instalados (chromium, firefox, webkit) sobre backend y frontend levantados.

Las 63 tareas se marcan en `tasks.md` §SPEC 030 al cerrar.

---

## `/speckit.analyze`

| Detección | Resultado previo a implementar | Cómo se verifica al cerrar |
|---|---|---|
| Requisito sin tarea / tarea sin requisito | 0 / 0 | matriz |
| D0-03 contradicha | no | ADR v2 R-1: prueba `test_spec030_architecture` (sin `reserve` en el camino de aprobación) |
| Trigger en `APPROVED` activo | **existe hoy** → se elimina en ola 7 | guardia estructural |
| Confirmación sin reserva | no | prueba de contado |
| Conversión reservando | no | `test_convertir_no_reserva_inventario` |
| Cantidad tecleada en lugar de base | **existe hoy** → ola 6-7 | prueba de presentación ×12 |
| Reserva sin línea | **existe hoy** → ola 3 | prueba de identidad |
| Reserva activa duplicable | **existe hoy** → ola 3 | prueba hostil 23505 |
| Lectura sin bloqueo / parcial / no determinista | **existe hoy** → ola 6 | prueba de carrera |
| Todo-o-nada violado / parcial accidental / backorder accidental | no | prueba multilínea |
| `allow_negative` sin auditoría | **existe hoy** → ola 11 | prueba de sobreventa |
| Almacén cross-company / cuerpo con empresa / UUID como autoridad | no (cadena `_owned`) | pruebas MC |
| Motor de aprobación duplicado | no | guardia: sin tablas nuevas de aprobación |
| Cancel / rejection / revert sin liberación | **existe hoy** (cancel) → ola 9 | pruebas |
| `qty_reserved` negativo posible | **existe hoy** (sin CHECK) → ola 5 | prueba hostil 23514 |
| TTL con worker ad hoc | no | guardia estructural |
| `RESERVED/RELEASED` drift | **existirá si no se migra todo** → olas 2, 4, 14 | grep de `RESERVED` en backend/frontend/pruebas |
| Efectos en picking / factura / CxC | no | pruebas de conteo |
| Estado no contractual en frontend | **existe** (`credit`, `approve`) → ola 14 | revisión + build |
| Drift OpenAPI | se regenera el fixture | `audit-completeness.test.ts` |
| Prueba negativa fallando por causa incorrecta | doctrina: cada negativa asevera el código de error | revisión de cada prueba |

BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · ORPHAN REQUIREMENTS 0 · ORPHAN TASKS 0 · MATERIAL OQ 0.

## TRACEABILITY (plan)

`traceability-matrix.md` §SPEC 030 se completa al cerrar con el formato exigido
`| Requirement | D0-03 Rule | Plan | Task | Migration/Code | Test | Evidence | Status |` para
FR-030-001..063 e IMP-030-001..063.

## EXPRESS AUTHORIZATION

Puertas satisfechas. Se procede a `/speckit.implement` por olas.
