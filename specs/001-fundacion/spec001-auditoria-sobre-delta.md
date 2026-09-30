# SPEC 001 · DELTA DIRIGIDO AUDITORIA-SOBRE-VS-ARRAY — LA PANTALLA DE AUDITORÍA PINTA LO QUE RECIBE

> Delta de frontend dentro de la Spec 001 (Fundación), dueña del endpoint, del modelo,
> de `AuditoriaPage` y del contrato `api-contracts.md`; Spec 012 (QA integral, Master
> 054) como apoyo de certificación. Cierra `AUDITORIA-SOBRE-VS-ARRAY`
> (`AUDIT-UI-ENVELOPE-MISMATCH`). No toca el backend, ni la búsqueda `q` (decisión
> pendiente), ni la columna «Fecha» (`AUDITORIA-CREATED-AT`, deuda separada).

## 0. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` | `735254e` / **`735254e`** — coinciden |
| `ACTUAL_BRANCH` | `develop` |
| `COMMITS_AFTER_735254E` | **0** |
| `PRESERVED_ARTIFACT_1` / `_2` | `KONTROL_MASTER_COMPLETENESS_AUDIT.md` · `qa/audits/KONTROL-AUDIT-POLICY-CLOCK-LOCAL-20260917/` — sin seguimiento, intactos |
| `WORKTREE_STATE` | 1.550 cambios **solo de modo**: `WORKTREE_ENVIRONMENT_NOISE`, excluidos con `core.fileMode=false` |
| `AUDIT-EVENTS-SIN-TENANT` | sigue **CLOSED / CONVERGED** (`e6968fe`); su suite de 11 pruebas se vuelve a ejecutar aquí |

### Entorno, reparado localmente y fuera del repositorio

`.venv/bin/python*` eran ficheros aplanados (`IntxLNK`) hacia un `python3.11` inexistente, y los
26 guiones de `.venv/bin/` (alembic, pytest, uvicorn…) llevaban en su primera línea la ruta
antigua del repositorio (`/home/maria/Proyectos/kontrol/...`). Se enlazaron los tres intérpretes
al CPython 3.11.16 que `uv` ya tenía y se reescribió esa primera línea. Nada de esto está bajo
seguimiento de git. Consecuencia: `alembic` y `pytest` del `.venv` vuelven a ejecutarse, y con
ellos `declararAlcance` del E2E y los 13 ficheros de prueba de migraciones que invocan
`.venv/bin/alembic` por ruta fija (`TEST-MIGRACIONES-VENV-FIJO` sigue abierta: la ruta fija
sigue siendo fija). Firefox y WebKit se instalaron para la matriz de la Spec 054.

## 1. Veredicto, por delante

**La pantalla pedía un array a un servidor que responde un sobre.** `apiFetch<T>` no podía
contradecirla: su genérico es una afirmación de quien llama. Fix: una función tipada para la
petición y `items` como filas. Ficheros de producto: **2** (`src/api/audit.ts`, nuevo, y
`src/pages/AuditoriaPage.tsx`, tres líneas). Backend: **0**. Esquema, migraciones: **0**. Forma
pública de la API: **sin cambio**.

## 2. Dueñas

| Papel | Spec | Evidencia |
|---|---|---|
| **Principal** | **SPEC 001 — Fundación** | `AuditoriaPage.tsx` (`WF-01`, `FR-001-070`), `audit/api.py`, `api-contracts.md:71`, `PagedResult<T>` en `api/types.ts:93`; el roadmap la nombraba (junto a 012) |
| Contrato | **SPEC 001** (`api-contracts.md`: «Timeline con filtros y paginación»; contrato de listados «page, page_size»; `ADR-012`) | §5 |
| QA | **SPEC 012** (Master 054) | pruebas de página, E2E, matriz de navegadores |

El Master 006 «Auditoría/observabilidad» se implementa en `001-fundacion` + `009` (mapa de
equivalencia); `006-tesoreria` es tesorería. `OWNER_IDENTITY_CONFLICT = 0`.

