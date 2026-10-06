# SPEC 054 · Delta dirigida — E2E-FLAKY-BAJO-CARGA

**Fecha** 2026-10-01 · **Dueña** SPEC054 (`specs/012-auditoria-integral-e2e`) ·
**Apoyo de producto** SPEC008 (`specs/008-almacenes-fisicos`, dueña de
`GET /organization/warehouses`) · **Base** `42cd793` · **Rama** `develop`

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` | `42cd793` / **`42cd793`** / `42cd793` |
| `ACTUAL_BRANCH` | `develop`; no se crea ninguna rama |
| `COMMITS_AFTER_42CD793` | 0 |
| `WORKTREE_STATE` | limpio |
| `ORCHESTRATION_STATUS` | `VERIFIED_END_TO_END`; `orchestration_readiness.py` 11/11 |
| `DEEPSEEK_TOOL` · `MODEL_ROUTING` · `RETRY_MAX` | `mcp__deepseek__deepseek_chat` · `deepseek-v4-flash` · 2 |

## 2. Veredicto, por delante

**No era azar, ni colisión entre pruebas, ni carga en general. Era una cuenta que subía con
cada corrida.**

Las pantallas de Picking y de Put-away llenan su desplegable «Almacén» con el listado
entero de la empresa. Ese listado ejecuta **12,7 sentencias SQL por almacén**. Cada prueba
E2E crea su propio almacén en la única empresa de la base de QA y no lo retira nunca. El
listado costaba un poco más en cada corrida, hasta que, con seis navegadores a la vez, las
pruebas que pasan por esas pantallas dejaron de caber en sus 30 segundos.

Se reproduce a voluntad: con 1 434 almacenes, `picking.spec.ts:192`, `:208` y `:240` caducan
**3 corridas de 3**. Son exactamente las tres que fallaban.

El defecto es de **producto** —un N+1 en `GET /organization/warehouses`—, destapado por la
manera de sembrar de las pruebas. El alcance se amplía a ese endpoint antes de implementar
(§9). Ni reintentos, ni esperas, ni menos trabajadores, ni más tiempo.

> **Esto es el veredicto con el que se entró a implementar, y resultó ser una parte.** Al
> certificar aparecieron otras tres cuentas que suben con la base de QA y dos carreras
> escritas en las pruebas. El veredicto final, con lo que queda abierto, está en §20.

## 3. Dueñas

| | Dueña | Evidencia |
|---|---|---|
| `PRIMARY_OWNER` | **SPEC054** — `specs/012-auditoria-integral-e2e` | la deuda está registrada con «dueña 054» |
| Listado de almacenes | **SPEC008** — `specs/008-almacenes-fisicos` | su contrato define `can_delete` y `allowed_actions`; `app/modules/organization/warehouse_api.py` y `structure.py` |
| `PICKING_PRODUCT_OWNER` | Master 031/032 → `005-ventas` (`PreparacionPage`) | `spec-equivalence-map.md`. **No se modifica** |
| `PUTAWAY_PRODUCT_OWNER` | Master 022 → `003-inventario-logistica` (`PutAwayPage`) | ídem. **No se modifica** |
| `OWNER_IDENTITY_CONFLICT` | **0** | |

## 4. Fallos históricos

| Fecha · ciclo | Corrida global | Cayeron | En solitario |
|---|---|---|---|
| 2026-09-30 · `EMPRESAS-SIN-SOBRE` (3 corridas) | 195/1/40 cada una | `treasury.spec.ts:486` · `route-crawl` (`/comercial/listas-precio` sin H1) · `inventory-confirmation` (`ECONNRESET`) · `putaway.spec.ts:405` — una vez cada una | pasan |
| 2026-10-01 · `AUDITORIA-PAGINACION-CLIENTE` | 199/1/40 | `putaway.spec.ts:187` — caduca en `waitForLoadState("networkidle")` | 3/3 |
| 2026-10-01 · `AUDIT-TOTAL-CARGA-TODO` | 196/4/40 | `picking.spec.ts:192`, `:208`, `:240` — caducan en `getByLabel("Almacén").selectOption(…)` · `putaway.spec.ts:187` | 1/1 cada una |
| 2026-10-01 · este ciclo, antes del arreglo | 196/4/40 | `picking.spec.ts:192`, `:208`, `:240` · `pick-execution.spec.ts:297` — el mismo `selectOption` | — |

Todos los de 2026-10-01 caducan a los 30,1 s esperando al desplegable «Almacén» o a que la
página termine de cargar. Ninguno falla una aserción de negocio.

## 5. Experimentos

`evidence/e2e-flaky/experimentos-pre-fix.txt`. Chromium; Playwright sin tocar:
`fullyParallel`, 6 trabajadores (la mitad de 12 núcleos), 30 s por prueba, 0 reintentos.

| Experimento | Corridas | Pasan | Fallan | La prueba verde más lenta |
|---|---|---|---|---|
| `picking.spec.ts` sola | 5 | 5 | 0 | 18–19 s |
| `putaway.spec.ts` sola | 5 | 5 | 0 | 15–16 s |
| Las dos juntas, 6 trabajadores | 5 | 5 | 0 | 21–22 s |
| Las dos juntas, **3** trabajadores | 2 | 2 | 0 | 11 s |
| Las dos juntas, **1** trabajador | 1 | 1 | 0 | **5,7 s** |
| Las dos + 5 suites que piden el listado (7 ficheros) | 4 | 4 | 0 | 23,8 → 24,4 → 26,3 → **26,9 s** |
| Las dos juntas, con 1 000 almacenes | 2 | 2 | 0 | 25 s |
| **Las dos juntas, con 1 434 almacenes** | **3** | **0** | **3** | `picking:192`, `:208`, `:240` a 30,1 s |
| Corrida global, 1 485 almacenes | 1 | — | 4 fallos | las tres de picking y `pick-execution:297` |

Lo que dicen:

- **La misma prueba tarda 5,7 s, 11 s y 21 s** con uno, tres y seis trabajadores: el tiempo
  es proporcional a la concurrencia. Las pruebas no se pisan los datos; compiten por el
  mismo servidor.
- **Cada corrida es más lenta que la anterior** (23,8 → 26,9 s) sin que cambie nada salvo
  los almacenes que las propias pruebas van dejando.
- **Dosis y respuesta**: 1 000 almacenes, 25 s y pasa; 1 434, caduca siempre. Es el
  reproductor mínimo: dos ficheros, `FAILURE_RATE` 3/3 frente a 0/5.
- `ORDER_DEPENDENCY`: ninguna. No hay orden que arreglar: cada prueba crea su almacén, su
  producto y su pedido con una marca propia.

### El coste, medido (`almacenes-listado-pre-fix.txt`)

| `GET /organization/warehouses` | Sentencias SQL | Sola | 3 a la vez | 6 a la vez |
|---|---|---|---|---|
| `limit=1` | 22 | 22 ms | | |
| `limit=50` | 610 | 172 ms | | |
| `limit=200` (una tanda de Picking) | 2 410 | 600 ms | 1,4 s | **2,9 s** |
| `limit=500` (Put-away, y cada prueba en su preparación) | 6 370 | 1,6 s | 3,8 s | **7,7 s** |

Picking carga el desplegable en tandas de 200 **una tras otra**: con 1 485 almacenes son 8
peticiones, y la opción del almacén recién creado no existe en la página hasta que termina
la última.

### Lo que se descartó, midiendo

| Hipótesis | Resultado |
|---|---|
| Datos compartidos, colisión de códigos, dependencia de orden | no: cada prueba usa datos propios con marca única; pasan en cualquier combinación mientras quepan en el tiempo |
| Selector ambiguo | no: se selecciona por el `id` del almacén propio |
| Sesión, cookies o empresa activa compartidas entre trabajadores | no: cada prueba abre su contexto e inicia sesión; el fallo no depende de quién más esté conectado sino de cuántos |
| Backend saturado en general | **no**: durante la corrida global, `/health/ready` contestó con mediana de 7 ms y máximo de 231 ms (`qa/e2e-latido.py`). Lo lento no es el servidor: es esa petición |
| Bloqueos en la base, errores 5xx, `ECONNRESET` | ninguno en las corridas de este ciclo |
| Residuos de PostgreSQL de la suite de backend | no: la base del E2E es `kaud`; `TEST-SCHEMAS-PG-SIN-LIMPIEZA` sigue cerrada |

## 6. Inventario de datos de las dos suites

| Objeto | Lo crea la prueba | Compartido | Se retira | Único |
|---|---|---|---|---|
| Usuario `admin`, tenant `DEMO`, empresa `D1` | no | **sí, sembrado** | — | — |
| Almacén (`WP-<marca>`, `W1-<marca>`) | sí | no | **nunca** | sí |
| Ubicaciones, producto, cliente, pedido, plan | sí | no | nunca | sí |
| «Otro almacén» para el caso de ubicación ajena | no: «uno que no sea el mío», del listado | sí, cualquiera | — | no hace falta |
| Tipo de movimiento `ENTRADA_RECEPCION` | el primero que llega | sí | — | por contrato (409 si ya existe) |

Crecimiento medido de la base del E2E (`kaud`): 170 almacenes creados el 2026-09-30 y 373
más el 2026-10-01 antes de este ciclo. Una corrida global añade unos 60.

## 7. Causa raíz

`app/modules/organization/warehouse_api.py`:

```python
"items": [_warehouse_dict(db, w, permissions) for w in rows]
```

y `_warehouse_dict` pregunta a la base, **almacén por almacén**: cuántos nodos hay de cada
uno de los cuatro tramos, cuántas ubicaciones, cuántos movimientos —para `can_delete`—, lo
mismo otra vez para `structure_regime`, y **todo de nuevo** dentro de
`warehouse_allowed_actions`, que vuelve a calcular el régimen y `can_delete`.

| Clasificación | |
|---|---|
| `PRODUCT_DEFECT` (rendimiento, N+1) | **sí** — `GET /organization/warehouses`, SPEC008 |
| `E2E_TEST_DEFECT` (datos que se acumulan) | **sí** — lo que convierte un coste moderado en una caducidad; se registra, §19 |
| `E2E_HARNESS_DEFECT` | no |
| `E2E_TEST_INFRA_CAPACITY_DEFECT` | no: el servidor no está saturado |
| `PRODUCT_CONCURRENCY_DEFECT` (carrera) | no: ninguna respuesta incorrecta; solo lenta |
| `UNKNOWN` | 0 para Picking, Put-away y Pick-execution |

Una empresa real no tiene 1 400 almacenes; con 50, el listado son 610 sentencias y 170 ms.
Por eso nadie lo había visto fuera de la base de QA. Pero el defecto es del endpoint.

`treasury.spec.ts:486`, `route-crawl`, `inventory-confirmation` y `putaway.spec.ts:405`
—una caída cada una el 2026-09-30, con unos 170 almacenes— **no quedan explicadas** por
esta causa y no se han vuelto a ver en las cinco corridas globales posteriores. No se les
atribuye lo que no se ha demostrado (§19).

## 8. `/speckit.specify`

| ID | Requisito |
|---|---|
| FR-054-E2EFLK-001 | Las pruebas de Picking, Pick-execution y Put-away dan el mismo resultado solas y dentro de una ejecución concurrente válida |
| FR-054-E2EFLK-002 | El coste de `GET /organization/warehouses` en sentencias SQL no depende del número de almacenes de la página |
| FR-054-E2EFLK-003 | La respuesta del listado no cambia: los mismos campos y los mismos valores, almacén por almacén, que `GET /organization/warehouses/{id}` |
| FR-054-E2EFLK-004 | `can_delete`, `delete_blocked_by`, `structure_regime` y `allowed_actions` siguen reflejando los permisos del usuario y el estado de cada almacén |
| FR-054-E2EFLK-005 | El alcance por empresa del listado no cambia |
| FR-054-E2EFLK-006 | No se añaden reintentos, esperas, omisiones ni serialización; no se reducen trabajadores ni se amplían tiempos |
| FR-054-E2EFLK-007 | Existe un reproductor reducido del fallo anterior al arreglo |
| FR-054-E2EFLK-008 | El reproductor queda verde de forma repetida tras el arreglo, **con la misma cantidad de datos** |
| FR-054-E2EFLK-009 | La corrida global posterior no tiene fallos atribuibles a esta deuda |
| FR-054-E2EFLK-010 | Cualquier otro fallo global se clasifica por evidencia |
| FR-054-E2EFLK-011 | El paralelismo de Playwright se conserva |
| FR-054-E2EFLK-012 | `TEST-SCHEMAS-PG-SIN-LIMPIEZA` sigue cerrada |
| FR-054-E2EFLK-013 | Esquema, migraciones, índices y frontend: 0 |
| FR-054-E2EFLK-014 | Un fallo real sigue fallando: no se ablanda ninguna aserción |

## 9. `/speckit.clarify` y ampliación de alcance

**Ampliación de alcance, antes de implementar.** El encargo permite corregir producto «solo
si la causa raíz demuestra un defecto de producto y el alcance y la dueña ya se
actualizaron». Se cumple: `PRODUCT CHANGE` pasa de `UNKNOWN` a **backend, SPEC008,
`GET /organization/warehouses`, solo rendimiento**. Sin decisión material: el contrato del
endpoint no cambia.

| # | Pregunta | Respuesta, medida |
|---|---|---|
| 1 | Dueña | SPEC054; producto, SPEC008 |
| 2–3 | Pruebas y aserciones exactas | §4 |
| 4–8 | Sola, en pareja, trabajadores, orden | §5 |
| 9 | Reproductor mínimo | dos ficheros con 1 434 almacenes: 3/3 fallos |
| 10–11 | Datos propios y semilla compartida | §6 |
| 12–14 | Usuario, empresa y sesión compartidos | usuario y empresa, sí; no influyen en el resultado |
| 15–17 | Selectores, conteos globales, identificadores fijos | sin defecto |
| 18 | Limpieza | no existe: las pruebas no retiran lo que crean |
| 19–21 | Backend, frontend y base durante el fallo | la página espera la última tanda del listado; el backend responde bien y tarde; la base, sin bloqueos |
| 22–24 | Presión, red, bloqueos | §5: el servidor contesta lo trivial en 7 ms |
| 25–28 | ¿Carrera de producto? ¿Prueba? ¿Arnés? ¿Capacidad? | no · datos acumulados, sí · no · no. Y rendimiento de producto, sí |
| 29 | Cambio de producto | `structure.py` y `warehouse_api.py`: el listado obtiene las dependencias de toda la página con una consulta agrupada por tabla |
| 30 | Esquema y migraciones | 0 |
| 31–33 | Pruebas, mutaciones, certificación global | §12 |
| 34 | Clasificación | §13 |

Diseño: las seis cuentas que hoy se hacen por almacén —zonas, pasillos, estanterías,
niveles, ubicaciones y movimientos— se hacen una vez por tabla para todos los almacenes de
la página (`… WHERE warehouse_id IN (…) GROUP BY warehouse_id`). De esas cuentas salen
`can_delete`, `delete_blocked_by`, `structure_regime` y `allowed_actions` con las mismas
reglas. El camino por almacén (`GET /warehouses/{id}`, altas, ediciones) **no se toca**, y
sirve de oráculo: el listado tiene que decir exactamente lo mismo.

Lo que no se hace, y por qué:

- **No se cambian las pantallas.** Con el listado a coste fijo, cargar el desplegable deja
  de ser un problema. Que Put-away corte en 500 por orden de código es una limitación
  escrita en su propio código; se registra (§19).
- **No se limpia la base de QA ni se toca cómo siembran las pruebas.** Es la otra mitad de
  la causa, pero arreglarla es rediseñar el aislamiento de datos de 35 suites. Se registra.
- **No se sube el tiempo, no se serializa, no se quitan trabajadores.**

`MATERIAL OQ = 0`. `UNKNOWN = 0` para el objetivo.

## 10. Compuerta constitucional

| | | |
|---|---|---|
| G01–G03 checkpoint, orquestación, dueña | §1, §3 | ✅ |
| G04 fallos históricos recuperados | §4 | ✅ |
| G05–G09 sola, pareja, trabajadores, orden | §5 | ✅ |
| G10–G12 datos, selectores, sesión | §5, §6 | ✅ |
| G13–G14 presión y red | §5 | ✅ |
| G15 reproductor mínimo | 3/3 | ✅ |
| G16–G17 causa y propiedad producto/prueba/arnés | §7 | ✅ |
| G18–G20 sin reintentos, esperas ni serialización | §9 | ✅ |
| G21–G23 arreglo, pruebas, mutaciones | §9, §12 | ✅ |
| G24–G25 cambio de producto y esquema conocidos | backend SPEC008 · 0 | ✅ |
| G26–G28 `MATERIAL OQ`, `UNKNOWN`, trazabilidad | 0 · 0 · 100 % | ✅ |

Principios: 6 (seguridad en backend: permisos y alcance del listado intactos), 10, 21
(evidencia en PostgreSQL), 22, 27. **PASS.**

## 11. `/speckit.plan`

W01–W20 hechos (§1–§9). W21 implementación: `structure.warehouses_dependencies` y el
cálculo por página en `warehouse_api`. W22 pruebas de paridad y de coste. W23 —pruebas
hostiles de concurrencia— no aplica: no hay carrera. W24 reproductor repetido, con la misma
dosis. W25 mutaciones. W26 matriz de navegadores: no aplica, el cambio es de backend. W27
dos corridas globales. W28–W31 atribución, `analyze`, trazabilidad, convergencia.

## 12. Pruebas y mutaciones, diseñadas antes de implementar

Backend, `tests/test_warehouse_list_cost.py` (SQLite y PostgreSQL):

| ID | Caso | Req. |
|---|---|---|
| WHL-01 | paridad: para almacenes en todos los estados —vacío, con cada tramo, con ubicación, con movimientos, inactivo, operativo, con y sin tramos declarados—, cada item del listado es **igual** a `GET /warehouses/{id}` | 003, 004 |
| WHL-02 | paridad con un usuario que solo tiene `organization:view`: `allowed_actions` recortadas igual | 004 |
| WHL-03 | coste: el listado de 3 almacenes y el de 40 ejecutan el **mismo número** de sentencias | 002 |
| WHL-04 | coste absoluto: una página no ejecuta más de una sentencia por tabla de dependencias | 002 |
| WHL-05 | alcance: el listado de una empresa no trae almacenes de otra, ni sus cuentas | 005 |
| WHL-06 | página vacía: sin almacenes no hay consulta `IN ()` ni error | 002 |
| WHL-07 | `total`, `limit`, `offset` y el orden por código no cambian | 003 |

Unitarias de la función pura que deriva la vista de un almacén a partir de sus cuentas
(T10, delegable): estados × régimen × tramos declarados × permisos.

| Mutante | Cambio | Debe matarlo |
|---|---|---|
| M-01 | volver a `_warehouse_dict` por almacén | WHL-03, 04 |
| M-02 | las cuentas no filtran por los almacenes de la página | WHL-01, 05 |
| M-03 | se omiten los movimientos al decidir `can_delete` | WHL-01 |
| M-04 | se omiten las ubicaciones al decidir el régimen | WHL-01 |
| M-05 | `allowed_actions` sin recortar por permisos | WHL-02 |
| M-06 | «delete» se ofrece aunque haya dependencias | WHL-01 |
| M-07 | un tramo usado no bloquea | WHL-01 |
| M-08 | el régimen guardado `OPERATIONAL` se ignora | WHL-01, unitarias |

E2E: ninguna prueba nueva. Las que existen son la certificación: el reproductor a la misma
dosis, cada suite sola, la pareja, y dos corridas globales. Ninguna se ablanda.

## 13. `/speckit.tasks` y `/speckit.analyze` previo

| ID | Tarea | Req. | EXECUTOR · MODEL | SEC | EGRESS | Ficheros |
|---|---|---|---|---|---|---|
| T01 | Reconciliación, dueñas, evidencia histórica | — | CLAUDE | NO | n-a | — |
| T02 | Experimentos y reproductor | 007 | CLAUDE | NO | n-a | `qa/repro-almacenes-listado.py`, `qa/e2e-latido.py` |
| T03 | Causa raíz, clasificación, diseño, casos y mutantes | todos | CLAUDE | YES | n-a | este documento |
| T04 | Cuentas agrupadas y vista por página | 002–005 | CLAUDE | YES | n-a | `app/modules/organization/structure.py`, `warehouse_api.py` |
| T05 | Paridad y coste contra la API | 002–005 | CLAUDE | YES | n-a | `tests/test_warehouse_list_cost.py` |
| T10 | Unitarias de la función pura de la vista | 004 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `tests/test_warehouse_view_pure.py` (nuevo) |
| T20 | Auditar, aplicar y probar T10 | — | CLAUDE | NO | n-a | — |
| T21 | Mutaciones | 002–005 | CLAUDE | YES | n-a | — |
| T22 | Reproductor a la misma dosis, solas, pareja | 001, 008 | CLAUDE | NO | n-a | — |
| T23 | Backend dirigido y completo, SQLite y PostgreSQL | 012 | CLAUDE | NO | n-a | — |
| T24 | Dos corridas globales E2E y atribución | 009, 010 | CLAUDE | NO | n-a | — |
| T25 | `analyze` final, trazabilidad, convergencia, hoja de ruta, Git | — | CLAUDE | NO | n-a | documentos |

`RETRY_MAX: 2` en T10. T04 es de Claude: toca lo que decide qué acciones se ofrecen a cada
usuario —permisos— y el alcance por empresa del listado. T05 también: su mundo de prueba
lleva la contraseña de la siembra. T10 es una función pura, sin base ni credenciales.

`analyze` previo: `BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` = 0;
requisitos y tareas huérfanas = 0; `MATERIAL OQ` = 0; `UNKNOWN` = 0; trazabilidad 100 %.

**Autorización de `implement`:** la del encargo `E2E-FLAKY-BAJO-CARGA`, con el alcance de
producto ampliado en §9.

## 14. Segunda ampliación de alcance, antes de tocar ninguna prueba

Al revisar la evidencia original de los cuatro fallos del 2026-09-30 (§4, §7), dos resultaron
no ser de carga sino **carreras escritas en la propia prueba**. Se reprodujeron antes de
decidir nada (`evidence/e2e-flaky/carreras-de-prueba.txt`):

| Fallo histórico | Lo que decía el error | Causa, demostrada | Reproducción |
|---|---|---|---|
| `putaway.spec.ts:405` «ubicar no crea nada de picking» | `ubicar creó una lista de preparación` | la prueba compara el **número de listas de preparación de toda la empresa** antes y después de ubicar. `GET /sales/pick-lists` devuelve todas, sin paginar, y otras siete suites (`picking`, `pick-execution`, `dispatch`, `billing`, `returns`, `receivables`, `order-confirmation`) crean las suyas en la misma empresa a la vez | la prueba repetida 12 veces junto a `picking` y `pick-execution`, **con el backend ya arreglado**: 1 caída, `Expected: 1189 · Received: 1190` |
| `treasury.spec.ts:486` «FLOAT-038-B · la interfaz de cajas…» | `expect(received).toEqual(expected)` a los 3,2 s | tras pulsar «Cerrar caja» la prueba espera a que la fila contenga `CLOSED`; la fila ya dice `PRE_CLOSED`, que **contiene** ese texto, así que no espera nada y lee la sesión antes de que el cierre termine | con la respuesta del cierre retrasada 1,5 s en una copia temporal de la prueba: **3 de 3**, `Expected "CLOSED" · Received "PRE_CLOSED"` |

Clasificación: `E2E_TEST_DEFECT` las dos. Ninguna es defecto de producto: ubicar no crea
listas y la caja se cierra bien. No dependen del listado de almacenes; la lentitud solo
ensanchaba la ventana.

**Alcance ampliado:** dos aserciones, en `e2e/putaway.spec.ts` y `e2e/treasury.spec.ts`.
Producto: 0. Tiempos, reintentos, esperas fijas, serialización, trabajadores: 0.

| ID | Requisito |
|---|---|
| FR-054-E2EFLK-015 | «ubicar no crea nada de picking» comprueba las listas de preparación **del almacén de su escenario**, no el total de la empresa; sigue fallando si aparece una en ese almacén |
| FR-054-E2EFLK-016 | El cierre de caja por la interfaz espera a que la fila diga `CLOSED` **sin** ser `PRE_CLOSED`; sigue fallando si la caja no llega a cerrarse |

| ID | Tarea | Req. | EXECUTOR · MODEL | SEC | EGRESS | Ficheros |
|---|---|---|---|---|---|---|
| T11 | Aserción sobre datos propios en `putaway.spec.ts:405` | 015 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `resources/frontend/e2e/putaway.spec.ts` |
| T12 | Espera exacta del estado en `treasury.spec.ts:486` | 016 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `resources/frontend/e2e/treasury.spec.ts` |
| T13 | Auditar, aplicar; reproducir de nuevo; comprobar que un fallo real sigue fallando | 014–016 | CLAUDE | NO | n-a | — |

T11 y T12 son delegables: la causa ya está decidida, el cambio es local, el contrato es la
aserción exacta, y el encargo lleva solo el fragmento de la prueba —sin contraseña de
siembra ni direcciones—. `RETRY_MAX: 2`.

Pruebas de T13: (a) `putaway:405` repetida junto a las suites que crean listas: 0 caídas;
(b) el reproductor del retraso de 1,5 s en el cierre: pasa; (c) mutantes de prueba, en
copia temporal: una lista creada en el almacén propio hace caer `putaway:405`, y un cierre
que nunca llega hace caer `treasury:486`.

`route-crawl` (`/comercial/listas-precio` sin H1) e `inventory-confirmation` (`ECONNRESET`)
siguen **sin causa demostrada**: no se tocan (§19).

`analyze` de la ampliación: `BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` = 0;
`MATERIAL OQ` = 0; trazabilidad 100 %. Autorización: la del encargo, que pide corregir los
defectos de prueba demostrados.

## 15. Implementación

```
T04  [ANALYZE]  can_delete, delete_blocked_by, structure_regime y allowed_actions salen de seis cuentas por almacén; el detalle (GET /warehouses/{id}) no se toca y es el oráculo
     [PLAN]     structure.warehouses_dependencies (una consulta agrupada por tabla para toda la página) + structure.warehouse_view (función pura); el listado las usa
     [CLASSIFY] CLAUDE_ONLY — decide qué acciones se ofrecen a cada usuario y el alcance por empresa
     [EXECUTE]  Claude
     [AUDIT]    n-a
     [TEST]     tests/test_warehouse_structure.py — 33 passed, 1 skipped (SQLite); ruff limpio; mypy sin líneas nuevas
     [STATUS]   COMPLETE

