# SPEC 054 · Delta dirigida — TEST-PG-UN-SCHEMA-POR-PRUEBA

**Fecha** 2026-10-13 · **Dueña** SPEC054 (`specs/012-auditoria-integral-e2e`; arnés de pruebas de backend) ·
**Apoyo** SPEC001 (`Base.metadata`, modelos), SPEC004/010 (suites de licencia con `db_session`), SPEC052 (el runner E2E
migra con Alembic: no cambia) · **Antecedente** `spec054-pg-test-lifecycle-delta.md` §19 (donde nació la deuda; PGLIFE
sigue siendo la autoridad del ciclo de vida) y `spec054-test-volumen-de-instalacion-compartido-delta.md` (patrón de
sondas en procesos aparte) · **Base** `805074c` · **Rama** `develop` · **Evidencia** `evidence/test-pg-un-schema-por-prueba/`

Ciclo de arnés: **producto 0**. Discovery-first, benchmark antes del diseño, POC antes de implementar; sin relajar el
aislamiento, sin omitir ni reordenar pruebas, sin `sleep` ni reintentos.

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` | `805074c` / `805074c` / `805074c` — coinciden |
| `ACTUAL_BRANCH` · `WORKTREE_STATE` · `COMMITS_AFTER_805074C` · `RUN_DATABASES` · `TEMP_TEST_DIRS` | `develop` · limpio · 0 · 0 · 0 |
| Puertos 8000/8010/5173 · MASTER57 / SPEC057 / NEXT MASTER SPEC | libres · 57 · PLANNED / NOT STARTED · NOT YET PRIORITIZED |

## 2. Descubrimiento

### 2.1 Las suites — `evidence/.../suite-inventory.md`

**12 suites `db_session`** de ámbito de función, 214 pruebas, patrón idéntico (`make_engine` → `init_models` →
`create_all` → `sessionmaker` → siembra → `yield` → `close`): `test_services`, `test_approvals`, `test_treasury`,
`test_fiscal`, `test_inventory`, `test_sales`, `test_maestros`, `test_homologation`, `test_purchasing`, `test_reporting`,
`test_licensing_central`, `test_regulatory`. Commits: en la fixture (`sembrar_empresas` + `commit` en 3), en pruebas
(`test_maestros` 7, `test_licensing_central` 2) y en el producto (`initialize`, `import_license`, `sync_license`…: 332
`commit()` en `app/`), **todos sobre la sesión principal de la prueba**. Sesiones secundarias 0 · `TestClient`/`overrides`
0 · hilos 0 · `engine.connect/begin` 0 · DDL en prueba 0 · secuencias/identidades en modelos **0** (claves de cadena).
Clasificación: 6 `ROLLBACK_SAFE` + 6 `COMMIT_WITHIN_MAIN_SESSION`; `UNKNOWN 0`. Otras 5 fixtures de función que crean
motor (43 pruebas: `test_installation_key_reference` y `central/test_central_authority` con `TestClient` y sesiones
secundarias; `test_license_import_race` y `test_license_revision_race` con hilos; `test_volumen_de_instalacion_ambito`
con una sola creación) quedan **fuera del mecanismo**, con razón explícita (§4). La hoja de ruta decía «trece»: son 12 + 5.

### 2.2 El arnés — `evidence/.../harness-map.md`

`make_engine` → `pg_harness.crear_motor_de_prueba` (schema `t_<12 hex>` con marca y `search_path` en `connect_args`) →
`create_all` en la fixture → PGLIFE apunta el schema al ámbito abierto (prueba o módulo) y lo suelta al cerrarlo
(`soltar_schema`: dispose, corta conexiones, `DROP … CASCADE`, comprueba). Módulo ya soportado por PGLIFE. SQLite:
`sqlite+pysqlite:///:memory:` con `StaticPool`, base nueva por motor (milisegundos).

### 2.3 Relaciones por schema y catálogo — `evidence/.../relations-per-schema.md`

