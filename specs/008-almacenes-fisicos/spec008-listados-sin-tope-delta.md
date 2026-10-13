# SPEC 008 · Delta dirigida — LISTADOS-SIN-TOPE

**Fecha** 2026-10-13 · **Dueñas** SPEC008 (`GET /organization/warehouses`; este directorio) y SPEC031 (`GET /sales/pick-lists`;
enlace cruzado en `specs/005-ventas-cuentas-por-cobrar/spec031-listados-sin-tope-delta.md`) · **Apoyo** SPEC001 (contrato
de listados `api-contracts.md:11` y deltas `spec001-empresas-sobre-delta.md`, `spec001-auditoria-paginacion-delta.md`),
SPEC054 (E2E, QA, pruebas de contrato), SPEC012 (matrices de API) · **Antecedente** `specs/012-auditoria-integral-e2e/
spec054-e2e-flaky-delta.md` §19 (donde nació la deuda) y la delta WHL (`tests/test_warehouse_list_cost.py`, contrato
`{total, limit, offset, items}` del listado de almacenes) · **Base** `6202994` · **Rama** `develop` · **Evidencia**
`evidence/listados-sin-tope/`

Ciclo de contrato de producto: discovery-first, convención antes que diseño, reproducción antes que corrección; sin cambio
silencioso de contrato, sin cambio de alcance de empresa, sin migración.

## 1. Checkpoint

`6202994` = HEAD = origin/develop · `develop` · limpio · 0 bases · 0 schemas `t_` · 0 dirs temporales · puertos libres · MASTER57 /
SPEC057 / NEXT MASTER SPEC sin tocar. El equipo se reinició entre ciclos: PostgreSQL de QA relanzado y `ktest` recreada
(`evidence/.../checkpoint.md`).

## 2. Descubrimiento

### 2.1 Inventario transversal — `collection-inventory.md`
177 `GET` candidatos: **17** canónicos (`page`/`page_size` ≤ 100, sobre `{items,total,page,page_size}`), **8** `limit/offset`
sin máximo (entre ellos el objetivo de almacenes), **79** con sobre falso (`page` 1, `page_size` = `len(items)`: sin paginar;
entre ellos el objetivo de pick-lists), resto `N_A`; `UNKNOWN 0`. Solo los dos objetivos se corrigen; los otros 85 se
registran como `ADDITIONAL_UNBOUNDED_LISTING` (§13), sin corregir «de paso» (FR-LT-014).

### 2.2 Convención — `pagination-convention.md`, `limit-convention.md`
`CANONICAL_ENVELOPE {items,total,page,page_size}` · `page` ≥ 1 (1) · `page_size` 1..**100** (20) · fuera de rango **422** ·
página más allá del final vacía con el mismo `total` · `total` dentro del alcance y de los filtros, antes de cortar · orden
determinista con desempate por `id` (precedente ratificado: empresas). **Fuente**: Spec 001 (`api-contracts.md:11`) transcrita
como canon en dos deltas convergidas (FR-001-177/179/188, AC-043..047). Para almacenes, el estilo `limit/offset` y el defecto
50 son contrato WHL vigente y no cambian; el tope (100), el mínimo (1), `offset` ≥ 0 y el 422 son la aplicación del canon de
plataforma al tamaño de página. `CONVENTION_IDENTIFIED = YES` · `LIMIT_MAX_RATIFIED = YES` · `ENVELOPE_RATIFIED = YES` ·
`OVER_LIMIT = 422` ratificado.

### 2.3 Reproducción — `warehouses-and-picklists-before.md`
Mundo sintético (1 100 listas y 300 almacenes en D1; 50 listas y 1 almacén en C2). **Almacenes**: `limit=100000` → 200 con
300 filas (175 KB); `limit=0` → 200 vacío; `limit=-1` y `offset=-1` → **500** en PostgreSQL (SQLite devuelve todo); `abc` → 422.
**Pick-lists**: 1 100 filas, **203 550 bytes**, `page`/`page_size` ignorados (`page=0`, `page=abc` → 200 con todo); alcance de
empresa correcto (las 50 de C2 no aparecen). `WAREHOUSE_UNBOUNDED = PROVEN` · `PICKLIST_UNPAGINATED = PROVEN`.