T05  [ANALYZE]  paridad listado ↔ detalle en 13 estados de almacén, dos usuarios con permisos recortados, otra empresa; coste en sentencias
     [PLAN]     tests/test_warehouse_list_cost.py — WHL-01..07, 14 pruebas
     [CLASSIFY] CLAUDE_ONLY — el mundo de prueba lleva la contraseña de siembra
     [EXECUTE]  Claude
     [AUDIT]    n-a
     [TEST]     14 passed en SQLite y en PostgreSQL
     [STATUS]   COMPLETE

T10  [ANALYZE]  función pura, contrato cerrado, sin base ni credenciales
     [PLAN]     tests/test_warehouse_view_pure.py — WHV-01..15
     [CLASSIFY] DEEPSEEK_ELIGIBLE
     [EXECUTE]  DeepSeek deepseek-v4-flash (3668/2747 tokens, $0.001265)
     [AUDIT]    PASS
     [TEST]     53 passed en SQLite y en PostgreSQL
     [STATUS]   COMPLETE

T11  [ANALYZE]  la aserción compara el total de listas de preparación de la empresa; reproducida la carrera (1 de 12)
     [PLAN]     la prueba mira las listas del almacén de su escenario
     [CLASSIFY] DEEPSEEK_ELIGIBLE
     [EXECUTE]  DeepSeek deepseek-v4-flash (1464/874 tokens, $0.000432)
     [AUDIT]    PASS
     [TEST]     putaway:405 ×24 junto a picking y pick-execution — 384 passed; mutante de prueba (lista en el almacén propio) — cae
     [STATUS]   COMPLETE

