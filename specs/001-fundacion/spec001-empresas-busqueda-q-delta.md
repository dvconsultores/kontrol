# SPEC 001 · DELTA DIRIGIDO EMPRESAS-BUSQUEDA-Q — LA CAJA DE EMPRESAS BUSCA DE VERDAD

> Delta funcional dentro de la Spec 001 (Fundación, que implementa el Master 007
> «Organización»), con el contrato transversal de búsqueda `FR-001-065` y la Spec 012
> (QA integral, Master 054) como apoyo. Cierra el único subtarget **ya decidido** de
> `UI-BUSQUEDA-MUERTA`: la búsqueda general de Empresas. No toca Auditoría ni
> Existencias, que siguen `MATERIAL_DECISION_REQUIRED`.

## 0. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` | `e6968fe` / **`e6968fe`** — coinciden |
| `ACTUAL_BRANCH` | `develop` |
| `COMMITS_AFTER_E6968FE` | **0** |
| `WORKTREE_STATE` | los dos artefactos de auditoría sin seguimiento, preservados; 1.550 cambios **solo de modo** (`100644→100755`, 0 inserciones, 0 borrados), clasificados `WORKTREE_ENVIRONMENT_NOISE` y excluidos del commit con `core.fileMode=false` |
| Entorno | el mismo del ciclo anterior: `.venv` y `node_modules/.bin` aplanados; intérprete reconstruido con `uv` (3.11.16 + `requirements.lock`); herramientas de Node invocadas por ruta (`node node_modules/<pkg>/…`); PostgreSQL de QA en 55432 con `kaud` (sembrada) y `ktest`; sin `clamscan`. Nada de esto se absorbe |

## 1. Veredicto, por delante

**Una caja que enviaba `q` a un servidor que no lo declaraba.** El backend ya acotaba por
tenant y por alcance del usuario; solo faltaba que leyera el término. Fix: **un parámetro
y un predicado**, con la semántica del precedente vivo de terceros. Ficheros de producto:
**1** (backend). Frontend: **0** (ya hacía todo lo que debía). Esquema, migraciones,
índices: **0**.

## 2. Dueñas

| Papel | Spec | Evidencia |
|---|---|---|
| **Principal** | **SPEC 001 — Fundación** | `spec-equivalence-map.md`: «007 Organización → `001-fundacion`»; el endpoint vive en `app/modules/organization/api.py`, la página en `src/pages/EmpresasPage.tsx`, el contrato en `specs/001-fundacion/contracts/api-contracts.md:50`; el roadmap la nombraba dueña (001/007) |
| Contrato | **SPEC 001** (`FR-001-065`) con `FR-002-042` (Spec 002) como precedente de campos | §5 |
| QA | **SPEC 012** (Master 054) | pruebas hostiles, E2E |

En el árbol `specs/` no existe carpeta `007-…` para Organización: `007-nucleo-fiscal` es el
núcleo fiscal. `OWNER_IDENTITY_CONFLICT = 0`.

## 3. La decisión recuperada de `aae7cd2`

`spec001-dead-search-analysis.md §6` («Empresas — decidida»):

| | |
|---|---|
| `EMPRESAS_SEARCH_DECISION_SOURCE` | `spec001-dead-search-analysis.md §6` y `§5` (la regla destilada de los dos buscadores vivos), ratificada en `next-spec-decision.md` del 2026-09-24 y del 2026-09-30 |
| `EMPRESAS_Q_FIELDS` | **`code`, `legal_name`, `trade_name`, `rif`** — la terna de `FR-002-042` («RIF/nombre/código») más el segundo nombre que la entidad tiene; `status` fuera por ser estado |
| Contradicción posterior | **ninguna** |

No se reabre. Aquella nota decía además que «la pantalla necesita el sobre paginado»: eso
es `EMPRESAS-SIN-SOBRE`, deuda **separada** y **no autorizada** por este encargo, que fija
«no cambiar la forma pública salvo declarar `q`». El array plano se conserva (§7).

