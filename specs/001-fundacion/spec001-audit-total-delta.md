# SPEC 001 · DELTA DIRIGIDO AUDIT-TOTAL-CARGA-TODO — EL TOTAL DE LA BITÁCORA LO CUENTA LA BASE

> Delta de backend dentro de la Spec 001 (Fundación, que implementa el Master 006
> «Auditoría/observabilidad»); Spec 012 (QA integral, Master 054) como apoyo. Cierra
> `AUDIT-TOTAL-CARGA-TODO`: `GET /audit/events` deja de traerse la bitácora entera del tenant
> para saber cuántos eventos hay. No cambia el contrato, el sobre, la paginación, el orden,
> el alcance de tenant, los filtros, el frontend, el esquema ni los índices.

## 0. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` | `cf35c27` / **`cf35c27`** / `cf35c27` |
| `ACTUAL_BRANCH` | `develop`; no se crea ninguna rama |
| `COMMITS_AFTER_CF35C27` | 0 |
| `WORKTREE_STATE` | limpio |
| `ORCHESTRATION_STATUS` | `VERIFIED_END_TO_END`; `orchestration_readiness.py` 11/11 |
| `DEEPSEEK_TOOL` · `MODEL ROUTING` · `RETRY_MAX` | `mcp__deepseek__deepseek_chat` · `deepseek-v4-flash` por defecto · 2 |

## 1. Veredicto, por delante

**Para decir un número, el servidor construía trece mil objetos.** Medido en PostgreSQL,
con 13 576 eventos del tenant y una página de 10: la base devuelve **13 586 filas** por
petición, el ORM construye **13 586 entidades**, y de los ~377 ms que tarda el endpoint la
base solo gasta ~40. El resto es Python materializando lo que luego reduce a `len(...)`.
El arreglo: `total` sale de un `SELECT count(*)` sobre exactamente el mismo conjunto
—tenant y filtros— del que después se corta la página.

Ficheros de producto: **1** (`app/modules/audit/api.py`). Frontend, contrato, esquema,
migraciones, índices: **0**.

## 2. Dueñas

| | Dueña | Evidencia |
|---|---|---|
| `PRIMARY_OWNER` | **Spec 001** (`001-fundacion`) | `spec-equivalence-map.md`: «006 Auditoría → `001-fundacion` + `009-reportes-auditoria`». `GET /audit/events` es FR-001-070..072, de la 001. La deuda está registrada con «dueña 001» |
| `AUDIT_DOMAIN_OWNER` | Spec 001 para el listado de tenant; la 009 es dueña de `/reporting/audit/timeline`, que este delta no toca | mismo mapa |
| `QA_OWNER` | Spec 012 (`012-auditoria-integral-e2e`), Master 054 | |
| `OWNER_IDENTITY_CONFLICT` | **0** — «SPEC006» en el encargo es el número del Master, no una carpeta | |

## 3. Lo que había, medido

`DISCOVERY_DOC`: `spec001-auditoria-paginacion-delta.md` §12. `EVIDENCE_PATH`:
`evidence/auditoria-paginacion/`. `ORIGINAL_TIMING`: 450 ms por página por HTTP.
`ORIGINAL_EVENT_COUNT`: 10 648.

Reproducción de este ciclo, `evidence/audit-total/reproduccion-pre-fix.txt`
(`qa/repro-audit-total.py`, la aplicación real en proceso contra `kaud`, PostgreSQL de QA):

| | Página 1 | Página 51 |
|---|---|---|
| Eventos del tenant (`total`) | 13 576 | 13 576 |
| `page_size` | 10 | 10 |
| Latencia del endpoint, 5 peticiones (min · mediana · max) | 199 · **377** · 387 ms | 194 · **370** · 381 ms |
| Sentencias sobre `audit_events` | 2 | 2 |
| Filas que devuelve la base | **13 586** | **13 586** |
| Entidades `AuditEvent` construidas | **13 586** | **13 586** |
| Tiempo en la base | 41 ms | 39 ms |

### Causa raíz (`resources/backend/app/modules/audit/api.py:53`)

```python
total = len(db.execute(query).scalars().all())
```