T12  [ANALYZE]  `toContainText("CLOSED")` se cumple con `PRE_CLOSED`; reproducida la carrera (3 de 3 con el cierre retrasado)
     [PLAN]     esperar `CLOSED` que no sea parte de `PRE_CLOSED`; mismo tiempo de espera
     [CLASSIFY] DEEPSEEK_ELIGIBLE
     [EXECUTE]  DeepSeek deepseek-v4-flash (1016/442 tokens, $0.000248)
     [AUDIT]    PASS
     [TEST]     con el cierre retrasado 1,5 s — 3 passed; mutante de prueba (el cierre no llega) — cae; original ×5 — 5 passed
     [STATUS]   COMPLETE
```

Ficheros de producto: `app/modules/organization/structure.py` y `warehouse_api.py`. Pruebas
E2E: `e2e/putaway.spec.ts` y `e2e/treasury.spec.ts`, una aserción cada una. Frontend
(`src/`), esquema, migraciones, índices, configuración de Playwright: **0**.

## 16. Mutaciones

`evidence/e2e-flaky/mutaciones.txt`. **16 mutantes, 16 muertos**, ninguno vivo; el código
restaurado es idéntico byte a byte. Los ocho planificados (M-01..M-08, con M-02 en dos
variantes) y siete añadidos al ver el código: copia del diccionario, página vacía, permisos
ignorados en el listado, cuentas aplastadas a 1, movimientos que no bloquean, activar y
desactivar intercambiados, tramos declarados sin alta. `M-02b` —las cuentas dejan de filtrar
por la página pero no rompen nada visible— solo la mata WHL-05, que mira los parámetros de
la consulta.

Mutantes de las dos pruebas E2E corregidas, en copias temporales ya borradas
(`carreras-de-prueba.txt`): con una lista de preparación en el almacén propio,
`putaway:405` cae; con un cierre que nunca llega, `treasury:486` cae a los 20 s leyendo
`PRE_CLOSED`. Las dos siguen pudiendo fallar.

## 17. Resultados

### El listado, medido igual que antes (`almacenes-listado-post-fix.txt`)

| `GET /organization/warehouses` | Sentencias: antes → después | Sola | 6 a la vez |
|---|---|---|---|
| `limit=1` | 22 → **16** | 22 → 18 ms | |
| `limit=50` | 610 → **16** | 172 → 16 ms | |
| `limit=200` | 2 410 → **16** | 600 → 27 ms | 2,9 s → **0,13 s** |
| `limit=500` | 6 370 → **16** | 1 606 → 52 ms | 7,7 s → **0,26 s** |

Las 16 son fijas: sesión, permisos, total, página y seis cuentas.

### Las pruebas que caducaban, con más almacenes que cuando caducaban (`experimentos-post-fix.txt`)

| Experimento | Almacenes | Antes | Después |
|---|---|---|---|
| Picking + Put-away juntas | 1 434 → 1 570 | **0 de 3**, a 30,1 s | **5 de 5**, la más lenta 5,2 s |
| Reproductor de 7 suites | menos de 1 000 → 1 826 | 4 de 4, 24–27 s y subiendo | 3 de 3, 7–8 s |
| `picking` sola | | 18–19 s | 4,6–5,0 s |
| `putaway` sola | | 15–16 s | 2,6–2,9 s |
| `pick-execution` sola | | — | 1,8–1,9 s |

### Corridas globales (Chromium, 240 pruebas, 6 trabajadores, 30 s, 0 reintentos)

| Corrida | Árbol | Resultado | Fallo | Latido del backend (máx.) |
|---|---|---|---|---|
| Antes del arreglo | `42cd793` | 196/4/40 | `picking:192`, `:208`, `:240`, `pick-execution:297` | 231 ms |
| 1 | arreglo del listado | **199/1/40** | `empresas-busqueda:58` — login en blanco 30 s | 206 ms |
| 2 | ídem | **200/0/40** | — | 243 ms |
| 3 | ídem, con traza | **200/0/40** | — | 437 ms |
| 4 y 5 | + T11, T12 | 194/6/40 · 193/7/40 | **inválidas**: corrieron a la vez que mi experimento de keep-alive, que agotó el pool del backend (§18) | 30 s |
| Final | + T11, T12, backend reiniciado, nada más en marcha | **193/1/40** + 6 sin correr | `notifications:142` — un tick del planificador de 33 s (§18) | 399 ms |

Los fallos que originaron la deuda en Picking, Pick-execution y Put-away no han vuelto en
ninguna corrida válida. **La corrida final no está en verde**, y la causa es otra cuenta
que sube con la base.

### Backend (`backend.txt`)

SQLite: 857 pasan · 968 omitidas · 43 fallan. PostgreSQL: 1 804 · 27 · 37. En las dos, el
conjunto de fallos es el de `42cd793` —documentos, por falta de `clamscan`— y hay 67
pruebas nuevas en verde. Tras la corrida en PostgreSQL: 0 schemas temporales, 0 conexiones.
`TEST-SCHEMAS-PG-SIN-LIMPIEZA` sigue cerrada.

## 18. Cada fallo, con su causa

| Fallo | Cuándo | Causa | Evidencia | Estado |
|---|---|---|---|---|
| `picking:192`, `:208`, `:240` · `pick-execution:297` · `putaway:187` (caducidad) | 2026-10-01, cuatro corridas | N+1 del listado de almacenes × almacenes que la base acumula | dosis-respuesta 0/3 → 5/5 | **explicado y corregido** (producto) |
| `putaway:405` | 2026-09-30 | la prueba cuenta las listas de preparación de toda la empresa mientras otras siete suites crean las suyas | 1 de 12 → 0 de 24 | **explicado y corregido** (prueba) |
| `treasury:486` | 2026-09-30 | la prueba espera `CLOSED`, que ya está dentro de `PRE_CLOSED` | 3 de 3 con el cierre retrasado → 3 de 3 verdes | **explicado y corregido** (prueba) |
| `inventory-confirmation:96` — `ECONNRESET` | 2026-09-30 (y dos veces antes, en la Spec 013 y en la matriz de `AUDITORIA-PAGINACION`) | uvicorn cierra una conexión inactiva a los 5 s; el cliente de API de Playwright la conserva esos mismos 5 s. Una petición que sale en ese instante recibe `ECONNRESET` o se queda sin respuesta hasta caducar | `keepalive.txt`: 15 de 80 alrededor de los 5 s, y una ventana de ~10 ms con 40 de 40 colgadas; con `--timeout-keep-alive 60`, **0 de 160** | **explicado, no corregido**: el arreglo es cómo se arranca el backend (§19) |
| `notifications:142` | 2026-10-01, corrida final | la prueba llama al planificador dentro de sus 30 s; el primer tick de cada corrida ha pasado de 0,3 s a 33 s en trece corridas, porque cada corrida deja dos reglas activas y sus usuarios, y cada hecho nuevo se reparte entre todas: ese tick escribió 132 977 destinatarios | `planificador-acumulacion.txt`, traza de la prueba | **explicado, no corregido** (§19) |
| `putaway:187` — «did not find some options» | 2026-10-01, corridas 4 y 5 y sola 2 de 2 | `PutAwayPage` pide los primeros 500 almacenes por código; mis experimentos crearon 418 `W1-…` en dos horas y el de la prueba cayó en la posición 539 | `putaway-corte-500.txt`: 2 de 2 caídas → renombrados los de los experimentos → 2 de 2 verdes | **explicado**; inducido por este ciclo, y a ritmo normal a unas 40 corridas de distancia (§19) |
| Seis pruebas a la vez a los 30 s, dos veces | 2026-10-01, corridas 4 y 5 | **mi experimento**: 40 conexiones colgadas agotaron el pool (5 + 10) y `LicenseMiddleware` esperó conexión dentro del bucle de eventos, 30 s | 16 `QueuePool limit … timeout 30.00` en el registro; latido de 30 s; 0 en todas las demás corridas | artefacto del ciclo; el mecanismo queda registrado (§19) |
| `route-crawl` — `/comercial/listas-precio` sin H1 | 2026-09-30 | **no demostrada** | no se ha repetido en 7 corridas globales | abierto (§19) |
| `empresas-busqueda:58` — login en blanco 30 s | 2026-10-01, corrida 1 | **no demostrada**. El backend respondía (latido ≤ 206 ms); la pantalla de login no pide almacenes | 0 de 5 la suite sola; 0 de 800 cargas del login con 6 trabajadores | abierto (§19) |

Clasificación final: `PRODUCT_DEFECT` (N+1, corregido) · `E2E_TEST_DEFECT` (dos carreras,
corregidas; datos que se acumulan, **abierto**) · `E2E_HARNESS_DEFECT` (keep-alive,
**abierto**) · `UNKNOWN` = 2 fallos de pantalla sin pintar.

## 19. Lo que queda registrado y no absorbido

| Deuda | Qué | Por qué no se cierra aquí |
|---|---|---|
| **`E2E-BASE-QA-ACUMULA`** | la base del E2E no se reinicia nunca y las pruebas no retiran lo que crean. Tres caminos medidos en este ciclo crecen con ella hasta romper una prueba: el listado de almacenes (corregido), el corte en 500 de Put-away y el reparto de notificaciones | **`MATERIAL_DECISION_REQUIRED`**: base nueva por corrida, tenant por corrida o limpieza por prueba es una decisión de diseño del arnés, y dos de las tres opciones son destructivas sobre la base de QA |
| **`E2E-NOTIFICACIONES-REGLAS-VIVAS`** | `notifications.spec.ts` crea dos reglas activas por corrida y no las desactiva; con 28 reglas y 868 usuarios el tick tarda 27–33 s y `notifications:142` cae en la corrida global | es la cara más urgente de la anterior: **hoy deja la corrida global en rojo**. Limpiar solo las reglas aplaza el problema —los usuarios siguen creciendo— y no lo decide este delta |
| **`ALMACENES-DESPLEGABLES-TRUNCADOS`** | `PutAwayPage` pide 500 almacenes; otras ocho pantallas, el límite por defecto, 50. El almacén que no entra no se puede elegir | producto, nueve pantallas: transversal. Arreglar solo Put-away sería un parche |
| **`BACKEND-KEEPALIVE-5S`** | uvicorn con su valor por defecto cierra a los 5 s; reproduce `ECONNRESET` y cuelgues con el cliente de Node | el arranque del backend vive en `Dockerfile.backend` (producción y desarrollo): cambiarlo es una decisión de despliegue |
| **`LICENCIA-MIDDLEWARE-BD-EN-EL-BUCLE`** | `LicenseMiddleware.dispatch` consulta la base en el bucle de eventos en cada escritura; con el pool agotado, el backend entero se detiene 30 s | observado solo bajo mi experimento; producto, dueña 004 |
| **`PICKLIST-DUPLICADA-500`** | `POST /sales/pick-lists` para un pedido que ya tiene una lista activa responde 500 (`uq_pick_lists_active_order` sin capturar), no 409 | producto, dueña 031; lo encontró un mutante de prueba |
| **`E2E-PANTALLA-SIN-PINTAR`** | dos fallos puntuales, uno por fecha, en los que la página no llega a pintarse y el backend está sano | sin causa demostrada; no se inventa una |
| **`LISTADOS-SIN-TOPE`** | `GET /organization/warehouses` acepta cualquier `limit`; `GET /sales/pick-lists` devuelve todas las listas de la empresa, sin paginar | observación |

Higiene de la base de QA hecha en este ciclo, toda sobre filas creadas por él: retirados
los 400 almacenes sintéticos `ZZFLK-…`; renombrados a `ZX-W1-…` los 418 `W1-…` de los
experimentos. Nada más se ha tocado: no se ha reiniciado la base ni desactivado ninguna
regla.

## 20. Veredicto final

`E2E-FLAKY-BAJO-CARGA` **no se cierra.** Se cierra lo que se demostró y se corrigió:

- la causa de las caducidades de Picking, Pick-execution y Put-away —el N+1 del listado de
  almacenes—, en producto, con el contrato intacto;
- dos carreras escritas en las pruebas, `putaway:405` y `treasury:486`.

Queda abierto, con causa demostrada y sin corregir porque el arreglo no es de este delta:
el `ECONNRESET` del keep-alive y el reparto de notificaciones que hoy tumba
`notifications:142`. Y quedan dos fallos de pantalla sin pintar sin causa.

La deuda decía que «la inestabilidad crece con la base de QA». Era literal: no hay un
defecto, hay una base que crece sin límite y varios caminos —de producto y de prueba— cuyo
coste o cuyo corte dependen de su tamaño. Se ha corregido el que rompía hoy; el siguiente
ya ha roto. Mientras la base del E2E no tenga ciclo de vida, la lista seguirá.

**Decisión que se pide a la dueña** (`E2E-BASE-QA-ACUMULA`): cómo se aísla o se renueva la
base del E2E. Es lo que cierra de verdad esta deuda.

| | |
|---|---|
| `STATUS` | **`PARTIALLY_CONVERGED`** — la deuda sigue `OPEN`, reducida y redefinida |
| Fallos originales explicados | 7 de 8 (todos menos `route-crawl`) |
| Fallos originales explicados **y corregidos** | 6 de 8 |
| Corrida global final | 193 / 1 / 40 + 6 sin correr — **no verde** |
| Reintentos, esperas fijas, serialización, menos trabajadores, más tiempo | 0 |
| Esquema, migraciones, índices, `src/` del frontend | 0 |

## 21. `analyze` final, trazabilidad y convergencia

| Requisito | Prueba o evidencia | Estado |
|---|---|---|
| 001 mismas pruebas solas y en concurrencia | par 5/5, reproductor 3/3, corridas 2, 3 y final | ✅ para Picking, Pick-execution y Put-away |
| 002 coste independiente del número de almacenes | WHL-03, WHL-04, WHL-06; 16 sentencias | ✅ |
| 003 respuesta idéntica al detalle | WHL-01, WHL-07 | ✅ |
| 004 permisos y estado | WHL-02, WHV-01..15 | ✅ |
| 005 alcance por empresa | WHL-05 | ✅ |
| 006 sin reintentos, esperas ni serialización | diff | ✅ |
| 007 reproductor previo | 0 de 3 con 1 434 almacenes | ✅ |
| 008 reproductor verde a la misma dosis | 5 de 5 con 1 570 | ✅ |
| 009 corrida global sin fallos de esta deuda | los de almacenes, ninguno; **`notifications:142` es de la misma familia** | ⚠️ **no cumplido** |
| 010 todo fallo clasificado por evidencia | §18; dos sin causa, dichos | ✅ |
| 011 paralelismo conservado | `playwright.config.ts` sin cambios | ✅ |
| 012 `TEST-SCHEMAS-PG-SIN-LIMPIEZA` cerrada | 0 schemas, 0 conexiones | ✅ |
| 013 esquema, migraciones, índices, frontend | 0 | ✅ |
| 014 un fallo real sigue fallando | 16 mutantes; dos mutantes de prueba | ✅ |
| 015 `putaway:405` sobre datos propios | 0 de 24; mutante cae | ✅ |
| 016 cierre de caja con espera exacta | 3 de 3 con retraso; mutante cae | ✅ |

`BLOCKER` = 0 para lo implementado · `MATERIAL OQ` = **1**, nueva y escalada
(`E2E-BASE-QA-ACUMULA`) · `UNKNOWN` = 2 fallos, registrados · requisitos huérfanos = 0 ·
FR-009 no cumplido, y por eso la deuda no se cierra.

Desviaciones mías, dichas: las corridas globales 4 y 5 no valen porque lancé un experimento
contra el mismo backend mientras corrían; los experimentos de este ciclo empujaron la base
de QA por encima del corte de Put-away y hubo que renombrar sus almacenes; una corrida de
PostgreSQL se lanzó con `-p no:logging` y cambió la etiqueta —no el conjunto— de un fallo.

Orquestación (`orquestacion.txt`): 15 tareas · 12 `CLAUDE_ONLY` · 3 `DEEPSEEK_ELIGIBLE`,
las tres ejecutadas por DeepSeek (`deepseek-v4-flash`) · 3 llamadas · 0 reintentos · 3
parches aceptados, 0 rechazados, 0 retocados · 6 148 / 4 063 tokens · $0,001945 · puente:
77 135 tokens. Investigación, causa raíz, diseño, T04 y T05, auditoría, mutaciones y
certificación: Claude.

---

# PARTE II — `E2E-BASE-QA-ACUMULA`: una base nueva por corrida, y reconvergencia

**Fecha** 2026-10-01 · **Dueña** SPEC054 (`specs/012-auditoria-integral-e2e`) · **Apoyo de
ciclo de vida de base** Master 052 → `001-fundacion` (las migraciones canónicas, sin
cambios) · **Base** `c94eed4` · **Rama** `develop`

## 22. Checkpoint y decisión

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` | `c94eed4` / **`c94eed4`** / `c94eed4` |
| `ACTUAL_BRANCH` · `WORKTREE_STATE` · `COMMITS_AFTER_C94EED4` | `develop` · limpio · 0 |
| `ORCHESTRATION_STATUS` | `VERIFIED_END_TO_END`; `orchestration_readiness.py` 11/11 |
| `DEEPSEEK_TOOL` · `MODEL_ROUTING` · `RETRY_MAX` | `mcp__deepseek__deepseek_chat` · `deepseek-v4-flash` · 2 |
| `PRIMARY_OWNER` | **SPEC054** — `specs/012-auditoria-integral-e2e` |
| `DB_LIFECYCLE_SUPPORT` | Master 052 → `001-fundacion`: `alembic upgrade head`, sin tocar |
| `PRODUCT_SUPPORTS` | ninguno previsto; si la reconvergencia destapa un defecto de producto, se amplía antes de implementar |
| `OWNER_IDENTITY_CONFLICT` | **0** |