### 2.4 Consumidores — `consumer-inventory.md`
Almacenes: 9 pantallas sin `limit` (defecto 50, sin cambio), `PreparacionPage` (`tanda = 200`), `PutAwayPage` (`limit=500`), 2
suites E2E con `limit=500`, 1 guion QA con 200/500, 1 suite backend con 200/500 (mundo de 46 almacenes). Pick-lists:
`PreparacionPage` y 2 suites E2E filtran por `order_id` (página por defecto sobra); `putaway.spec.ts:413` necesita todas las
de la empresa. `EXPECTS_RAW_ARRAY 0` · `CONSUMERS_UNKNOWN 0`.

### 2.5 OpenAPI antes — `openapi-before.md`
544 operaciones · 533 protegidas · 11 públicas · `BearerAccessToken`; `limit`/`offset` sin límites; pick-lists sin `page`/`page_size`.

## 3. Decisiones de contrato (`contract-decision.md`)

| Decisión | Valor | Fuente |
|---|---|---|
| Almacenes: `limit` | `Query(50, ge=1, le=100)` — defecto 50 (WHL), tope 100 (canon), 422 fuera de rango | §2.2 |
| Almacenes: `offset` | `Query(0, ge=0)` — 422 si negativo (hoy 500 en PostgreSQL) | validación canónica |
| Almacenes: sobre y orden | `{total, limit, offset, items}`, `code` asc — sin cambio | WHL |
| Pick-lists: parámetros | `order_id`, `page: Query(1, ge=1)`, `page_size: Query(20, ge=1, le=100)` | canon |
| Pick-lists: sobre | `{items, total, page, page_size}` con `total` contado en SQL dentro de la empresa y del filtro, antes de cortar | canon, FR-001-179 |
| Pick-lists: orden | `created_at desc, id` (el negocio actual + desempate del precedente) | `organization/api.py:100` |
| Consumidores que necesitan todo | recorren páginas con el máximo (100) | FR-001-188 (`listAllCompanies`) |
| Alcance de empresa | sin cambio: contexto validado → filtro de empresa → filtros → `count` → orden → `offset`/`limit` | FR-LT-007/008 |

`ORDERING_CONTRACT = PROVEN` · `TENANT_SCOPE_PRESERVED = PROVEN` (reproducción + LT-12..14) · `MATERIAL OQ = 0`.

## 4. `/speckit.specify`
FR-LT-001…030 del encargo, tal cual (tope ratificado, 422, sobre canónico en pick-lists, `total` antes de cortar, orden
determinista, aislamiento intacto, filtros intactos, página vacía más allá del final, consumidores adaptados sin relajar
aserciones, endpoints conformes sin cambio, OpenAPI documentado, seguridad intacta, sin migración, 409 PICKLIST_DUPLICATE
intacto, RequestContext/`X-Kontrol-Company` intactos, cierres previos intactos, MASTER57/057/puntero sin cambio).

## 5. `/speckit.clarify`
1–3 inventario, sobre y tope: §2.1–2.2 · 4 por encima del máximo: 422 · 5–6 defecto/offset: 20 (canon) para pick-lists, 50
(WHL) para almacenes; `offset` ≥ 0 · 7 orden: `created_at desc, id` · 8–11 comportamiento actual y medidas: §2.3 · 12 orden de
la consulta: contexto → empresa → filtros → `count` → orden → corte · 13 `total`: `count` sobre la subconsulta (patrón de
almacenes y empresas) · 14 filtros: `order_id` conservado · 15–19 consumidores: §2.4; raw array 0 · 20 pantalla: ninguna
lista pick-lists en tabla (`PreparacionPage` es una cola; busca el plan vivo por `order_id`); no hay UX nueva · 21 OpenAPI:
544 sin cambio; `limit`/`offset` con límites; `page`/`page_size` nuevos en pick-lists · 22 errores: 422 `VALIDATION_ERROR` ·
23 rendimiento: primera página de 20 ≪ 203 KB · 24 pruebas hostiles LT-01…24 · 25 mutaciones M-01…M-12 · 26 suites
completas ambos motores + frontend gates · 27 E2E: fuente E2E y frontend cambian → **dos** globales · 28 DeepSeek: T01/T05
(mecánico) y T04 (ayudante espejo de `listAllCompanies`).