| | |
|---|---|
| `TOTAL_CURRENT_IMPLEMENTATION` | `len()` de la lista de todas las entidades del conjunto |
| `QUERY_CURRENT` | `SELECT <18 columnas> FROM audit_events WHERE tenant_id = … [AND filtros] ORDER BY event_time DESC`, sin `LIMIT` |
| `MATERIALIZES_ALL_ROWS` | **SÍ** — 13 576 filas, con sus columnas JSON `before`/`after` |
| `PYTHON_COUNT` | **SÍ** |
| `SERIALIZATION_BEFORE_COUNT` | no: la serialización a diccionarios solo recorre la página. El coste es construir las entidades |
| `FILTERS_APPLIED` | `entity_type`, `entity_id`, `action`, por igualdad, cuando vienen |
| `TENANT_PREDICATE` | `AuditEvent.tenant_id == user.tenant_id`, lo primero |

Y la base, además, **ordena** las 13 576 filas para una consulta cuyo único uso es
contarlas: `Sort Method: external merge  Disk: 5256kB`.

Es el único listado del producto que cuenta así: los demás usan
`select(func.count()).select_from(query.subquery())` (16 apariciones en `app/modules`).

### El conjunto lógico

| Pieza | Items | Count objetivo |
|---|---|---|
| Tenant | `tenant_id == user.tenant_id` | el mismo objeto de consulta |
| `entity_type`, `entity_id`, `action` | igualdad, si vienen | los mismos |
| Fechas, `request_id`, `q` | **no existen** como filtros del endpoint | — |
| Joins | **ninguno**: `FROM audit_events` | ninguno → `COUNT_DISTINCT_REQUIRED = NO` |
| `ORDER BY event_time DESC` | sí | **no** |
| `LIMIT` / `OFFSET` | sí | **no** |

## 4. `/speckit.specify`

Continúan la serie de la Spec 001 (último usado: FR-001-210, AC-052). Entre paréntesis, el
identificador del encargo.

| ID | Requisito |
|---|---|
| FR-001-211 (AUDCOUNT-001) | `total` se calcula con una operación de conteo en la base, sin construir las entidades `AuditEvent` del conjunto |
| FR-001-212 (002) | El conteo y los items aplican el mismo predicado de tenant |
| FR-001-213 (003) | El conteo y los items aplican exactamente los mismos filtros |
| FR-001-214 (004) | El conteo es anterior a la paginación: sin `LIMIT`, sin `OFFSET` y sin `ORDER BY` |
| FR-001-215 (005) | `total` es exacto: nada de estimaciones |
| FR-001-216 (006) | La forma de la respuesta no cambia: `items`, `total`, `page`, `page_size` |
| FR-001-217 (007) | La paginación no cambia |
| FR-001-218 (008) | La visibilidad por tenant no cambia |
| FR-001-219 (009) | El orden de los items no cambia: `event_time DESC` |
| FR-001-220 (010) | `q` no se toca |
| FR-001-221 (011) | Hay cobertura que falla si `total` vuelve a calcularse materializando el conjunto |
| FR-001-222 (012) | Hay cobertura de `total` por tenant, por cada filtro, por página y por tamaño |
| FR-001-223 (013) | Se mide antes y después sobre el mismo conjunto de datos |
| FR-001-224 (014) | Frontend, esquema, migraciones e índices: 0 |
| FR-001-225 (015) | `AUDIT-ORDEN-SIN-DESEMPATE` queda fuera |

| AC | Criterio |
|---|---|
| AC-053 | Una petición de una página de N eventos construye N entidades `AuditEvent`, sea cual sea el total |
| AC-054 | Una petición ejecuta dos sentencias sobre `audit_events`: un `SELECT count(*)` y la página |
| AC-055 | `total` es idéntico al número de eventos que se obtienen recorriendo todas las páginas, con cualquier combinación de filtros |

## 5. `/speckit.clarify`

