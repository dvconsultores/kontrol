# SPEC 004 · DELTA DIRIGIDO — LA IMPORTACIÓN DE LICENCIA FIRMADA EXIGE AUTORIDAD

> Iniciado el 2026-10-06. Dueño: **Spec 004 global — Licenciamiento**
> (`spec-equivalence-map.md` línea 11: «004 Licenciamiento · `001-fundacion` +
> `010-licenciamiento-central`»). Vive junto a `spec004-licencia-preauth-delta.md`. No se
> crea otra Spec. Cierra `LICENCIA-IMPORT-SIN-SESION`.
>
> Este delta es de **autorización del llamador**. La firma, la clave, la identidad de la
> instalación, las fechas y `America/Caracas` **no se tocan**. No hay permiso nuevo, rol nuevo,
> token nuevo, esquema ni migración.

## 1. Checkpoint y dueñas

| | |
|---|---|
| `LAST_KNOWN_PREVIOUS_BASE` | `ecd22fc` |
| `REPORTED_LAST_CYCLE_FINAL_HEAD` | desconocido en el encargo; **recuperado: `0a888d9`** («fix(spec-004): el estado de la licencia es público y mínimo…»), el commit que cerró `LICENCIA-STATUS-SIN-SESION`, `LICENCIA-LECTURA-SIN-PERMISO` y `HEALTH-LIVE-VERSION` |
| `ACTUAL_HEAD` / `REMOTE_HEAD` / `ACTUAL_BRANCH` / `WORKTREE_STATE` | `0a888d9` / `0a888d9` / `develop` / limpio · `COMMITS_AFTER_ECD22FC = 1` (el anterior). Checkpoint canónico: **`0a888d9`** |
| `ORCHESTRATION_STATUS` | `VERIFIED_END_TO_END`; `orchestration_readiness.py` 11/11 · `mcp__deepseek__deepseek_chat` · `deepseek-v4-flash` · `RETRY_MAX 2` |
| `PRIMARY_OWNER` | **SPEC004** — `010-licenciamiento-central` (aquí) + `001-fundacion` (US-003, FR-001-050/051/054) |
| `SECURITY_OWNER` · `PERMISSION_OWNER` | Master 002 y 003 → `001-fundacion`; el permiso usado, `license:create`, ya existe en el catálogo de la 004 |
| `INSTALLATION_OWNER` | Master 052 → `001-fundacion`; **no aplica** canal de instalador: `scripts/setup.sh` y `activate-test-license.sh` activan la licencia de prueba llamando al servicio dentro del contenedor, no por HTTP |
| `QA_OWNER` | SPEC054 → `012-auditoria-integral-e2e` |
| `OWNER_IDENTITY_CONFLICT` | **0** |

**Decisión de la dueña, ya tomada:** la importación/activación/renovación de licencia firmada
no sigue anónima; se protege con un mecanismo canónico **existente**; `license:view` no se
convierte en permiso de escritura; sin permiso, rol, token ni canal de recuperación nuevos. Si
no existiera autoridad canónica, se detendría. **Existe** (§2, §3).

## 2. Inventario de escrituras de licencia (W05–W16)

| Operación | Ruta · método | Auth hoy | Permiso hoy | Actor contractual | Muta | Sin licencia | Vencida | READ_ONLY | Quién la llama |
|---|---|---|---|---|---|---|---|---|---|
| Importar licencia inicial | `POST /license/activate` | **ninguna** | — | administrador local (US-003) | estado, artefacto, evento | sí | sí | sí (`/api/v1/license/` exento del bloqueo) | nadie en el repo por HTTP: los guiones llaman al servicio |
| Importar archivo offline | `POST /license/import` | **ninguna** | — | ídem | ídem | sí | sí | sí | ídem |
| Activar/sincronizar con el servidor central | `POST /licensing/sync` | sesión | **`license:create`** | administrador (US-010-002, FR-010-002) | estado, evento, corrida | sí | sí | **no** (`require_write_allowed`) | `ConfiguracionCentralPage` |
| Solicitud de renovación (comprobante) | `POST /license/renewal-request` · `POST /licensing/renewal-requests` | sesión | — · `license:create` | administrador (FR-001-054, FR-010-020) | solicitud | sí | sí | no (central) / sí (local) | `MiLicenciaPage` (ya con `license:view`) · `RenovacionPage` |
| Transición de renovación · de modo | `POST …/transition` · `POST /licensing/mode-transition` | sesión | `license:approve` | aprobador | sí | — | — | no | `RenovacionPage` |
| Configuración central | `PUT /licensing/central-config` | sesión | `license:edit` | administrador | config | — | — | no | `ConfiguracionCentralPage` |
| Guiones | `scripts/setup.sh` (paso 6), `scripts/activate-test-license.sh`, `qa/pg-e2e-seed.py`, `qa/*-bootstrap.py` | local, dentro del contenedor o del proceso | — | operador de despliegue/QA | licencia **de prueba** | sí | — | — | `import_license` del servicio, **nunca HTTP**; sus comentarios dicen «POST /api/v1/license/activate» |
| Lecturas | `/license/status` público mínimo · `/license/detail`, `/license/history`, `/license/installation-request`, `/licensing/*` con `license:view` | cerrado el 2026-10-06 | | | no | | | | |

