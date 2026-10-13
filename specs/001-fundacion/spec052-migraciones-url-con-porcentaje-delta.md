# SPEC 052 · Delta dirigida — MIGRACIONES-URL-CON-PORCENTAJE

**Fecha** 2026-10-13 · **Dueña** SPEC052 (instalador, actualización y migración; `entrypoint.sh`,
`alembic/env.py`; artefactos en `specs/001-fundacion/spec052-*`) · **Apoyo** SPEC001 (`Settings.db_url`,
`app/core/database.py`), SPEC004 (la Autoridad Central tiene su propio `env.py` con la **misma** raíz),
SPEC054 (migración real en QA) · **Base** `2037ad6` · **Rama** `develop` · **Evidencia**
`evidence/migraciones-url-con-porcentaje/`

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` | `2037ad6` / `2037ad6` / `2037ad6` — **coinciden** |
| `ACTUAL_BRANCH` · `WORKTREE_STATE` · `COMMITS_AFTER_2037AD6` · `RUN_DATABASES` | `develop` · limpio · 0 · 0 |
| Puertos 8000/8010/5173 | libres |
| MASTER57 / SPEC057 / NEXT MASTER SPEC | 57 · PLANNED / NOT STARTED · NOT YET PRIORITIZED — sin tocar |

## 2. Inventario (Alembic 1.14.0 · SQLAlchemy 2.0.36)

| Registro | Valor |
|---|---|
| `CLIENT_ALEMBIC_ENV` | `resources/backend/alembic/env.py`: `settings = get_settings()` → **`config.set_main_option("sqlalchemy.url", settings.db_url)`** → offline `config.get_main_option` → online `engine_from_config(config.get_section(...))` |
| `CENTRAL_ALEMBIC_ENV` | `resources/backend/central_authority/alembic/env.py`: la **misma forma** (`set_main_option` + `get_main_option` + `engine_from_config`), prefijo `KONTROL_CENTRAL_`, tabla `cla_alembic_version` → `CENTRAL_SAME_DEFECT = YES` |
| `ALEMBIC_INI` | `alembic.ini` y `central_authority/alembic.ini`: solo `script_location` y registro; **ninguna `sqlalchemy.url`** (no hay respaldo al que caer) |
| `SET_MAIN_OPTION_SITES` | los dos `env.py` (URL) · `qa/e2e_base.py:235`, `qa/n4-legacy-hostile-seed.py:91` (solo `script_location`) · `tests/test_n10_convergence.py:117` (URL de prueba sin `%`, y `env.py` la sobrescribía de todos modos) |
| `INTERPOLATION_BOUNDARY` | `alembic.config.Config.set_main_option` → `configparser.set` → `BasicInterpolation.before_set`: **revienta al asignar**, antes de conectar |
| `RUNTIME_ENGINE_PATH` | cliente `app/core/database.py:36` `create_engine(get_settings().db_url, …)`; Central `central_authority/database.py:17` `create_engine(get_settings().db_url, …)` → **sin `configparser`, sin defecto** (`RUNTIME_USES_CONFIGPARSER = NO`) |
| Contrato de `KONTROL_DB_URL` | URL SQLAlchemy completa (`compose.yaml:37`, obligatoria; `Settings.db_url: str`); el runtime la consume tal cual; nada exige duplicar `%` ni prohíbe `%` en la credencial → `URL_CONTRACT = PROVEN`, sin cambio |
| `ENTRYPOINT_ORDER` | cliente `scripts/entrypoint.sh`: validación P14 → `alembic upgrade head` → `exec "$@"`; Central `central_authority/entrypoint.sh`: `alembic -c central_authority/alembic.ini upgrade head` → `exec "$@"`. Migrar **antes** de arrancar; sin reintentos ni esperas |
| `QA_MIGRATION_PATH` · `E2E_MIGRATION_PATH` | `qa/e2e_base.py::migrar`: subproceso `python -m alembic upgrade head` con `KONTROL_DB_URL` → pasa por `env.py` (sufre el defecto; por eso `url_de` añadía `application_name` **sin codificar**, l. 119–121); `qa/pg-provision.sh` no migra |
| QA auth | `pg_hba.conf` del servidor de QA: `trust` → la autenticación con una clave con `%` no es verificable aquí; se certifican el parseo, la conexión y la URL lógica |

## 3. Reproducción antes de tocar nada (`reproduccion-head.txt`)

**Mínima (`configparser`):** `Config("alembic.ini").set_main_option("sqlalchemy.url",
"postgresql+psycopg2://***@localhost:5432/base?application_name=kontrol%20qa")` →
`ValueError: invalid interpolation syntax in '…' at position 31` (desde `configparser.before_set`);
`make_url` de la misma cadena: válida (`password 'p@ss%word'`, `query {'application_name': 'kontrol qa'}`).

**Real (PostgreSQL de QA, bases nuevas), con los `env.py` de `HEAD`:** U2 `%40`, U3 `%23`, U4 `%25`, U5
query con `%20`, U6 usuario `po%73tgres` → `ValueError: invalid interpolation syntax` en cliente y en
Central (`MIG-02…06`, `MIG-17`); camino canónico por subproceso (`python -m alembic upgrade head` con la
URL con `%`) → código de salida 1 con la misma excepción (salida sanitizada). U1 (sin `%`) migra en `HEAD`;
en la evidencia «falla» solo porque el registrador de la prueba no intercepta el motor que crea
`engine_from_config`: artefacto de la prueba, declarado. `DEFECT_REPRODUCED = YES · CONFIGPARSER_PATH_BROKEN
= YES · DATABASE_URL_VALID = YES`.

## 4. Patrón y lugar del arreglo

Candidatos: (A) escapar `%` → `%%` al entrar en `configparser`; (B) no pasar la URL por `configparser`:
construir el motor con `create_engine(url)`; (C) `context.configure` con conexión ya construida; (D)
otro del repositorio. **Elegido: B**, porque es exactamente lo que hacen los dos *runtimes* (`create_engine
(settings.db_url)`), elimina la frontera en vez de rodearla (no hay doble escape posible ni representación
«para configparser» que pueda filtrarse como URL lógica), `alembic.ini` no declara URL (nada que preservar),
y no añade dependencias ni helpers. `FIX_LOCATION = PROVEN`: el único punto por el que la URL entraba en
`configparser` era la línea `set_main_option` de cada `env.py`; `engine_from_config` solo existía para
leerla de vuelta. El runtime no se toca (`RUNTIME_IMPACT = PROVEN: ninguno`).

## 5. `/speckit.specify` · `/speckit.clarify` · compuerta

FR-MIGPCT-001/002 Alembic acepta una URL válida con `%` y `configparser` no la rechaza (porque ya no la
ve) · 003 migración y runtime resuelven la misma URL lógica (ambos `settings.db_url` directa) · 004/005/006
URL sin `%`, query y ausencia de doble escape (prueba: la URL que recibe `create_engine` == la lógica) ·
007/008/009 revisiones, esquema y cabeza intactos (cabezas declaradas: `0057_spec047_notifications`,
`0002_cla_sync_auth`) · 010 sin dependencias · 011 migrar antes de arrancar (contrato probado en ambos
entrypoints) · 012 sin credenciales en salida ni evidencia (subproceso con URL con `%`, salida escaneada;
el runner ya enmascara `://***@`) · 013 QA/E2E migran bases nuevas por `env.py` (global canónica) · 014
Central, misma raíz, mismo arreglo · 015 runtime intacto · 016–026 auth, OpenAPI, licencia, 409 de picking,
typecheck y captura E2E, omisiones de clamscan, keep-alive, versión, MASTER57, 057, puntero.

