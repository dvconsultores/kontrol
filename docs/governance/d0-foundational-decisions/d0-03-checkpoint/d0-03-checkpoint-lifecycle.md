# D0-03 — CICLO SPECKIT DEL CHECKPOINT (SPECIFY · CLARIFY · PLAN · GATE · CHECKLIST · TASKS · ANALYZE)

Este documento es la evidencia de que la decisión pasó por la metodología completa. El contenido
sustantivo de cada etapa vive en los artefactos que se citan; aquí se registra la etapa, su alcance y
su resultado. **Product code changes = 0.**

---

## `/speckit.specify` — alcance del checkpoint

**Solicitud.** Resolver formalmente cuándo (y bajo qué política completa) se reserva inventario en
KONTROL, y dejar un contrato implementable por la Spec 030 sin implementarla.

**Alcance incluido.** Disparador · tipos de operación · contado/crédito · reserva parcial · stock
insuficiente · backorder · almacén · semántica de cantidad · UOM/presentación · modificación ·
cancelación · vigencia · liberación · concurrencia · sobreventa · permisos · auditoría · interacción
con aprobación · handoff a picking · multiempresa.

**Alcance excluido.** Cualquier código productivo, migración, endpoint, worker, pantalla; picking,
ruta, ubicación, selección de lote/serial (031/032); confirmación independiente (033); facturación
(034); despacho físico (035); crédito como motor (045, ya existe); backorder y sustitución (FUTURE).

### Requisitos del checkpoint

| ID | Requisito | Resuelto en |
|---|---|---|
| FR-D0-03-001 | El disparador de reserva está explícitamente definido | Decision §1 · ADR v2 |
| FR-D0-03-002 | El disparador no depende de una condición implícita de código | Decision §1, §8 · current-state §3 |
| FR-D0-03-003 | Contado tiene comportamiento definido | Decision §2.P, §3 · Flows A/B |
| FR-D0-03-004 | Crédito tiene comportamiento definido | Decision §2.P, §3 · Flows C/D |
| FR-D0-03-005 | Pedidos sin evaluación de crédito tienen comportamiento definido | Decision §3 (fila «sin política») |
| FR-D0-03-006 | Stock insuficiente tiene comportamiento definido | Decision §2.K · Flow B |
| FR-D0-03-007 | Reserva parcial está explícitamente permitida o prohibida | Decision §2.D (**prohibida**) · Flow H |
| FR-D0-03-008 | Backorder está explícitamente permitido/prohibido/fuera de alcance | Decision §2.M (**OUT_OF_SCOPE**) |
| FR-D0-03-009 | La autoridad del almacén está definida | Decision §2.E |
| FR-D0-03-010 | El aislamiento por empresa está definido | Decision §2.O, §6 |
| FR-D0-03-011 | La semántica de cantidad está definida | Decision §2.D |
| FR-D0-03-012 | UOM / cantidad base están definidas | Decision §2.D · Clarify 14-15 |
| FR-D0-03-013 | La modificación del pedido tiene efecto de reserva definido | Decision §2.I · Flow E |
| FR-D0-03-014 | La cancelación libera según contrato | Decision §2.J · Flow F |
| FR-D0-03-015 | El rechazo de crédito tiene efecto definido | Decision §2.P · Flow D |
| FR-D0-03-016 | La expiración está definida o es N/A explícito | Decision §2.F-G · Flow I |
| FR-D0-03-017 | La liberación manual está definida o es N/A | Decision §2.H |
| FR-D0-03-018 | La idempotencia es obligatoria | Decision §2.L · Concurrency §6 |
| FR-D0-03-019 | La concurrencia no puede producir sobre-reserva no autorizada | Concurrency §3-5 · Flow G |
| FR-D0-03-020 | La sobreventa está permitida/prohibida explícitamente | Decision §2.K (**prohibida salvo `allow_negative`**) |
| FR-D0-03-021 | La reserva no consume stock de otra empresa | Decision §6 |
| FR-D0-03-022 | La reserva no consume stock no elegible | Decision §2.E (solo `DISPONIBLE`) |
| FR-D0-03-023 | La reserva no absorbe picking | Decision §2.Q, §5 |
| FR-D0-03-024 | La reserva no absorbe facturación | Decision §5 |
| FR-D0-03-025 | La reserva no absorbe despacho | Decision §5 |
| FR-D0-03-026 | La aprobación usa Spec 045 | Decision §2.P |
| FR-D0-03-027 | El permiso no sustituye al contexto de empresa | Decision §2.O, §6 |
| FR-D0-03-028 | El contrato de auditoría está definido | Decision §7 |
| FR-D0-03-029 | El handoff a 031 está definido | Decision §2.Q · Flow J |
| FR-D0-03-030 | D0-03 produce un contrato implementable por Spec 030 | Decision §9 · `specs/005-…/spec.md` §SPEC 030 |

