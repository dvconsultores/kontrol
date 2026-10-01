# SPEC 001 · DELTA DIRIGIDO EMPRESAS-SIN-SOBRE — EL LISTADO DE EMPRESAS RESPONDE EL SOBRE DEL CONTRATO

> Delta de contrato dentro de la Spec 001 (Fundación, que implementa el Master 007
> «Organización» y es dueña de `api-contracts.md`); Spec 012 (QA integral, Master 054)
> como apoyo. Cierra `EMPRESAS-SIN-SOBRE`: `GET /api/v1/organization/companies` pasa del
> array plano al sobre paginado `{items, total, page, page_size}` que el contrato de
> listados exige, y todos sus consumidores migran a la vez. No toca la semántica de `q`,
> ni `Company.code`, ni el alcance de tenant o de usuario.

## 0. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` | `8b845a1` / **`8b845a1`** — coinciden |
| `ACTUAL_BRANCH` | `develop`, al día con `origin/develop` |
| `COMMITS_AFTER_8B845A1` | **0** |
| `WORKTREE_STATE` | **limpio**: los cambios de modo se restauraron a 644 y los dos artefactos de auditoría se sacaron del repositorio a `~/kontrol-artefactos-no-versionados/` por decisión de la dueña (2026-09-30) |
| Entorno | PostgreSQL de QA reaprovisionado esta sesión (`kaud` sembrada, `ktest`); `.venv` del repositorio reparado localmente; sin `clamscan`. Nada se absorbe |

## 1. Veredicto, por delante

**El contrato ya estaba escrito; el endpoint era el único listado que no lo cumplía.**
`api-contracts.md:11`: «Listados con `q`, `status`, `sort`, `page`, `page_size`». Dieciséis
listados del producto responden `{items, total, page, page_size}`; Empresas respondía un
array, ignoraba `page` y `page_size` en silencio y no decía `total`. Fix: el mismo sobre,
con `total` contado sobre el mismo conjunto que `items` —tenant, alcance del usuario y
`q`— y orden determinista; el frontend tipa el sobre una vez, la pantalla pagina en el
servidor y el selector de contexto recorre las páginas declaradas. Ficheros de producto:
**5** (1 backend, 4 frontend). Esquema, migraciones, índices: **0**.

## 2. Dueñas

| Papel | Spec | Evidencia |
|---|---|---|
| **Principal** | **SPEC 001 — Fundación** | `spec-equivalence-map.md`: «007 Organización → `001-fundacion`»; `organization/api.py`, `EmpresasPage.tsx`, `CompanyContext.tsx`, `api-contracts.md` |
| Contrato | **SPEC 001** — `contracts/api-contracts.md` (contrato de listados) y `FR-001-065` (paginación >10) | §5 |
| QA | **SPEC 012** (Master 054) | pruebas de contrato, E2E, guarda de completitud |

`OWNER_IDENTITY_CONFLICT = 0`.

## 3. Lo que había, medido

`COMPANY_LIST_ENDPOINT = GET /api/v1/organization/companies` (`list_companies_api_v1_organization_companies_get`).
Evidencia: `evidence/empresas-sobre/reproduccion-api-pre-fix.txt`.

| Medida (`uab`, DEMO, D1 y D2) | Valor |
|---|---|
| `ARRAY_OR_OBJECT` | **ARRAY** |
| `CURRENT_COUNT` | 2 |
| `?page=2` | 200, **las mismas 2** (el parámetro no existe y se ignora) |
| `?page_size=1` | 200, **las mismas 2** |
| `total` | no existe |
| OpenAPI | parámetros `[q]`; `responses.200.schema = {}` |

`CURRENT_FRONTEND_CONSUMER`: `EmpresasPage.tsx:25` (`apiFetch<CompanySummary[]>`, tabla con
paginación de cliente sobre el array entero) y `CompanyContext.tsx:202` (el selector de
contexto, `apiFetch<CompanySummary[]>`, con `Array.isArray(lista) ? lista : []`).

## 4. Inventario de consumidores

