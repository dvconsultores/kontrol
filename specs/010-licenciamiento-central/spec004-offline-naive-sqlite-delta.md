# SPEC 004 · Delta dirigida — OFFLINE-NAIVE-EN-SQLITE

**Fecha** 2026-10-13 · **Dueña** SPEC004 (licenciamiento; `app/modules/licensing/service.py`) · **Apoyo**
SPEC001 (`DateTime(timezone=True)` y comportamiento de SQLite), SPEC054 (paridad SQLite/PostgreSQL) ·
**Base** `3126ce2` · **Rama** `develop` · **Evidencia** `evidence/offline-naive-sqlite/`

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` | `3126ce2` / `3126ce2` / `3126ce2` — **coinciden** |
| `ACTUAL_BRANCH` · `WORKTREE_STATE` · `COMMITS_AFTER_3126CE2` · `RUN_DATABASES` | `develop` · limpio · 0 · 0 |
| Puertos 8000/8010/5173 | libres |
| MASTER57 / SPEC057 / NEXT MASTER SPEC | 57 · PLANNED / NOT STARTED · NOT YET PRIORITIZED — sin tocar |

## 2. Localización

| Registro | Valor |
|---|---|
| `SERVICE_FILE` · `METHOD` | `app/modules/licensing/service.py::verify_offline(db)` (FR-010-003) |
| `INPUTS` · `NOW_SOURCE` | `LicenseState` de la instalación, `LicenseCentralConfig.grace_days` (7 si no hay config) · `_now()` = `datetime.now(UTC)` (aware) |
| `LAST_RELIABLE_DATE_USAGE` | `grace_end = last + timedelta(days=grace_days)`; `if now > grace_end` → `GRACE_EXPIRED`; si no `WITHIN_GRACE` con `grace_days_left = (grace_end - now).days`; sin fecha → `NO_RELIABLE_DATE` |
| `RETURN_TYPE` | dict `{offline_valid, reason, grace_days, grace_days_left[, grace_end, last_reliable_date]}` |
| `OVERVIEW_ROUTE` · `OFFLINE_STATUS_ROUTE` | `GET /licensing/overview` (`central_overview` → incluye `offline = verify_offline(db)`) · `GET /licensing/offline-status` · ambos `require_permission("license", "view")` con sesión; sin contexto de empresa (instalación) |
| `MODEL` · `COLUMN_TYPE` · `NULLABLE` | `LicenseState.last_reliable_date: DateTime(timezone=True)`, nullable |
| `WRITERS` | `activate_license` (`state.last_reliable_date = last_reliable or _now()`, l. 348) · sync (`_dt_from(server_time)` si es más reciente que el actual, l. 822) |
| `READERS` · `COMPARISONS` | `compute_mode` (l. 318, 411: **ya normaliza** con `_as_utc`) · sync (l. 822: **ya normaliza** ambos lados) · `verify_offline` (l. 952–954: **no normalizaba**) · serializa con `isoformat()` |
| `SEMANTIC_TYPE` | **INSTANT**: nace de `datetime.now(UTC)` o del `server_time` ISO del sync autenticado (`_dt_from` → aware); la Spec lo llama «reloj confiable». No es fecha civil de negocio: `POLICY-CLOCK-LOCAL` (America/Caracas) no interviene |
| `EXISTING_HELPER` · `EXISTING_PATTERN` | `license_contract._as_utc(dt)` («Normaliza datetimes a UTC (SQLite devuelve naive en DateTime(timezone))»: etiqueta UTC si no hay zona) · `service._utc(dt)` (expresa un aware en UTC al persistir; precedente FR-010-323 para `period_*`, l. 338–341, delta `LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN`) |
| Inventario del módulo (`DateTime(timezone=True)`) | `period_start/end`, `critical_warning_start`, `read_only_start` (persistidos con `_utc`, leídos con `_as_utc` en `compute_mode`) · `verified_at`, `imported_at`, `replaced_at`, `ran_at`, `taken_at` (sellos, **no se comparan** con `now` en el servicio) · `last_reliable_date` (el único con comparación sin normalizar). Fuera del módulo: `treasury/rates.py`, `master_data/uom.py`, `identity_access` ya normalizan con el mismo criterio; ninguna deuda nueva |
| `TEST_THAT_MISSED_BUG` · `WHY` | `test_licensing_central.py::TestOffline` (2 pruebas): escribían `state.last_reliable_date` aware, hacían `commit()` y llamaban `verify_offline` con la **misma sesión**: el objeto en memoria conserva la zona (`expire_on_commit=False`) y nunca se releyó de SQLite |
| `FRONTEND_CONSUMER` | `ConfiguracionCentralPage` (`/licensing/overview`, `retry: false`) y `MiLicenciaPage`; con 500 la página no mostraba la configuración. Frontend de producto: **0** cambios |

`ROOT_CAUSE = SERVICE_NORMALIZATION_MISSING` (sobre la conducta real `SQLITE_DESERIALIZES_NAIVE`): el
módulo ya tiene criterio y helpers para este caso; `verify_offline` era el único lector que no los usaba.
`FIX_LOCATION = B`, helper canónico del módulo en el lector (`_as_utc`), más `_utc` en los dos escritores
para que lo persistido sea hora de pared UTC como los instantes del período. `SCHEMA_CHANGE = 0`.
`HISTORICAL_REINTERPRETATION = 0`: lo persistido nació en UTC (`_now()`), así que etiquetarlo UTC
devuelve el mismo instante; el sync ya escribía `server_time` normalizado a `+00:00` por `_dt_from`.

## 3. Reproducción antes de tocar nada (`reproduccion-head.txt`)

Suite hostil `tests/test_licensing_offline_sqlite.py` (mundo HTTP de `test_license_access` con licencia
activa y usuario `operador` sin `license:view`; `_configure_central` con gracia 7; **reloj fijo**
`AHORA = 2026-10-13T12:00Z` por `monkeypatch` de `licensing_service._now`; cada vector escribe
`last_reliable_date`, confirma y cierra la sesión; cada petición HTTP lee de la base con la suya):

| Motor | `last_reliable_date` recargada | `/offline-status` | `/overview` | Excepción |
|---|---|---|---|---|
| **SQLite** | `tzinfo is None` (hora de pared UTC) | **500** `INTERNAL_ERROR` | **500** | `TypeError: can't compare offset-naive and offset-aware datetimes` (6 veces: todos los vectores con fecha) |
| PostgreSQL | aware, `== AHORA − 2 d` | 200 | 200 | ninguna; 9/9 + 1 omitida por diseño |

