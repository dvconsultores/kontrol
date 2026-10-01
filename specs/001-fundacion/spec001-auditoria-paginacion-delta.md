# SPEC 001 · DELTA DIRIGIDO AUDITORIA-PAGINACION-CLIENTE — LA BITÁCORA SE PAGINA EN EL SERVIDOR, UNA SOLA VEZ

> Delta de frontend dentro de la Spec 001 (Fundación, que implementa el Master 006
> «Auditoría/observabilidad» y el Master 005 «Design System»); Spec 012 (QA integral,
> Master 054) como apoyo. Cierra `AUDITORIA-PAGINACION-CLIENTE`: la pantalla de Auditoría
> deja de paginar en cliente la página que el servidor ya le entrega paginada. Reutiliza
> `DataTable.manualPagination` tal como quedó en `EMPRESAS-SIN-SOBRE`. No toca el backend,
> `DataTable`, la búsqueda (`UI-BUSQUEDA-MUERTA`), la columna Fecha ni el alcance de tenant.
>
> Primer delta funcional ejecutado con la orquestación Claude + DeepSeek
> (`docs/governance/ai-orchestration-policy.md`).

## 0. Checkpoint

| Comprobación | Valor |
|---|---|
| `ACTUAL_HEAD` / `REMOTE_HEAD` | **`571e589`** / `571e589` — `develop` al día con `origin/develop` |
| `ACTUAL_BRANCH` | `develop`; no se crea ninguna rama |
| `COMMITS_AFTER_E813E6F` | **4**, los cuatro de orquestación (`98fe053`, `c8adc0d`, `4fcb8a9`, `571e589`); ninguno toca producto. Se conservan |
| `WORKTREE_STATE` | limpio |
| `ORCHESTRATION_STATUS` | `VERIFIED_END_TO_END`; `orchestration_readiness.py`: 11/11 |
| `DEEPSEEK_TOOL` | `mcp__deepseek__deepseek_chat`, visible en esta sesión (llamada de prueba respondida) |
| `DEEPSEEK_MODEL_ROUTING` | `deepseek-v4-flash` por defecto; `deepseek-v4-pro` solo si una tarea delegable lo exige |
| Entorno | PostgreSQL de QA en 55432 (`kaud` sembrada); backend en 8000 y Vite en 5173 levantados para este ciclo |

## 1. Veredicto, por delante

**El servidor ya paginaba; la pantalla no le pedía más que la primera página y, encima, la
volvía a paginar.** Medido en el navegador antes de tocar nada: la API publica
`total = 10 279` y entrega `items = 20`; la tabla enseña 10, ofrece «Página 1 de 2» y
pulsar «siguiente» no produce ninguna petición. **De 10 279 eventos, la pantalla deja ver
20.** El arreglo es el patrón convergido de Empresas: la página y su tamaño son estado de
la pantalla, viajan en la petición y en la clave de caché, la tabla recibe
`manualPagination` y el paginador se gobierna con el `total` del sobre.

Ficheros de producto: **2**, los dos de frontend (`api/audit.ts`, `pages/AuditoriaPage.tsx`).
Backend, `DataTable`, esquema, migraciones, índices: **0**.

## 2. Dueñas

| | Dueña | Evidencia |
|---|---|---|
| `PRIMARY_OWNER` | **Spec 001** (`001-fundacion`) — Master 006 Auditoría | `spec-equivalence-map.md`: «006 → `001-fundacion` + `009-reportes-auditoria`». La pantalla `/auditoria` y `GET /audit/events` son de la 001 (FR-001-070..072); la 009 es dueña de `/reporting/audit/timeline`, que este delta no toca. La deuda está registrada con «dueña 001» |
| `SHARED_UI_OWNER` | Spec 001 — Master 005 Design System (`DataTable`, `Pagination`) | mismo mapa. **No se modifica** |
| `CONTRACT_OWNER` | Spec 001 — `contracts/api-contracts.md:11`: «Listados con `q`, `status`, `sort`, `page`, `page_size`» | |
| `QA_OWNER` | Spec 012 (`012-auditoria-integral-e2e`) — Master 054 | matriz de navegadores y deuda `E2E-FLAKY-BAJO-CARGA` |
| `OWNER_IDENTITY_CONFLICT` | **0** | |

La hipótesis del encargo decía «SPEC006»: es el número del Master. La carpeta dueña es
`001-fundacion`; no hay conflicto, solo dos numeraciones.

## 3. Lo que había, medido

`evidence/auditoria-paginacion/reproduccion-ui-pre-fix.txt`, entrando por el menú:

| | Valor |
|---|---|
| Petición de la pantalla | `GET /audit/events?q=` — sin `page` ni `page_size` |
| `API_PAGE` · `API_PAGE_SIZE` · `API_ITEMS` · `API_TOTAL` | 1 · 20 · 20 · **10 279** |
| Forma | `{items, page, page_size, total}` |
| `UI_PAGE_INDEX` · `UI_LOCAL_PAGE_SIZE` · `UI_VISIBLE_ROWS` | 0 · 10 · **10** |
| Paginador | uno, el interno de `DataTable`: «Página 1 de 2», «Mostrando 1–10 de 20 registros» |
| Al pulsar «siguiente» | **0 peticiones**; la tabla pasa a «Mostrando 11–20 de 20» |
| Eventos alcanzables | **20 de 10 279** |
| `DOUBLE_PAGINATION` | **YES** |
| Consola | un 401 de `auth/refresh` anterior al inicio de sesión; ajeno a la pantalla |

El caso es visible sin fabricar nada: el servidor entrega 20 y la tabla corta en 10. En
Empresas, con 10 por página en los dos lados, el defecto habría sido invisible.

### El mecanismo exacto

`AuditoriaPage` entrega `query.data.items` a `DataTable` sin `manualPagination`. Sin esa
prop, `DataTable` monta `getPaginationRowModel()` de TanStack (tamaño 10 por defecto), pinta
su propio `Pagination` cuando `data.length > 10` y su pie «Mostrando…», todo calculado con
`data.length`. La pantalla no tiene estado de página, no envía `page` ni `page_size` y su
clave de caché es `["audit", "events", search]`.

### El contrato del servidor (`resources/backend/app/modules/audit/api.py`)

| | |
|---|---|
| Endpoint | `GET /api/v1/audit/events`, permiso `audit:view`, alcance de tenant |
| `page` | `Query(1, ge=1)` — **base 1** |
| `page_size` | `Query(20, ge=1, le=100)` |
| Fuera de rango | 422 |
| Más allá del final | 200 con `items: []` (medido: `page=515`) |
| Orden | `event_time DESC` |
| `total` | el del conjunto ya filtrado por tenant y por los filtros; no depende de la página |
| Filtros del servidor | `entity_type`, `entity_id`, `action` — **la pantalla no expone ninguno** |
| `q` | no declarado: el servidor lo ignora (`UI-BUSQUEDA-MUERTA`) |

`BACKEND PRODUCT CHANGE = 0`: el contrato ya soporta lo que la pantalla necesita.

### El precedente (`e813e6f`, `EmpresasPage.tsx`)

| Pieza | Empresas | Auditoría, objetivo |
|---|---|---|
| Estado | `pagina` (base 0), `tamano` (10) | igual |
| Petición | `page: pagina + 1`, `page_size: tamano` | igual |
| Clave de caché | `[…, search, pagina, tamano]` | `["audit", "events", search, pagina, tamano]` |
| Tabla | `manualPagination`, `data = items` | igual |
| Paginador | `Pagination` de la pantalla si `total > 10` (FR-019), con `total` del sobre | igual |
| Cambio de tamaño | vuelve a la primera página | igual |
| Cambio de búsqueda | vuelve a la primera página | **no se copia** (§5, punto 24) |
| Cliente de API | objeto de consulta; `page` y `page_size` viajan siempre; plantilla plana | igual |

`DataTable.manualPagination` es un booleano: desactiva el modelo de paginación local, el
paginador interno y el pie. No hay `rowCount`, `pageCount` ni `onPaginationChange`: el
`total` y los manejadores son del `Pagination` que pinta la pantalla. Tamaños que ofrece
`Pagination`: 10, 25, 50, 100 — todos dentro del máximo del contrato.

## 4. `/speckit.specify`

Los identificadores continúan la serie de la Spec 001 (último usado: FR-001-190, AC-049).
Entre paréntesis, el del encargo.

| ID | Requisito |
|---|---|
| FR-001-191 (AUDP-001) | La pantalla de Auditoría pagina en el servidor: la página que pinta es la que el servidor entrega |
| FR-001-192 (AUDP-002) | Las filas son exactamente `response.items` |
| FR-001-193 (AUDP-003) | `DataTable` no vuelve a paginar `response.items` |
| FR-001-194 (AUDP-004) | Se reutiliza `DataTable.manualPagination`, sin mecanismo paralelo |
| FR-001-195 (AUDP-005) | El paginador se gobierna con `response.total` |
| FR-001-196 (AUDP-006) | Cambiar de página produce una petición nueva |
| FR-001-197 (AUDP-007) | La página de la interfaz (base 0) viaja como `page = índice + 1` |
| FR-001-198 (AUDP-008) | Cambiar el tamaño produce una petición con el `page_size` nuevo y vuelve a la primera página |
| FR-001-199 (AUDP-009) | `page` y `page_size` forman parte de la clave de caché |
| FR-001-200 (AUDP-010/011) | La pantalla no tiene filtros (medido): no se añaden, y no hay convención de reinicio que aplicar |
| FR-001-201 (AUDP-012) | Se conserva `PagedResult<AuditEvent>` como único tipo de respuesta |
| FR-001-202 (AUDP-013) | Se conserva la columna Fecha: `event_time` con `formatearFecha` |
| FR-001-203 (AUDP-014) | Se conserva el aislamiento de tenant en `items` y en `total` |
| FR-001-204 (AUDP-015) | La caja de búsqueda no cambia de comportamiento: sigue enviando lo que enviaba y no adquiere efectos nuevos |
| FR-001-205 (AUDP-016) | El backend no cambia |
| FR-001-206 (AUDP-017) | `DataTable` y `Pagination` no cambian |
| FR-001-207 (AUDP-018) | Hay pruebas que hacen visible una doble paginación y fallan si se quita `manualPagination` |
| FR-001-208 (AUDP-019) | Hay pruebas que detectan `total = items.length`, la clave sin página, la clave sin tamaño, el desfase de uno y el tamaño sin reinicio |
| FR-001-209 (AUDP-020) | Esquema, migraciones e índices: 0 |
| FR-001-210 | El paginador solo aparece si `total > 10` (FR-019), y carga, error y vacío se conservan |

