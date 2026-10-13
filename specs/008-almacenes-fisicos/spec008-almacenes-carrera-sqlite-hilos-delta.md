# SPEC 008 · Delta dirigida — ALMACENES-CARRERA-SQLITE-HILOS

Dueña: Spec 008 (almacenes físicos: la prueba y el servicio son suyos). Apoyo: Spec 054 (el arnés de backend,
`tests/conftest.py`, recibe la primitiva; enlace cruzado en
`specs/012-auditoria-integral-e2e/spec054-e2e-flaky-delta.md`). Fecha: 2026-10-13. Rama `develop`, HEAD de partida
`ffdbaf6`. Producto 0, migraciones 0, esquema 0. Evidencia en `evidence/almacenes-carrera-sqlite-hilos/`.

Encargo: `tests/test_warehouse_structure.py::test_concurrencia_de_codigo_resuelta_por_constraint` falla de forma
intermitente, solo en SQLite. Primero reproducir, luego la topología de conexiones, luego la causa raíz y una
clasificación con compuerta; solo entonces una corrección, y solo del arnés. Sin `retry`, `sleep`, `skip`, `xfail`,
inflado de `timeout`, reordenación ni cerrojos en la prueba.

## 1. Checkpoint — `evidence/.../checkpoint.md`

`EXPECTED_HEAD = ACTUAL_HEAD = REMOTE_HEAD = ffdbaf6`, `develop`, árbol limpio, 0 bases de corrida E2E, 0 schemas
`t_` residuales, 0 directorios temporales del arnés, puertos 8000/8010/5173 libres. MASTER57 = 57, SPEC057 PLANNED /
NOT STARTED, NEXT MASTER SPEC NOT YET PRIORITIZED. Producción fuera de alcance.

## 2. Descubrimiento

### 2.1 Prueba, servicio y restricción — `target-test-and-service.md`

La prueba lanza dos hilos con `Barrier(2)` contra `POST /organization/locations` (mismo almacén, mismo código) sobre la
`TestClient` del módulo y exige `sorted(results) == [200, 409]` y una sola fila. `create_location_full` hace `db.add`,
`db.commit()` y traduce **solo** `IntegrityError` a 409 `LOCATION_CODE_DUPLICATE` (`_integrity()`, sin
`es_violacion_unica`). La restricción es `uq_warehouse_locations_wh_code (warehouse_id, code)` (migración 0017). El
fixture de módulo monta `make_engine()` → SQLite `:memory:` + `StaticPool` + `check_same_thread=False`.

### 2.2 P21 recuperado físicamente — `p21-authority.md`

P21 exige PostgreSQL para la evidencia de integración y acota las excepciones a pruebas que no ejerciten el dialecto; P25
exige que una prueba de concurrencia fuerce la carrera y no acepte un 500. **P21 no excluye SQLite** para esta prueba: ya
corre en SQLite en la suite por defecto y debe hacerlo bien o no correr; `skip` está prohibido por el encargo.

### 2.3 Reproducción y frecuencia — `frequency-study.md`, `frequency-series-before.txt`

Sola ×20: 8 fallos (`[200]` ×6, `[]` ×1, `[409]` ×1). Sola con sonda ×20: 4. Módulo ×10: 4, siempre la misma prueba.
Suite completa: ya manifestada en ciclos anteriores (43/1582), no se repite antes de corregir (plan acotado).

### 2.4 Topología — `connection-topology.md` (`CONNECTION_TOPOLOGY = PROVEN`)

Sonda de eventos de motor con ids sintéticos: **una única conexión DBAPI C1** para el hilo principal y los hilos de
`TestClient` T3–T6 en 20/20 corridas. Cada petición abre su `Session`, pero todas se apoyan en la misma `sqlite3.Connection`.

### 2.5 Firmas — `failure-signatures.md` (`UNKNOWN = 0`)

