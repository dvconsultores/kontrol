# SPEC 001 · DELTA DIRIGIDO AUDIT-EVENTS-SIN-TENANT — LA BITÁCORA NO CRUZA INQUILINOS

> Delta de seguridad dentro de la Spec 001 (Fundación), con ARCH-MC-001 como contrato de
> alcance y la Spec 012 (QA integral, Master 054) como apoyo de certificación. Corrige la
> fuga entre inquilinos que `UI-BUSQUEDA-MUERTA` encontró debajo de la caja de búsqueda de
> auditoría: `GET /api/v1/audit/events` devolvía la bitácora entera de la instalación a
> cualquiera con `audit:view`. No absorbe la búsqueda `q`, ni el sobre de `AuditoriaPage`,
> ni `created_at`, ni `INBOX-045-AISLAMIENTO`.

## 0. Checkpoint

| Comprobación | Valor |
|---|---|
| `LAST_KNOWN_HEAD` | `eaa93fe` |
| `ACTUAL_HEAD` | **`aae7cd2`** — `docs(spec-001): el contrato manda buscar, pero en existencias no hay ni una columna que buscar` |
| `ACTUAL_BRANCH` | `develop` |
| `COMMITS_AFTER_EAA93FE` | **1**: `aae7cd2` |
| `UI_BUSQUEDA_MUERTA_ANALYSIS_COMMIT` | **`aae7cd2`** — es el commit cuyo hash no se informó; la evidencia del repositorio manda |
| `WORKTREE_STATE` | 1.550 ficheros con cambio **solo de modo** (`100644 → 100755`; `git diff --shortstat`: 0 inserciones, 0 borrados) más los dos artefactos de auditoría sin seguimiento. Ningún cambio de contenido previo a este delta |

Ni reset, ni checkout: `aae7cd2` es la autoridad.

### Ficheros sin confirmar, clasificados

| Fichero | Origen | Relación con este delta | Decisión |
|---|---|---|---|
| `KONTROL_MASTER_COMPLETENESS_AUDIT.md` | Auditoría maestra de completitud | Ninguna | Se preserva; no se mueve ni se confirma |
| `qa/audits/KONTROL-AUDIT-POLICY-CLOCK-LOCAL-20260917/` | Auditoría del delta POLICY-CLOCK-LOCAL | Ninguna | Se preserva tal cual |
| 1.550 cambios de modo | Copia del árbol por un sistema de ficheros sin bits de ejecución | Ninguna | No se confirman: este delta añade sus ficheros con `core.fileMode=false` |

### Estado del entorno de ejecución, medido

No es del repositorio, pero condiciona toda la evidencia y por eso se escribe:

| Hecho | Medida | Consecuencia |
|---|---|---|
| `resources/backend/.venv/bin/python*` y `resources/frontend/node_modules/.bin/*` son ficheros de texto con marcador `IntxLNK` | enlaces simbólicos **aplanados** por la copia; `pyvenv.cfg` apunta a `/usr/bin/python3.11`, que no existe (el sistema tiene 3.13) | ningún guion que invoque `.venv/bin/…` puede ejecutarse |
| Entorno reconstruido **fuera del repositorio** | `uv` + CPython **3.11.16** + `requirements.lock` (46 paquetes) en el scratchpad de la sesión | la suite corre con el mismo lockfile |
| El lockfile no declara `reportlab` ni `python-magic`, que el entorno antiguo sí tenía | `requirements.txt` declara `reportlab==5.0.0`; `python-magic` no está en ninguno | deuda de entorno registrada (§19), instalados en el entorno de trabajo para poder medir |
| `clamscan` no existe en esta máquina | `shutil.which("clamscan")` → vacío; el entorno anterior tenía ClamAV 1.4.3 (`n9-clamav-report.md`) | las pruebas documentales responden `SCAN_FAILED` 422 al subir, antes de llegar a nada; **44 fallos idénticos con el `api.py` original y con el corregido** (`atribucion-fallos-entorno.txt`) |
| PostgreSQL de QA reaprovisionado | `qa/pg-provision.sh start` (pgserver 16.2, 55432); `/tmp/kontrol-pgdata-045` ya no existía | la base `keu` con los **20 eventos del hallazgo original ya no existe**: no puede reauditarse; se reproduce sobre `kaud`, sembrada con `qa/e2e-seed.sh` |

## 1. Veredicto, por delante

**El defecto es de lectura, en un solo sitio, y el modelo ya tenía todo lo necesario.**

| Pregunta del encargo | Respuesta medida |
|---|---|
| ¿`AuditEvent` tiene `tenant_id`? | **Sí**, desde `0001_fundacion`, indexado, FK a `tenants` desde `0034` |
| ¿Lo rellenan los escritores? | **Sí**: 22 sitios, todos desde el usuario autenticado o deducido de la empresa validada |
| ¿Hay filas con tenant nulo? | **0** en la base de QA; ningún escritor lo produce por diseño |
| ¿Hay eventos globales de auditoría? | **No existen contractualmente**: los de instalación viven en `LicenseEvent` y `HomologationEvent` |
| ¿Dónde se pierde el aislamiento? | `audit/api.py::list_events`: `select(AuditEvent)` sin `where` de tenant |
| ¿Afecta a otras superficies? | **No**: la otra lectura, `/reporting/audit/timeline`, es de empresa y valida la empresa contra el tenant |
| ¿Migración? ¿Backfill? | **0 / 0** |
| ¿Decisión material pendiente? | **0**: tenant decidido por FR-001-032/033; empresa dentro del tenant decidida por ARCH-MC-001 |

Fix: **una cláusula** en el `select`, antes de filtros, recuento y paginación. Ficheros de
producto: **1**. Esquema: **0**. Migraciones: **0**. Datos modificados: **0** (sello de
integridad idéntico antes y después).

## 2. Dueña canónica