Pasaban en SQLite antes del arreglo: OFF-01 (documenta la deserialización), OFF-07 (sin fecha: rama que
no compara), OFF-12 (el objeto en memoria conserva la zona: por eso `TestOffline` no lo veía) y OFF-14
(401/403 antes de cualquier decisión). `SQLITE_500_REPRODUCED = YES · POSTGRES_CONTROL = PASS ·
DB_RELOAD_NECESSARY = PROVEN` (OFF-12).

## 4. `/speckit.specify`

FR-OFFSQL-001/002 ambos endpoints sin 500 en SQLite con fecha confiable · 003 misma decisión en los dos
motores para el mismo instante · 004 los instantes UTC persistidos se comparan como UTC en cualquier motor
· 005 la zona del proceso no cambia la decisión · 006 sin reinterpretación histórica · 007/008/009 gracia,
vencimiento y revisión/reemisión intactos · 010 `/license/status` público mínimo intacto · 011
`license:view` intacto · 012 reverificación de arranque intacta · 013/014/015 sync, tasa y rotación
intactos · 016 la prueba de regresión recarga desde la base · 017 PostgreSQL verde con los mismos vectores
· 018/019 sin migración ni cambio de tipo · 020 frontend 0 · 021–028 OpenAPI, roles, 409 de picking,
typecheck y captura E2E, omisiones de clamscan, keep-alive 75, versión · 029–031 MASTER57, 057, puntero.

## 5. `/speckit.clarify` — 27 puntos