## 3. La evidencia original, recuperada

`aae7cd2` · `spec001-dead-search-analysis.md §7` y `evidence/dead-search/auditoria-lo-que-habia-debajo.txt`:

| | |
|---|---|
| `AUDITORIA_PAGE_FILE` | `resources/frontend/src/pages/AuditoriaPage.tsx` |
| `REQUEST_FUNCTION` | `apiFetch<AuditEvent[]>(\`/audit/events?q=…\`)` en la línea 30, dentro de `useQuery` |
| `FRONTEND_EXPECTED_TYPE` | `AuditEvent[]` |
| `BACKEND_RESPONSE_MODEL` | ninguno declarado: el handler devuelve un `dict` `{page, page_size, total, items}` |
| `DATATABLE_USAGE` | `data={query.data ?? []}` (línea 46): el sobre entero como lista |

## 4. Reproducción, antes de tocar nada

Pila real: backend `127.0.0.1:8000` sobre `kaud` (PostgreSQL), Vite `5173`, Chromium, sesión
`admin`/DEMO entrando por el menú «Sistema → Auditoría». Evidencia:
`evidence/auditoria-sobre/reproduccion-{ui,api}-pre-fix.txt`.

| Medida | Valor |
|---|---|
| Petición | `GET /api/v1/audit/events?q=` → 200 |
| Forma del cuerpo | **OBJETO**, claves `items, page, page_size, total` |
| `items.length` / `total` / `page` / `page_size` | **20** / 108 (`number`) / 1 (`number`) / 20 (`number`) |
| Filas en la tabla | **0** |
| Estado vacío «Sin eventos» | **no visible** |
| Error visible | ninguno |
| Consola | un aviso de hidratación del router y un 401 del refresco de sesión al cargar; ninguno de la tabla |

La tabla recibía un objeto donde espera un array: `data.length` es `undefined`, la tabla ni pinta ni
avisa. Por API, la misma forma: `KEYS = [items, page, page_size, total]`, `ITEMS_TYPE = list`,
`TOTAL_TYPE = PAGE_TYPE = PAGE_SIZE_TYPE = int`; el item publica `event_time` y **no**
`created_at`.

## 5. El contrato del sobre es contractual, no incidental

| Fuente | Qué dice |
|---|---|
| `api-contracts.md:71` | `GET /api/v1/audit/events` — «Timeline con filtros y **paginación**» |
| `api-contracts.md`, contrato de listados | «Listados con `q`, `status`, `sort`, `page`, `page_size`» |
| `ADR-012` | «Endpoint de timeline con permisos» |
| `audit/api.py::list_events` | devuelve `{page, page_size, total, items}` desde su primera versión |
| `tests/test_audit_tenant_isolation.py` | fija `body["items"]` y `body["total"]` (11 pruebas) |
| `e2e/approvals.spec.ts:300` | consume `.items` |
| Siete pantallas del frontend | tipan sus listados como `PagedResult<T>` o `{ items: T[] }` |
| OpenAPI | `responses.200.content.application/json.schema = {}`: la operación **no declara** `response_model` |

`BACKEND_ENVELOPE_CONTRACT = CONTRACTUAL`. Que OpenAPI no lo describa es una deuda del
backend (`AUDIT-OPENAPI-SIN-RESPONSE-MODEL`, §14), no una ambigüedad: ningún documento dice
«array».

## 6. Por qué `tsc` no lo vio

`api/client.ts:232`: `apiFetch<T>(path): Promise<T>` termina en `return payload as T`. El tipo
lo afirma quien llama; nadie lo comprueba. `TYPE_SAFETY_ROOT_CAUSE = genérico afirmado por el
llamador, sin función tipada por endpoint`. La corrección no toca `apiFetch` —lo usan decenas de
módulos—: declara **una** función tipada para este endpoint, `listAuditEvents(): Promise<AuditEventPage>`,
con `AuditEventPage = PagedResult<AuditEvent>`, el tipo canónico que ya existe. A partir de ahí,
tratar el sobre como array **no compila** (control negativo, §13), y una prueba de tipo
(`expectTypeOf`, evaluada por `tsc -b`) impide retipar la función.