| Consumidor | Propósito | Esperaba array | Necesita todas | Migración |
|---|---|---|---:|---|
| `src/pages/EmpresasPage.tsx` | listado administrativo | sí | no | sobre + paginación de servidor |
| `src/app/contexts/CompanyContext.tsx` | **selector de contexto** (autoridad de qué empresa puede activarse) | sí | **sí** | recorre las páginas declaradas (§8) |
| `src/api/client.ts:75` | `RUTAS_SIN_EMPRESA` (no lleva cabecera) | — | — | sin cambio |
| 21 suites E2E + `helpers/ventas.ts` | primera empresa del admin por API | tolerancia dual `Array.isArray(b) ? b : b.items` | no | `.items`, sin la rama muerta |
| `e2e/n6-multicompany.spec.ts:73` | captura la respuesta de la propia aplicación | `Empresa[]` | no | `{ items }` |
| 12 ficheros de `tests/` backend | `.json()[0]["id"]`, recuentos, conjuntos | sí | no | `.json()["items"]` |
| `qa/functional-e2e-{local,inprocess}.py`, `qa/repro-empresas-busqueda-q.py` | guiones de QA | sí | no | `["items"]` |
| `qa/runs/…`, `qa/audits/…` | artefactos históricos | — | — | no se reescriben |

**Ningún consumidor recibe una lista truncada sin saberlo**: el único que necesita todas
las empresas es el selector, y ahora las reúne por contrato (§8). El listado
administrativo pagina a la vista, con su `total`.

## 5. El contrato, transcrito

| Fuente | Qué dice |
|---|---|
| `CONTRACT_SOURCE_1` — `specs/001-fundacion/contracts/api-contracts.md:11` | «Listados con `q`, `status`, `sort`, `page`, `page_size`» |
| `CONTRACT_SOURCE_2` — `api-contracts.md:50` | `GET /api/v1/organization/companies` «Listar/crear empresa» |
| `CONTRACT_SOURCE_3` — `FR-001-065`, `frontend-foundation.md §8` | «paginación >10» en los DataTables |
| Canon implementado (16 listados; medido en `maestros/terceros`) | `{items, total, page, page_size}` · `page` desde **1** (`ge=1`) · `page_size` **20** por defecto, **100** máximo (`le=100`) · fuera de rango **422 `VALIDATION_ERROR`** · página más allá del final **200 con `items` vacío y `total` intacto** |
| Tipo canónico frontend | `PagedResult<T>` (`api/types.ts:93`), usado por terceros, productos y servicios |
| Modelo canónico backend | **no existe**: los dieciséis listados devuelven `dict`; ninguno declara `response_model` (`LISTADOS-SIN-RESPONSE-MODEL`, §14) |

```
COMPANY_LIST_CONTRACT = {
  items:     Company[]   (id, code, legal_name, trade_name, rif, status, functional_currency, allowed_actions)
  total:     int         (conjunto tras tenant, alcance del usuario y q; antes de cortar la página)
  page:      int         (la pedida, ≥ 1; por defecto 1)
  page_size: int         (el pedido, 1..100; por defecto 20)
}
PAGINATION_STYLE = page/page_size · PAGE_BASE = 1 · DEFAULT_PAGE_SIZE = 20 · MAX_PAGE_SIZE = 100
TOTAL_SEMANTICS = visibles para el usuario, filtradas, antes de paginar
ORDERING = created_at, id   (desempate canónico: setup/api.py:41, purchasing/api.py:448)
```

`status` y `sort`, que el contrato de listados nombra en general, no existían en Empresas ni
se añaden aquí: son funcionalidad nueva, no alineación (`EMPRESAS-STATUS-SORT`, §14).

## 6. `/speckit.specify`

Tras `FR-001-175`:

| ID | Requisito | Prioridad |
|---|---|---|
| FR-001-176 | El listado de empresas responde el sobre del contrato de listados, `{items, total, page, page_size}` | P0 |
| FR-001-177 | Los nombres, tipos y semántica son los del canon: `page` desde 1, `page_size` 20 por defecto y 100 máximo, 422 fuera de rango, página vacía más allá del final | P0 |
| FR-001-178 | La paginación se ejecuta en el backend, después de tenant, alcance del usuario y `q` | P0 |
| FR-001-179 | `total` cuenta el conjunto visible para el usuario tras tenant, alcance y `q`, y comparte predicado con `items` | P0 |
| FR-001-180 | `q` conserva la semántica convergida (`code`, `legal_name`, `trade_name`, `rif`; contiene; sin distinguir mayúsculas; sin trim ni escape) | P0 |
| FR-001-181 | El listado conserva el aislamiento por tenant y el alcance de empresas del usuario | P0 |
| FR-001-182 | El orden es determinista: fecha de alta y, a igual fecha, identificador | P0 |
| FR-001-183 | Todos los consumidores del endpoint migran al sobre en el mismo cambio; no queda tolerancia dual array/sobre | P0 |
| FR-001-184 | El frontend tipa la respuesta como `PagedResult<CompanySummary>` desde una función por endpoint; tratar el sobre como array no compila | P0 |
| FR-001-185 | OpenAPI declara `q`, `page` y `page_size` con sus límites | P0 |
| FR-001-186 | `Company.code`, el tenant, los alcances y `q` no cambian de semántica | P0 |
| FR-001-187 | Sin esquema, migración ni índice | P0 |
| FR-001-188 | Los consumidores que necesitan todas las empresas (el selector de contexto) las reúnen recorriendo las páginas que el contrato declara, con el tamaño máximo que admite | P0 |
| FR-001-189 | Existen pruebas de contrato que detectan el array legacy, y de `q` + paginación, alcance + `total`, tenant + `total`, paginación por defecto y de borde | P0 |
| FR-001-190 | `EmpresasPage` pagina en el servidor con un solo paginador, conserva carga, error, vacío y búsqueda, y vuelve a la primera página al cambiar `q` | P0 |

| ID | Criterio |
|---|---|
| AC-043 | **Dado** 30 empresas visibles, **cuando** se pide sin parámetros, **entonces** `page` 1, `page_size` 20, `total` 30 y 20 items; la página 2 trae los 10 restantes sin repetir ni omitir |
| AC-044 | **Dado** un usuario limitado a D1, **entonces** `total` es 1 aunque el tenant tenga 30 |
| AC-045 | **Dado** `ALFA-OBJETIVO` en dos tenants, **entonces** cada uno cuenta 1 |
| AC-046 | **Dado** `q` con 25 coincidencias y `page_size` 10, **entonces** tres páginas de 10, 10 y 5, `total` 25 |
| AC-047 | **Dado** `page=0`, `page_size=101` o `page=x`, **entonces** 422 |
| AC-048 | **Dado** 230 empresas, **entonces** el selector de contexto las reúne en tres peticiones de 100 |
| AC-049 | **Dado** 23 empresas, **entonces** la pantalla muestra 10 filas y un único paginador «Página 1 de 3»; a 25 por página, 23 filas y un único paginador |

## 7. `/speckit.clarify`

| # | Pregunta | Respuesta |
|---|---|---|
| 1–3 | dueñas | 001 · 001 · 012 |
| 4–6 | endpoint · forma actual · forma contractual | `GET /api/v1/organization/companies` · array · sobre (§5) |
| 7–8 | sobre canónico backend · frontend | ninguno (dicts) · `PagedResult<T>` |
| 9–14 | paginación · estilo · defecto · máximo · base · total | sí · `page/page_size` · 20 · 100 · 1 · visibles filtradas antes de paginar |
| 15–16 | orden · filtros actuales | `created_at, id` · ninguno |
| 17–19 | `q` · tenant · alcance | intactos: `ilike` en cuatro campos; `tenant_id = user.tenant_id`; `id IN accessible_company_ids` |
| 20–22 | consumidores · los que necesitan todas · mecanismo | §4 · el selector · recorrer páginas de 100 |
| 23–26 | `EmpresasPage` hoy · objetivo · `queryKey` · reinicio | paginación de cliente sobre el array · servidor, 10 por página, `Pagination` propio · `[…, q, pagina, tamano]` · a la primera al cambiar `q` o el tamaño (patrón de Alertas) |
| 27–29 | carga · error · vacío | intactos (`LoadingState`, `role=alert`, «Sin empresas») |
| 30–32 | OpenAPI hoy · objetivo · `response_model` | `[q]`, `schema {}` · `[q, page, page_size]` con límites · `dict`, como los otros dieciséis |
| 33–36 | esquema · migración · índice · rendimiento | 0 · 0 · 0 · un `COUNT` más sobre decenas de filas por tenant |
| 37 | compatibilidad | cambio de forma pública para 36 consumidores conocidos, migrados todos en este commit |
| 38–41 | pruebas · mutaciones · E2E · regresión | §11–§12 |