**Catálogo** (`setup/api.py::_bootstrap_roles`): `license: view, create, edit, approve`. No hay
`license:import`, `license:activate`, `license:renew` ni `installation:update`; **no se crean**.
`license:create` ya es el permiso de **activar** la licencia (`POST /licensing/sync`: «Sincroniza/
activa la licencia con el servidor central», FR-010-002, US-010-002: «Como administrador, quiero
sincronizar/activar la licencia») y de abrir una renovación. El rol `ADMIN` que crea
`setup/initialize` lleva el catálogo entero, `license:create` incluido.

**Representación del propietario/vendedor:** no es usuario, rol ni token del sistema. Su
autoridad es la **firma Ed25519** del artefacto con la clave privada central, verificada contra
`KONTROL_LICENSE_PUBLIC_KEY_PEM` (FR-001-050/055). El administrador local es quien **carga** el
artefacto (US-003: «Como administrador local, quiero importar y activar una licencia firmada»;
DOC-07 §6.2). Dos compuertas, por tanto: autorización del llamador (sesión + `license:create`)
y validez del artefacto (firma + identidad de instalación). Ninguna sustituye a la otra.

**Ancla de confianza:** `import_license` usa `settings.license_public_key_pem` **o, si está
vacía, la clave pública de la propia instalación** (`activate-test-license.sh` lo usa para la
licencia de prueba autofirmada). Es un mecanismo de prueba que en un despliegue sin la clave del
propietario aceptaría licencias firmadas con la clave del servidor: se registra como
`LICENCIA-ANCLA-AUTOFIRMADA` (§12); no se toca aquí.

**Frontend:** no hay pantalla ni formulario de importación; ningún `apiFetch` a `/license/activate`
ni `/license/import`. La activación real es por API (curl) o por los guiones. Nada que ocultar ni
rediseñar; sin modal.

**Límites:** el cuerpo es `LicenseImportRequest(payload: dict, signature_hex: str)` sin tope
propio; `max_upload_bytes` (25 MB) rige solo los documentos. Inventariado, no se amplía.

### Matriz de estados y acceso (W11–W13)

| Estado | ¿Existe? | Login | Sesión normal | Escrituras de negocio | Importar licencia | Autoridad disponible |
|---|---|---|---|---|---|---|
| `PENDING` (sin licencia, primera instalación) | sí | **sí** (el login no consulta la licencia; `/auth/login` exento) | sí | sí (`mode_blocks_write` solo bloquea READ_ONLY y SECURITY_SUSPENSION) | sí | `ADMIN` con `license:create` existe desde `setup/initialize` |
| `FULL_ACCESS` | sí | sí | sí | sí | sí | sí |
| `RENEWAL_NOTICE` (1–20 abr) · `CRITICAL_RENEWAL_NOTICE` (21–30 abr) | sí | sí | sí | sí | sí | sí |
| `READ_ONLY` (desde 1 may sin renovar) | sí | **sí** | sí | **423** por el middleware | **sí**: `/api/v1/license/` está en `LICENSE_EXEMPT_PREFIXES` y las rutas de importación no llevan `require_write_allowed` | sí |
| `SECURITY_SUSPENSION` | sí (transición manual) | sí | sí | 423 | sí (mismo motivo) | sí |
| «vencida», «inválida» | no son estados: vencida es `RENEWAL_NOTICE`/`CRITICAL`/`READ_ONLY` según la fecha; inválida se rechaza al importar (423) y no cambia el estado | | | | | |

**Riesgo de bloqueo mutuo: ninguno.** En todos los estados el administrador puede iniciar
sesión e importar. La ruta autorizada y documentada tras el arreglo: iniciar sesión como
administrador (`license:create`) → `POST /license/activate` o `/import` con el artefacto firmado
por el propietario. La primera activación es igual: `setup/initialize` crea al administrador
**antes** de que exista licencia.

### Reproducción, antes del arreglo (`evidence/licencia-import/antes.txt`)

Mundo nuevo (SQLite, `initialize`, clave de autoridad **generada en el proceso**, licencia
**sintética**; un usuario `lector` con todo el catálogo menos `license:create`):