203 tablas · 638 índices · **0 secuencias** · 811 restricciones → **841 relaciones** en `pg_class` por schema (la cifra
«1 129» de la hoja de ruta no se reproduce con este conteo). `create_all` 0,94 s + `DROP` 0,18 s ≈ **1,1 s por prueba**.
Un schema multiplica por 3–12 las tablas de catálogo.

### 2.4 Benchmark ANTES — `evidence/.../benchmark-before.md`

Suite completa PostgreSQL en `805074c`: **384 schemas** creados y soltados (384 `create_all`, ≈ 322 944 relaciones),
**929,8 s** de pared (DDL estimado ≈ 430 s, ≈ 46 %), 2 584 / 38 / 28, residuos 0, catálogo sin delta (marca de agua
≈ 96 MB ya alcanzada; `TEST-PG-CATALOGO-MARCA-DE-AGUA` solo se mide).

## 3. Candidatos y POC — `evidence/.../poc-candidate-a.md`

| Candidato | Resultado |
|---|---|
| **A · schema por módulo + conexión por prueba con transacción externa; `Session(join_transaction_mode="create_savepoint")`** | POC en `test_licensing_central` (+ módulo adversarial): 15 → **2 schemas**, 13,2 s → **4,9 s**, aislamiento, commits (de prueba y de producto), segunda sesión del ámbito, PGLIFE y residuos: **PASS** en PostgreSQL. En SQLite (`pysqlite` + `StaticPool`) la transacción externa **no** contiene los commits (14 fallos + marcador visible): **solo PostgreSQL** |
| B · schema por módulo + `TRUNCATE` por prueba | no se mide: no aporta frente a A en estas 12 suites (sin sesiones secundarias ni hilos) y añade el riesgo de omitir una tabla |
| C · plantilla/clonado | `CREATE DATABASE … TEMPLATE` por prueba es más caro que un schema y exige privilegios: descartado sin implementar |
| **D · HYBRID** | **elegido**: A en PostgreSQL para las 12 suites; SQLite conserva la base en memoria nueva por prueba (FR-PGS-011); las 5 fixtures con sesiones secundarias/hilos conservan su schema por prueba con razón explícita |

`MECHANISM = PROVEN` · `AHORRO_MEDIDO = YES` (POC: −87 % de schemas y −63 % de tiempo en el módulo; proyección de la
corrida: 384 → ≈ 182 schemas) · `AISLAMIENTO_PRESERVADO = YES` (adversarial A/B/C/D) · `SEQUENCE_ISOLATION_CONTRACT`:
no hay secuencias (probado) · hilos: no aplica a las 12.

## 4. Diseño

`tests/conftest.py`: fixture de módulo `_esquema_del_modulo` (PostgreSQL: `make_engine` + `create_all` una vez; PGLIFE lo
apunta al módulo; `dispose` al cerrar; SQLite: `None`) y fixture de función **`sesion_de_prueba`** (PostgreSQL:
`connect()` + `begin()` + `Session(bind=conexión, join_transaction_mode="create_savepoint", expire_on_commit=False)`;
`finally`: `close`, `rollback`, `close`; SQLite: motor en memoria + `create_all` + sesión, `close` + `dispose`). Las 12
suites conservan su `db_session` como `def db_session(sesion_de_prueba)` que siembra lo mismo de hoy y la devuelve.
Matriz final:

| SUITE | TESTS | MECHANISM | SCHEMA_SCOPE | TRANSACTION_SCOPE | CLEANUP | THREAD_SAFE | SECONDARY_SESSION_SAFE | SEQUENCE_SAFE | REASON |
|---|---|---|---|---|---|---|---|---|---|
| las 12 `db_session` | 214 | ROLLBACK_GROUP (A) en PG · base nueva por prueba en SQLite | módulo (PG) | prueba (externa + SAVEPOINT) | rollback + PGLIFE al cerrar el módulo | n/a (sin hilos) | n/a (sin sesiones secundarias; una segunda sesión del ámbito va a la misma conexión) | sí (0 secuencias) | commits solo en la sesión principal |
| `test_installation_key_reference`, `central/test_central_authority` | 29 | SCHEMA_PER_TEST_EXCEPTION | prueba | — | PGLIFE | — | requieren `TestClient` con sesiones por petición y `dm._SessionLocal` | sí | sesiones secundarias reales |
| `test_license_import_race`, `test_license_revision_race` | 8 | SCHEMA_PER_TEST_EXCEPTION | prueba | — | PGLIFE | hilos con sesión y commit real | — | sí | carreras reales |
| `test_volumen_de_instalacion_ambito` | 6 (1 motor) | sin cambio | prueba | — | PGLIFE | — | — | sí | una sola creación; prueba del arnés del volumen |

