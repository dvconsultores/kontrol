# SPEC 001/003 · DELTA DIRIGIDO — ALTA DE ROLES PERSONALIZADOS POR API

> Iniciado el 2026-10-12. Dueña: **Spec 003 — Usuarios / roles / alcance** (`identity_access`, 8 tablas;
> `PARTIALLY_IMPLEMENTED`), que vive documentalmente en `001-fundacion` (FR-001-040 roles, permisos por
> acción y alcance; FR-001-043 SoD básica y roles protegidos; FR-001-072 auditoría de cambios de
> rol/permiso); la hoja de ruta la registra como dueña 003. Apoyos: 002 (sesión, sin cambio), 054 (QA), 055
> (endurecimiento). 005 no interviene (no hay pantalla de alta); 045 no interviene (la SoD vive en
> aprobaciones, no en la definición de roles). Deuda: `ROLES-SIN-API-DE-ALTA`. MASTER57, 057, D0-07, 039–043
> y 056 no se tocan. Producción (502) fuera.
>
> **Objetivo:** alta de roles personalizados con sus permisos por API, con la autorización, el alcance, la
> identidad, la atomicidad y la auditoría que el modelo vigente ya define; sin CRUD completo, sin
> permisos nuevos, sin esquema nuevo, sin asignar el rol a nadie.

## 1. Checkpoint y dueñas