Inventario de `as`/`any` en la pantalla: **0** antes y después.

## 7. `DataTable`, paginación y estados

`components/DataTable.tsx`: `data: TData[]`, paginación **de cliente** (TanStack Table, 10 por
página, control visible a partir de 11), `total = data.length`, `loading` → `LoadingState`
(`role="status"`), `error` → `role="alert"`, `data.length === 0` → `EmptyState`. No admite
`total`, `page` ni `page_size` del servidor. La pantalla no mantiene estado de página: pide la
página 1 de 20 del servidor y la tabla la pagina en cliente. Ese diseño es anterior a este delta
y **no se rediseña** (`AUDITORIA-PAGINACION-CLIENTE`, §14): `total`, `page` y `page_size` del
sobre quedan tipados y disponibles, no consumidos, porque hoy no hay a quién entregárselos.

Consumidores del endpoint: `AuditoriaPage` (único en `src/`) y `approvals.spec.ts:300` (ya usa
`.items`). `ReportesAuditoriaPage` consume otro endpoint. Mismo defecto en otras superficies:
**ninguna** (las siete que tipan sobre lo hacen bien).

## 8. `/speckit.specify`

Tras `FR-001-149`:

| ID | Requisito | Prioridad |
|---|---|---|
| FR-001-150 | `AuditoriaPage` consume el sobre `{items, total, page, page_size}` que publica el listado de auditoría | P0 |
| FR-001-151 | Las filas entregadas a `DataTable` son `response.items` | P0 |
| FR-001-152 | `total`, `page` y `page_size` quedan tipados según el contrato y disponibles para quien los consuma | P1 |
| FR-001-153 | El frontend tipa la respuesta como sobre, nunca como `AuditEvent[]`, sin `as` ni `any` | P0 |
| FR-001-154 | Tratar el sobre como array, o retipar la petición, deja de compilar o hace fallar la suite | P0 |
| FR-001-155 | El backend no cambia su forma de respuesta | P0 |
| FR-001-156 | El aislamiento de tenant certificado en `AUDIT-EVENTS-SIN-TENANT` se conserva | P0 |
| FR-001-157 | No se implementa la búsqueda `q` de auditoría | P0 |
| FR-001-158 | La columna «Fecha» no cambia (`AUDITORIA-CREATED-AT` sigue separada) | P0 |
| FR-001-159 | Carga, error y vacío siguen siendo carga, error y vacío | P0 |
| FR-001-160 | OpenAPI y el backend permanecen sin cambios | P0 |
| FR-001-161 | Sin esquema ni migración | P0 |
| FR-001-162 | Cobertura de página y E2E que demuestre que con `items > 0` la tabla pinta esas filas | P0 |

| ID | Criterio |
|---|---|
| AC-033 | **Dado** un sobre con dos eventos y `total` 108, **entonces** la tabla tiene exactamente dos filas, identificables por su `request_id` |
| AC-034 | **Dado** un sobre con `items = []`, **entonces** se muestra «Sin eventos» |
| AC-035 | **Dado** un error del servidor, **entonces** se muestra el error y no el estado vacío |
| AC-036 | **Dado** una respuesta que no es el sobre, **entonces** no se pinta ninguna fila |
| AC-037 | **Dado** dos inicios de sesión por API cuyo `X-Request-ID` devuelve el servidor, **entonces** aparecen como filas en un navegador real, y el de otro tenant no |

## 9. `/speckit.clarify`