| AC | Criterio |
|---|---|
| AC-050 | Con más de 10 eventos, la pantalla ofrece tantas páginas como `ceil(total / tamaño)` y cada una se pide al servidor |
| AC-051 | Con 25 por página, la tabla pinta las 25 filas recibidas y hay un solo paginador |
| AC-052 | En la última página se pinta el resto y «siguiente» queda deshabilitado |

## 5. `/speckit.clarify`

| # | Pregunta | Respuesta, medida |
|---|---|---|
| 1–3 | Dueñas | Spec 001 (primaria y de interfaz compartida); Spec 012 (QA) |
| 4 | Endpoint | `GET /api/v1/audit/events` |
| 5–8 | `page`, `page_size`, valores por defecto, máximo | `page` ≥ 1 (1); `page_size` 1..100 (20) |
| 9–10 | Base de página | API: 1 · interfaz: 0 · `page = pagina + 1` |
| 11 | Forma | `{items, total, page, page_size}` |
| 12 | `total` | conjunto filtrado por tenant; independiente de la página |
| 13 | Orden | `event_time DESC`, sin desempate (§12, observación) |
| 14–15 | Estado actual de página y tamaño | no existe |
| 16–17 | Modo actual y mecanismo | paginación local de TanStack sobre la página del servidor (§3) |
| 18–20 | API de `manualPagination` | booleano; `total` y manejadores van en `Pagination` |
| 21–22 | Clave de caché | de `["audit","events",search]` a `["audit","events",search,pagina,tamano]` |
| 23 | Filtros existentes | **ninguno** en la pantalla. `entity_type`, `entity_id` y `action` existen solo en el servidor |
| 24 | Reinicio por filtro | sin filtros, no aplica. **La caja de búsqueda no reinicia la página**: el servidor ignora `q`, así que escribir en ella no cambia el conjunto; hacer que salte a la página 1 daría un efecto visible nuevo a un control cuya función está pendiente de decisión de la dueña. El reinicio llegará con esa decisión |
| 25 | Reinicio por tamaño | sí, a la primera página (patrón de Empresas) |
| 26–28 | Carga, error, vacío | los de `DataTable`, sin cambios; el paginador no se pinta sin datos |
| 29 | Última página | `Pagination` deshabilita «siguiente» con `ceil(total / tamaño)` |
| 30 | ¿Cambia el backend? | **NO** |
| 31 | ¿Cambia `DataTable`? | **NO** |
| 32 | ¿Cambia la pantalla? | **SÍ**: `AuditoriaPage.tsx` y `api/audit.ts` |
| 33–35 | Esquema, migraciones, índices | 0 · 0 · 0 |
| 36 | Pruebas dirigidas | Vitest con un servidor de mentira que pagina de verdad; pruebas de tipo; cliente de API |
| 37 | E2E | sobre la respuesta que la propia pantalla recibe y el orden por `event_time`; nunca sobre un total fijo: la bitácora crece con cada inicio de sesión de otras pruebas |
| 38 | Mutaciones | §7 |
| 39 | Clasificación | §8 |

Sobre `q`: `listAuditEvents` sigue enviando `q` cuando la caja tiene texto, como hacía. No
se añade, no se quita, no se decide qué busca y no se usa en las pruebas nuevas.

`MATERIAL OQ = 0`. `UNKNOWN = 0`.

## 6. `/speckit.plan` y diseño

`api/audit.ts` — el mismo molde que `api/organization.ts`:

```ts
export interface ConsultaDeAuditoria { q?: string; page?: number; page_size?: number }
export function listAuditEvents(consulta: ConsultaDeAuditoria = {}): Promise<AuditEventPage>
// q solo si tiene texto; page y page_size viajan siempre (por defecto 1 y 20);
// la ruta es una plantilla plana: `/audit/events?${params.toString()}`
```