| Papel | Spec | Motivo |
|---|---|---|
| **Principal** | **SPEC 001 — Fundación** | El endpoint, el modelo, la fábrica `record_audit`, FR-001-070/071/072 y el contrato `api-contracts.md §Auditoría` son suyos; el roadmap ya la nombraba dueña |
| Contrato de seguridad | **SPEC 001** (FR-001-032/033, ADR-011) + **ARCH-MC-001** (FR-MC-020/021/022, matriz de alcance por endpoint, guarda N10) | Deciden tenant y empresa; no hay nada que decidir de nuevo |
| QA | **SPEC 012** (Master 054) | Pruebas hostiles y certificación |
| Apoyo | **SPEC 009** (Reportes/auditoría) | Dueña de `/reporting/audit/timeline`, la segunda superficie, que ya estaba acotada |

La hipótesis del encargo («SPEC006 — Audit/Observability») se resuelve por el
`spec-equivalence-map`: el Master 006 «Auditoría/observabilidad» se implementa en
`001-fundacion` + `009-reportes-auditoria`; en el árbol `specs/`, `006-tesoreria` es
tesorería. `OWNER_IDENTITY_CONFLICT = 0`.

## 3. Clasificación

`CROSS_TENANT_DATA_EXPOSURE`, que en la nomenclatura del repositorio es una **fuga entre
inquilinos** y consta como **grave** en `technical-debt-roadmap.md` (la única deuda de la
cola que enseña datos de un inquilino a otro, `next-spec-decision.md` del 2026-09-24).
Prioridad por delante de toda deuda de UX/QA.

## 4. El endpoint, físicamente

| | |
|---|---|
| Método y ruta | `GET /api/v1/audit/events` |
| `operationId` | `list_events_api_v1_audit_events_get` · tag `audit` |
| Router / handler | `app/modules/audit/api.py` · `list_events` (`app/main.py:100` lo monta bajo `/api/v1`) |
| Servicio / repositorio | ninguno: el `select` vive en el handler |
| Respuesta | sobre `{page, page_size, total, items[]}` con `id, action, entity_type, entity_id, user_id, request_id, source, event_time` |
| Parámetros declarados | `page`, `page_size`, `entity_type`, `entity_id`, `action` |
| Seguridad | `require_permission("audit", "view")` → devuelve el `User` autenticado (tenant en `user.tenant_id`) |
| Contexto de empresa | **no aplica**: `TENANT/INSTALLATION` según ARCH-MC-001 |
| Antes del fix | `select(AuditEvent).order_by(event_time desc)` + filtros funcionales; `total = len(todo)`; `offset/limit` |

El «RequestContext canónico» del encargo es aquí el `User` que devuelve la dependencia
(tenant, identidad, permisos) y, para rutas de empresa, `CompanyContext`. El endpoint lo
recibía y **lo descartaba** (`_: User = Depends(...)`).

## 5. Reproducción determinista, antes de tocar nada

Sobre PostgreSQL 16.2 real (`kaud`, cabeza `0057`, sembrada con `qa/e2e-seed.sh`: DEMO con
D1/D2 y usuarios `admin`/`ua`/`ub`/`uab`; DEMO2 con E1 y `uc`). Guion:
`qa/repro-audit-tenant-leak.py`. Evidencia: `evidence/audit-tenant-isolation/reproduccion-pre-fix.txt`.

| Paso | Medida pre-fix |
|---|---|
| A · eventos accidentales: un login en DEMO y otro en DEMO2; `admin/DEMO` lista | `total=7`, `items=7`; dueño real leído en la base: **DEMO 5, DEMO2 2** |
| A · eventos de DEMO2 devueltos a `admin/DEMO` | **2**: `ae38eefd-…`, `26bdb1de-…` (`USER_CREATED` y `LOGIN_SUCCESS` de `uc`) |
| B · dos eventos **de contenido idéntico** (`AUDTEN_PROBE`/`Probe`/`probe-mismo-id`, mismo `request_id`), uno por tenant | `EVENT_A=46d2ff2e-…` (DEMO) · `EVENT_B=41c4c5fc-…` (DEMO2) |
| B · `admin/DEMO ?action=AUDTEN_PROBE` | `total=2` · A visible · **B visible** |
| B · `uc/DEMO2 ?action=AUDTEN_PROBE` | `total=2` · **A visible** · B visible |
| C · camino de escritura | el último `LOGIN_SUCCESS` de cada tenant lleva **su** tenant (`company_id` nulo: evento de tenant) |
| Veredicto | **LEAK**, en las dos direcciones, con `total` global |

La prueba no depende de «había 1 de DEMO2 entre 20»: los dos eventos controlados solo se
distinguen por el tenant.

## 6. Modelo físico: ORM, PostgreSQL y migraciones

`app/modules/audit/models.py::AuditEvent` (`__scope__ = Scope.TENANT`, tabla `audit_events`).
Evidencia: `evidence/audit-tenant-isolation/esquema-postgresql.txt`.

| Columna | Tipo | Nulo | FK | Índice | Propósito |
|---|---|---|---|---|---|
| `id` | varchar(36) | no | — | PK | identidad |
| **`tenant_id`** | varchar(36) | **sí** | `tenants.id` (`fk_audit_events_tenant`, 0034) | `ix_audit_events_tenant_id` | **dueño** |
| `company_id` | varchar(36) | sí | `companies.id` (`fk_audit_events_company`, 0034) | sí | empresa, cuando el evento es de empresa |
| `user_id` | varchar(36) | sí | — | sí | actor |
| `session_id` | varchar(36) | sí | — | — | sesión |
| `request_id` | varchar(64) | sí | — | sí | correlación |
| `action` | varchar(64) | no | — | sí | acción |
| `entity_type` | varchar(64) | no | — | sí | entidad |
| `entity_id` | varchar(36) | sí | — | sí | entidad |
| `before` / `after` | json | sí | — | — | estado |
| `source` | varchar(32) | no, default `'API'` | — | — | `API` / `SCHEDULER` / `QA` |
| `reason` | varchar(255) | sí | — | — | motivo |
| `evidence` | json | sí | — | — | evidencia |
| `ip` | varchar(45) | sí | — | — | origen |
| `event_time` | timestamptz | no | — | — | sello del servidor |
| `created_at` / `updated_at` | timestamptz | no, `now()` | — | — | mixin |