| | |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` / `ACTUAL_BRANCH` / `WORKTREE_STATE` | `0b98d97` / **`0b98d97`** / `0b98d97` / `develop` / limpio · `COMMITS_AFTER_0B98D97 = 0` · `RUN_DATABASES = 0` · puertos libres |
| Dueñas | 003 primaria (en `001-fundacion`); 002, 054, 055 apoyo · `OWNER_IDENTITY_CONFLICT = 0` |
| Punteros | `NEXT TECHNICAL CYCLE = ROLES-SIN-API-DE-ALTA` (este) · `NEXT MASTER SPEC = NOT YET PRIORITIZED` |

## 2. Descubrimiento (W03–W20) — modelo, API, servicio, semillas, autorización

| Registro | Valor |
|---|---|
| `ROLE_TABLE` / `ROLE_PK` | `roles` · `id` UUID (`UUIDMixin`, `TimestampMixin`, `CreatedByMixin`) |
| `ROLE_CODE_FIELD` / `ROLE_NAME_FIELD` | `code` `String(64)`, índice **no único** `ix_roles_code` · `name` `String(200)` |
| `ROLE_COMPANY_FIELD` / `ROLE_TENANT_FIELD` | `company_id` FK anulable (**estrecha** el alcance a una empresa) · **no hay `tenant_id`**: el *docstring* certificado en N10 fija que `roles` es el **catálogo de la instalación** («hay un catálogo, no uno por tenant»; roles propios por tenant es capacidad futura registrada) |
| `ROLE_SYSTEM_FLAG` / `ROLE_SOFT_DELETE` | `protected` (solo el arranque crea `ADMIN` protegido, `company_id` nulo) · `status` (`ACTIVE`; `list_roles` filtra activos); sin borrado |
| `ROLE_PERMISSION_RELATION` / `USER_ROLE_RELATION` | `role_permissions (role_id, permission_id, constraints)` · `user_roles (user_id, role_id, company_id, vigencia)` |
| `Permission` | `resource`, `action`, `scope_type`, `constraints`; identidad pública `recurso:accion` (así los publica `list_roles` y así los usan `require_permission` y `rol_sin_permiso.py`) |
| APIs existentes | `GET /roles` (`roles:view`) · `POST/DELETE /users/{id}/roles[/{role_id}]` (`roles:edit`) · **ningún alta de rol, ningún alta de permisos a un rol, ningún listado de permisos** · sin PUT/DELETE de rol |
| Servicio | `list_roles`, `get_user_roles`, `assign_role_to_user` (valida `company_id` contra el tenant del actor: `404 COMPANY_NOT_FOUND`; `409 ROLE_ALREADY_ASSIGNED`; audita `ROLE_ASSIGNED`), `remove_role_from_user` · **no existe `create_role`** |
| Alta fuera de la API | `qa/rol_sin_permiso.py` escribe `Role(code, name, protected=False, status="ACTIVE")` + `RolePermission` por `recurso:accion` en una sola transacción: la deuda es real y la forma de la operación ya está dictada por el uso |
| `ROLE_CREATE_PERMISSION` | **`roles:create`** existe en el catálogo del arranque (`setup/api.py`: `"roles": ["view", "create", "edit"]`) y **nadie lo exige**: ni ruta ni servicio |
| Actor | quien tenga `roles:create` (el `ADMIN` del arranque lo tiene por catálogo); no hay «superadmin» distinto; el tenant es el del actor (`actor.tenant_id`), como en `create_user` |
| Error contract | `KontrolError` 4xx con `code`/`message`/`field_errors`; `NotFoundError` 404; `ConflictError` 409; validación semántica de cuerpo con 422 (`PASSWORD_POLICY`); `PERMISSION_DENIED` 403; `AUTH_REQUIRED` 401 |
| Auditoría | `_audit(db, action=…, entity_type=…, entity_id=…, tenant_id=…, user_id=…, after=…)` → `audit_events`; FR-001-072 exige auditar «cambio de rol/permiso» |
| SoD | solo en aprobaciones (Spec 045: creador ≠ aprobador, delegación no amplía); **ninguna regla sobre la definición de roles** |
| Frontend | `RolesPage` lista roles y asigna/quita roles a usuarios; `ReglasPage` lista roles; **no hay formulario de alta**: frontend de producto **0** |
| Concurrencia | sin unicidad en la base; el repositorio ya usa `pg_advisory_xact_lock` para serializar altas sin esquema (`licensing.service` alta de instalación; autoridad central) |

### Compuertas materiales

| Compuerta | Veredicto |
|---|---|
| `ROLE_SCOPE` | **PROVEN**: catálogo de la instalación; `company_id` nulo = toda la instalación, o una empresa **del tenant del actor** (el control exacto de `assign_role_to_user`). No se inventa `tenant_id`; la capacidad «roles por tenant» sigue siendo la futura ya registrada |
| `ROLE_CREATE_AUTHORIZATION` | **PROVEN**: `roles:create` existe y estaba sin uso |
| `ROLE_CREATE_PAYLOAD` | **PROVEN**: rol + permisos **atómicos**, permisos como `recurso:accion` (la identidad que ya publica `list_roles` y que escribe `rol_sin_permiso.py`); lista vacía admitida (un rol sin permisos no concede nada) |
| `ROLE_IDENTITY_POLICY` | **PROVEN**: identidad `(code, company_id)`, la que el arranque consulta (`code == "ADMIN" and company_id is NULL`); sin unicidad en la base → duplicado serializado con candado consultivo (patrón del repositorio), **sin migración**; forma del código: no vacío, ≤ 64, sin espacios (restricción de forma, no de negocio) |
| `PRIVILEGE_DELEGATION_POLICY` | **PROVEN por el contrato vigente**: no existe techo de delegación en ningún punto (`roles:edit` ya permite asignar `ADMIN` —todos los permisos— a cualquier usuario; `users:create` crea usuarios sin techo). Crear un rol con permisos del catálogo que el actor no posee **no amplía** lo que la asignación ya permite. Introducir un techo sería una política nueva: queda **declarado** como deuda abierta de decisión de la dueña (`ROLES-SIN-TECHO-DE-DELEGACION`), no se inventa aquí |
| `SYSTEM_ROLE_POLICY` | **PROVEN**: `protected`, `status`, `created_by` son del servidor (`extra="forbid"` → 422 si vienen en el cuerpo); la API solo crea `protected = False` |
| `COMPANY_TENANT_ISOLATION` | **PROVEN**: tenant = el del actor; empresa de otro tenant o inexistente → `404 COMPANY_NOT_FOUND` (igual que asignar) |
| SoD | **NOT_APPLICABLE** con evidencia: ninguna regla sobre definiciones de rol |
| Esquema | **0**: sin columna, índice ni tabla |

## 3. `/speckit.specify` — FR-003-ROLE-001..036

001 `POST /roles` · 002–004 sesión + `roles:create`, sin permiso nuevo · 005–006 alcance del modelo; `company_id` del cuerpo validado contra el tenant del actor, nunca autoridad · 007–008 permisos existentes; el alta no crea permisos · 009–010 `protected`/`status`/`created_by` del servidor; nunca protegido · 011–012 identidad `(code, company_id)`; `409 ROLE_DUPLICATE` · 013–015 permiso desconocido → 422 sin persistir; una transacción · 016 no asigna · 017–018 sin techo (contrato vigente, declarado) y SoD no aplica · 019 cruce de tenant → 404 · 020 reutiliza modelos, `_audit`, `get_user_in_tenant`-style checks · 021–022 `ROLE_CREATED` sin secretos · 023–024 hereda `BearerAccessToken`; matriz 0 desajustes · 025–027 listado, asignación, auth, aislamiento sin cambio · 028 esquema 0 · 029 frontend 0 · 030–033 licencia, central, keep-alive, versión sin cambio · 034–036 MASTER57, 057, puntero.

## 4. `/speckit.clarify` — 39 preguntas, `MATERIAL OQ = 0`

1–10 §2 · 11–14 `roles:create`; `ADMIN` lo tiene; sin superadmin distinto · 15–16 cruce → 404; sin tenant en roles por modelo · 17–20 `{code, name, company_id?, permissions[]}` atómico; códigos `recurso:accion`; desconocido → 422 con la lista · 21 sin techo (declarado) · 22 SoD no aplica · 23–24 `extra="forbid"` · 25 `ROLE_CREATED` · 26 una transacción · 27 409 · 28 sin borrado · 29 no asigna · 30 sin formulario · 31 `roles_router` existente, `POST ""` · 32 `RoleOut` = fila de `list_roles` + `company_id` · 33 401/403/404/409/422 existentes · 34 544 operaciones, 533 protegidas · 35 esquema 0 · 36–38 ROLE-01..20 + E2E dirigido + global · 39 DeepSeek: 0.

## 5. `/speckit.plan`, compuerta, checklist, tareas

`identity_service.create_role(db, tenant_id, code, name, company_id, permissions, actor)` (validación de empresa,
catálogo de permisos, candado consultivo en PostgreSQL, duplicado por `(code, company_id)`, inserción de rol +
permisos, `ROLE_CREATED`, `commit`); `POST /roles` (`RoleCreate` cerrado, `RoleOut`, 201, `require_permission("roles",
"create")`). Pruebas `tests/test_roles_create.py` (ROLE-01..20 con PG-only para la carrera) y
`e2e/roles-alta.spec.ts`. **Compuerta G01–G36: PASS.** Tareas: T01 descubrimiento/Spec Kit · T02 servicio + ruta ·
T03 pruebas y E2E · T04 mutaciones, suites, E2E global, docs, Git. `analyze` previo: `BLOCKER = CRITICAL =
CONTRADICTIONS = OWNER CONFLICT = 0`, huérfanos 0, `MATERIAL OQ = 0`, `UNKNOWN = 0`, trazabilidad 100 %.
**Autorización de `implement`:** la del encargo (las siete compuertas PROVEN).

## 6. Implementación (T02)

- **`identity_access/service.py::create_role`** · recorta `code`/`name`; si viene `company_id`, la empresa debe
  existir y ser del tenant del actor (`404 COMPANY_NOT_FOUND`, el mismo control que `assign_role_to_user`);
  resuelve los permisos `recurso:accion` contra el catálogo (`Permission`), deduplicados y ordenados; cualquiera
  desconocido → `422 PERMISSION_UNKNOWN` con `field_errors.permissions = [desconocidos]` **antes de escribir
  nada**; en PostgreSQL toma `pg_advisory_xact_lock(_BLOQUEO_ALTA_ROL)` (sección crítica de milisegundos;
  SQLite serializa solo); duplicado por `(code, company_id)` → `409 ROLE_DUPLICATE`; inserta `Role(protected=False,
  status="ACTIVE", created_by=actor)` y sus `RolePermission`; audita `ROLE_CREATED` (`entity_type="Role"`, `after =
  {code, name, company_id, permissions}`); un solo `commit`. Devuelve la fila como `list_roles` más `company_id`.
- **`identity_access/api.py`** · `RoleCreate` (`extra="forbid"`; `code` 1–64 sin espacios; `name` 1–200;
  `company_id` opcional; `permissions` lista, vacía por defecto) · `RoleOut` · `POST /roles` (201) con
  `require_permission("roles", "create")`; tenant = `actor.tenant_id`. Hereda `BearerAccessToken` por la
  dependencia (OpenAPI: 544 operaciones, 533 protegidas, 11 públicas iguales).
- **Lo que no cambia** · `GET /roles`, `POST/DELETE /users/{id}/roles`, el rol `ADMIN` protegido del arranque,
  autenticación, sesión, `RequestContext`, `X-Kontrol-Company`, licencia, central, keep-alive, versión;
  esquema **0**; frontend **0** (`RolesPage` sigue listando y asignando; el formulario de alta es de la 005 y
  no existe aún). **DeepSeek: 0 llamadas** (decisiones de seguridad y cambio dictado de dos ficheros).

## 7. Pruebas (T03)

| Suite | Casos | Motor |
|---|---|---|
| `tests/test_roles_create.py` | ROLE-01 sin sesión 401; ROLE-02 sesión sin `roles:create` 403 y nada creado; ROLE-03/04 alta 201 con esquema canónico, permisos deduplicados y ordenados, `created_by` del servidor, visible en `GET /roles`, **sin asignaciones nuevas** (ROLE-17); ROLE-05 alcance de empresa del tenant; ROLE-06/07 empresa de otro tenant o inexistente → 404; ROLE-08 permiso desconocido → 422 con la lista, sin rol ni permiso nuevo; ROLE-10/11 `protected`/`status`/`created_by`/`tenant_id`/`id` en el cuerpo → 422 (parametrizado); ROLE-10b nunca protegido; ROLE-12 duplicado 409, otro alcance 201, `ADMIN` también 409; ROLE-12b siete cuerpos inválidos → 422; **ROLE-13 (PostgreSQL)** 12 altas simultáneas → exactamente 1 × 201 y 11 × 409, una fila; ROLE-16 fallo al asociar permisos → sin rol a medias ni auditoría; ROLE-19 `ROLE_CREATED` con `after` exacto y sin secretos; ROLE-20 listado sigue exigiendo `roles:view`, `ADMIN` intacto | SQLite (23 + 1 PG-only) y PostgreSQL (24) |
| Regresión | `test_openapi_security` (matriz 544 ↔ runtime, públicas iguales), `test_n10_cross_tenant`, suites completas | — |
| E2E | `e2e/roles-alta.spec.ts` (E2E-ROLE-01..05: 401, 403 con usuario sin `roles:create` fabricado por `rol_sin_permiso.py`, 201 con permisos, 409, 422, listado) en `chromium`; global ×1 (endpoint aislado, sin cambio transversal) | PostgreSQL + autoridad real |

**Mutaciones** (`evidence/roles-alta/mutaciones.txt`; pytest con purga de `__pycache__` y
`PYTHONDONTWRITEBYTECODE=1`; GOOD → PASS 64 y 24 PG): M-01 el alta sin `roles:create` · M-02 el cuerpo fija
`protected` · M-03 el servicio deja de fijar `protected=False` · M-04 permiso desconocido ignorado · M-05 empresa
sin comprobar contra el tenant · M-06 sin comprobación de duplicado · M-07 duplicado sin alcance · M-08 sin
candado consultivo (**PostgreSQL**) · M-09 `commit` del rol antes de los permisos · M-10 sin auditoría · M-11 el
alta asigna el rol al actor · M-12 el permiso pasa a `roles:edit` · M-13 la ruta se publica sin la dependencia
de seguridad. **13/13 muertas**. Tres defectos del guion, declarados y corregidos antes de medir de verdad: M-03
inicial era equivalente (no cambiaba el valor), el anclaje de M-12 estaba mal escrito (abortó la pasada en M-12 y
M-13 no llegó a correr) y M-13 inicial era un `SyntaxError`. RESTORED → PASS en los trece.

## 8. Resultados

| Gate | Resultado |
|---|---|
| `tests/test_roles_create.py` | **23 passed + 1 PG-only** (SQLite) · **24 passed** (PostgreSQL, con ROLE-13: 12 altas simultáneas → 1 × 201, 11 × 409, una fila) |
| OpenAPI | **544** operaciones, **533** protegidas, **11** públicas (iguales); `POST /roles` con `[{BearerAccessToken: []}]`, respuestas 201/422; matriz OAS-14 0 desajustes (`test_openapi_security` 40/40) |
| Backend completo SQLite (`backend-sqlite-completo.txt`) | **44 failed / 1507 passed / 1021 skipped** = 42 documentales sin `clamscan` + `test_dos_renovaciones_simultaneas…` + `test_warehouse_structure::test_concurrencia…`; **0 regresiones**; +22 nuevas |
| Backend completo PostgreSQL (`backend-postgres-completo.txt`, 13 min 52 s) | **37 failed / 2508 passed / 27 skipped** = línea base exacta (35 documentales + 2 `n9_integrity`); **0 regresiones**; +25 nuevas |
| Intermitentes SQLite (`repeticion-dirigida-sqlite.txt`) | `test_dos_renovaciones_simultaneas…` falla también **en `HEAD` sin mis cambios** (2/2 fallos actual, 1/1 fallo en HEAD; en PostgreSQL pasa): defecto preexistente de carrera sobre SQLite, no de este ciclo; `test_concurrencia_de_codigo…` 1 de 2 en actual y falla en HEAD: `ALMACENES-CARRERA-SQLITE-HILOS`, registrada. Clasificación C/D, **A = 0**; ninguno absorbido |
| `ruff check` · `mypy` (módulos tocados) | limpio · limpio |
| Frontend (`frontend-gates.txt`) | producto **0**; typecheck OK · lint OK · **467/467** · build OK |
| Mutaciones | **13/13 muertas** |
| E2E dirigido (`e2e-dirigido-roles-alta.txt`) | **1/1** (E2E-ROLE-01..05), limpieza LIMPIA |
| E2E global (`e2e-global.txt`) | **236 passed / 0 failed / 40 skipped** (235 + 1), base `r20261012t045252…`, limpieza LIMPIA; puertos libres |
| Bases de corrida al cierre | **0** |
| Esquema · frontend · auth/sesión · aislamiento · licencia · central · keep-alive · versión | **0 · 0 · sin cambio** |

## 9. `analyze` final, trazabilidad y veredicto

`POST /roles` = 1 · permisos nuevos = 0 · tablas/columnas/índices nuevos = 0 · CRUD extra = 0 · roles protegidos
creables por API = 0 · `company_id` del cuerpo como autoridad = 0 (validado contra el tenant) · permisos creados
dinámicamente = 0 · asignaciones a usuarios por el alta = 0 · lectura manual del JWT = 0 (hereda la dependencia) ·
frontend = 0 · producción = 0 · fiscal = 0 · 057 = 0 · `NEXT MASTER SPEC` = 0 · `BLOCKER = CRITICAL = CONTRADICTIONS
= OWNER CONFLICT = 0` · huérfanos 0 · `MATERIAL OQ = 0` · `UNKNOWN = 0` · trazabilidad 100 %.

| Deuda | Estado |
|---|---|
| `ROLES-SIN-API-DE-ALTA` | **CLOSED / CONVERGED** (2026-10-12) |
| `ROLES-SIN-TECHO-DE-DELEGACION` | **NUEVA, OPEN** — decisión de la dueña (§2) |
| `test_dos_renovaciones_simultaneas…` sobre SQLite | preexistente, falla en `HEAD`; anotado, no absorbido (es de la Spec 002: carrera de renovación sobre SQLite con hilos; en PostgreSQL pasa) |
| `ALMACENES-CARRERA-SQLITE-HILOS` y resto del encargo · MASTER57 · SPEC057 · NEXT MASTER SPEC | sin cambio |

Orquestación: 4 tareas, `CLAUDE_ONLY` 4, **DeepSeek 0 llamadas**.

| FR (003-ROLE) | Dónde | Prueba / mutación |
|---|---|---|
| 001–004 API, sesión, `roles:create`, sin permiso nuevo | ruta + `require_permission` | ROLE-01, 02; E2E-ROLE; M-01, M-12 |
| 005–006, 019 alcance; `company_id` validado; cruce de tenant | `create_role` | ROLE-05, 06/07; M-05 |
| 007–008, 013 permisos existentes; sin crear; desconocido → 422 sin persistir | catálogo | ROLE-08; M-04 |
| 009–010 flags del servidor | `extra="forbid"`, `protected=False` | ROLE-10/11, 10b; M-02, M-03 |
| 011–012 identidad `(code, company_id)`; 409; concurrencia | candado + duplicado | ROLE-12, 12b, 13; M-06, M-07, M-08 |
| 014–015 atomicidad | un `commit` | ROLE-16; M-09 |
| 016 sin asignar | — | ROLE-03/04 (ROLE-17); M-11 |
| 017–018 techo (declarado) y SoD (no aplica) | §2 | — |
| 020 reutilización | `_audit`, controles existentes | revisión |
| 021–022 auditoría sin secretos | `ROLE_CREATED` | ROLE-19; M-10 |
| 023–024 OpenAPI heredado; matriz | dependencia | OAS-14; M-13 |
| 025–033 sin cambio en el resto | — | suites completas, E2E |
| 034–036 MASTER57, 057, puntero | docs | §9 |

**Veredicto: `ROLES-SIN-API-DE-ALTA — CLOSED / CONVERGED`.**
