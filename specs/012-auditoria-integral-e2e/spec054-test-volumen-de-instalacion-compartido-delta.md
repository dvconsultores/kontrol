# SPEC 054 · Delta dirigida — TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO

**Fecha** 2026-10-13 · **Dueña** SPEC054 (`specs/012-auditoria-integral-e2e`; arnés de pruebas de backend) ·
**Apoyo** SPEC004 (semántica del volumen y de la clave de instalación: no cambia), SPEC001 (`Settings` /
`get_settings`), SPEC052 (patrón de estado efímero por corrida del runner E2E) · **Antecedente**
`specs/010-licenciamiento-central/spec004-instalacion-key-reference-120-delta.md` (A3; donde se anotó esta deuda
como vecina no absorbida) y `spec054-pg-test-lifecycle-delta.md` (PGLIFE: el ciclo de vida de lo que la suite
crea, aquí en el sistema de ficheros) · **Base** `1f28c83` · **Rama** `develop` · **Evidencia**
`evidence/test-volumen-de-instalacion-compartido/`

Ciclo de arnés: **producto 0**. Discovery-first; sin relajar, omitir ni reordenar pruebas; sin `sleep` ni reintentos.

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` | `1f28c83` / `1f28c83` / `1f28c83` — **coinciden** |
| `ACTUAL_BRANCH` · `WORKTREE_STATE` · `COMMITS_AFTER_1F28C83` · `RUN_DATABASES` | `develop` · limpio · 0 · 0 |
| Puertos 8000/8010/5173 | libres |
| MASTER57 / SPEC057 / NEXT MASTER SPEC | 57 · PLANNED / NOT STARTED · NOT YET PRIORITIZED — sin tocar |

Detalle: `evidence/.../repository-checkpoint.md`.

## 2. Descubrimiento

### 2.1 El arnés (`tests/conftest.py`) — `evidence/.../fixture-inventory.md`

No hay fixture del volumen: `tests/conftest.py:25-26` fija **al importar** `KONTROL_INSTALLATION_VOLUME_PATH =
tempfile.gettempdir()/kontrol-test-license` con `os.environ.setdefault`. Es una constante **por máquina**: la
comparten todas las pruebas, todos los módulos, todas las sesiones y todos los procesos `pytest`. Nadie la crea
(la crea el producto en el primer `get_or_create_installation`) y **nadie la limpia**. Lo mismo ocurre con
`KONTROL_STORAGE_PATH` y `KONTROL_BACKUP_PATH` (vecinos, fuera de alcance, §13). `tests/test_migrations_offline.py:35`
repite el mismo `setdefault` (inerte bajo pytest). El conftest vive dos veces en `sys.modules` (`conftest`,
registrado por pytest, y `tests.conftest`, importado por 25 pruebas): el código a nivel de módulo corre dos veces.
Orden medido con `--setup-show`: una fixture `autouse` de módulo del conftest se monta **antes** que el mundo
`autouse` de cada módulo y se desmonta después.

### 2.2 Consumidores — `evidence/.../consumer-matrix.md`

81 ficheros con alguna coincidencia · **34** mundos de módulo escriben la clave vía `initialize` →
`get_or_create_installation` · **4** la escriben y la leen en el mismo ámbito (`test_license_sync_client`,
`test_license_trust_anchor`, `test_license_period_rollback`, `test_licensing_central`) · **6** fijan su propio
volumen (`test_installation_key_reference`, `test_spec004_installation_race`, `central/test_central_authority`,
`test_backend_keepalive`, `test_e2e_base_ciclo`, `test_migrations_offline`) · 2 coincidencias de cadena sin acceso
al volumen · 35 independientes · **`ASSUMES_PREEXISTING_KEY` = 0** · **`UNKNOWN` = 0**. Ningún `scope="class"` ni
`scope="session"`. Hilos y subprocesos de pruebas no escriben la clave de otro ámbito.

### 2.3 Producto — `evidence/.../settings-cache-analysis.md`

`installation_volume_path` se lee **en tiempo de ejecución** (`_private_key_path`, `resolve_key_reference`,
`get_or_create_installation`), nunca se captura al importar (`app/main.py:47` captura `Settings` para
`app_name`/`cors`/prefijo, no el volumen). `get_settings` es `lru_cache`: hay que `cache_clear()` al fijar y al
restaurar la variable (patrón existente en 30+ ficheros). `SETTINGS_ACCESS_PATTERN = runtime` ·
`IMPORT_TIME_CAPTURE = app/main.py (sin volumen)` · `RUNTIME_LOOKUP = sí` · `CACHE_BEHAVIOR = lru_cache + cache_clear`.
**Producto: 0 cambios necesarios.**

### 2.4 Runner E2E — `evidence/.../e2e-isolation-comparison.md`

`E2E_VOLUME_SCOPE = por corrida` · `E2E_VOLUME_PATH_SOURCE = estado/<run_id>/license` · `E2E_CLEANUP = rmtree(estado)`
· `SHARED_WITH_BACKEND_UNIT_TESTS = false` (lo exige `test_e2e_corrida_13`). El runner **no cambia**.

## 3. Mediciones

| Medición | Resultado | Evidencia |
|---|---|---|
| 01 · estado previo | el directorio existe con una clave sintética (0600, 119 B) de la corrida anterior; nadie la limpió | `preexisting-state.md` |
| 02 · sesiones consecutivas | `CROSS_SESSION_VISIBILITY = YES` (B arranca viendo la clave de A) y B la sobrescribe | `consecutive-sessions.md` |
| 03a · dos procesos simultáneos | `SAME_DIRECTORY` · `OVERWRITE` · `CROSS_READ` · `SIGNATURE_MISMATCH` = YES: A falla 10/13 con 502 `CENTRAL_SYNC_REJECTED` / `SYNC_AUTH_INVALID`; B pasa | `parallel-processes.md` |
| 03b · determinista | un proceso B que inicializa una instalación entre el montaje del mundo de A y su firma hace fallar `csync_02` con `SYNC_AUTH_INVALID`, siempre | `parallel-processes.md` |

**`INTERFERENCE_PROVEN = YES`** (`interference-proof.md`). Causa raíz: ruta fija por máquina en el arnés; el
producto escribe correctamente la clave canónica (A3) donde se le configura.

## 4. Alcance del aislamiento — `evidence/.../isolation-scope-decision.md`

`SELECTED_SCOPE = HYBRID`: **raíz única por proceso** (`pytest_configure` → `tempfile.mkdtemp(prefix="kontrol-test-license-")`,
en `config.stash`; eliminada en `pytest_unconfigure` con restauración de la variable) + **un volumen hijo vacío
por módulo** (fixture `autouse` de módulo sobre un gestor de contexto reutilizable: `mkdtemp(dir=raíz)`, fija la
variable, `cache_clear`, y al salir `rmtree`, restaura y `cache_clear`). FUNCTION descartado con evidencia (34
mundos de módulo escriben la clave una vez por módulo); `tmp_path_factory` descartado (pytest retiene tres
`basetemp`: dejaría claves en disco). Pruebas dependientes de estado ajeno: 0.

## 5. `/speckit.specify` — requisitos

| FR | Requisito |
|---|---|
| FR-TV-001 | Cada proceso `pytest` usa una raíz de volumen de instalación única (nombre aleatorio de `mkdtemp`, nunca fija). |
| FR-TV-002 | Dos sesiones `pytest` concurrentes no comparten volumen. |
| FR-TV-003 | Dentro de una sesión, cada módulo recibe su propio volumen hijo (alcance probado en §4). |
| FR-TV-004 | Cada volumen empieza vacío. |
| FR-TV-005 | Cada volumen se elimina al terminar su ámbito, pase o falle la prueba (finalizador de fixture); la raíz, al cerrar el proceso. |
| FR-TV-006 | Ninguna prueba lee una clave de instalación creada por otro ámbito. |
| FR-TV-007 | Ninguna prueba depende de estado de licencia/instalación dejado por otra sesión. |
| FR-TV-008 | `get_settings().installation_volume_path` refleja el volumen del ámbito actual. |
| FR-TV-009 | `get_settings` de producto no se modifica. |
| FR-TV-010 | La lógica de instalación/licenciamiento no se modifica. |
| FR-TV-011 | La clave sintética conserva 0600. |
| FR-TV-012 | Ningún material de clave entra en evidencia. |
| FR-TV-013 | Las pruebas que dependieran de una clave previa se hacen autosuficientes (inventario: 0). |
| FR-TV-014 | Sin reordenación de pruebas como solución. |
| FR-TV-015 / 016 / 017 | Sin `skip` nuevo · sin reintentos · sin `sleep`. |
| FR-TV-018 | El runner E2E conserva su aislamiento por corrida (sin cambio). |
| FR-TV-019 | `TEST-PG-UN-SCHEMA-POR-PRUEBA` permanece separada (OPEN). |
| FR-TV-020 | `INSTALACION-KEY-REFERENCE-120` permanece cerrada (A3 intacto). |
| FR-TV-021 | Auth/OpenAPI/licenciamiento/sync/desafío sin cambio. |
| FR-TV-022 | Gate de tipos E2E y diagnóstico intactos. |
| FR-TV-023 | Las cuatro omisiones ClamAV sin cambio. |
| FR-TV-024 / 025 / 026 | MASTER57 = 57 · SPEC057 PLANNED / NOT STARTED · NEXT MASTER SPEC NOT YET PRIORITIZED. |

## 6. `/speckit.clarify`

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | Fixture actual | no hay: `setdefault` al importar (`conftest.py:26`) |
| 2 | Alcance | proceso/máquina (ruta fija) |
| 3 | Consumidores | matriz completa, 81 ficheros, `UNKNOWN 0` |
| 4 | Visibilidad entre sesiones | YES (medición 02) |
| 5 | Interferencia entre procesos | YES (03a concurrente, 03b determinista) |
| 6 | Alcance elegido | HYBRID (raíz por proceso + hijo por módulo) |
| 7 | Por qué | 34 mundos de módulo; orden de autouse medido; 0 lectores de claves ajenas |
| 8 | Caché de settings | `lru_cache`; `cache_clear` al fijar y al restaurar |
| 9 | Capturas al importar | `app/main.py` (sin volumen): no bloquean |
| 10 | Pruebas que parchean rutas | 6, siguen correctas: el aislamiento no las hace incorrectas; **no se retocan** (TV-13) |
| 11 | Pruebas que asumen clave previa | 0 |
| 12 | Primitiva temporal | `tempfile.mkdtemp` (raíz y hijos); `tmp_path_factory` descartado (retención) |
| 13 | Limpieza | `rmtree` del hijo al desmontar el módulo; de la raíz en `pytest_unconfigure` |
| 14 | Limpieza tras fallo | finalizador de fixture (pytest lo ejecuta pase o falle) + prueba TV-09 con sonda que falla |
| 15 | Permisos | el producto sigue creando 0600 (TV-10) |
| 16 | E2E | ya aislado por corrida; sin cambio (TV-19) |
| 17 | Producto | 0 (TV-20) |
| 18 | Fixtures PostgreSQL | sin cambio; PGLIFE intacto; la deuda hermana no se absorbe (TV-22) |
| 19 | Mutaciones | M-01…M-12 (§9) |
| 20 | Certificación | dirigidas SQLite y PostgreSQL, paralela, completas SQLite y PostgreSQL, una E2E global |
| 21 | DeepSeek | elegible solo la matriz mecánica de pruebas en proceso sobre el gestor de contexto (T04), tras congelar el diseño |

`INTERFERENCE_PROVEN = YES` · `ISOLATION_SCOPE = PROVEN` · `PRODUCT_CHANGE = 0` · `MATERIAL OQ = 0` · `UNKNOWN = 0`.

## 7. `/speckit.plan`

W01 reconciliación ✔ · W02 orquestación (MCP `deepseek` disponible; delegación solo T04) · W03 inventario del
conftest ✔ · W04 consumidores ✔ · W05 mapa de ámbitos ✔ · W06 caché ✔ · W07 capturas al importar ✔ · W08 E2E ✔ ·
W09 estado previo ✔ · W10 sesiones consecutivas ✔ · W11 procesos paralelos ✔ · W12 interferencia probada ✔ · W13
alcance ✔ · W14 raíz única (`mkdtemp` en `pytest_configure`) · W15 caché (`_fijar_volumen` = variable +
`cache_clear`) · W16 pruebas dependientes (0) · W17 limpieza (hijo en finalizador, raíz en `pytest_unconfigure`) ·
W18 pruebas del arnés TV-01…TV-23 · W19 mutaciones M-01…M-12 · W20 clasificación (§9) · W21 analyze previo ·
W22 trazabilidad · W23 implement · W24 dirigidas SQLite · W25 dirigidas PostgreSQL · W26 paralela · W27
mutaciones · W28 SQLite completa · W29 PostgreSQL completa · W30 E2E global canónica · W31 analyze final · W32
trazabilidad final · W33 converge.

## 8. CONSTITUTION GATE

G01 HEAD `1f28c83` ✔ · G02 `develop` ✔ · G03 MASTER57 ✔ · G04 SPEC057 intacta ✔ · G05 dueña SPEC054 (arnés) ✔ ·
G06 fixture del volumen mapeada ✔ · G07 consumidores clasificados ✔ · G08 `UNKNOWN` 0 ✔ · G09 sesiones medidas ✔ ·
G10 procesos medidos ✔ · G11 interferencia probada ✔ · G12 alcance probado ✔ · G13 caché probada ✔ · G14 capturas
clasificadas ✔ · G15 E2E ya aislado ✔ · G16 producto 0 ✔ · G17 sin reordenación ✔ · G18 sin relajación ✔ · G19 sin
`skip` nuevo ✔ · G20 sin reintentos ✔ · G21 sin `sleep` ✔ · G22 limpieza definida ✔ · G23 seguridad de la clave
definida ✔ · G24 pruebas definidas ✔ · G25 mutaciones definidas ✔ · G26 BLOCKER 0 · G27 CRITICAL 0 · G28
CONTRADICTIONS 0 · G29 OWNER CONFLICT 0 · G30 ORPHAN REQUIREMENTS 0 · G31 ORPHAN TASKS 0 · G32 MATERIAL OQ 0 · G33
UNKNOWN 0 · G34 TRAZABILIDAD 100 % → **PASS**. Autorización expresa del encargo: condiciones cumplidas →
`/speckit.implement` autorizado.

## 9. `/speckit.tasks`

Campos comunes: `SECURITY_SENSITIVE` según tarea · `EGRESS_SAFE` sí (sintético) · `RETRY_MAX 2` · `EVIDENCE`
`evidence/test-volumen-de-instalacion-compartido/`.

| ID | Requisitos | EXECUTOR / MODEL | TARGET_FILES | Acción | DONE_WHEN / TEST |
|---|---|---|---|---|---|
| T01 | FR-TV-001…005, 008 | **CLAUDE_ONLY** (diseño de fixture, caché de settings, limpieza) / n-a | `tests/conftest.py` | quitar el `setdefault` del volumen; `pytest_configure` crea la raíz (`mkdtemp`) y la fija con `cache_clear`; `pytest_unconfigure` la elimina y restaura; gestor `volumen_de_instalacion_aislado(raiz, nombre)`; fixture `autouse` de módulo `volumen_de_instalacion` | las suites que escriben/leen la clave pasan (dirigidas); `ruff` limpio |
| T02 | FR-TV-001 | **CLAUDE_ONLY** (misma tarea) / n-a | `tests/test_migrations_offline.py` | quitar el `setdefault` redundante del volumen compartido (inerte bajo pytest) | `grep kontrol-test-license tests/` → 0 |
| T03 | FR-TV-001…007, 011, 012, 014 | **CLAUDE_ONLY** (subprocesos, paralelismo, orden, estático) / n-a | `tests/test_volumen_de_instalacion.py`, `tests/sondas_volumen/{README.md,informar.py,sonda_a.py,sonda_b.py,sonda_falla.py}` | TV-01 raíces distintas por proceso · TV-02 vacío al empezar · TV-03 B no ve A · TV-04 dos procesos concurrentes · TV-09 limpieza tras fallo · TV-11 sin PEM en la salida · TV-12 independencia de orden · TV-23 sin reordenación (estático) | pruebas verdes; mutaciones M-01, M-06, M-07, M-08, M-09, M-10, M-12 muertas |
| T04 | FR-TV-004, 005, 008, 011 | **DEEPSEEK_ELIGIBLE** / `deepseek-v4-flash` (matriz mecánica sobre un contrato cerrado) | `tests/test_volumen_de_instalacion_ambito.py` | TV-05 settings = ámbito · TV-06 cambio de ámbito A→B sin caché rancia · TV-07 restauración de la variable · TV-08 limpieza normal · TV-10 clave 0600 dentro del volumen · TV-02b hijo vacío | pruebas verdes; mutaciones M-02, M-03, M-04, M-05, M-11 muertas |
| T05 | FR-TV-013…026 | **CLAUDE_ONLY** / n-a | — (verificación) | dirigidas SQLite/PostgreSQL (TV-13…TV-18), paralela (TV-04 a escala de suites), completas, E2E global, `git diff app/` = 0 (TV-20), inventario de `skip` (TV-21), PGLIFE intacto (TV-22) | evidencias §12 |

## 10. `/speckit.analyze` previo y trazabilidad

Búsqueda: `KONTROL_INSTALLATION_VOLUME_PATH` (conftest:26, migrations_offline:35, 6 parcheadores propios, runner) ·
`kontrol-test-license` (2 sitios: ambos desaparecen) · `_private_key_path` / `resolve_key_reference` (producto
runtime; pruebas en su ámbito) · `get_settings` / `cache_clear` (patrón existente) · `tmp_path` /
`TemporaryDirectory` / `mkdtemp` (parcheadores propios; ninguno de sesión) · `scope=` (module/function; sin
class/session) · `autouse` (PGLIFE + mundos) · `pytest-order` / `test order` (no instalado, no usado) · `sleep` /
`retry` / `skip` / `xfail` (sin cambios previstos) · `UNKNOWN` 0.

`INTERFERENCE_PROVEN = YES` · `ISOLATION_SCOPE = PROVEN` · `SETTINGS_PROPAGATION = PROVEN` · `CLEANUP_DESIGN = PROVEN`
· `PRODUCT_CHANGE = 0` · `TEST_ORDER_DEPENDENCY_TARGET = 0` · `NEW_SKIP = 0` · `RETRY_WORKAROUND = 0` ·
`SLEEP_WORKAROUND = 0` · BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0 · ORPHAN REQUIREMENTS 0 ·
ORPHAN TASKS 0 · MATERIAL OQ 0 · UNKNOWN 0 · TRAZABILIDAD 100 %.

Trazabilidad: deuda → `conftest.py:26` (ruta fija) → caché de settings (§2.3) → clave (`get_or_create_installation`,
`_installation_private_key`) → medición 02 → medición 03a/03b → prueba de interferencia → alcance HYBRID → raíz
`mkdtemp` por proceso → `_fijar_volumen` (caché) → limpieza (hijo/raíz) → pruebas dependientes (0) → TV-01…TV-23 →
M-01…M-12 → SQLite completa → PostgreSQL completa → E2E global → convergencia.

## 11. `/speckit.implement` — por tarea

### T01 · `tests/conftest.py` (CLAUDE_ONLY)
```
[ANALYZE]  ruta fija por máquina al importar; conftest doble en sys.modules; orden autouse medido; get_settings runtime
[PLAN]     raíz por proceso en pytest_configure (mkdtemp, config.stash) + eliminación/restauración en pytest_unconfigure;
           gestor volumen_de_instalacion_aislado(raiz, nombre) (mkdtemp hijo, _fijar_volumen = variable + cache_clear,
           finally: rmtree + restaurar + cache_clear); fixture autouse de módulo volumen_de_instalacion sobre el gestor