`UNKNOWN 0`. `TEST_ORDER_DEPENDENCY 0`. Producto 0.

## 5. `/speckit.specify`

FR-PGS-001 el arnés reduce materialmente las creaciones de schema completo en PostgreSQL · 002 el aislamiento de datos por
prueba se mantiene · 003 una prueba no ve filas de otra del mismo módulo · 004 un `commit` del código no filtra datos a
la prueba siguiente · 005 una segunda sesión del ámbito no filtra datos entre pruebas · 006 las suites con hilos
conservan su semántica (quedan fuera del mecanismo) · 007 secuencias: contrato probado (no hay) · 008 PGLIFE sigue
soltando todo · 009 schemas residuales 0 · 010 limpieza tras fallo · 011 SQLite sin cambio semántico · 012 producto 0 ·
013 sin `skip` · 014 sin relajar aserciones · 015 sin reordenación · 016 sin `sleep`/reintentos · 017–020 métricas
antes/después (tiempo, schemas, relaciones, catálogo) · 021 `TEST-PG-CATALOGO-MARCA-DE-AGUA` OPEN · 022
`TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO` CLOSED · 023 A3 CLOSED · 024 runner E2E sin cambio · 025 auth/OpenAPI/
licenciamiento/sync/picking sin cambio · 026 las 4 omisiones ClamAV sin cambio · 027–029 MASTER57 = 57, SPEC057 PLANNED /
NOT STARTED, NEXT MASTER SPEC NOT YET PRIORITIZED.

## 6. `/speckit.clarify`

| # | Pregunta | Respuesta |
|---|---|---|
| 1–3 | suites, pruebas, cadena de fixtures | 12 suites / 214 pruebas / patrón único (§2.1) |
| 4–5 | `create_all` y relaciones por schema | 384 por corrida · 841 relaciones + 811 restricciones |
| 6–7 | duración y catálogo antes | 929,8 s · sin delta (marca de agua alcanzada) |
| 8–11 | commits, sesiones secundarias, hilos, motor directo | solo sesión principal · 0 · 0 · 0 |
| 12 | secuencias | 0 en modelos y en el schema |
| 13 | DDL en prueba | 0 |
| 14–17 | POC A, B, C, híbrido | A PASS en PG y descartado en SQLite; B y C descartados con motivo; HYBRID por motor y por suite |
| 18 | mecanismo | A en PG para las 12; SQLite igual que hoy; 5 excepciones con razón |
| 19 | prueba de aislamiento | PGS-02…06 en proceso + sondas en procesos aparte |
| 20 | PGLIFE | el schema de módulo lo apunta el ámbito de módulo (PGLIFE sin cambio) |
| 21 | limpieza tras fallo | PGS-10 (sonda que falla; 0 schemas con el pid del hijo) |
| 22 | SQLite | base nueva por prueba, `dispose` al terminar (PGS-09 rama SQLite) |
| 23 | ahorro esperado | ≈ 200 schemas y ≈ 220 s menos por corrida (a medir en W36) |
| 24–26 | mutaciones, suites completas, E2E | M-01…M-12; ambas completas; una global |
| 27 | DeepSeek | T03 (reescritura mecánica de 12 fixtures con contrato byte a byte) |

`SUITE_INVENTORY_COMPLETE = YES` · `UNKNOWN_SUITE_CLASSIFICATION = 0` · `BEFORE_METRICS = COMPLETE` · `MECHANISM_POC = PASS` ·
`AHORRO_MEDIDO = YES` · `AISLAMIENTO_PRESERVADO = YES` · `PRODUCT_CHANGE = 0` · `MATERIAL OQ = 0` · `UNKNOWN = 0`.