**Deriva ORM ↔ PostgreSQL: 0** (18 columnas, nulabilidad y las dos FK coinciden; lo
confirma además `test_n10_convergence.py::test_el_orm_y_la_base_no_difieren_en_nada`,
verde sobre PostgreSQL en esta sesión).

| Migración | Qué hizo con `audit_events` |
|---|---|
| `0001_fundacion` | Crea la tabla **con `tenant_id` y `company_id`** (ambos anulables) y sus siete índices |
| `0034_n7_tenant_fk` | Añade `fk_audit_events_tenant` y `fk_audit_events_company`; deja el nulo «porque hay acciones anteriores a conocer el tenant (el arranque de la instalación)» |
| Otras | **ninguna**: no hay backfill, ni cambio de tipo, ni columna añadida después |

`tenant_id` existió siempre. No hay filas «legacy» de una época sin tenant.

## 7. Datos existentes

Evidencia: `datos-existentes-pre.txt`, `integridad-pre-fix.txt`, `integridad-post-fix.txt`.

| Medida (kaud, tras la siembra, antes de reproducir) | Valor |
|---|---:|
| `TOTAL_AUDIT_EVENTS` | 5 |
| `TENANT_ID_NULL` | **0** |
| `COMPANY_ID_NULL` | 5 (`USER_CREATED`: eventos de tenant) |
| `company_id` presente con `tenant_id` nulo | **0** |
| Empresa de otro tenant que el de la fila (contradicción) | **0** |
| Por tenant | DEMO 4 · DEMO2 1 |
| Sin usuario | 4 (los crea la siembra sin actor) |

Y sobre la base que vio el hallazgo (`keu`, 2026-09-24): DEMO 19 · DEMO2 1 · total 20,
según `evidence/dead-search/auditoria-lo-que-habia-debajo.txt`. Esa base ya no existe.

### Clasificación de las filas con tenant nulo

No hay ninguna que clasificar en los datos. Se clasifica **por escritor** (§8): ningún
camino del producto produce `tenant_id` nulo salvo dos imposibles en PostgreSQL —
`SESSION_REVOKED` sobre una sesión cuyo usuario no exista, y `record_audit` con una
`company_id` que no resuelva a empresa, que `fk_audit_events_company` rechaza—. Clases:

| Clase | Filas | Semántica |
|---|---:|---|
| A · legítimamente globales | 0 | **No existen contractualmente**: FR-001-070 exige tenant/company; los eventos de instalación (licencia, homologación) tienen tablas propias |
| B · mal escritas | 0 | — |
| C · legacy | 0 | `tenant_id` existe desde `0001` |
| D · system-level | 0 | el planificador escribe con empresa explícita (§8) |
| E · desconocidas | **0** | — |

**Semántica decidida**: un evento con tenant nulo **no es de nadie y no lo lee nadie** en
`/audit/events`. Regalárselo a todos (`IS NULL OR`) sería inventar un lector; no se hace.

### Filas con tenant y sin empresa

Válidas: son los **eventos de tenant** que FR-001-072 enumera —inicio y cierre de sesión,
contraseñas, usuarios, roles y alcances— más los catálogos de tenant (unidades) y los
documentos. `canonical-scope-matrix.md §4`: «`audit_events` es del tenant como fila; su
`company_id` designa una empresa» cuando la hay. No se exige `company_id` universal.

## 8. Escritores, todos

Evidencia: `escritores.txt`. Una sola fábrica construye `AuditEvent`: `app/shared/audit.py::record_audit`,
que **deduce el tenant de la empresa** cuando solo recibe `company_id` (N5) para que una fila
no pueda decir una empresa de un tenant y otro tenant.

| Escritor | Sitios | Fuente de tenant | Fuente de empresa | ¿Puede dar tenant nulo? |
|---|---:|---|---|---|
| `identity_access/service.py::_audit` | 11 | `tenant_id` resuelto por `tenant_code` en el login, o `user.tenant_id` | — (eventos de tenant) | solo `SESSION_REVOKED` si la sesión apuntara a un usuario inexistente |
| `inventory`, `purchasing`, `treasury`, `regulatory`, `approvals`, `fiscal`, `sales` (`_audit`) | 7 envoltorios | deducido de `company_id` | `company_id` del servicio, que llega de `CompanyContext` validado | no (la FK rechaza una empresa inexistente) |
| `notifications/service.py::_auditar` | 1 | deducido | `company_id` explícito; `Actor("SYSTEM")` → `source=SCHEDULER` | no |
| `reporting/service.py` (`REPORT_EXPORTED`) | 1 | deducido | `company_id` del contexto | no |
| `organization/warehouse_api.py::_audit` | 1 | `user.tenant_id` | `ctx.company_id` | no |
| `master_data/uom_api.py::_audit` | 1 | `user.tenant_id` | — | no |
| `documents/api.py::_audit` y `documents/service.py::_audit` | 2 | `user.tenant_id` / `actor.tenant_id` (el actor es el `User` autenticado: `documents/api.py:554,693,710`; `freeze_links` con actor nulo **no** audita) | — | no |
| `licensing/service.py::_record_event`, `homologation/service.py::_record_event` | — | escriben `LicenseEvent` / `HomologationEvent`, **no** `AuditEvent` | — | fuera de la tabla |

Escritores de fondo: el único actor sin petición HTTP es `SISTEMA` en notificaciones, y
escribe con `company_id` explícito (FR-MC-019, FR-047-045). No hay `AuditEvent` de arranque
de instalación: el comentario de `0034` describe una posibilidad, no un escritor.

**Camino de escritura certificado** (§5 C y `test_aud_tenant_08`): una acción bajo el
tenant A queda con tenant A; bajo B, con B; una acción de empresa queda con su tenant y su
empresa. Ningún escritor se reescribe.

