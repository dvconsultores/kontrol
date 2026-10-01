# SPEC 054 · Delta dirigida — TEST-SCHEMAS-PG-SIN-LIMPIEZA

**Fecha** 2026-10-01 · **Dueña** SPEC054 (`specs/012-auditoria-integral-e2e`) ·
**Apoyo** SPEC052 (`specs/001-fundacion`, dueña de las pruebas de migración que crean bases) ·
**Base** `3ea8d66` · **Rama** `develop`

Infraestructura de pruebas. **No toca producto**: ni `app/`, ni frontend, ni API, ni
esquema, ni migraciones.

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` | `3ea8d66` / **`3ea8d66`** / `3ea8d66` |
| `ACTUAL_BRANCH` | `develop`; no se crea ninguna rama |
| `COMMITS_AFTER_3EA8D66` | 0 |
| `WORKTREE_STATE` | limpio |
| `ORCHESTRATION_STATUS` | `VERIFIED_END_TO_END`; `orchestration_readiness.py` 11/11 |
| `DEEPSEEK_TOOL` · `MODEL_ROUTING` · `RETRY_MAX` | `mcp__deepseek__deepseek_chat` · `deepseek-v4-flash` · 2 |

## 2. Veredicto, por delante

**Cada llamada a `make_engine` crea un schema entero y un motor, y nadie los suelta.** No
hay dueño: la función devuelve el motor y se olvida del schema; las 27 fixtures que la
llaman cierran su sesión y nada más. Trece de ellas son de ámbito de función, así que el
arnés crea **un schema de 1 129 relaciones y ~10 MB por cada prueba**. Reproducido con un
solo fichero: 21 pruebas dejan 21 schemas y 212 MB, y cada repetición los suma —21, 42, 63—.
Es fuga lógica: los schemas siguen ahí. Las conexiones mueren con el proceso; lo que crece
dentro de una corrida es el número de motores con su pool abierto.

Aparte, cuatro ficheros de pruebas de migración crean 17 bases enteras con nombre fijo y no
las sueltan: 319 MB que no se acumulan, pero se quedan.

## 3. Dueñas

| | Dueña | Evidencia |
|---|---|---|
| `PRIMARY_OWNER` | **SPEC054** — `specs/012-auditoria-integral-e2e` | la deuda está registrada con «dueñas 054/052»; el arnés (`tests/conftest.py::make_engine`) nació en `579affb`, «la suite se ejecuta sobre PostgreSQL real», para cumplir el Principio 21 |
| `INFRA_SUPPORT_OWNER` | SPEC052 (Master 052, en `specs/001-fundacion`) | las pruebas `test_*_migration_*`, `test_uom_backfill`, `test_warehouse_migration_0018` crean bases |
| `OWNER_IDENTITY_CONFLICT` | **0** | |

## 4. Evidencia histórica

| | |
|---|---|
| `FIRST_OBSERVED` | 2026-09-30, `EMPRESAS-BUSQUEDA-Q` (`spec001-empresas-busqueda-q-delta.md`) |
| `WORST_DB_SIZE` | 6,8 GB tras tres corridas completas; llenó el `tmpfs` de 7,6 GB y PostgreSQL cayó en la cuarta |
| `WORST_CONNECTION_COUNT` | ~80 de 100; dos pruebas erraron por `too many clients` |
| `MOST_RECENT_BEFORE` → `AFTER` | 2026-10-01, `AUDIT-TOTAL-CARGA-TODO`: 111 MB → 3 240 MB, 10 → 313 schemas, pico de 60 conexiones, en **una** corrida |
| Remedio usado hasta hoy | `DROP DATABASE ktest` y recrearla, a mano |

## 5. La base de prueba, identificada

| Señal | Valor |
|---|---|
| Declarada expresamente para pruebas | `KONTROL_TEST_DB_URL` (documentada en `.claude/CLAUDE.md`) |
| Nombre | `ktest` |
| Servidor | `localhost:55432`, el `pgserver` de QA (`qa/pg-provision.sh`), datos en `/tmp/kontrol-pgdata-045` |
| Base del producto | `KONTROL_DB_URL` sin definir en pruebas (SQLite por defecto): distinta |
| Entorno | `KONTROL_ENVIRONMENT=local` |
| **`DB_IS_TEST`** | **YES** |

## 6. Inventario del arnés

`resources/backend/tests`: 113 módulos de prueba, 8 de apoyo.

| | |
|---|---|
| Fábrica de motores | una: `conftest.make_engine`. En PostgreSQL crea `CREATE SCHEMA "t_<12 hex>"` con un motor administrativo que sí se libera, y devuelve otro motor con `search_path` a ese schema |
| Llamadas | **27**, todas dentro de fixtures; ninguna a nivel de módulo |
| Ámbito de función (`db_session`) | **13** módulos: un schema y un motor **por prueba** |
| Ámbito de módulo (`_app_client`, `_mundo`) | **12** módulos, más `conftest_multicompany.mundo` (lo usan 46 módulos) y `audit_world.montar` |
| Ámbito de sesión | ninguno |
| Limpieza actual | `session.close()` y nada más: **0** `engine.dispose()`, **0** `DROP SCHEMA` |
| `POOL_CLASS` | `QueuePool` por defecto (`pool_size=5`, `max_overflow=10`) |
| Referencias globales | `app.core.database._engine` y `_SessionLocal` quedan apuntando al motor de la última fixture |
| `pytest-xdist` | **no instalado**: la suite corre en un solo proceso. No hay colisión entre trabajadores que resolver |
| Motores asíncronos | ninguno |
| Hilos | sí, en pruebas de concurrencia; comparten el motor de su fixture |
| Registro de recursos o `pytest_sessionfinish` | no existe |
| Bases enteras | 13 ficheros hacen `CREATE DATABASE`; 9 la sueltan al terminar y **4 no**: `test_documents_migration_0024` (1), `test_spec052_migration_0033_legacy` (2), `test_uom_backfill` (7), `test_warehouse_migration_0018` (7) |

## 7. Reproducción y causa raíz

`evidence/pg-test-lifecycle/reproduccion-pre-fix.txt` (`qa/repro-pg-test-residuos.py`, tres
corridas del mismo subconjunto):

| Subconjunto | Tras 1 | Tras 2 | Tras 3 | Pico de conexiones |
|---|---|---|---|---|
| `test_fiscal.py` (21 pruebas, fixture por prueba) | 21 schemas | 42 | 63 · **+532 MB** | 11 en un solo módulo |
| `test_audit_tenant_isolation.py` (fixture de módulo) | 64 | 65 | 66 | 1 |

Conexiones residuales tras cada corrida: 0 — el proceso termina y el sistema las cierra.

| Clasificación | |
|---|---|
| `TEST_SCHEMA_NOT_DROPPED` | **sí** — la causa del crecimiento |
| `TEST_ENGINE_NOT_DISPOSED` | **sí** — la causa del pico de conexiones dentro de una corrida |
| `TEST_FINALIZER_MISSING` · `TEST_RESOURCE_OWNER_UNCLEAR` | **sí** · **sí** |
| `TEST_DATABASE_NOT_DROPPED` | sí, en 4 ficheros; acotado, no acumulativo |
| `TEST_LOGICAL_CLEANUP_OK_PHYSICAL_BLOAT` | secundario: tras soltar 66 schemas a mano, `ktest` quedó en 259 MB y no en 7. Es el catálogo (`pg_class`, `pg_attribute`, `pg_depend`), que conserva su marca de agua; se mide tras el arreglo |
| `TEST_FIXTURE_SCOPE_TOO_NARROW` | observación: un schema por prueba es caro, pero es aislamiento deliberado. No se cambia |
| `TEST_XDIST_RESOURCE_COLLISION` · `TEST_ASYNC_ENGINE_NOT_DISPOSED` · `TEST_EXCEPTION_SKIPS_CLEANUP` | no aplican: sin xdist, sin motores asíncronos, y no hay limpieza que saltarse |
| `UNKNOWN` | 0 |

## 8. `/speckit.specify`

| ID | Requisito |
|---|---|
| FR-054-PGLIFE-001 | Todo lo que la suite crea en PostgreSQL tiene dueño y ciclo de vida explícito: crear → usar → cerrar → soltar → comprobar |
| FR-054-PGLIFE-002 | Todo motor creado por `make_engine` se libera (`dispose`) al terminar el ámbito que lo creó |
| FR-054-PGLIFE-003 | Las conexiones se cierran antes de eliminar el schema que usan |
| FR-054-PGLIFE-004 | Todo schema temporal se elimina al terminar su ámbito; toda base temporal de las pruebas de migración, también |
| FR-054-PGLIFE-005 | La limpieza se ejecuta aunque la prueba falle |
| FR-054-PGLIFE-006 | Repetir un subconjunto no aumenta los schemas huérfanos |
| FR-054-PGLIFE-007 | Repetir un subconjunto no aumenta las conexiones residuales |
| FR-054-PGLIFE-008 | Tras la suite completa, las conexiones vuelven a la línea base |
| FR-054-PGLIFE-009 | La suite completa no exige recrear `ktest` |
| FR-054-PGLIFE-010 | El crecimiento de `ktest` entre la línea base y el final está explicado y acotado |
| FR-054-PGLIFE-011 | Ninguna operación destructiva actúa sobre una base que no sea inequívocamente de prueba, y solo se elimina lo que el propio proceso creó |
| FR-054-PGLIFE-012 | El producto no cambia |
| FR-054-PGLIFE-013 | No se oculta ninguna prueba fallida |
| FR-054-PGLIFE-014 | Sin reintentos, esperas ni omisiones nuevas |
| FR-054-PGLIFE-015 | Hay pruebas que fallan si un motor no se libera, un schema queda huérfano o una conexión queda abierta |
| FR-054-PGLIFE-016 | La ejecución en un solo proceso se conserva; no se introduce ni se desactiva paralelismo |
| FR-054-PGLIFE-017 | La suite sobre SQLite no cambia |
| FR-054-PGLIFE-018 | Los fallos por falta de `clamscan` y `AUTH-ROTACION-SQLITE-HILOS` quedan fuera |

## 9. `/speckit.clarify`

| # | Pregunta | Respuesta, medida |
|---|---|---|
| 1 | Dueña | SPEC054; apoyo SPEC052 |
| 2–3 | Base e identidad | §5 |
| 4–9 | Fixtures, motores, sesiones, schemas | §6 |
| 10 | Nombre de schema | `t_<12 hex>` aleatorio. Se conserva: con un registro por proceso, el azar no impide limpiar |
| 11 | Bases | §6: 4 ficheros sin limpieza |
| 12–15 | xdist, trabajadores, hilos, asíncrono | no · 1 · sí, dentro de la fixture · no |
| 16–17 | Limpieza actual y ausente | `session.close()` · falta `dispose` y `DROP SCHEMA` |
| 18 | Orden | las fixtures de la prueba cierran sus sesiones → `engine.dispose()` → se cuenta y se corta lo que quede conectado a ese schema → `DROP SCHEMA … CASCADE` → se comprueba que ya no existe |
| 19 | Camino de fallo | la limpieza va en el desmontaje de una fixture `autouse`: pytest la ejecuta falle o pase la prueba |
| 20–22 | Línea base | `ktest`: 7 MB, 0 schemas temporales, 0 conexiones |
| 23–24 | Reproducción mínima y completa | §7 · §4 |
| 25 | ¿Fuga o hinchazón? | fuga lógica; la hinchazón del catálogo es secundaria y se mide |
| 26 | ¿Recrear la base es arquitectura o parche? | parche. La arquitectura es un schema por fixture dentro de una base que se reutiliza |
| 27 | ¿Importa el pool? | no se cambia. `NullPool` taparía el defecto: el motor seguiría sin dueño |
| 28 | ¿Importa el paralelismo? | no hay |
| 29–30 | `clamscan` y hilos de SQLite | fuera |
| 31–33 | Pruebas, hostiles, mutaciones | §12 |
| 34 | Clasificación | §13 |

Decisiones de diseño, todas de infraestructura de prueba y de Claude:

- **Dónde vive el ciclo de vida.** No se reescriben las 27 fixtures. `make_engine` registra
  lo que crea en el ámbito abierto, y dos fixtures `autouse` de `conftest.py` —una de
  módulo, otra de función— abren y cierran esos ámbitos. Lo que nace durante una prueba se
  suelta al acabar la prueba; lo que nace en una fixture de módulo, al acabar el módulo.
- **Compuerta de identidad.** Antes de crear o soltar: la URL es la declarada en
  `KONTROL_TEST_DB_URL`; el nombre de la base contiene «test»; no es la base del producto;
  el entorno es `local`, `dev` o `qa`. Y al soltar: el nombre cumple el patrón, lleva la
  marca que el arnés le puso al crearlo y está en el registro de este proceso.
- **Una conexión que una prueba dejó abierta** no impide soltar el schema: se cuenta, se
  informa al final de la corrida y se corta. No se convierte en fallo de la prueba.
- **Un schema que no se pudo soltar** sí es un error, con nombre.

`MATERIAL OQ = 0`. `UNKNOWN = 0`.

## 10. Compuerta constitucional

| | | |
|---|---|---|
| G01–G03 checkpoint, orquestación, dueña | §1, §3 | ✅ |
| G04–G05 identidad de la base y seguridad de lo destructivo | §5, §9 | ✅ |
| G06–G09 dueños de fixtures, motores, sesiones y schemas | §6 | ✅ |
| G10–G12 fuga mínima, repetida y clasificada | §7 | ✅ |
| G13–G15 causa, ciclo de vida y camino de fallo | §7, §9 | ✅ |
| G16 xdist | no existe | ✅ |
| G17 producto | 0 | ✅ |
| G18–G19 `clamscan` y hilos de SQLite fuera | §8 | ✅ |
| G20–G22 pruebas, mutaciones, tareas | §12, §13 | ✅ |
| G23–G25 `MATERIAL OQ`, `UNKNOWN`, trazabilidad | 0 · 0 · 100 % | ✅ |

Principios: 10 (calidad demostrable), 14 (infraestructura reproducible), 15 (datos
protegidos: nada destructivo fuera de una base de prueba), 21 (paridad de motor: la
evidencia en PostgreSQL tiene que poder repetirse), 27. **PASS.**

## 11. `/speckit.plan`

`tests/pg_harness.py` (nuevo): compuerta de identidad, creación de schema con marca,
registro por ámbitos, liberación con comprobación, e informe de residuos.
`tests/conftest.py`: `make_engine` delega en él; dos fixtures `autouse` y un
`pytest_sessionfinish` como red de seguridad. Las 4 pruebas de migración sin limpieza
registran la base que crean. `qa/pg-test-residuos.py`: medida y purga de huérfanos de una
corrida muerta a la fuerza.

Pasos W01–W36 del encargo; W27 (xdist) no aplica.

## 12. Pruebas y mutaciones, diseñadas antes de implementar

| ID | Caso | Req. |
|---|---|---|
| PG-LIFE-01 | al cerrar el ámbito, el motor queda sin conexiones en el servidor | 002 |
| PG-LIFE-02 | al cerrar el ámbito, el schema no existe | 004 |
| PG-LIFE-03 | conexiones: antes, durante y después vuelven a la línea base | 003, 007 |
| PG-LIFE-04 | un módulo real ejecutado tres veces en subproceso: 0 schemas huérfanos y 0 conexiones residuales | 006, 007 |
| PG-LIFE-05 | una prueba que falla a propósito, y otra cuya fixture falla tras crear el motor: se limpia igual | 005 |
| PG-LIFE-06, 07 | xdist — **no aplican** | — |
| PG-LIFE-08 | un módulo de fixture por prueba, en bucle: sin crecimiento lógico | 006 |
| PG-LIFE-09 | lo creado fuera de todo ámbito lo suelta `pytest_sessionfinish` | 001 |
| PG-LIFE-10 | compuerta: URL no declarada, nombre sin «test», entorno `prod`/`staging`/`uat`, base igual a la del producto, no PostgreSQL → se niega | 011 |
| PG-LIFE-11 | en SQLite, `make_engine` devuelve el motor en memoria de siempre y no registra nada | 017 |
| PG-LIFE-12 | `qa/pg-test-residuos.py` informa schemas, tamaño y conexiones | 010 |
| PG-LIFE-13 | una conexión que la prueba deja abierta se cuenta, se corta y el schema se suelta | 003 |
| PG-LIFE-14 | no se suelta un schema sin marca, con otro nombre o que el proceso no creó | 011 |
| PG-LIFE-15 | una base temporal registrada se elimina al cerrar el ámbito | 004 |

| Mutante | Cambio | Debe matarlo |
|---|---|---|
| M-01 | quitar `engine.dispose()` | PG-LIFE-01, 03 |
| M-02 | quitar `DROP SCHEMA` | PG-LIFE-02, 04, 05, 08 |
| M-03 | limpiar solo si la prueba pasa | PG-LIFE-05 |
| M-04 | no cortar la conexión que quedó abierta | PG-LIFE-13 |
| M-05 | nombre global de schema por trabajador — **no aplica** | — |
| M-06 | soltar sin compuerta de identidad | PG-LIFE-10 |
| M-06b | soltar sin comprobar marca ni registro | PG-LIFE-14 |
| M-07 | `make_engine` no registra lo que crea | PG-LIFE-02, 04 |
| M-08 | no soltar la base temporal registrada | PG-LIFE-15 |
| M-09 | sin red de seguridad al acabar la sesión | PG-LIFE-09 |

## 13. `/speckit.tasks` y `/speckit.analyze` previo

| ID | Tarea | Req. | EXECUTOR · MODEL | SEC | EGRESS | Ficheros |
|---|---|---|---|---|---|---|
| T01 | Reconciliación, orquestación, dueñas, evidencia histórica | — | CLAUDE | NO | n-a | — |
| T02 | Medida y reproducción | 006, 010 | CLAUDE | YES | n-a | `qa/pg-test-residuos.py`, `qa/repro-pg-test-residuos.py` |
| T03 | Inventario, causa raíz, ciclo de vida, compuerta, casos y mutantes | todos | CLAUDE | YES | n-a | este documento |
| T04 | Ciclo de vida y compuerta | 001–005, 011 | CLAUDE | YES | n-a | `tests/pg_harness.py`, `tests/conftest.py` |
| T05 | Las 4 pruebas de migración registran su base | 004 | CLAUDE | YES | n-a | 4 ficheros de `tests/` |
| T06 | Pruebas de ciclo de vida contra PostgreSQL y sondas | 015 | CLAUDE | YES | n-a | `tests/test_pg_harness_lifecycle.py`, `tests/sondas_pg/` |
| T10 | Pruebas de la compuerta de identidad (PG-LIFE-10): función pura, sin base | 011 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `tests/test_pg_harness_gate.py` (nuevo) |
| T20 | Auditar, aplicar y probar T10 | — | CLAUDE | NO | n-a | — |
| T21 | Mutaciones | 015 | CLAUDE | YES | n-a | — |
| T22 | Certificación dirigida y repetida | 006–008 | CLAUDE | NO | n-a | — |
| T23 | Suite completa en PostgreSQL con medidas, segunda vuelta, y SQLite | 008–010, 017 | CLAUDE | NO | n-a | — |
| T24 | `analyze` final, trazabilidad, convergencia, hoja de ruta, Git | — | CLAUDE | NO | n-a | documentos |

`RETRY_MAX: 2` en T10. Casi todo es de Claude, y es lo que el encargo pide: diseño del
ciclo de vida, orden de limpieza, seguridad de lo destructivo, y ficheros con URLs de base
de QA. T10 es lo único cerrado y sin ese contexto: casos de una función pura que solo mira
variables de entorno; sus URLs de ejemplo son inventadas y no llevan credenciales.

`analyze` previo: `BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` = 0;
requisitos y tareas huérfanas = 0; `MATERIAL OQ` = 0; `UNKNOWN` = 0; trazabilidad 100 %.

**Autorización de `implement`:** la del encargo `TEST-SCHEMAS-PG-SIN-LIMPIEZA`.

## 14. Implementación

| Fichero | Qué hace |
|---|---|
| `tests/pg_harness.py` (nuevo) | la compuerta de identidad; `crear_motor_de_prueba`, que crea el schema, lo firma con un comentario y da a sus conexiones un `application_name` propio; el registro por ámbitos; `soltar_schema` y `soltar_base`, que liberan y **comprueban** |
| `tests/conftest.py` | `make_engine` delega en `pg_harness` cuando la URL es de PostgreSQL —en SQLite sigue igual—; dos fixtures `autouse`, de módulo y de función, abren y cierran los ámbitos; `pytest_sessionfinish` es la red de seguridad y `pytest_terminal_summary` cuenta lo que no cuadra |
| 4 pruebas de migración | una línea cada una: `registrar_base(nombre)` tras su `CREATE DATABASE` |
| `tests/test_pg_harness_lifecycle.py`, `tests/sondas_pg/` (nuevos) | PG-LIFE-01..15: 28 pruebas, 26 de ellas solo en PostgreSQL |
| `tests/test_pg_harness_gate.py` (nuevo, T10) | la compuerta: 43 casos, sin base de datos |
| `qa/pg-test-residuos.py`, `qa/repro-pg-test-residuos.py` (nuevos) | medida de residuos, purga de huérfanos de una corrida muerta a la fuerza, y la reproducción |

Las 27 fixtures que llaman a `make_engine` **no se tocaron**. Producto: 0 ficheros.

### El orden de la limpieza, medido

```
la fixture de la prueba cierra su sesión                 (ya lo hacía)
→ engine.dispose()                                        cierra las conexiones del pool
→ ¿queda alguien conectado a ese schema?                  se ve por application_name
     sí → se anota en el informe y se corta               es una conexión que la prueba no cerró