[CLASSIFY] CLAUDE_ONLY (diseño de fixture, caché de settings, limpieza, manejo de claves)
[EXECUTE]  Claude
[AUDIT]    PASS (solo conftest; sin dependencias; sin sleep/skip; imports stdlib)
[TEST]     ruff check tests/conftest.py — limpio · --setup-show: SETUP M _recursos_pg_del_modulo → volumen_de_instalacion → _app_client
[STATUS]   COMPLETE
```
### T02 · `tests/test_migrations_offline.py` (CLAUDE_ONLY)
```
[ANALYZE]  setdefault redundante e inerte del volumen fijo; el subproceso del módulo ya usa tmp/"lic"
[PLAN]     eliminar la línea; storage/backup quedan (fuera de alcance)
[EXECUTE]  Claude  [AUDIT] PASS  [TEST] grep -rn kontrol-test-license tests/ → solo el prefijo `kontrol-test-license-` del conftest
[STATUS]   COMPLETE
```
### T03 · `tests/test_volumen_de_instalacion.py` + `tests/sondas_volumen/` (CLAUDE_ONLY)
```
[ANALYZE]  patrón de sondas de PGLIFE (`tests/sondas_pg`, `_correr` con subprocess + `-p no:cacheprovider`); informe JSON con huellas
[PLAN]     informar.py (huella, escribir_clave vía producto, informar, escenario) · sonda_a/sonda_b/sonda_falla · TV-01, 02, 03/08, 04, 09, 11, 12, 23
[EXECUTE]  Claude  [AUDIT] PASS (ruff limpio; sin sleep; SQLite en los hijos)
[TEST]     pytest tests/test_volumen_de_instalacion.py — 8/8 (SQLite) · también en la dirigida PostgreSQL
[STATUS]   COMPLETE
```
### T04 · `tests/test_volumen_de_instalacion_ambito.py` (DEEPSEEK_ELIGIBLE · `deepseek-v4-flash`)
```
[ANALYZE]  contrato cerrado: gestor + constantes del conftest; 6 pruebas con aserciones exactas; base en memoria como test_installation_key_reference
[EXECUTE]  DeepSeek deepseek-v4-flash · intento 1: 2505/2380 tokens, $0.001 · reintento 1: 2256/2178 tokens, $0.000926 · total ≈ $0.002
[AUDIT]    intento 1: REJECT (F401 `Iterator` sin usar; I001 `conftest` colocado tras `app.*`; deriva en tv_06: contexto C en vez del
           anidado A⊃B pedido) · reintento 1: PASS (los tres corregidos; el anidado tv06c⊃tv06d queda dentro de tv06b: las
           aserciones del contrato se cumplen y se acepta tal cual; sin dependencias; sin sleep/skip; solo el fichero objetivo)
