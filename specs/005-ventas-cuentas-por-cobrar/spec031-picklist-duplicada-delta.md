# SPEC 031 · Delta dirigida — PICKLIST-DUPLICADA-500

**Fecha** 2026-10-12 · **Dueña** SPEC031 (cola, asignación y ruta de picking; `specs/005-ventas-cuentas-por-cobrar/spec031-*.md`) ·
**Apoyo** SPEC001 (catálogo de errores, `ConflictError`, formato de respuesta), SPEC054 (QA; el mutante que lo
descubrió, `spec054-e2e-flaky-delta.md` §19), SPEC013 (`app/core/integrity.py`, el discriminador de violaciones) ·
**Base** `de8e806` · **Rama** `develop` · **Evidencia** `evidence/picklist-duplicada/`

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` | `de8e806` / `de8e806` / `de8e806` — **coinciden** |
| `ACTUAL_BRANCH` · `WORKTREE_STATE` · `COMMITS_AFTER_DE8E806` · `RUN_DATABASES` | `develop` · limpio · 0 · 0 |
| Puertos 8000/8010/5173 | libres |
| MASTER57 / SPEC057 / NEXT MASTER SPEC | 57 · PLANNED / NOT STARTED · NOT YET PRIORITIZED — sin tocar |

## 2. Localización

| Registro | Valor |
|---|---|
| `ROUTE` | `POST /api/v1/sales/pick-lists` (`app/modules/sales/api.py:493`, `require_write_allowed` + `require_permission("ventas", "create")` + `get_company_context`; responde **200** `{id, code, status}`) |
| `SERVICE` | `app/modules/sales/service.py::create_picklist` (empresa → `_require_order` 404 si el pedido no es de la empresa → `ORDER_NOT_PREPARABLE` si no está `RELEASED`/`PREPARING` → `_require_warehouse` → inserta `PickList` + líneas → `order.updated_at`) |
| `ORM_MODEL` | `app/modules/sales/models.py::PickList` (`__scope__ = COMPANY`; `CheckConstraint pick_list_status`) |
| `MIGRATION` · `CONSTRAINT` | `alembic/versions/0049_spec031_picking_plan.py`: `CREATE UNIQUE INDEX uq_pick_lists_active_order ON pick_lists (order_id) WHERE status IN ('DRAFT', 'CONFIRMED')` — **PARTIAL UNIQUE INDEX**, columna `order_id`, predicado `status IN ('DRAFT','CONFIRMED')`. En el ORM con `.ddl_if(dialect="postgresql")`: **SQLite no lo tiene** |
| `STATES` | `PLAN_STATUSES = DRAFT, CONFIRMED, CLOSED, CANCELLED, INVALIDATED` · `PLAN_ACTIVE_STATUSES = ("DRAFT", "CONFIRMED")` (`models.py:205-209`); el servicio ya usa esa tupla en `confirm_plan` y en la cola |
| Contrato documentado | `spec031-post-d015-implementation-cycle.md:71`: «índice único parcial — **un solo plan activo por pedido**: `(order_id) WHERE status IN ('DRAFT','CONFIRMED')`»; comentario del modelo: «Un pedido no puede tener dos planes vivos a la vez»; `test_spec031_architecture.py:137` exige el índice en migración y ORM |
| `CONSTRAINT_ALIGNMENT` | **PROVEN**: predicado del índice = `PLAN_ACTIVE_STATUSES` = lo que `confirm_plan` y la cola consideran vivo. Sin divergencia, sin migración |
| `PATTERN_409` | `ConflictError(code=…, message=…, details=…)` → handler global → `{code, message, field_errors, request_id, details}` 409. Hermano con constraint real: `treasury/rates.py:160-172` (`begin_nested()` + `except IntegrityError` + `es_violacion_unica(e, "uq_currencies_company_code_active")`, re-lanza si no es esa). El candado consultivo (`roles`, `licensing`) sirve a tablas **sin** constraint de base |
| Discriminador | `app/core/integrity.py::es_violacion_unica(error, restriccion)`: `True` solo si `pgcode == 23505` y `diag.constraint_name == restriccion`; en SQLite siempre `False` (sin diagnóstico) → se re-lanza |
| Código de error | no existía ninguno para «el pedido ya tiene plan vivo». Convención del catálogo: `LOT_DUPLICATE`, `ROLE_DUPLICATE`, `MOVEMENT_TYPE_DUPLICATE`, `DUPLICATE_OBSERVATION` → **`PICKLIST_DUPLICATE`** (nomenclatura técnica dentro del contrato 409 ya cerrado; sin decisión de la dueña) |
| Auditoría | `create_picklist` **no** audita (las auditorías de ventas son de transiciones de pedido y cotización) → nada que emitir ni que silenciar |
| `FRONTEND_CONSUMER` | `src/modules/ventas/preparacion/PreparacionPage.tsx:134-150`: antes de crear consulta `GET /sales/pick-lists?order_id=` y reutiliza el plan `DRAFT`/`CONFIRMED`; si crea y falla, `notify` muestra `ApiError.message`. Con el 409 el usuario leerá el mensaje del contrato: **sin cambio de frontend** |
| OpenAPI | 0 operaciones del repositorio declaran `responses=`: no hay convención de documentar 409 por operación → no se inicia aquí (PL-19 NOT_APPLICABLE); la operación sigue con `BearerAccessToken` (PL-18) |
| Pruebas y E2E existentes | `tests/test_spec031_picking.py` (servicio, `mundo` PostgreSQL), `tests/test_mc_sales_ar_ab.py` (HTTP, 404 cruzado), `e2e/picking.spec.ts` (dueña del flujo; `billing`, `dispatch`, `receivables`, `putaway` crean un plan por pedido) |

## 3. Reproducción antes de tocar nada (`reproduccion-head.txt`)

Suite hostil `tests/test_picklist_duplicada.py` (mundo sintético DEMO/D1 + T2/C2 por la API real, `TestClient`
con `raise_server_exceptions=False` para ver lo que vería un cliente) corrida contra `de8e806`:

| Motor | Primera alta | Segunda alta | Qué pasó |
|---|---|---|---|
| **PostgreSQL** | 200 | **500** `INTERNAL_ERROR` «Ocurrió un error interno. Intente nuevamente.» | `sqlalchemy.exc.IntegrityError` ← `psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "uq_pick_lists_active_order"` sin traducir |
| PostgreSQL, 2 hilos | — | `[200, 500]` | la carrera llega al índice y el perdedor es un 500 |
| PostgreSQL, 10 hilos | — | 1 × 200, **9 × 500** | ídem |
| **SQLite** | 200 | **200** | sin índice parcial, **persiste un segundo plan vivo** para el mismo pedido: el defecto en SQLite no es un 500, es un duplicado silencioso |

`ROW_COUNT_AFTER` (PostgreSQL): 1 (el índice protegió la base); `ORDER_STATE_AFTER`: `RELEASED`;
plan vigente: intacto. La suite falló en lo que debía: 3 pruebas en SQLite, 6 en PostgreSQL; las de
autenticación, permiso, pedido ajeno y «otra violación de integridad» ya pasaban en `HEAD`.

## 4. `/speckit.specify`

FR-PLDUP-001 segunda alta viva → 409 · 002 código estable `PICKLIST_DUPLICATE` · 003/004 sin segundo plan ni
líneas · 005/006 pedido y plan vigente intactos · 007/008 concurrencia: exactamente un éxito y el mismo 409 para
el resto · 009 el índice sigue siendo el respaldo final · 010 otra violación de integridad no se disfraza ·
011 SQLite secuencial también 409 · 012/013/014 sesión, permiso y aislamiento intactos · 015 pedido ajeno
sigue 404 · 016 sin auditoría falsa (no hay auditoría) · 017 el frontend recibe el contrato canónico ·
018 OpenAPI `BearerAccessToken` · 019 sin migración ni cambio del índice · 020/021 estados y ejecución
intactos · 022 LISTADOS-SIN-TOPE aparte · 023 typecheck de e2e vigente · 024 las 4 omisiones de clamscan ·
025 licencia/sync/tasa/reverificación/versión/keep-alive · 026–028 MASTER57, 057, puntero.

## 5. `/speckit.clarify` — 31 puntos

1–6 ruta, servicio, modelo, índice, predicado, estados vivos: §2. 7–13 comportamiento actual y rastro: §3.
14–15 patrón y clase: `ConflictError` + `rates.py`. 16 código: `PICKLIST_DUPLICATE`. 17 discriminación:
`es_violacion_unica(e, "uq_pick_lists_active_order")`. 18 rollback: `begin_nested()` (savepoint) alrededor de
la inserción; al chocar, la sesión sigue viva. 19–20 candado consultivo: **no**: el hermano con constraint real
no lo usa; aquí la base decide y el perdedor recibe el conflicto; un candado solo evitaría llegar al índice,
sin cambiar el contrato. 21 pedido ajeno: `_require_order` 404 **antes** de mirar planes. 22–23 precedencia:
`require_permission` y `get_company_context` en la dependencia, antes del servicio. 24 auditoría: no aplica.
25 frontend: ya reutiliza el plan vivo y muestra el mensaje. 26 OpenAPI: sin convención de 409. 27–28 pruebas:
PL-01…18 (SQLite y PostgreSQL; 2 y 10 hilos; carrera simulada contra el índice). 29 mutaciones: 10. 30 esquema:
0. 31 DeepSeek: 0 (concurrencia, contrato, discriminación y alcance son `CLAUDE_ONLY`; lo mecánico son 38
líneas). `ACTIVE_STATE_CONTRACT`, `DOMAIN_409_CONTRACT`, `CONSTRAINT_ALIGNMENT`, `CONCURRENCY_DESIGN`,
`FOREIGN_SCOPE_BEHAVIOR` = **PROVEN**. `MATERIAL OQ = 0 · UNKNOWN = 0`. Ninguna condición de STOP.

## 6. Compuerta constitucional

G01–G04 ✔ · G05 dueña 031 probada (migración 0049, `spec031-post-d015-implementation-cycle.md`) ✔ · G06–G10
ruta, servicio, índice, predicado, estados ✔ · G11 SQLite reproducido (duplicado silencioso) ✔ · G12
PostgreSQL reproducido (500) ✔ · G13 concurrencia medida (1 × 200 + 9 × 500) ✔ · G14 patrón 409 ✔ · G15
código ✔ · G16 transacción (savepoint) ✔ · G17 discriminación exacta ✔ · G18 diseño de concurrencia ✔ · G19
pedido ajeno 404 ✔ · G20 precedencia 401/403 ✔ · G21 auditoría (no hay) ✔ · G22 frontend sin cambio ✔ · G23
OpenAPI sin cambio ✔ · G24 migraciones 0 ✔ · G25–G26 pruebas y mutaciones ✔ · G27–G30 BLOCKER 0, MATERIAL
OQ 0, UNKNOWN 0, trazabilidad 100 % ✔. **PASS.** Autorización: la del encargo con los cinco PROVEN.

## 7. `/speckit.plan` · `/speckit.tasks`

W01–W21 (§1–§6) · W22–W24 implementación y pruebas (§8) · W25–W27 dirigidas (§9) · W28–W29 suites completas
(§10) · W30 gates de frontend (§9) · W31–W32 E2E (§11) · W33–W35 analyze, trazabilidad, converge.

| Tarea | Requisito | Dueña | EXECUTOR | MODEL | SEC | EGRESS | Ficheros | Acción | DONE_WHEN | Prueba | Mutación | RETRY |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T01 | FR-001…011, 015 | 031 | CLAUDE | n-a | sí (concurrencia, alcance) | n-a | `app/modules/sales/service.py` | `_plan_activo` (alcance de la empresa + `PLAN_ACTIVE_STATUSES`), `_plan_duplicado` (409 con el plan vigente), comprobación previa y `begin_nested()` con traducción solo de `uq_pick_lists_active_order` | PL-01…15 verdes en ambos motores | `test_picklist_duplicada.py` | M-01, M-03…M-10 | — |
| T02 | FR-001…018 | 031/054 | CLAUDE | n-a | sí | n-a | `tests/test_picklist_duplicada.py` (nuevo) | suite hostil: secuencial, cuerpo, rastro, 401/403/404, 2 y 10 hilos, otra violación, carrera simulada, terminales, OpenAPI | 14/14 PostgreSQL, 11 + 3 omitidas SQLite | — | M-12 | — |
| T03 | FR-001/017 | 031/054 | CLAUDE | n-a | no | n-a | `e2e/picking.spec.ts` | escenario «un segundo plan vivo es 409» contra el backend real | dirigida verde; dos globales | E2E | — | — |
| T04 | FR-019…028 | 031 | CLAUDE | n-a | no | n-a | hoja de ruta, `next-spec-decision.md`, recuento | cerrar la deuda; puntero; 57 | ficheros | — | — | — |

`CLAUDE_ONLY 4 · DEEPSEEK_ELIGIBLE 0 · DEEPSEEK CALLS 0` (contrato, concurrencia, discriminación de
integridad y alcance son del encargo `CLAUDE_ONLY`; no quedó matriz mecánica separable).

## 8. Implementación (Claude)

**`app/modules/sales/service.py`** (+38/−2): importa `IntegrityError` y `es_violacion_unica`; constante
`_UN_PLAN_VIVO_POR_PEDIDO = "uq_pick_lists_active_order"`; `_plan_activo(db, company_id, order_id)` con el
**mismo predicado que el índice** (`PLAN_ACTIVE_STATUSES`) y el alcance de la empresa; `_plan_duplicado` →
`ConflictError(code="PICKLIST_DUPLICATE", message="El pedido ya tiene un plan de picking activo; continúe
con ese plan.", details={order_id, picklist_id, status})`. En `create_picklist`, tras `_require_order`
(404), el estado del pedido y el almacén: si hay plan vivo → 409; si no, `with db.begin_nested(): add +
flush`; `except IntegrityError`: si **no** es la violación única de ese índice se re-lanza (`PL-13`), si lo
es se responde el mismo 409 leyendo al ganador. Sin candado, sin reintentos, sin `except` amplio. SQLite:
la comprobación previa basta para el duplicado secuencial (no tiene índice); PostgreSQL: la base decide la
carrera y el perdedor recibe el conflicto.

**`tests/test_picklist_duplicada.py`** (nuevo, 14 pruebas): PL-01/02/03/04/05/06/07/16/17 en una
(secuencial, cuerpo exacto, rastro cero, pedido y plan intactos, sin auditoría); PL-08 401; PL-09 403
`PERMISSION_DENIED`; PL-10 pedido ajeno (otro tenant, con plan vivo) 404 `SALES_ORDER_NOT_FOUND` sin fuga;
PL-11/12 2 y 10 hilos (PostgreSQL) → `[200] + [409]*(n-1)`, una fila; PL-13 un `CHECK` incumplido sigue
siendo `IntegrityError`; PL-14 (PostgreSQL) carrera simulada contra el índice → mismo 409 con el ganador en
`details` y la sesión sigue sirviendo; PL-15 cada estado terminal libera el pedido y cada estado vivo bloquea;
PL-18 `BearerAccessToken`.

**`e2e/picking.spec.ts`** (+19): «un segundo plan vivo para el mismo pedido es un 409 de dominio, no un
500»: segunda alta → 409 `PICKLIST_DUPLICATE`, `details.picklist_id` = el plan del escenario, el listado
sigue con un solo plan.

**Sin cambio:** migraciones (0), índice, estados, `api.py`, `PickListCreate`, frontend de producto, OpenAPI
(544 operaciones), auth, licencia, runner E2E.

## 9. Resultados dirigidos (`suite-hostil-tras-arreglo.txt`, `mutaciones.txt`, `frontend-gates.txt`)

| Gate | Resultado |
|---|---|
| `tests/test_picklist_duplicada.py` SQLite | **11 pasan, 3 omitidas** (PL-11/12/14 son de PostgreSQL: carrera e índice) |
| `tests/test_picklist_duplicada.py` PostgreSQL | **14/14**: 2 hilos `[200, 409]`, 10 hilos `[200] + [409]×9`, una fila; carrera simulada → mismo 409 y sesión viva |
| `ruff check` (servicio y prueba) | limpio |
| `mypy app/modules/sales/service.py` | 86 errores **antes y después**, ninguno en las líneas tocadas (preexistentes, `MYPY-SALES-SERVICE`) |
| Frontend: typecheck (src + herramientas + e2e) · lint · Vitest · build | ✔ · ✔ · **473/473** · ✔ (producto frontend 0) |

**Mutaciones** (GOOD → PASS en ambos motores; MUTATED → FAIL en el motor donde la prueba es autoridad;
RESTORED → PASS; `__pycache__` purgado y `PYTHONDONTWRITEBYTECODE=1`):

| Mutante | Motor | Lo mata | Resultado |
|---|---|---|---|
| M-01 sin comprobación previa (queda solo el índice, que SQLite no tiene) | SQLite | PL-01, PL-15b | muere |
| M-02 quitar el candado consultivo | — | **no aplica**: el diseño no usa candado (decide el índice) | — |
| M-03 la violación del índice ya no se traduce | PostgreSQL | PL-11/12 (500 en la carrera), PL-14 | muere |
| M-04 toda `IntegrityError` se disfraza de duplicado | SQLite | PL-13 | muere |
| M-05 otro código de dominio | SQLite | PL-03 | muere |
| M-06 sin savepoint (la sesión queda rota tras la carrera) | PostgreSQL | PL-14 | muere |
| M-07 el conflicto toca el pedido y lo confirma | SQLite | PL-06 | muere |
| M-08 el conflicto toca el plan vigente y lo confirma | SQLite | PL-07 | muere |
| M-09 el duplicado se mira antes del pedido y sin alcance (409 para un pedido ajeno) | SQLite | PL-10 (y PL-01/15b) | muere |
| M-10 un plan terminal sigue contando como vivo | SQLite | PL-15 ×3 | muere |
| M-11 auditar el rechazo como éxito | — | **no aplica**: el alta no audita | — |
| M-12 el alta deja de exigir `ventas:create` | SQLite | PL-09 | muere |

10 mutantes aplicables, **10 muertos**, 0 equivalentes, 0 supervivientes. M-07 y M-08 confirman la
transacción a propósito: sin `commit` serían equivalentes por la API (la excepción impide el commit de la
petición), y eso también se declara.

## 10. Suites completas de backend (`backend-sqlite-completo.txt`, `backend-postgres-completo.txt`, `intermitente-licensing-central.txt`)

El gancho de resumen del `conftest` no imprime la línea de totales en `-q`; los recuentos salen de la barra
de progreso del log (`.`/`F`/`s`), y la lista `FAILED` se compara una a una con la línea base del cierre de
`ROLES-SIN-API-DE-ALTA`.

| Motor | Resultado | Línea base | Diferencia, clasificada |
|---|---|---|---|
| SQLite | **43 fallos / 1519 pasan / 1024 omitidas** | 44 / 1507 / 1021 | +11 pasan y +3 omitidas (esta suite); **−1 fallo**: `test_auth_session_rotation::test_dos_renovaciones_simultaneas…` (INTERMITTENT de hilos en SQLite, ya clasificado; esta vez pasó). Los 43 = 42 documentales sin `clamscan` (BASELINE, `ENTORNO-SIN-CLAMSCAN`) + `test_warehouse_structure::test_concurrencia…` (BASELINE, `ALMACENES-CARRERA-SQLITE-HILOS`) |
| PostgreSQL | **38 fallos / 2521 pasan / 27 omitidas** | 37 / 2508 / 27 | +14 pasan (esta suite) −1; **+1 fallo**: `test_licensing_central::TestSincronizacion::test_sync_success_records_run_snapshot_and_event` — INTERMITTENT de tiempo ya conocido: la aserción compara `last_reliable_date` con un instante fijado antes y difiere exactamente por lo que tardó la suite (16:34:54 frente a 16:31:35); pasa dirigido (§10.1). Los 37 restantes = 35 documentales + 2 `test_n9_integrity` (BASELINE) |

`TARGET REGRESSION = 0 · NEW INDEPENDENT DEBT = 0 · UNKNOWN = 0`.

### 10.1 El intermitente de licencia, dirigido

`test_sync_success_records_run_snapshot_and_event` dirigido ×3 sobre PostgreSQL tras la E2E: **PASSED ×3**
(`intermitente-licensing-central.txt`). Clasificación: INTERMITTENT de tiempo, ya conocido, ajeno al cambio
(no toca licencia).

## 11. E2E (`e2e-dirigida-picking.txt`, `e2e-global-{1,2}-afectada.txt`, `clasificacion-globales-1-2.txt`, `e2e-global-{3,4}.txt`)

**Dirigida** `picking.spec.ts` (dueña del flujo, con el escenario nuevo) `r20261012t165318p2920432na1df6b`:
**9/9**, incluido «un segundo plan vivo para el mismo pedido es un 409 de dominio, no un 500».

**Globales 1 y 2** (`r20261012t165344…`, `r20261012t165715…`): 267 pasan, **2 fallan**, 4 omitidas, 4 «no
corrieron» (los proyectos de licencia dependen de `chromium`). Los cuatro fallos son **distintos** entre
corridas (`pick-execution:297`, `picking:192` · `dispatch:342`, `documents-a11y:64`) y **idénticos** en
causa: `locator.fill` agotado a los 30 s «waiting for getByLabel(/Empresa \(código\)/)» — el formulario de
acceso no se pintó —, antes de tocar ningún endpoint del cambio. Es la deuda abierta
`E2E-PANTALLA-SIN-PINTAR`, no absorbida. Prueba independiente de la clasificación, **antes** de correr nada
más: `backend.log` de ambas corridas con 0 errores; reloj estable; el host con una interfaz VPN activa
(`proton0`, el disparador de cambio de red que esa deuda documenta); y las cuatro suites afectadas pasan
dirigidas en una base nueva (**27/27**, 1 omitida por clamscan). El escenario nuevo pasó en ambas globales.

**Globales 3 y 4**, consecutivas, permitidas solo por esa clasificación (sin «correr hasta verde»):

| Corrida | Id | passed | failed | skipped | Suite | Limpieza |
|---|---|---|---|---|---|---|
| Referencia (cierre de E2E-SIN-TYPECHECK) | `r20261012t134227p2519190n8e265a` | 272 | 0 | 4 | 231,0 s | LIMPIA |
| Global 3 | `r20261012t170254p2976305nb21064` | **273** | **0** | **4** | 226,3 s | LIMPIA |
| Global 4 | `r20261012t170658p3002221ne206cf` | **273** | **0** | **4** | 225,5 s | LIMPIA |

272 + 1 (el escenario nuevo) = 273. Las 4 omitidas son las de `ENTORNO-SIN-CLAMSCAN` (PL-22). Bases de
corrida residuales: **0**. Corridas adicionales: las dos declaradas, con su motivo.

## 12. `/speckit.analyze` final y trazabilidad

`DUPLICATE_PICKLIST_500 0 · DUPLICATE_ACTIVE_PICKLIST_ROW 0 · PARTIAL_PICKLIST_PERSISTENCE 0 ·
ORDER_MUTATED_ON_CONFLICT 0 · EXISTING_PICKLIST_MUTATED_ON_CONFLICT 0 · CONCURRENT_MULTI_SUCCESS 0 ·
CONCURRENT_500 0 · BROAD_INTEGRITYERROR_TRANSLATION 0 · UNRELATED_INTEGRITYERROR_AS_DUPLICATE 0 ·
TRANSACTION_LEFT_BROKEN 0 · ACTIVE_STATE_CONTRACT_MISMATCH 0 · CONSTRAINT_CHANGED 0 · CLIENT_SCHEMA_CHANGE 0 ·
CENTRAL_SCHEMA_CHANGE 0 · FOREIGN_ORDER_CONFLICT_LEAK 0 · AUTH_REGRESSION 0 · PERMISSION_REGRESSION 0 ·
REQUESTCONTEXT_REGRESSION 0 · AUDIT_FALSE_SUCCESS n/a (no audita) · OPENAPI_SECURITY_REGRESSION 0 ·
E2E_TYPECHECK_REGRESSION 0 · CLAMSCAN_SKIP_REGRESSION 0 · ROLE_CREATE_REGRESSION 0 · LICENSING_REGRESSION 0 ·
KEEPALIVE_75_REGRESSION 0 · VERSION_PANEL_REGRESSION 0 · LISTADOS_SIN_TOPE_ABSORBED 0 ·
PRODUCTION_502_SCOPE_EXPANSION 0 · SPEC057_STARTED 0 · NEXT_MASTER_SPEC_SELECTED 0 · RETRY_WORKAROUND 0 ·
SLEEP_WORKAROUND 0 · TIMEOUT_INFLATION 0 · SECRET_EXPOSURE 0 · BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 ·
OWNER CONFLICT 0 · ORPHAN REQUIREMENTS 0 · ORPHAN TASKS 0 · MATERIAL OQ 0 · UNKNOWN 0 · TRACEABILITY 100 %.`

PICKLIST-DUPLICADA-500 → `POST /sales/pick-lists` → `create_picklist` → contrato «un solo plan activo por
pedido» (`PLAN_ACTIVE_STATUSES` = predicado del índice) → `uq_pick_lists_active_order` → reproducción (500
en PostgreSQL, duplicado silencioso en SQLite) → 409 `PICKLIST_DUPLICATE` → concurrencia (índice como
respaldo, savepoint, traducción exacta) → PL-01…18 → M-01…M-12 → E2E dirigida y globales → evidencia.
FR-PLDUP-001…028 → T01–T04 → pruebas → mutaciones → evidencia: 100 %.

## 13. Convergencia

**`PICKLIST-DUPLICADA-500 — CLOSED / CONVERGED`.** El 500 era un `UniqueViolation` sin traducir; ahora es
un 409 de dominio con el plan vigente, sin rastro, sin tocar pedido ni plan, con 401/403/404 por delante,
exactamente un ganador bajo concurrencia y el índice intacto como respaldo final; en SQLite, donde no hay
índice, la comprobación previa cierra el duplicado silencioso que también existía. Migraciones 0; producto
frontend 0; OpenAPI 544 sin cambio. 14 pruebas backend + 1 E2E; 10/10 mutantes muertos; suites completas sin
regresión (SQLite 43/1519/1024, PostgreSQL 38/2521/27, fallos clasificados uno a uno); E2E 273/0/4 ×2 tras
clasificar con prueba independiente dos globales afectadas por `E2E-PANTALLA-SIN-PINTAR`. Orquestación: 4
tareas `CLAUDE_ONLY`, 0 DeepSeek. Hoja de ruta, `next-spec-decision.md` y recuento MASTER57 (57) actualizados.
