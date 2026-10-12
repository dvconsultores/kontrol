# SPEC 001 · DELTA DIRIGIDO — EL OPENAPI DECLARA LA AUTENTICACIÓN REAL

> Iniciado el 2026-10-12. Dueña: **Spec 001 — Fundación** (`001-fundacion`: FR-001-020/021 definen la
> autenticación —access token de corta duración en cabecera, refresh en cookie HttpOnly— y
> `app/core/dependencies.py` es suyo; la hoja de ruta la registra como dueña 001). Apoyos: 002/003 solo
> como dominio funcional (sesión, permisos, alcance), que **no cambia**; 054 (QA); 055 (endurecimiento
> del contrato). Deuda: `OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`. MASTER57, 057, D0-07, 039–043 y 056 no se
> tocan. Producción (502) fuera de este ciclo.
>
> **Objetivo:** que el contrato OpenAPI describa fielmente el mecanismo de autenticación que ya
> protege las rutas —qué operaciones exigen credencial y por qué transporte— sin cambiar la
> autenticación, la sesión, los permisos, el `RequestContext`, `X-Kontrol-Company` ni ninguna ruta.

## 1. Checkpoint y dueñas

| | |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` / `ACTUAL_BRANCH` / `WORKTREE_STATE` | `0aa0310` / **`0aa0310`** / `0aa0310` / `develop` / limpio · `COMMITS_AFTER_0AA0310 = 0` · `RUN_DATABASES = 0` · puertos 8000/8010/5173 libres |
| Dueñas | 001 primaria; 002/003 dominio (sin cambio); 054 QA; 055 endurecimiento · `OWNER_IDENTITY_CONFLICT = 0` |
| Punteros | `NEXT TECHNICAL CYCLE = OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD` (este) · `NEXT MASTER SPEC = NOT YET PRIORITIZED` |

## 2. Descubrimiento (W03–W11) — el mecanismo real y el contrato publicado

| Registro | Valor |
|---|---|
| `AUTH_TRANSPORT` | cabecera `Authorization: Bearer <access token>`; prefijo literal `Bearer ` (sensible a mayúsculas), token con espacios recortados |
| `AUTH_CREDENTIAL_NAME` | access token **JWT** (`pyjwt`, `HS256`, `type = "access"`, `exp` corto: `access_token_minutes`), emitido por `POST /auth/login` y `POST /auth/refresh` (`token_type: "bearer"`) |
| `AUTH_DEPENDENCY` | `app/core/dependencies.py::get_current_user` (leía `request.headers["Authorization"]` a mano): sin prefijo → `401 AUTH_REQUIRED`; token ilegible/caducado/de otro tipo → `401 AUTH_INVALID_TOKEN`; usuario inexistente o no `ACTIVE` → `403 AUTH_USER_INACTIVE` |
| `SESSION_MODEL` | refresh token JWT (`type = "refresh"`, `sid`, `jti`) en cookie **HttpOnly** `kontrol_refresh` (`Secure`/`SameSite` por ajustes, `path=/api/v1/auth`), rotado por `POST /auth/refresh` (único consumidor; ya declarado como parámetro `cookie` en el OpenAPI) y borrado por `POST /auth/logout` (que no exige sesión: revoca si la cookie viene) |
| `CSRF` | **no hay**: `Settings.csrf_enabled` existe y **nadie lo lee**; el access token no va en cookie, así que no hay doble requisito que documentar |
| `REQUEST_CONTEXT_BUILDER` / `PERMISSION_DEPENDENCY` | `require_permission(resource, action)` → `get_current_user` + `identity_service.user_has_permission` → `403 PERMISSION_DENIED`; `company_context.require_company_context` llama a `get_current_user` **directamente** (segunda vía de entrada, misma lectura) |
| `COMPANY_SCOPE_MECHANISM` | `X-Kontrol-Company` es contexto de empresa validado por el backend (el cliente propone, el servidor decide; `403 SCOPE_DENIED`); **ya** se declara como parámetro `header` opcional en el contrato: no es autenticación |
| `OPENAPI_VERSION` / `SECURITY_SCHEMES` / `GLOBAL_SECURITY` | `3.1.0` · **ninguno** · ninguna |
| `OPERATIONS_TOTAL` / `WITH_SECURITY` / `WITHOUT_SECURITY` (antes) | **543 · 0 · 543** (`BEFORE_SECURITY_SCHEMES = {}`; `BEFORE_PROTECTED_OPERATION_SECURITY = ausente`, p. ej. `/system/diagnostics`; `BEFORE_PUBLIC_OPERATION_SECURITY = ausente`: indistinguibles) |
| Matriz runtime (árbol de dependencias real de cada ruta, `get_current_user` alcanzable o no) | **532 protegidas · 11 públicas**: `GET /health/live`, `GET /health/ready`, `GET /setup/status`, `POST /setup/initialize`, `GET /license/status`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/password-reset/request`, `POST /auth/password-reset/confirm`, `GET /` |
| Rutas con autenticación opcional | **ninguna** |
| `/docs`, `/redoc`, `/openapi.json` | servidos fuera de `prod`; en `prod` `docs_url = redoc_url = None` (sin cambio) |
| Autoridad Central | su app no sirve OpenAPI (`openapi_url=None`) y su «autenticación» es un sobre firmado con cabeceras `X-Kontrol-*` (no es un esquema estándar): **fuera de alcance**, sin deuda nueva porque no publica contrato |
| Herramientas de contrato | `resources/frontend/src/tests/fixtures/openapi-routes.json` (inventario de rutas para `audit-completeness`; no incluye seguridad) · pruebas backend que leen `app.openapi()` (`test_n8_contract`, `test_spec047_architecture`, listados con sobre) |