## 9. Superficies de lectura, todas

Evidencia: `superficies.txt`.

| Superficie | Alcance hoy | Filtro de tenant | Filtro de empresa | Permiso | Veredicto |
|---|---|---|---|---|---|
| `GET /api/v1/audit/events` | `TENANT/INSTALLATION` | **ausente** → **presente** | no aplica (contrato) | `audit:view` | **la fuga; corregida** |
| `GET /api/v1/reporting/audit/timeline` | `COMPANY_SCOPE` | implícito: `CompanyContext` solo resuelve empresas del tenant del usuario (`404 COMPANY_NOT_FOUND` si no) | `ctx.company_id` | `get_current_user` + contexto | acotada; probada hostil (`test_aud_tenant_09`) |
| `GET /api/v1/audit/events/{id}` | declarada en `api-contracts.md:72` | — | — | — | **no existe en el código** (§19) |
| Exportación de auditoría | — | — | — | — | **no existe**: `reporting.export` exporta filas de informes; `AuditExportRequested` es solo un nombre en `contracts/events.md` |
| Dashboard / conteos | — | — | — | — | `reporting.dashboard` **no** lee `AuditEvent` |
| Frontend `AuditoriaPage` (`/auditoria`) | consume el listado | — | — | — | no se toca (deudas `AUDITORIA-SOBRE-VS-ARRAY`, `AUDITORIA-CREATED-AT`) |
| Frontend `ReportesAuditoriaPage` (`/reportes/auditoria`) | consume la línea de tiempo | — | — | — | sin cambio |
| E2E `approvals.spec.ts:300` | consume el listado con `?limit=200` (parámetro no declarado) | — | — | — | mismo tenant; sin cambio (§19) |

No hay IDOR que probar porque no hay detalle; no hay CSV que probar porque no hay
exportación. `test_aud_tenant_11` fija el inventario: si nace una superficie nueva bajo
`/audit`, la prueba lo dice.

## 10. El contrato, leído entero

**FR-001-032** (P0, Sistema): «Toda operación pertenece a una empresa y respeta el alcance
organizacional del usuario». Sujeto: toda operación. Alcance: el del usuario. Restricción:
no salir de él. Excepción: ninguna.

**FR-001-033** (P0, QA): «Las pruebas incluyen aislamiento negativo: un usuario de una
empresa no accede a datos de otra». Decide la **prueba**, no solo la regla: el aislamiento
se demuestra con un usuario que intenta y no consigue.

Entre ambos: 032 decide el alcance (tenant y empresa del usuario); 033 exige demostrarlo en
negativo; los permisos los decide FR-001-040/042 (`audit:view`), y el fix no los sustituye.

**ADR-011** (aprobado en G0): tenant/company explícito en cada agregado, «filtros de
seguridad en repositorios», «aislamiento verificable y pruebas negativas», «reportes y
exportaciones verifican alcance antes de ejecutar». **ADR-012**: `AuditEvent` con tenant y
company, «endpoint de timeline con permisos», sin borrado (P5).

**ARCH-MC-001**, converged: FR-MC-020 «toda consulta se acota en el backend», FR-MC-021
«un listado nunca devuelve filas ajenas esperando que el cliente filtre», FR-MC-022 «leer
un recurso ajeno responde 404». Y su `endpoint-scope-matrix.md §audit (1)`:
`GET /api/v1/audit/events` → **`TENANT/INSTALLATION`**, origen de la empresa **no aplica**,
«Hoy: tenant», «Debe: sin cambio». La guarda `test_n10_convergence.py:204` lo fija:
`"/api/v1/audit": "tenant: la bitácora se consulta por tenant"`. La matriz describía como
«hoy» lo que el handler nunca hizo: ese es exactamente el defecto.

### Tenant frente a empresa dentro del tenant

Dos niveles, resueltos en orden:

1. **Nunca otro tenant.** Decidido por FR-001-032/033; no hay excepción.
2. **Dentro del tenant, todas las empresas.** Decidido por ARCH-MC-001: el listado es de
   tenant y la empresa «no aplica»; el modelo lo declara (`Scope.TENANT`); la matriz
   canónica lo razona («del tenant como fila»); el precedente es `list_users`, que
   devuelve el tenant entero; y la vista **por empresa** ya existe y es otra:
   `/reporting/audit/timeline`, `COMPANY_SCOPE`, con `X-Kontrol-Company` validada. Un
   usuario con `audit:view` ve la bitácora de su tenant, incluidas las empresas en las
   que no opera; si quiere solo la suya, tiene la línea de tiempo. No se restringe
   «indebidamente a la empresa actual», que es lo que el encargo prohíbe decidir por
   intuición.

### Roles cross-tenant

**No existen.** `User` no tiene marca de superusuario; los roles son del tenant (`ADMIN`
se crea por tenant en `_bootstrap_roles`, con `company_id` nulo = «vale en cualquier
empresa **del tenant**», `identity_access/models.py:41-47`); `CROSS_TENANT` aparece solo
en `core/mc/preflight.py` como clase diagnóstica de migración. El servidor central de
licencias es externo a la instalación. No se abre ninguna excepción.

### 403 / 404

FR-MC-022 y `n8-company-header-contract.md §4`: recurso ajeno → **404 sin revelar
existencia**. Aquí no hay detalle; en el listado, lo ajeno simplemente no está. La línea
de tiempo responde `404 COMPANY_NOT_FOUND` (probado).

## 11. `/speckit.specify`

Tras `FR-001-117`:

| ID | Requisito | Prioridad |
|---|---|---|
| FR-001-118 | Todo evento de auditoría de un tenant es visible **únicamente** dentro de ese tenant; no existe excepción cross-tenant | P0 |
| FR-001-119 | Un administrador de tenant no lee eventos de otro tenant: `admin` no significa cross-tenant | P0 |
| FR-001-120 | El aislamiento lo aplica el **backend** desde el contexto autenticado; ni consulta, ni cuerpo, ni cabecera lo amplían | P0 |
| FR-001-121 | El alcance de tenant se aplica **antes** de filtros funcionales, recuento y paginación, en SQL | P0 |
| FR-001-122 | `total` cuenta solo los eventos visibles en el alcance autorizado | P0 |
| FR-001-123 | Un evento ajeno no es recuperable por identificador, exportación ni superficie equivalente; las superficies bajo `/audit` quedan inventariadas | P0 |
| FR-001-124 | Los escritores bajo contexto autenticado persisten el tenant canónico | P0 |
| FR-001-125 | El tenant de un evento no lo elige el cliente | P0 |
| FR-001-126 | La empresa, cuando aplica, se evalúa dentro del tenant autorizado; el listado de tenant no se acota a la empresa actual | P0 |
| FR-001-127 | Ningún evento histórico se pierde, se borra ni se reasigna al corregir el aislamiento | P0 |
| FR-001-128 | Un evento con tenant nulo no tiene lector en el listado de tenant; no se admite `IS NULL OR` | P0 |
| FR-001-129 | Existen pruebas hostiles multi-tenant con eventos de contenido idéntico | P0 |
| FR-001-130 | La misma protección cubre **todas** las superficies públicas de lectura de `AuditEvent` | P0 |
| FR-001-131 | No existe filtrado de tenant únicamente en el frontend | P0 |
| FR-001-132 | Filtros funcionales, orden y paginación se conservan | P0 |

| ID | Criterio |
|---|---|
| AC-023 | **Dado** EVENT_A (tenant A) y EVENT_B (tenant B) idénticos en todo lo demás, **cuando** un administrador de A lista, **entonces** ve A, no ve B y `total` es 1 |
| AC-024 | **Dado** 23 eventos en A y 23 en B, **cuando** A pagina de 10 en 10, **entonces** obtiene 10, 10 y 3, todos suyos |
| AC-025 | **Dado** un usuario de A limitado a la empresa A1, **entonces** el listado de tenant incluye A2 y la línea de tiempo con `X-Kontrol-Company: A2` responde 404 |
| AC-026 | **Dado** una fila con tenant nulo, **entonces** ningún tenant la ve |
| AC-027 | **Dado** el sello de integridad de las filas anteriores al fix, **entonces** es idéntico después |

## 12. `/speckit.clarify`

| # | Pregunta | Respuesta | Evidencia |
|---|---|---|---|
| 1 | Dueña principal | SPEC 001 | §2 |
| 2 | Dueña del contrato de seguridad | SPEC 001 + ARCH-MC-001 | §10 |
| 3 | Dueña QA | SPEC 012 | §2 |
| 4 | Tabla exacta | `audit_events` | §6 |
| 5 | Modelo exacto | `app/modules/audit/models.py::AuditEvent` | §6 |
| 6 | ¿`tenant_id` existe? | **sí** | `esquema-postgresql.txt` |
| 7 | ¿anulable? | sí (FK a `tenants`) | ídem |
| 8 | ¿`company_id` existe? | sí | ídem |
| 9 | ¿anulable? | sí (FK a `companies`) | ídem |
| 10 | Filas con tenant nulo | **0** | `datos-existentes-pre.txt` |
| 11 | Filas con empresa nula | 5/5 en la siembra: eventos de tenant | ídem |
| 12 | Semántica de tenant nulo | sin dueño, sin lector | §7 |
| 13 | Semántica de empresa nula | evento de tenant (FR-001-072) | §7 |
| 14 | ¿Eventos globales/sistema en `AuditEvent`? | **no**: tablas propias | §8 |
| 15 | ¿Rol cross-tenant? | **no** | §10 |
| 16 | Alcance del admin | su tenant | §10 |
| 17 | Empresa dentro del tenant | todas (ARCH-MC-001) | §10 |
| 18 | Caminos de escritura | 22 sitios, una fábrica | §8 |
| 19 | Escritores de fondo | `SISTEMA` con empresa explícita | §8 |
| 20 | Endpoint de listado | `GET /api/v1/audit/events` | §4 |
| 21 | Endpoint de detalle | declarado, **no implementado** | §9, §19 |
| 22 | Exportaciones | ninguna de `AuditEvent` | §9 |
| 23 | Dashboard/reportes | no leen `AuditEvent` | §9 |
| 24 | Permiso actual | `audit:view` | §4 |
| 25 | Uso del contexto | `User` autenticado, antes descartado | §4 |
| 26 | Recuento actual | `len(select(...).all())` sin alcance | §4 |
| 27 | Paginación | `offset/limit` sobre el conjunto global | §4 |
| 28 | Filtros funcionales | `entity_type`, `entity_id`, `action` | §4 |
| 29 | ¿Migración? | **no** | §6 |
| 30 | ¿Backfill? | **no** | §7 |
| 31 | Ambigüedad de datos existentes | ninguna | §7 |
| 32 | HTTP para acceso ajeno por id | 404 (FR-MC-022); sin detalle hoy | §10 |
| 33 | Estrategia de pruebas | suite hostil de 11 pruebas, dos tenants, contenido idéntico, SQLite y PostgreSQL | §15 |
| 34 | Mutaciones | 7 mutantes del handler | §15 |
| 35 | Regresión | backend completo en SQLite y PostgreSQL; N10; E2E del consumidor | §16 |

**MATERIAL OQ = 0. UNKNOWN = 0.** La única pregunta que podía detener el ciclo —qué ven
las empresas dentro del tenant— la tenía decidida ARCH-MC-001 antes de empezar.

## 13. `/speckit.plan`