## 6. `/speckit.plan`
W01–W17 ✔ (reconciliación, inventario, convención, reproducción, dataset >1 000, consumidores, pantalla, E2E/QA, alcance,
orden, `total`, OpenAPI antes, decisión: sin blocker) · W18–W24 diseño, pruebas, mutaciones, clasificación, analyze,
trazabilidad · W25 almacenes (T01) · W26 pick-lists (T02) · W27 frontend (T04) · W28 E2E/QA/pruebas (T05) · W29–W30
dirigidas backend/frontend · W31 mutaciones · W32–W33 completas · W34 frontend gates · W35 OpenAPI · W36 E2E ×2 · W37
rendimiento después · W38–W40 analyze, trazabilidad, converge.

## 7. CONSTITUTION GATE
G01–G06 ✔ · G07 inventario completo ✔ · G08 UNKNOWN 0 ✔ · G09 sobre ✔ · G10 tope 100 ✔ · G11 422 ✔ · G12–G13 reproducidos ✔ ·
G14 consumidores ✔ · G15–G16 contratos frontend/E2E/QA conocidos ✔ · G17 alcance probado ✔ · G18 orden ✔ · G19 `total` ✔ ·
G20 OpenAPI antes ✔ · G21–G22 sin migración ni esquema ✔ · G23–G24 pruebas y mutaciones definidas ✔ · G25–G33 BLOCKER 0 ·
CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0 · ORPHAN 0/0 · MATERIAL OQ 0 · UNKNOWN 0 · TRAZABILIDAD 100 % → **PASS**.
Autorización expresa del encargo: condiciones cumplidas.

## 8. `/speckit.tasks`

| ID | Requisitos | EXECUTOR / MODEL | TARGET_FILES | Acción | DONE_WHEN |
|---|---|---|---|---|---|
| T01 | FR-LT-001/002/011/015 | **DEEPSEEK_ELIGIBLE** / flash (restricción `Query` mecánica) | `app/modules/organization/warehouse_api.py` | `limit: Query(50, ge=1, le=100)`, `offset: Query(0, ge=0)` | LT-01…03 verdes |
| T02 | FR-LT-003…010 | **CLAUDE_ONLY** (alcance de empresa, `total`, orden) | `app/modules/sales/api.py` | paginación canónica de pick-lists | LT-04…15, 23 verdes |
| T03 | FR-LT-001…011, 019 | **CLAUDE_ONLY** | `tests/test_listados_sin_tope.py` | LT-01…16, 23, 24 + invariante estático (M-09) | verdes en ambos motores |
| T04 | FR-LT-012 | **DEEPSEEK_ELIGIBLE** / flash (espejo de `listAllCompanies`) | `src/api/{types,organization,organization.test}.ts`, `PutAwayPage.tsx`, `PreparacionPage.tsx` | `listAllWarehouses` + pruebas + consumo | typecheck/lint/Vitest |
| T05 | FR-LT-013 | **DEEPSEEK_ELIGIBLE** / flash (sustituciones mecánicas) | `test_warehouse_list_cost.py`, `qa/repro-almacenes-listado.py`, `e2e/putaway.spec.ts`, `e2e/picking.spec.ts` | `limit=200/500 → 100`; helper E2E que recorre páginas de pick-lists | suites y typecheck E2E |
| T06 | FR-LT-014…030 | **CLAUDE_ONLY** | — | mutaciones, suites, gates, OpenAPI, E2E ×2, rendimiento, converge | §12–13 |

Todos: `SECURITY_SENSITIVE` solo T02/T03 (alcance de empresa; Claude) · `EGRESS_SAFE` sí · `RETRY_MAX 2`.