[TEST]     ruff — limpio · pytest tests/test_volumen_de_instalacion_ambito.py — 6/6 · raíces residuales 0
[STATUS]   COMPLETE (RETRY 1)
```
Egress en las dos llamadas: `ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0 REAL_PATHS=0`.

### T05 · verificación (CLAUDE_ONLY)
Dirigidas SQLite 283/0/7 y PostgreSQL 328/0/1 (`suites-dirigidas.md`) · certificación paralela A 13/13 y B 34/34 a la vez
(`parallel-certification.md`) · mutaciones 12/12 (`mutation-campaign.md`) · limpieza (`cleanup-proof.md`) · claves
(`private-key-safety.md`) · inventario de `skip`/`xfail` 51 = 51 · `sleep`/`retry` 0 · `git diff app/ central_authority/` = 0.
Suites completas y E2E en §12.

## 12. Resultados

| Certificación | Resultado | Evidencia |
|---|---|---|
| Dirigidas SQLite (16 módulos) | 283 ejecutadas · 0 fallos · 7 omitidas preexistentes | `suites-dirigidas.md` |
| TV (SQLite) | 8/8 · TV-ámbito 6/6 | `suites-dirigidas.md` |
| Dirigidas PostgreSQL (21 módulos, con TV, carreras y PGLIFE) | 328 · 0 fallos · 1 omitida preexistente | `suites-dirigidas.md` |
| Certificación paralela (misma pareja de la medición 03a) | A 13/13 y B 34/34 **a la vez**; raíces 0 | `parallel-certification.md` |
| Mutaciones | **12/12 muertas**; RESTORED verde; producto restaurado | `mutation-campaign.md` |
| Limpieza | normal, tras fallo (sonda) y tras excepción (gestor): PASS; raíces residuales 0 en todas las corridas | `cleanup-proof.md` |
| Claves | `PRIVATE_KEY_CONTENT_IN_EVIDENCE 0` · `SECRET_EXPOSURE 0` | `private-key-safety.md` |
| SQLite completa | **43 / 1567 / 1040** (ref. 43 / 1553 / 1040): 42 ENTORNO-SIN-CLAMSCAN + 1 intermitente de hilos; la carrera de almacenes hoy pasa; **TARGET_REGRESSION 0 · UNKNOWN 0**; +14 = pruebas nuevas; omitidas iguales | `sqlite-full.md` |
| PostgreSQL completa | **38 / 2584 / 28** (ref. 38 / 2570 / 28): 35 documentales + 2 `n9_integrity` + 1 intermitente temporal conocido (PASSED ×3 dirigido); **TARGET_REGRESSION 0 · UNKNOWN 0**; +14; omitidas iguales; PGLIFE sin residuos | `postgres-full.md` |
| Frontend | producto 0; gates no requeridos por el encargo (sin cambio en `resources/frontend/`) | — |
| E2E global canónica (runner sin cambio → una) | **273 / 0 / 4** (3.9 min), limpieza LIMPIA, 0 bases, puertos libres; las 4 omitidas son ENTORNO-SIN-CLAMSCAN; E2E-PANTALLA-SIN-PINTAR no se manifestó | `global-e2e.txt` |
| TV-13 (parcheadores propios) | `test_installation_key_reference`, `test_spec004_installation_race`, `central/test_central_authority`, `test_backend_keepalive`, `test_e2e_base_ciclo`, `test_migrations_offline` pasan sin retoque | suites |
| TV-14…TV-18 (A3, legado, desafío/sync, SQLite, PostgreSQL) | verdes en dirigidas y completas | suites |
| TV-19 (E2E con su propio volumen) | `test_e2e_corrida_13` verde; global limpia | suites, `global-e2e.txt` |
| TV-20 (producto) | `git diff app/ central_authority/` = **0** | §13 |
| TV-21 (skips) | marcas `skip`/`xfail` en `tests/`: 51 = 51; omitidas de las suites iguales | §13 |
| TV-22 (deuda PG) | `TEST-PG-UN-SCHEMA-POR-PRUEBA` sigue OPEN; PGLIFE intacto | roadmap |

## 13. `/speckit.analyze` final, trazabilidad y veredicto

Búsqueda sobre el árbol final: `kontrol-test-license` → solo el prefijo `kontrol-test-license-` de `mkdtemp` (0 rutas
fijas) · `shared installation volume` / `fixed tempfile` → 0 · `installation_private_key.pem` → producto (constante,
escritor) y pruebas en su propio ámbito · `cross-session` / `cross-process` → TV-03/TV-04 verdes · `cache_clear
missing` / `settings stale` → `_fijar_volumen` limpia al fijar y al restaurar (M-03 muerto) · `test order` /
`pytest-order` / `pytest_collection_modifyitems` → 0 (TV-23) · `sleep` / `retry` → 0 en lo tocado · `skip` /
`xfail` → 51 = 51 · `preexisting key` → 0 pruebas dependientes · `private key evidence` → 0 · `TemporaryDirectory`
/ `tmp_path_factory` → no (descartado con motivo) · `product diff` → 0 · `UNKNOWN` → 0.

`SHARED_INSTALLATION_VOLUME 0` · `CROSS_SESSION_KEY_VISIBILITY 0` · `CROSS_PROCESS_KEY_OVERWRITE 0` ·
`PREEXISTING_KEY_DEPENDENCY 0` · `STALE_SETTINGS_VOLUME_PATH 0` · `TEMP_DIRECTORY_LEAK 0` ·
`PRIVATE_KEY_CONTENT_IN_EVIDENCE 0` · `KEY_PERMISSION_REGRESSION 0` · `TEST_ORDER_WORKAROUND 0` · `TEST_REORDERING 0` ·
`NEW_SKIP 0` · `ASSERTION_WEAKENING 0` · `RETRY_WORKAROUND 0` · `SLEEP_WORKAROUND 0` · `PRODUCT_CHANGE 0` ·
`INSTALLATION_KEY_REFERENCE_REGRESSION 0` · `LICENSING_REGRESSION 0` · `CENTRAL_SYNC_REGRESSION 0` ·
`CHALLENGE_REGRESSION 0` · `STARTUP_REVERIFY_REGRESSION 0` · `AUTH_REGRESSION 0` · `OPENAPI_REGRESSION 0` ·
`PICKLIST_409_REGRESSION 0` · `E2E_TYPECHECK_REGRESSION 0` · `E2E_CAPTURE_REGRESSION 0` · `CLAMSCAN_SKIP_REGRESSION 0` ·
`KEEPALIVE_75_REGRESSION 0` · `VERSION_PANEL_REGRESSION 0` · `PG_SCHEMA_DEBT_ABSORBED 0` · `E2E_PANTALLA_ABSORBED 0` ·
`PRODUCTION_502_SCOPE_EXPANSION 0` · `SPEC057_STARTED 0` · `NEXT_MASTER_SPEC_SELECTED 0` · `SECRET_EXPOSURE 0` ·
BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0 · ORPHAN REQUIREMENTS 0 · ORPHAN TASKS 0 · MATERIAL OQ 0 ·
UNKNOWN 0 · **TRAZABILIDAD 100 %** (`traceability-matrix.md`).

Observaciones anotadas, **no absorbidas** (candidatas para la dueña): (a) `KONTROL_STORAGE_PATH` y
`KONTROL_BACKUP_PATH` siguen fijos y compartidos en `tests/conftest.py` (el almacenamiento acumula 63 entradas
entre corridas); (b) en `test_license_sync_client`, `csync_02` depende de que `csync_01` haya configurado la
Autoridad en el mismo módulo (dependencia de orden intramodular, ajena al volumen).

Orquestación: tareas 5 · `CLAUDE_ONLY` 4 (T01, T02, T03, T05) · `DEEPSEEK_ELIGIBLE` 1 (T04) · ejecutadas por DeepSeek 1
(`deepseek-v4-flash`, 2 llamadas: 1 rechazo + 1 aceptado en el reintento 1; ≈ 4 761 tokens de entrada / 4 558 de
salida; ≈ $0.002) · implementadas por Claude 4 · pruebas nuevas 14 (+ 3 sondas) · mutaciones 12/12 · regresiones 0.

**Veredicto: `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO — CLOSED / CONVERGED`.** Commit y push a `origin/develop` al cierre.