Clarify 1–32: §2–§4; 13 excepción exacta `ValueError: invalid interpolation syntax` (es `ValueError`, no
`InterpolationSyntaxError`: `before_set` la lanza al asignar); 17 matriz U1–U6 (§6); 20 doble escape:
imposible por construcción y probado por igualdad de URL; 22 redacción: la del runner (`://***@`) y el
escaneo de la salida; 27–28 pruebas en proceso (registrador de `create_engine` + base nueva por caso) y
por subproceso (camino canónico); 29 mutaciones 10; 30 suites completas: no (producto backend 0;
tooling de despliegue): dirigidas de N10 y del runner + global E2E; 31 una global (el runner migra con
`env.py`); 32 DeepSeek 0. `DEFECT_REPRODUCED · URL_CONTRACT · FIX_LOCATION · RUNTIME_IMPACT ·
CENTRAL_IMPACT · EQUIVALENCE = PROVEN · MATERIAL OQ 0 · UNKNOWN 0`. Ninguna condición de STOP (sin
cambio de contrato, sin dependencia, sin migración, sin esquema; runtime y migración ya comparten
semántica de URL).

Compuerta G01–G30: ✔ (G15 reproducción real completa en PostgreSQL; G17 Central afectada y corregida;
G24 ficheros de migración 0). **PASS.** Autorización: la del encargo con los seis PROVEN.