| # | Pregunta | Respuesta |
|---|---|---|
| 1–3 | dueñas | 001 · 001 · 012 |
| 4 | `AuditoriaPage` | `src/pages/AuditoriaPage.tsx` |
| 5 | endpoint | `GET /api/v1/audit/events` (`list_events_api_v1_audit_events_get`) |
| 6 | OpenAPI | `schema: {}` — no declara la respuesta |
| 7 | modelo backend | `dict` literal `{page, page_size, total, items}` |
| 8–9 | petición / tipo frontend | `apiFetch<AuditEvent[]>` → `listAuditEvents(): Promise<PagedResult<AuditEvent>>` |
| 10 | raíz de la inseguridad de tipos | genérico afirmado por el llamador (`payload as T`) |
| 11–12 | `DataTable` | `data: TData[]`; paginación de cliente, sin `total` del servidor |
| 13–15 | uso de `total`/`page`/`page_size` | ninguno hoy; tipados y disponibles |
| 16–18 | carga / error / vacío | `role=status` / `role=alert` con el mensaje de la pantalla / «Sin eventos» |
| 19 | otros consumidores | `approvals.spec.ts:300` (correcto) |
| 20–23 | cambios backend / frontend / tipo compartido / `apiFetch` | **no** / sí (2 ficheros) / no (`PagedResult` ya existe) / **no** |
| 24–25 | esquema / migración | 0 / 0 |
| 26–27 | fecha / `q` | intactas |
| 28 | aislamiento | conservado y reejecutado |
| 29–32 | pruebas / mutaciones / E2E / regresión | §12–§13 |

**MATERIAL OQ = 0. UNKNOWN = 0.**

## 10. `/speckit.plan` y diseño

W01–W34 ejecutados en el orden del encargo; W28 (matriz de navegadores) con Firefox y WebKit
instalados para ello.

```
src/api/audit.ts       listAuditEvents(search): Promise<AuditEventPage>   ← PagedResult<AuditEvent>
AuditoriaPage.tsx      queryFn: () => listAuditEvents(search)
                       data={query.data?.items ?? []}                      ← [] solo mientras no hay respuesta
```

`q` sigue viajando exactamente como antes (`?q=<search>`), porque no es parte de este contrato.
Descartados: cambiar el backend a array; `Array.isArray`; `data?.items ?? data`; `as AuditEvent[]`;
refactorizar `apiFetch`.

## 11. CONSTITUTION GATE

| # | Puerta | Veredicto |
|---|---|---|
| G-AUDENV-01..02 | checkpoint · dueña | **PASA** |
| G-AUDENV-03..04 | reproducido en navegador · sobre por API | **PASA** — §4 |
| G-AUDENV-05..06 | OpenAPI · modelo de respuesta | **PASA** — `schema {}`, `dict`; contrato demostrado por otras fuentes (§5) |
| G-AUDENV-07..09 | tipo incorrecto · `DataTable` · raíz | **PASA** — §3, §6, §7 |
| G-AUDENV-10 | consumidores | **PASA** — 2 |
| G-AUDENV-11 | implementación mínima | **PASA** — §10 |
| G-AUDENV-12..14 | backend intacto · fecha aparte · `q` aparte | **PASA** |
| G-AUDENV-15..17 | regresión de aislamiento · esquema 0 · migración 0 | **PASA** |
| G-AUDENV-18..19 | mutaciones · regresión | **PASA** — §13 |
| G-AUDENV-20..22 | MATERIAL OQ 0 · UNKNOWN 0 · trazabilidad 100 % | **PASA** |

## 12. `/speckit.tasks`, `/speckit.analyze` previo e `/speckit.implement`