| Llamador | Artefacto | Respuesta | Efecto |
|---|---|---|---|
| anónimo | firma inválida | 423 `LICENSE_SIGNATURE_INVALID` | **un evento** `LICENSE_SIGNATURE_INVALID` escrito |
| anónimo | firma válida, otra instalación | 423 `LICENSE_INSTALLATION_MISMATCH` | otro evento |
| anónimo | firma válida | **200**, estado `LIC-SINTETICA-1/FULL_ACCESS` | **la instalación queda activada por cualquiera** |
| anónimo | firma válida, licencia **más vieja y vencida** | **200**, estado `LIC-SINTETICA-VIEJA/READ_ONLY` | **la instalación queda en solo lectura por cualquiera** |
| token inventado | firma válida | 200 | igual que anónimo |
| sesión con `license:view` sin `license:create` | firma válida | 200 | un lector activa la licencia |
| anónimo ×5 | firma inválida | 423 ×5 | **+5 eventos**: la tabla de auditoría crece sin límite a voluntad de un anónimo |

`IMPORT_ENDPOINT = POST /license/activate, POST /license/import` ·
`CURRENT_ANON_STATUS = 200 con firma válida / 423 sin ella` · `CURRENT_INVALID_TOKEN_STATUS =
igual que anónimo` · `CURRENT_AUTH_STATUS = igual, sin permiso alguno` ·
`CURRENT_MUTATION_BEHAVIOR = estado reemplazado, artefacto y evento escritos; también un
evento por cada intento fallido`.

## 3. Modelo de amenaza

| Actor | Antes | Después |
|---|---|---|
| Anónimo con una licencia firmada antigua de esta instalación (p. ej. filtrada de un respaldo) | la reimporta y deja la instalación en `READ_ONLY` | 401, sin tocar nada ni escribir evento |
| Anónimo con cualquier blob | provoca verificación de firma y un evento por intento | 401 antes de parsear el artefacto |
| Usuario autenticado sin `license:create` (incluido `license:view`) | activa o reemplaza la licencia | 403, sin tocar nada |
| Administrador con `license:create` + artefacto inválido o ajeno | 423 | 423, igual (compuerta 2 intacta) |
| Administrador + artefacto válido | 200 | 200, igual; el evento lleva ahora `user_id` |
| Propietario (vendedor) | firma; no opera | igual |

## 4. `/speckit.specify`

FR-010-125..147 (los FR-LICIMP-001..023 del encargo, uno a uno):

| FR | Requisito |
|---|---|
| FR-010-125 | `POST /license/activate` y `POST /license/import` no están disponibles a llamadores anónimos |
| FR-010-126 | La autorización del llamador es independiente de la validación criptográfica del artefacto: son dos compuertas |
| FR-010-127 | Se reutiliza la autoridad canónica existente de activación: sesión válida + `license:create` (la de `POST /licensing/sync`, FR-010-002) |
| FR-010-128 · 129 · 130 | Sin permiso nuevo · sin rol nuevo · sin token, secreto ni canal de recuperación nuevos |
| FR-010-131 | Una instalación sin licencia, con aviso, vencida (`READ_ONLY`) o suspendida conserva un camino autorizado de activación/renovación: el administrador inicia sesión e importa |
| FR-010-132 | El arreglo no crea bloqueo mutuo: el login no depende de la licencia y `/api/v1/license/` sigue exento del bloqueo de escritura |
| FR-010-133 · 134 | Se siguen rechazando artefactos con firma inválida (423 `LICENSE_SIGNATURE_INVALID`) y licencias de otra instalación (423 `LICENSE_INSTALLATION_MISMATCH`), igual que hoy |
| FR-010-135 · 136 · 137 | Identidad de instalación, reglas de vigencia y `America/Caracas` intactas |
| FR-010-138 · 139 · 140 | `/license/status` público y mínimo · `/health/live` y `/ready` como quedaron · `/system/diagnostics` con sesión + `license:view` |
| FR-010-141 | Quien tiene `license:view` sin `license:create` es rechazado (403): el catálogo distingue lectura de mutación |
| FR-010-142 | Pruebas hostiles directas de backend sobre la autorización del llamador, en SQLite y PostgreSQL |
| FR-010-143 | Pruebas que distinguen «llamador no autorizado + artefacto válido» (401/403, estado intacto) de «autorizado + artefacto inválido» (423, estado intacto) |
| FR-010-144 | Sin esquema ni migración |
| FR-010-145 | Certificación E2E con `qa/e2e-run.py` y base efímera |
| FR-010-146 | Los cierres previos (estado público, lecturas con permiso, diagnóstico, health) siguen en verde |
| FR-010-147 | Si no existiera autoridad canónica, parar: no aplica, existe |