1 `LicenseState.last_reliable_date`, `DateTime(timezone=True)`, nullable · 2 **INSTANT** (§2) · 3–4
escritores y lectores (§2) · 5 SQLite: hora de pared sin zona (OFF-01) · 6 PostgreSQL: instante (OFF-01)
· 7 `now > grace_end` con `grace_end = naive + timedelta` · 8 `api.py::offline_status` →
`verify_offline`; `api.py::overview` → `central_overview` → `verify_offline` · 9 `TestOffline` sin releer
(§2) · 10 inventario: solo esta columna se compara sin normalizar (§2) · 11–12 `_as_utc` y `_utc`, con
precedente en el mismo fichero · 13 lector (`_as_utc`) + escritores (`_utc`) · 14 sin reinterpretación
(nació en UTC) · 15 `replace(tzinfo=UTC)` no consulta la zona del proceso (OFF-11 en UTC, Caracas y Tokio)
· 16 reloj fijo por `monkeypatch` (precedente: `AHORA` en `test_license_trust_anchor.py`) · 17 vectores:
−2 d (dentro, 5 días), −7 d exacto (**dentro**, 0 días: el contrato rechaza solo al superar), −7 d −1 s
(vencida), −30 d (vencida), `NULL`; la Spec no contempla fecha futura (el sesgo de reloj lo maneja
`compute_mode`, no `verify_offline`): sin V4 · 18 gracia de `LicenseCentralConfig.grace_days` (7 por
defecto; el contrato no cambia) · 19 cuerpos exactos iguales en ambos motores · 20 frontend sin cambio ·
21 esquema 0 · 22–23 la misma suite corre en ambos motores (OFF-12 solo documenta SQLite) · 24 10
mutantes · 25 suites completas (producto backend cambia) · 26 dos globales (licencia es ruta compartida) ·
27 DeepSeek 0 (semántica temporal y de licencia: `CLAUDE_ONLY`; el cambio son 3 líneas).
`TEMPORAL_SEMANTICS · ROOT_CAUSE · FIX_LOCATION · CROSS_ENGINE_SEMANTICS = PROVEN · MATERIAL OQ 0 · UNKNOWN 0`.

## 6. Compuerta constitucional

G01–G04 ✔ · G05 dueña 004 ✔ · G06–G08 localizados ✔ · G09 SQLite 500 reproducido ✔ · G10 control
PostgreSQL ✔ · G11 `TypeError` capturado ✔ · G12 recarga necesaria probada (OFF-12) ✔ · G13 semántica
INSTANT ✔ · G14 patrón canónico (`_as_utc`/`_utc`) ✔ · G15 lugar del arreglo ✔ · G16 inventario del módulo
✔ · G17 sin absorber otros módulos (ya normalizan) ✔ · G18 misma decisión definida por vectores ✔ · G19
reloj fijo ✔ · G20 fronteras ✔ · G21 `/license/status` intacto ✔ · G22 `license:view` intacto ✔ · G23
reverificación intacta ✔ · G24 sync intacto ✔ · G25 esquema 0 ✔ · G26–G27 pruebas y mutaciones ✔ ·
G28–G31 ✔. **PASS.** Autorización: la del encargo, con los cinco PROVEN y `SCHEMA_CHANGE = 0`.

| Tarea | Requisito | Dueña | EXECUTOR | SEC | EGRESS | Ficheros | Acción | DONE_WHEN | Prueba | Mutación |
|---|---|---|---|---|---|---|---|---|---|---|
| T01 | FR-001…006 | 004 | CLAUDE | sí (licencia) | n-a | `licensing/service.py` | `verify_offline` lee con `_as_utc`; `activate_license` y el sync persisten con `_utc` | OFF verde en ambos motores | `test_licensing_offline_sqlite.py` | M-01…M-04, M-06, M-09, M-10 |
| T02 | FR-016/017 | 004/054 | CLAUDE | no | n-a | `tests/test_licensing_central.py` | `TestOffline` hace `expire_all()` tras el commit | con M-01 esas dos pruebas fallan en SQLite | — | M-01 |
| T03 | FR-001…017 | 004/054 | CLAUDE | no | n-a | `tests/test_licensing_offline_sqlite.py` (nuevo) | OFF-01…14 con reloj fijo y recarga | 12 SQLite · 11 + 1 omitida PostgreSQL | — | M-05, M-07, M-08 |
| T04 | FR-029…031 | 004 | CLAUDE | no | n-a | hoja de ruta, puntero, recuento | cerrar; puntero; 57 | ficheros | — | — |

`CLAUDE_ONLY 4 · DEEPSEEK_ELIGIBLE 0 · DEEPSEEK CALLS 0`.

## 7. Implementación (Claude)

**`app/modules/licensing/service.py`** (+9/−3): en `verify_offline`, `last =
license_contract._as_utc(state.last_reliable_date)` (comentario con la causa); en `activate_license`,
`state.last_reliable_date = _utc(last_reliable or _now())`; en el sync, `_utc(recibido)` al adoptar el
`server_time`. Invariante: el instante antes del viaje a la base == el instante después, en los dos motores.
Sin conversión por la zona del proceso, sin migración, sin tocar gracia, vencimiento, `/license/status`,
permisos, reverificación, sync, tasa ni rotación. `ruff` limpio; `mypy` del módulo sin incidencias.