**Decisión de la dueña, ya tomada:** `E2E-BASE-QA-ACUMULA = FRESH_DATABASE_PER_E2E_RUN`.
Cada corrida E2E certificable corre contra una base PostgreSQL nueva, creada para ella y
eliminada al terminar. `kaud` queda para QA manual y deja de ser la base de certificación.
`TENANT_PER_RUN` y `CLEANUP_PER_TEST` quedan rechazados como mecanismo primario. Dentro de
la base de la corrida, cada prueba sigue obligada a usar datos propios.

Es además lo que la Constitución ya pedía: PostgreSQL recién creado, de cero a la cabeza de
migraciones, semilla mínima y E2E (P21, P24).

## 23. Lo que hay hoy (W05–W08)

| | Hoy | Evidencia |
|---|---|---|
| Lanzador | **no existe**. El backend (`uvicorn`), Vite y Playwright se arrancan a mano, cada uno con sus variables | `Dockerfile.backend` es el único sitio del repositorio que arranca uvicorn |
| Base del E2E | `kaud`, creada una vez con `qa/pg-provision.sh mkdb` y nunca renovada: 828 MB | `pg_database` |
| Siembra | `qa/e2e-seed.sh <url>` → `pg-e2e-seed.py` (instalación, tenant DEMO, D1, `admin`, licencia), `spec047-e2e-seed.py` (D2), `n6-e2e-seed.py` (DEMO2/E1, `ua`/`ub`/`uab`/`uc`, fichero de ids). Idempotente. La invoca `e2e/global-setup.ts` si hay `KONTROL_E2E_DB_URL` | los tres guiones |
| Migraciones | `alembic upgrade head` con `KONTROL_DB_URL`; **un** head, `0057_spec047_notifications` | `alembic heads` |
| Planificador | no es un proceso: `helpers/planificador.ts` ejecuta `python -m app.modules.scheduler tick` contra `KONTROL_E2E_DB_URL` | el ayudante |
| Puertos | fijos: backend 8000, Vite 5173 (`strictPort`); el proxy de Vite apunta a `KONTROL_API_URL` | `vite.config.ts` |
| Servidor | PostgreSQL 16.2 local de QA (`qa/pg-provision.sh`); `postgres` es el único rol que puede crear bases; `kontrol_migrator` es el dueño de `kaud` | `pg_roles` |