Además, dentro del contrato existente: el evento `LICENSE_IMPORTED` (y los de rechazo) lleva el
`user_id` del llamador autorizado, que hoy viaja como `None`; no es un evento nuevo.

## 5. `/speckit.clarify` — 39 preguntas

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | Dueña | SPEC004 (`010` + `001`); apoyos 002, 003, 054; 052 no aplica |
| 2–3 | Endpoint y método | `POST /license/activate`, `POST /license/import` |
| 4 | Comportamiento anónimo hoy | 200 con firma válida; 423 y evento con firma inválida |
| 5 | Validación del artefacto | firma Ed25519 contra la clave pública configurada (o la de la instalación si no hay), `installation_id`, parseo de campos |
| 6 | Mutación | reemplaza `LicenseState`, guarda artefacto, escribe evento; un evento también por intento fallido |
| 7 | Actor previsto | administrador local (US-003, DOC-07 §6.2) |
| 8 | Propietario/vendedor | la firma; no tiene usuario ni token |
| 9 | Administrador del cliente | el rol `ADMIN` de `setup/initialize` lleva `license:create`: es quien carga el artefacto por contrato |
| 10–11 | Permiso de escritura/activación existente | `license:create` (`/licensing/sync`, renovaciones) |
| 12–13 | Instalador/CLI/bootstrap | los guiones activan la licencia **de prueba** llamando al servicio dentro del contenedor; no hay canal HTTP alternativo ni hace falta |
| 14–18 | Estados, login, sesión | matriz §2: login y sesión en todos los estados; `/license/` exento |
| 19 | Primera activación | administrador creado por `setup/initialize` → login → `POST /license/activate` |
| 20 | Renovación | mismo camino, o `/licensing/sync` si hay servidor central |
| 21 | Offline | `POST /license/import`, mismo permiso |
| 22 | Candidato de autorización | `require_permission("license", "create")`, sin `require_write_allowed` (la renovación en `READ_ONLY` debe poder entrar) |
| 23 | Frontera de `license:view` | lectura; no se usa para escribir |
| 24–25 | Criptografía e identidad | sin cambios |
| 26 | Misma licencia otra vez | estado igual, evento añadido (contrato de hoy; se preserva) |
| 27 | Licencia más vieja | hoy la reemplaza y puede dejar `READ_ONLY`: deuda `LICENCIA-DOWNGRADE-FIRMADO` (§12), no se absorbe |
| 28 | Otra instalación | 423, igual |
| 29 | Auditoría | existe (`LicenseEvent`); se preserva y se completa con `user_id` |
| 30 | Consumidor frontend | ninguno |
| 31–33 | Login, health, diagnóstico | independientes; regresiones LICIMP-14..16 |
| 34 | Esquema/migración | 0 |
| 35 | Backend | `tests/test_license_import_access.py`, dos motores; mundo sin licencia aparte; estados por fechas |
| 36 | Frontend | sin cambio → sin pruebas nuevas; suite completa igualmente |
| 37 | E2E | `e2e/licencia-import.spec.ts`; el artefacto lo firma `qa/licencia_firmada.py` con la clave de la instalación de la corrida (ancla de prueba, §2); bootstrap y `READ_ONLY` se prueban en backend sobre PostgreSQL porque la siembra siempre activa y mover fechas rompería a los demás trabajadores |
| 38 | Mutaciones | 9 aplicables (§7); M-05 «solo frontend» no aplica (no hay UI) |
| 39 | DeepSeek | solo textos de guiones y contrato (T05) |

`MATERIAL OQ = 0`: la autoridad canónica existe.

## 6. `/speckit.plan` y compuerta

**Backend** (`licensing/api.py`): `activate` e `import_offline` reciben
`actor: User = Depends(require_permission("license", "create"))` y pasan
`user_id=str(actor.id)` a `import_license`. Orden de compuertas: dependencias (sesión, permiso)
→ cuerpo (Pydantic) → firma → identidad → modo → mutación. Sin `require_write_allowed`.
`service.py` no cambia.

**QA**: `qa/licencia_firmada.py` (firma un payload sintético con la clave privada de la
instalación de la corrida; solo entornos local/dev/qa) · `e2e/licencia-import.spec.ts`.
**Docs**: `scripts/setup.sh`, `scripts/activate-test-license.sh` (comentarios),
`api-contracts.md`.