`pages/AuditoriaPage.tsx` — el mismo molde que `EmpresasPage.tsx`: `pagina` (0) y `tamano`
(10) como estado; clave `["audit", "events", search, pagina, tamano]`; petición
`{ q: search, page: pagina + 1, page_size: tamano }`; `DataTable` con `manualPagination`;
`Pagination` de la pantalla si `total > 10`, con `total` del sobre, y cambio de tamaño que
vuelve a la primera página. `SearchInput` queda como está.

Pasos: W01 reconciliación · W02 orquestación · W03 dueñas · W04 precedente · W05
reproducción · W06 contrato · W07–W11 estado, tabla, bases, clave, filtros · W12 diseño ·
W13 clasificación · W14 implementación · W15–W16 pruebas de componente y de tipo · W17 E2E
dirigido · W18 mutaciones · W19–W21 regresión de sobre, fecha y tenant · W22 Vitest, tipos,
lint, build · W23 matriz de navegadores · W24 E2E global, una corrida · W25 atribución ·
W26 `analyze` final · W27 trazabilidad · W28 convergencia.

## 7. Pruebas y mutaciones, diseñadas antes de implementar

Vitest, con un servidor de mentira que corta por `page` y `page_size`:

| ID | Caso | Requisito |
|---|---|---|
| PAG-01 | 108 eventos: el paginador dice «Página 1 de 11», no una página | 195 |
| PAG-02 | con 25 por página se pintan las 25 filas y hay un solo paginador | 193, 194, 207 |
| PAG-03 | «siguiente» pide `page=2&page_size=10` y pinta la página 2, no la 1 | 196 |
| PAG-04 | la primera petición es `page=1`; la segunda página es `page=2` | 197 |
| PAG-05 | elegir 25 pide `page_size=25` | 198, 199 |
| PAG-06 | desde la página 3, elegir 25 vuelve a `page=1` | 198 |
| PAG-07 | ir a la 2 y volver a la 1 pinta otra vez la 1 | 199 |
| PAG-10 | 23 eventos: la página 3 tiene 3 filas y «siguiente» queda deshabilitado | AC-052 |
| PAG-11 | `items=[]`, `total=0`: estado vacío, sin paginador | 210 |
| PAG-12 | sin respuesta: estado de carga | 210 |
| PAG-13 | error: alerta, no vacío, sin paginador | 210 |
| PAG-14 | la petición devuelve `PagedResult<AuditEvent>` y acepta la consulta tipada | 201 |
| PAG-16, 17, 18 | 7 eventos: sin paginador; exactamente 10: sin paginador; 11: «Página 1 de 2» | 210 |
| CLI-01..05 | cliente: por defecto `page=1&page_size=20`; página y tamaño pedidos; lo que falta toma el valor del contrato; devuelve el sobre sin transformarlo; tipo | 197, 199, 201 |

PAG-08 (clave con tamaño) queda cubierta por PAG-05 y PAG-06; PAG-09 (reinicio por
filtro) no aplica: no hay filtros. PAG-15 (fecha) y el sobre siguen en sus propios
ficheros, `AuditoriaPage.fecha.test.tsx` y `AuditoriaPage.test.tsx`.

| Mutante | Cambio | Debe matarlo |
|---|---|---|
| M-01 | quitar `manualPagination` | PAG-02 |
| M-02 | `total` del paginador = `items.length` | PAG-01 |
| M-03 | clave sin `pagina` | PAG-03 |
| M-04 | clave sin `tamano` | PAG-05 |
| M-05 | `page: pagina` (sin `+ 1`) | PAG-04 |
| M-06 | cambiar tamaño sin volver a la primera página | PAG-06 |
| M-07 | — no aplica: no existe ningún filtro que reinicie | — |
| M-08 | segundo corte local: `items.slice(0, 10)` | PAG-02 |
| M-09 | el paginador aparece siempre, aunque `total ≤ 10` | PAG-16 |
| M-10 | la petición no envía `page_size` | PAG-05, CLI |
| M-11 | el cliente no envía `page` | CLI, PAG-03 |

E2E (`e2e/auditoria-paginacion.spec.ts`), sobre una pila real:

| ID | Escenario |
|---|---|
| PAG-E2E-01 | entrar por el menú: la petición lleva `page=1&page_size=10`; las filas son los `items` recibidos; el paginador usa el `total` recibido. «Siguiente»: la petición lleva `page=2` y las filas son los `items` de esa respuesta; dentro de cada página el orden es del más reciente al más antiguo. «Anterior»: vuelve la página 1 |
| PAG-E2E-02 | elegir 25: la petición lleva `page=1&page_size=25` y se ven las 25 filas, con un solo paginador |
| PAG-E2E-03 | desde la página 2, elegir 25 vuelve a `page=1` |
| PAG-E2E-04 | por API: la última página trae el resto, una página más allá viene vacía, y `page=0` y `page_size=101` dan 422 |

El diseño inicial de PAG-E2E-01 tenía dos aserciones erróneas, corregidas durante la
implementación (§10): esperaba una petición al volver a la página 1, y afirmaba un orden
entre páginas que una bitácora viva no garantiza.

