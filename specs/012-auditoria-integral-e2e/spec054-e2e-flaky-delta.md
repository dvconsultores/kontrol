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