**Compuerta (G01–G30):** G01–G02 HEAD y commit previo verificados ✅ · G03 orquestación ✅ ·
G04 dueña ✅ · G05 reproducido ✅ · G06–G10 actor, propietario, administrador, catálogo,
autoridad canónica ✅ · G11–G16 caminos sin licencia, vencida, `READ_ONLY`, login, bloqueo mutuo,
primera instalación ✅ (matriz) · G17–G18 fronteras de criptografía e identidad ✅ · G19 frontend
(sin flujo) ✅ · G20–G22 estado público, health, diagnóstico preservados ✅ · G23–G24 esquema =
migración = 0 ✅ · G25–G27 pruebas, mutaciones, tareas ✅ · G28–G30 `MATERIAL OQ = 0`,
`UNKNOWN = 0`, trazabilidad 100 % ✅. Constitución: P1, P2, P3, P6 (seguridad en backend), P8
(permiso del catálogo, sin nombres de rol), P10, P12, P15, P21, P24, P27 ✅; P26 no aplica.

## 7. Pruebas y mutaciones

**Backend, `tests/test_license_import_access.py`** (mundo: `initialize`; clave de autoridad
generada en el módulo e inyectada por `KONTROL_LICENSE_PUBLIC_KEY_PEM`; `admin` con todo;
`lector` con todo menos `license:create`; `comun` sin ningún `license:*`; licencias sintéticas):

| ID | Caso |
|---|---|
| LICIMP-01 | anónimo + licencia válida → 401 `AUTH_REQUIRED`; estado y eventos intactos |
| LICIMP-02 | anónimo + firma inválida → 401 con el **mismo** cuerpo que 01 (salvo `request_id`): nada distingue firma válida de inválida antes de autorizar |
| LICIMP-03 | token inventado, `Basic`, caducado → 401; intactos |
| LICIMP-04 | `comun` + válida → 403 `PERMISSION_DENIED`; intactos |
| LICIMP-05 | `lector` (`license:view`) + válida → 403; intactos |
| LICIMP-06 | `admin` + válida → 200 `{ok, license_id, mode}`; estado nuevo; evento `LICENSE_IMPORTED` con `user_id = admin` |
| LICIMP-07 | `admin` + firma inválida → 423 `LICENSE_SIGNATURE_INVALID`; estado intacto |
| LICIMP-08 | `admin` + otra instalación → 423 `LICENSE_INSTALLATION_MISMATCH`; estado intacto |
| LICIMP-09 | `admin` + la misma licencia → 200, estado igual, un evento más (contrato de hoy) |
| LICIMP-10 | `admin` + licencia más vieja → 200 y la reemplaza (contrato de hoy, documentado como `LICENCIA-DOWNGRADE-FIRMADO`); se restaura |
| LICIMP-11 | mundo **sin licencia**: anónimo → 401; `admin` inicia sesión en `PENDING` y activa → `FULL_ACCESS` |
| LICIMP-12 | fechas en `READ_ONLY`: `PUT /licensing/central-config` → 423 (bloqueo vigente) pero `admin` importa → 200 `FULL_ACCESS`; `lector` → 403 |
| LICIMP-13 | fechas en `RENEWAL_NOTICE` y `CRITICAL_RENEWAL_NOTICE`: `admin` renueva → `FULL_ACCESS` |
| LICIMP-14 | `/license/status` anónimo → exactamente `{mode, license_url}` |
| LICIMP-15 | `/system/diagnostics`: anónimo 401, `comun` 403, `lector` 200 |
| LICIMP-16 | `/health/live` `{status, service}`, `/health/ready` `{status, service, database}` |
| LICIMP-17 | sin esquema: evidencia por diff (`alembic/`, `models.py` sin cambios) |
| LICIMP-18 · 19 | 10 intentos anónimos, 10 de `lector`, 10 con token inventado, con y sin firma válida: estado **y recuento de eventos** intactos |
| LICIMP-20 | ningún rechazo 401/403 lleva identidad, `license_id`, `signature`, «firma», rutas ni detalle criptográfico |

**E2E, `e2e/licencia-import.spec.ts`**: E2E-LICIMP-01 anónimo → 401 y evento no visible en
`/license/history` · 02 usuario sin `license:*` → 403 · 03 usuario con `license:view` sin
`license:create` → 403 · 04 administrador + artefacto válido (firmado por el ayudante con la clave
de la instalación de la corrida; `license_id` `LIC-E2E`, mismo contenido) → 200 y `/license/detail`
lo refleja · 05 administrador + firma inválida → 423 · 06 administrador + otra instalación → 423 ·
07 · 08 (sin licencia; `READ_ONLY`) → en backend sobre PostgreSQL (LICIMP-11, 12), no en E2E (la
siembra siempre activa y mover fechas rompería a los demás trabajadores) · 09 estado público
mínimo · 10 diagnóstico protegido.