Prototipo a mano, con una base desechable: crear y migrar a `0057`, **2,1 s**; sembrar,
**3,8 s**; 20 MB. Línea base tras sembrar: 1 instalación, 2 tenants, 3 empresas, 5 usuarios,
licencia `FULL_ACCESS`, **0 almacenes, 0 reglas de notificación**.

Hallazgo del prototipo: `installations.key_reference` es `String(120)` y guarda la ruta de
la clave de instalación; con un volumen de ruta larga la siembra falla con
`StringDataRightTruncation`. El estado de la corrida vivirá en una ruta corta, y el lanzador
la comprueba antes de crear nada. Se registra (§ final), no se absorbe.

## 24. `/speckit.specify`

`FR-054-E2EDB-001` … `-028`, con el texto del encargo. En corto:

| ID | Requisito |
|---|---|
| 001–003 | base PostgreSQL nueva y exclusiva por corrida; `RUN_ID` único; nombre con marcadores inequívocos `e2e` y `test` |
| 004, 015 | nada destructivo sobre una base que no cumpla la identidad E2E; la purga solo actúa sobre bases inequívocamente E2E |
| 005, 009 | `kaud` no se crea, trunca, recrea, migra ni elimina; ningún proceso de la corrida se conecta a ella |
| 006–007 | migraciones canónicas hasta el head real; siembra canónica y determinista |
| 008 | el backend arranca contra la base de la corrida, y se comprueba en ejecución |
| 010–012 | los procesos se cierran antes de eliminar la base; se elimina tras una corrida verde y tras una roja |
| 013 | la limpieza no oculta el código de salida de la suite |
| 014 | herramienta para listar y purgar bases E2E huérfanas tras una muerte anormal |
| 016 | evidencia por corrida: run, head, siembra, resultado, limpieza; sin URLs con secretos |
| 017–018 | dos corridas no heredan datos; dentro de una corrida, cada prueba sigue usando los suyos |
| 019 | sin reintentos, esperas, omisiones, menos trabajadores ni serialización |
| 020–022 | reevaluar `E2E-FLAKY-BAJO-CARGA`; medir el tick del planificador en `notifications:142`; reevaluar `route-crawl` y `empresas-busqueda:58` |
| 023–025 | sin cambios de esquema ni migraciones de producto; `TEST-SCHEMAS-PG-SIN-LIMPIEZA` sigue cerrada |
| 026–027 | al menos dos corridas globales desde base nueva; todo fallo, atribuido con evidencia |
| 028 | la deuda solo se cierra si no queda una inestabilidad agregada sin causa |

## 25. `/speckit.clarify` — 38 preguntas, respondidas con el repositorio

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | Dueña | SPEC054; apoyo 052 por las migraciones |
| 2–3 | Lanzador y base actuales | §23: no hay lanzador; `kaud` |
| 4 | Conexión administrativa | motor `AUTOCOMMIT` sin pool contra la base `postgres` del servidor de QA, con un rol que pueda crear bases. `CREATE`/`DROP DATABASE` no van dentro de una transacción |
| 5–6 | Nombre y `RUN_ID` | `RUN_ID = r<AAAAMMDD>t<HHMMSS>p<pid>n<6 hex>` (UTC, solo `[a-z0-9]`, no es secreto). Base: **`kontrol_e2e_test_<RUN_ID>`** — 48 caracteres como mucho, de los 63 de PostgreSQL. Patrón exacto: `^kontrol_e2e_test_r\d{8}t\d{6}p\d{1,7}n[0-9a-f]{6}$`. No colisiona con nada del repositorio: las pruebas de migración usan otros prefijos y `ktest` es de la suite de backend |
| 7 | Compuerta de identidad | `exigir_base_e2e`: el nombre cumple el patrón **entero**; no es una base protegida (`postgres`, `template0`, `template1`, `kaud`, `ktest`, la de `KONTROL_DB_URL`, la de `KONTROL_TEST_DB_URL`, la administrativa); y, para destruir, la base lleva la **marca** que el arnés le puso al crearla (`COMMENT ON DATABASE`: run, pid, máquina, fecha). El arnés nunca elimina un nombre que le llegue de fuera: lo construye él a partir del `RUN_ID`, o lo lee del catálogo ya filtrado |
| 8 | Compuerta de entorno | `KONTROL_ENVIRONMENT` ∈ {`local`, `dev`, `qa`}; servidor en la lista de permitidos (`KONTROL_E2E_PG_HOSTS`, por defecto solo `localhost`) |
| 9–10 | Migraciones | `alembic upgrade head` en `resources/backend`, con `KONTROL_DB_URL` de la corrida. Se exige **un** head en el árbol y que `alembic_version` de la base sea ese |
| 11–13 | Siembra | `qa/e2e-seed.sh`, sin cambios. No copia nada de `kaud`. Se niega a sembrar una base que ya tenga tenants —así se detecta una doble siembra— y comprueba la línea base al terminar. Secretos: solo la contraseña de siembra de QA, que ya está en el repositorio; no se añade ninguno |
| 14–16 | Backend, frontend, planificador | `uvicorn app.main:app` en 127.0.0.1:8000 con `KONTROL_DB_URL` de la corrida y su propio volumen de instalación; Vite en 5173 con `KONTROL_API_URL`; el planificador no es un proceso (§23) |
| 17–19 | Procesos, salud, orden de limpieza | un solo dueño: `qa/e2e-run.py`. Cada proceso en su grupo. Salud: `/api/v1/health/ready` y la raíz de Vite. Limpieza: suite → Vite → backend → esperar su salida → comprobar que nadie sigue conectado → base |
| 20 | Cortar conexiones | solo si, con los consumidores ya parados, queda alguien: se cortan **solo** las de la base de la corrida (`datname = …`), y se anota cuántas |
| 21 | Corrida fallida | todo va en un `finally`: migración, siembra, backend, Vite o suite que fallen dejan la base eliminada |
| 22–23 | `kill -9` y huérfanas | no hay `finally` que valga: `qa/e2e-bases.py listar` y `purgar --confirmar`. Huérfana = patrón + marca + el proceso lanzador de la marca ya no existe en esta máquina. Una base cuyo lanzador vive no se purga |
| 24–25 | Corridas simultáneas y puertos | nombres, estado y evidencia no colisionan; **los puertos sí**. Dos corridas globales a la vez en la misma máquina **no están soportadas**: el lanzador se niega a empezar si 8000 o 5173 están ocupados, antes de crear la base. No se rediseña |
| 26 | Evidencia | `qa/e2e-runs/<RUN_ID>/` (ignorado por Git): `manifest.json`, registros del backend, de Vite y de la suite, resultados de Playwright. El estado efímero —clave de instalación, almacenamiento— va en `/tmp/kontrol-e2e/<RUN_ID>/` y se elimina con la base |
| 27–28 | `kaud` y `ktest` | protegidas por nombre en la compuerta, además del patrón. El lanzador toma la huella de las dos antes y después sin conectarse a ellas (`pg_stat_database`: sesiones y tuplas escritas) |
| 29 | Esquema de producto | 0. La base efímera es el esquema de producto, migrado |
| 30 | Notificaciones | el lanzador lee, antes de eliminar la base, reglas, usuarios y la serie de ticks del planificador, y los deja en el manifiesto |
| 31–32 | `route-crawl`, `empresas-busqueda:58` | se reevalúan en las corridas globales, con `--trace retain-on-failure` para capturar HTML, consola y red si vuelven |
| 33 | `inventory-confirmation` | frontera: si reaparece un `ECONNRESET`, es `BACKEND-KEEPALIVE-5S`, deuda aparte; no se arregla aquí |
| 34–35 | Regresiones | `picking`, `pick-execution`, `putaway` (187 y 405) y `treasury:486` se miran en cada corrida |
| 36 | Corridas globales | dos como mínimo, cada una desde su base; una tercera si hace falta para atribuir |
| 37 | Reintentos | ninguno; `playwright.config.ts` no se toca |
| 38 | DeepSeek | §28 |