**`tests/test_licensing_central.py`**: las dos pruebas de `TestOffline` ganan `db_session.expire_all()`
tras el `commit` (releen de la base; con M-01 fallan en SQLite, como debieron fallar siempre).

**`tests/test_licensing_offline_sqlite.py`** (nuevo, 12): §3.

## 8. Mutaciones (`mutaciones.txt`) y gates de frontend (`frontend-gates.txt`)

GOOD → PASS en SQLite, PostgreSQL y la suite de acceso; MUTATED → FAIL en el motor donde la prueba es
autoridad; RESTORED → PASS; `__pycache__` purgado y `PYTHONDONTWRITEBYTECODE=1`.

| Mutante | Motor | Lo mata | Resultado |
|---|---|---|---|
| M-01 sin normalización en `verify_offline` | SQLite | OFF-02/09/10/11 (vuelve el 500) | muere |
| M-02 el valor sin zona se interpreta como America/Caracas | SQLite | OFF-02/09/10 (instante 4 h corrido) | muere |
| M-03 se interpreta con la zona local del proceso | SQLite | OFF-02/09/10/11 | muere |
| M-04 se desplaza la hora en vez de etiquetar la zona | SQLite | OFF-02/09/10 | muere |
| M-05 la prueba deja de recargar desde la base | SQLite | OFF-01, OFF-12 | muere |
| M-06 frontera `>=` en vez de `>` | PostgreSQL | OFF-09 | muere |
| M-07 campo nuevo en el DTO público (1.ª versión) | — | **equivalente por error del guion**: el campo cayó dentro del docstring; declarado y sustituido | — |
| M-07b `license_id` en el DTO público | SQLite | `test_license_access::test_lic_01/02` (claves exactas) | muere |
| M-08 `/offline-status` sin `license:view` | SQLite | OFF-14 | muere |
| M-09 gracia con un día más | PostgreSQL | OFF-02/09/10 | muere |
| M-10 la vista traga un `TypeError` (1.ª versión) | — | **equivalente al diseño**: sin `TypeError` no hay nada que tragar; sustituido | — |
| M-10b la vista deja de consultar `verify_offline` | SQLite | OFF-02 (la vista ≠ el endpoint) | muere |

10 mutantes aplicables, **10 muertos**; 2 equivalentes declarados y sustituidos.

Frontend (sin cambio de producto): typecheck (src + herramientas + e2e) ✔ · lint ✔ · Vitest **477/477** ·
build ✔.

## 9. Suites completas de backend (`backend-sqlite-completo.txt`, `backend-postgres-completo.txt`)

Recuentos desde la barra de progreso (el gancho de resumen del `conftest` no imprime totales en `-q`);
lista `FAILED` comparada una a una con la línea base del cierre de `ROLES-SIN-API-DE-ALTA`.

| Motor | Resultado | Diferencia frente a la base | Clasificación |
|---|---|---|---|
| SQLite | **44 fallos / 1528 pasan / 1028 omitidas** | lista `FAILED` **idéntica** (0 nuevos, 0 desaparecidos); +21 pasan (11 de picking y 10 de esta suite); +7 omitidas (3 de picking solo-PostgreSQL y 4 de documentos) | 42 documentales sin `clamscan` (BASELINE, `ENTORNO-SIN-CLAMSCAN`) · `test_auth_session_rotation::test_dos_renovaciones_simultaneas…` (KNOWN_INTERMITTENT de hilos en SQLite) · `test_warehouse_structure::test_concurrencia…` (BASELINE, `ALMACENES-CARRERA-SQLITE-HILOS`) |
| PostgreSQL | **38 fallos / 2534 pasan / 28 omitidas** | +1 fallo: `test_licensing_central::TestSincronizacion::test_sync_success_records_run_snapshot_and_event`; +1 omitida (OFF-12, solo documenta SQLite) | 35 documentales + 2 `test_n9_integrity` (BASELINE) · el +1 es el KNOWN_INTERMITTENT de tiempo (aserción de `last_reliable_date` contra un instante fijado antes de la suite; ya clasificado el 2026-10-12, pasa dirigido: §9.1) |

`TARGET_REGRESSION = 0 · NEW_INDEPENDENT_DEBT = 0 · UNKNOWN = 0`. Nota: ese intermitente **no** es este
defecto: compara `state.last_reliable_date.replace(tzinfo=UTC)` con `SERVER_TIME` (línea 185) y falla por
el reloj real, no por la zona.

### 9.1 El intermitente, dirigido