## 4. Reproducción, antes de tocar nada

Pila real: backend en `127.0.0.1:8000` sobre `kaud` (PostgreSQL), Vite en `5173`, Chromium.
Evidencia: `evidence/empresas-busqueda-q/reproduccion-{api,ui}-pre-fix.txt`.

| Medida | `uab`/DEMO (D1 y D2) | `uc`/DEMO2 (E1) |
|---|---|---|
| `GET /organization/companies` | 200 · 2 filas | 200 · 1 fila |
| `?q=ZZZ-NO-EXISTE-EMPRESA-Q` | 200 · **2 filas** | 200 · **1 fila** |
| `?q=SEGUNDA` / `?q=J-4047` / `?q=D1` | 200 · 2 filas | 200 · 1 fila |
| `?__kontrol_unknown_query_probe__=1` | 200 · 2 filas | 200 · 1 fila |
| Navegador, `/organizacion/empresas` por el menú, escribiendo en la caja | la petición sale con `q` (`/api/v1/organization/companies?q=ZZZ-…`) y la tabla sigue con **2 filas**; placeholder «Buscar en esta pantalla…» | — |

`B == A` para todo término: `q` era un parámetro silencioso.

## 5. Contrato y precedente

- **FR-001-065** (P0): «DataTables sin scroll horizontal, **búsqueda general**, filtro de
  estado, paginación >10, acciones a la derecha». `SEARCH_UI_EXISTS = YES`,
  `Q_CONTRACTUAL = YES`.
- **`api-contracts.md:50`**: `GET /api/v1/organization/companies` «Listar/crear empresa».
- **Precedente** (`evidence/…/precedente-terceros.txt`): `list_parties` declara `q: str = ""`,
  y con `if q:` aplica `like = f"%{q}%"` e `ilike` sobre cada campo en **OR**; los otros
  cinco `q` del producto (catálogo, unidades, kardex, seriales) hacen exactamente lo mismo.

| Semántica | Precedente | Empresas |
|---|---|---|
| `SEARCH_MATCH_TYPE` | contiene (`%q%`) | igual |
| Mayúsculas | no distingue (`ilike`) | igual |
| `trim` | **no** (`"   "` busca tres espacios) | igual: no se inventa |
| Comodines `%`/`_` | sin escape: actúan como comodines | igual: no se abre una política nueva |
| `q` vacía o ausente | sin filtro (`if q:`) | igual |
| Nulos | `ilike` sobre `NULL` es `NULL`, el OR lo ignora | `trade_name` es el único anulable: probado |
| Declaración | `q: str = ""` → OpenAPI `query`, `string`, no requerido | igual |

## 6. Frontend, medido y sin cambios

`src/pages/EmpresasPage.tsx`: `SearchInput` controlado (`search`), `queryKey:
["organization", "companies", search]`, `queryFn` → `/organization/companies?q=<encodeURIComponent(search)>`,
sin `debounce`, sin estado de página propio (la paginación es de cliente en `DataTable`,
que reinicia la página al cambiar los datos por el comportamiento por defecto de TanStack
Table), sin `AbortSignal`. `CompanyContext` consume la misma ruta sin `q` para el selector.

| Elemento | Estado |
|---|---|
| muestra la caja | sí |
| envía `q` | sí |
| `q` en `queryKey` | sí |
| reinicio de página | no aplica: paginación de cliente, sin estado propio |
| `PRODUCT FRONTEND CHANGE` | **0** |

El placeholder sigue siendo el genérico «Buscar en esta pantalla…»; nombrarlo como en
terceros es cosmético y no está en la autorización: se registra (§14).

## 7. El endpoint, físicamente