Las aserciones se hacen contra la respuesta que la pantalla recibe y contra el orden, no
contra un total fijo ni contra la posición de un evento: otras pruebas en paralelo inician
sesión y empujan la bitácora.

## 8. CONSTITUTION GATE

| | | |
|---|---|---|
| G01 HEAD reconciliado | `571e589` | ✅ |
| G02 orquestación operativa | 11/11, herramienta visible | ✅ |
| G03 dueña resuelta | Spec 001 | ✅ |
| G04–G07 defecto, paginación del servidor, sobre y doble paginación demostrados | §3 | ✅ |
| G08–G09 precedente y `manualPagination` entendidos | §3 | ✅ |
| G10–G12 bases, `total`, tamaño | §5 | ✅ |
| G13 clave objetivo | §6 | ✅ |
| G14–G15 filtros inventariados y reinicio | ninguno; §5 punto 24 | ✅ |
| G16–G17 backend y `DataTable` | 0 · 0 | ✅ |
| G18 `q` excluida | §5 | ✅ |
| G19–G21 fecha, sobre y tenant preservados | regresiones en §7 | ✅ |
| G22–G24 esquema, migraciones, índices | 0 · 0 · 0 | ✅ |
| G25 tareas clasificadas | §9 | ✅ |
| G26–G27 mutaciones y E2E definidos | §7 | ✅ |
| G28–G30 `MATERIAL OQ`, `UNKNOWN`, trazabilidad | 0 · 0 · 100 % | ✅ |

Principios: 1 (Spec antes que código), 2 (autorización del encargo), 3 (trazabilidad), 7
(frontend uniforme: mismo patrón que Empresas), 10 (calidad demostrable), 22 (autoridad
única: un solo mecanismo de paginación de servidor), 27 (mutaciones observables).
**Gate: PASS.**

## 9. `/speckit.tasks` y `/speckit.analyze` previo

| ID | Tarea | Req. | EXECUTOR · MODEL | SEC | EGRESS | Ficheros | Prueba |
|---|---|---|---|---|---|---|---|
| T01 | Reconciliación, orquestación, dueñas | — | CLAUDE | NO | n-a | — | §0, §2 |
| T02 | Reproducción en navegador | 191 | CLAUDE | NO | n-a | `qa/repro-auditoria-paginacion.mjs` | `reproduccion-ui-pre-fix.txt` |
| T03 | Contrato, precedente, diseño, casos y mutantes | todos | CLAUDE | NO | n-a | este documento | §3–§7 |
| T10 | Pruebas del cliente de API (CLI-01..05) | 197, 199 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `src/api/audit.test.ts` (nuevo) | la propia |
| T11 | Pruebas de paginación de la pantalla (PAG-01..18) | 191–199, 207–210 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `src/pages/AuditoriaPage.paginacion.test.tsx` (nuevo) | la propia |
| T12 | Ajustar la suite del sobre: URL nueva en ENV-01; ENV-05 afirmaba la paginación en cliente y se retira | 192, 201 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `src/pages/AuditoriaPage.test.tsx` | la propia |
| T13 | Cliente y pantalla según §6 | 191–199, 204, 210 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `src/api/audit.ts`, `src/pages/AuditoriaPage.tsx` | T10, T11, T12, `typecheck` |
| T14 | E2E de paginación; la suite E2E del sobre deja de suponer el corte en cliente | AC-050..052 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `e2e/auditoria-paginacion.spec.ts` (nuevo), `e2e/auditoria-sobre.spec.ts` | Playwright dirigido |
| T20 | Auditar, aplicar y probar cada parche | — | CLAUDE | NO | n-a | — | por tarea |
| T21 | Mutaciones | 207, 208 | CLAUDE | NO | n-a | — | `mutaciones.txt` |
| T22 | Regresión: sobre, fecha, tenant, `DataTable`, Empresas | 201–203, 206 | CLAUDE | YES | n-a | — | §11 |
| T23 | Vitest completo, tipos, lint, build | — | CLAUDE | NO | n-a | — | `frontend-gates.txt` |
| T24 | E2E dirigido, matriz, una corrida global y atribución | — | CLAUDE | NO | n-a | — | `e2e-*.txt` |
| T25 | `analyze` final, trazabilidad, convergencia, hoja de ruta, Git | — | CLAUDE | NO | n-a | documentos | §13 |

`RETRY_MAX: 2` en las delegadas. Orden: primero las pruebas (T10–T12), que deben fallar
contra el código actual; después la implementación (T13), que las pone en verde.

Por qué son delegables T10–T14: contrato cerrado, ficheros identificados, patrón existente
que imitar, casos escritos por Claude, resultado verificable, sin decisión de arquitectura,
seguridad ni negocio. Ninguna toca autenticación, tenant, dinero ni datos.

`analyze` previo — buscado en el repositorio: `AuditoriaPage`, `listAuditEvents`,
`manualPagination`, `getPaginationRowModel`, `queryKey`, `items.length`, `q`, `event_time`,
`formatearFecha`, `Array.isArray`, `any`:

| | |
|---|---|
| `BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` | 0 · 0 · 0 · 0 |
| Requisitos huérfanos · tareas huérfanas | 0 · 0 |
| `MATERIAL OQ` · `UNKNOWN` | 0 · 0 |
| Trazabilidad | 100 % |
| Consumidores de `listAuditEvents` | uno: `AuditoriaPage.tsx` (más sus dos suites) |

**Autorización de `implement`:** la del encargo `AUDITORIA-PAGINACION-CLIENTE`.

## 10. `/speckit.implement` — quién hizo qué

Toda la implementación delegable la propuso DeepSeek y la aplicó Claude tras auditarla.
Detalle por llamada en `evidence/auditoria-paginacion/orquestacion.txt`, leído de las
trazas de cada ejecutor.

| Tarea | Intentos | Resultado |
|---|---|---|
| T12 ajuste de la suite del sobre | 1 | `AUDIT_PASS` |
| T13 cliente y pantalla (**el producto**) | 1 | `AUDIT_PASS`: los cuatro bloques coincidían exactamente y el resultado es el diseño de §6 |
| T10 pruebas del cliente | 2 | intento 1 `AUDIT_REJECT`: importaba el módulo dentro de cada prueba, contra un invariante escrito · reintento 1 `AUDIT_PASS` |
| T11 pruebas de la pantalla | 2 | intento 1 `AUDIT_REJECT`: un `import` a mitad de fichero y una cabecera que describía mal el defecto · reintento 1 `AUDIT_PASS`, y su diferencia con el intento 1 son exactamente los motivos del rechazo |
| T14 E2E | 3 | intento 1 y reintento 1 rechazados por **errores de contrato de Claude**, no del ejecutor (abajo) · reintento 2 `AUDIT_PASS` |

```
tareas totales 14 · CLAUDE_ONLY 9 · DEEPSEEK_ELIGIBLE 5 · ejecutadas por DeepSeek 5
DEEPSEEK CALLS 9 · reintentos 4 (tope de 2 por tarea, respetado) · modelo deepseek-v4-flash en todas
parches rechazados 4 · parches aplicados 6 · parches retocados a mano por Claude 0
tokens DeepSeek 31 286 / 19 805 · coste DeepSeek $0.0098
EGRESS_CHECK en las 9 cargas reales: secretos 0 · ficheros .env 0 · session_id 0 · thinking 0
```

Lo que Claude hizo entero: la reproducción (`qa/repro-auditoria-paginacion.mjs`), el
contrato, el diseño, los casos de prueba y los mutantes, las auditorías, la aplicación, las
pruebas, las mutaciones, la atribución de fallos y este documento.

### Los dos errores de contrato, que fueron de Claude

1. **«Anterior» no vuelve a pedir la página 1.** El encargo del E2E esperaba una petición
   al volver de la página 2 a la 1. La aplicación configura `staleTime: 30_000`
   (`src/main.tsx`): dentro de esos 30 s la página 1 sale de la caché. Detectado al auditar,
   antes de aplicar.
2. **La página 2 puede repetir filas de la 1.** El encargo afirmaba que ningún evento de la
   página 2 es más reciente que el más antiguo de la 1. Es falso en una bitácora que crece:
   si entran eventos entre las dos peticiones, todo se desplaza. Lo destapó la matriz de
   tres navegadores en paralelo (1 fallo de 48, repetido en tres corridas). La aserción
   correcta, y la que queda, es el orden dentro de cada página.

Los dos se corrigieron **cambiando el contrato del encargo y volviendo a delegar**, no
retocando el parche. El segundo deja registrada una propiedad real del producto:
`AUDITORIA-OFFSET-EN-BITACORA-VIVA`.

### Primero las pruebas, y en rojo

Antes de aplicar T13, contra el código anterior: `audit.test.ts` 3 de 5 en rojo;
`AuditoriaPage.paginacion.test.tsx` 8 de 15 en rojo (PAG-01 a PAG-07 y PAG-10; las siete
que pasaban son carga, error, vacío, tipo y umbral, que no dependen del arreglo);
`AuditoriaPage.test.tsx` ENV-01 en rojo. Después de T13: todo en verde.

## 11. Evidencia — `evidence/auditoria-paginacion/`