## 7. `/speckit.plan`

W01–W13 ✔ (reconciliación, orquestación, inventario, cadena de fixtures, arnés/PGLIFE, relaciones, benchmark y catálogo
antes, commits, sesiones, hilos, secuencias, DDL) · W14 POC A ✔ · W15 B descartado con motivo · W16 C descartado · W17–W18
comparación y elección (HYBRID) ✔ · W19 adversarial ✔ (POC y PGS-02…06) · W20 PGLIFE ✔ · W21 limpieza tras fallo (PGS-10)
· W22 diseño final ✔ · W23 excepciones ✔ · W24 pruebas PGS · W25 mutaciones · W26 clasificación · W27 analyze · W28
trazabilidad · W29 implement (T01 conftest, T03 suites) · W30–W31 dirigidas · W32 adversarial · W33 mutaciones · W34–W35
completas · W36–W37 benchmark y catálogo después · W38 E2E global · W39–W41 analyze, trazabilidad, converge.

## 8. CONSTITUTION GATE

G01–G05 ✔ · G06 inventario completo ✔ · G07 arnés mapeado ✔ · G08 relaciones medidas ✔ · G09–G12 schemas, relaciones,
tiempo y catálogo ANTES ✔ · G13–G17 commits, sesiones, hilos, secuencias, DDL clasificados ✔ · G18 POC medida ✔ · G19
mecanismo elegido con evidencia ✔ · G20 AHORRO_MEDIDO ✔ · G21 AISLAMIENTO_PRESERVADO ✔ · G22 PGLIFE ✔ · G23 limpieza tras
fallo (PGS-10) ✔ · G24 SQLite sin cambio ✔ · G25 producto 0 ✔ · G26–G30 sin reordenación/skip/relajación/sleep/retry ✔ ·
G31–G32 pruebas y mutaciones definidas ✔ · G33–G41 BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0 · ORPHAN
0/0 · MATERIAL OQ 0 · UNKNOWN 0 · TRAZABILIDAD 100 % → **PASS**. Autorización expresa del encargo: condiciones cumplidas.

## 9. `/speckit.tasks`

| ID | Requisitos | EXECUTOR / MODEL | TARGET_FILES | Acción | DONE_WHEN |
|---|---|---|---|---|---|
| T01 | FR-PGS-001…005, 008, 011 | **CLAUDE_ONLY** (diseño transaccional del arnés) | `tests/conftest.py` | `_esquema_del_modulo` + `sesion_de_prueba` | PGS-02…09 verdes en ambos motores |
| T02 | FR-PGS-002…010, 013–016 | **CLAUDE_ONLY** | `tests/test_pg_sesion_aislada.py`, `tests/sondas_pg/sonda_sesion*.py`, README de sondas | PGS-02…11, 23, 26, 27, 28 | verdes; mutaciones muertas |
| T03 | FR-PGS-001 | **DEEPSEEK_ELIGIBLE** / `deepseek-v4-flash` (reescritura mecánica con contrato byte a byte) | las 12 suites | `def db_session(sesion_de_prueba)` con la misma siembra; imports sin uso fuera | ruff limpio; 12 suites verdes; PGS-27 verde |
| T04 | FR-PGS-017…020 | **CLAUDE_ONLY** | — | benchmark y catálogo DESPUÉS; mutaciones; suites completas; E2E | evidencias §12 |

Todos: `SECURITY_SENSITIVE no` · `EGRESS_SAFE sí (sintético)` · `RETRY_MAX 2`.

## 10. `/speckit.analyze` previo y trazabilidad