| | |
|---|---|
| Ruta | `GET /api/v1/organization/companies` · `list_companies` · `app/modules/organization/api.py:55` |
| Seguridad | `get_current_user` (tenant en `user.tenant_id`); sin `CompanyContext` (`TENANT/INSTALLATION`, N10: «el selector precede al contexto») |
| Alcance | `WHERE tenant_id = user.tenant_id` en SQL, y después `accessible_company_ids` (la autoridad `user_scopes`) en Python |
| Parámetros pre-fix | **ninguno** |
| Filtros funcionales | ninguno |
| Orden | `created_at` |
| Respuesta | **array plano** de `{id, code, legal_name, trade_name, rif, status, functional_currency, allowed_actions}`; sin `total`, sin `page`: **no pagina** (`EMPRESAS-SIN-SOBRE`, abierta) |

Consecuencia para el encargo: «`q` antes de count/paginación» y «`total` filtrado» no
tienen contraparte física; lo que sí puede exigirse, y se exige, es que la respuesta sea
**exactamente el conjunto que coincide**, entero y en el orden de siempre.

## 8. `/speckit.specify`

Tras `FR-001-132`:

| ID | Requisito | Prioridad |
|---|---|---|
| FR-001-133 | El listado de empresas acepta un parámetro de consulta opcional `q` | P0 |
| FR-001-134 | `q` busca únicamente sobre `code`, `legal_name`, `trade_name` y `rif` | P0 |
| FR-001-135 | La búsqueda se ejecuta en el backend sobre el conjunto autorizado | P0 |
| FR-001-136 | El frontend no se limita a filtrar lo cargado: cada término es una petición | P0 |
| FR-001-137 | El tenant sale del contexto autenticado, nunca de `q`, la consulta o el cuerpo | P0 |
| FR-001-138 | `q` se aplica dentro del alcance de tenant y del alcance del usuario (AND), en SQL, antes de cualquier recorte | P0 |
| FR-001-139 | La respuesta es el conjunto filtrado completo (este listado no pagina) | P0 |
| FR-001-140 | Sin `q`, o con `q` vacía, el listado es el de antes | P0 |
| FR-001-141 | Un término sin coincidencias responde 200 con lista vacía | P0 |
| FR-001-142 | Un término que coincide devuelve esa empresa y ninguna no coincidente | P0 |
| FR-001-143 | La búsqueda preserva el aislamiento entre tenants | P0 |
| FR-001-144 | La búsqueda preserva el orden existente | P0 |
| FR-001-145 | OpenAPI declara `q` como cadena opcional | P0 |
| FR-001-146 | El trato a parámetros realmente desconocidos no cambia (`API-QUERY-SILENCIOSA` sigue abierta) | P0 |
| FR-001-147 | La semántica de `Company.code` no cambia | P0 |
| FR-001-148 | Sin cambios de esquema ni migraciones | P0 |
| FR-001-149 | Cobertura backend, frontend, E2E y mutaciones que impidan que la búsqueda vuelva a quedar muerta | P0 |

| ID | Criterio |
|---|---|
| AC-028 | **Dado** una empresa con marcador único en cada uno de los cuatro campos, **cuando** se busca el marcador, **entonces** solo aparece esa empresa |
| AC-029 | **Dado** `ALFA-OBJETIVO` en dos tenants, **entonces** cada administrador encuentra solo la suya |
| AC-030 | **Dado** un usuario limitado a D1, **cuando** busca una empresa del tenant fuera de su alcance, **entonces** obtiene lista vacía |
| AC-031 | **Dado** un término inexistente, **entonces** 200 y `[]`, y en pantalla el estado vacío |
| AC-032 | **Dado** el término en minúsculas o un fragmento interior, **entonces** coincide |

## 9. `/speckit.clarify`