| W | Trabajo | Resultado |
|---|---|---|
| W01 | checkpoint | §0 |
| W02 | recuperar evidencia de UI-BUSQUEDA-MUERTA | `evidence/dead-search/`, roadmap, `aae7cd2` |
| W03 | dueñas | §2 |
| W04 | reproducir determinista | §5 |
| W05–W07 | modelo, PostgreSQL, migraciones | §6 |
| W08–W10 | datos, tenant nulo, empresa nula | §7 |
| W11–W12 | escritores y contexto | §8 |
| W13 | superficies | §9 |
| W14–W18 | FR-001-032/033, Spec 001, semánticas | §10 |
| W19–W22 | consulta, recuento, detalle, exportación | §4, §9 |
| W23 | migración/backfill | ninguno |
| W24 | diseño mínimo | abajo |
| W25–W30 | pruebas, hostiles, IDOR (n/a), escritura, regresión de filtros, mutaciones | §15 |
| W31–W34 | dirigido, completo, integración, E2E | §16 |
| W35 | deriva de esquema | N10 verde |
| W36–W38 | análisis final, trazabilidad, convergencia | §17, §18, §20 |

### Diseño elegido — una cláusula, en el sitio donde nace el conjunto

```
AuditEvent
  → WHERE tenant_id = user.tenant_id      ← alcance de tenant (nuevo)
  → [company: no aplica en esta superficie]
  → filtros funcionales (entity_type, entity_id, action)
  → ORDER BY event_time DESC
  → total (sobre el conjunto acotado)
  → OFFSET/LIMIT
```

Descartado: filtrar por empresas accesibles (dejaría fuera los eventos de tenant y
contradiría ARCH-MC-001); `IS NULL OR` (inventa un lector); un `tenant_id` en la consulta
(el cliente no es autoridad); filtrar en Python tras paginar (rompe `total` y las páginas);
un `join` con `companies` (perdería los eventos sin empresa). Todos ellos son, además,
mutantes que la suite mata (§15).

No se cambia `total = len(...)` por un `COUNT`: sería una mejora de eficiencia ajena al
aislamiento (§19).

## 14. CONSTITUTION GATE

| # | Puerta | Veredicto |
|---|---|---|
| G-AUD-01 | checkpoint reconciliado | **PASA** — `aae7cd2` |
| G-AUD-02 | dueñas resueltas | **PASA** — 001 · ARCH-MC-001 · 012 · 009 |
| G-AUD-03 | leak reproducido determinista | **PASA** — §5, PostgreSQL |
| G-AUD-04 | modelo mapeado | **PASA** — 18 columnas |
| G-AUD-05 | esquema inspeccionado | **PASA** — deriva 0 |
| G-AUD-06 | historia de migraciones | **PASA** — 0001, 0034 |
| G-AUD-07 | filas con tenant nulo clasificadas | **PASA** — 0 filas; por escritor |
| G-AUD-08 | semántica de empresa nula | **PASA** — evento de tenant |
| G-AUD-09 | eventos globales/sistema | **PASA** — no existen en `AuditEvent` |
| G-AUD-10 | roles cross-tenant | **PASA** — no existen |
| G-AUD-11 | FR-001-032 leído entero | **PASA** |
| G-AUD-12 | FR-001-033 leído entero | **PASA** |
| G-AUD-13 | contrato del contexto verificado | **PASA** — `User` + `CompanyContext` |
| G-AUD-14 | escritores inventariados | **PASA** — 22 sitios |
| G-AUD-15 | superficies inventariadas | **PASA** — 2 reales, 1 declarada sin código |
| G-AUD-16 | alcance del listado definido | **PASA** — tenant |
| G-AUD-17 | alcance del detalle definido | **PASA** — no existe; si nace, tenant (prueba 11) |
| G-AUD-18 | alcance de exportación/reportes | **PASA** — no leen `AuditEvent`; timeline por empresa |
| G-AUD-19 | empresa dentro del tenant | **PASA** — todas, por ARCH-MC-001 |
| G-AUD-20 | migración | **PASA** — 0 |
| G-AUD-21 | backfill | **PASA** — 0 |
| G-AUD-22 | sin reescritura destructiva | **PASA** — sello idéntico |
| G-AUD-23 | mutaciones definidas | **PASA** — 7 |
| G-AUD-24 | regresión definida | **PASA** — §16 |
| G-AUD-25 | MATERIAL OQ = 0 | **PASA** |
| G-AUD-26 | UNKNOWN = 0 | **PASA** |
| G-AUD-27 | TRACEABILITY = 100 % | **PASA** — §18 |

## 15. `/speckit.checklist`, `/speckit.tasks` y `/speckit.analyze` previo

Los 46 puntos del encargo quedan marcados por las secciones anteriores; los no aplicables
—detalle, exportación, dashboard, backfill— constan como «no existe» con su evidencia.

| ID | Tarea | Ficheros | Requisito | Mutación |
|---|---|---|---|---|
| T-01 | Checkpoint, árbol y entorno | — | — | — |
| T-02 | Dueñas | — | — | — |
| T-03 | Reproducción determinista sobre PostgreSQL | `qa/repro-audit-tenant-leak.py` | 129 | — |
| T-04 | Modelo, esquema real, migraciones | — | — | — |
| T-05 | Datos existentes y clasificación de nulos | — | 127, 128 | — |
| T-06 | Inventario de escritores | — | 124, 125 | — |
| T-07 | Inventario de superficies | — | 123, 130 | — |
| T-08 | Alcance de tenant en el listado | `app/modules/audit/api.py` | 118–122, 126, 128, 132 | M1–M7 |
| T-09 | Suite hostil multi-tenant | `tests/test_audit_tenant_isolation.py` | 129, 131 | — |
| T-10 | Mutaciones | — | 129 | M1–M7 |
| T-11 | Regresión SQLite y PostgreSQL, N10 | — | 132 | — |
| T-12 | E2E del consumidor del listado | — | 132 | — |
| T-13 | Documentación, roadmap, convergencia | este fichero, `docs/roadmap/*` | — | — |

**Requisitos huérfanos: 0. Tareas huérfanas: 0.**