`test_sync_success_records_run_snapshot_and_event` ×3 sobre PostgreSQL: **PASSED ×3**
(`intermitente-licensing-central.txt`). KNOWN_INTERMITTENT, ajeno al cambio.

## 10. Certificación E2E (`e2e-global-1.txt`, `e2e-global-2.txt`)

Licencia es ruta compartida: dos globales canónicas consecutivas, cada una con su base nueva.

| Corrida | Id | passed | failed | skipped | Suite | Manifiesto `entorno` | Limpieza |
|---|---|---|---|---|---|---|---|
| Global 1 | `r20261013t005740p3574682ne24ba1` | **273** | **0** | **4** | 232,6 s | red sin cambios · reloj coherente · túnel presente | LIMPIA |
| Global 2 | `r20261013t010143p3600866n5a8f87` | **273** | **0** | **4** | 233,7 s | ídem | LIMPIA |

Los cinco proyectos (chromium y los cuatro de licencia: revisión, sync, rotación, tasa) pasan; las 4
omitidas son las de `ENTORNO-SIN-CLAMSCAN`. Bases residuales **0**. Corridas adicionales: ninguna.

## 11. `/speckit.analyze` final, trazabilidad y veredicto

`SQLITE_OFFLINE_500 0 · SQLITE_NAIVE_AWARE_TYPEERROR 0 · CROSS_ENGINE_DECISION_MISMATCH 0 (cuerpos
idénticos por vector) · HOST_TIMEZONE_DEPENDENCE 0 (UTC, Caracas, Tokio) · HISTORICAL_TIMESTAMP_REINTERPRETATION 0 ·
BUSINESS_TIMEZONE_POLICY_CHANGE 0 · OFFLINE_WINDOW_CHANGE 0 · LICENSE_EXPIRY_SEMANTIC_CHANGE 0 ·
PUBLIC_LICENSE_STATUS_CHANGE 0 · LICENSE_VIEW_PERMISSION_CHANGE 0 · STARTUP_REVERIFY_REGRESSION 0 ·
CENTRAL_SYNC_REGRESSION 0 · RATE_LIMIT_REGRESSION 0 · KEY_ROTATION_REGRESSION 0 · SIGNED_REVISION_REGRESSION 0 ·
CLIENT_SCHEMA_CHANGE 0 · CENTRAL_SCHEMA_CHANGE 0 · FRONTEND_PRODUCT_CHANGE 0 · OPENAPI_REGRESSION 0 ·
ROLE_CREATE_REGRESSION 0 · PICKLIST_409_REGRESSION 0 · E2E_TYPECHECK_REGRESSION 0 · E2E_CAPTURE_REGRESSION 0 ·
CLAMSCAN_SKIP_REGRESSION 0 · KEEPALIVE_75_REGRESSION 0 · VERSION_PANEL_REGRESSION 0 · E2E_PANTALLA_ABSORBED 0 ·
PRODUCTION_502_SCOPE_EXPANSION 0 · SPEC057_STARTED 0 · NEXT_MASTER_SPEC_SELECTED 0 · RETRY_WORKAROUND 0 ·
SLEEP_WORKAROUND 0 · TIMEOUT_INFLATION 0 · SECRET_EXPOSURE 0 · BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 ·
OWNER CONFLICT 0 · ORPHAN REQUIREMENTS 0 · ORPHAN TASKS 0 · MATERIAL OQ 0 · UNKNOWN 0 · TRACEABILITY 100 %.`

OFFLINE-NAIVE-EN-SQLITE → `/licensing/offline-status`, `/licensing/overview` → `verify_offline` →
`LicenseState.last_reliable_date` → recarga en SQLite sin zona (OFF-01/12) → `TypeError` (§3) → INSTANT (§2)
→ `_as_utc`/`_utc` (precedente del módulo) → lector + escritores (§7) → vectores con reloj fijo (§5) →
OFF-01…14 + `TestOffline` recargando → M-01…M-10b → suites completas (§9) → E2E ×2 (§10) → convergencia.
FR-OFFSQL-001…031 → T01–T04 → pruebas → mutaciones → evidencia: 100 %.

**`OFFLINE-NAIVE-EN-SQLITE — CLOSED / CONVERGED`.** Orquestación: 4 tareas `CLAUDE_ONLY`, 0 DeepSeek.
Hoja de ruta, `next-spec-decision.md` y recuento MASTER57 (57) actualizados; SPEC057 y NEXT MASTER SPEC sin
cambio; la política del arnés E2E y `ROLES-SIN-TECHO-DE-DELEGACION` siguen pendientes de la dueña.