| # | Pregunta | Respuesta |
|---|---|---|
| 1–3 | dueñas | 001 · 001 (`FR-001-065`) · 012 |
| 4 | `EmpresasPage` | `src/pages/EmpresasPage.tsx` |
| 5–7 | endpoint / handler / servicio | `GET /api/v1/organization/companies` · `list_companies` · sin servicio: el `select` vive en el handler, como en terceros |
| 8 | sobre de respuesta | array plano; no pagina |
| 9 | parámetros pre-fix | ninguno |
| 10–11 | `q` ausente / ignorada pre-fix | sí / sí (§4) |
| 12 | campos | `code`, `legal_name`, `trade_name`, `rif` — confirmados, no reabiertos |
| 13–17 | match / mayúsculas / fragmento / trim / comodines | contiene · no distingue · sí · sin trim · sin escape (precedente) |
| 18 | nulos | solo `trade_name`; `ilike` sobre `NULL` no coincide ni rompe |
| 19 | orden | `created_at`, se conserva |
| 20 | filtros existentes | ninguno |
| 21 | alcance | tenant en SQL + `accessible_company_ids` |
| 22–23 | paginación / total | no existen en este endpoint (`EMPRESAS-SIN-SOBRE`) |
| 24 | `q` en `queryKey` | sí |
| 25 | reinicio de página | no aplica |
| 26 | debounce | no hay; no se añade |
| 27 | OpenAPI | gana `q` (`query`, `string`, opcional); nada más |
| 28–29 | esquema / migración | 0 / 0 |
| 30 | rendimiento | `ilike` sin índice funcional sobre una tabla de decenas de filas por tenant (empresas jurídicas): correcto; observación registrada, sin índice por reflejo |
| 31–33 | pruebas / mutaciones / regresión | §12, §13 |

**MATERIAL OQ = 0. UNKNOWN = 0.**

## 10. `/speckit.plan` y diseño

W01–W39 del encargo ejecutados en el orden dado; los que dependen de paginación (W14, W23)
se resolvieron como «no existe» con su evidencia.

```
select(Company).where(tenant_id = user.tenant_id)
  → if q: .where(code ILIKE %q% OR legal_name ILIKE %q% OR trade_name ILIKE %q% OR rif ILIKE %q%)
  → order_by(created_at)
  → [c for c in … if c.id in accessible_company_ids]     ← ya existía
```

Sin servicio nuevo, sin abstracción de búsqueda, sin `trim`, sin escape, sin índice.

## 11. CONSTITUTION GATE

| # | Puerta | Veredicto |
|---|---|---|
| G-COMPSEARCH-01..03 | checkpoint · dueñas · decisión previa | **PASA** |
| G-COMPSEARCH-04..05 | reproducido desde UI · desde API | **PASA** — §4 |
| G-COMPSEARCH-06..07 | `q` contractual · campos confirmados | **PASA** |
| G-COMPSEARCH-08..11 | match · mayúsculas · trim · comodines | **PASA** — precedente medido |
| G-COMPSEARCH-12 | alcance de tenant verificado | **PASA** |
| G-COMPSEARCH-13..15 | count/paginación · filtros · orden | **PASA** — no pagina; sin filtros; `created_at` |
| G-COMPSEARCH-16..18 | `queryKey` · reinicio · OpenAPI | **PASA** |
| G-COMPSEARCH-19..22 | esquema 0 · migración 0 · sin política de parámetros · sin identidad de `code` | **PASA** |
| G-COMPSEARCH-23..25 | pruebas · mutaciones · regresión | **PASA** — §12, §13 |
| G-COMPSEARCH-26..28 | MATERIAL OQ 0 · UNKNOWN 0 · trazabilidad 100 % | **PASA** |

## 12. `/speckit.tasks`, `/speckit.analyze` previo e `/speckit.implement`