| Fichero | Qué demuestra |
|---|---|
| `reproduccion-ui-pre-fix.txt` | 20 eventos alcanzables de 10 279; «siguiente» no pide nada: `DOUBLE_PAGINATION=YES` |
| `reproduccion-ui-post-fix.txt` | `page=1..4&page_size=10`, una petición por pulsación; «Página 4 de 1044»; `DOUBLE_PAGINATION=NO` |
| `orquestacion.txt` | las 9 delegaciones: modelo servido, tokens, coste, carga sin secretos, relevo literal, veredicto |
| `mutaciones.txt` | **17 de 17 mutantes muertos**, con `GOOD → PASS` y `RESTORED → PASS` |
| `mutaciones-e2e.txt` | la suite de navegador también ve el defecto: 4 mutantes, los 4 la hacen fallar |
| `frontend-gates.txt` | `typecheck`, `lint`, **Vitest 431/431** (27 ficheros) y `build`, todos con salida 0 |
| `backend-dirigido.txt` | aislamiento de tenant y paginación del servidor: 11/11 en SQLite y 11/11 en PostgreSQL; backend sin cambios |
| `e2e-dirigido-chromium.txt` | 16/16 |
| `e2e-matriz.txt` | Chromium, Firefox y WebKit en paralelo, **tres corridas seguidas: 48/48 cada una** |
| `e2e-global.txt` | la corrida global autoritativa y su atribución |

Vitest: la referencia era 412. Ahora **431** = 412 − 1 (ENV-05, que afirmaba la paginación
en cliente) + 5 (cliente) + 15 (pantalla).

### Mutaciones

| Mutante | Lo matan |
|---|---|
| M-01 sin `manualPagination` | PAG-01, PAG-02, PAG-05 |
| M-02 `total` = `items.length` (y M-02b en el umbral) | PAG-01 y siete más |
| M-03 clave sin página | PAG-03, 04, 06, 07, 10 |
| M-04 clave sin tamaño | PAG-02, PAG-05 |
| M-05 desfase de uno | 12 pruebas |
| M-06 tamaño sin volver a la primera | PAG-06 |
| M-07 filtro sin reinicio | **no aplica**: la pantalla no tiene filtros |
| M-08 segundo corte local | PAG-02, PAG-05 |
| M-09 / M-09b umbral del paginador | PAG-17 · PAG-11, 16, 17 |
| M-10 a M-15 petición, valores por defecto, tamaño inicial, manejador | CLI y PAG |
| M-16 la Fecha vuelve a `created_at` | la suite de fecha |

Ninguno equivalente. En el navegador: M-01, M-03, M-05 y M-06 hacen fallar el E2E.

### Regresión

| | |
|---|---|
| Sobre (`AUDITORIA-SOBRE-VS-ARRAY`) | 6 pruebas de componente y 2 E2E × 3 navegadores, en verde |
| Fecha (`AUDITORIA-CREATED-AT`) | 5 pruebas y 1 E2E × 3 navegadores, en verde; el mutante M-16 muere |
| Tenant (`AUDIT-EVENTS-SIN-TENANT`) | 11/11 en SQLite y en PostgreSQL; E2E ENV-04 en verde |
| `DataTable` | sin cambios; su suite en verde |
| Empresas (`EMPRESAS-SIN-SOBRE`, `EMPRESAS-BUSQUEDA-Q`) | 9 pruebas de pantalla, 5 de cliente y 9 E2E × 3 navegadores, en verde |
| Guarda de completitud | en verde: lee la ruta de `api/audit.ts` porque es una plantilla plana |

### E2E global — una corrida autoritativa

Chromium, 35 ficheros de suite, **240 pruebas** (las 236 de la referencia más las 4
nuevas): **199 pasan, 40 omitidas, 1 falla**. Las suites del objetivo —paginación, sobre,
fecha— y las de Empresas pasan dentro de esa misma corrida.

| | |
|---|---|
| `TEST` | `putaway.spec.ts:187` (Spec 022 — put-away): caduca a los 30 s en `waitForLoadState("networkidle")` |
| `TARGET RELATED` | **NO**: 0 referencias a `/auditoria` o `/audit/events`; pantalla y endpoints de inventario |
| `PASSES ALONE` | **SÍ**: 3 de 3, repetida en solitario |
| `PREEXISTING FLAKY EVIDENCE` | **SÍ**: `E2E-FLAKY-BAJO-CARGA` ya registra `putaway.spec.ts` (línea 405) entre las cuatro pruebas que cayeron una vez cada una el 2026-09-30 |
| `NEW REGRESSION` | **NO** |
| Clasificación | **`PREEXISTING_FLAKY`** — no se repite la corrida global |

En la matriz dirigida apareció además, una vez, un `ECONNRESET` del inicio de sesión por API
en `auditoria-sobre` ENV-04 (WebKit); es la misma familia —el backend de QA es un solo
proceso— y no volvió a aparecer en las tres corridas finales de 48.

## 12. Deudas y hallazgos, registrados y no absorbidos