Búsqueda previa a implementar, sobre `aae7cd2`: `AuditEvent` se consulta en **2** sitios
del producto; `tenant_id` en consulta como parámetro: **0**; `X-Kontrol-Company` en
`/audit`: **0** (y no debe estar); filtrado tardío: **1** (el defecto); `IS NULL OR`
sobre tenant: **0**; joins que cambien el alcance: **0**; excepción para admin: **0**;
`DELETE`/`UPDATE` sobre `audit_events`: **0**; migraciones: **0**; `sleep`/`retry`/`skip`
en la suite nueva: **0**. BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0.

## 16. `/speckit.implement`

Autorización expresa del encargo, con todos los contadores en cero.

**`resources/backend/app/modules/audit/api.py`** — 21 líneas añadidas, 3 quitadas: la
dependencia deja de descartarse (`user: User`), y el `select` nace con
`.where(AuditEvent.tenant_id == user.tenant_id)` antes de filtros, orden, recuento y
paginación. Docstring y comentario dicen por qué. Ningún parámetro nuevo: el contrato
publicado (`operationId`, cinco parámetros, sobre de respuesta) es el mismo.

**`resources/backend/tests/test_audit_tenant_isolation.py`** — 11 pruebas, dos tenants
(DEMO con D1/D2; DEMO2 con E1), tres usuarios de prueba (`admin2`, `ua` limitado a D1,
`sinrol`), eventos de contenido idéntico.

**`qa/repro-audit-tenant-leak.py`** — el guion de §5, para repetir la medida sobre
cualquier base de QA sembrada.

Frontend: **0 ficheros**. Esquema: **0**. Migraciones: **0**. Datos: **0**.

## 17. Evidencia — `evidence/audit-tenant-isolation/`

| Fichero | Qué demuestra |
|---|---|
| `reproduccion-pre-fix.txt` | LEAK en las dos direcciones, `total` global, escritura correcta |
| `reproduccion-post-fix.txt` | AISLADO: `admin/DEMO` recibe 7/7 de DEMO, 0 de DEMO2; sondas separadas |
| `esquema-postgresql.txt` | columnas, restricciones e índices reales |
| `datos-existentes-pre.txt` | 5 filas, tenant nulo 0, contradicciones 0 |
| `integridad-pre-fix.txt` / `integridad-post-fix.txt` | mismas 9 filas, mismo `md5`, `updated_at = created_at` en todas: **nada se borró ni se reasignó** |
| `escritores.txt` | inventario físico de escritores |
| `superficies.txt` | inventario físico de superficies |
| `mutaciones.txt` | 7/7 mutantes muertos |
| `dirigidas-postgresql.txt` | suite nueva + aislamiento + auditoría + reportes + N10 sobre PostgreSQL |
| `regresion-sqlite.txt` / `regresion-postgresql.txt` | backend completo en ambos motores |
| `e2e.txt` | consumidor del listado en un navegador real |

### Mutaciones

| Mutación | Qué reintroduce | Resultado |
|---|---|---|
| AUD-TENANT-M1 | se retira el filtro de tenant | **muere** — 9 pruebas |
| AUD-TENANT-M2 | filtro en Python después de paginar | **muere** — 6 (total, páginas, 01, 02, 06, 10) |
| AUD-TENANT-M3 | `tenant_id IS NULL OR tenant propio` | **muere** — la 10 |
| AUD-TENANT-M4 | empresas accesibles como sustituto del tenant | **muere** — 7 (los eventos de tenant desaparecen) |
| AUD-TENANT-M5 | un rol asignado exime del filtro (admin = cross-tenant) | **muere** — 9 |
| AUD-TENANT-M6 | el tenant lo propone la consulta | **muere** — la 01 (parámetro forzado) y la 11 (contrato) |
| AUD-TENANT-M7 | `total` global, items acotados | **muere** — 6 |

7/7 efectivas; fichero restaurado y comparado byte a byte con la versión corregida.

## 17b. Regresión y comprobaciones

| Suite | Resultado |
|---|---|
| `tests/test_audit_tenant_isolation.py`, SQLite | **11/11** |
| Misma suite + `test_security_integration` + `test_audit_integration` + `test_reporting` + `test_n10_convergence` + `test_mc_security_045_046`, PostgreSQL | verdes salvo tres de entorno: `reportlab` ausente del lock, `libmagic` (resuelto instalando `python-magic`) y `CREATE DATABASE` con el rol migrador (resuelto con el superusuario); N10 **5/5**, deriva ORM/base **0** |
| `ruff` y `mypy` sobre los ficheros tocados | limpios |
| Backend completo, **SQLite** | **696 pasadas · 942 saltadas · 45 no verdes, las 45 atribuidas**: 42 por `clamscan` ausente (documentales), 2 por la ruta fija `.venv/bin/alembic`, 1 `AUTH-ROTACION-SQLITE-HILOS` (falla igual con el código anterior). Las 942 saltadas son los 13 módulos que solo corren sobre PostgreSQL (P21): la cifra de referencia de ciclos anteriores, 1.656 pasadas, es la de PostgreSQL (`regresion-sqlite.txt`) |
| Backend completo, **PostgreSQL** | **1.529 pasadas · 27 saltadas · 127 no verdes, las 127 atribuidas**: 37 por `clamscan` ausente (35 documentales + 2 de `test_n9_integrity`, `FILE_NOT_SCANNED`), 88 por la ruta fija `.venv/bin/alembic` (17 fallos + 71 errores en los 13 ficheros de migración), 2 por contención con la corrida SQLite concurrente (`test_treasury`, 25/25 en solitario). **Ninguno de auditoría, aislamiento, multiempresa, N7, N9 de alcance o N10** (`regresion-postgresql.txt`) |
| Atribución de los fallos de entorno | las cuatro familias afectadas (documentos ×3, migraciones offline) dan **44 fallos / 29 pasadas / 3 saltadas** con el `api.py` **original** y exactamente lo mismo con el corregido (`atribucion-fallos-entorno.txt`) |
| E2E `approvals.spec.ts` (consume `/audit/events`), Chromium, pila real sobre PostgreSQL | **13/13** |
| Frontend | sin cambios; no se ejecuta |