| Tarea | Requisito | Dueña | EXECUTOR | SEC | Ficheros | Acción | DONE_WHEN | Prueba | Mutación |
|---|---|---|---|---|---|---|---|---|---|
| T01 | FR-001…006/015 | 052 | CLAUDE | sí (credenciales) | `alembic/env.py` | `create_engine(settings.db_url, NullPool)`; offline `url=settings.db_url`; sin `set_main_option`/`engine_from_config` | MIG-02…06 verdes | `test_migraciones_url_porcentaje.py` | M-01…M-05, M-07, M-09 |
| T02 | FR-014 | 004/052 | CLAUDE | sí | `central_authority/alembic/env.py` | mismo arreglo | MIG-17 verde | ídem | M-08 |
| T03 | FR-001…014 | 052/054 | CLAUDE | no | `tests/test_migraciones_url_porcentaje.py` (nuevo) | MIG-01, 02–06 (matriz), 07, 08/13, 09/10, 14, 17 | 15/15 PostgreSQL; estáticas en SQLite | — | M-06, M-10 |
| T04 | FR-024…026 | 052 | CLAUDE | no | hoja de ruta, puntero, recuento | cerrar; puntero; 57 | ficheros | — | — |

`CLAUDE_ONLY 4 · DEEPSEEK_ELIGIBLE 0 · DEEPSEEK CALLS 0`.

## 6. Implementación (Claude)

**`alembic/env.py`** (+7/−9) y **`central_authority/alembic/env.py`** (+6/−4): `from sqlalchemy import
create_engine, pool`; se elimina `config.set_main_option("sqlalchemy.url", …)`; offline
`context.configure(url=settings.db_url, …)`; online `create_engine(settings.db_url, poolclass=pool.NullPool)`.
Nada más cambia: `fileConfig`, `init_models`, `target_metadata`, `compare_type`, `version_table` de la
Central, `alembic.ini`, revisiones (0), esquema (0), `entrypoint.sh` (0), runtime (0), dependencias (0).

**`tests/test_migraciones_url_porcentaje.py`** (nuevo, 15): MIG-01 la frontera sigue rechazando `%` y
ningún `env.py` pasa por ella (contrato estático) · MIG-02…06 matriz U1 sin `%`, U2 `%40`, U3 `%23`, U4
`%25`, U5 query `application_name=mig%20pct&connect_timeout=5`, U6 usuario `po%73tgres`: base nueva por caso,
`alembic upgrade head` en proceso por el `env.py` real con `KONTROL_DB_URL` (caché de `get_settings`
limpiada) y un registrador sobre `sqlalchemy.create_engine`: la URL recibida `==` la lógica (`make_url`,
query incluida) y `alembic_version == 0057_spec047_notifications` · MIG-07 control directo (`make_url`
decodifica usuario, clave y query) · MIG-08/13 camino canónico por subproceso con URL con `%`: código 0,
cabeza, y la salida no contiene la clave ni la URL · MIG-09/10 cabezas declaradas en ambos árboles · MIG-14
ambos entrypoints migran antes de `exec "$@"` y no reintentan ni esperan · MIG-17 Central: U1, U4, U5 con
`KONTROL_CENTRAL_DB_URL` y `cla_alembic_version == 0002_cla_sync_auth`. Credenciales: sintéticas, el
servidor de QA autentica por `trust`; en la evidencia las URL van enmascaradas.

## 7. Resultados (`suite-tras-arreglo.txt`, `mutaciones.txt`, `backend-dirigido.txt`, `e2e-global-1.txt`)

| Gate | Resultado |
|---|---|
| `tests/test_migraciones_url_porcentaje.py` PostgreSQL | **15/15** (matriz U1–U6, control, subproceso sin credenciales, cabezas, entrypoints, Central U1/U4/U5) |
| ídem SQLite | estáticas y control (MIG-01, 07, 09/10, 14) en verde; las de migración real se omiten por diseño |
| `ruff` (`env.py` ×2, prueba) | limpio |
| Dirigidas sobre PostgreSQL: `test_n10_convergence` (migra en proceso), `test_e2e_corrida`, `test_e2e_base_ciclo` (migran por subproceso) | **46/46** |
| Frontend | sin cambio de producto ni de `e2e/`: gates no requeridos por el encargo; la global E2E ejerce el frontend completo |
| Suites completas de backend | no requeridas (ningún módulo de producto cambia; `env.py` es herramienta de despliegue); el camino de migración se certifica con la matriz, N10, el runner y la global |

**Mutaciones** (GOOD → PASS, MUTATED → FAIL, RESTORED → PASS; `__pycache__` de `alembic/` purgado antes
de cada corrida, `PYTHONDONTWRITEBYTECODE=1`; PostgreSQL):