| # | Pregunta | Respuesta, medida |
|---|---|---|
| 1 | Dueña | Spec 001; apoyo Spec 012 |
| 2–3 | Handler y servicio | `list_events` en `app/modules/audit/api.py`; no hay capa de servicio ni repositorio: la consulta vive en el handler |
| 4–6 | Implementación actual, SQL y filas | §3 |
| 7–8 | Tenant y filtros | §3 |
| 9–10 | Joins y riesgo de duplicados | ninguno · ninguno |
| 11 | `COUNT(*)` o `COUNT(id)` | **`count(*)`**: es lo que emite `func.count()`, el patrón de los otros 16 listados; `id` es clave primaria no nula, serían equivalentes |
| 12 | `DISTINCT` | **no** |
| 13 | Orden actual | `event_time DESC`, sin desempate. Se conserva tal cual en los items |
| 14–15 | Dónde se pagina y dónde se cuenta | en el handler, sobre el mismo objeto `query` |
| 16 | API del ORM | `db.execute(select(func.count()).select_from(query.subquery())).scalar_one()`, con `query` **sin** `order_by` |
| 17 | Sentencias esperadas | **2**: conteo y página |
| 18–22 | Frontend, forma de la API, esquema, migraciones, índices | 0 · 0 · 0 · 0 · 0 |
| 23 | Medición | la misma sonda antes y después, sobre `kaud`: 5 peticiones a la página 1 y 5 a la 51; min, mediana, max; sentencias, filas y entidades; `EXPLAIN ANALYZE` |
| 24 | Pruebas | un observador de SQL y de cargas del ORM (`tests/audit_world.py`): comportamiento, no texto del código fuente |
| 25 | Mutaciones | §7 |
| 26 | Clasificación | §9 |
| 27 | ¿Es separable la deuda del orden? | **SÍ**. El conteo no necesita orden; el `ORDER BY` solo se mueve de sitio —de la consulta base a la de items— y la sentencia de items resultante es idéntica. Añadir un desempate cambiaría el SQL de los items: no se hace |

`MATERIAL OQ = 0`. `UNKNOWN = 0`.

## 6. `/speckit.plan` y diseño

```python
query = select(AuditEvent).where(AuditEvent.tenant_id == user.tenant_id)
if entity_type: query = query.where(AuditEvent.entity_type == entity_type)
if entity_id:   query = query.where(AuditEvent.entity_id == entity_id)
if action:      query = query.where(AuditEvent.action == action)

total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
items = db.execute(
    query.order_by(AuditEvent.event_time.desc()).offset((page - 1) * page_size).limit(page_size)
).scalars().all()
```

- **Un solo conjunto.** El conteo y la página salen del mismo objeto `query`: no hay dos
  listas de filtros que puedan divergir. No se crea ningún constructor de consultas.
- **El orden se aplica solo a los items.** Hoy `order_by` está en la consulta base; si se
  dejara ahí, la subconsulta del conteo lo arrastraría. Se mueve a la consulta de items,
  cuyo SQL queda byte a byte igual que hoy.
- **Sin índice nuevo.** La base ya resuelve esto en ~40 ms; el defecto es la
  materialización. Lo que `EXPLAIN` diga del plan se registra, no se absorbe.

Pasos: W01 reconciliación · W02 orquestación · W03 dueñas · W04 evidencia previa · W05
reproducción · W06–W07 implementación actual y SQL · W08 predicados · W09 joins · W10–W11
orden y separabilidad · W12–W13 conteo y reutilización · W14 medición · W15 clasificación ·
W16 implementación · W17–W20 pruebas · W21 sonda · W22 mutaciones · W23 SQLite · W24
PostgreSQL · W25 backend completo · W26 E2E de Auditoría · W27 frontend sin cambios · W28
`analyze` final · W29 trazabilidad · W30 convergencia.

## 7. Pruebas y mutaciones, diseñadas antes de implementar

`tests/test_audit_total_count.py`, sobre el mundo de dos tenants de `tests/audit_world.py`:

| ID | Caso | Req. |
|---|---|---|
| COUNT-01 | 37 eventos, página de 5: `total == 37` | 215 |
| COUNT-02 | páginas 1, 2, 8 y 9 (más allá del final): `total` siempre 37 | 214, 217 |
| COUNT-03 | tamaños 1, 10 y 100: `total` siempre 37 | 214 |
| COUNT-04 | hostil: A y B con la misma marca; cada uno cuenta lo suyo. Sin filtro, crear eventos en B no mueve el `total` de A | 212, 218 |
| COUNT-05 | `action` solo: cuenta los de esa acción | 213 |
| COUNT-06 | `entity_type` solo | 213 |
| COUNT-07 | `entity_id` solo | 213 |
| COUNT-08 | rango de fechas — **no aplica**: el endpoint no tiene ese filtro | — |
| COUNT-09 | filtros combinados: `total` e items son el mismo conjunto | 213 |
| COUNT-10 | 37 eventos, página de 5: se construyen **5** entidades, no 42; más allá del final, 0 | 211, 221, AC-053 |
| COUNT-11 | dos sentencias: una `count(` sin `ORDER BY`, `LIMIT` ni `OFFSET`; la otra con `ORDER BY audit_events.event_time DESC` y `LIMIT`. El mismo número con página de 5 que de 50 | 214, 219, AC-054 |
| COUNT-12 | forma: claves del sobre y de cada item, `total` entero | 216 |
| COUNT-13 | 23 eventos de 10 en 10: `[10, 10, 3]`, sin repetidos, todos, y cada página en orden no creciente | 217, 219 |
| COUNT-14 | sin coincidencias: `items == []`, `total == 0`, y se siguen ejecutando las dos sentencias | 215 |
| COUNT-15 | 300 eventos, página de 10: 10 entidades construidas, `total == 300` | 211, 221 |
| COUNT-16 | paridad: para seis combinaciones de filtros, `total` es igual al número de eventos obtenido recorriendo todas las páginas, y ese conjunto es el esperado | AC-055 |

| Mutante | Cambio | Debe matarlo |
|---|---|---|
| M-01 | volver a `len(...all())` | COUNT-10, 11, 15 |
| M-02 | conteo sin el predicado de tenant | COUNT-04 |
| M-03 | conteo que ignora `action` | COUNT-05, 09, 16 |
| M-03b | conteo que ignora `entity_id` | COUNT-07 |
| M-03c | conteo que ignora `entity_type` | COUNT-06 |
| M-04 | conteo que ignora la fecha — **no aplica** | — |
| M-05 | conteo después de `LIMIT`/`OFFSET` | COUNT-01, 02 |
| M-06 | conteo de todo el tenant, sin filtros | COUNT-01, 09 |
| M-07 | `total = len(items)` | COUNT-01, 03 |
| M-08 | duplicado por join — **no aplica**: no hay joins | — |
| M-09 | el conteo arrastra el `ORDER BY` | COUNT-11 |
| M-10 | los items pierden el `ORDER BY` | COUNT-11, 13 |
| M-11 | los items pierden el predicado de tenant | suite de tenant existente |

## 8. CONSTITUTION GATE

| | | |
|---|---|---|
| G01 checkpoint · G02 orquestación · G03 dueña | §0, §2 | ✅ |
| G04–G06 causa reproducida, materialización demostrada, SQL entendido | §3 | ✅ |
| G07–G09 tenant, filtros, joins | §3 | ✅ |
| G10–G13 conteo definido; items, forma y paginación preservados | §6 | ✅ |
| G14 deuda del orden separable | §5, punto 27 | ✅ |
| G15–G18 frontend, esquema, migraciones, índices | 0 | ✅ |
| G19–G21 pruebas, mutaciones y medición definidas | §5, §7 | ✅ |
| G22 tareas clasificadas | §9 | ✅ |
| G23–G25 `MATERIAL OQ`, `UNKNOWN`, trazabilidad | 0 · 0 · 100 % | ✅ |

Principios: 1, 2, 3, 6 (seguridad en backend: el tenant sale del usuario y gobierna también
el conteo), 10, 21 (paridad de motor: SQLite y PostgreSQL), 22, 27. **Gate: PASS.**

## 9. `/speckit.tasks` y `/speckit.analyze` previo