## 9. `/speckit.analyze` previo y trazabilidad
Búsqueda: `Query(le` (17 canónicos + T01) · `limit: int = 50` (8; solo almacenes cambia) · `"page": 1, "page_size": len(` (79;
solo pick-lists cambia) · `company_id`/`RequestContext`/`X-Kontrol-Company` (sin cambio) · `order_by` (desempate añadido solo
en pick-lists) · `.scalars().all()` sin corte (pick-lists → con corte) · `limit=100000` (reproducido) · `useQuery`/`apiFetch`
(2 pantallas) · `UNKNOWN` 0. `SCHEMA_CHANGE 0` · `MIGRATION 0` · BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0 ·
ORPHAN 0/0 · MATERIAL OQ 0 · UNKNOWN 0 · TRAZABILIDAD 100 %.

## 10. `/speckit.implement` — por tarea

### T01 · `warehouse_api.py` (DEEPSEEK_ELIGIBLE · flash) + T05 · consumidores (DEEPSEEK_ELIGIBLE · flash), un lote
```
[EXECUTE]  DeepSeek deepseek-v4-flash · 1 llamada: 2137/2231 tokens, $0.000906
[AUDIT]    PASS — 16 bloques, solo ficheros objetivo, firmas y valores exactos del contrato; aplicados verbatim
[TEST]     ruff limpio · LT + WHL + estructura + duplicada: SQLite 88 ejecutadas 0 fallos (4 omitidas PG-only preexistentes)
[STATUS]   COMPLETE
```
### T02 · `sales/api.py` (CLAUDE_ONLY: alcance de empresa, `total`, orden)
```
[PLAN]     page/page_size canónicos; count en SQL dentro de empresa+filtro; created_at desc, id; offset/limit en SQL
[EXECUTE]  Claude   [AUDIT] PASS (ruff; sin migración; alcance intacto)   [TEST] LT-04…15, 23, SQL   [STATUS] COMPLETE
```
### T03 · `tests/test_listados_sin_tope.py` (CLAUDE_ONLY)
```
[EXECUTE]  Claude   [TEST] 29 pruebas: SQLite y PostgreSQL verdes   [STATUS] COMPLETE
```
### T04 · frontend (DEEPSEEK_ELIGIBLE · flash)
```
[EXECUTE]  DeepSeek deepseek-v4-flash · 1 llamada: 4857/3288 tokens, $0.001583
[AUDIT]    PASS — 9 bloques, espejo de listAllCompanies, sin imports huérfanos, sin UX nueva; aplicados verbatim
[TEST]     tsc -b --noEmit OK · eslint --max-warnings 0 OK · vitest organization.test.ts 9/9
[STATUS]   COMPLETE
```
Egress en las dos llamadas: `ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0 REAL_PATHS=0`.

### T06 · verificación (CLAUDE_ONLY)
Dirigidas PostgreSQL (LT, WHL, estructura, duplicada, picking 031/032, OpenAPI): 165/165 · OpenAPI 544/533/11 con
exactamente 2 operaciones cambiadas · mutaciones 12/12 (M-03 mal formado → M-03b) · rendimiento después · suites
completas, gates de frontend y dos globales E2E en §12.

## 11. Observaciones registradas, no absorbidas

| | |
|---|---|
| **`ADDITIONAL_UNBOUNDED_LISTING`** (85 listados) | 7 con `limit/offset` sin máximo (`organization/locations`, `organization/locations/ordered`, `warehouse_api.py:974`, `maestros/unidades`, `approvals/inbox`, `documents`) y 78 con sobre falso `{page: 1, page_size: len(items)}` (fiscal 12, tesorería 23, regulación 11, ventas 12, compras 8, inventario 8, informes 2, homologación 2). Mismo tipo de deuda que esta, con dueñas distintas (varias fiscales, intocables en estos ciclos) y consumidores sin inventariar; cada una exige su propio inventario de consumidores. `evidence/.../collection-inventory.md` |
| `ALMACENES-PAGINACION-LIMIT-OFFSET` | 8 listados usan `limit/offset` y el sobre `{total, limit, offset, items}` en vez del canon `page/page_size`; cambiar los nombres rompería consumidores (12 pantallas, 10 suites E2E en almacenes) y reabriría la delta WHL: decisión de las dueñas, no de este ciclo |
| Reinicio del equipo entre ciclos | el directorio de datos de PostgreSQL de QA vive en el temporal: tras un reinicio hay que relanzarlo y recrear `ktest` (`checkpoint.md`) |
| Guion de medición | `repro.py` crea un schema del arnés y no lo suelta (no es una prueba; no pasa por PGLIFE): los dos schemas que dejó se purgaron con `qa/pg-test-residuos.py --purgar` (0 residuales); anotado para no confundirlo con un residuo de la suite |