| ID | Tarea | Ficheros | Requisito | Mutación |
|---|---|---|---|---|
| T-01 | Checkpoint, ruido de modo, artefactos | — | — | — |
| T-02 | Dueñas y decisión recuperada | — | — | — |
| T-03 | Reproducción API y navegador | `qa/repro-empresas-busqueda-q.py` | 136, 141 | — |
| T-04 | Precedente y semántica | `evidence/…/precedente-terceros.txt` | 134 | 08, 09 |
| T-05 | Parámetro `q` declarado | `organization/api.py` | 133, 145 | 01 |
| T-06 | Predicado sobre los cuatro campos, en SQL, dentro del tenant | `organization/api.py` | 134, 135, 137, 138, 142–144 | 02–07 |
| T-07 | Suite backend (17 pruebas) | `tests/test_company_search.py` | 149 | 01–09 |
| T-08 | Prueba de página (3) | `src/pages/EmpresasPage.test.tsx` | 136, 149 | — |
| T-09 | E2E (5) | `e2e/empresas-busqueda.spec.ts` | 141–143, 149 | — |
| T-10 | Mutaciones, SQLite y PostgreSQL | — | 149 | 01–09 |
| T-11 | Regresión backend, puertas del frontend, E2E de la pantalla | — | 140, 146, 148 | — |
| T-12 | Documentación y roadmap | este fichero, `docs/roadmap/*` | — | — |

**Huérfanos: 0 requisitos, 0 tareas.** Análisis previo sobre `e6968fe`: `q` en
`organization/api.py`: 0 → 1 declarado; `tenant_id`/`company_id` como parámetros: 0;
filtrado en Python de `q`: 0; SQL en cadena: 0; índices/migraciones: 0; `sleep`/`skip` en
las pruebas nuevas: 0. BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0.

**Implementado**: `resources/backend/app/modules/organization/api.py` (+15/−4): `q: str = ""`
y el predicado; el docstring dice por qué esos campos y esa semántica. `mypy` señala dos
errores en `company_context.py:83-84` que **ya estaban en HEAD** y no se tocan.

## 13. Evidencia — `evidence/empresas-busqueda-q/`

| Fichero | Qué demuestra |
|---|---|
| `reproduccion-api-pre-fix.txt` / `-post-fix.txt` | `q` ignorada → `q` aplicada, en ambos tenants; la sonda de parámetro desconocido responde igual antes y después |
| `reproduccion-ui-pre-fix.txt` / `-post-fix.txt` | en Chromium, por el menú: 2→2 filas antes; 2→0 / 2→1 después, y limpiar devuelve las 2 |
| `precedente-terceros.txt` | el patrón canónico, tal cual está escrito |
| `mutaciones.txt` | 9 mutantes: 7 muertos en SQLite; el 08 muere en PostgreSQL; el 06 es equivalente |
| `n10-postgresql.txt` | 5/5: deriva ORM/base 0, ninguna operación sin alcance |
| `frontend-gates.txt` | `tsc -b` 0 · ESLint 0 · Vitest **388/388** (385 + 3) · `vite build` correcto |
| `e2e.txt` | **22/22** en Chromium: 5 nuevas + `empresa-helper` 4 + `n6-multicompany` 13 |
| `regresion-postgresql.txt` | backend completo sobre PostgreSQL |

### Mutaciones

| Mutación | Qué reintroduce | Resultado |
|---|---|---|
| SEARCH-COMP-01 | `q` deja de aplicarse | **muere** — 15 pruebas |
| SEARCH-COMP-02..05 | cada campo fuera del OR | **muere** — la de su campo, y más |
| SEARCH-COMP-06 | con `q`, la búsqueda **sustituye** al `where` de tenant | **sobrevive, equivalente**: `accessible_company_ids` se calcula sobre `Company.tenant_id == user.tenant_id` y descarta lo ajeno; la salida es idéntica. El `where` de tenant se conserva en SQL de todos modos |
| SEARCH-COMP-07 | `q` en Python después de recortar | **muere** — 12 |
| SEARCH-COMP-08 | `like` en vez de `ilike` | **sobrevive en SQLite** (su `LIKE` ya ignora mayúsculas) y **muere en PostgreSQL** — 2 pruebas: la semántica queda probada en el motor de producción |
| SEARCH-COMP-09 | igualdad en vez de «contiene» | **muere** — 7 |

