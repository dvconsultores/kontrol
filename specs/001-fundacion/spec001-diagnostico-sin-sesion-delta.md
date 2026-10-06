# SPEC 001 · Delta dirigida — DIAGNOSTICO-SIN-SESION

**Fecha** 2026-10-06 · **Dueña** SPEC001 (`001-fundacion`: FR-001-084 diagnóstico de
instalación; Master 002 seguridad y sesiones; Master 003 permisos; Master 005 navegación) ·
**Apoyo** Master 004 licenciamiento (`010-licenciamiento-central`, por el permiso), SPEC054
(certificación) · **Base** `ecb3c8a` · **Rama** `develop`

## 1. Checkpoint y dueñas

| | |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` | `ecb3c8a` / **`ecb3c8a`** / `ecb3c8a` · `develop` · árbol limpio · `COMMITS_AFTER_ECB3C8A = 0` |
| `ORCHESTRATION_STATUS` | `VERIFIED_END_TO_END`; `orchestration_readiness.py` 11/11 · `mcp__deepseek__deepseek_chat` · `deepseek-v4-flash` · `RETRY_MAX 2` |
| `PRIMARY_OWNER` | **SPEC001** — `specs/001-fundacion` (FR-001-084 y Masters 002, 003, 005 resuelven ahí según `spec-equivalence-map.md`) |
| `PERMISSION_OWNER` | Master 003 → `001-fundacion`; el permiso elegido pertenece al catálogo de la 004 (`license:*`), que también resuelve en `001-fundacion` + `010-licenciamiento-central` |
| `UI_OWNER` · `QA_OWNER` | Master 005 → `001-fundacion` · SPEC054 → `012-auditoria-integral-e2e` |
| `OWNER_IDENTITY_CONFLICT` | **0** |

**Decisión de la dueña, ya tomada:** el diagnóstico interno exige sesión válida y permiso
técnico/administrativo **existente**; los health checks necesarios siguen públicos, separados y
mínimos. Además, `.claude/CLAUDE.md` registra `qa/e2e-run.py` como comando canónico de
certificación E2E.

## 2. Inventario (W04–W15)

| | Hoy | Dónde |
|---|---|---|
| Ruta frontend | `/diagnostico` → `DiagnosticoPage`, bajo `RouteGuard` (exige sesión), **sin** permiso; en el menú «Sistema» para todo usuario | `router.tsx:140`, `Sidebar.tsx:251` |
| Endpoint interno | `GET /api/v1/system/diagnostics`: única dependencia `get_db`. **Anónimo** | `app/modules/system/api.py` |
| Health públicos | `GET /health/live` → `{status, service, version}` · `GET /health/ready` → `{status, service, database: ok\|unreachable}` (hace `SELECT 1`) | ídem |
| Consumidores de health | `Dockerfile.backend` HEALTHCHECK → `/health/live` · `qa/e2e_corrida.py` y `qa/e2e-latido.py` → `/health/ready` · `DashboardPage` → `/health/ready` (tarjeta «API») | |
| Autenticación | `get_current_user`: sin `Authorization: Bearer` → **401 `AUTH_REQUIRED`**; token ilegible o caducado → **401 `AUTH_INVALID_TOKEN`** | `app/core/dependencies.py` |
| Autorización | `require_permission(recurso, acción)` → **403 `PERMISSION_DENIED`**, cerrado por defecto. Sin ocultación por 404 | ídem |
| Catálogo de permisos | `setup/api.py::_bootstrap_roles`: 23 recursos. Ninguno se llama «sistema», «diagnóstico» ni «configuración». **`license:view`** existe en el catálogo, no lo exige ningún endpoint, y es lo que ya gobierna en el menú la sección «Licenciamiento» —configuración central, entitlements, renovación, eventos— (`Sidebar.tsx:221`) | |
| Alcance | el diagnóstico es **global de instalación**: entorno, versión, base, identidad de instalación y licencia. Ningún dato de tenant ni de empresa; no usa `CompanyContext` | |
| Auditoría | el acceso no genera eventos; no está en el contrato | |
| OpenAPI | **ninguna** de las 542 operaciones declara `security` y no hay `securitySchemes`: el patrón vigente es no declararlo | `openapi.json` |
| Pruebas existentes | ninguna sobre `/system/*` | |

### Reproducción, antes del arreglo (`evidence/diagnostico-sin-sesion/antes.txt`)

Pila completa sobre base nueva (`qa/e2e-run.py`):

| | |
|---|---|
| `FRONTEND_ROUTE` | `/diagnostico` sin sesión → `/login`, sin pintar nada (`RouteGuard`). Con sesión de administrador: menú con «Diagnóstico» y pantalla con Entorno, Base de datos, Instalación, Identificador, Licencia |
| `BACKEND_ENDPOINTS` | `GET /api/v1/system/diagnostics` |
| `ANON_STATUS` | **200**. Con `Authorization: Bearer no.es.un.token`: **200** también |
| `ANON_PAYLOAD` | `{"environment":"local","version":"1.0.0","database":{"ok":true},"installation":{"id":"KTL-VE-…","state":"ACTIVE"},"license":{"activated":true,"mode":"FULL_ACCESS","period_end":"…"},"storage":"/tmp/kontrol-e2e/<run>/storage"}` |
| `DATA_EXPOSED` | identidad de instalación, modo y vigencia de licencia, entorno, versión, estado de la base y la **ruta de almacenamiento del servidor** — contra el docstring del propio endpoint («no expone secretos, rutas internas…») |
| `route-crawl` | no lo detecta ni debe: recorre con sesión de administrador |
| refresh / URL directa / navegación | iguales entre sí: la protección es solo la de sesión del frontend; el backend no protege nada |

Hallazgo vecino, **no absorbido**: `GET /license/status` también responde sin sesión
(identificador de instalación, `license_id`, `kid`, fechas). Lo pide `LicenseContext` antes del
inicio de sesión, así que cerrarlo cambia el arranque de la aplicación: decisión de la dueña
(`LICENCIA-STATUS-SIN-SESION`, §13).

## 3. Modelo de amenaza

| Actor | Hoy | Debe |
|---|---|---|
| Anónimo, llamada directa | 200 con todo | 401 `AUTH_REQUIRED`, sin diagnóstico |
| Token malformado / caducado | 200 | 401 `AUTH_INVALID_TOKEN` |
| Sesión válida sin permiso | 200 | 403 `PERMISSION_DENIED`, sin diagnóstico |
| Sesión válida con `license:view` | 200 | 200 |
| Empresa equivocada o cabecera `X-Kontrol-Company` manipulada | irrelevante: no hay datos de empresa | el diagnóstico es global; la cabecera no concede ni cambia nada, y quien no tiene permiso sigue en 403 |
| Anónimo, URL del frontend | `/login` | igual |
| Sesión válida sin permiso, URL del frontend o menú | pantalla y entrada de menú visibles | `ForbiddenState`, sin petición al backend; sin entrada de menú |
| Recarga con permiso | se queda en `/diagnostico` (arreglado en `ecb3c8a`) | igual |

## 4. `/speckit.specify`

IDs propios de la Spec 001 (siguen a FR-001-225); entre paréntesis, el del encargo.

| ID | Requisito |
|---|---|
| FR-001-226 (DIAG-001) | El diagnóstico interno no está disponible a usuarios anónimos |
| FR-001-227 (002) | El backend exige autenticación válida: sin credenciales, 401 `AUTH_REQUIRED`; credenciales ilegibles o caducadas, 401 `AUTH_INVALID_TOKEN` |
| FR-001-228 (003) | El backend exige el permiso existente **`license:view`** (el del catálogo que gobierna la lectura de licencia e instalación) |
| FR-001-229 (004) | Si no existiera un permiso correcto, se detiene por decisión material antes de crear uno — **no aplica: existe** |
| FR-001-230 (005) | Un usuario autenticado sin permiso no obtiene el diagnóstico: 403 `PERMISSION_DENIED` |
| FR-001-231 (006) | El frontend protege navegación, URL directa y recarga |
| FR-001-232 (007) | El frontend no pinta ni pide el diagnóstico antes de confirmar la autorización |
| FR-001-233 (008) | El menú no muestra «Diagnóstico» a quien no tiene `license:view` |
| FR-001-234 (009) | `/health/live` y `/health/ready` siguen públicos y separados del diagnóstico |
| FR-001-235 (010) | Los health públicos exponen información mínima: su contrato actual, sin ampliarlo |
| FR-001-236 (011) | No se rompen los consumidores de health: Docker, el lanzador de QA, el panel |
| FR-001-237 (012) | El diagnóstico es global de instalación: no se inventa alcance de empresa y la cabecera de empresa no concede nada |
| FR-001-238 (013) | Ningún acceso anónimo o prohibido expone configuración, rutas internas, trazas ni infraestructura; el diagnóstico autorizado deja de responder la ruta de almacenamiento |
| FR-001-239 (014) | Pruebas hostiles directas contra el backend |
| FR-001-240 (015) | E2E para anónimo, sin permiso, autorizado, URL directa, recarga, menú, backend directo y health público |
| FR-001-241 (016) | La certificación E2E corre con `qa/e2e-run.py`, base nueva por corrida |
| FR-001-242 (017) | `.claude/CLAUDE.md` registra ese comando como canónico |
| FR-001-243 (018) | Esquema y migraciones: 0 |
| FR-001-244 (019) · FR-001-245 (020) | `E2E-BASE-QA-ACUMULA` y `E2E-FLAKY-BAJO-CARGA` no se reabren |

## 5. `/speckit.clarify` — 32 preguntas

| # | Pregunta | Respuesta, con evidencia |
|---|---|---|
| 1 | Dueña | §1 |
| 2–3 | Ruta y endpoint | `/diagnostico` · `GET /system/diagnostics` |
| 4–6 | Anónimo, carga, datos sensibles | §2: 200 con identidad de instalación, licencia y ruta de almacenamiento |
| 7 | Dependencia de auth actual | ninguna |
| 8 | Sistema de permisos | `require_permission(recurso, acción)` sobre `Permission`/`Role`/`UserRole`, cerrado por defecto |
| 9–10 | Permiso candidato y quién lo tiene | **`license:view`**. El catálogo no tiene un recurso de sistema o diagnóstico; `license:view` existe, cubre «leer identidad y licencia de la instalación», que es el contenido del diagnóstico (FR-001-084 nace del mismo DOC-07 que la licencia), y ya es el permiso de la sección «Licenciamiento» del menú. Lo tiene el rol `ADMIN` de cada tenant. No se crea permiso: `MATERIAL OQ = 0` |
| 11–12 | Alcance y `RequestContext` | global de instalación; no se exige empresa (sería inventar un alcance) |
| 13–17 | Health, consumidores, Docker, lanzador, carga | §2. `live` y `ready` siguen idénticos: su contrato lo usan Docker, el lanzador y el panel. `version` en `live` ya existía; no se amplía ni se recorta (`HEALTH-LIVE-VERSION`, observación, §13) |
| 18–19 | Guard y restauración | `RouteGuard` + `AuthProvider` (desde `ecb3c8a` no hay «listo» sin usuario, luego `hasPermission` es definitivo cuando la página se pinta) |
| 20 | UX de prohibido | `ForbiddenState` en la página, el patrón de `AlertasPage` y `ReglasPage` |
| 21 | Menú | `permission: "license:view"` en la entrada, como las entradas de la 047 |
| 22–23 | URL directa y recarga | sin sesión → `/login`; sin permiso → `ForbiddenState`; con permiso, recarga en la ruta (RESTAURA-01) |
| 24 | OpenAPI | no se declara `security` en ninguna operación; se sigue el patrón (`OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`, §13) |
| 25–29 | Pruebas | §7 |
| 30 | Esquema | 0 |
| 31 | DeepSeek | §8 |
| 32 | Gobernanza | una línea en «Comandos canónicos», sin direcciones ni secretos |

`MATERIAL OQ = 0` · `UNKNOWN = 0`.

## 6. `/speckit.plan` y compuerta

W01–W21 hechos (§1–§8). W22 backend: `require_permission("license", "view")` en el endpoint y
retirar `storage`. W23 frontend: `hasPermission` + `ForbiddenState` + `enabled` en la página;
`permission` en el menú. W24 health intactos. W25–W27 pruebas. W28 certificación con
`qa/e2e-run.py`. W29 `CLAUDE.md`. W30–W33 regresión, `analyze`, trazabilidad, convergencia.

Compuerta G01–G30: todas ✅ (§1 checkpoint y orquestación; §2 reproducción, endpoints, ruta,
health, consumidores, catálogo, permiso, alcance; §3 contratos; §5 estrategias; §7 pruebas y
mutantes; §8 tareas; esquema y migraciones 0; `MATERIAL OQ` 0; `UNKNOWN` 0; trazabilidad 100 %).
Principios: 6 (seguridad en backend), 10, 21, 22, 27. **PASS.** Checklist: 38 casillas, ninguna abierta.

## 7. Pruebas y mutaciones

Backend, `tests/test_system_access.py` (SQLite y PostgreSQL):

| ID | Caso | Req. |
|---|---|---|
| SYS-01 | sin credenciales: 401 `AUTH_REQUIRED`; el cuerpo no trae ninguna clave del diagnóstico | 226, 227 |
| SYS-02 | token ilegible: 401 `AUTH_INVALID_TOKEN` | 227 |
| SYS-03 | token caducado (firmado con la clave, `exp` en el pasado): 401 `AUTH_INVALID_TOKEN` | 227 |
| SYS-04 | sesión válida sin `license:view` (rol con todo lo demás): 403 `PERMISSION_DENIED`, sin diagnóstico | 230 |
| SYS-05 | sesión con `license:view`: 200 con **exactamente** `environment, version, database, installation, license`; sin `storage`; ningún valor con aspecto de ruta | 228, 238 |
| SYS-06 | la cabecera de empresa no cambia nada: con una empresa inventada el autorizado sigue en 200 y el no autorizado en 403 | 237 |
| SYS-07 | `/health/live` y `/health/ready` anónimos: 200 con sus claves exactas de hoy | 234, 235, 236 |
| SYS-08 | ningún health lleva ruta, DSN, host, nombre de base, tenant, empresa, usuario ni traza | 235 |

Frontend (Vitest): `DiagnosticoPage.test.tsx` gana F-02 (sin permiso: `ForbiddenState`, **sin
petición**) y F-03 (con permiso: pinta); `Sidebar.test.tsx` (nuevo): F-04/F-05 la entrada
«Diagnóstico» aparece solo con `license:view`, y las demás entradas de «Sistema» no cambian.
F-06 lo garantiza `RESTAURA-01` (nada se decide sin usuario) y F-02 (sin permiso, sin petición).

E2E, `e2e/diagnostico.spec.ts`, sobre base nueva: E2E-DIAG-01 anónimo en `/diagnostico` →
`/login`, sin «Versión»; -02 usuario sin permiso → `Acceso prohibido`, sin petición al
diagnóstico, y la API directa 403; -03 administrador → la pantalla; -04 recarga → sigue en la
ruta con el contenido; -05 menú: con permiso sí, sin permiso no; -06 backend anónimo 401;
-07 health anónimos 200; -08 health sin claves del diagnóstico ni rutas. El usuario sin permiso
lo crea `qa/rol_sin_permiso.py` (no hay API de alta de roles con permisos: `ROLES-SIN-API-DE-ALTA`, §13).

| Mutante | Cambio | Debe matarlo |
|---|---|---|
| M-01 | el endpoint vuelve a `get_db` solo | SYS-01..04, E2E-06 |
| M-02 | `get_current_user` en vez del permiso | SYS-04, SYS-06, E2E-02 |
| M-03 | la página no mira el permiso | F-02, E2E-02 |
| M-04 | el menú sin `permission` | F-04, E2E-05 |
| M-05 | la restauración se da por lista sin el usuario | RESTAURA-01 |
| M-06 | `/health/ready` exige sesión | SYS-07; el lanzador no arranca |
| M-07 | `/health/live` responde `storage` | SYS-08 |
| M-08 | alcance de empresa: no aplica (global) | — |
| M-09 | el diagnóstico vuelve a responder `storage` | SYS-05 |
| M-10 | la página pide el diagnóstico aunque no haya permiso | F-02 |

## 8. `/speckit.tasks` y `/speckit.analyze` previo

| ID | Tarea | Req. | EXECUTOR · MODEL | SEC | EGRESS | Ficheros |
|---|---|---|---|---|---|---|
| T01 | Reconciliación, inventario, reproducción, amenaza, diseño | todos | CLAUDE | YES | n-a | este documento |
| T02 | Endpoint protegido y sin ruta | 226–230, 237, 238 | CLAUDE | **YES** | n-a | `app/modules/system/api.py` |
| T03 | Pruebas hostiles de backend SYS-01..08 | 239 | CLAUDE | **YES** | n-a | `tests/test_system_access.py` |
| T04 | Página con permiso; menú con permiso | 231–233 | CLAUDE | **YES** | n-a | `DiagnosticoPage.tsx`, `Sidebar.tsx` |
| T05 | F-02, F-03 en `DiagnosticoPage.test.tsx` | 231, 232 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `DiagnosticoPage.test.tsx` |
| T06 | `Sidebar.test.tsx` F-04, F-05 | 233 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `src/layout/Sidebar.test.tsx` (nuevo) |
| T07 | `qa/rol_sin_permiso.py` | 240 | CLAUDE | **YES** | n-a | nuevo |
| T08 | `e2e/diagnostico.spec.ts` E2E-DIAG-01..08 | 240 | CLAUDE | **YES** | n-a | nuevo |
| T09 | `.claude/CLAUDE.md`: comando canónico | 242 | CLAUDE | NO | n-a | `.claude/CLAUDE.md` |
| T10 | Auditar y aplicar T05, T06; mutaciones | 239, 240 | CLAUDE | NO | n-a | — |
| T11 | Backend dirigido y completo; frontend completo; E2E dirigido y global con `qa/e2e-run.py` | 236, 241 | CLAUDE | NO | n-a | — |
| T12 | `analyze` final, trazabilidad, convergencia, hoja de ruta, Git | — | CLAUDE | NO | n-a | documentos |

`RETRY_MAX: 2` en T05 y T06; sus encargos llevan solo fragmentos de prueba: ni usuarios, ni
cabeceras, ni tokens reales. `analyze` previo: `BLOCKER` · `CRITICAL` · `CONTRADICTIONS` ·
`OWNER CONFLICT` = 0; huérfanos = 0; `MATERIAL OQ` = 0; `UNKNOWN` = 0; trazabilidad 100 %.

**Autorización de `implement`:** la del encargo `DIAGNOSTICO-SIN-SESION`.

## 9. Implementación

```
T02  [ANALYZE]  endpoint global de instalación sin dependencia alguna; catálogo sin recurso de sistema; license:view existe y gobierna la lectura de licencia
     [PLAN]     require_permission("license", "view") en la ruta; retirar `storage` del cuerpo; docstring que lo dice
     [CLASSIFY] CLAUDE_ONLY — autorización y frontera de health
     [EXECUTE]  Claude
     [TEST]     tests/test_system_access.py — 14 passed en SQLite y en PostgreSQL
     [STATUS]   COMPLETE

T03  [CLASSIFY] CLAUDE_ONLY — pruebas hostiles de seguridad (tokens firmados con la clave de prueba, roles)
     [EXECUTE]  Claude · SYS-01..08 · 14 casos
     [STATUS]   COMPLETE

T04  [PLAN]     DiagnosticoPage: `hasPermission(PERMISO_DE_DIAGNOSTICO)`; sin permiso, <ForbiddenState/> y `enabled: false`; Sidebar: `permission: "license:view"` en la entrada
     [CLASSIFY] CLAUDE_ONLY — autorización de ruta
     [EXECUTE]  Claude · [TEST] eslint y tsc limpios
     [STATUS]   COMPLETE

T05  [CLASSIFY] DEEPSEEK_ELIGIBLE · [EXECUTE] DeepSeek deepseek-v4-flash (1449/924 tokens, $0.000444) · [AUDIT] PASS · [TEST] DiagnosticoPage.test.tsx 6/6 · [STATUS] COMPLETE
T06  [CLASSIFY] DEEPSEEK_ELIGIBLE · [EXECUTE] DeepSeek deepseek-v4-flash (intento: 1753/1082, $0.000531; reintento: 1996/1042, $0.000554)
     [AUDIT]    REJECT (NAV-03 falla: el encargo decía que «Mi licencia» exige license:view y no es así — error de Claude) → RETRY 1 → PASS
     [TEST]     Sidebar.test.tsx 4/4 · [STATUS] COMPLETE
T07  [EXECUTE]  Claude · qa/rol_sin_permiso.py: usuario con todo el catálogo menos los permisos negados, en la base de la corrida · [STATUS] COMPLETE
T08  [EXECUTE]  Claude · e2e/diagnostico.spec.ts, E2E-DIAG-01..08 en seis pruebas · [TEST] 6/6 sobre base nueva · [STATUS] COMPLETE
T09  [EXECUTE]  Claude · .claude/CLAUDE.md «Comandos canónicos»: certificación E2E completa con qa/e2e-run.py; sin direcciones ni secretos · [STATUS] COMPLETE
```

Producto: `app/modules/system/api.py` (backend), `DiagnosticoPage.tsx`, `Sidebar.tsx` (frontend).
Esquema, migraciones, RBAC general, roles, health: 0. `playwright.config.ts`: 0.

## 10. Pruebas y mutaciones

| Suite | Casos | Autor |
|---|---|---|
| `tests/test_system_access.py` (SQLite y PostgreSQL) | 14 (SYS-01..08) | Claude |
| `DiagnosticoPage.test.tsx` (+DIAG-05, 06) · `Sidebar.test.tsx` (NAV-01..04) | 6 · 4 | DeepSeek |
| `e2e/diagnostico.spec.ts` (E2E-DIAG-01..08) | 6 pruebas | Claude |

**Mutaciones: 11 de 11** (`evidence/diagnostico-sin-sesion/mutaciones.txt`): las nueve del
plan que aplican (M-08 no aplica: no hay alcance de empresa) y dos más —otro permiso en el
backend, otro permiso en la pantalla—. Y una de extremo a extremo: con el backend abierto de
nuevo, E2E-DIAG-02 y E2E-DIAG-06 caen (200 donde debía haber 403 y 401): la protección del
frontend sola no basta, y la suite lo dice.

## 11. Resultados

### El contrato, después (`evidence/diagnostico-sin-sesion/`)

| Actor | `GET /system/diagnostics` | Pantalla `/diagnostico` | Menú |
|---|---|---|---|
| Anónimo | **401 `AUTH_REQUIRED`**, sin ninguna clave del diagnóstico | `/login`, sin pintar nada, sin petición | — |
| Token ilegible o caducado | **401 `AUTH_INVALID_TOKEN`** | — | — |
| Sesión válida sin `license:view` | **403 `PERMISSION_DENIED`** | `Acceso prohibido`, en `/diagnostico`, **sin petición** | sin «Diagnóstico» |
| Sesión con `license:view` | 200: `environment, version, database, installation, license` — **sin `storage`** | la pantalla; recargar la mantiene | con «Diagnóstico» |
| Cabecera `X-Kontrol-Company` inventada | no cambia nada: 200 igual al autorizado; 403 al no autorizado; 401 al anónimo | | |
| `/health/live`, `/health/ready` anónimos | 200, exactamente las claves de hoy; nada del diagnóstico ni del servidor | | |

Docker (`/health/live`), el panel (`/health/ready`) y el lanzador de QA (`/health/ready`)
siguen funcionando: las tres corridas globales arrancaron el backend con ese health.

### Certificación E2E, base nueva por corrida (`corridas-globales.txt`)

| Corrida | Resultado | Suite | Limpieza |
|---|---|---|---|
| dirigida `diagnostico.spec.ts` | **6 / 0** | 4,7 s | LIMPIA |
| global 1 | 199 / **7** / 40 | 211 s | LIMPIA |
| global 2 | **206 / 0 / 40** | 204 s | LIMPIA |
| global 3 | **206 / 0 / 40** | 170 s | LIMPIA |

La suite tiene ahora 246 pruebas (6 nuevas); las 40 omitidas son las de `KONTROL_E2E_USER`
(`E2E-CUARENTA-OMITIDAS`, abierta). 0 bases de corrida al terminar.

**Los 7 fallos de la corrida 1 no son del producto ni de las pruebas: `EXTERNAL_ENVIRONMENT`.**
El manifiesto de la corrida empieza a las 04:56 UTC y acaba a las 10:08 UTC con una suite de
211 s: **el reloj del equipo saltó +5 h 08 min** durante la corrida (NTP, tras el reinicio del
2026-10-04 que vació `/tmp`). Con el salto llegó un cambio de red: la traza de
`sales-orders.spec.ts:167` muestra los módulos de la aplicación abortados por Chromium con
`net::ERR_NETWORK_CHANGED` —es el «login en blanco» de `E2E-PANTALLA-SIN-PINTAR`, esta vez con
traza—, y seis pruebas de `returns.spec.ts` recibieron a la vez `401 AUTH_INVALID_TOKEN` con
tokens recién emitidos: un token dura 15 minutos y el reloj avanzó cinco horas entre emitirlo y
usarlo. El backend no registró ningún error; `diagnostico.spec.ts` pasó 6/6 en las tres
corridas; las dos siguientes, con el reloj estable, 206/0/40.

### Backend y frontend (`backend-y-frontend.txt`)

PostgreSQL: 1 985 pasan · 27 omitidas · 37 fallan, la misma composición que en `ecb3c8a`
(documentos sin `clamscan`), 14 pruebas nuevas. SQLite: 1 001 · 1 005 · 43: los 42 de
documentos y uno de los dos intermitentes conocidos de SQLite con hilos. Tras la corrida en
PostgreSQL: 0 schemas temporales, 0 conexiones, 0 bases de corrida. Frontend: 447 pruebas,
`eslint` y `tsc` limpios; `vite build` correcto.

## 12. Deudas

| Deuda | Estado tras este ciclo |
|---|---|
| **`DIAGNOSTICO-SIN-SESION`** | **CLOSED / CONVERGED** |
| `E2E-PANTALLA-SIN-PINTAR` | **explicada** (`ERR_NETWORK_CHANGED`: red y reloj del equipo); sigue **OPEN** como observación de entorno: no hay cambio de producto ni de prueba que la cierre |
| `E2E-BASE-QA-ACUMULA` · `E2E-NOTIFICACIONES-REGLAS-VIVAS` · `E2E-FLAKY-BAJO-CARGA` · `TEST-SCHEMAS-PG-SIN-LIMPIEZA` | siguen **CLOSED / CONVERGED** |
| `ENTORNO-SIN-CLAMSCAN` · `E2E-CUARENTA-OMITIDAS` · `BACKEND-KEEPALIVE-5S` · `INSTALACION-KEY-REFERENCE-120` · `MIGRACIONES-URL-CON-PORCENTAJE` · `ALMACENES-CARRERA-SQLITE-HILOS` · las demás | **OPEN**, sin tocar |

Nuevas, encontradas y **no absorbidas**:

| Deuda | Qué |
|---|---|
| **`LICENCIA-STATUS-SIN-SESION`** | `GET /license/status` responde sin sesión identificador de instalación, `license_id`, `kid` y fechas; lo pide la pantalla de acceso. Decisión de la dueña |
| **`LICENCIA-LECTURA-SIN-PERMISO`** | las lecturas de licenciamiento exigen sesión pero no `license:view`, aunque el permiso existe y el menú lo usa |
| **`ROLES-SIN-API-DE-ALTA`** | `roles:create` y `roles:edit` existen en el catálogo; la API solo lista roles y los asigna |
| **`OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`** | 0 de 542 operaciones declaran `security`; sin `securitySchemes` |
| **`HEALTH-LIVE-VERSION`** | `/health/live` público publica `version`; lo usa Docker. No se amplía ni se recorta: decisión de la dueña |

## 13. Veredicto

**`DIAGNOSTICO-SIN-SESION`: cerrada.** El diagnóstico de la instalación exige sesión y el
permiso existente `license:view` en el backend —que es la autoridad: 401 y 403 según el
caso— y lo respetan la pantalla y el menú; ya no responde la ruta de almacenamiento. Los
health checks públicos siguen separados, mínimos y como estaban. Sin permiso nuevo, sin rol
nuevo, sin esquema, sin migración. `.claude/CLAUDE.md` registra `qa/e2e-run.py` como comando
canónico de certificación E2E.

| | |
|---|---|
| `ANONYMOUS_DIAGNOSTICS_ACCESS` · `AUTHENTICATED_UNAUTHORIZED_ACCESS` · `FRONTEND_ONLY_SECURITY` · `ROLE_NAME_HARDCODE` | 0 |
| `TENANT_LEAK` · `COMPANY_LEAK` | 0 (no hay datos de tenant ni de empresa; la cabecera no concede nada) |
| `PROTECTED_CONTENT_FLASH` · `PUBLIC_HEALTH_BROKEN` · `HEALTH_SENSITIVE_DISCLOSURE` · `E2E_FRESH_DB_REGRESSION` | 0 |
| `PRODUCT_SCHEMA_CHANGE` · `PRODUCT_MIGRATION` · `RETRY_WORKAROUND` · `SLEEP_WORKAROUND` · `SKIP_WORKAROUND` | 0 |
| `STATUS` | **`CONVERGED`** |

## 14. `analyze` final y trazabilidad

| Requisito | Prueba o evidencia | |
|---|---|---|
| 226, 227 anónimo y credenciales | SYS-01..03, E2E-DIAG-01, 06 | ✅ |
| 228, 230 permiso existente; sin permiso 403 | SYS-04, SYS-06, E2E-DIAG-02; M-02, M-02b | ✅ |
| 229 sin permiso correcto, parar | no aplica: `license:view` existe | ✅ |
| 231, 232 frontend: navegación, URL directa, recarga; sin petición antes de autorizar | DIAG-05, E2E-DIAG-01, 02, 04; RESTAURA-01; M-03, M-10 | ✅ |
| 233 menú | NAV-01..04, E2E-DIAG-02, 03/05; M-04 | ✅ |
| 234–236 health públicos, mínimos, consumidores | SYS-07, SYS-08, E2E-DIAG-07/08; M-06, M-07; tres arranques del lanzador | ✅ |
| 237 global de instalación | SYS-06 | ✅ |
| 238 sin ruta ni infraestructura | SYS-05, SYS-08; M-09 | ✅ |
| 239, 240 pruebas hostiles y E2E | 14 + 6 | ✅ |
| 241, 242 certificación con `qa/e2e-run.py`; `CLAUDE.md` | tres corridas; diff de `.claude/CLAUDE.md` | ✅ |
| 243 esquema y migraciones | 0 | ✅ |
| 244, 245 nada se reabre | `qa/e2e_*` sin cambios; corridas 206/0/40 | ✅ |

`BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` = 0 · huérfanos = 0 · `MATERIAL OQ` = 0 ·
`UNKNOWN` = 0 · trazabilidad 100 %.

Desviaciones mías, dichas: el encargo de T06 afirmaba que «Mi licencia» exige `license:view`
(no es así; lo gobierna la sección «Licenciamiento»): un rechazo y un reintento por mi culpa.
Dos órdenes mías escribieron un fichero en una carpeta equivocada por un cambio de directorio
entre llamadas; se movió antes de ejecutar nada. La corrida global 1 se hizo con el reloj del
equipo mal; su atribución está en §11.

Orquestación (`orquestacion.txt`): 12 tareas · 10 `CLAUDE_ONLY` · 2 `DEEPSEEK_ELIGIBLE`,
ejecutadas por DeepSeek (`deepseek-v4-flash`) · 3 llamadas · 1 reintento · 2 parches aceptados,
1 rechazado, 0 retocados · 5 198 / 3 048 tokens · $0,001529 · puente: 70 927 tokens ·
`EXECUTOR_ABRIDGEMENT`: no se reprodujo.