F1 (500 inesperado: `ResourceClosedError` o `sqlite3.DatabaseError` donde se esperaba `IntegrityError`) → F7 → el hilo
muere al relanzar `TestClient` → F3/F9 (`[200] == [200, 409]`). Nunca F6 (`database is locked`). Variante: `[409]` con
total 0 (el `rollback` del perdedor deshace la fila del ganador sobre la misma conexión).

### 2.6 Entrelazado controlado y POC de mismo datastore — `controlled-interleaving.md`, `same-datastore-poc.md`

Barrera en `before_cursor_execute` antes de cada `INSERT INTO warehouse_locations` (instrumentación, no corrección):
topología actual **5/5 fallos deterministas**; fichero temporal con una conexión por hilo **5/5 `[200, 409]`**. Natural
×30: 17/30 fallos frente a 0/30. En la topología de fichero se verifica antes que dos conexiones crudas son objetos
distintos y que B lee lo que A confirmó (regla de mismo datastore; `:memory:` privado por conexión descartado).

## 3. Causa raíz y compuerta de clasificación — `root-cause.md`

`ROOT_CAUSE_CLASS = HARNESS_SHARED_CONNECTION`. `StaticPool` + `:memory:` + `check_same_thread=False` hacen que dos
peticiones concurrentes compartan la misma conexión pysqlite; el `commit` de una cierra el cursor de la otra o su
`rollback` deshace la fila ajena. Descartados con evidencia: `HARNESS_STATE_LEAK` (falla sola en proceso nuevo),
`SQLITE_LOCKING_SEMANTICS` (nunca `database is locked`; con una conexión por hilo el bloqueo se resuelve dentro del
`busy_timeout` por defecto), `PRODUCT_DEFECT` (PostgreSQL 5/5 y fichero SQLite 35/35; el producto nunca comparte una
conexión entre peticiones), `POSTGRESQL_ONLY_CONTRACT` (P21 no lo exige; `skip` prohibido). **No hay STOP**: la
corrección autorizada es de arnés.

Observaciones registradas, no absorbidas (`OBSERVACIONES.md`): `_integrity()` traduce cualquier `IntegrityError`
(dueña 008); otros cuatro módulos SQLite lanzan hilos contra la app sobre `StaticPool` (`test_auth_session_rotation`,
ya `AUTH-ROTACION-SQLITE-HILOS`; `test_uom_conversion`; `test_documents_security`; `test_roles_create` y
`test_picklist_duplicada` evitan la carrera en SQLite con `skipif(not PG)`).

## 4. `/speckit.specify` — requisitos

| Id | Requisito |
|---|---|
| FR-01 | El arnés ofrece una primitiva para módulos que ejecutan hilos contra la app: en SQLite, un datastore en fichero temporal efímero con una conexión DBAPI por hilo concurrente; en PostgreSQL, el motor de `make_engine()` sin cambios |
| FR-02 | La primitiva no fija `timeout`/`busy_timeout`, `isolation_level` ni `PRAGMA`; `connect_args` se limita a `check_same_thread=False` |
| FR-03 | El fichero y su directorio se eliminan al salir del contexto, pase o falle lo de dentro, y el motor queda `dispose()`ado |
| FR-04 | `make_engine()` por defecto no cambia (`:memory:` + `StaticPool`) |
| FR-05 | `tests/test_warehouse_structure.py` monta su mundo con la primitiva; la prueba objetivo no cambia (mismas aserciones, misma `Barrier(2)`) |
| FR-06 | Producto, migraciones y esquema: 0 cambios (`git diff --stat -- app/ alembic/` vacío) |
| FR-07 | Pruebas de arnés ACS-01…08 que certifican topología, mismo datastore, aislamiento, entrelazado controlado, bloqueo ≠ duplicado, limpieza y contrato estático, sin `skip` y en los dos motores |
| NFR-01 | Sin `retry`, `sleep`, `skip`, `xfail`, cerrojos en la prueba, reordenación ni inflado de tiempos |
| NFR-02 | Sin migración, sin dependencia nueva, sin secretos ni rutas reales en la evidencia |