### Regresión y comprobaciones

| Suite | Resultado |
|---|---|
| `tests/test_company_search.py` | **17/17** en SQLite y en PostgreSQL |
| Aislamiento, N10, multiempresa (dirigidas, PostgreSQL) | verdes (la comparación ORM/base pasa en solitario; en el lote compartido choca con el motor SQLite que otro módulo deja configurado, ya observado en el ciclo anterior) |
| Backend completo, PostgreSQL | **1.546 pasadas · 27 saltadas · 127 no verdes, las 127 atribuidas y con la misma forma que en el ciclo anterior (+17 pasadas: esta suite)**: 37 por `clamscan` ausente (35 documentales + 2 de `test_n9_integrity`), 88 por la ruta fija `.venv/bin/alembic` (17 fallos + 71 errores), 2 de `test_treasury` por `FATAL: sorry, too many clients already` —la suite llegó a **80 conexiones abiertas de 100** (`conexiones-durante-la-corrida.txt`); el módulo pasa 25/25 en solitario—. Una corrida previa dio 354 errores con la misma causa, agravada por un `pytest` huérfano que retenía 38 conexiones; se eliminó y se repitió limpia (`regresion-postgresql.txt`) |
| Frontend | `tsc -b` 0 · ESLint 0 · Vitest 388/388 · `vite build` 0 |
| E2E de la pantalla de Empresas | 22/22 |

## 14. Deudas y hallazgos, registrados y no absorbidos

| ID | Estado |
|---|---|
| `UI-BUSQUEDA-MUERTA` | **PARTIALLY_RESOLVED**: Empresas **CLOSED**; Auditoría y Existencias `MATERIAL_DECISION_REQUIRED` |
| `EMPRESAS-SIN-SOBRE` | abierta: el listado sigue siendo un array plano sin `total` ni `page`; si algún día pagina, `q` ya está antes de cualquier recorte |
| `EMPRESAS-PLACEHOLDER-GENERICO` (nuevo, cosmético) | la caja dice «Buscar en esta pantalla…»; terceros nombra sus campos («Buscar por nombre, RIF o código…») |
| `BUSQUEDA-Q-SIN-ESCAPE` (nuevo, observación transversal) | ningún `q` del producto escapa `%` ni `_`: un término con esos caracteres actúa como comodín. Es la convención vigente en siete endpoints; decidir otra es transversal |
| `TEST-SCHEMAS-PG-SIN-LIMPIEZA` (nuevo, entorno) | `make_engine` crea un schema y un motor por módulo sobre PostgreSQL y no suelta ni el schema ni las conexiones: tres corridas completas dejaron `ktest` en 6,8 GB, llenaron el `tmpfs` de 7,6 GB del clúster de QA y PostgreSQL cayó durante la cuarta; y dentro de una sola corrida las conexiones ociosas llegan a 80 de las 100 del clúster, con dos pruebas de tesorería erroneando por `too many clients`. Se soltó y recreó la base; la regresión se repitió sobre una base limpia |
| `PERFORMANCE_OBSERVATION` | `ilike` sobre cuatro columnas sin índice funcional; volumen de empresas jurídicas por tenant: decenas. Sin acción |
| `API-QUERY-SILENCIOSA`, `API-COMPANY-ID-EN-CONSULTA`, `SEED-EMPRESA-CODIGO-NO-UNICO` | sin cambio |

## 15. Estado resultante

| Cosa | Estado |
|---|---|
| `EMPRESAS-BUSQUEDA-Q` | **CLOSED / CONVERGED** |
| Ficheros de producto | 1 (backend) · frontend 0 |
| Pruebas nuevas | 17 backend · 3 frontend · 5 E2E · mutaciones 8/9 efectivas + 1 equivalente |
| Esquema · migraciones · índices | 0 · 0 · 0 |
| Contrato público | gana `q`; nada más cambia |
| Decisiones nuevas de la dueña | ninguna |