### Compuertas materiales

| Compuerta | Veredicto |
|---|---|
| `AUTH_TRANSPORT` | **PROVEN**: Bearer JWT en cabecera, un solo analizador |
| `OPENAPI_AUTH_REPRESENTATION` | **PROVEN**: `type: http`, `scheme: bearer`, `bearerFormat: JWT` describe exactamente eso; ni OAuth2 (no hay flujos ni scopes), ni apiKey, ni cookie (la cookie es la entrada de `/auth/refresh`, no la credencial de las operaciones) |
| `SECURITY_DEFAULT_STRATEGY` | **PROVEN** por arquitectura, no por preferencia: FastAPI añade `security` a cada operación cuyo árbol de dependencias incluye una `SecurityBase`; haciendo que la **misma** dependencia que autentica (`get_current_user`) sea esa `SecurityBase`, la partición protegida/pública del contrato se deriva del runtime, sin seguridad global ni `security: []` manuales, y una ruta nueva hereda la declaración correcta por usar la misma primitiva |
| `PUBLIC_ROUTE_POLICY` / `PROTECTED_ROUTE_POLICY` | **PROVEN**: 11 / 532 leídas del árbol; las 11 son las que el contrato ya define como públicas/pre-auth (health, bootstrap, estado público de licencia, login/refresh/logout/recuperación, raíz) |
| `CSRF` | **no aplica** (sin cookie de acceso ni comprobación CSRF en el código) |
| Inconsistencias runtime | **ninguna**: toda ruta de negocio llega a `get_current_user`; las públicas son exactamente las esperadas |

## 3. `/speckit.specify` — FR-001-OASSEC-001..036

001–004 el OpenAPI declara el esquema real (`http`/`bearer`/`JWT`) y toda operación protegida lo exige · 005
las 11 públicas siguen sin `security` · 006–007, 011–014 runtime idéntico (401/403, permisos, alcance) · 008
sin scopes · 009 `X-Kontrol-Company` sigue como parámetro, no como esquema · 010 `RequestContext` intacto ·
015–021 login, logout, setup, health, estado de licencia, import/sync y diagnóstico sin cambio · 022 sin
material en el contrato · 023 determinista · 024–026 una sola fuente: la dependencia; sin lista manual; sin
seguridad global · 027–028 esquema 0, frontend 0 · 029–033 licencia, sync, límite de tasa, reverificación,
keep-alive y panel de versión sin cambio · 034–036 MASTER57, 057, puntero sin cambio.

## 4. `/speckit.clarify` — 39 preguntas, `MATERIAL OQ = 0`

1–7 §2 · 8–11 §2 (3.1.0; sin esquemas; sin global; 0/543) · 12–13 `get_current_user` alcanzable o no en el
árbol · 14 ninguna opcional · 15–21 contratos de login, logout, setup, health, estado, import/sync y
diagnóstico: sin cambio · 22–23 docs fuera de prod; Swagger mostrará «Authorize» con Bearer porque **es**
Bearer · 24 CSRF no aplica · 25–26 `http`/`bearer`/`JWT`, nombre **`BearerAccessToken`** · 27 por operación,
derivado · 28 **sí**: subclase de `HTTPBearer` con la semántica exacta del analizador actual · 29 sin
`custom_openapi` · 30 permisos: fuera de alcance (no hay metadata reutilizable; la descripción de cada
ruta ya los cita en su docstring) · 31 Central fuera · 32–33 543 operaciones; matriz derivada en prueba ·
34–35 OAS-01..23 y M-01..13 · 36–37 esquema 0, frontend 0 · 38 E2E global de regresión (el frontend ya
envía Bearer) · 39 DeepSeek: 0 (todo es decisión de seguridad o dictado).