**MATERIAL OQ = 0. UNKNOWN = 0.** Los tres documentos coinciden; no hay forma que elegir.

## 8. `/speckit.plan` y diseño

W01–W45 ejecutados en el orden del encargo.

```
backend  organization/api.py::list_companies(q, page, page_size)
         select(Company).where(tenant_id = user.tenant_id, id IN alcanzables) [.where(q en 4 campos)]
         total = COUNT(subquery)                              ← mismo predicado
         items = order_by(created_at, id).offset((page-1)*page_size).limit(page_size)
         → {items, total, page, page_size}

frontend api/organization.ts   listCompanies({q, page, page_size}): Promise<PagedResult<CompanySummary>>
                               listAllCompanies(): recorre page=1.. con page_size=100 hasta reunir total
         CompanyContext        autorizadas = await listAllCompanies()
         EmpresasPage          página y tamaño en estado; queryFn listCompanies; DataTable manualPagination;
                               Pagination propio con el total del sobre (solo si total > 10, FR-001-065)
         DataTable             prop aditiva `manualPagination`: no re-pagina ni pinta su contador
```

Descartado: dejar el array; `page_size=10000`; `all=true`; `Array.isArray` en producto;
`Company[] | PagedResult<Company>`; doble paginación; rediseñar `DataTable`; `response_model`
solo aquí (sería el único de diecisiete: se registra como deuda transversal).

## 9. CONSTITUTION GATE

| # | Puerta | Veredicto |
|---|---|---|
| G-COMPLIST-01..03 | checkpoint · dueñas · forma actual | **PASA** |
| G-COMPLIST-04..08 | contrato · sobre · paginación · total · orden | **PASA** — §5 |
| G-COMPLIST-09..11 | `q` · tenant · alcance | **PASA** — intactos y probados |
| G-COMPLIST-12..15 | consumidores · los de lista completa · migración · sin truncamiento | **PASA** — §4, §8 |
| G-COMPLIST-16..17 | sobre canónico backend · frontend | **PASA** — dict canónico · `PagedResult` |
| G-COMPLIST-18..21 | `EmpresasPage` · `queryKey` · reinicio · OpenAPI | **PASA** — §8 |
| G-COMPLIST-22..24 | compatibilidad · esquema 0 · migración 0 | **PASA** |
| G-COMPLIST-25..26 | mutaciones · regresión | **PASA** — §12 |
| G-COMPLIST-27..29 | MATERIAL OQ 0 · UNKNOWN 0 · trazabilidad 100 % | **PASA** |

## 10. `/speckit.tasks`, `/speckit.analyze` previo e `/speckit.implement`

| ID | Tarea | Ficheros | Requisito | Mutación |
|---|---|---|---|---|
| T-01 | Checkpoint, evidencia previa, dueñas | — | — | — |
| T-02 | Reproducción de la forma actual (API, pantalla) | `evidence/…/reproduccion-*` | 176 | — |
| T-03 | Contrato transcrito y canon medido en terceros | — | 177 | — |
| T-04 | Inventario y clasificación de consumidores | — | 183, 188 | — |
| T-05 | Backend: sobre, `total`, paginación, orden, OpenAPI | `organization/api.py` | 176–182, 185 | B1–B8 |
| T-06 | Frontend: módulo tipado y selector que recorre páginas | `src/api/organization.ts`, `CompanyContext.tsx` | 184, 188 | F2, F4 |
| T-07 | Frontend: `EmpresasPage` paginada en el servidor y `DataTable.manualPagination` | `EmpresasPage.tsx`, `DataTable.tsx` | 190 | F1, F3, F5, F6, F7 |
| T-08 | Migración de consumidores: 22 E2E, 12 tests backend, 3 guiones QA | ver §4 | 183 | — |
| T-09 | Pruebas backend de contrato (12) y ajuste de la suite de búsqueda | `tests/test_company_list_envelope.py`, `tests/test_company_search.py` | 189 | B1–B8 |
| T-10 | Pruebas frontend (página 9, módulo 5, tabla 1, proveedor 10) y guarda de completitud | `EmpresasPage.test.tsx`, `organization.test.ts`, `DataTable.test.tsx`, `companyProvider.test.tsx`, `tests/audit-completeness.test.ts` | 184, 189, 190 | F1–F7 |
| T-11 | E2E nuevo y regresión E2E global | `e2e/empresas-sobre.spec.ts` | 183, 190 | — |
| T-12 | Documentación, roadmap, convergencia | — | — | — |