| Mutante | Lo mata | Resultado |
|---|---|---|
| M-01 vuelve `set_main_option` + `engine_from_config` (cliente) | MIG-01 y matriz U2–U6 (`ValueError`) | muere |
| M-02 doble escape (`%` → `%%` hacia SQLAlchemy) | U2–U6 (la URL recibida ≠ la lógica) | muere |
| M-03 se pierde la query | U5 | muere |
| M-04 se ignora la variable y se usa la URL por defecto de `Settings` | MIG-01, matriz (destino distinto) | muere |
| M-05 el `env` imprime la URL completa | MIG-08/13 (credenciales en la salida) | muere |
| M-06 el entrypoint arranca antes de migrar | MIG-14 | muere |
| M-07 la URL normal cambia de base | MIG-01, matriz | muere |
| M-08 solo se arregla el cliente (Central vuelve a `configparser`) | MIG-01, MIG-17 | muere |
| M-09 `.set(username="postgres", password=None)` | — | **equivalente** (en SQLAlchemy `URL.set(password=None)` es «sin cambio»): solo lo mataba el contrato estático; declarado y sustituido |
| M-09b la credencial cambia en tránsito (`.set(password="otra")`) | MIG-01 y toda la matriz | muere |
| M-10 aparece una revisión sin declararla | MIG-09/10 y la matriz (cabeza distinta) | muere |

10 mutantes aplicables, **10 muertos**; 1 equivalente declarado y sustituido.

**E2E canónica** (una global: el runner crea la base, la migra por `env.py` en subproceso, la siembra y
corre la suite): `r20261013t020610p3639667n6d0058` → **273 / 0 / 4**, 237 s; manifiesto `migracion:
{esperada: 0057_spec047_notifications, actual: 0057_spec047_notifications, cabezas: 1}`, red sin cambios,
reloj coherente; limpieza LIMPIA; bases residuales **0**. `E2E-PANTALLA-SIN-PINTAR` no se manifestó.

## 8. `/speckit.analyze` final, trazabilidad y veredicto

`DB_URL_PERCENT_INTERPOLATION_FAILURE 0 · DB_URL_LOGICAL_CHANGE 0 · DB_URL_DOUBLE_ESCAPE 0 · DB_URL_QUERY_LOSS 0 ·
NORMAL_URL_REGRESSION 0 · RUNTIME_DB_PATH_REGRESSION 0 (runtime sin tocar) · CENTRAL_DB_PATH_REGRESSION 0 ·
FULL_DB_URL_LOGGED 0 · PASSWORD_EXPOSURE 0 (evidencia con `://***@`; credenciales de prueba sintéticas,
servidor `trust`) · ENTRYPOINT_ORDER_CHANGE 0 · MIGRATION_FILE_CHANGE 0 · MIGRATION_REVISION_ADDED 0 ·
CLIENT_SCHEMA_CHANGE 0 · CENTRAL_SCHEMA_CHANGE 0 · NEW_DEPENDENCY 0 · RETRY_WORKAROUND 0 · SLEEP_WORKAROUND 0 ·
AUTH_REGRESSION 0 · OPENAPI_REGRESSION 0 · LICENSING_REGRESSION 0 · PICKLIST_409_REGRESSION 0 ·
E2E_TYPECHECK_REGRESSION 0 · E2E_CAPTURE_REGRESSION 0 · CLAMSCAN_SKIP_REGRESSION 0 · KEEPALIVE_75_REGRESSION 0 ·
VERSION_PANEL_REGRESSION 0 · E2E_PANTALLA_ABSORBED 0 · PRODUCTION_502_SCOPE_EXPANSION 0 · SPEC057_STARTED 0 ·
NEXT_MASTER_SPEC_SELECTED 0 · SECRET_EXPOSURE 0 · BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0 ·
ORPHAN REQUIREMENTS 0 · ORPHAN TASKS 0 · MATERIAL OQ 0 · UNKNOWN 0 · TRACEABILITY 100 %.`

MIGRACIONES-URL-CON-PORCENTAJE → contrato de `KONTROL_DB_URL` (URL completa, tal cual) → `env.py` ×2 →
`configparser` (`before_set`) → reproducción mínima y real (§3) → control directo (`make_url`, runtime) →
Central (misma raíz) → patrón B (§4) → matriz U1–U6 → equivalencia (cabeza y URL lógica) → MIG-01…17 →
M-01…M-10 → N10, runner, global E2E → convergencia. FR-MIGPCT-001…026 → T01–T04 → pruebas → mutaciones →
evidencia: 100 %.

**`MIGRACIONES-URL-CON-PORCENTAJE — CLOSED / CONVERGED`.** Lo no certificable aquí, dicho: la
autenticación de PostgreSQL con una clave que lleve `%` (el servidor de QA usa `trust`); el parseo, la
conexión y la igualdad de la URL lógica sí. Orquestación: 4 tareas `CLAUDE_ONLY`, 0 DeepSeek. Hoja de ruta,
`next-spec-decision.md` y recuento MASTER57 (57) actualizados; SPEC057 y NEXT MASTER SPEC sin cambio.