**Mutaciones:** M-01 `activate` sin autorización → LICIMP-01 · M-02 `license:view` en vez de
`license:create` → LICIMP-05 · M-03 `verify_license_signature` siempre verdadero → LICIMP-07 ·
M-04 sin comprobar la instalación → LICIMP-08 · M-05 «solo frontend»: **no aplica** (no hay UI) ·
M-06 `import` sin autorización → LICIMP-18/19 (estado y eventos cambian) · M-07 `_bootstrap_roles`
sin `license:create` → LICIMP-11 (primera activación imposible) · M-08 `/api/v1/license/` fuera
de `LICENSE_EXEMPT_PREFIXES` → LICIMP-12 (renovación en `READ_ONLY` bloqueada) · M-09
`/license/detail` sin permiso → LIC-09 · M-10 diagnóstico sin permiso → SYS-04.

## 8. `/speckit.tasks` y `/speckit.analyze` previo

| ID | Tarea | Req. | EXECUTOR · MODEL | SEC | EGRESS | Ficheros |
|---|---|---|---|---|---|---|
| T01 | Reconciliación, inventario, matriz, reproducción, amenaza, diseño | todos | CLAUDE | YES | n-a | este documento, `evidence/licencia-import/antes.txt` |
| T02 | `activate` e `import_offline` con `license:create` y `user_id` | 125–134, 141 | CLAUDE | **YES** | n-a | `licensing/api.py` |
| T03 | `tests/test_license_import_access.py` LICIMP-01..20 | 142, 143 | CLAUDE | **YES** | n-a | `tests/` |
| T04 | `qa/licencia_firmada.py` · `e2e/licencia-import.spec.ts` | 145 | CLAUDE | **YES** | n-a | `qa/`, `e2e/` |
| T05 | Comentarios de `setup.sh` y `activate-test-license.sh`; filas de `api-contracts.md` | 131, docs | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | tres ficheros |
| T06 | Auditar y aplicar T05; mutaciones M-01..M-10 | 142 | CLAUDE | NO | n-a | — |
| T07 | Backend dirigido y completo (dos motores); frontend completo; E2E dirigido y globales con `qa/e2e-run.py` | 145, 146 | CLAUDE | NO | n-a | — |
| T08 | `analyze` final, trazabilidad, convergencia, hoja de ruta, Git | — | CLAUDE | NO | n-a | documentos |

`RETRY_MAX: 2` en T05; su encargo lleva solo texto de comentarios y una tabla de contrato. `analyze`
previo: `BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` = 0; huérfanos = 0;
`MATERIAL OQ` = 0; `UNKNOWN` = 0; trazabilidad 100 % (§14).

**Autorización de `implement`:** la del encargo `LICENCIA-IMPORT-SIN-SESION`, cumplidas sus
condiciones: existe la autoridad canónica (`license:create`).

## 9. Implementación

**Backend (T02, Claude).** `licensing/api.py`: `activate` e `import_offline` reciben
`actor: User = Depends(require_permission("license", "create"))` y pasan `user_id=str(actor.id)`
a `import_license`. Como dependencia de FastAPI, la autorización se resuelve **antes** del cuerpo
y de cualquier verificación criptográfica: un anónimo no provoca ni parseo del artefacto ni
evento. Sin `require_write_allowed`: la renovación en `READ_ONLY` entra (el middleware ya exime
`/api/v1/license/`). `service.py`, `models.py`, `alembic/`, `setup/api.py`, `core/license.py`:
**sin cambios** (LICIMP-17: diff). `ruff` y `mypy` limpios.

**QA (T04, Claude).** `qa/licencia_firmada.py`: firma un payload sintético para la instalación de
la corrida con la clave privada de la instalación (ancla de confianza cuando no hay clave del
propietario); opciones `--otra-instalacion` y `--firma-invalida`; solo entornos local/dev/qa; la
URL de la base viaja en el entorno. `e2e/licencia-import.spec.ts`, 8 pruebas.

**Docs (T05, DeepSeek `deepseek-v4-flash`, 832/704 tokens, $0,0003, `AUDIT_PASS` al primer intento,
4/4 bloques exactos):** comentarios de `scripts/setup.sh` y `scripts/activate-test-license.sh`
—la licencia la importa el administrador local con sesión y `license:create`— y filas de
`api-contracts.md`. `bash -n` de ambos guiones limpio.

**Frontend:** sin cambios (no hay flujo de importación). Suite completa igualmente (§11).

Reintentos: 0. Rechazos: 0. Coste DeepSeek: **$0,0003**. Egress: solo texto de comentarios y una
tabla; `EGRESS_CHECK` a cero.

## 10. Pruebas y mutaciones

`tests/test_license_import_access.py`: 20 casos, 26 ejecuciones (parametrizados por ruta y por
cabecera). `evidence/licencia-import/mutaciones-backend.txt`, cada una GOOD→PASS, MUTATED→FAIL,
RESTORED→PASS:

| Mutación | La mata |
|---|---|
| M-01 `activate` sin autorización del llamador | LICIMP-01 |
| M-02 `license:view` en vez de `license:create` | LICIMP-05 |
| M-03 la firma no se verifica | LICIMP-07 |
| M-04 la instalación no se comprueba | LICIMP-08 |
| M-05 autorización solo en el frontend | **no aplica**: no hay UI de importación; la autoridad es del backend por construcción |
| M-06 `import` sin autorización (muta sin autoridad) | LICIMP-18/19 |
| M-07 el catálogo pierde `license:create` | el mundo de prueba no puede ni crearse (`el catálogo no trae license:create`): la primera activación sería imposible |
| M-08 `/api/v1/license/` fuera de la exención de solo lectura | LICIMP-12 |
| M-09 `/license/detail` sin permiso | LIC-09 |
| M-10 diagnóstico sin permiso | SYS-04 |

**9/9 muertas**, todas con cambio observable.

## 11. Resultados

### El contrato, después (`evidence/licencia-import/despues.txt`)

Mismo mundo que la reproducción: anónimo con firma inválida, con licencia ajena, con firma
válida y con licencia vieja → **401 `AUTH_REQUIRED`**, estado `ninguno`, **0 eventos**; token
inventado → 401 `AUTH_INVALID_TOKEN`; `license:view` sin `license:create` → **403**; cinco
intentos anónimos → 0 eventos. Administrador con firma inválida → 423 `LICENSE_SIGNATURE_INVALID`
(evento, como hoy); administrador con firma válida → 200 `FULL_ACCESS`, evento `LICENSE_IMPORTED`
con su `user_id`.

### Certificación E2E, base nueva por corrida (`corridas-globales.txt`)

| Corrida | Resultado |
|---|---|
| Dirigida 0 | 20/4: las cuatro caídas eran de mi prueba (comparaba el detalle entero; E2E-LICIMP-04 reimporta `LIC-E2E` en paralelo con otras fechas). Corregida la invariante a identificador y modo; el producto no cambió |
| Dirigida: `licencia-import` + `licencia` + `diagnostico` | **24/24** |
| Global 1 | **224 / 0 / 40** (216 + 8 nuevas) |
| Global 2 | **224 / 0 / 40** |

Limpieza `LIMPIA`, base eliminada, 0 bases de corrida al terminar. `qa/e2e_*` sin cambios.
`E2E-PANTALLA-SIN-PINTAR` no apareció.

### Backend y frontend (`backend-y-frontend.txt`)

| Suite | Resultado | Línea base |
|---|---|---|
| Backend SQLite, completa | **44 fallos / 1 082 pasan / 1 005 omitidas** (122 s): 42 de documentos sin `clamscan` + las dos intermitentes de hilo de SQLite (`test_auth_session_rotation`, `test_warehouse_structure`), que alternan solas, fallan igual con el router de HEAD y pasan en PostgreSQL. Composición de línea base; +26 ejecuciones nuevas | 42–43 fallos: documentos sin `clamscan` (+ la intermitente de hilo) |
| Backend PostgreSQL, completa | **37 fallos / 2 067 pasan / 27 omitidas** (12 min): 10 + 25 de documentos sin `clamscan`, 2 de `test_n9_integrity`. Composición idéntica a la línea base; +26 ejecuciones nuevas | 37 fallos: documentos sin `clamscan` (10 + 25) y 2 de `test_n9_integrity` |
| Seguridad de licencia dirigida (`import_access` + `license_access` + `system_access`) | 96/96 en PostgreSQL; 26/26 nuevas en SQLite | |
| Frontend `vitest` · `tsc` · `eslint` · `vite build` | 459/459 en 34 ficheros · limpios | 459 |

## 12. Deudas

**Cerrada:** `LICENCIA-IMPORT-SIN-SESION`.

**Nuevas, registradas sin absorber:**

| Deuda | Qué es | Dueña |
|---|---|---|
| `LICENCIA-DOWNGRADE-FIRMADO` | `import_license` no compara la licencia entrante con la vigente: una licencia firmada **más vieja** de esta instalación la reemplaza y puede dejar `READ_ONLY` (LICIMP-10 lo documenta). Hoy solo puede provocarlo el administrador; antes, cualquiera | 004 |
| `LICENCIA-ANCLA-AUTOFIRMADA` | sin `KONTROL_LICENSE_PUBLIC_KEY_PEM`, el ancla de confianza es la clave pública de la propia instalación (mecanismo de la licencia de prueba): un despliegue que olvide la clave del propietario aceptaría licencias firmadas con la clave del servidor. Decidir si en `production` la clave del propietario es obligatoria | 004 / 052 |