**Huérfanos: 0 / 0.** Análisis previo sobre `8b845a1`: `Array.isArray` sobre esta respuesta
en producto: 1 (`CompanyContext`, retirado); en E2E: 22 (retirados); `page_size=10000`/`all=true`:
0; filtrado de `q` en Python tras paginar: 0; `COUNT` global: 0; esquema/migración: 0;
`sleep`/`skip` en las pruebas nuevas: 0. BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0.

## 11. Evidencia — `evidence/empresas-sobre/`

| Fichero | Qué demuestra |
|---|---|
| `reproduccion-api-pre-fix.txt` / `-post-fix.txt` | array sin `total` → sobre con `total` acotado (`uab` 2, `ua` 1, `uc` 1), páginas de 1, página 9 vacía, 422 en `page=0` y `page_size=101`, OpenAPI con límites |
| `reproduccion-ui-post-fix.txt` | la compuerta ofrece las 2 empresas (selector), la tabla pinta los items, un solo paginador (ninguno con 2 empresas), `q` sigue viva |
| `mutaciones-backend.txt` | 8/8 mutantes muertos |
| `mutaciones-frontend.txt` | 7/7 mutantes muertos (F6 exigió una prueba nueva a 25 por página) y control negativo de tipos |
| `backend-dirigido.txt` | sobre + búsqueda + 11 ficheros migrados: 116/116 en SQLite; PostgreSQL 70/70 + N10 5/5 en solitario |
| `frontend-gates.txt` | `tsc -b` 0 · ESLint 0 · Vitest · `vite build` 0 |
| `e2e-matriz.txt` / `e2e-global.txt` | suites de Empresas en tres navegadores; E2E completa en Chromium |

### Mutaciones

| Mutación | Qué reintroduce | Resultado |
|---|---|---|
| SOBRE-B1 | el array plano | **muere** — 25 pruebas |
| SOBRE-B2 | `total` del tenant entero, sin alcance ni `q` | **muere** — 17 |
| SOBRE-B3 | `total` sin `q` | **muere** — 17 |
| SOBRE-B4 | la página se corta antes de `q` | **muere** — 17 |
| SOBRE-B5 | `items` sin el alcance del usuario | **muere** — L10, Q11 |
| SOBRE-B6 | sin desempate por `id` | **muere** — L05, Q01 |
| SOBRE-B7 | `page_size` sin tope | **muere** — L08, L12 |
| SOBRE-B8 | la página se ignora | **muere** — L05, L06, L07, L09 |
| SOBRE-F1 | la respuesta entera como filas | **muere** — `tsc` (TS2322) y 7 pruebas |
| SOBRE-F2 | la petición tipada como `Company[]` | **muere** — `tsc` |
| SOBRE-F3 | soporte dual `items ?? sobre` | **muere** — `tsc` y LIST-F-04 |
| SOBRE-F4 | el selector se queda con la primera página | **muere** — `organization.test` |
| SOBRE-F5 | cambiar `q` no vuelve a la primera página | **muere** — LIST-F-03 |
| SOBRE-F6 | la tabla vuelve a paginar en cliente (doble paginación) | sobrevivía a 10 por página (equivalente); **muere** con LIST-F-06 a 25 por página |
| SOBRE-F7 | la página no envía `page`/`page_size` | **muere** — 4 pruebas |

Control negativo de tipos: `data={query.data ?? []}` → `tsc` **falla** (TS2322); restaurado.

### Regresión y comprobaciones