## 12. Resultados

| Certificación | Resultado | Evidencia |
|---|---|---|
| Pruebas hostiles LT (29) | SQLite y PostgreSQL verdes; 422 en todo lo fuera de contrato (antes 200 con todo o 500); sobre exacto; páginas sin solape; orden con desempate; empresa y empresa ajena; `total` con filtro; > 1 000 filas → una página de 20 (< 6 KB); corte en SQL | `hostile-tests.md` |
| Dirigidas | SQLite 88 (4 omitidas PG-only preexistentes) · PostgreSQL 165 (LT, WHL, estructura, duplicada, picking 031/032, OpenAPI): 0 fallos | `hostile-tests.md` |
| Mutaciones | **12/12 muertas** (M-03 mal formado → M-03b) | `mutation-campaign.md` |
| SQLite completa | **42 / 1609 / 1040** (ref. 43 / 1582 / 1040): 42 ClamAV; la carrera de almacenes hoy pasa; +27 = LT; omitidas iguales; **TARGET_REGRESSION 0 · UNKNOWN 0** | `sqlite-full.md` |
| PostgreSQL completa | **38 / 2625 / 28** (ref. 37 / 2600 / 28): 35 ClamAV + 2 `n9_integrity` + 1 intermitente temporal conocido (PASSED ×3); +25 = LT; omitidas iguales; schemas residuales de la suite 0 | `postgres-full.md` |
| Frontend | typecheck (src + herramientas + e2e) ✔ · lint ✔ · Vitest **481/481** (477 + 4) · build ✔ | `frontend-gates.md` |
| OpenAPI | **544 / 533 / 11**, `BearerAccessToken`, mismo conjunto de públicas; exactamente 2 operaciones cambian su documento (`limit` 1..100, `offset` ≥ 0; `page` ≥ 1, `page_size` 1..100; 422 declarado) | `openapi-after.md` |
| E2E | corrida 1: 266/3/4 con 3 fallos **clasificados como intermitente de arnés independiente** (ayudante de empresa, carrera de pintado; sin relación con el ciclo); corridas 2 y 3: **273/0/4** y **273/0/4**; las 4 omitidas = ClamAV; 0 bases, puertos libres | `global-e2e.md` |
| Rendimiento | pick-lists 203 550 B → 3 748 B por página (−98 %); `limit=100000` → 422 en 6 ms; negativos: 500 → 422 | `performance-after.md` |
| LT-16 / 409 | `test_picklist_duplicada` 10/10 y M-12 muerto | `hostile-tests.md` |
| LT-17…19 frontend | `PutAwayPage` y `PreparacionPage` consumen `listAllWarehouses`; `PreparacionPage` sigue leyendo `items` de `?order_id=`; sin paginador nuevo ni UX nueva | `frontend-consumer.md` |
| LT-20/21/22 | OpenAPI ✔ · QA: `repro-almacenes-listado.py` a 100; `functional-e2e-*` sin cambio (defecto 50) ✔ · E2E picking equivalentes sin relajar aserciones ✔ | — |

## 13. `/speckit.analyze` final, trazabilidad y veredicto