**Observadas, dentro de lo cerrado:** cada intento fallido escribía un evento; con la
autorización delante, un anónimo ya no escribe nada (LICIMP-18/19). Un llamador autorizado con
artefacto inválido sigue dejando evento, como el contrato de hoy.

## 13. Veredicto

**`LICENCIA-IMPORT-SIN-SESION`: cerrada.** Importar, activar o renovar una licencia firmada por
HTTP exige sesión válida y `license:create`, la autoridad de activar que el catálogo y la Spec 010
ya tenían; la firma del propietario y la identidad de la instalación siguen siendo la segunda
compuerta, intactas. Ningún estado de licencia deja fuera al administrador: el login no consulta
la licencia, `/api/v1/license/` está exento del bloqueo de escritura y `setup/initialize` crea al
administrador antes de que exista licencia. Sin permiso, rol, token, canal, esquema ni migración
nuevos; fechas, zona horaria, criptografía e identidad intactas.

| | |
|---|---|
| `ANONYMOUS_LICENSE_IMPORT` · `UNAUTHORIZED_LICENSE_IMPORT` · `LICENSE_VIEW_AS_WRITE` · `FRONTEND_ONLY_AUTH` | 0 |
| `NO_LICENSE_LOCKOUT` · `READ_ONLY_LOCKOUT` · `EXPIRED_LOCKOUT` · `NO_BOOTSTRAP_PATH` | 0 (matriz §2; LICIMP-11..13) |
| `SIGNATURE_BYPASS` · `INSTALLATION_MATCH_BYPASS` · `MUTATION_BEFORE_AUTH` · `DETAILED_LICENSE_LEAK` | 0 |
| `DIAGNOSTICS_REGRESSION` · `HEALTH_REGRESSION` · `PUBLIC_STATUS_REGRESSION` | 0 |
| `NEW_PERMISSION` · `NEW_ROLE` · `NEW_TOKEN` · `NEW_RECOVERY_SECRET` · `SCHEMA_CHANGE` · `MIGRATION` · `LICENSE_RULE_CHANGE` · `TIMEZONE_CHANGE` · `CRYPTO_CHANGE` · `IDENTITY_CHANGE` | 0 |
| `RETRY_WORKAROUND` · `SLEEP_WORKAROUND` · `SKIP_WORKAROUND` · `TIMEOUT_RAISED` · `SECRET_EXPOSURE` | 0 |
| `STATUS` | **`CONVERGED`** |

## 14. `analyze` final y trazabilidad

| Requisito | Prueba o evidencia | |
|---|---|---|
| FR-010-125 sin anónimos | LICIMP-01, 02, 03, 18/19; E2E-LICIMP-01; M-01, M-06; `despues.txt` | ✅ |
| FR-010-126 dos compuertas | LICIMP-01 (válida, no autorizado) frente a 07/07b/08 (autorizado, inválida); M-03, M-04 | ✅ |
| FR-010-127 autoridad canónica existente | inventario §2 (`/licensing/sync`, US-010-002); LICIMP-06; E2E-LICIMP-04 | ✅ |
| FR-010-128..130 sin permiso, rol, token nuevos | diff: `setup/api.py` sin cambios; ninguna dependencia nueva | ✅ |
| FR-010-131, 132 camino autorizado en todo estado; sin bloqueo mutuo | matriz §2; LICIMP-11, 12, 13; M-07, M-08 | ✅ |
| FR-010-133, 134 firma inválida y otra instalación siguen 423 | LICIMP-07, 07b, 08; E2E-LICIMP-05, 06 | ✅ |
| FR-010-135..137 identidad, vigencia, zona horaria | `service.py`, `core/license.py` sin cambios | ✅ |
| FR-010-138..140 estado público, health, diagnóstico | LICIMP-14, 15, 16; E2E-LICIMP-09, 10; M-09, M-10 | ✅ |
| FR-010-141 `license:view` no importa | LICIMP-05; E2E-LICIMP-03; M-02 | ✅ |
| FR-010-142, 143 pruebas hostiles, en dos motores | 26 ejecuciones SQLite, 96 PostgreSQL | ✅ |
| FR-010-144 sin esquema | diff: `models.py`, `alembic/` sin cambios | ✅ |
| FR-010-145, 146 E2E con base efímera; cierres previos en verde | dirigida 24/24; globales 224/0/40 ×2; suites completas | ✅ |
| FR-010-147 parar si no hay autoridad | no aplica: existe | ✅ |

`BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` = 0; huérfanos = 0; `MATERIAL OQ` = 0;
`UNKNOWN` = 0; trazabilidad 100 %.