| Suite | Resultado |
|---|---|
| `test_company_list_envelope.py` (12) + `test_company_search.py` (17) | **32/32** en SQLite y PostgreSQL |
| Los 11 ficheros backend migrados + aislamiento de auditoría | **116/116** (SQLite) |
| Aislamiento multiempresa, contrato N8, N10 (PostgreSQL) | **70/70**; N10 **5/5** en solitario (en el lote comparte motor con otro módulo, como en ciclos anteriores) |
| Backend completo | no ejecutado a propósito: un fichero de producto backend, cubierto por las suites dirigidas; una corrida completa deja 2,2 GB y 80 conexiones (`TEST-SCHEMAS-PG-SIN-LIMPIEZA`) |
| Frontend | `tsc -b` 0 · ESLint 0 · Vitest **412/412** (400 + 12: página 9 → 6 nuevas, módulo 5, tabla 1) · `vite build` 0 |
| E2E dirigido, tres navegadores | **39/39**: `empresas-sobre` (4), `empresas-busqueda` (5) y `empresa-helper` (4) en Chromium, Firefox y WebKit, repetidas tras aplanar la plantilla de la petición |
| E2E global (Chromium) | **tres corridas: 195/1/40, 195/1/40 y 194/2/40** (pasadas/fallos/saltadas). Los cuatro fallos son distintos entre sí —`treasury.spec.ts:486`, `route-crawl` (`/comercial/listas-precio` sin H1), `inventory-confirmation` (`ECONNRESET` contra un backend recién reiniciado) y `putaway.spec.ts:405`— y **los cuatro pasan en solitario** (3/3, 1/1, 3/3, 9/9). Ninguno consume el listado de empresas más allá del ayudante de sesión, que funcionó en los 236 restantes. Es la concurrencia de la propia suite sobre una base de QA que acumula cuatro corridas en una tarde (`E2E-FLAKY-BAJO-CARGA`, §13) |

## 12. Guarda de completitud

`src/tests/audit-completeness.test.ts` (G3/G4) extrae las rutas que cada página pide con
`apiFetch("…")` y comprueba que existen. Una página que delega la petición en un módulo
tipado por endpoint (`@/api/organization`, como `@/api/audit`) no tiene literal que extraer y
la guarda la daba por «placeholder». La guarda pasa a seguir esas importaciones y a validar
las rutas del módulo: el patrón de función tipada por endpoint queda cubierto, no exento.

## 13. Deudas y hallazgos, registrados y no absorbidos

| ID | Estado |
|---|---|
| `EMPRESAS-SIN-SOBRE` | **CLOSED / CONVERGED** |
| `LISTADOS-SIN-RESPONSE-MODEL` (nuevo, transversal) | ninguno de los diecisiete listados declara `response_model`: OpenAPI publica `schema {}`; generaliza `AUDIT-OPENAPI-SIN-RESPONSE-MODEL` |
| `EMPRESAS-STATUS-SORT` (nuevo, menor) | el contrato de listados nombra `status` y `sort`; Empresas no los implementa (tampoco antes) |
| `DATATABLE-CAPTION-EN-MODO-MANUAL` (nuevo, cosmético) | con `manualPagination`, el `caption` y el `aria-label` de resultados cuentan las filas de la página, no el `total` del servidor |
| `E2E-FLAKY-BAJO-CARGA` (nuevo, observación QA) | cuatro pruebas E2E distintas fallaron una vez cada una en tres corridas globales y las cuatro pasan en solitario: concurrencia entre suites sobre una base compartida (`treasury:486`, `route-crawl`, `inventory-confirmation`, `putaway:405`) |
| `AUDITORIA-PAGINACION-CLIENTE` | abierta; ahora tiene el mecanismo (`manualPagination` + `Pagination` con `total`) listo para usar |
| `EMPRESAS-PLACEHOLDER-GENERICO`, `BUSQUEDA-Q-SIN-ESCAPE` | sin cambio |

## 14. Estado resultante

| Cosa | Estado |
|---|---|
| `EMPRESAS-SIN-SOBRE` | **CLOSED / CONVERGED** |
| Ficheros de producto | 5 (1 backend, 4 frontend) |
| Consumidores migrados | 22 E2E · 12 tests backend · 3 guiones QA · 2 pantallas |
| Pruebas nuevas | 12 backend · 15 frontend · 4 E2E · mutaciones 15/15 |
| Esquema · migraciones · índices | 0 · 0 · 0 |
| Forma pública de la API | **cambia al contrato**: array → sobre |
| Decisiones nuevas de la dueña | ninguna |