---

## `/speckit.clarify` — 30 preguntas resueltas

| # | Pregunta | Respuesta | Fuente |
|---|---|---|---|
| 1 | ¿Qué significa *reservado* en KONTROL? | Cantidad en unidad base comprometida a una línea de pedido emitido, aún no extraída físicamente. No mueve mercancía ni cambia su estado de custodia | Decision §0 |
| 2 | ¿Autoridad actual de `reserved`? | Filas `Reservation` `ACTIVE` (ledger de hecho) proyectadas en `InventoryBalance.qty_reserved` | current-state §4 |
| 3 | ¿Autoridad actual de `available`? | `qty_available = qty_on_hand − qty_reserved` en la fila `DISPONIBLE` (FR-003-013) | current-state §4 |
| 4 | ¿Qué código de reserva existe hoy? | `inventory.reserve/release_reservation/expire_reservations`; `sales._reserve_order` | behavior |
| 5 | ¿Qué evento lo dispara? | `transition_order(target="APPROVED")`, tras crédito | behavior |
| 6 | ¿Está documentado? | Descrito (FR-003-041, FR-005-020), **no decidido** (ADR v1: «es donde quedó») | current-state §1 |
| 7 | ¿Contado y crédito usan el mismo disparador? | **Sí**: `ORDER_CONFIRMATION`. Difieren después (crédito pasa por `CREDIT_PENDING`) | Decision §3 |
| 8 | ¿Se permite reserva parcial? | **No.** Todo-o-nada por pedido | Decision §2.D |
| 9 | ¿Se permite backorder? | **No en 030** (OUT_OF_SCOPE, OQ-04 FUTURE). El modelo lo admite sin rediseño | Decision §2.M |
| 10 | ¿Se permite sobreventa? | **No**, salvo almacén con `policies.allow_negative = true`; nunca por carrera | Decision §2.K |
| 11 | ¿Se conoce el almacén antes de reservar? | Debe conocerse: `warehouse_id` obligatorio para emitir un pedido con líneas de inventario (`422 WAREHOUSE_REQUIRED`) | Decision §2.B |
| 12 | ¿Se conoce la ubicación? | No, y no hace falta: la reserva es por almacén; la ubicación la asigna 031/032 | Decision §2.E |
| 13 | ¿Lote/serial se elige al reservar o al pickear? | Al pickear, salvo que la **línea del pedido** los fije explícitamente (exigencia del cliente); entonces la reserva los lleva | Decision §2.E |
| 14 | ¿Qué cantidad se persiste? | Ambas: `quantity` tecleada con `uom_id/presentation_id/conversion_factor_snapshot` y `base_quantity`; la comparación con disponible es en base | Decision §2.D |
| 15 | ¿Cuál es la cantidad base? | La de la línea de pedido (Spec 011, snapshot al capturar); la reserva **no** recalcula con el factor vigente | Decision §2.D |
| 16 | ¿Cómo se modifica una reserva? | No se modifica: se libera entera al volver el pedido a `DRAFT` y se recrea al reemitir | Decision §2.I |
| 17 | ¿Cómo se libera? | Automáticamente por cancelación, rechazo de crédito, reversión a borrador o expiración; se **consume** (`FULFILLED`) en el despacho | Decision §2.H |
| 18 | ¿Puede expirar? | Solo si la empresa configura `reservation_ttl_days` y solo mientras el pedido espera crédito. Defecto: sin expiración | Decision §2.F-G |
| 19 | ¿Quién puede liberar? | El sistema, por los eventos anteriores. Manualmente solo reservas **manuales** (`inventario:reserve` + motivo). Las de pedido, nunca a mano: se cancela o revierte el pedido | Decision §2.H |
| 20 | ¿Qué pasa si el crédito se rechaza? | `REJECTED` terminal y liberación de toda la reserva en la misma transacción | Decision §2.P |
| 21 | ¿Si el pedido se cancela? | `CANCELLED` y liberación atómica; permitido desde cualquier estado vivo | Decision §2.J |
| 22 | ¿Si aumenta la cantidad? | Solo en `DRAFT`. Un pedido emitido se revierte a `DRAFT` (libera todo), se edita y se reemite (reserva de nuevo, con la disponibilidad de ese momento) | Decision §2.I |
| 23 | ¿Si disminuye? | Mismo camino. No hay liberación por diferencia | Decision §2.I |
| 24 | ¿Cómo se evita la doble reserva? | Índice único parcial `(source_line_id) WHERE status = 'ACTIVE'` + la transición es única por máquina de estados | Concurrency §6 |
| 25 | ¿Cómo se evita la sobre-reserva concurrente? | `SELECT … FOR UPDATE` sobre la fila de saldo dentro de la transacción; unicidad en la clave del saldo; prueba de carrera obligatoria en PostgreSQL | Concurrency §3-5 |
| 26 | ¿Qué estado del pedido habilita 031? | `RELEASED` (el actual `RESERVED`, renombrado por 030) | Decision §2.Q |
| 27 | ¿Disparador fijo o configurable? | **Fijo** | Decision §4 |
| 28 | Si configurable, ¿opciones? | N/A. Lo configurable es `reservation_ttl_days` (empresa) y `allow_negative` (almacén) | Decision §4 |
| 29 | ¿Default? | Trigger `ORDER_CONFIRMATION`; TTL desactivado; sobreventa prohibida | Decision §4 |
| 30 | ¿Cómo se trata el histórico? | Las reservas existentes conservan su semántica y se marcan `trigger = LEGACY_CREDIT_APPROVAL`; pedidos en vuelo sin reserva → `MANUAL_REVIEW` en la migración de 030 | Decision §5 |