| ID | Tarea | Ficheros | Requisito | Mutación |
|---|---|---|---|---|
| T-01 | Checkpoint, artefactos, ruido de modo, entorno | — | — | — |
| T-02 | Evidencia original y dueñas | — | — | — |
| T-03 | Reproducción navegador y API | `evidence/…/reproduccion-*` | 150 | — |
| T-04 | Contrato del sobre demostrado | — | 155, 160 | — |
| T-05 | Función tipada de la petición | `src/api/audit.ts` | 153, 154 | M2, M6 |
| T-06 | La pantalla consume `items` | `src/pages/AuditoriaPage.tsx` | 150, 151, 152, 159 | M1, M3, M4, M7 |
| T-07 | Pruebas de página (7) | `src/pages/AuditoriaPage.test.tsx` | 162 | M1–M7 |
| T-08 | E2E (2, tres navegadores) | `e2e/auditoria-sobre.spec.ts` | 162 | — |
| T-09 | Regresión de aislamiento y sanidad backend | — | 156 | — |
| T-10 | Puertas, E2E global, convergencia | — | 154, 159 | — |

**Huérfanos: 0 / 0.** Análisis previo sobre `735254e`: `as AuditEvent[]`/`as any` en la
pantalla: 0; `Array.isArray` sobre esta respuesta: 0; cambios de backend: 0; `q`: sin cambio;
`created_at`: sin cambio; `sleep`/`skip` en las pruebas nuevas: 0. BLOCKER 0 · CRITICAL 0 ·
CONTRADICTIONS 0 · OWNER CONFLICT 0.

**Implementado**: `src/api/audit.ts` (nuevo, 20 líneas) y `AuditoriaPage.tsx` (+3/−2).
Columnas, `SearchInput`, `queryKey` y `retry` sin cambio.

## 13. Evidencia — `evidence/auditoria-sobre/`

| Fichero | Qué demuestra |
|---|---|
| `reproduccion-ui-pre-fix.txt` / `-post-fix.txt` | 20 items, 0 filas → 20 items, 10 filas (primera página de cliente), «Invalid Date» en la columna Fecha por la deuda separada |
| `reproduccion-api-pre-fix.txt` | forma exacta del sobre y OpenAPI sin `response_model` |
| `mutaciones.txt` | 6/6 mutantes muertos, control negativo de tipos |
| `frontend-gates.txt` | `tsc -b` 0 · ESLint 0 · Vitest **395/395** (388 + 7) · `vite build` 0 |
| `backend-dirigido.txt` | aislamiento (11) + búsqueda de empresas (17) verdes en SQLite y PostgreSQL |
| `e2e-chromium.txt` / `e2e-matriz.txt` | 2/2 en Chromium; matriz Firefox y WebKit |
| `e2e-global.txt` | E2E completa en Chromium |

### Mutaciones

| Mutación | Qué reintroduce | Resultado |
|---|---|---|
| ENV-M1 | `data={query.data ?? []}` (el sobre como lista) | **muere** — `tsc` (TS2322) y 5 pruebas |
| ENV-M2 | `AuditEventPage = AuditEvent[]` (con y sin la importación de `PagedResult`) | **muere** — `tsc`: `.items` no existe en la página, `expectTypeOf` no satisface |
| ENV-M3 | `data?.items ?? data ?? []` (soporte dual) | **muere** — `tsc` (TS2322) y ENV-08 |
| ENV-M4 | `data={[]}` (se ignoran los items) | **muere** — ENV-01, 03, 05 |
| ENV-M5 | `total` incorrecto | **no aplica**: la tabla no consume `total` del servidor (§7) |
| ENV-M6 | `listAuditEvents(): Promise<any>` | **muere** — `tsc` por `expectTypeOf` (TS2344) |
| ENV-M7 | el error se convierte en lista vacía | **muere** — ENV-04 |
| ENV-M8 | retirar el aislamiento de tenant | **no aplica**: 0 ficheros de backend tocados |

Control negativo de tipos: con `data={query.data ?? []}`, `npm run typecheck` **falla** con un
error; restaurado y verificado byte a byte.

### Regresión y comprobaciones