`MATERIAL OQ = 0`. `UNKNOWN = 0`.

## 26. `/speckit.plan` y compuerta constitucional

W01–W17 hechos (§22–§25, §28). W18–W25: `qa/e2e_nombres.py` (puro), `qa/e2e_base.py`
(compuerta, crear, migrar, sembrar, soltar, listar), `qa/e2e_corrida.py` (procesos y
ciclo), `qa/e2e-run.py` y `qa/e2e-bases.py` (órdenes), y `e2e/global-setup.ts` deja de
sembrar cuando la corrida la lanza el arnés. W26–W29: pruebas DB-01..22. W30–W39:
dirigidas, medida de notificaciones, corridas globales, atribución y residuales. W40
mutaciones. W41–W45 limpieza, `kaud` intacta, `analyze`, trazabilidad, convergencia.

| Compuerta | | |
|---|---|---|
| G01–G04 checkpoint, orquestación, dueña, decisión | §22 | ✅ |
| G05–G08 lanzador, dependencia de `kaud`, migraciones, siembra | §23 | ✅ |
| G09–G13 nombre, `RUN_ID`, compuerta, conexión administrativa, cableado del backend | §25 | ✅ |
| G14–G17 procesos, limpieza, corrida fallida, huérfanas | §25 | ✅ |
| G18–G21 `kaud`, `ktest`, simultaneidad, puertos | §25 | ✅ |
| G22–G24 notificaciones, `route-crawl`, login | §25 | ✅ |
| G25–G26 sin migración de producto; sin reintentos ni esperas | §24 | ✅ |
| G27–G29 pruebas, mutaciones, tareas clasificadas | §27, §28 | ✅ |
| G30–G32 `MATERIAL OQ` 0 · `UNKNOWN` 0 · trazabilidad 100 % | | ✅ |

Principios: 21 y 24 (PostgreSQL recién creado como evidencia), 10, 22, 27. **PASS.**

Checklist: las 47 casillas del encargo, verificadas contra §22–§28; ninguna abierta.

## 27. Pruebas y mutaciones, diseñadas antes de implementar

`resources/backend/tests/` (solo PostgreSQL; el servidor administrativo se deriva de
`KONTROL_TEST_DB_URL`, y el rol dueño es el mismo: las pruebas no llevan credenciales).

| ID | Caso | Req. |
|---|---|---|
| DB-01 | nombres inválidos —vacío, `None`, sin marcadores, con sufijo o prefijo de más, mayúsculas, inyección— rechazados | 003, 004 |
| DB-02 | `kaud`: denegada **antes** de cualquier SQL | 005 |
| DB-03 | `ktest`: denegada | 004 |
| DB-04 | la base de `KONTROL_DB_URL`, un entorno `prod`/`staging`/`uat` o un servidor fuera de la lista: denegados | 004 |
| DB-05 | dos `RUN_ID`, dos bases; crear una que ya existe falla y no la reutiliza | 001, 002 |
| DB-06 | base recién creada migrada: `alembic_version` = head, un solo head | 006 |
| DB-07 | siembra: línea base exacta; sembrar una base ya sembrada se rechaza | 007 |
| DB-08 | el backend de la corrida escribe en la base de la corrida, y solo en ella | 008, 009 |
| DB-09 | corrida verde: la base desaparece | 011 |
| DB-10, DB-20 | suite que falla con código 3: la base desaparece y el lanzador sale con 3 | 012, 013 |
| DB-11..13 | fallo en migración, en siembra, en el arranque del backend: la base desaparece y el lanzador falla | 012 |
| DB-14 | una base E2E sin lanzador vivo aparece como huérfana; la de un lanzador vivo, como viva | 014 |
| DB-15 | purgar elimina solo las huérfanas; sin `--confirmar` no elimina nada; una base con el patrón pero sin la marca no se toca | 014, 015 |
| DB-16 | la corrida B no ve el dato que creó la corrida A | 017 |
| DB-17, DB-18 | huella de `kaud` y `ktest` igual antes y después | 005 |
| DB-19 | ni la salida del lanzador ni el manifiesto contienen una URL con credenciales | 016 |
| DB-21 | limpiar dos veces: la segunda no hace nada y no falla | 010 |
| DB-22 | dos `RUN_ID` simultáneos no comparten nombre, estado ni evidencia; con el puerto ocupado el lanzador se niega antes de crear la base | 002 |

| Mutante | Cambio | Debe matarlo |
|---|---|---|
| M-01 | quitar la comprobación del patrón del nombre | DB-01 |
| M-02 | sacar `kaud` de las protegidas y relajar el patrón | DB-02 |
| M-03 | reutilizar en silencio una base que ya existe | DB-05 |
| M-04 | eliminar sin mirar la marca | DB-15 |
| M-05 | no comprobar el head tras migrar | DB-06 |
| M-06 | sembrar sin mirar si la base ya tiene tenants | DB-07 |
| M-07 | no eliminar la base si la suite falla | DB-10 |
| M-08 | devolver 0 si la limpieza fue bien | DB-20 |
| M-09 | no eliminar la base si falla la preparación | DB-11..13 |
| M-10 | purgar sin exigir `--confirmar` | DB-15 |
| M-11 | purgar también las bases de un lanzador vivo | DB-14, DB-15 |
| M-12 | cortar las conexiones de todo el servidor, no solo las de la base | DB-21 (con una conexión testigo a otra base) |
| M-13 | el backend arranca contra `KONTROL_DB_URL` heredada, no contra la de la corrida | DB-08 |
| M-14 | aceptar un entorno `prod` | DB-04 |

## 28. `/speckit.tasks` y `/speckit.analyze` previo

| ID | Tarea | Req. | EXECUTOR · MODEL | SEC | EGRESS | Ficheros |
|---|---|---|---|---|---|---|
| T30 | Reconciliación, inventario, prototipo, diseño | todos | CLAUDE | YES | n-a | este documento |
| T31 | Nombres y marcas: funciones puras | 002, 003 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `qa/e2e_nombres.py` (nuevo) |
| T32 | Pruebas de T31 | 002, 003 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `resources/backend/tests/test_e2e_nombres.py` (nuevo) |
| T33 | Compuerta, crear, migrar, sembrar, soltar, listar, huella | 001–007, 014, 015 | CLAUDE | YES | n-a | `qa/e2e_base.py` |
| T34 | Ciclo de vida y procesos; órdenes | 008–013, 016 | CLAUDE | YES | n-a | `qa/e2e_corrida.py`, `qa/e2e-run.py`, `qa/e2e-bases.py` |
| T35 | La siembra de Playwright cede ante el arnés | 007 | CLAUDE | NO | n-a | `resources/frontend/e2e/global-setup.ts`, `.gitignore` |
| T36 | Pruebas de la compuerta con direcciones sintéticas (DB-01..04) | 004, 005 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `resources/backend/tests/test_e2e_base_identidad.py` (nuevo) |
| T37 | Pruebas de ciclo sobre PostgreSQL real (DB-05..22) | 001–017 | CLAUDE | YES | n-a | `tests/test_e2e_base_ciclo.py`, `tests/test_e2e_corrida.py` |
| T38 | Auditar, aplicar y probar T31, T32, T36 | — | CLAUDE | NO | n-a | — |
| T39 | Mutaciones | 004–015 | CLAUDE | YES | n-a | — |
| T40 | Dirigidas en base nueva; medida de notificaciones | 020, 021 | CLAUDE | NO | n-a | — |
| T41 | Corridas globales 1 y 2 (y 3 si hace falta); atribución | 022, 026, 027 | CLAUDE | NO | n-a | — |
| T42 | Residuales: causa, dueña y arreglo, si `MATERIAL OQ = 0` | 028 | CLAUDE (se reclasifica tarea a tarea) | — | — | por determinar tras T41 |
| T43 | Backend completo, residuos, `kaud`/`ktest` intactas | 023–025 | CLAUDE | NO | n-a | — |
| T44 | `analyze` final, trazabilidad, convergencia, hoja de ruta, Git | — | CLAUDE | NO | n-a | documentos |

`RETRY_MAX: 2` en T31, T32 y T36. Los tres encargos usan direcciones inventadas
(`postgresql://user:pass@host:5432/test_db`): ni el servidor, ni el puerto, ni los nombres
de rol de QA salen del repositorio. `kaud` y `ktest` son nombres de base, no secretos, y
forman parte del contrato de la compuerta.

`analyze` previo: `BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` = 0;
requisitos y tareas huérfanas = 0; `MATERIAL OQ` = 0; `UNKNOWN` = 0; trazabilidad 100 %.
Riesgos mirados uno a uno: base de producto (compuerta), `kaud` compartida (protegida y con
huella), huérfanas (herramienta), puertos fijos (negativa temprana), secretos en registros
(DB-19), esquema o migración ocultos (0), reintentos, esperas, omisiones, trabajadores,
serie (0).

**Autorización de `implement`:** la del encargo `E2E-BASE-QA-ACUMULA`.

## 29. Primera corrida global sobre base nueva, y tercera ampliación de alcance

El arnés (§30) funciona: en 9 s crea la base, la migra, la siembra, levanta el backend,
comprueba que escribe en ella y lo elimina todo. La primera corrida global exploratoria
sobre base nueva dio **199 / 1 / 40**, y el fallo fue `route-crawl`:
`/comercial/listas-precio` sin H1. **El mismo del 2026-09-30, que estaba sin causa.** Esta
vez había traza, y sola sobre base nueva falla siempre.

Lo que se encontró, medido antes de decidir nada
(`evidence/e2e-base-por-corrida/recorrido-de-rutas.txt`):

| | Defecto | Evidencia |
|---|---|---|
| **A** · producto, sesión | Al recargar una ruta, `AuthProvider` da la sesión por restaurada (`isReady`) cuando llega el token, **antes** de tener al usuario (`/auth/me` va sin esperar). `RouteGuard` ve «listo y sin usuario», manda a `/login`, y `LoginPage`, ya con usuario, manda a **Inicio**. La ruta pedida se pierde | recorrido de diagnóstico sobre el código de `c94eed4`: **81 de 96 rutas** del menú acaban en `/`. Que una ruta se llegue a pintar depende de qué llegue antes, su módulo o `/auth/me` |
| **Prueba** · `route-crawl` | no comprueba que sigue en la ruta que pidió: en 81 de 96 casos lee el H1 de Inicio y lo da por bueno | ídem |
| **B** · producto | `ListasPrecioPage` trata `GET /treasury/currencies` como un array; el servidor responde el sobre `{items, …}`. En cuanto llegan las monedas, `(monedas.data ?? []).map is not a function` y la pantalla cae | traza: error de consola en el render; sola, 2 de 2 |
| **C** · producto | `DiagnosticoPage` espera `{status, services, version}`; `GET /system/diagnostics` responde `{environment, version, database, installation, license, …}`. `Object.entries(undefined)`: la pantalla cae siempre que se llega a pintar, desde el commit fundacional | recorrido de diagnóstico con A corregido de forma provisional: 96 rutas en su sitio, 1 rota |

Por eso el fallo era «esporádico»: la pantalla rota solo se ve cuando la ruta gana la
carrera de A. No era carga ni acumulación; `kaud` no lo tapaba más que cualquier otra base.

**Alcance ampliado, antes de implementar** — producto, frontend:

| Dueña | Fichero | Cambio |
|---|---|---|
| Master 002 (seguridad y sesiones) → `001-fundacion`, FR-001-042 | `src/app/contexts/AuthContext.tsx` | la restauración de sesión no se da por terminada hasta tener al usuario |
| Master 012 (maestros comerciales) → `specs/012-maestros-comerciales` | `src/modules/comercial/ListasPrecioPage.tsx` | leer `items` del sobre de monedas |
| Master 001, FR-001-084 → `001-fundacion` | `src/pages/DiagnosticoPage.tsx`, `src/api/types.ts` | pintar lo que el diagnóstico responde de verdad |
| SPEC054 | `e2e/route-crawl.spec.ts` | comprobar que cada ruta sigue siendo la pedida |

Sin decisión material: los tres son defectos frente a contratos que ya existen —recargar no
debe cambiar de página; el sobre de listados es el de `api-contracts.md`; FR-001-084 pide
versión, identidad y licencia, que es lo que el servidor da—. Backend, esquema, migraciones: 0.

| ID | Requisito |
|---|---|
| FR-054-E2EDB-029 | Tras recargar o abrir directamente una ruta con sesión válida, la aplicación pinta esa ruta: nunca pasa por `/login` ni acaba en Inicio |
| FR-054-E2EDB-030 | Listas de precios pinta las monedas de la empresa y no cae al recibirlas |
| FR-054-E2EDB-031 | Diagnóstico pinta versión, entorno, base de datos, instalación y licencia tal como los responde el servidor, y no cae |
| FR-054-E2EDB-032 | `route-crawl` falla si una ruta del menú acaba en otra ruta |

| ID | Tarea | Req. | EXECUTOR · MODEL | SEC | EGRESS | Ficheros |
|---|---|---|---|---|---|---|
| T50 | Restauración de sesión y su prueba | 029 | CLAUDE | **YES** (sesión) | n-a | `AuthContext.tsx`, `src/app/contexts/AuthContext.restauracion.test.tsx` |
| T51 | Monedas de Listas de precios y su prueba | 030 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `ListasPrecioPage.tsx`, `ListasPrecioPage.test.tsx` |
| T52 | Diagnóstico y su prueba | 031 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `DiagnosticoPage.tsx`, `src/api/types.ts`, `DiagnosticoPage.test.tsx` |
| T53 | El recorrido comprueba la ruta | 032 | CLAUDE | NO | n-a | `e2e/route-crawl.spec.ts` |
| T54 | Auditar y aplicar T51, T52; recorrido de diagnóstico de nuevo; mutaciones de A, B, C | 029–032 | CLAUDE | NO | n-a | — |

T36 se **reclasifica a `CLAUDE_ONLY` antes de ejecutarse**: su contrato lleva los nombres
de las bases de QA, y el encargo pide no enviarlos. `DEEPSEEK CALLS` de T36 = 0.

`analyze` de la ampliación: `BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` = 0;
`MATERIAL OQ` = 0; trazabilidad 100 %.

Hallazgos del mismo recorrido que **no** se absorben (§ final): `GET /system/diagnostics` no
exige sesión y devuelve la ruta de almacenamiento del servidor, contra su propio docstring.

## 30. Implementación — el arnés

| Fichero | Qué es |
|---|---|
| `qa/e2e_nombres.py` | puro: `RUN_ID`, nombre de la base, marca, nombre de aplicación. Solo lo que cumple el patrón entero es una base de corrida |
| `qa/e2e_base.py` | la compuerta (`exigir_base_e2e`), crear, migrar y comprobar la cabeza, sembrar una sola vez y comprobar la línea base, eliminar y comprobar que no está, listar y purgar huérfanas, huella de las bases protegidas |
| `qa/e2e_corrida.py` | el ciclo entero y sus procesos, con la limpieza en `finally` |
| `qa/e2e-run.py` · `qa/e2e-bases.py` | las dos órdenes |
| `e2e/global-setup.ts` | no vuelve a sembrar una corrida que ya trae su base sembrada |
| `.gitignore` | `qa/e2e-runs/`, la evidencia local de cada corrida |

```
resources/backend/.venv/bin/python qa/e2e-run.py                       # la suite entera
resources/backend/.venv/bin/python qa/e2e-run.py -- e2e/picking.spec.ts --trace retain-on-failure
resources/backend/.venv/bin/python qa/e2e-bases.py listar | purgar [--confirmar]
```

Decisiones de implementación, todas dentro de lo clarificado:

- **La base nace de `template0`**, con dueño, UTF-8 y UTC, y con un `COMMENT ON DATABASE`
  que dice de qué corrida es, qué proceso la creó, en qué máquina y cuándo. Para eliminarla
  hacen falta el patrón **y** esa marca; una base con nombre de corrida y sin marca no se toca.
- **El backend se comprueba en ejecución**, no por configuración: el lanzador inicia sesión
  por la API y exige que la sesión aparezca en la base de la corrida, y que todas las
  conexiones con el nombre de aplicación de la corrida estén en ella. Si no, aborta.
- **Los procesos de la corrida solo conocen su base**: `KONTROL_DB_URL` y `KONTROL_E2E_DB_URL`
  se fijan, y `KONTROL_TEST_DB_URL` se quita, aunque el operador las tuviera puestas.
- **Se eliminan solo las sesiones de la base de la corrida**, y solo si, con Vite y el
  backend ya parados, queda alguien: `DROP DATABASE … WITH (FORCE)`, que PostgreSQL limita a
  esa base. Se anota cuántas eran. En las corridas reales: 0.
- **Huérfana** es la base con patrón y marca cuyo lanzador ya no existe en esta máquina. El
  número de proceso se recicla: solo cuenta como lanzador el proceso que ya existía cuando
  se creó la base. La purga detiene antes lo que la corrida dejó en marcha, que se reconoce
  porque lleva su `RUN_ID` en el entorno.
- **`kaud` y `ktest` no se tocan**: están fuera del patrón, están en la lista de protegidas,
  y el lanzador compara su huella antes y después sin conectarse a ellas.
- **Código de salida**: el de la suite; 70 si la preparación falló; 75 si la suite pasó y la
  limpieza no; 130 si se interrumpió.
- **Nada con usuario y clave en la salida**: consola, registros y manifiesto se tachan.
- **Dos corridas a la vez en una máquina no están soportadas** (puertos 8000 y 5173): si
  están ocupados, el lanzador no crea nada. También impide certificar con otra pila levantada.

## 31. Pruebas y mutaciones

| Suite | Casos | Dónde | Autor |
|---|---|---|---|
| `tests/test_e2e_nombres.py` | 76 | puras | DeepSeek (T32, un reintento) |
| `tests/test_e2e_base_identidad.py` | 54 | puras, direcciones inventadas | Claude (T36 reclasificada) |
| `tests/test_e2e_base_ciclo.py` | 23 | PostgreSQL real | Claude |
| `tests/test_e2e_corrida.py` | 14 | PostgreSQL real, lanzador y backend de verdad | Claude |
| `AuthContext.restauracion.test.tsx` | 3 | Vitest | Claude |
| `ListasPrecioPage.test.tsx` · `DiagnosticoPage.test.tsx` | 3 · 4 | Vitest | DeepSeek (T51; T52 con un reintento) |

DB-01..22 quedan cubiertas (§36). **Mutaciones: 29 de 29 en el arnés, 10 de 10 en el
frontend** (`mutaciones.txt`), y una más de extremo a extremo: con el defecto de sesión
reintroducido, el recorrido reforzado cae en la primera ruta (`/mi-licencia` → `/`). Un
mutante sobrevivió en la primera pasada —la censura de credenciales estaba hecha dos veces
y quitar una no se notaba—: se dejó una sola por sitio y se endureció la prueba.

Y la muerte a la fuerza, de verdad (`muerte-a-la-fuerza.txt`): con `kill -9` al lanzador a media
corrida, la base queda y el backend sigue respondiendo; `e2e-bases.py listar` la da por
huérfana, con sus dos procesos; `purgar` sin confirmar no elimina nada; con `--confirmar`
desaparecen la base, el backend y el estado.

## 32. Resultados

### Tres corridas globales consecutivas, cada una sobre su base (`corridas-globales.txt`)

| Corrida | Resultado | Suite | Limpieza | Usuarios · reglas · almacenes al acabar | Tick más lento |
|---|---|---|---|---|---|
| 1 | **200 / 0 / 40** | 179 s | LIMPIA | 64 · 2 · 85 | 0,84 s |
| 2 | **200 / 0 / 40** | 179 s | LIMPIA | 64 · 2 · 85 | 0,80 s |
| 3 | **200 / 0 / 40** | 180 s | LIMPIA | 64 · 2 · 85 | 0,84 s |

Las tres acaban en el mismo estado, hasta el megabyte: ninguna heredó nada. Backend: 0
errores no controlados, 0 esperas de pool, 0 respuestas 500. Suite: 0 `ECONNRESET`. Al
terminar no queda ninguna base de corrida en el servidor, y la huella de `kaud` y `ktest`
tomada antes y después es idéntica.

### Notificaciones (FR-021)

| | En `kaud` (2026-10-01) | En base nueva |
|---|---|---|
| `RULES_AT_START` | 26–28 | **0** |
| `RULES_BEFORE_NOTIFICATIONS_TEST` | 28 | **2** |
| `USERS_AT_START` | 868 | **5** |
| `USERS_BEFORE_NOTIFICATIONS_TEST` | 868 | **29–32** |
| `TICK_DURATION` del primer tick con trabajo (43 hechos) | **33,09 s** | **0,60–0,70 s** |
| `TICK_DURATION` del más lento de la corrida | 33,09 s | 0,80–0,84 s |
| `notifications:142` | cae a los 30 s | pasa en 5 s |

Clasificación: **`INTER-RUN QA ACCUMULATION`**. Dentro de una corrida el tick no crece: con
64 usuarios y 2 reglas al final, el más lento tarda menos de un segundo. No hay acumulación
intra-corrida que investigar.

### Recorrido de rutas (FR-022) — §29

Con los tres arreglos y la comprobación de ruta: `route-crawl` sola, 2 de 2; en las tres
corridas globales, 3 de 3. Y ahora comprueba las 96 rutas de verdad.

### `empresas-busqueda:58` (FR-022)

Pasa en las cuatro corridas globales sobre base nueva (2,4–2,7 s). El login en blanco del
2026-10-01 **no se ha reproducido** —ni entonces en 800 cargas aisladas, ni ahora— y su
causa sigue sin demostrar. Queda como deuda propia (§34), con una diferencia: cada corrida
guarda ya el registro de Vite, el del backend y, si algo cae, la traza del navegador.

### Backend y frontend (`backend-y-frontend.txt`)

PostgreSQL: 1 971 pasan · 27 omitidas · 37 fallan; el conjunto de fallos es el de `c94eed4`
y hay 167 pruebas nuevas. SQLite: 986 · 1 005 · 44: los 43 de siempre y uno más,
`test_concurrencia_de_codigo_resuelta_por_constraint`, que es **preexistente e
intermitente solo en SQLite** —sola falla 9 de 20 en `42cd793`, dos ciclos atrás, y pasa 5
de 5 en PostgreSQL—; este ciclo no toca `app/` ni esa suite. Tras la corrida en PostgreSQL:
0 schemas temporales, 0 conexiones, 0 bases de corrida. Frontend: 441 pruebas, `eslint` y
`tsc` limpios.