| | |
|---|---|
| **`AUDITORIA-OFFSET-EN-BITACORA-VIVA`** (nueva) | la paginación por desplazamiento repite filas entre páginas cuando la bitácora crece mientras se pagina. Inherente al contrato; evitarlo sería paginación por cursor |
| **`AUDIT-TOTAL-CARGA-TODO`** (nueva) | el servidor cuenta `total` cargando todos los eventos del tenant: 450 ms por página con 10 648 eventos |
| **`AUDIT-ORDEN-SIN-DESEMPATE`** (nueva) | orden solo por `event_time`; hoy 0 instantes repetidos entre los 500 más recientes |
| **`EJECUTOR-ABREVIA-EL-CONTEXTO`** (nueva, herramientas) | el puente abrevió el contexto en 4 de 9 delegaciones, y consumió ~323 000 tokens de Sonnet para transportar ~51 000 de DeepSeek |
| `DATATABLE-CAPTION-EN-MODO-MANUAL` | evidencia nueva en Auditoría: con 10 433 eventos el `caption` dice «Resultados: 10 registros». No se toca |
| `UI-BUSQUEDA-MUERTA` / Auditoría | intacta. La caja sigue enviando `q` y, a propósito, no reinicia la página; anotado en la deuda |
| `AUDIT-OPENAPI-SIN-RESPONSE-MODEL`, `LISTADOS-SIN-RESPONSE-MODEL` | intactas |
| `E2E-FLAKY-BAJO-CARGA` | ver la corrida global |
| `E2E-SIN-TYPECHECK` | sigue: las suites de `e2e/` no pasan por `tsc`; las nuevas pasaron `eslint` y se ejecutaron |

Con paginación de servidor y la misma espera que Empresas, al cambiar de página la tabla
da paso al estado de carga y el paginador desaparece hasta que llega la respuesta. Es el
comportamiento del patrón convergido, no se cambia aquí.

## 13. `/speckit.analyze` final, trazabilidad y convergencia

| | |
|---|---|
| Ficheros de producto | **2**: `src/api/audit.ts`, `src/pages/AuditoriaPage.tsx` |
| Backend · `DataTable` · `Pagination` | 0 · 0 · 0 |
| Esquema · migraciones · índices | 0 · 0 · 0 (57 migraciones, cabeza `0057_spec047_notifications`, sin tocar) |
| `q` | ni añadida, ni quitada, ni usada en pruebas nuevas |
| `any`, casts, uniones array/sobre, `Array.isArray` | 0 en el producto |
| `sleep`, reintentos, `skip`, tiempos de espera aumentados | 0 |
| Ramas creadas | 0 |
| `BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` | 0 · 0 · 0 · 0 |
| `MATERIAL OQ` · `UNKNOWN` | 0 · 0 |

| Requisito | Prueba que lo demuestra |
|---|---|
| FR-001-191, 192 | PAG-01, PAG-03; PAG-E2E-01; ENV-01 |
| FR-001-193, 194, 207 | PAG-02; PAG-E2E-02; M-01, M-08 |
| FR-001-195 | PAG-01, PAG-18; M-02 |
| FR-001-196 | PAG-03; PAG-E2E-01; M-03, M-15 |
| FR-001-197 | PAG-04; CLI-01..03; M-05, M-11 |
| FR-001-198 | PAG-05, PAG-06; PAG-E2E-02, 03; M-06, M-10, M-12 |
| FR-001-199 | PAG-03, PAG-05, PAG-07; M-03, M-04 |
| FR-001-200 | inventario de §3: 0 filtros; nada que probar |
| FR-001-201 | PAG-14, CLI-05, ENV-07, ENV-08 |
| FR-001-202 | suite de fecha; M-16 |
| FR-001-203 | `test_audit_tenant_isolation.py` ×2 motores; E2E ENV-04 |
| FR-001-204 | la caja no se tocó (`git diff`); ninguna prueba nueva la usa |
| FR-001-205, 206, 209 | `git diff --stat`: 0 ficheros de backend, de componentes y de migraciones |
| FR-001-208 | M-02, M-03, M-04, M-05, M-06 muertos |
| FR-001-210 | PAG-11, 12, 13, 16, 17, 18; M-09 |
| AC-050, 051, 052 | PAG-01 y PAG-E2E-01 · PAG-02 y PAG-E2E-02 · PAG-10 y PAG-E2E-04 |

Trazabilidad: **20/20 requisitos y 3/3 criterios** con prueba. **Gate de convergencia: PASA.**

## 14. Estado resultante

| | |
|---|---|
| `AUDITORIA-PAGINACION-CLIENTE` | **CLOSED / CONVERGED** — 2026-10-01 |
| Deudas que siguen cerradas | `AUDIT-EVENTS-SIN-TENANT`, `AUDITORIA-SOBRE-VS-ARRAY`, `AUDITORIA-CREATED-AT`, `EMPRESAS-BUSQUEDA-Q`, `EMPRESAS-SIN-SOBRE` |
| Master 56 | 56 filas, sin cambio de estado; la 001 sigue `PARTIALLY_IMPLEMENTED` |
| Decisiones de la dueña pendientes | las mismas: `UI-BUSQUEDA-MUERTA` (Auditoría, Existencias), `API-QUERY-SILENCIOSA`, `SEED-EMPRESA-CODIGO-NO-UNICO`, `MOVTYPE-GLOBAL-SIN-UNICIDAD`, `FECHAS-ZONA-DE-PRESENTACION` |