Criterios de aceptación: AC-01 prueba sola ×20 SQLite 20/20; AC-02 módulo ×10 SQLite 10/10; AC-03 prueba sola ×20
PostgreSQL 20/20; AC-04 ACS-01…08 verdes en SQLite y PostgreSQL; AC-05 suites completas SQLite ×2 y PostgreSQL ×1 sin
regresión frente a la línea base; AC-06 E2E global ×1 limpia; AC-07 mutaciones M-01…M-12 GOOD→PASS, MUTATED→FAIL,
RESTORED→PASS (equivalentes declaradas); AC-08 0 ficheros `kontrol-test-sqlite-*` tras cada corrida.

## 5. `/speckit.clarify`

| Pregunta | Respuesta | Fuente |
|---|---|---|
| ¿`make_engine(concurrente=True)` o primitiva aparte? | Gestor de contexto aparte, `motor_para_hilos(nombre)`: el ciclo de vida (crear/eliminar fichero) pide un ámbito explícito; `make_engine()` no tiene ámbito y no debe aprender a limpiar | diseño |
| ¿Dónde vive el fichero? | `tempfile.mkdtemp(prefix="kontrol-test-sqlite-<nombre>-")` en el tmp del sistema, eliminado al salir; no se mezcla con la raíz del volumen de instalación (otra responsabilidad) | diseño |
| ¿Se toca `busy_timeout`? | No: la POC resuelve 35/35 con el defecto del driver (5,0 s) y la espera real es de milisegundos | POC |
| ¿Adoptan la primitiva los otros módulos con hilos? | No en este ciclo: cada uno es de su dueña y tiene su propia aserción; se registran como observación | encargo (no absorber) |
| ¿Hace falta PostgreSQL ×2 o E2E ×2? | PostgreSQL ×1 y E2E ×1 (el encargo); SQLite ×2 porque es el motor donde se manifestaba | encargo |

`MATERIAL OQ = 0`.

## 6. `/speckit.plan`

T01 primitiva en `tests/conftest.py` → T02 adopción en `tests/test_warehouse_structure.py` → T03
`tests/test_motor_para_hilos.py` (ACS-01…08) → T04 verificación dirigida (AC-01…04) → T05 mutaciones → T06 suites
completas y E2E → T07 cierre (roadmap, puntero, recuento, commit y push). Todo `CLAUDE_ONLY`: concurrencia y arnés
compartido son `CLAUDE_ONLY` por política; `DEEPSEEK CALLS = 0` (no hay tarea mecánica con contrato cerrado que compense
una delegación: cada cambio es de diseño de concurrencia o de prueba de concurrencia).

## 7. CONSTITUTION GATE

`BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`; requisitos y tareas sin huérfanos; `MATERIAL OQ = 0`;
`UNKNOWN = 0`; trazabilidad 100 % (§9). P21 respetado (PostgreSQL certifica; SQLite no se excluye ni se degrada). P25
respetado (la prueba sigue forzando la carrera y sigue sin aceptar 500). P2: autorización de `implement` = la del encargo
`ALMACENES-CARRERA-SQLITE-HILOS`. Sin migración, sin cambio de producto, sin rama nueva. **GATE: PASS.**

## 8. `/speckit.tasks`

| Tarea | Ficheros | EXECUTOR / MODEL | SECURITY_SENSITIVE / EGRESS_SAFE | TEST | DONE_WHEN |
|---|---|---|---|---|---|
| T01 primitiva `motor_para_hilos` | `tests/conftest.py` | CLAUDE / n-a | no / n-a | ACS-01…08 | FR-01…04 |
| T02 adopción | `tests/test_warehouse_structure.py` (solo el fixture `_app_client`) | CLAUDE / n-a | no / n-a | ACS-09/10 | FR-05 |
| T03 pruebas de arnés | `tests/test_motor_para_hilos.py` (nuevo) | CLAUDE / n-a | no / n-a | ACS-01…08 ×2 motores | FR-07 |
| T04 verificación dirigida | — | CLAUDE | — | AC-01…04 | series en `frequency-series-after.txt` |
| T05 mutaciones | copias temporales | CLAUDE | — | M-01…M-12 | `mutations.md` |
| T06 suites y E2E | — | CLAUDE | — | AC-05, AC-06 | `full-suites.md`, `e2e.md` |
| T07 cierre | roadmap, puntero, recuento, `OBSERVACIONES.md` | CLAUDE | — | — | commit + push, árbol limpio |