| Suite | Resultado |
|---|---|
| `AuditoriaPage.test.tsx` | **7/7** |
| Vitest completo | **395/395** |
| `tsc -b`, ESLint, `vite build` | 0 · 0 · 0 |
| Aislamiento de auditoría (`AUDIT-EVENTS-SIN-TENANT`) + búsqueda de empresas | **28/28** en SQLite y PostgreSQL |
| Backend completo | **no ejecutado a propósito**: 0 ficheros de producto backend; una corrida completa sobre PostgreSQL deja 2,2 GB y 80 conexiones (`TEST-SCHEMAS-PG-SIN-LIMPIEZA`), sin nada que certificar a cambio |
| E2E dirigido | Chromium 2/2 · matriz **6/6** (Chromium, Firefox, WebKit ×2). El primer intento de WebKit falló porque, con seis pruebas en paralelo, otros inicios de sesión empujaban el evento controlado fuera de la primera página de cliente: la aserción pasó a comprobar la correspondencia `items → filas` completa (recuento, orden, acción, entidad y Request ID de cada fila), que es lo que el defecto rompía |
| E2E global (Chromium) | **191 pasadas · 0 fallos · 40 saltadas · exit 0** (segunda corrida). La primera dio 182/3/40: los dos fallos de `auditoria-sobre` buscaban el rastro en la página 1 de 20 que pide la pantalla, y bajo carga paralela el evento ya no estaba en ella —la aserción pasó a la verdad del servidor con página amplia—; el tercero, `notifications:142`, porque el ayudante del planificador se lanza con el entorno del proceso y a este le faltaban las variables del backend (`ValidationError` de `Settings`): se exportan y pasa. Las 40 saltadas son las que la propia suite salta en Chromium (S3, navegador específico) y no se investigan aquí |

Nota de Vitest (3.2.7): `apiFetch.mockClear()` o `mockReset()` **dentro de un `beforeEach`** hace
que la prueba del estado de error falle con el propio rechazo, mientras que la misma limpieza
**dentro del cuerpo de la prueba** no. Ninguna otra prueba del repositorio ejercita un rechazo;
se registra como observación (`VITEST-MOCKCLEAR-EN-HOOK`, §14) y las pruebas limpian en el cuerpo.

## 14. Deudas y hallazgos, registrados y no absorbidos

| ID | Estado |
|---|---|
| `AUDITORIA-CREATED-AT` (`AUDIT-UI-FECHA-CAMPO-INCORRECTO`) | abierta: la columna «Fecha» pinta «Invalid Date» porque lee `created_at` y el servidor publica `event_time` |
| `UI-BUSQUEDA-MUERTA` · Auditoría | `MATERIAL_DECISION_REQUIRED` sobre los campos; `q` sigue viajando y sigue sin efecto |
| `AUDITORIA-PANTALLA-DUPLICADA` | abierta |
| `AUDITORIA-PAGINACION-CLIENTE` (nuevo, menor) | la pantalla pide la página 1 de 20 del servidor y la tabla la pagina en cliente de 10 en 10: `total` (108 hoy) no se muestra ni hay forma de pedir la página 2. `DataTable` no admite paginación de servidor |
| `AUDIT-OPENAPI-SIN-RESPONSE-MODEL` (nuevo, menor) | `list_events` no declara `response_model`: OpenAPI publica `schema {}` para una respuesta que es contractualmente un sobre |
| `VITEST-MOCKCLEAR-EN-HOOK` (nuevo, observación) | ver §13 |
| `TEST-MIGRACIONES-VENV-FIJO`, `LOCK-SIN-REPORTLAB-MAGIC`, `TEST-SCHEMAS-PG-SIN-LIMPIEZA` | abiertas; el `.venv` se reparó localmente, no en el repositorio |

## 15. Estado resultante

| Cosa | Estado |
|---|---|
| `AUDITORIA-SOBRE-VS-ARRAY` | **CLOSED / CONVERGED** |
| Ficheros de producto | 2 (frontend) · backend 0 |
| Pruebas nuevas | 7 de página · 2 E2E × 3 navegadores · mutaciones 6/6 (+2 no aplicables) |
| Forma pública de la API | sin cambio |
| Decisiones nuevas de la dueña | ninguna |