## 5. `/speckit.plan`, compuerta, checklist, tareas

`BearerAccessToken(HTTPBearer)` en `app/core/dependencies.py` con `scheme_name="BearerAccessToken"`,
`bearerFormat="JWT"`, `auto_error=False` y `__call__` delegando en `read_bearer_credentials(request)`, la
única lectura de la cabecera (misma semántica que antes: prefijo literal, vacío → inválido, otro esquema →
ausente); `get_current_user(credentials = Depends(bearer_access_token), db)` decide los códigos como siempre;
`company_context.require_company_context` llama a `get_current_user(read_bearer_credentials(request), db)`.
Sin anotaciones pospuestas en ese módulo (FastAPI inspecciona la firma del esquema). Nada más cambia.
Pruebas: `tests/test_openapi_security.py` (OAS-01..23, incluida la matriz completa runtime ↔ contrato y los
hostiles de cabecera que fijan la semántica exacta). **Compuerta G01–G39: PASS.** Tareas: T01
descubrimiento/Spec Kit · T02 esquema + dependencia · T03 pruebas · T04 mutaciones, suites, E2E global,
docs, Git. `analyze` previo: `BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`, huérfanos 0,
`MATERIAL OQ = 0`, `UNKNOWN = 0`, trazabilidad 100 %. **Autorización de `implement`:** la del encargo (las
cinco compuertas PROVEN).

## 6. Implementación (T02)

- **`app/core/dependencies.py`** · `BEARER_SCHEME_NAME = "BearerAccessToken"`; `class BearerAccessToken(HTTPBearer)`
  con `scheme_name`, `bearerFormat="JWT"`, descripción del contrato y `auto_error=False`; su `__call__`
  delega en **`read_bearer_credentials(request)`**, la única lectura de `Authorization` del producto, que
  conserva la semántica exacta anterior: prefijo literal `Bearer ` (sensible a mayúsculas) → credencial
  con espacios recortados (vacía incluida), cualquier otra cosa → `None`. `get_current_user(credentials =
  Depends(bearer_access_token), db)` sigue decidiendo: `None` → `401 AUTH_REQUIRED`; decodificación fallida
  → `401 AUTH_INVALID_TOKEN`; usuario ausente o no activo → `403 AUTH_USER_INACTIVE`. `require_permission` y
  todo lo que depende de `get_current_user` heredan el esquema sin tocarse. Se retira `from __future__
  import annotations` del módulo porque FastAPI inspecciona en tiempo de ejecución la firma de `__call__`
  del esquema (las anotaciones del módulo son válidas en 3.11 sin posponerlas).
- **Por qué una subclase y no `HTTPBearer` de serie** · el de serie acepta `bearer` en minúsculas y
  convierte `Bearer ` vacío en «no autenticado»; las pruebas existentes (`SYS-02`, `LIC-*`) fijan el
  contrato actual (`Bearer ` → `AUTH_INVALID_TOKEN`) y el principio del ciclo es que OpenAPI describe el
  runtime sin modificarlo. OAS-15b fija ambas diferencias y M-05/M-06 las vigilan.
- **`app/core/company_context.py`** · el único llamador directo (`require_company_context`) pasa a
  `get_current_user(read_bearer_credentials(request), db)`: misma lectura, ningún segundo analizador
  (OAS-23 y M-12).
- **Lo que no cambia** · `main.py` (sin `custom_openapi`, sin seguridad global, `docs` solo fuera de
  `prod`), el router de auth (login/refresh/logout/recuperación siguen sin sesión; la cookie de refresh
  sigue siendo el parámetro de `/auth/refresh`), permisos, `RequestContext`, `X-Kontrol-Company` (sigue
  como parámetro `header`), licencia, sync, límite de tasa, reverificación, keep-alive, panel de versión,
  esquema (0) y frontend (0: ya envía `Authorization: Bearer`). Autoridad Central: fuera (no publica
  OpenAPI). **DeepSeek: 0 llamadas** (decisión de seguridad + cambio dictado de dos ficheros).

## 7. Pruebas y mutaciones (T03, T04)