Búsqueda: `db_session` (12 + 0 UNKNOWN) · `make_engine` (12 fixtures de función → 0 tras T03; módulos y excepciones
quedan) · `create_all` (12 → conftest) · `scope=` (sin sesión) · `commit`/`rollback` (sesión principal) ·
`begin_nested`/`savepoint`/`join_transaction_mode` (solo conftest) · `SessionLocal`/`sessionmaker`/`engine.connect`/
`dependency_overrides`/`thread` (0 en las 12) · `sequence`/`nextval`/`identity` (0) · `TRUNCATE` (no se usa) ·
`search_path` (connect_args, sin cambio) · `pytest order`/`skip`/`xfail`/`sleep`/`retry` (sin cambios) · `UNKNOWN` 0.
`AHORRO_MEDIDO = YES` · `AISLAMIENTO_PRESERVADO = YES` · `MECHANISM = PROVEN` · `PGLIFE_PRESERVED = YES` · `PRODUCT_CHANGE = 0`
· `SQLITE_SEMANTIC_CHANGE = 0` · BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0 · ORPHAN 0/0 · MATERIAL OQ 0 ·
UNKNOWN 0 · TRAZABILIDAD 100 %.

Trazabilidad: deuda → 12 suites → `db_session` de función → `make_engine`/`create_all` → 841 relaciones → benchmark antes →
commits/sesiones/hilos/secuencias → POC A/B/C → HYBRID → adversarial → PGLIFE → T01/T03 → PGS → M-01…M-12 → SQLite completa →
PostgreSQL completa → benchmark después → catálogo → E2E → convergencia.

## 11. `/speckit.implement` — por tarea

### T01 · `tests/conftest.py` (CLAUDE_ONLY)
```
[ANALYZE]  commits solo en la sesión principal; 0 sesiones secundarias/hilos/secuencias; PGLIFE ya soporta ámbito de módulo;
           pysqlite+StaticPool no sostiene la transacción externa (POC)
[PLAN]     _esquema_del_modulo (PG: make_engine+create_all una vez; SQLite: None) y sesion_de_prueba (PG: conexión +
           begin + Session(join_transaction_mode="create_savepoint") + finally close/rollback/close; SQLite: motor en
           memoria + create_all + sesión, close + dispose)
[CLASSIFY] CLAUDE_ONLY (diseño transaccional del arnés)   [EXECUTE] Claude   [AUDIT] PASS (ruff; sin sleep/skip; producto 0)
[TEST]     PGS 14/15 en PG y SQLite antes de T03 (solo el invariante estático 27 pendiente) → 15/15 tras T03
[STATUS]   COMPLETE
```
### T02 · `tests/test_pg_sesion_aislada.py` + `tests/sondas_pg/sonda_sesion*.py` (CLAUDE_ONLY)
```
[PLAN]     PGS-02…06b en proceso (A escribe/confirma/actualiza/borra, producto hace commit, B y C parten de cero; segunda
           sesión del ámbito), PGS-08 secuencias, PGS-09 identidad schema/motor por motor, sondas en procesos aparte
           (entera, que falla, dos módulos, orden inverso, prueba sola, dos procesos a la vez), PGS-27/28 estáticos
[EXECUTE]  Claude   [AUDIT] PASS   [TEST] 15/15 PG · 15/15 SQLite   [STATUS] COMPLETE
```
### T03 · las 12 suites (DEEPSEEK_ELIGIBLE · `deepseek-v4-flash`)
```
[EXECUTE]  intento 1: 2828/4504 tokens, $0.001639 · reintento 1: 2403/4339 tokens, $0.001551 · total ≈ $0.0032
[AUDIT]    intento 1: REJECT — 48 bloques correctos en contenido, pero los 24 REPLACE vacíos de import dejan una línea en
           blanco dentro del bloque de imports (ruff I001 ×12 al aplicarlos verbatim); restauradas las 12 copias
           reintento 1: PASS — 29 bloques (imports contiguos agrupados con la línea siguiente; fixtures idénticas);
           aplicados verbatim; ruff limpio; sin make_engine/create_all/sessionmaker en las 12; pruebas y aserciones intactas
[TEST]     12 suites + PGS: SQLite 229/229 · PostgreSQL 229/229 con 13 schemas (antes 229)
[STATUS]   COMPLETE (RETRY 1)
```
Egress en las dos llamadas: `ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0 REAL_PATHS=0`.