| ID | Tarea | Req. | EXECUTOR · MODEL | SEC | EGRESS | Ficheros | Prueba |
|---|---|---|---|---|---|---|---|
| T01 | Reconciliación, orquestación, dueñas | — | CLAUDE | NO | n-a | — | §0, §2 |
| T02 | Sonda y reproducción en PostgreSQL | 223 | CLAUDE | NO | n-a | `qa/repro-audit-total.py` | `reproduccion-pre-fix.txt` |
| T03 | Causa raíz, conjunto lógico, diseño del conteo, casos y mutantes | todos | CLAUDE | YES | n-a | este documento | §3–§7 |
| T04 | Mundo de dos tenants y observador de SQL y de cargas | 221 | CLAUDE | YES | n-a | `tests/audit_world.py` | humo |
| T10 | Suite COUNT-01..16 sobre el mundo de T04 | 211–219, 221, 222 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `tests/test_audit_total_count.py` (nuevo) | la propia: roja en COUNT-10, 11, 14 y 15 antes de T11 |
| T11 | El conteo en el handler, según §6 | 211–219 | **CLAUDE** | **YES** | n-a | `app/modules/audit/api.py` | T10, suite de tenant |
| T20 | Auditar, aplicar y probar el parche de T10 | — | CLAUDE | NO | n-a | — | — |
| T21 | Mutaciones | 221, 222 | CLAUDE | YES | n-a | — | `mutaciones.txt` |
| T22 | Sonda posterior y `EXPLAIN` | 223 | CLAUDE | NO | n-a | — | `reproduccion-post-fix.txt` |
| T23 | Backend completo en SQLite y PostgreSQL, con control de recursos | — | CLAUDE | NO | n-a | — | `backend-completo.txt` |
| T24 | Regresión E2E de Auditoría y corrida global | 216–218 | CLAUDE | NO | n-a | — | `e2e-*.txt` |
| T25 | `analyze` final, trazabilidad, convergencia, hoja de ruta, Git | — | CLAUDE | NO | n-a | documentos | §13 |

`RETRY_MAX: 2` en la delegada.

**Por qué T11 no se delega**, aunque sea un cambio de cinco líneas con el contrato cerrado:
la edición mueve la línea del predicado de tenant, y `CLAUDE.md` reserva a Claude el
aislamiento de tenant «aunque DeepSeek pudiera generar el código». La política va por
delante de las instrucciones de la tarea.

**Por qué T04 no se delega y T10 sí:** el mundo de prueba lleva la contraseña de la siembra
de QA, que no sale a un proveedor externo; por eso vive en un módulo aparte y la suite, que
es la parte repetitiva, no la contiene ni la necesita.

`analyze` previo — buscado: `len(`, `.all()`, `func.count`, `subquery`, `order_by`,
`offset`, `limit`, `tenant_id`, `q`, joins, `distinct`:

| | |
|---|---|
| `BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` | 0 · 0 · 0 · 0 |
| Requisitos huérfanos · tareas huérfanas | 0 · 0 |
| `MATERIAL OQ` · `UNKNOWN` | 0 · 0 |
| Trazabilidad | 100 % |
| Otros `len(...all())` usados como total en `app/` | ninguno: es el único |

**Autorización de `implement`:** la del encargo `AUDIT-TOTAL-CARGA-TODO`.

## 10. `/speckit.implement` — quién hizo qué

| Tarea | Quién | Resultado |
|---|---|---|
| T04 mundo de prueba y observador | Claude | `tests/audit_world.py`; humo contra el handler anterior: 17 entidades construidas para una página de 5 |
| T10 suite COUNT-01..16 | **DeepSeek** `deepseek-v4-flash`, 2 intentos | intento 1 `AUDIT_REJECT`: las 15 pruebas eran las diseñadas, pero el docstring añadía «los casos … fallan contra el código actual», que sería falso al arreglar el handler · reintento 1 `AUDIT_PASS`: su diferencia con el intento 1 es exactamente esa frase |
| T11 el conteo en el handler | **Claude** | tres cambios en `app/modules/audit/api.py`: el `import`, la consulta base sin `order_by`, y `total`/`items` |

```
TASKS TOTAL 12 · CLAUDE_ONLY 11 · DEEPSEEK_ELIGIBLE 1 · DEEPSEEK EXECUTED 1
DEEPSEEK CALLS 2 · RETRIES 1 (tope 2) · PATCHES ACCEPTED 1 · REJECTED 1 · retocados a mano 0
MODELS USED deepseek-v4-flash · DEEPSEEK TOKENS 9 640 / 8 189 · COST $0.0036
SONNET BRIDGE TOKENS 88 591
EGRESS_CHECK en las 2 cargas reales: secretos 0 · credencial de QA 0 · session_id 0 · thinking 0
```