| Suite | Casos | Motor |
|---|---|---|
| `tests/test_openapi_security.py` | OAS-01 un solo esquema, sin seguridad global · OAS-02 `http`/`bearer`/`JWT`, sin OAuth2/apiKey/OIDC · OAS-03..13 las 11 públicas sin `security` (parametrizado) · OAS-09..12 nueve protegidas representativas con `[{BearerAccessToken: []}]` (diagnóstico, `me`, sesiones, import, sync, detalle, usuarios, empresas, notificaciones) · **OAS-14 matriz completa**: 543 operaciones, runtime (árbol de dependencias) ↔ contrato, **0 desajustes**, públicas = exactamente las 11 · OAS-15 anónimo → 401 `AUTH_REQUIRED` · OAS-15b siete cabeceras hostiles con su código exacto (`bearer` minúsculas y `Bearer` sin espacio → `AUTH_REQUIRED`; `Bearer ` vacío, basura y `alg=none` → `AUTH_INVALID_TOKEN`) · OAS-15c caducado y refresh-como-access → 401 · OAS-16 públicas intactas · OAS-17 sesión sin permiso → 403 `PERMISSION_DENIED` · OAS-18 empresa ajena → 404 `COMPANY_NOT_FOUND` (política existente) · OAS-19 `X-Kontrol-Company` no es esquema y sigue como parámetro · OAS-20 sin scopes · OAS-21 cookie de refresh como parámetro, ningún esquema apiKey/cookie · OAS-22 sin material y determinista · OAS-23 un solo analizador; docs fuera de prod | SQLite (mundo propio) y PostgreSQL |
| Regresión dirigida | `test_system_access`, `test_license_access`, `test_license_import_access`, `test_auth_session_rotation`, `test_n8_contract`, `test_spec047_architecture`, `test_company_list_envelope`, `test_company_search`, `test_audit_tenant_isolation`, `test_security_integration`, `test_process_flows`: **177 passed** | SQLite |
| E2E | global ×2 (la dependencia es transversal) | PostgreSQL + autoridad real |

**Mutaciones** (`evidence/openapi-seguridad/mutaciones.txt`; pytest con purga de `__pycache__` y
`PYTHONDONTWRITEBYTECODE=1`; GOOD → PASS 54/54): M-01 la dependencia vuelve a leer la cabecera sin `SecurityBase`
(el esquema desaparece) · M-02 el esquema se declara `apiKey` · M-03 el login declara seguridad · M-04 una
protegida vuelve a leer la cabecera a mano dentro de la función (protegida en runtime, pública en el contrato)
· M-05 el analizador acepta `bearer` en minúsculas · M-06 credencial vacía pasa a «no autenticado» · M-07 el
diagnóstico deja de exigir el permiso · M-08 `bearerFormat` miente · M-09 `X-Kontrol-Company` publicado como
esquema · M-10 seguridad global (las públicas la heredan) · M-11 el esquema cambia de nombre · M-12 segundo
analizador en el contexto de empresa · M-13 scopes OAuth inventados. **Primera pasada 11/13**: dos defectos de
la campaña, no del producto —M-04 no mutaba nada (FastAPI fusiona `openapi_extra["security"] = []` con la
lista existente) y M-11 sobrevivía porque la prueba leía el nombre desde la constante—. Corregidos (mutante
realista para M-04; nombre `BearerAccessToken` literal en OAS-01) y repetidos: **13/13 muertas**, M-04 con
exactamente las dos pruebas que debían caer (OAS-09 y la igualdad de públicas de OAS-14). RESTORED → PASS en
todas.

## 8. Resultados