Ninguna prueba se debilitó, se saltó ni se marcó como esperada-fallida para llegar aquí.

## 18. `/speckit.analyze` final y trazabilidad

| Requisito | Prueba | Mutación |
|---|---|---|
| FR-001-118 | `01_el_administrador_de_a_no_recibe_eventos_de_b`, `02_inverso…`, `03_dos_eventos_identicos…` | M1, M5 |
| FR-001-119 | `01`, `02` (ambos administradores de su tenant) | M5 |
| FR-001-120 | `01` (parámetros `tenant_id`/`company_id` forzados), `11` (contrato sin cabecera de empresa) | M6 |
| FR-001-121 | `05_la_paginacion_recorre_solo_el_tenant_propio` | M2 |
| FR-001-122 | `04_el_total_cuenta_solo_el_tenant_propio` | M7 |
| FR-001-123 | `11` (inventario: solo `/audit/events`), `09` (timeline 404) | — |
| FR-001-124 | `08_los_escritores_persisten_el_tenant_del_contexto_autenticado` | — |
| FR-001-125 | `01` forzado, `08`, `11` | M6 |
| FR-001-126 | `09_el_listado_es_de_tenant_y_la_vista_por_empresa_es_la_de_reportes` | M4 |
| FR-001-127 | sello de integridad idéntico (`integridad-*.txt`) | — |
| FR-001-128 | `10_un_evento_sin_tenant_no_lo_lee_ningun_tenant` | M3 |
| FR-001-129 | la suite entera, en SQLite y PostgreSQL | M1–M7 |
| FR-001-130 | `09`, `11`, `superficies.txt` | — |
| FR-001-131 | aislamiento probado contra la API, 0 ficheros de frontend | — |
| FR-001-132 | `05`, `06_los_filtros_funcionales_actuan_dentro_del_tenant`, `07` (permiso intacto) | M2, M7 |

| Contador final | Valor |
|---|---:|
| Eventos ajenos devueltos (PostgreSQL, post-fix) | **0** |
| Superficies de `AuditEvent` sin alcance | **0** |
| Escritores que no persisten tenant | **0** |
| Filas con tenant nulo | **0** |
| Filas borradas / reasignadas / modificadas | **0 / 0 / 0** |
| Migraciones / backfill | **0 / 0** |
| Parámetros nuevos en el contrato | **0** |
| BLOCKER / CRITICAL / CONTRADICTIONS | 0 / 0 / 0 |
| ORPHAN REQUIREMENTS / TASKS | 0 / 0 |
| MATERIAL OQ / UNKNOWN | 0 / 0 |
| **TRACEABILITY** | **100 %** |

## 19. Deudas y hallazgos registrados, no absorbidos

| ID | Hallazgo | Dueña |
|---|---|---|
| `AUDIT-DETAIL-NO-IMPLEMENTADO` (nuevo, menor) | `api-contracts.md:72` declara `GET /api/v1/audit/events/{id}` y el código no lo implementa. Si se implementa, nace con `WHERE id = :id AND tenant_id = ctx.tenant_id` y 404 (FR-MC-022); `test_aud_tenant_11` lo recordará | 001 |
| `AUDIT-TOTAL-MATERIALIZA` (nuevo, menor) | `list_events` calcula `total` cargando todas las filas del alcance (`len(...all())`) en vez de `COUNT`. Correcto, ineficiente | 001 |
| `LOCK-SIN-REPORTLAB-MAGIC` (nuevo, entorno) | `requirements.lock` no contiene `reportlab` (que `requirements.txt` sí declara) ni `python-magic`; el entorno antiguo los tenía. Un entorno reconstruido desde el lock falla en exportación PDF y en detección MIME | 001/052 |
| `TEST-MIGRACIONES-VENV-FIJO` (nuevo, menor) | **13 ficheros** de prueba invocan `.venv/bin/alembic` por ruta fija (`os.path.join(BACKEND, ".venv", "bin", "alembic")`): dependen de dónde esté el intérprete, no de cuál. En esta máquina: 2 fallos en SQLite y 40 errores en PostgreSQL, ninguno de migraciones | 052/054 |
| `AUTH-ROTACION-SQLITE-HILOS` (nuevo, menor) | `test_auth_session_rotation.py::test_dos_renovaciones_simultaneas…` falla en SQLite en esta máquina (un hilo sin respuesta), pasa en PostgreSQL y falla igual con el código anterior al delta | 001/054 |
| `E2E-APPROVALS-LIMIT-NO-DECLARADO` (nuevo, menor) | `approvals.spec.ts:300` envía `?limit=200` a un endpoint que no lo declara; recibe 20. Familia de `API-QUERY-SILENCIOSA` | 054 |
| `AUDIT-UI-ENVELOPE-MISMATCH` = `AUDITORIA-SOBRE-VS-ARRAY`, `AUDIT-UI-FECHA-CAMPO-INCORRECTO` = `AUDITORIA-CREATED-AT` | ya registradas con esos nombres estables; no se corrigen | 012 |
| `UI-BUSQUEDA-MUERTA` · Auditoría (OQ-1) | sigue material sobre **qué campos**; la mitad de la pregunta —«sobre qué conjunto»— queda contestada: el del tenant | 012 |
| `INBOX-045-AISLAMIENTO`, `API-QUERY-SILENCIOSA`, `API-COMPANY-ID-EN-CONSULTA` | abiertas, sin cambio | — |

## 20. Estado resultante

| Cosa | Estado |
|---|---|
| `AUDIT-EVENTS-SIN-TENANT` | **CLOSED / CONVERGED** |
| Ficheros de producto | 1 (`audit/api.py`) |
| Pruebas nuevas | 11 · mutaciones 7/7 |
| Esquema · migraciones · datos | 0 · 0 · 0 |
| Contrato público | sin cambio de forma |
| Frontend | sin cambio |
| Decisiones nuevas de la dueña | **ninguna**: se implementó lo decidido |