### T04 · verificación (CLAUDE_ONLY)
Mutaciones 12/12 (M-09 equivalente → M-09b sobre PGLIFE) · dirigidas · suites completas · benchmark y catálogo DESPUÉS · E2E (§12).

## 12. Resultados

| Certificación | Resultado | Evidencia |
|---|---|---|
| Dirigidas (12 suites + PGS) | SQLite 229/229 · PostgreSQL 229/229 con **13 schemas** (antes 229); residuos 0 | `directed-suites.md` |
| Aislamiento adversarial | PGS-02…06b, sondas en serie/paralelo/orden inverso/prueba sola/que falla | `isolation-proof.md` |
| Mutaciones | **12/12 muertas** (M-09 equivalente → M-09b sobre PGLIFE); residuos de los mutantes purgados con `qa/pg-test-residuos.py` | `mutation-campaign.md` |
| SQLite completa | **43 / 1582 / 1040** (ref. 43 / 1567 / 1040): 42 ENTORNO-SIN-CLAMSCAN + 1 intermitente de hilos; +15 = PGS; omitidas iguales; 0 schemas; **TARGET_REGRESSION 0 · UNKNOWN 0** | `sqlite-full.md` |
| PostgreSQL completa | **37 / 2600 / 28** (ref. 38 / 2584 / 28): 35 documentales + 2 `n9_integrity`; +15 PGS +1 intermitente que hoy pasa; omitidas iguales; residuos 0 | `postgres-full-and-benchmark-after.md` |
| Benchmark ANTES → DESPUÉS | schemas **384 → 188 (−51,0 %)** · relaciones ≈ 322 944 → 158 108 (−51,0 %) · pared **929,8 → 810,0 s (−12,9 %)** · catálogo sin delta (marca de agua alcanzada) · residuos 0 → **MATERIAL_IMPROVEMENT** | ídem |
| Catálogo (PGS-22) | medido antes y después, sin delta; `TEST-PG-CATALOGO-MARCA-DE-AGUA` **sigue OPEN** | ídem |
| Frontend | producto 0; gates no requeridos por el encargo | — |
| E2E global (runner sin cambio → una) | **273 / 0 / 4** (3.9 min), limpieza LIMPIA, 0 bases, puertos libres; las 4 omitidas = ENTORNO-SIN-CLAMSCAN; E2E-PANTALLA-SIN-PINTAR no se manifestó | `global-e2e.txt` |
| PGS-13 volumen de instalación | TV 8/8 + 6/6 dentro de las completas | suites |
| PGS-14…18 (licencia, sync, auth, OpenAPI, picking) | verdes en las completas | suites |
| PGS-19 E2E independiente | migra con Alembic, no usa `sesion_de_prueba` | `global-e2e.txt` |
| PGS-20/21 rendimiento | tabla ANTES/DESPUÉS con deltas | `postgres-full-and-benchmark-after.md` |
| Producto | `git diff app/ central_authority/` = 0 | §13 |

## 13. `/speckit.analyze` final, trazabilidad y veredicto

Búsqueda sobre el árbol final: `schema per test` / `create_all per test` → 0 en las 12 suites (PGS-27) · `scope=function`
→ `sesion_de_prueba` (por diseño) · `scope=module` → `_esquema_del_modulo` · `scope=session` → 0 en el conftest (PGS-28)
· `rollback missing` / `commit leak` / `secondary session leak` → M-02/M-03/M-05 muertos, PGS-03…06b · `thread leak` →
no aplica (0 hilos en el grupo) · `sequence leak` → 0 secuencias (PGS-08) · `shared Session` → M-04 muerto · `PGLIFE
regression` → M-06/M-09b muertos, `pg_harness.py` sin diff · `schema residue` → 0 en todas las corridas · `SQLite
semantic change` → 0 (M-08, PGS-09, suite completa) · `test ordering` / `skip` / `xfail` / `sleep` / `retry` → 0 (PGS-27/28;
omitidas 1040 = 1040 y 28 = 28) · `assertion weakening` → 0 (las 12 suites: solo la fixture y 3 líneas de import por fichero)
· `product diff` → 0 · `catalog debt closed incorrectly` → 0 (sigue OPEN) · `installation volume regression` → 0 (TV
14/14) · `key reference` / `licensing` / `OpenAPI` / `auth` / `picking` / `E2E` regressions → 0 · `SPEC057` / `NEXT MASTER`
→ sin cambio · `UNKNOWN` → 0.