`EJECUTOR-ABREVIA-EL-CONTEXTO` no se reprodujo: en las dos delegaciones el puente envió
íntegro lo autorizado (el encargo en la primera; el intento anterior completo en la
segunda) y no leyó nada más. La deuda sigue abierta; aquí no se corrige.

### Primero las pruebas, y en rojo

Contra el handler anterior: **4 de 15 en rojo** —COUNT-10, 11, 14 y 15, las que miran cómo
se cuenta— y 11 en verde, porque el `total` anterior era correcto: lo malo era el camino.
Tras T11: 15 de 15, en SQLite y en PostgreSQL.

## 11. Evidencia — `evidence/audit-total/`

| Fichero | Qué demuestra |
|---|---|
| `reproduccion-pre-fix.txt` | 13 586 filas y 13 586 entidades por petición; 377 ms; la base ordena en disco lo que solo se va a contar |
| `reproduccion-post-fix.txt` | 11 filas y 10 entidades por petición; 30 ms; `SELECT count(*)` resuelto con `Index Only Scan` |
| `backend-dirigido.txt` | conteo (15) y aislamiento de tenant (11): 26/26 en SQLite y en PostgreSQL |
| `mutaciones.txt` | **14 de 14 mutantes muertos, en los dos motores** |
| `orquestacion.txt` | las 2 delegaciones: modelo, tokens, coste, carga sin secretos, contexto íntegro, veredicto |
| `backend-completo.txt` | la suite completa en SQLite y en PostgreSQL, con el control de recursos |
| `e2e-auditoria.txt`, `e2e-global.txt` | regresión de Auditoría en el navegador y corrida global |

### Antes y después, mismo conjunto de datos (`kaud`, PostgreSQL)

| | Antes | Después |
|---|---|---|
| `DATASET_ROWS` (eventos del tenant) | 13 576 | 13 577 |
| `PAGE_SIZE` | 10 | 10 |
| Latencia, página 1 (min · mediana · max) | 199 · **377** · 387 ms | 28 · **30** · 42 ms |
| Latencia, página 51 (min · mediana · max) | 194 · **370** · 381 ms | 29 · **30** · 31 ms |
| `QUERY_COUNT` sobre `audit_events` | 2 | 2 |
| `ROWS_MATERIALIZED` (filas que devuelve la base) | **13 586** | **11** |
| Entidades `AuditEvent` construidas | **13 586** | **10** |
| Tiempo en la base | 41 ms | 14 ms |

No hay un objetivo de latencia que cumplir; lo que converge es la causa: las filas que
viajan y los objetos que se construyen ya no dependen del tamaño de la bitácora.

### SQL, antes y después

| | Antes | Después |
|---|---|---|
| Camino del conteo | `SELECT <18 columnas> FROM audit_events WHERE tenant_id = … ORDER BY event_time DESC` → 13 576 filas → `len()` | `SELECT count(*) FROM (SELECT … FROM audit_events WHERE tenant_id = …) AS anon_1` → 1 fila |
| Plan del conteo | `Seq Scan` + `Sort` (`external merge`, 5 256 kB en disco), 15,8 ms | `Aggregate` sobre `Index Only Scan using ix_audit_events_tenant_id`, **1,4 ms**; PostgreSQL aplana la subconsulta |
| Página | `… ORDER BY event_time DESC LIMIT … OFFSET …` | **idéntica** |
| Plan de la página | `Seq Scan` + `top-N heapsort` | el mismo |

### Mutaciones

| Mutante | Lo matan |
|---|---|
| M-01 volver a `len(...all())` | COUNT-10, 11, 14, 15 |
| M-02 conteo sin tenant | COUNT-04 y la suite de tenant |
| M-03, M-03b, M-03c conteo que ignora `action`, `entity_id`, `entity_type` | COUNT-05, 06, 07, 09, 16 |
| M-04 fecha, M-08 join | **no aplican**: el endpoint no tiene filtro de fechas ni joins |
| M-05 conteo después de `LIMIT`/`OFFSET` | COUNT-01, 02, 03 y más |
| M-06 conteo de todo el tenant | COUNT-01 y más |
| M-07 `total = len(items)` | COUNT-01, 02, 03 |
| M-09 el conteo arrastra el `ORDER BY` | COUNT-11 |
| M-10, M-10b los items pierden o invierten el orden | COUNT-11, COUNT-13 |
| M-11 los items pierden el tenant | suite de tenant, COUNT-09, 16 |
| M-12 conteo de valores distintos | COUNT-01 y más |
| M-13 desfase de página en los items | COUNT-02, 13 |