---

## `/speckit.plan` — plan documental (14 olas)

| Ola | Contenido | Artefacto |
|---|---|---|
| 1 | Auditoría del comportamiento actual | `current-reservation-behavior.md` |
| 2 | Semántica de inventario (on-hand, reserved, available, estados) | `d0-03-reservation-current-state.md` §4 |
| 3 | Flujos comerciales y de crédito | `d0-03-reservation-flow-matrix.md` A–D |
| 4 | Opciones de disparador | `d0-03-reservation-options.md` |
| 5 | Concurrencia y sobreventa | `d0-03-reservation-concurrency-analysis.md` |
| 6 | Almacén y UOM | Decision §2.D-E |
| 7 | Modificación, cancelación, liberación | Decision §2.H-J · Flows E/F/I |
| 8 | Handoff a picking | Decision §2.Q · Flow J |
| 9 | Comparación de opciones | Options §3 |
| 10 | Decisión de negocio | Decision §1-§4 |
| 11 | ADR | `adr/ADR-D0-003-inventory-reservation.md` v2 · `policies/POL-D0-002` v2 |
| 12 | Revalidación documental de Spec 030 | `specs/005-ventas-cuentas-por-cobrar/` (spec, clarifications, plan, checklist, tasks, data-model) |
| 13 | Grafo de dependencias y Master 56 | `docs/roadmap/*` · registro D0 |
| 14 | Convergencia | `convergence.md` |

---

## CONSTITUTION GATE