## 9. `/speckit.analyze` previo y trazabilidad

| Requisito | Tarea | Prueba |
|---|---|---|
| FR-01 | T01 | ACS-01, ACS-02, ACS-04 |
| FR-02 | T01 | ACS-08 |
| FR-03 | T01 | ACS-06, ACS-07 |
| FR-04 | T01 | suites completas (AC-05), ACS-08 |
| FR-05 | T02 | ACS-09, ACS-10, ACS-11, ACS-08 (texto de la prueba objetivo intacto) |
| FR-06 | T07 | `git diff --stat -- app/ alembic/` (AC-05) |
| FR-07 | T03 | ACS-01…08 |
| NFR-01 | T01–T03 | ACS-08, revisión del diff |
| NFR-02 | T07 | barrido de secretos de la evidencia |

Huérfanos 0 · contradicciones 0 · `MATERIAL OQ = 0` · `UNKNOWN = 0` · **trazabilidad 100 %**. Autorización expresa:
la del encargo. Implementación a continuación.

## 10. `/speckit.implement` — por tarea

### T01 · `tests/conftest.py` (CLAUDE_ONLY)

`[ANALYZE]` contrato FR-01…04; invariantes: `make_engine()` intacto, nada de tiempos ni `PRAGMA`, limpieza en `finally`.
`[PLAN]` constante `PREFIJO_DE_SQLITE = "kontrol-test-sqlite-"` y gestor de contexto `motor_para_hilos(nombre) ->
Iterator[Engine]` tras `make_engine()`; import `from sqlalchemy.engine import Engine` en la cabecera. `[CLASSIFY]`
CLAUDE_ONLY (diseño de concurrencia del arnés compartido). `[EXECUTE]` Claude. `[AUDIT]` PASS: 42 líneas añadidas, sin
dependencias nuevas, sin cambio de esquema. `[TEST]` `ruff check` limpio; ACS-01…08 verdes en SQLite y PostgreSQL (§11).
`[STATUS]` COMPLETE.

### T02 · `tests/test_warehouse_structure.py` (CLAUDE_ONLY)

`[PLAN]` el fixture de módulo `_app_client` envuelve su cuerpo en `with motor_para_hilos("warehouse-structure") as engine:`
(mismo cuerpo, sangrado un nivel; comentario de tres líneas con el porqué); import `motor_para_hilos` en lugar de
`make_engine`. La prueba objetivo no cambia. `[AUDIT]` PASS: `git diff` de 69 líneas, todas de sangrado salvo el `with`,
el comentario y el import. `[TEST]` prueba sola ×20 y módulo ×10 en SQLite, prueba sola ×20 en PostgreSQL (§11).
`[STATUS]` COMPLETE.

### T03 · `tests/test_motor_para_hilos.py` (CLAUDE_ONLY, nuevo)

ACS-01…08 según `design.md`; `PLAZO = 10` s como tope de las barreras (una prueba que lo agota falla, no espera);
`_en_hilos` devuelve las excepciones que matan a los hilos para que un 500/`ResourceClosedError` sea visible en la
aserción y no un «faltan resultados» (OBS-03). ACS-05 usa `sqlite3` de la biblioteca estándar y un motor propio con
`timeout=0` (bloqueo inmediato; no es la primitiva). ACS-08 escanea el **código** de la primitiva sin su docstring y el
texto de la prueba objetivo (`Barrier(2)`, `sorted(results) == [200, 409]`, `total == 1`, sin `sleep/Lock/retry/skip/
xfail/timeout/or len(results)`) y exige la barrera de ACS-04. Una iteración: la primera versión de ACS-08 escaneaba
también el docstring (que nombra `timeout` para decir que no se toca) y fallaba; se excluyó el docstring. `[AUDIT]`
PASS. `[TEST]` 8/8 en SQLite y en PostgreSQL. `[STATUS]` COMPLETE.