Búsqueda sobre el árbol final: `unbounded list` / `limit without le` → almacenes con `le=100` (los otros 7 `limit/offset`
registrados en §11) · `limit 100000` → 422 (LT-02) · `pick-lists raw array` → 0 (`EXPECTS_RAW_ARRAY 0`) · `all().scalars`
sin corte en pick-lists → 0 (LT-SQL; M-09) · `pagination after filtering` → orden contexto → empresa → filtros → count →
orden → corte (M-08) · `company leak` / `total cross-company` → 0 (LT-12/13/14; M-07) · `offset ignored` → 0 (M-05) ·
`unstable order` → 0 (LT-11; M-06) · `frontend raw array` → 0 (M-10) · `QA first page only` → 0 (M-11; helper E2E recorre
páginas) · `OpenAPI missing max` → 0 · `schema migration` / `new migration` → 0 · `picklist duplicate regression` → 0 (M-12)
· `auth regression` / `OpenAPI security regression` → 0 (544/533/11) · `harness regression` → 0 (PGLIFE, volumen, schema por
módulo intactos) · `skip` / `xfail` / `sleep` / `retry` → 0 (omitidas 1040 = 1040, 28 = 28) · `SPEC057` / `NEXT MASTER` →
sin cambio · `UNKNOWN` → 0.

`UNBOUNDED_WAREHOUSE_LIMIT 0` · `UNPAGINATED_PICKLIST_COLLECTION 0` · `NONCANONICAL_LIMIT_MAX 0` ·
`NONCANONICAL_OVERLIMIT_BEHAVIOR 0` · `PICKLIST_ENVELOPE_MISMATCH 0` · `TOTAL_COUNT_MISMATCH 0` · `OFFSET_IGNORED 0` ·
`UNSTABLE_ORDER 0` · `TENANT_SCOPE_CHANGE 0` · `CROSS_COMPANY_ITEM_LEAK 0` · `CROSS_COMPANY_TOTAL_LEAK 0` ·
`FILTER_SEMANTIC_REGRESSION 0` · `FRONTEND_CONSUMER_REGRESSION 0` · `QA_CONSUMER_TRUNCATION 0` · `E2E_CONSUMER_REGRESSION 0` ·
`OPENAPI_LIMIT_DOC_MISSING 0` · `OPENAPI_SECURITY_REGRESSION 0` · `AUTH_REGRESSION 0` · `PICKLIST_409_REGRESSION 0` ·
`SCHEMA_CHANGE 0` · `MIGRATION_ADDED 0` · `BACKEND_HARNESS_REGRESSION 0` · `INSTALLATION_VOLUME_REGRESSION 0` ·
`PG_SCHEMA_OPTIMIZATION_REGRESSION 0` · `E2E_TYPECHECK_REGRESSION 0` · `E2E_CAPTURE_REGRESSION 0` · `CLAMSCAN_SKIP_REGRESSION 0`
· `KEEPALIVE_75_REGRESSION 0` · `VERSION_PANEL_REGRESSION 0` · `E2E_PANTALLA_ABSORBED 0` · `PRODUCTION_502_SCOPE_EXPANSION 0` ·
`SPEC057_STARTED 0` · `NEXT_MASTER_SPEC_SELECTED 0` · `TEST_ORDER_WORKAROUND 0` · `NEW_SKIP 0` · `ASSERTION_WEAKENING 0` ·
`RETRY_WORKAROUND 0` · `SLEEP_WORKAROUND 0` · `SECRET_EXPOSURE 0` · BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER
CONFLICT 0 · ORPHAN REQUIREMENTS 0 · ORPHAN TASKS 0 · MATERIAL OQ 0 · UNKNOWN 0 · **TRAZABILIDAD 100 %** (`traceability-matrix.md`).

Orquestación: tareas 6 · `CLAUDE_ONLY` 3 (T02, T03, T06) · `DEEPSEEK_ELIGIBLE` 3 (T01+T05 en un lote, T04) · ejecutadas por
DeepSeek 2 llamadas (`deepseek-v4-flash`; 0 rechazos; ≈ 6 994 tokens de entrada / 5 519 de salida; ≈ $0.0025) ·
implementadas por Claude 3 · pruebas nuevas 29 backend + 4 Vitest · mutaciones 12/12 · regresiones 0.

**Veredicto: `LISTADOS-SIN-TOPE — CLOSED / CONVERGED`.** Commit y push a `origin/develop` al cierre.