`SCHEMA_PER_TEST_COST_REMAINING_UNJUSTIFIED 0` (las 188 restantes están clasificadas: mundos de módulo, 43 de fixtures
con sesiones secundarias/hilos con razón explícita, sondas) · `TEST_DATA_LEAK 0` · `COMMIT_LEAK 0` ·
`SECONDARY_SESSION_LEAK 0` · `THREAD_SESSION_LEAK 0` · `SEQUENCE_CONTRACT_REGRESSION 0` · `PGLIFE_REGRESSION 0` ·
`RESIDUAL_SCHEMA 0` · `FAILURE_CLEANUP_REGRESSION 0` · `SQLITE_SEMANTIC_CHANGE 0` · `PRODUCT_CHANGE 0` ·
`TEST_ORDER_WORKAROUND 0` · `TEST_REORDERING 0` · `NEW_SKIP 0` · `ASSERTION_WEAKENING 0` · `RETRY_WORKAROUND 0` ·
`SLEEP_WORKAROUND 0` · `INSTALLATION_VOLUME_REGRESSION 0` · `INSTALLATION_KEY_REFERENCE_REGRESSION 0` ·
`LICENSING_REGRESSION 0` · `CENTRAL_SYNC_REGRESSION 0` · `AUTH_REGRESSION 0` · `OPENAPI_REGRESSION 0` ·
`PICKLIST_409_REGRESSION 0` · `E2E_TYPECHECK_REGRESSION 0` · `E2E_CAPTURE_REGRESSION 0` · `CLAMSCAN_SKIP_REGRESSION 0` ·
`KEEPALIVE_75_REGRESSION 0` · `VERSION_PANEL_REGRESSION 0` · `CATALOG_DEBT_FALSELY_CLOSED 0` · `E2E_PANTALLA_ABSORBED 0` ·
`PRODUCTION_502_SCOPE_EXPANSION 0` · `SPEC057_STARTED 0` · `NEXT_MASTER_SPEC_SELECTED 0` · `SECRET_EXPOSURE 0` · BLOCKER 0 ·
CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0 · ORPHAN REQUIREMENTS 0 · ORPHAN TASKS 0 · MATERIAL OQ 0 · UNKNOWN 0 ·
**TRAZABILIDAD 100 %** (`traceability-matrix.md`).

Observaciones anotadas, no absorbidas: la hoja de ruta hablaba de «trece suites» y «1 129 relaciones»: medidos, son
12 suites `db_session` + 5 fixtures de función, y 841 relaciones + 811 restricciones. `KONTROL_STORAGE_PATH`/
`KONTROL_BACKUP_PATH` compartidos y `csync_02` dependiente de `csync_01` siguen anotados del ciclo anterior.

Orquestación: tareas 4 · `CLAUDE_ONLY` 3 (T01, T02, T04) · `DEEPSEEK_ELIGIBLE` 1 (T03) · ejecutadas por DeepSeek 1
(`deepseek-v4-flash`, 2 llamadas: 1 rechazo por formato —líneas en blanco en los imports, I001— y 1 aceptado en el
reintento 1; ≈ 5 231 tokens de entrada / 8 843 de salida; ≈ $0.0032) · implementadas por Claude 3 · pruebas nuevas 15
(+ 4 sondas) · mutaciones 12/12 · regresiones 0.

**Veredicto: `TEST-PG-UN-SCHEMA-POR-PRUEBA — CLOSED / CONVERGED` (MATERIAL_IMPROVEMENT).** Commit y push a
`origin/develop` al cierre.