| Validación | Resultado | Evidencia |
|---|---|---|
| ARCH-MC-001 (contexto de empresa es la autoridad; permiso ≠ empresa) | PASS | Decision §6: toda operación de reserva deriva la empresa del pedido cargado bajo contexto; cross-company/tenant → 404 |
| Spec 011 (cantidad base con snapshot) | PASS | Decision §2.D: reserva en base, factor snapshot de la línea, sin recálculo |
| Spec 023 / 003 (un solo motor de inventario) | PASS | 030 invoca `reserve/release/expire`; no crea contador ni ledger alternativo |
| Spec 025 | N/A | Transferencias/conteos no participan; la reserva sobre mercancía en tránsito es FUTURE |
| Spec 029 (conversión no reserva) | PASS | Frontera intacta; trigger posterior a `DRAFT` |
| Spec 045 (un solo motor de aprobaciones) | PASS | Crédito vía `SALES_CREDIT`; obsolescencia vía `document_changed`; sin `ReservationApprovalEngine` |
| Separación 030 / 031 / 032 | PASS | 030 no elige ubicación, ruta, lote ni serial; entrega estado `RELEASED` y filas de reserva |
| Autoridad PostgreSQL (P21, ADR-D0-001) | PASS | Bloqueo de fila y unicidad parcial son PostgreSQL; prueba de carrera exigida sobre PostgreSQL |
| Sin segundo motor de inventario | PASS | — |
| Sin segundo motor de aprobaciones | PASS | — |
| Sin implementación de funcionalidad | PASS | `git diff --stat` sobre `resources/` y `alembic/` = 0 archivos |
| P8 (no codificar la política de un cliente) | PASS | El trigger es semántica de producto (como la máquina de estados); lo que varía por cliente (TTL, sobreventa, política de crédito) es configuración |
| P5 (histórico inmutable) | PASS | Reservas históricas no se reinterpretan (Decision §5) |
| P23 (captura temprana) | PASS | La reserva registra línea, UOM, base, trigger y motivo desde su nacimiento |

**CONSTITUTION GATE: PASS**

---

## `/speckit.checklist`

- [x] Current reservation behavior audited — `current-reservation-behavior.md`
- [x] Inventory authority identified — current-state §4
- [x] `available` semantics identified — FR-003-013 confirmado
- [x] `reserved` semantics identified — filas + contador
- [x] Trigger options compared — options.md
- [x] Cash flow defined — Flows A/B
- [x] Credit flow defined — Flows C/D
- [x] No-credit flow defined — Decision §3
- [x] Insufficient stock defined — rechazo 409, todo-o-nada
- [x] Partial reservation decided — prohibida
- [x] Backorder decided — OUT_OF_SCOPE
- [x] Overselling decided — prohibida salvo `allow_negative`
- [x] Warehouse scope decided — almacén del pedido, sin abastecimiento cruzado
- [x] Location boundary decided — 031/032
- [x] Lot/serial boundary decided — picking, salvo exigencia explícita en línea
- [x] UOM/base quantity decided — base con snapshot
- [x] Modification behavior decided — reversión a borrador
- [x] Cancellation behavior decided — liberación atómica
- [x] Credit rejection behavior decided — liberación + `REJECTED`
- [x] Expiry decided — opcional por TTL, defecto desactivado, dueño 047
- [x] Manual release decided — solo reservas manuales, con motivo
- [x] Concurrency behavior defined — bloqueo de fila + unicidad + prueba
- [x] Idempotency defined — índice parcial por línea; liberar dos veces es no-op
- [x] Handoff to 031 defined — `RELEASED`
- [x] Company isolation defined — Decision §6
- [x] Permissions defined — `ventas:submit` (nuevo, 030) / `ventas:approve` / `inventario:reserve`
- [x] Audit defined — Decision §7
- [x] Chosen option documented — B
- [x] Rejected options documented — A, C, D, E, F
- [x] ADR prepared — v2 ACTIVE
- [x] Spec030 readiness evaluable — convergence.md

---

## `/speckit.tasks`