| Gate | Resultado |
|---|---|
| Contrato antes / después (`openapi-antes-despues.txt`) | `securitySchemes {}` · 0/543 con `security` → **`BearerAccessToken` (`http`/`bearer`/`JWT`) · 532/543 con `security` · 11 públicas** (las del contrato), sin seguridad global |
| `tests/test_openapi_security.py` | **40 passed** (SQLite) · **40 passed** (PostgreSQL) |
| Regresión dirigida de autenticación, permisos, alcance y contrato | **177 passed** |
| Backend completo SQLite (`backend-sqlite-completo.txt`) | **43 failed / 1485 passed / 1020 skipped** = 42 documentales sin `clamscan` + `test_dos_renovaciones_simultaneas…` (intermitente SQLite registrado; dirigido 1/1); **0 regresiones**; +40 nuevas |
| Backend completo PostgreSQL (`backend-postgres-completo.txt`, 23 min 8 s) | **38 failed / 2483 passed / 27 skipped** = 35 documentales + 2 `n9_integrity` (línea base 37) + `test_sync_success_records_run_snapshot_and_event` (intermitente de tiempo del arnés; **dirigido 1/1**, `repeticion-dirigida-pg.txt`); clasificación C ×2, **A = 0, E = 0**; ninguno absorbido |
| `ruff check app tests` · `mypy` | limpio · `dependencies.py` limpio; `company_context.py` conserva **2 avisos preexistentes** (tipos `UUID`/`str` en `accessible_company_ids`, líneas no tocadas, idénticos en `HEAD`) |
| Frontend (`frontend-gates.txt`) | producto **0**; typecheck OK · lint OK · **467/467** · build OK |
| Mutaciones | **13/13 muertas** (tras corregir dos mutantes inválidos de la campaña) |
| E2E global ×2 (`e2e-global-1.txt`, `e2e-global-2.txt`) | **235 passed / 0 failed / 40 skipped** y **235 / 0 / 40**; bases `r20261012t024304…` y `r20261012t024647…`, limpieza LIMPIA; puertos libres al cierre |
| Bases de corrida al cierre | **0** |
| `RUNTIME_AUTH_BEFORE == RUNTIME_AUTH_AFTER` | **sí**: 401 `AUTH_REQUIRED` / 401 `AUTH_INVALID_TOKEN` / 403 `AUTH_USER_INACTIVE` / 403 `PERMISSION_DENIED` / 404 `COMPANY_NOT_FOUND`, públicas intactas (OAS-15..18, SYS, LIC, sesión, flujos) |
| Esquema cliente / central · frontend · licencia · sync · límite de tasa · reverificación · keep-alive · panel de versión | **0 · 0 · 0 · sin cambio** (suites completas y E2E) |

## 9. `analyze` final, trazabilidad y veredicto

`securitySchemes` reales = 1 · OAuth2/scopes/apiKey/cookie ficticios = 0 · `custom_openapi` = 0 ·
seguridad global = 0 · lista manual de rutas en producto = 0 (la única lista vive en la prueba, como
afirmación) · analizadores de `Authorization` = 1 · `X-Kontrol-Company` como esquema = 0 · CSRF = no aplica
· cambios de runtime en auth/sesión/permisos/alcance = 0 · docs expuestas en prod = 0 (sin cambio) · esquema
0 · frontend 0 · producción 0 · fiscal 0 · 057 0 · `NEXT MASTER SPEC` 0 · `BLOCKER = CRITICAL =
CONTRADICTIONS = OWNER CONFLICT = 0` · huérfanos 0 · `MATERIAL OQ = 0` · `UNKNOWN = 0` · trazabilidad 100 %.

| Deuda | Estado |
|---|---|
| `OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD` | **CLOSED / CONVERGED** (2026-10-12) |
| Permisos por operación en el contrato | fuera de alcance, declarado: no hay metadata reutilizable; sería una decisión de contrato nueva (sin extensión `x-*` inventada) |
| Autoridad Central | fuera: no publica OpenAPI; su protocolo firmado no es un esquema estándar |
| Intermitentes del arnés | OPEN, clasificados, no absorbidos |
| Resto del encargo · MASTER57 · SPEC057 · NEXT MASTER SPEC | sin cambio |

Orquestación: 4 tareas, `CLAUDE_ONLY` 4, **DeepSeek 0 llamadas**.

| FR (001-OASSEC) | Dónde | Prueba / mutación |
|---|---|---|
| 001–004 esquema real; protegidas lo declaran | `BearerAccessToken`, `get_current_user` | OAS-01, 02, 09..12, 14; M-01, 02, 08, 11 |
| 005, 026 públicas sin seguridad; sin global | derivación por dependencia | OAS-03..13, 14; M-03, 10 |
| 006–007, 011–014 runtime idéntico | `read_bearer_credentials` exacto | OAS-15, 15b, 15c, 16, 17; 177 regresión; M-05, 06, 07 |
| 008 sin scopes | — | OAS-20; M-13 |
| 009–010 `X-Kontrol-Company` y `RequestContext` | parámetro, no esquema | OAS-18, 19; M-09 |
| 015–021 login, logout, setup, health, estado, import/sync, diagnóstico | sin cambio | OAS-03..13, 16, 17; suites |
| 022–023 sin material; determinista | — | OAS-22 |
| 024–025 una sola fuente; herencia por primitiva | `SecurityBase` = dependencia | OAS-14, 23; M-01, 04, 12 |
| 027–033 esquema, frontend, licencia, sync, tasa, reverificación, keep-alive, versión | sin cambio | suites completas, E2E ×2, `test_backend_keepalive`, `test_system_version` |
| 034–036 MASTER57, 057, puntero | docs | §9 |

**Veredicto: `OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD — CLOSED / CONVERGED`.**
