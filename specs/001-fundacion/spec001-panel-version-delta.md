# SPEC 001 · DELTA DIRIGIDO — LA TARJETA «VERSIÓN» DE INICIO Y LA AUTORIDAD DE LA VERSIÓN

> Iniciado el 2026-10-08. Dueña: **Spec 001 — Fundación** (`001-fundacion`; FR-001-084: el diagnóstico
> reporta «versión»; FR-001-042: el backend es la autoridad de acceso); apoyos **004** (la solicitud de
> activación lleva la «versión del producto», ADR-D0-006 R-D0-06-4; el permiso `license:view`), **005**
> (la tarjeta de Inicio) y **054** (QA/E2E). Deuda: `PANEL-VERSION-VACIA`. MASTER57, 057, D0-07, 039–043 y
> 056 no se tocan. No se reabre nada cerrado. El 502 de `kontrol.globaldv.net` queda fuera: no se toca
> producción ni se le atribuye esta deuda.
>
> **Objetivo:** localizar el panel y la cadena completa de la versión, probar su semántica y su
> autoridad, y corregir la causa real sin inventar un número, sin hash fijo, sin `.git` en producción y
> sin ampliar la exposición pública.

## 1. Checkpoint y dueñas

| | |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` / `ACTUAL_BRANCH` / `WORKTREE_STATE` | `ff5e648` / **`ff5e648`** / `ff5e648` / `develop` / limpio · `COMMITS_AFTER_FF5E648 = 0` · `RUN_DATABASES = 0` · puertos 8000/8010/5173 libres |
| Dueñas | 001 primaria (FR-001-084, FR-001-042); 004 (solicitud de activación, `license:view`); 005 (tarjeta); 054 (QA) · `OWNER_IDENTITY_CONFLICT = 0`. 052 no tiene directorio de Spec: la imagen (`Dockerfile.backend`) se trata como apoyo documental |
| Punteros | `NEXT TECHNICAL CYCLE = PANEL-VERSION-VACIA` (este) · `NEXT MASTER SPEC = NOT YET PRIORITIZED` |

## 2. Descubrimiento (W03–W11) — el panel, la cadena y la reproducción

| Registro | Valor |
|---|---|
| `PANEL_ROUTE` / `PANEL_COMPONENT` / `FIELD_LABEL` | `/` (Inicio) · `resources/frontend/src/pages/DashboardPage.tsx` · tarjeta **«Versión»** |
| `DISPLAYED_VALUE` (antes) | **«—»** siempre: `health.data?.version ?? "—"` |
| `API_REQUEST` / `API_RESPONSE` (antes) | `GET /api/v1/health/ready` → `{"status","service","database"}`: **nunca trajo `version`** (D4 de `HEALTH-LIVE-VERSION`: ready es mínimo) |
| Tipo del frontend (antes) | `HealthResponse { status; services: Record; version }`: no coincidía con lo que `ready` responde (el `services` que `DiagnosticoPage` ya tuvo que dejar de esperar) |
| `BEFORE_UI_VALUE` / `BEFORE_API_VALUE` / `BEFORE_SOURCE_VALUE` | «—» / sin campo / `1.0.0` |

**La cadena, paso a paso (antes):**

| Paso | Fichero · símbolo | Entrada → salida | Fallback |
|---|---|---|---|
| `VERSION_SOURCE` | `app/__init__.py:__version__ = "1.0.0"` · `pyproject.toml version = "1.0.0"` · `Settings.app_version = "1.0.0"` (literal propio, **leído de `KONTROL_APP_VERSION` si existiera**) · `central_authority.__version__` (otro componente) · `frontend/package.json 1.0.0` (paquete del frontend, no se muestra) | tres literales iguales para la misma cosa, sin contrato que los una | — |
| `BUILD_INJECTION` | **ninguna**: `Dockerfile.backend` copia `app/`, `alembic/`, `entrypoint.sh`; **no** copia `pyproject.toml`; sin ARG/ENV de versión; sin `.git` en la imagen; CI no inyecta nada; `git tag`: **ninguno** | — | — |
| `BACKEND_MODEL` | `get_settings().app_version` | `1.0.0` | — |
| `API_CONTRACT` | `GET /system/diagnostics` (`license:view`) → `version` · `installation_request_payload` → `version` (solicitud de activación, ADR-D0-006) · OpenAPI `info.version` · **`GET /` raíz, público** → `version` | el diagnóstico es la vía ratificada (D3: «la versión la da el diagnóstico, con `license:view`»); la raíz pública la publicaba sin que nadie la hubiera decidido | — |
| `FRONTEND_QUERY` | `DashboardPage` → `/health/ready` (incorrecto) · `DiagnosticoPage` → `/system/diagnostics` (correcto, `enabled: permitido`) | | «—» |
| `UI_COMPONENT` / `RENDERED_VALUE` | `indicatorCard("Versión", …)` | «—» | «—» |

### Compuertas materiales

| Compuerta | Veredicto | Por qué |
|---|---|---|
| `PANEL_SOURCE` | **PROVEN** | la tarjeta de Inicio lee un campo que su endpoint no responde |
| `VERSION_SEMANTICS` | **PROVEN** | **versión del producto** (del backend KONTROL que corre): FR-001-084 («versión» del diagnóstico de la instalación), ADR-D0-006 R-D0-06-4 («la autoridad recibe … **versión del producto**» en la solicitud de activación), `license.minimum_version` del contrato de licencia se expresa contra ella. Forma SemVer (`1.0.0`). **Solo informativa** en la UI: no existe comparación de versiones en el código (`minimum_version` se guarda y se muestra, no se compara) y no se añade ninguna. No es commit, ni tag, ni build: el contrato pide una versión, no un identificador de despliegue |
| `VERSION_AUTHORITY` | **PROVEN** | `app/__init__.py:__version__`: es lo único que viaja dentro del artefacto desplegado (`Dockerfile.backend` no copia `pyproject.toml`), no depende de `.git` ni de CI, y ya era lo que `Settings` duplicaba. Jerarquía explícita: `__version__` manda; `pyproject.toml` la refleja (guard); `Settings.app_version` se deriva (sin literal ni variable de entorno); el frontend la **presenta**, no la define. `central_authority.__version__` y `package.json` son versiones de **otros** paquetes, deliberadamente independientes y no mostradas |
| `ROOT_CAUSE` | **PROVEN** | **F) FRONTEND_QUERY_BUG** (la tarjeta pedía la versión a `ready`) agravada por **D) API_CONTRACT** del tipo `HealthResponse` (declaraba campos que `ready` nunca tuvo) y **H) EMPTY_FALLBACK_BUG** («—» como estado permanente). Hallazgos laterales del mismo descubrimiento: literal duplicado y puerta de entorno en `Settings`, y la raíz pública publicando la versión contra D3 |
| Exposición | PROVEN | la tarjeta vive tras el login; la versión solo se pide con `license:view` (como el enlace a «Mi licencia» y `DiagnosticoPage`); nada nuevo público; la raíz pública **deja** de publicarla (alineación con D3, misma dueña que decidió `HEALTH-LIVE-VERSION`) |
| Instalador / actualización | sin impacto | no existe lógica de actualización ni comparación de versiones en el repositorio; la solicitud de activación sigue llevando la misma versión |
| Esquema | 0 / 0 | ninguna tabla guarda la versión |

## 3. `/speckit.specify` — FR-001-VER-001..028

001 la tarjeta nunca pinta vacío/nulo/`undefined` · 002 semántica: versión del producto (§2) · 003
autoridad única `app.__version__`, `pyproject` la refleja · 004 el frontend no la inventa (fallback
«No disponible», constante única) · 005 corresponde al artefacto que corre (viaja en `app/`) · 006–007
sin hash de commit (no hay build id en el contrato; guard estático contra el SHA actual) · 008–009 sin
`.git` ni `git` en tiempo de ejecución · 010 desarrollo muestra la del paquete (es verdadera: es la del
código que corre) · 011 metadato ausente → «No disponible», nunca `""` · 012 health sin cambio · 013
permiso del diagnóstico sin cambio · 014 sin exposición pública nueva; la raíz pública deja de
publicarla · 015 activación/sync sin cambio · 016 SemVer vigilado por guard · 017 solo presentación: sin
comparador · 018 estados cargando/error/vacío · 019 sin modal · 020–021 sin secretos ni rutas · 022
esquema 0 · 023–025 licencia, sync y keep-alive 75 s sin cambio · 026–028 MASTER57, 057 y puntero sin cambio.

## 4. `/speckit.clarify` — 34 preguntas, `MATERIAL OQ = 0`

1–8 §2 · 9–12 semántica: producto, SemVer, sin build id, sin tags · 13–14 sin CI ni Docker que inyecte ·
15–16 dev y prod muestran lo mismo: la versión del código que corre · 17 `.git` **no** está en la imagen ·
18–20 diagnóstico: `license:view`, contrato con `version` ya existente · 21 sin instalador/actualizador
· 22 SemVer vigilado, sin comparación · 23–24 estados: cargando → «Cargando…», error/vacío → «No
disponible», sin permiso → la tarjeta no existe (precedente: el enlace a «Mi licencia» y
`DiagnosticoPage`, Q17/Q18 del delta de preauth) · 25–26 versión y build quedan distintos porque no hay
build: no se inventa · 27 `app.__version__` · 28–29 build local y Docker leen el mismo fichero · 30 el
runner E2E no cambia · 31–32 pruebas VER y mutaciones M-01..13 (backend con pytest, frontend con vitest)
· 33 esquema 0 · 34 DeepSeek: **0** (la tarea es diagnóstico + decisión de autoridad + cambios
dictados; nada separable con contrato cerrado que no sea dictado).

## 5. `/speckit.plan`, compuerta, checklist, tareas

Backend: `Settings.app_version` pasa a propiedad derivada de `app.__version__` (sin literal ni variable
de entorno); la raíz `/` responde `{service, status}`; el diagnóstico, OpenAPI y la solicitud de
activación siguen leyendo `settings.app_version`. Frontend: `HealthResponse` = `{status, service,
database}`; `DashboardPage` pide el diagnóstico solo con `license:view` (`enabled`), pinta
`versionMostrada` (string no vacío o «No disponible»), «Cargando…» mientras llega, «No disponible» si
falla, y sin permiso no pinta la tarjeta. Pruebas: `tests/test_system_version.py` (VER-02, 02b, 03, 03b,
08, 09, 13, 16, 18), `src/pages/DashboardPage.test.tsx` (VER-04, 05, 05b, 06, 10, 11, 13, 16),
`e2e/inicio-version.spec.ts` (E2E-VER-01, 02, 04). **Compuerta G01–G29: PASS.** Tareas: T01
descubrimiento/Spec Kit · T02 backend · T03 frontend · T04 pruebas y E2E · T05 mutaciones, suites, E2E
global ×2 (cambia la pantalla de Inicio, común a todos), docs, Git. `analyze` previo: `BLOCKER = CRITICAL =
CONTRADICTIONS = OWNER CONFLICT = 0`, huérfanos 0, `MATERIAL OQ = 0`, `UNKNOWN = 0`, trazabilidad 100 %.
**Autorización de `implement`:** la del encargo (las cuatro compuertas PROVEN).

## 6. Implementación (T02, T03)

- **Autoridad** · `app/core/config.py`: `app_version` deja de ser un campo con literal propio (y, por
  serlo, una variable de entorno `KONTROL_APP_VERSION` que nadie documentaba y que podía declarar una
  versión distinta de la del código) y pasa a ser una **propiedad** que devuelve `app.__version__`. Los
  tres lectores —diagnóstico, OpenAPI (`FastAPI(version=…)`) y la solicitud de activación— no cambian:
  siguen leyendo `settings.app_version`. `pyproject.toml` conserva `1.0.0` y una guarda exige que las
  dos coincidan (las dos suben juntas; la imagen solo lleva `app/`). Sin lectura de `pyproject` en
  tiempo de ejecución (no está en la imagen), sin `importlib.metadata` (el paquete no está instalado),
  sin `git`.
- **Raíz pública** · `app/main.py`: `GET /` responde `{service, status}`; retira `version`, alineado con
  D3 (`HEALTH-LIVE-VERSION`: la versión solo con sesión y `license:view`). nginx nunca enruta `/` al
  backend, así que en producción tras el proxy no cambia nada observable; sin proxy, deja de publicarse.
- **Frontend** · `src/api/types.ts`: `HealthResponse = {status, service, database}` (lo que `ready`
  responde). `src/pages/DashboardPage.tsx`: `PERMISO_DE_VERSION = "license:view"`,
  `VERSION_NO_DISPONIBLE = "No disponible"`, `versionMostrada()` (string no vacío → tal cual; cualquier
  otra cosa → «No disponible»); consulta `["diagnostics"]` → `/system/diagnostics` con `enabled:
  puedeVerVersion` y `retry: false` (la misma clave que `DiagnosticoPage`: una sola petición, caché
  compartida); la tarjeta pinta «Cargando…», la versión o «No disponible», y **no se pinta** sin
  permiso. La tarjeta «API» sigue leyendo `ready`.
- **Lo que no cambia** · health (`live`, `ready`), permiso y contrato del diagnóstico, licencia, sync,
  límite de tasa, keep-alive 75 s, esquema cliente y central, `central_authority.__version__` y
  `package.json` (otros paquetes). **DeepSeek: 0 llamadas** (todo dictado o decisión).

## 7. Pruebas y mutaciones (T04, T05)

| Suite | Casos | Motor |
|---|---|---|
| `tests/test_system_version.py` | VER-02 autoridad SemVer, `Settings` derivado, `pyproject` igual, sin campo `app_version`; VER-02b `KONTROL_APP_VERSION=9.9.9` no cambia nada; VER-03 el diagnóstico publica `__version__` con sesión y permiso; VER-13 raíz `/`, `live`, `ready` sin versión; 401 sin sesión; 403 sin `license:view` y sin versión en el cuerpo; VER-03b la solicitud de activación lleva `__version__`; VER-16 `__version__ = 7.3.1` (monkeypatch) llega al diagnóstico sin tocar la cadena y no a la raíz; VER-08 el SHA del commit actual no está en `app/` ni en `frontend/src`; VER-09 el producto no ejecuta `git`; VER-18 arranque sin `pyproject` ni `.git` alcanzables | SQLite y PostgreSQL |
| `src/pages/DashboardPage.test.tsx` | VER-04 con permiso pinta la versión del diagnóstico (y la pide ahí); VER-10 «Cargando…», nunca «—»; VER-05 espacios → «No disponible»; VER-06 `null`/ausente/número → «No disponible» (y `versionMostrada` puro); VER-05b error → «No disponible», sin `1.0.0`; VER-13 sin permiso: sin tarjeta y sin petición; VER-11 la tarjeta «API» sigue con `ready`; VER-16 refleja cualquier versión publicada | Vitest |
| `e2e/inicio-version.spec.ts` | E2E-VER-01 Inicio pinta la versión que responde el diagnóstico (SemVer), sin «—»; E2E-VER-02 usuario sin `license:view` (fabricado por `qa/rol_sin_permiso.py`): sin tarjeta y 0 peticiones al diagnóstico; E2E-VER-04 health y raíz mínimos y sin versión; diagnóstico 401 sin sesión | chromium, autoridad y base reales de la corrida |
| Regresión | `test_system_access` (SYS-01..08), `test_license_access`, `test_licensing_central`, `DiagnosticoPage.test.tsx`, suites completas, E2E global ×2 | — |

**Mutaciones** (`evidence/panel-version/mutaciones.txt`; backend con pytest y purga de `__pycache__` +
`PYTHONDONTWRITEBYTECODE=1`, frontend con Vitest; GOOD → PASS 30/30 pytest y 8/8 vitest antes de mutar):
M-01 el proveedor devuelve `""` · M-02 la tarjeta pinta la versión en crudo · M-03 el diagnóstico publica
un literal · M-04 el SHA del commit actual escrito en el producto · M-05 `KONTROL_APP_VERSION` manda · M-06
el frontend inventa `1.0.0` · M-07 la tarjeta vuelve a leer el health · M-08 `/health/live` publica la
versión · M-09 el diagnóstico sin permiso · M-10 la tarjeta a quien no puede · M-11 `pyproject` diverge ·
M-12 la imagen pierde el keep-alive 75 s · M-13 la raíz pública publica la versión. Resultado: **13/13
muertas**, RESTORED → PASS en las trece. **E2E dirigido** (`e2e-dirigido-inicio-version.txt`, proyecto
`chromium`, `--no-deps`): **3/3**, limpieza LIMPIA.

## 8. Resultados

La cadena de certificación se interrumpió una vez con la sesión (quedaron solo mutaciones y E2E dirigido);
se validó el árbol intacto, se relanzó el PostgreSQL de QA (caído tras un reinicio) y se repitió la cadena
completa el 2026-10-12.

| Gate | Resultado |
|---|---|
| Dirigidas (`tests/test_system_version.py` + `test_system_access.py`) | **23 passed** |
| Backend completo SQLite (`backend-sqlite-completo.txt`) | **43 failed / 1445 passed / 1020 skipped** = 42 documentales sin `clamscan` + `test_auth_session_rotation::test_dos_renovaciones_simultaneas…` (intermitente SQLite ya registrado en la línea base; dirigido 1/1); +9 nuevas; **0 regresiones** |
| Backend completo PostgreSQL (`backend-postgres-completo.txt`, 24 min 10 s) | **39 failed / 2442 passed / 27 skipped** = 35 documentales + 2 `n9_integrity` (línea base 37) + `test_sync_success_records_run_snapshot_and_event` y `test_e2ecorrida_01` (los dos intermitentes del arnés clasificados en el ciclo anterior; **dirigido 2/2**, `repeticion-dirigida-pg.txt`). Clasificación: C ×3; **A (regresión del ciclo): 0; E (desconocido): 0**; ninguno absorbido |
| `ruff check app tests` | limpio tras retirar un import sin uso en `tests/central/test_central_challenge_rate_limit_pg.py` (defecto mío del ciclo de límite de tasa, no de este; declarado). `qa/` tiene 29 avisos preexistentes en guiones de reproducción que este ciclo no toca |
| `mypy` (módulos tocados) | limpio |
| Frontend (`frontend-gates.txt`) | typecheck OK · lint OK · **467/467** (459 + 8 de `DashboardPage.test.tsx`) · build OK |
| Mutaciones (`mutaciones.txt`) | **13/13 muertas** (pytest y Vitest), RESTORED → PASS |
| E2E dirigido (`e2e-dirigido-inicio-version.txt`) | **3/3** (E2E-VER-01, 02, 04), limpieza LIMPIA |
| E2E global ×2 (`e2e-global-1.txt`, `e2e-global-2.txt`) | **235 passed / 0 failed / 40 skipped** y **235 / 0 / 40** (232 + 3); bases `r20261012t013311…` y `r20261012t013705…`, limpieza LIMPIA; puertos 8000/8010/5173 libres al cierre |
| Bases de corrida al cierre | **0** |
| Reproducción antes/después | `BEFORE_UI_VALUE` «—» · `BEFORE_API_VALUE` sin campo en `ready` · `BEFORE_SOURCE_VALUE` `1.0.0` → `AFTER_UI_VALUE` = la versión del diagnóstico (E2E-VER-01), «No disponible» o «Cargando…»; sin permiso, sin tarjeta |
| Esquema cliente / central · health · diagnóstico (permiso) · licencia · sync · keep-alive | **0 / 0 · 0 · 0 · 0 · 0 · 75 s intacto** (VER-20 vía `test_backend_keepalive`) |
| Docker | no disponible en esta máquina: no se afirma `docker build`; la imagen solo copia `app/`, y VER-18 prueba el arranque sin `pyproject` ni `.git` |

## 9. `analyze` final, trazabilidad y veredicto

`version empty/null/undefined/"" = 0` (VER-05/06/10, `versionMostrada`) · `hardcoded version = 0` (un
solo literal: `app/__init__.py`, por diseño) · `hardcoded sha = 0` (VER-08) · `git rev-parse/describe
runtime = 0` (VER-09) · `.git dependency = 0` (VER-18) · `duplicate version sources = 0` (`Settings`
derivado; `pyproject` espejo con guard; `central_authority` y `package.json` son otros paquetes) ·
`public version leak = 0` (raíz `/` y health sin versión: VER-13, E2E-VER-04) · `diagnostics permission
bypass = 0` (401/403: VER-13, SYS-01..08) · `stale build metadata = 0` (VER-16) · `fabricated fallback = 0`
(M-06 muerta) · `installer/update regression = 0` (no existe tal lógica) · `licensing/keepalive regression
= 0` · `schema migration = 0` · `production 502 changes = 0` · `fiscal = 0` · `SPEC057 = 0` · `NEXT MASTER
SPEC = 0` · `BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0` · huérfanos 0 · `MATERIAL OQ = 0` ·
`UNKNOWN = 0` · trazabilidad 100 %.

| Deuda | Estado |
|---|---|
| `PANEL-VERSION-VACIA` | **CLOSED / CONVERGED** (2026-10-12; implementación del 2026-10-08) |
| Intermitentes del arnés (`test_dos_renovaciones_simultaneas…`, `test_sync_success…`, `test_e2ecorrida_01`) | OPEN, clasificados, no absorbidos |
| Avisos `ruff` en `qa/` (guiones de reproducción, preexistentes) | fuera de este ciclo; anotados |
| Resto del encargo | OPEN, sin cambio |
| MASTER57 · SPEC057 · D0-07 · 039–043 · 056 · NEXT MASTER SPEC | sin cambio |

Orquestación: 5 tareas, `CLAUDE_ONLY` 5, `DEEPSEEK_ELIGIBLE` 0, **DeepSeek 0 llamadas**.

| FR (001-VER) | Dónde | Prueba / mutación |
|---|---|---|
| 001, 011, 018 nunca vacío; estados | `versionMostrada`, tarjeta | VER-04/05/05b/06/10; E2E-VER-01; M-02, M-10 |
| 002, 003, 005, 016 semántica, autoridad, artefacto, SemVer | `app.__version__`, `Settings.app_version` (propiedad), guard `pyproject` | VER-02, 02b, 03, 03b, 18; M-01, M-03, M-05, M-11 |
| 004 el frontend no inventa | `VERSION_NO_DISPONIBLE` | VER-05b; M-06 |
| 006–009 sin SHA, sin `.git`, sin `git` | — | VER-08, 09, 18; M-04 |
| 012–014 health y raíz sin versión; permiso intacto; sin exposición nueva | `main.py` raíz, `system/api.py` | VER-13, SYS-01..08, E2E-VER-02/04; M-08, M-09, M-13 |
| 017 solo presentación | sin comparador | §2 |
| 019–021 sin modal, sin secretos ni rutas | tarjeta; diagnóstico ya saneado | SYS-05 |
| 022–025 esquema, licencia, sync, keep-alive | sin cambio | suites completas; VER-20 (`test_backend_keepalive`); M-12 |
| 026–028 MASTER57, 057, puntero | docs | §9 |

**Veredicto: `PANEL-VERSION-VACIA — CLOSED / CONVERGED`.**