| Tarea | Descripción | Artefacto | Estado |
|---|---|---|---|
| T-D003-001 | Auditar código de reserva existente | behavior | ✔ |
| T-D003-002 | Auditar modelo de reserva en BD | behavior · current-state §4 | ✔ |
| T-D003-003 | Auditar cálculo de `available` | current-state §4 | ✔ |
| T-D003-004 | Auditar cálculo de `reserved` | current-state §4 | ✔ |
| T-D003-005 | Mapear estados del pedido | behavior · Decision §9 | ✔ |
| T-D003-006 | Mapear estados de crédito | current-state §5 | ✔ |
| T-D003-007 | Mapear estados de inventario | current-state §4 (ADR-D0-010) | ✔ |
| T-D003-008 | Modelar contado con stock | Flow A | ✔ |
| T-D003-009 | Modelar contado sin stock | Flow B | ✔ |
| T-D003-010 | Modelar aprobación de crédito | Flow C | ✔ |
| T-D003-011 | Modelar rechazo de crédito | Flow D | ✔ |
| T-D003-012 | Evaluar reserva parcial | Decision §2.D · Flow H | ✔ |
| T-D003-013 | Evaluar backorder | Decision §2.M | ✔ |
| T-D003-014 | Evaluar sobreventa | Decision §2.K · Concurrency §7 | ✔ |
| T-D003-015 | Evaluar selección de almacén | Decision §2.E | ✔ |
| T-D003-016 | Evaluar frontera de ubicación | Decision §2.E | ✔ |
| T-D003-017 | Evaluar frontera lote/serial | Decision §2.E | ✔ |
| T-D003-018 | Evaluar UOM / cantidad base | Decision §2.D | ✔ |
| T-D003-019 | Definir modificación | Decision §2.I | ✔ |
| T-D003-020 | Definir cancelación | Decision §2.J | ✔ |
| T-D003-021 | Definir expiración | Decision §2.F-G | ✔ |
| T-D003-022 | Definir liberación manual | Decision §2.H | ✔ |
| T-D003-023 | Definir contrato de concurrencia | Concurrency | ✔ |
| T-D003-024 | Definir contrato de idempotencia | Concurrency §6 | ✔ |
| T-D003-025 | Definir handoff a picking | Decision §2.Q · Flow J | ✔ |
| T-D003-026 | Comparar opciones | options.md | ✔ |
| T-D003-027 | Seleccionar decisión | Decision §1 | ✔ |
| T-D003-028 | Crear/actualizar ADR | ADR-D0-003 v2 · POL-D0-002 v2 | ✔ |
| T-D003-029 | Actualizar clarificaciones de Spec 030 | `specs/005-…/clarifications.md` | ✔ |
| T-D003-030 | Actualizar mapa de dependencias | `docs/roadmap/*` · registro D0 | ✔ |
| T-D003-031 | Actualizar trazabilidad | `traceability-matrix.md` | ✔ |
| T-D003-032 | Converger el checkpoint | `convergence.md` | ✔ |

---

## `/speckit.analyze`

| Detección buscada | Resultado |
|---|---|
| Trigger indefinido | No: `ORDER_CONFIRMATION`, transición `DRAFT → SUBMITTED` |
| Contado indefinido | No: Flow A/B |
| Crédito indefinido | No: Flow C/D |
| Stock insuficiente indefinido | No: 409, todo-o-nada |
| Reserva parcial indefinida | No: prohibida |
| Backorder ambiguo | No: OUT_OF_SCOPE con modelo preparado |
| Sobreventa implícita | No: solo `allow_negative`, auditada |
| Autoridad de almacén ambigua | No: `SalesOrder.warehouse_id` obligatorio |
| Semántica de cantidad ambigua | No: base + tecleada con snapshot |
| Expiración sin dueño | No: TTL opcional; ejecución por endpoint existente; planificador = Spec 047 |
| Liberación sin disparador | No: cinco disparadores enumerados |
| Modificación sin efecto | No: reversión a borrador |
| Concurrencia sin contrato | No: bloqueo de fila + unicidad + prueba |
| Aislamiento de empresa no definido | No: Decision §6 |
| Frontera de picking ambigua | No: `RELEASED` → 031 |
| Duplicación de aprobación | No: 045 |
| Código existente tratado como decisión | No: el trigger elegido **no** es el del código; se documenta la diferencia |
| Opción elegida sin evidencia | No: DOCX Pedido §1, contratos 003/005/011/045, cadena 031-033, análisis de carrera |
| Spec 030 declarada lista con OQ material | No: OQ-03 resuelta por decisión de producto; OQ-04 FUTURE |
| Implementación incluida por accidente | No: `git diff` sobre `resources/` y `alembic/` = 0 |

| Métrica | Valor |
|---|---:|
| BLOCKER | 0 |
| CRITICAL | 0 |
| CONTRADICTIONS | 0 (la de «liberación» se resolvió con nombres atados a transiciones; las de FR-003-041/FR-005-020 quedan enmendadas) |
| ORPHAN REQUIREMENTS | 0 (30/30 con evidencia, clarificación, opción, decisión, ADR e impacto) |
| ORPHAN TASKS | 0 (32/32 con artefacto) |
| UNRESOLVED MATERIAL OQ | 0 |