→ DROP SCHEMA "t_…" CASCADE                               con lock_timeout de 30 s: nunca se cuelga
→ ¿sigue existiendo?  sí → ResiduoDePrueba                error con nombre
```

Antes de crear y antes de soltar pasa la compuerta. Antes de soltar, además: el nombre
cumple `t_<12 hex>`, el schema lleva la marca del arnés y está en el registro del proceso.

### Orquestación

```
TASKS TOTAL 12 · CLAUDE_ONLY 11 · DEEPSEEK_ELIGIBLE 1 · DEEPSEEK EXECUTED 1
DEEPSEEK CALLS 1 · RETRIES 0 · PATCHES ACCEPTED 1 · REJECTED 0 · retocados a mano 0
MODELS USED deepseek-v4-flash · DEEPSEEK TOKENS 3 406 / 2 416 · COST $0.0011
SONNET BRIDGE TOKENS 32 960
```

T10 pasó la auditoría a la primera: las 13 pruebas (43 casos) son las diseñadas. El puente
no leyó ningún fichero y envió el encargo entero.

**Una desviación de egress, de Claude.** Las URLs de ejemplo del encargo llevaban el
servidor, el puerto y el nombre de la base de QA local (`localhost:55432/ktest`), y este
ciclo pedía no enviar URLs de QA. No llevaban usuario real ni contraseña y esa misma
dirección está escrita en `.claude/CLAUDE.md`: no es un secreto. Pero es una desviación de
la regla, y debieron usarse un servidor y un puerto inventados.

## 15. Mutaciones

`evidence/pg-test-lifecycle/mutaciones.txt`: **21 de 21 muertos**, `GOOD → PASS` y
`RESTORED → PASS`.

| Mutante | Lo matan |
|---|---|
| M-01 sin `engine.dispose()` | PG-LIFE-01, 04 |
| M-02, M-02b sin `DROP SCHEMA` (con y sin comprobación) | PG-LIFE-02, 04, 05, 08, 09 y más |
| M-03 limpiar solo si la prueba pasó | PG-LIFE-05 |
| M-04 no cortar la conexión olvidada | PG-LIFE-13, 13b |
| M-05 nombre de schema por trabajador | **no aplica**: no hay xdist |
| M-06, M-06a eliminar o crear sin compuerta | PG-LIFE-10b · PG-LIFE-10 |
| M-06b, M-06c eliminar sin comprobar marca o nombre | PG-LIFE-14b · PG-LIFE-14 |
| M-07 `make_engine` no apunta lo que crea | PG-LIFE-01 y diez más |
| M-08, M-08b la base temporal no se elimina; cualquier nombre vale | PG-LIFE-15 · 15b |
| M-09 sin red de seguridad | PG-LIFE-09 |
| M-10, M-11 sin ámbito de módulo o de prueba | PG-LIFE-08 · PG-LIFE-04 |
| M-12 sin `application_name` · M-13 sin marca | PG-LIFE-01, 03, 13 · doce pruebas |
| M-14 a M-17 la compuerta acepta cualquier nombre, entorno, base de producto o URL | GATE-05 · 07 · 09, 11 · 02, 03 |

En la primera versión de las pruebas M-01, M-10 y M-11 habrían sobrevivido: sin `dispose`
la conexión se cortaba igual desde el servidor, y sin ámbitos todo se soltaba al final. Se
añadieron las aserciones que lo distinguen —«se cerró por las buenas» y «solo vive un
schema de este proceso»— antes de correr las mutaciones.

## 16. Resultados

### Dirigido: el mismo subconjunto, tres corridas

| | Antes | Después |
|---|---|---|
| `test_fiscal.py`: schemas tras 1, 2 y 3 corridas | 21 · 42 · 63 | **0 · 0 · 0** |
| Pico de schemas vivos | 63 | **1** |
| Pico de conexiones | 11 | **1** |
| `test_audit_tenant_isolation.py`: schemas tras 3 corridas | +3 | **0** |
| Bases enteras que dejan las 4 suites de migración | 17 (319 MB) | **0** |

### Suite completa en PostgreSQL, dos veces seguidas, sin recrear la base

`evidence/pg-test-lifecycle/suite-completa-postgresql.txt`. `pytest tests -rfE`, un proceso,
sobre `ktest` recién creada para que la medida sea comparable con las históricas.

| | Última corrida anterior (`3ea8d66`) | Corrida 1 | Corrida 2 |
|---|---|---|---|
| Resultado | 1 666 pasan · 37 fallan · 27 omitidas | 1 737 · **37** · 27 | 1 737 · **37** · 27 |
| Schemas al terminar | 313 | **0** | **0** |
| Pico de schemas vivos | 313 | **1** | **1** |
| Tamaño de `ktest` al terminar | 3 240 MB | 185 MB | **171 MB** |
| Pico de tamaño | 3 240 MB | 318 MB | 338 MB |
| Pico de conexiones | 60 de 100 | **5** | **5** |
| Conexiones al terminar | — | 0 | 0 |
| Mínimo libre en el `tmpfs` | 2,5 G | 5,4 G | 5,3 G |
| Duración | 17 min 37 s | 10 min 56 s | 10 min 28 s |
| ¿Hubo que recrear `ktest`? | sí | no | no |

- **No hay acumulación.** La segunda corrida termina con la base más pequeña que la primera.
- **Los 37 fallos son el mismo conjunto que sobre `3ea8d66`**, prueba a prueba, en las dos
  corridas: documentos, por falta de `clamscan` (`PREEXISTING_ENVIRONMENT_CLAMSCAN`). Fallos
  nuevos: 0. Pruebas nuevas que pasan: 71.
- **Ninguna prueba de la suite deja conexiones abiertas**: la sección de recursos del
  resumen de pytest no aparece en ninguna corrida. Tampoco hubo nada que no se dejara soltar.
- **La base sigue sirviendo**: una suite nueva corrió después sobre la misma `ktest`, 15/15.
- **Las 17 bases temporales** de las pruebas de migración ya no están: en el servidor quedan
  `kaud`, `ktest` y `postgres`.
- De propina, la suite tarda siete minutos menos: ya no arrastra trescientos schemas.

### Fuga lógica frente a hinchazón física

Los 171 MB que quedan son **catálogo** (`pg_class`, `pg_attribute`, `pg_depend`): la suite
crea y suelta unas 350 000 relaciones por corrida y esas tablas conservan su marca de agua.
Es espacio que PostgreSQL reutiliza —por eso la segunda corrida no crece— y que
`autovacuum` va devolviendo: minutos después de terminar, `ktest` pesaba 142 MB. No hay
schemas, ni relaciones (413, las de una base vacía), ni conexiones. Se registra como
observación, no como residuo.

### SQLite

`pytest tests`: 790 pasan, 968 omitidas, **43 fallan**. Es el mismo conjunto que sobre
`3ea8d66`, prueba a prueba: 42 de documentos por falta de `clamscan`
(`PREEXISTING_ENVIRONMENT_CLAMSCAN`) y `test_auth_session_rotation`
(`PREEXISTING_SQLITE_THREAD_FLAKE`). 45 pruebas nuevas pasan y 26 nuevas se omiten por ser
de PostgreSQL. La sección «recursos de prueba en PostgreSQL» no aparece: en SQLite el arnés
no apunta nada.

### E2E

No se ejecuta: este delta no cambia producto y la compuerta de la SPEC054 no lo exige.

## 17. `/speckit.analyze` final

| Contador | Exigido | Medido |
|---|---|---|
| Schemas huérfanos tras la suite | 0 | **0** (dos corridas) |
| Conexiones residuales | 0 | **0** |
| Motores sin liberar | 0 | 0 — todo motor de `make_engine` pasa por el registro |
| Bases temporales sin soltar | 0 | 0 de 17 |
| Recreación manual de `ktest` | no | no |
| Multiplicación de tamaño por corrida | no | no: 185 MB → 171 MB |
| Operación destructiva sin compuerta | 0 | 0 |
| Ficheros de `app/` · frontend · migraciones | 0 | 0 · 0 · 0 |
| Reintentos, esperas, omisiones para ocultar fallos | 0 | 0 — las 26 omisiones nuevas son pruebas de PostgreSQL bajo SQLite, la convención de la suite |
| Fallos ocultos | 0 | 0 — los 37 y los 43 siguen fallando y son los mismos |
| Paralelismo cambiado · pool cambiado · `gc` como contrato | no | no · no · no |
| Ramas creadas | 0 | 0 |
| `BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` | 0 | 0 |
| `MATERIAL OQ` · `UNKNOWN` | 0 | 0 · 0 |

## 18. Trazabilidad

| Requisito | Prueba o evidencia |
|---|---|
| FR-054-PGLIFE-001 | PG-LIFE-01, 02, 09, 09b; M-07, M-09 |
| 002 | PG-LIFE-01, 03; M-01 |
| 003 | PG-LIFE-03, 13, 13b; M-04, M-12 |
| 004 | PG-LIFE-02, 08, 15; M-02, M-08, M-10, M-11; 17 → 0 bases |
| 005 | PG-LIFE-05; M-03 |
| 006 | PG-LIFE-04, 08; reproducción dirigida 21·42·63 → 0·0·0 |
| 007 | PG-LIFE-03, 04 |
| 008 | suite completa: 0 conexiones al terminar, dos veces |
| 009 | segunda corrida y suite posterior sobre la misma base |
| 010 | suite completa: 318 y 338 MB de pico, 171 MB al final; §16, catálogo |
| 011 | GATE-01..13; PG-LIFE-10, 10b, 14, 14b, 14c, 15b; M-06, M-06a, M-06b, M-06c, M-08b, M-14..M-17 |
| 012 | `git diff --stat`: 0 ficheros fuera de `tests/`, `qa/`, `specs/` y `docs/` |
| 013 | PG-LIFE-05 (la sonda sigue fallando); conjuntos de fallos idénticos a la base |
| 014 | `analyze` final |
| 015 | PG-LIFE-01..15 y 21 mutantes |
| 016 | sin xdist antes y después |
| 017 | PG-LIFE-11, 11b; suite completa en SQLite con el mismo conjunto de fallos |
| 018 | §16: `clamscan` y hilos de SQLite, clasificados y sin tocar |

**18/18.** Cada tarea → ejecutor → auditoría → prueba → evidencia: §13, §14 y
`orquestacion.txt`.

## 19. Observaciones registradas, no corregidas

| | |
|---|---|
| **`TEST-PG-UN-SCHEMA-POR-PRUEBA`** (nueva) | trece suites crean un schema entero —1 129 relaciones— por cada prueba. Ya no se queda, pero sigue siendo lo más caro de la corrida y lo que hincha el catálogo. Pasar esas fixtures a ámbito de módulo cambia el aislamiento de las pruebas: es otra decisión |
| **`TEST-PG-CATALOGO-MARCA-DE-AGUA`** (nueva) | tras una corrida completa `ktest` pesa ~170 MB de catálogo reutilizable. No crece entre corridas. Solo importaría con un volumen mucho menor |
| **`ENTORNO-SIN-CLAMSCAN`** (se registra ahora) | la máquina de QA no tiene `clamscan`: 37 pruebas de documentos fallan en PostgreSQL y 42 en SQLite, siempre las mismas. Estaba anotado en la evidencia de varios ciclos y no en la hoja de ruta |
| `AUTH-ROTACION-SQLITE-HILOS` | sigue OPEN; volvió a caer en SQLite |
| Compuerta: el nombre de la base debe contener «test» | es una regla nueva del arnés. Quien use otra base de prueba tendrá que llamarla en consecuencia; la regla falla antes de crear nada y dice por qué |
| Corridas muertas a la fuerza (`kill -9`) | no ejecutan desmontajes: dejan sus schemas. `qa/pg-test-residuos.py --purgar` los elimina, y solo los que llevan la marca del arnés y a los que nadie sigue conectado |

## 20. Convergencia

| | |
|---|---|
| Causa raíz | demostrada: schema y motor sin dueño |
| Ciclo de vida | crear → usar → cerrar → soltar → comprobar, en un solo sitio |
| Dirigido · mutaciones | 71/71 en PostgreSQL, 45/45 en SQLite · 21/21 |
| Suite completa PostgreSQL | dos corridas: 0 schemas, 0 conexiones, sin recrear la base, mismos 37 fallos de entorno |
| Suite completa SQLite | mismos 43 fallos que la base |
| Producto | sin cambios |
| `MATERIAL OQ` · `UNKNOWN` · trazabilidad | 0 · 0 · 100 % |

**`TEST-SCHEMAS-PG-SIN-LIMPIEZA`: CLOSED / CONVERGED — 2026-10-01.** Master 56: 56 filas,
sin cambio de estado.