`GOOD → PASS`, cada mutante `FAIL`, `RESTORED → PASS`, en SQLite y en PostgreSQL. Ninguno
equivalente.

### Backend completo

Una corrida por motor, con el handler nuevo (`backend-completo.txt`):

| | SQLite | PostgreSQL |
|---|---|---|
| Resultado | 746 pasan · 942 omitidas · **42 fallan** | 1 666 pasan · 27 omitidas · **37 fallan** |
| Fallos en pruebas de auditoría | 0 | 0 |
| Dónde fallan | `test_documents`, `test_documents_legacy_import`, `test_documents_security` | `test_documents`, `test_documents_security`, `test_n9_integrity` |
| La misma suite sobre `cf35c27` | el mismo conjunto de fallos | **el mismo conjunto, `diff` vacío** |
| Fallos nuevos por este delta | **0** | **0** |

Los fallos son de entorno y anteriores a este cambio: la máquina no tiene `clamscan`, y sin
él la subida de un documento no llega a crear versión. En SQLite, además, cae a veces la
prueba de hilos registrada como `AUTH-ROTACION-SQLITE-HILOS`. La referencia se midió sobre
una exportación limpia de `cf35c27` con el mismo intérprete. El backend queda **verde en lo
que es producto de este delta**; no queda verde sin más, y así se anota.

Control de recursos de la corrida de PostgreSQL (`TEST-SCHEMAS-PG-SIN-LIMPIEZA`, que no se
corrige aquí): `ktest` pasó de 111 MB a **3 240 MB** y de 10 a 313 esquemas; pico de **60
conexiones** de 100; el `tmpfs` bajó de 6,4 G libres a 2,5 G. Después se recreó `ktest`.

### Regresión en el navegador

`e2e-auditoria.txt`, Chromium, contra el backend con el handler nuevo: paginación, sobre y
fecha, **7/7**; y la reproducción de navegador recorre las páginas 1 a 4 con una petición
por pulsación («Página 4 de 1360»). Frontend: `git diff` vacío, así que no se repite la
matriz de tres navegadores ni Vitest.

Corrida global, una (`e2e-global.txt`): 240 pruebas, **196 pasan, 40 omitidas, 4 fallan**.

| `TEST` | `TARGET RELATED` | `PASSES ALONE` | `NEW REGRESSION` |
|---|---|---|---|
| `picking.spec.ts:192`, `:208`, `:240` | NO | SÍ, cada una | NO |
| `putaway.spec.ts:187` | NO | SÍ | NO |

Las cuatro caducan a los 30 s en pantallas de inventario. Ejecutadas una a una hicieron
**0 peticiones a `/audit/events`**, contadas en el registro de acceso del backend: no pasan
por el handler que cambió. `putaway.spec.ts:187` cayó igual en la corrida global del ciclo
anterior, antes de este cambio. Clasificación: **`PREEXISTING_FLAKY`**
(`E2E-FLAKY-BAJO-CARGA`); no se repite la corrida. Lo que sí queda anotado es que la
inestabilidad crece: cuatro caídas donde hubo una, sobre una base de QA que acumula corridas.

## 12. Deudas y hallazgos, registrados y no absorbidos

| | |
|---|---|
| **`AUDIT-PAGINA-SIN-INDICE-DE-ORDEN`** (nueva) | quitada la materialización, lo que queda es la página: `Seq Scan` del tenant más `top-N heapsort`, 14 ms con 13 577 eventos, porque no hay índice por `(tenant_id, event_time)`. Crece con la bitácora. Un índice es esquema y migración: no se absorbe |
| `AUDIT-ORDEN-SIN-DESEMPATE` | **sigue OPEN**. El `ORDER BY` de los items es el mismo, byte a byte; solo se movió de la consulta base a la de items |
| `AUDITORIA-OFFSET-EN-BITACORA-VIVA` | **sigue OPEN**. `total` y la página son dos sentencias sin instantánea común, como antes |
| `EJECUTOR-ABREVIA-EL-CONTEXTO` | sigue OPEN; no se reprodujo en este ciclo |
| `TEST-SCHEMAS-PG-SIN-LIMPIEZA` | sigue OPEN; medido en la corrida completa |
| `UI-BUSQUEDA-MUERTA`, `AUDIT-OPENAPI-SIN-RESPONSE-MODEL`, `LISTADOS-SIN-RESPONSE-MODEL` | intactas |