## 33. `E2E-FLAKY-BAJO-CARGA`, fallo por fallo, después de la base nueva

| Fallo | Causa | Qué se hizo | En base nueva (4 corridas globales) |
|---|---|---|---|
| `picking:192`, `:208`, `:240` · `pick-execution:297` · `putaway:187` (caducidad) | N+1 del listado de almacenes × almacenes acumulados | corregido en producto (`c94eed4`) | pasan en 3–4 s |
| `putaway:405` | la prueba contaba las listas de toda la empresa | corregida la prueba (`c94eed4`) | pasa en 0,8 s |
| `treasury:486` | la prueba esperaba `CLOSED`, que está en `PRE_CLOSED` | corregida la prueba (`c94eed4`) | pasa en 5,5 s |
| `notifications:142` | reglas y usuarios acumulados entre corridas: tick de 33 s | **base nueva por corrida** | tick de 0,6–0,8 s; pasa en 5 s |
| `putaway:187` («did not find some options») | corte en 500 del desplegable × almacenes acumulados | base nueva: 85 almacenes por corrida. El corte sigue en el producto (`ALMACENES-DESPLEGABLES-TRUNCADOS`, abierta) | pasa en 3,3 s |
| `route-crawl` sin H1 | dos pantallas que caían al pintarse, visibles solo cuando la ruta ganaba una carrera de la restauración de sesión; y un recorrido que no miraba en qué ruta estaba | **corregidos los tres defectos de producto y la prueba** (§29) | pasa, y recorre de verdad las 96 rutas |
| `inventory-confirmation` — `ECONNRESET` | keep-alive de 5 s en los dos extremos | **explicado y reproducido; no corregido** → `BACKEND-KEEPALIVE-5S`, deuda propia, decisión de despliegue | 0 apariciones |
| `empresas-busqueda:58` — login en blanco | **sin causa demostrada** | deuda propia, `E2E-PANTALLA-SIN-PINTAR`, reducida a este único caso | 0 apariciones; pasa en 2,5 s |
| Seis pruebas a la vez a los 30 s | mi experimento de 40 conexiones (ciclo anterior) | no se repite el experimento; el mecanismo, en `LICENCIA-MIDDLEWARE-BD-EN-EL-BUCLE` | 0 esperas de pool |

## 34. Deudas

| Deuda | Estado tras este ciclo |
|---|---|
| **`E2E-BASE-QA-ACUMULA`** | **CLOSED / CONVERGED** — decisión de la dueña implementada: base nueva por corrida |
| **`E2E-NOTIFICACIONES-REGLAS-VIVAS`** | **CLOSED** — era acumulación entre corridas; en base nueva no existe. En `kaud` las reglas siguen ahí: es una base de QA manual |
| **`E2E-FLAKY-BAJO-CARGA`** | **CLOSED / CONVERGED** (§35) |
| `E2E-PANTALLA-SIN-PINTAR` | **OPEN**, reducida: queda solo el login en blanco del 2026-10-01, sin causa. El caso de `route-crawl` está explicado y corregido |
| `BACKEND-KEEPALIVE-5S` | **OPEN** — sin tocar, como pedía el encargo |
| `ALMACENES-DESPLEGABLES-TRUNCADOS` | **OPEN** — la base nueva no la cierra: el corte sigue en nueve pantallas |
| `LICENCIA-MIDDLEWARE-BD-EN-EL-BUCLE` · `PICKLIST-DUPLICADA-500` · `LISTADOS-SIN-TOPE` · `ENTORNO-SIN-CLAMSCAN` | **OPEN** — sin tocar |
| `TEST-SCHEMAS-PG-SIN-LIMPIEZA` | sigue **CLOSED / CONVERGED** |

Nuevas, encontradas y **no absorbidas**:

| Deuda | Qué |
|---|---|
| **`DIAGNOSTICO-SIN-SESION`** | `GET /system/diagnostics` no exige sesión —su única dependencia es `get_db`— y responde identificador de instalación, modo y vigencia de licencia, y la **ruta de almacenamiento** del servidor, contra su propio docstring («no expone rutas internas»). Seguridad: decisión de la dueña |
| **`INSTALACION-KEY-REFERENCE-120`** | `installations.key_reference` es `String(120)` y guarda la ruta de la clave de instalación: con un volumen de ruta larga, el alta de la instalación falla con `StringDataRightTruncation` |
| **`MIGRACIONES-URL-CON-PORCENTAJE`** | `alembic/env.py` pasa `KONTROL_DB_URL` por `configparser`: una URL con «%» —una contraseña con caracteres codificados— rompe `alembic upgrade head`, que es lo primero que hace el contenedor al arrancar |
| **`ALMACENES-CARRERA-SQLITE-HILOS`** | `test_concurrencia_de_codigo_resuelta_por_constraint` es intermitente en SQLite (9 de 20 sola, ya en `42cd793`); en PostgreSQL pasa |
| **`E2E-CUARENTA-OMITIDAS`** | 40 de las 240 pruebas E2E se omiten porque exigen `KONTROL_E2E_USER`, que ninguna corrida de certificación ha definido: accesibilidad y documentos no se certifican |

## 35. Veredicto

**`E2E-BASE-QA-ACUMULA`: cerrada.** Cada corrida E2E certificable crea su base, la migra a
la cabeza, la siembra, levanta contra ella backend y Vite, corre la suite y lo elimina todo,
pase o falle; lo que queda tras una muerte a la fuerza se lista y se purga. `kaud` sale de
la certificación y no se toca.

**`E2E-FLAKY-BAJO-CARGA`: cerrada**, con la condición que fijó la dueña (FR-028): no queda
una inestabilidad agregada sin causa.

- **Todo lo que tiene causa demostrada y arreglo propio está corregido**: en producto, el
  N+1 del listado de almacenes, la restauración de sesión que perdía la ruta y las dos
  pantallas que caían al pintarse; en las pruebas, las dos carreras y el recorrido de
  rutas, que ahora comprueba lo que decía comprobar; y en el arnés, la acumulación entre
  corridas, que desaparece con la base nueva.
- **Uno está explicado y sin corregir**, en su propia deuda: `BACKEND-KEEPALIVE-5S`. Mientras
  esté abierta, una corrida puede recibir un `ECONNRESET` puntual: se sabrá qué es.
- **Uno sigue sin causa**, en su propia deuda: el login en blanco, visto una vez y no
  reproducido en más de 800 cargas ni en cuatro corridas globales sobre base nueva.

Tres corridas globales consecutivas desde base nueva: 200 / 0 / 40 las tres; y una cuarta el
2026-10-06, en un clúster reaprovisionado tras un reinicio y sin `kaud`, igual.

Lo que esta deuda era, al final: una base que crecía sin límite destapando caminos cuyo
coste dependía de su tamaño, dos pruebas con carreras, y —lo que la base vieja no dejaba
ver— dos pantallas rotas detrás de una restauración de sesión que perdía la ruta.

| | |
|---|---|
| `STATUS` | **`CONVERGED`** |
| Corridas globales desde base nueva | 5 (1 exploratoria, 3 de certificación, 1 el 2026-10-06 tras un reinicio que vació `/tmp` y se llevó `kaud` y `ktest`): la exploratoria destapó `route-crawl`; las 4 finales, 200/0/40 |
| Reintentos, esperas fijas, omisiones, serialización, menos trabajadores, más tiempo | 0 |
| Esquema, migraciones, índices | 0 |
| Producto | frontend: `AuthContext.tsx`, `ListasPrecioPage.tsx`, `DiagnosticoPage.tsx`, `api/types.ts`. Backend: 0 |
| `kaud` · `ktest` | intactas (huella idéntica) |

## 36. `analyze` final y trazabilidad

| Requisito | Prueba o evidencia | |
|---|---|---|
| 001–003 base nueva, `RUN_ID`, nombre | E2ENOM-01..12, E2ECICLO-01..03 | ✅ |
| 004, 015 compuerta y purga | E2EID-01..18, E2ECICLO-13..15, 18..21 (DB-01..04, 15) | ✅ |
| 005, 009 `kaud` | E2EID-03, 04; huella antes/después; E2ECORRIDA-01, 13 (DB-02, 17, 18) | ✅ |
| 006 migraciones | E2ECICLO-04..07 (DB-06) | ✅ |
| 007 siembra | E2ECICLO-08..10 (DB-07); `global-setup.ts` | ✅ |
| 008 backend contra su base | E2ECORRIDA-01, 06 (DB-08) | ✅ |
| 010–012 limpieza | E2ECORRIDA-01..05, 12; E2ECICLO-11, 12 (DB-09..13, 21) | ✅ |
| 013 código de salida | E2ECORRIDA-02 (DB-10, 20) | ✅ |
| 014 huérfanas | E2ECICLO-16, 17, 19..22 (DB-14, 15) | ✅ |
| 016 evidencia sin secretos | E2ECORRIDA-01, 03 (DB-19); manifiestos | ✅ |
| 017 aislamiento | E2ECORRIDA-07 (DB-16); tres corridas con el mismo estado final | ✅ |
| 018 datos propios | sin cambio: las pruebas siguen usando su marca | ✅ |
| 019 sin reintentos ni esperas | `playwright.config.ts` sin cambios; E2ECORRIDA-14 | ✅ |
| 020–022 reevaluación | §32, §33 | ✅ |
| 023–025 sin esquema ni migraciones; `TEST-SCHEMAS` cerrada | diff; residuos 0 | ✅ |
| 026 dos corridas desde base nueva | tres | ✅ |
| 027 todo fallo atribuido | §33; el de SQLite, §32 | ✅ |
| 028 cierre sin inestabilidad agregada | §35 | ✅ |
| 029 recargar no cambia de ruta | RESTAURA-01..03; `route-crawl` | ✅ |
| 030 Listas de precios | LM-01..03 | ✅ |
| 031 Diagnóstico | DIAG-01..04 | ✅ |
| 032 el recorrido comprueba la ruta | mutante de extremo a extremo | ✅ |
| DB-22 simultaneidad | E2ECORRIDA-08, 11: nombres aislados; con el puerto ocupado no se crea nada | ✅ |

`BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` = 0 · `MATERIAL OQ` = 0 ·
`UNKNOWN` = 1 fallo, en deuda propia · requisitos y tareas huérfanas = 0 · trazabilidad 100 %.

Desviaciones mías, dichas: el encargo de T32 llevaba los nombres `kaud` y `ktest` como
literales de prueba —sin servidor, puerto, rol ni credenciales—, y debieron ser inventados;
dos rechazos de parche fueron por errores de mis encargos (una línea en blanco que no
dicté bien, un `beforeEach` que devolvía una función); una primera reproducción manual
contra `kaud` estaba mal planteada y no demostraba nada, y se descartó; al detener esa pila
manual, dos órdenes mías se mataron a sí mismas y dejaron Vite vivo unos minutos.

Orquestación (`orquestacion.txt`): 20 tareas · 16 `CLAUDE_ONLY` · 4 `DEEPSEEK_ELIGIBLE`,
las cuatro ejecutadas por DeepSeek (`deepseek-v4-flash`) · 6 llamadas · 2 reintentos · 4
parches aceptados, 2 rechazados, 0 retocados · 18 930 / 14 378 tokens · $0,006570 · puente:
194 581 tokens.