`DEEPSEEK CALLS = 0` (todas las tareas son CLAUDE_ONLY: concurrencia y arnés compartido).

## 11. Resultados

| Gate | Resultado | Evidencia |
|---|---|---|
| AC-01 prueba sola ×20 SQLite | 20/20 (antes 8/20 fallos) | `frequency-series-after.txt` |
| AC-02 módulo ×10 SQLite | 10/10 (antes 4/10 fallos) | ídem |
| AC-03 prueba sola ×20 PostgreSQL | 20/20 | ídem |
| AC-04 ACS-01…08 | 8/8 SQLite · 8/8 PostgreSQL; suites de almacenes + ACS en PostgreSQL 116/116 | `acs-results.md` |
| AC-05 suites completas | SQLite 1616/43/1040 ×2 (43 = 42 ClamAV + `AUTH-ROTACION-SQLITE-HILOS`, preexistente: 8/10 sin el ciclo); PostgreSQL 2634/37/28 (35 ClamAV + 2 n9), 0 nuevos; `git diff --stat -- app/ alembic/` vacío | `full-suites.md`, `auth-rotation-attribution.txt` |
| AC-06 E2E global ×1 | 280 passed · 4 skipped, limpieza LIMPIA | `e2e.md` |
| AC-07 mutaciones | 12/12 detectadas (M-04 solo estáticamente: equivalente en comportamiento, SQLAlchemy 2.0 ya fija `check_same_thread=False` en fichero); GOOD→PASS, MUTATED→FAIL, RESTORED→PASS | `mutations.md` |
| AC-08 limpieza | 0 `kontrol-test-sqlite-*` tras cada serie, suite, mutación y E2E; 0 bases de corrida; 0 schemas `t_`; puertos libres | `full-suites.md`, `e2e.md` |
| Gates estáticos | `ruff check` limpio; `mypy` 154 errores, todos de `app/` (línea base; 0 en los ficheros de prueba tocados) | `acs-results.md` |
| P21 / P25 | PostgreSQL certifica (20/20, suite completa); la prueba sigue forzando la carrera y sin aceptar 500 | `p21-authority.md`, `p25-check.md` |

Incidencias del ciclo (todas de medición, ninguna de producto): primera serie etiquetada mal por el `-q` doble de pytest
(parada y repetida); un directorio `kontrol-test-sqlite-*` y uno `kontrol-test-license-*` huérfanos del proceso matado,
eliminados a mano; primera POC con códigos de almacén repetidos entre modos (`KeyError`, corregida).

## 12. `/speckit.analyze` final, trazabilidad y veredicto

FR-01…07 y NFR-01/02 cubiertos por T01–T07 con sus pruebas (§9), sin huérfanos; `MATERIAL OQ = 0`; `UNKNOWN = 0`;
`CONTRADICTIONS = 0`; producto 0, migraciones 0, dependencias 0, rama `develop`. Convergencia: la deuda
`ALMACENES-CARRERA-SQLITE-HILOS` pasa a **CLOSED / CONVERGED** (2026-10-13); `AUTH-ROTACION-SQLITE-HILOS` sigue OPEN con
la causa raíz presumible anotada; OBS-01…03 registradas para sus dueñas. MASTER57 = 57; SPEC057 PLANNED / NOT STARTED;
NEXT MASTER SPEC NOT YET PRIORITIZED. Producción fuera de alcance, sin tocar.

Cierre por delta: tareas 7 · `CLAUDE_ONLY` 7 · `DEEPSEEK_ELIGIBLE` 0 · ejecutadas por DeepSeek 0 · reintentos 0 · parches
rechazados/aceptados 0/0 · implementadas por Claude 3 (T01–T03, las tres enteras) · pruebas nuevas 8 (ACS-01…08) + 50
corridas dirigidas + 3 suites completas + 1 E2E · mutaciones 12/12 · regresiones 0 · coste de DeepSeek $0.