## 13. `/speckit.analyze` final, trazabilidad y convergencia

| Contador | Exigido | Medido |
|---|---|---|
| `FULL_MATERIALIZATION_FOR_TOTAL` · `PYTHON_TOTAL_COUNT` | 0 · 0 | 0 · 0 |
| `DB_COUNT_QUERY` | 1 | 1 |
| `TENANT_COUNT_DRIFT` · `FILTER_COUNT_DRIFT` · `PAGINATION_COUNT_DRIFT` | 0 · 0 · 0 | 0 · 0 · 0 — un solo objeto `query` |
| `ORDERING_CHANGED` · `API_SHAPE_CHANGED` · `FRONTEND_CHANGED` | 0 · 0 · 0 | 0 · 0 · 0 |
| `Q_IMPLEMENTED` · `CURSOR_PAGINATION` | 0 · 0 | 0 · 0 |
| `NEW_INDEX` · `SCHEMA_CHANGE` · `MIGRATION` | 0 · 0 · 0 | 0 · 0 · 0 |
| `NEW_TARGET_REGRESSION` | 0 | 0 |
| `sleep`, reintentos, `skip` | 0 | 0 |
| Ramas creadas | 0 | 0 |
| `BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` | 0 | 0 |
| `MATERIAL OQ` · `UNKNOWN` | 0 · 0 | 0 · 0 |

| Requisito | Prueba que lo demuestra |
|---|---|
| FR-001-211, 221 | COUNT-10, 14, 15; M-01; sonda: 13 586 → 10 entidades |
| FR-001-212, 218 | COUNT-04; suite de tenant (11); M-02, M-11 |
| FR-001-213 | COUNT-05, 06, 07, 09, 16; M-03, M-03b, M-03c, M-06 |
| FR-001-214 | COUNT-02, 03, 11; M-05, M-07, M-09 |
| FR-001-215 | COUNT-01, 16; M-12 |
| FR-001-216 | COUNT-12; E2E del sobre |
| FR-001-217 | COUNT-13; E2E de paginación; M-13 |
| FR-001-219 | COUNT-11, 13; M-10, M-10b; SQL de la página idéntico en la sonda |
| FR-001-220 | `git diff`: `q` no aparece |
| FR-001-222 | COUNT-01..09, 16 |
| FR-001-223 | `reproduccion-pre-fix.txt`, `reproduccion-post-fix.txt` |
| FR-001-224 | `git diff --stat`: 0 ficheros de frontend, de modelos y de migraciones |
| FR-001-225 | §12 |
| AC-053, 054, 055 | COUNT-10 y 15 · COUNT-11 · COUNT-16 |

Cada tarea → ejecutor → parche → auditoría → prueba → evidencia: §9, §10 y
`orquestacion.txt`. Trazabilidad: **15/15 requisitos y 3/3 criterios**.
**Gate de convergencia: PASA.**

## 14. Estado resultante

| | |
|---|---|
| `AUDIT-TOTAL-CARGA-TODO` | **CLOSED / CONVERGED** — 2026-10-01 |
| `AUDIT-ORDEN-SIN-DESEMPATE` · `AUDITORIA-OFFSET-EN-BITACORA-VIVA` | OPEN · OPEN |
| Deudas que siguen cerradas | `AUDIT-EVENTS-SIN-TENANT`, `AUDITORIA-SOBRE-VS-ARRAY`, `AUDITORIA-CREATED-AT`, `AUDITORIA-PAGINACION-CLIENTE`, `EMPRESAS-BUSQUEDA-Q`, `EMPRESAS-SIN-SOBRE` |
| Master 56 | 56 filas, sin cambio de estado; la 001 sigue `PARTIALLY_IMPLEMENTED` |
