# SPEC 004 · DELTA DIRIGIDO — LA LICENCIA ANTES DE LA SESIÓN Y SIN PERMISO

> Iniciado el 2026-10-06. Dueño: **Spec 004 global — Licenciamiento**
> (`spec-equivalence-map.md` línea 11: «004 Licenciamiento · `001-fundacion` +
> `010-licenciamiento-central`»). Vive junto a `spec004-installation-race-delta.md`.
> No se crea otra Spec. Cierra `LICENCIA-STATUS-SIN-SESION`,
> `LICENCIA-LECTURA-SIN-PERMISO` y revisa `HEALTH-LIVE-VERSION`.
>
> Este delta es de **frontera de autenticación y autorización**. La política de
> licencia —ciclo anual, avisos, solo lectura, `America/Caracas`, firma Ed25519,
> identidad de instalación— **no se toca**. No hay permiso nuevo, rol nuevo,
> esquema ni migración.

## 1. Checkpoint y dueñas

| | |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` / `REMOTE_HEAD` | `ecd22fc` / **`ecd22fc`** / `ecd22fc` · `develop` · árbol limpio · `COMMITS_AFTER_ECD22FC = 0` |
| `ORCHESTRATION_STATUS` | `VERIFIED_END_TO_END`; `orchestration_readiness.py` 11/11 · `mcp__deepseek__deepseek_chat` · `deepseek-v4-flash` · `RETRY_MAX 2` |
| `PRIMARY_OWNER` | **SPEC004** — `010-licenciamiento-central` (aquí) + `001-fundacion` (FR-001-050..056, 067) |
| `SECURITY_OWNER` · `PERMISSION_OWNER` | Master 002 y 003 → `001-fundacion`; el permiso usado, `license:view`, ya existe en el catálogo de la 004 |
| `UI_OWNER` · `QA_OWNER` | Master 005 → `001-fundacion` · SPEC054 → `012-auditoria-integral-e2e` |
| `HEALTH_OWNER` | Master 001 (`FR-001-080`), apoyo aquí porque la decisión D3 se toma en este encargo |
| `OWNER_IDENTITY_CONFLICT` | **0** |

**Decisiones de la dueña, ya tomadas (D1–D4):** `GET /license/status` puede seguir
anónimo, pero con un **contrato mínimo pre-sesión** —solo lo que la experiencia de acceso
necesita—; **toda lectura detallada** de licencia o instalación exige sesión **y**
`license:view`, en el backend; `/health/live` público **no** publica la versión; `/health/ready`
sigue público si es mínimo. Reglas: lista explícita de campos (no «serializar y excluir»),
cerrado ante error (nunca `FULL_ACCESS` por defecto), una sola fuente de verdad (`mode`), 401
y 403 canónicos.

## 2. Inventario (W04–W15)

| | Hoy | Dónde |
|---|---|---|
| `GET /license/status` | única dependencia `get_db`. **Anónimo.** Devuelve `installation_id`, `activated`, `license_id`, `mode`, `period_start`, `period_end`, `critical_warning_start`, `read_only_start`, `entitlements`, `minimum_version`, `kid`, `license_url` | `licensing/api.py`, `service.get_status` |
| Sin licencia | `{installation_id, activated: false, mode: "PENDING", fechas null, entitlements {}, minimum_version null, license_url}` | `service.get_status` |
| Quién lo pide antes de la sesión | `LicenseProvider` en el arranque (`main.tsx`, por encima del router). Consume **solo `mode`** (`mode`, `blocksWrite`) y **`license_url`** (`LicenseBanner`). `Topbar` y `DashboardPage` usan `mode`. La pantalla de acceso **no** lo lee. `qa/perf-smoke.py` lo mide (latencia, sin leer el cuerpo) | `LicenseContext.tsx`, `LicenseBanner.tsx`, `qa/perf-smoke.py` |
| Quién lo pide con sesión | `MiLicenciaPage` (ruta `/mi-licencia`, menú «Principal», **sin permiso**) muestra `installation_id`, `mode`, `period_start/end`, `read_only_start` y registra comprobantes; es la pantalla de FR-001-054, cuyo actor es el **Administrador** | `MiLicenciaPage.tsx`, `Sidebar.tsx:55` |
| `GET /license/history` | **Anónimo.** Eventos de licencia con `license_id` y modo | `licensing/api.py` |
| `GET /license/installation-request` | **Anónimo.** `installation_id`, clave pública de la instalación, versión, `nonce`. Ningún frontend ni guion lo consume (los guiones usan `POST /license/activate`); la prueba de la carrera de la 004 llama al servicio, no a la ruta | `service.installation_request_payload`, `scripts/*.sh` |
| `GET /licensing/*` de lectura | `central-config`, `sync-runs`, `entitlements`, `entitlement-snapshots`, `offline-status`, `renewal-requests`, `overview`: exigen **sesión**, no `license:view`. Las escrituras sí exigen `license:edit/create/approve` | `licensing/api.py` |
| Menú | la sección «Licenciamiento» y «Diagnóstico» ya exigen `license:view`; «Mi licencia» no | `Sidebar.tsx` |
| Health | `/health/live` → `{status, service, version}` · `/health/ready` → `{status, service, database}` | `system/api.py` |
| Consumidores de `version` en `/health/live` | **ninguno**: `Dockerfile.backend` y `compose.yaml` solo miran el código de respuesta; `scripts/setup.sh` imprime el cuerpo; `docs/evidence/docker-validation-checklist.md` y `docs/auditoria` hacen `curl -fsS`; `DashboardPage` lee `version` de **`/health/ready`**, que nunca la trajo («—»). Lo afirman SYS-07 y E2E-DIAG-07, que son pruebas nuestras | inventario de este ciclo |
| Autenticación · autorización | `get_current_user` → 401 `AUTH_REQUIRED` / `AUTH_INVALID_TOKEN`; `require_permission` → 403 `PERMISSION_DENIED`, cerrado por defecto | `core/dependencies.py` |
| Middleware de licencia | bloquea escrituras en `READ_ONLY`/`SECURITY_SUSPENSION` leyendo el estado en el servidor: el frontend **no** decide (FR-001-053/056) | `core/middleware.py` |
| Pruebas existentes | ninguna llama a `GET /license/status`, `/license/history` ni `/licensing/*` por HTTP; `test_licensing_central.py` prueba el servicio | `tests/` |

### Reproducción, antes del arreglo (`evidence/licencia-preauth/antes.txt`)

Mundo nuevo (SQLite, `initialize`, licencia firmada de prueba `LIC-010000`, usuario con todo el
catálogo menos `license:view`):

- `ANON GET /license/status` → **200** con `installation_id`, `license_id`, `kid`, las cuatro
  fechas, `entitlements` y `minimum_version`. Con un token inventado, lo mismo.
- `ANON GET /license/history` → **200**; `ANON GET /license/installation-request` → **200** con
  identidad y clave pública de la instalación.
- Sin `license:view`: `/license/history`, `/licensing/central-config`, `/entitlements`,
  `/entitlement-snapshots`, `/sync-runs`, `/renewal-requests` → **200**.
- `/health/live` → `{"status":"ok","service":"kontrol-backend","version":"1.0.0"}`.
- Hallazgo lateral: sin `license:view`, `/licensing/overview` y `/licensing/offline-status`
  responden **500** sobre SQLite (`verify_offline` compara `last_reliable_date` —que SQLite
  devuelve sin zona— con `now` en UTC). Sobre PostgreSQL (`timestamptz`) no ocurre. No es de
  este encargo: queda registrado como `OFFLINE-NAIVE-EN-SQLITE` (§12).

## 3. Modelo de amenaza

| Actor | Antes | Después |
|---|---|---|
| Anónimo en la red del cliente | lee identidad de la instalación, `license_id`, `kid`, fechas, derechos y versión mínima; descarga la solicitud de activación con la clave pública | solo `mode` y `license_url`; la solicitud de activación exige sesión y permiso |
| Usuario autenticado sin `license:view` | lee todo lo anterior y además historial, configuración central, entitlements, snapshots, sincronizaciones y solicitudes de renovación | 403 en todo lo detallado; la pantalla «Mi licencia» y su entrada de menú respetan el permiso |
| Usuario con `license:view` | igual que hoy | igual que hoy, por un endpoint detallado protegido |
| Observador de `/health/live` | versión del backend | `alive` sin versión |

El frontend nunca es la frontera: el backend responde 401/403 aunque la pantalla se salte.

## 4. `/speckit.specify`

Requisitos nuevos de la Spec 004, numerados en la 010 (FR-010-102..124; los FR-LICSEC-001..023
del encargo, uno a uno):

| FR | Requisito |
|---|---|
| FR-010-102 | `GET /license/status` sigue respondiendo sin sesión, con un **contrato mínimo pre-sesión** construido por **lista explícita** de campos: `mode` y `license_url`. Nada más |
| FR-010-103 | Ese contrato **no** lleva identidad de instalación, `license_id`, `kid`, fechas, cliente, contrato, firma, claves, `entitlements`, `minimum_version`, entorno, rutas, tenant ni empresa |
| FR-010-104 | `mode` es la **única** fuente de verdad del acceso pre-sesión: no se crea `login_allowed` ni otra bandera derivada en el servidor |
| FR-010-105 | **Cerrado ante error**: sin estado de licencia el modo es `PENDING`; un fallo al calcularlo es un error, nunca `FULL_ACCESS` por defecto. Un campo ausente en el estado rompe la respuesta, no la abre |
| FR-010-106 | Un token ausente, ilegible, caducado o válido **no cambia** el contrato de `/license/status` |
| FR-010-107 | Existe `GET /license/detail`, que devuelve el estado completo de hoy, y exige sesión válida **y** `license:view` |
| FR-010-108 | Toda lectura detallada de licencia o instalación exige `license:view`: `/license/history`, `/license/installation-request`, `/licensing/central-config`, `/sync-runs`, `/entitlements`, `/entitlement-snapshots`, `/offline-status`, `/renewal-requests`, `/overview` |
| FR-010-109 | Sin sesión → 401 (`AUTH_REQUIRED`; `AUTH_INVALID_TOKEN` si el token no vale); con sesión sin permiso → 403 `PERMISSION_DENIED`. Ningún rechazo lleva datos de licencia ni de instalación |
| FR-010-110 | La cabecera de empresa no concede ni cambia nada: la licencia es global de instalación |
| FR-010-111 | Las escrituras de licenciamiento conservan sus permisos de hoy (`license:edit/create/approve`); `POST /license/activate` y `/license/import` siguen gobernados por la firma. No se tocan |
| FR-010-112 | `LicenseProvider` consume el contrato mínimo tipado (`LicensePublicStatus`); `mode`, `blocksWrite`, el aviso y la barra siguen funcionando |
| FR-010-113 | «Mi licencia» exige `license:view` **antes de pedir nada** (`ForbiddenState` sin petición) y lee `GET /license/detail` |
| FR-010-114 | La entrada de menú «Mi licencia» solo se muestra con `license:view`; el enlace del aviso de licencia, igual (el aviso en sí se muestra a todos) |
| FR-010-115 | Por URL directa sin sesión, `/mi-licencia` lleva al acceso; con sesión sin permiso muestra acceso prohibido sin pedir el detalle; con permiso pinta la pantalla y sobrevive a la recarga |
| FR-010-116 | `GET /health/live` responde `{status, service}`: **sin versión**. Sigue público |
| FR-010-117 | `GET /health/ready` sigue público y mínimo: `{status, service, database}` |
| FR-010-118 | Ningún health lleva identidad, licencia, entorno, rutas ni infraestructura |
| FR-010-119 | Los consumidores de health —Docker, `setup.sh`, lanzador E2E, panel— siguen funcionando sin cambios |
| FR-010-120 | Pruebas hostiles de backend sobre SQLite y PostgreSQL: anónimo, token ilegible, caducado, sin permiso, con permiso, cabecera de empresa, lista explícita (un campo extra en el servicio **no** sale), health |
| FR-010-121 | Pruebas de frontend: contexto, pantalla, menú, aviso. E2E con base nueva por corrida (`qa/e2e-run.py`), API y navegador |
| FR-010-122 | Sin cambios de esquema, migración, permiso, rol, reglas de vigencia, zona horaria, firma ni identidad |
| FR-010-123 | Contrato publicado al día: `specs/001-fundacion/contracts/api-contracts.md` y las pruebas que afirmaban `version` en `/health/live` |
| FR-010-124 | Nada ya convergido se reabre: suites completas de backend (dos motores), frontend y dos globales E2E en verde con sus líneas base |

## 5. `/speckit.clarify` — 32 preguntas

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | ¿Qué necesita de verdad la experiencia pre-sesión? | `mode` (aviso, barra, bloqueo de escritura en la UI) y `license_url` (enlace). Nada más; la pantalla de acceso no lee la licencia |
| 2 | ¿`activated` hace falta? | No: `mode = PENDING` ya lo dice. Sería una segunda fuente |
| 3 | ¿`blocks_write` o `login_allowed` en el servidor? | No (D1, FR-010-104): el frontend lo deriva de `mode`, y la autoridad real es el middleware |
| 4 | ¿Lista explícita o `exclude`? | Lista explícita: un DTO Pydantic con `extra="forbid"` construido campo a campo. Un campo nuevo en `get_status` no sale por accidente (LIC-16 lo prueba) |
| 5 | ¿Dónde vive el detalle? | `GET /license/detail` nuevo, protegido; `get_status` del servicio no cambia (lo usa el middleware, el diagnóstico y `overview`) |
| 6 | ¿Por qué no reusar `/licensing/overview` para «Mi licencia»? | Es más pesado (config central, offline, sincronizaciones) y hoy falla sobre SQLite; la pantalla solo necesita el estado |
| 7 | ¿`/license/installation-request` sigue anónimo? | No (D2: es una lectura de identidad de instalación). Nadie lo consume sin sesión: la activación la hace un administrador ya creado por `setup/initialize`, y los guiones usan `POST /activate` |
| 8 | ¿`POST /license/activate` e `/import` anónimos? | Son escrituras gobernadas por la firma del propietario; fuera del alcance (lecturas). Se anota, no se toca |
| 9 | ¿`POST /license/renewal-request` (sesión sin permiso)? | Escritura; conserva su regla. La pantalla que lo usa ahora exige `license:view` |
| 10 | ¿Qué permiso? | `license:view`, existente, el que ya gobierna «Licenciamiento» y «Diagnóstico». Sin permiso nuevo |
| 11 | ¿Permiso por ruta en el backend o solo frontend? | Backend siempre (P6); el frontend solo evita pedir y pintar |
| 12 | ¿401 ó 403 para anónimo? ¿404 para ocultar? | 401/403 canónicos; sin ocultación |
| 13 | ¿Rechazos sin fuga? | Sí: cuerpo de error estándar; se afirma por claves y por expresión regular |
| 14 | ¿Cabecera de empresa? | No concede ni filtra: licencia global de instalación |
| 15 | ¿Tenant? | La instalación tiene un tenant; ningún dato de tenant sale en el contrato mínimo |
| 16 | ¿«Mi licencia» para todo usuario (FR-001-054)? | Su actor es el **Administrador**; `license:view` es el permiso de ver la licencia. Se gobierna con él |
| 17 | ¿El aviso de licencia a todos? | Sí (FR-001-067): el modo lo muestra a todos; el enlace a «Mi licencia» solo a quien puede entrar, para no llevar a un «acceso prohibido» |
| 18 | ¿La pantalla pide antes de autorizar? | No: `enabled: permitido`, como `DiagnosticoPage` |
| 19 | ¿`LicenseStatus` del frontend? | Se conserva como el **detalle** (lo usan `LicensingOverview.status` y la pantalla); se añade `LicensePublicStatus` para el contexto |
| 20 | ¿Qué pasa si `/license/status` falla en el navegador? | `status = null`, `mode = null`, sin aviso. No decide nada: el servidor bloquea escrituras por sí mismo (FR-001-053) |
| 21 | ¿`version` en `/health/live` tiene consumidor contractual? | Ninguno la lee (inventario). Es separable: se retira (D3) |
| 22 | ¿Dónde se ve la versión ahora? | En el diagnóstico (`license:view`). El panel la leía de `/health/ready`, que nunca la trajo: observación `PANEL-VERSION-VACIA`, no se toca |
| 23 | ¿`/health/ready` cambia? | No: ya es mínimo (D4) |
| 24 | ¿Docker? | `HEALTHCHECK` mira el código; sin cambios |
| 25 | ¿OpenAPI `security`? | Patrón vigente: no se declara (`OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`, abierta). `response_model` del estado público sí entra en el OpenAPI |
| 26 | ¿Las pruebas de la carrera de la 004 cambian? | No: llaman al servicio |
| 27 | ¿SQLite y PostgreSQL? | Las pruebas de acceso corren en ambos. Para que `/overview` y `/offline-status` sirvan de control positivo en SQLite, el mundo de prueba deja `last_reliable_date` en nulo (camino `NO_RELIABLE_DATE`, que no compara), con la deuda citada en el fichero |
| 28 | ¿E2E? | `e2e/licencia.spec.ts` con `qa/e2e-run.py`; el usuario sin permiso lo fabrica `qa/rol_sin_permiso.py` |
| 29 | ¿Mutaciones? | ≥ 6 con cambio observable (P27) |
| 30 | ¿Egress a DeepSeek? | Solo fragmentos de prueba y tipos con valores sintéticos; sin identidades, licencias, firmas ni DSN |
| 31 | ¿Qué queda fuera? | Reglas de vigencia, fechas, zona horaria, firma, criptografía, identidad, D0-06, D0-07, deudas ajenas |
| 32 | ¿Decisión material abierta? | Ninguna: D1–D4 cubren el ciclo. `MATERIAL OQ = 0` |

## 6. `/speckit.plan` y compuerta

**Backend** (`licensing/api.py`, `system/api.py`): DTO `LicensePublicStatus(mode, license_url)`
con `extra="forbid"`; `GET /license/status` lo construye campo a campo desde `get_status` y lo
declara `response_model`; `GET /license/detail` protegido con `require_permission("license",
"view")` devuelve `get_status`; las nueve lecturas detalladas cambian `get_current_user` por
`require_permission("license", "view")`; `/health/live` deja de llevar `version`.

**Frontend**: `types.ts` añade `LicensePublicStatus`; `LicenseContext` lo consume y exporta
`PERMISO_DE_LICENCIA = "license:view"`; `MiLicenciaPage` gobierna con el permiso antes de pedir y
lee `/license/detail`; `Sidebar` pone `permission` a «Mi licencia»; `LicenseBanner` muestra el
enlace solo con permiso.

**Pruebas**: `tests/test_license_access.py` (LIC-01..16, HEALTH-01..05), SYS-07 al contrato
nuevo; `MiLicenciaPage.test.tsx`, `LicenseContext.test.tsx`, `LicenseBanner.test.tsx`,
`Sidebar.test.tsx` (NAV-03 corregido, NAV-05); `e2e/licencia.spec.ts` (E2E-LIC-01..10),
E2E-DIAG-07 al contrato nuevo. Contrato `api-contracts.md`.

**Compuerta constitucional (G01–G26):** P1 Spec antes que código ✅ (este documento precede a
todo cambio) · P2 autorización expresa ✅ (encargo `LICENCIA-STATUS-SIN-SESION`) · P3
trazabilidad ✅ (§14) · P6 seguridad en backend ✅ (401/403 en el servidor; el frontend solo
respeta) · P7 frontend uniforme ✅ (`ForbiddenState`, patrón de `DiagnosticoPage`) · P8 sin
reglas hardcodeadas ✅ (permiso del catálogo, sin nombres de rol) · P9 instalación
independiente ✅ · P10 calidad demostrable ✅ (hostiles, mutaciones, E2E) · P12 decisiones
documentadas ✅ (D1–D4, §5) · P15 datos del cliente protegidos ✅ (identidad y licencia dejan de
ser públicas) · P21 paridad de motores ✅ (pruebas en ambos; hallazgo lateral registrado) · P24
instalación limpia ✅ (base nueva por corrida) · P27 mutaciones observables ✅. Sin esquema, sin
migración: P26 no aplica. `BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`.

## 7. Pruebas y mutaciones

**Backend, `tests/test_license_access.py`** (mundo: `initialize`, licencia firmada de prueba,
`operador` sin `license:view`, `admin` con todo):

| ID | Caso |
|---|---|
| LIC-01 | anónimo `GET /license/status` → 200 con **exactamente** `{mode, license_url}`; `mode` real |
| LIC-02 | sin licencia (mundo aparte) → `mode = PENDING`, mismas dos claves; nunca `FULL_ACCESS` |
| LIC-03 | el cuerpo no contiene identidad, `license_id`, `kid`, fechas, cliente, firma, claves, `entitlements`, `minimum_version` |
| LIC-04 | token inventado y token caducado → mismo 200 y mismas claves |
| LIC-05 | sesión con `license:view` → mismo contrato mínimo (un solo contrato) |
| LIC-06 | anónimo `GET /license/detail` → 401 `AUTH_REQUIRED`, sin fuga |
| LIC-07 | token ilegible → 401 `AUTH_INVALID_TOKEN`, sin fuga |
| LIC-08 | token caducado firmado con la clave real → 401, sin fuga |
| LIC-09 | sesión sin permiso → 403 `PERMISSION_DENIED`, sin fuga |
| LIC-10 | sesión con permiso → 200 con `installation_id`, `license_id`, `mode`, fechas; `mode` igual al de `/status` |
| LIC-11 | las nueve lecturas detalladas, anónimas → 401 |
| LIC-12 | las nueve, sin permiso → 403, sin fuga |
| LIC-13 | las nueve, con permiso → 200 (control positivo) |
| LIC-14 | la cabecera de empresa no concede (sin permiso + cabecera → 403) ni cambia (con permiso → mismo cuerpo) |
| LIC-15 | estado `READ_ONLY` en la base → `/status` anónimo dice `READ_ONLY` (el aviso pre-sesión funciona) |
| LIC-16 | `get_status` parcheado con un campo extra `secret` → no sale; con `mode` ausente → error, no 200 |
| HEALTH-01 | `/health/live` → 200 `{status, service}` exactamente, `status = ok` |
| HEALTH-02 | el cuerpo de `/health/live` no contiene `app_version` ni la palabra `version` |
| HEALTH-03 | `/health/ready` → 200 `{status, service, database}` |
| HEALTH-04 | ningún health lleva identidad, licencia, entorno, rutas ni infraestructura |
| HEALTH-05 | los health responden igual con un token inventado (siguen públicos) |

**Frontend**: F-01 contexto expone `mode`/`blocksWrite` desde el contrato mínimo · F-02 contexto
ante error → `status null`, sin lanzar · F-03 «Mi licencia» sin permiso → acceso prohibido y
**cero** peticiones · F-04 con permiso pide `/license/detail` y pinta identificador, modo y fechas ·
F-05 menú: «Mi licencia» solo con `license:view` (NAV-03 corregido, NAV-05) · F-06 aviso: el modo
se muestra siempre, el enlace solo con permiso · F-07 el aviso no se pinta en `FULL_ACCESS`.

**E2E, `e2e/licencia.spec.ts`**: E2E-LIC-01 API anónima `/license/status` → exactamente dos
claves, sin identidad · 02 `/license/detail` anónimo 401 e inventado 401 · 03 sin permiso: 403 en
`/detail` y en `/history` · 04 sin permiso en el navegador: sin entrada de menú, `/mi-licencia`
→ acceso prohibido, cero peticiones al detalle · 05 administrador: entrada, pantalla con
identificador y período · 06 administrador: recarga mantiene ruta · 07 administrador: «Eventos»
carga el historial · 08 sin sesión, `/mi-licencia` → acceso · 09 health `live` sin `version`,
`ready` igual · 10 el contrato mínimo no cambia con el token del administrador.

**Mutaciones (≥ 6, observables):** M-01 `/status` devuelve `get_status` entero → LIC-01/03 ·
M-02 `/detail` con `get_current_user` → LIC-09 · M-03 una lectura detallada vuelve a
`get_current_user` → LIC-12 · M-04 `/health/live` vuelve a llevar `version` → HEALTH-01/02 ·
M-05 `MiLicenciaPage` sin `enabled: permitido` → F-03 · M-06 `Sidebar` sin `permission` → F-05 ·
M-07 `LicenseBanner` enlace sin permiso → F-06 · M-08 `/installation-request` anónimo → LIC-11.

## 8. `/speckit.tasks` y `/speckit.analyze` previo

| ID | Tarea | Req. | EXECUTOR · MODEL | SEC | EGRESS | Ficheros |
|---|---|---|---|---|---|---|
| T01 | Reconciliación, inventario, reproducción, amenaza, diseño | todos | CLAUDE | YES | n-a | este documento, `evidence/licencia-preauth/antes.txt` |
| T02 | DTO mínimo, `/license/detail`, nueve lecturas con `license:view`, `/health/live` sin versión | 102–111, 116–118 | CLAUDE | **YES** | n-a | `licensing/api.py`, `system/api.py` |
| T03 | `tests/test_license_access.py` LIC-01..16, HEALTH-01..05; SYS-07 | 120 | CLAUDE | **YES** | n-a | `tests/` |
| T04 | `LicensePublicStatus`; `LicenseContext` tipado y `PERMISO_DE_LICENCIA` | 112 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | `types.ts`, `LicenseContext.tsx` |
| T05 | «Mi licencia» con permiso y `/license/detail`; menú; enlace del aviso | 113–115 | CLAUDE | **YES** | n-a | `MiLicenciaPage.tsx`, `Sidebar.tsx`, `LicenseBanner.tsx` |
| T06 | `MiLicenciaPage.test.tsx` F-03, F-04 | 121 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | nuevo |
| T07 | `LicenseContext.test.tsx` F-01, F-02; `LicenseBanner.test.tsx` F-06, F-07; `Sidebar.test.tsx` NAV-03, NAV-05 | 121 | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | tres ficheros |
| T08 | `e2e/licencia.spec.ts` E2E-LIC-01..10; E2E-DIAG-07 | 121, 123 | CLAUDE | **YES** | n-a | `e2e/` |
| T09 | `api-contracts.md` | 123 | CLAUDE | NO | n-a | `specs/001-fundacion/contracts/` |
| T10 | Auditar y aplicar T04, T06, T07; mutaciones M-01..08 | 120, 121 | CLAUDE | NO | n-a | — |
| T11 | Backend dirigido y completo (dos motores); frontend completo; E2E dirigido y dos globales con `qa/e2e-run.py` | 119, 124 | CLAUDE | NO | n-a | — |
| T12 | `analyze` final, trazabilidad, convergencia, hoja de ruta, Git | — | CLAUDE | NO | n-a | documentos |

`RETRY_MAX: 2` en T04, T06, T07; sus encargos llevan tipos y fragmentos de prueba con valores
sintéticos: ni identidades, ni licencias, ni firmas, ni DSN, ni tokens. `analyze` previo:
`BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` = 0; huérfanos = 0; `MATERIAL OQ` =
0; `UNKNOWN` = 0; trazabilidad 100 % (§14).

**Autorización de `implement`:** la del encargo `LICENCIA-STATUS-SIN-SESION +
LICENCIA-LECTURA-SIN-PERMISO + HEALTH-LIVE-VERSION BOUNDARY REVIEW`.

## 9. Implementación

**Backend (T02, Claude).** `licensing/api.py`: `LicensePublicStatus(BaseModel)` con
`extra="forbid"`, `mode` y `license_url`; `GET /license/status` lo declara `response_model` y lo
construye `LicensePublicStatus(mode=estado["mode"], license_url=estado["license_url"])` —si
`get_status` no trae `mode`, falla (500), no inventa—. Nuevo `GET /license/detail` con
`require_permission("license", "view")` devuelve `get_status` entero. `/installation-request`,
`/history` y las siete lecturas de `/licensing/*` cambian `get_current_user` por
`require_permission("license", "view")`; `POST /license/renewal-request` conserva
`get_current_user` y las escrituras sus permisos. `system/api.py`: `/health/live` →
`{"status": "ok", "service": "kontrol-backend"}`. `service.py` **no cambia**: `get_status` sigue
sirviendo al middleware, al diagnóstico y a `overview`. `ruff` y `mypy` limpios.

**Frontend.** T04 (DeepSeek, `AUDIT_PASS` al primer intento, 6 bloques): `LicensePublicStatus` en
`types.ts`; `LicenseContext` lo consume y exporta `PERMISO_DE_LICENCIA = "license:view"`. T05
(Claude): `MiLicenciaPage` decide con `hasPermission` antes de pedir (`enabled: permitido`,
`ForbiddenState`) y lee `/license/detail` (`queryKey ["license", "detail"]`); `Sidebar` pone
`permission: "license:view"` a «Mi licencia»; `LicenseBanner` muestra el enlace «Ver Mi licencia»
solo con el permiso, y el aviso a todos. `DashboardPage`, `Topbar` y `LicensingOverview.status`
no cambian (consumen `mode` o el detalle con permiso).

**Pruebas.** T03 (Claude): `tests/test_license_access.py`, 21 casos → 56 ejecuciones
(parametrizados), más SYS-07 al contrato nuevo. T06 y T07 (DeepSeek, `AUDIT_PASS` al primer
intento, 1 + 4 bloques): `MiLicenciaPage.test.tsx` (3), `LicenseContext.test.tsx` (4),
`LicenseBanner.test.tsx` (3), `Sidebar.test.tsx` (NAV-03 corregido, NAV-05, NAV-06). T08 (Claude):
`e2e/licencia.spec.ts`, 10 pruebas; E2E-DIAG-07 al contrato nuevo. T09: `api-contracts.md` y el
fixture `openapi-routes.json` (G3/G4 del frontend exige que cada `apiFetch` apunte a una ruta
publicada: `/license/detail` se añade).

| Tarea | Ejecutor | Resultado |
|---|---|---|
| T04 | DeepSeek `deepseek-v4-flash` · 1 641/907 tokens · $0,0005 | `AUDIT_PASS`, 6/6 bloques exactos |
| T06 | DeepSeek `deepseek-v4-flash` · 2 198/1 325 tokens · $0,0007 | `AUDIT_PASS`, fichero nuevo, 3/3 en verde a la primera |
| T07 | DeepSeek `deepseek-v4-flash` · 3 061/2 143 tokens · $0,0010 | `AUDIT_PASS`, 4/4 bloques; 13/13 en verde a la primera |
| T01–T03, T05, T08–T12 | Claude | — |

Reintentos: 0. Rechazos: 0. Coste DeepSeek: **$0,0021**. Egress: solo tipos, fragmentos de
prueba y valores sintéticos (`KTL-XX-0000-TEST`); `EGRESS_CHECK` todo a cero en las tres llamadas.

## 10. Pruebas y mutaciones

`evidence/licencia-preauth/mutaciones-backend.txt` y `mutaciones-frontend.txt`; cada una
GOOD→PASS, MUTATED→FAIL, RESTORED→PASS, con la prueba que la mata:

| Mutación | Qué rompe | La mata |
|---|---|---|
| M-01 `/status` devuelve `get_status` entero | lista explícita | LIC-01, 03, 16 (`ResponseValidationError`: el `response_model` también la para) |
| M-02 `/detail` con `get_current_user` | permiso del detalle | LIC-09 |
| M-03 `/license/history` sin permiso · M-03b `/licensing/entitlements` sin permiso | permiso de las lecturas | LIC-12 |
| M-04 `/health/live` vuelve a llevar `version` | D3 | HEALTH-01 |
| M-08 `/installation-request` anónimo | D2 | LIC-11 |
| M-09 DTO construido con `model_construct(**estado)` (sin lista ni `forbid`) | lista explícita | LIC-16 |
| M-05 `MiLicenciaPage` sin `enabled: permitido` · M-05b sin `ForbiddenState` | pedir o pintar sin permiso | F-03 |
| M-06 `Sidebar` sin `permission` | menú | NAV-03, NAV-06 |
| M-07 enlace del aviso sin permiso · M-07b el aviso desaparece sin permiso | aviso para todos, enlace con permiso | F-06b, F-06 |
| M-10 `blocksWrite` siempre falso | contexto | F-01 |

**14/14 muertas** (8 backend, 6 frontend). Ninguna por casualidad: cada una cambia lo observable.

## 11. Resultados

### El contrato, después (`evidence/licencia-preauth/despues.txt`)

Mismo mundo que la reproducción: `ANON GET /license/status` → `200 {"mode":"FULL_ACCESS",
"license_url":"/mi-licencia"}`, igual con token inventado; `GET /license/detail` anónimo → 401
`AUTH_REQUIRED`, sin permiso → 403 `PERMISSION_DENIED`; `/license/history`,
`/license/installation-request` y las siete lecturas de `/licensing/*` → 401 anónimas y 403 sin
permiso, con el cuerpo de error estándar y nada de la licencia; `/health/live` →
`{"status":"ok","service":"kontrol-backend"}`; `/health/ready` como estaba.

### Certificación E2E, base nueva por corrida (`corridas-globales.txt`)

| Corrida | Resultado |
|---|---|
| Dirigida: `licencia.spec.ts` + `diagnostico.spec.ts` | **16/16** |
| Global 1 | **216 / 0 / 40** (206 + 10 nuevas) |
| Global 2 | 215 / **1** / 40 — `smoke.spec.ts:7`: el encabezado de la pantalla de acceso no visible en los 5 s por defecto de esa prueba (la única sin los 15 s del resto). El título estático ya respondía, la prueba hermana del mismo `/login` pasó en 378 ms en ese instante, registros limpios, reloj estable, sin traza (reintentos 0). Nada de `/login` lee el contexto de licencia. Es `E2E-PANTALLA-SIN-PINTAR`, abierta (tercera observación, §12); no se sube el tiempo sin causa demostrada |
| Mutante E2E M-11 (`MiLicenciaPage` sin `enabled` ni `ForbiddenState`) | E2E-LIC-04 **falla** (muere), 9/10; restaurado |
| Global 3 | **216 / 0 / 40** |

Las cinco corridas: limpieza `LIMPIA`, base eliminada, `qa/e2e-bases.py listar` → 0 al terminar.
`qa/e2e_*` sin cambios.

### Backend y frontend (`backend-y-frontend.txt`)

| Suite | Resultado | Línea base |
|---|---|---|
| Backend SQLite, completa | **43 fallos / 1 057 pasan / 1 005 omitidas** (112 s): 42 de documentos sin `clamscan` + `test_warehouse_structure` (la intermitente de hilo de SQLite). Composición idéntica a la línea base; +56 ejecuciones nuevas | 42–43 fallos: documentos sin `clamscan` (+ una intermitente de hilo) |
| Backend PostgreSQL, completa | **37 fallos / 2 041 pasan / 27 omitidas** (12 min): 10 + 25 de documentos sin `clamscan`, 2 de `test_n9_integrity`. Composición idéntica a la línea base; +56 ejecuciones nuevas | 37 fallos: documentos sin `clamscan` (10 + 25) y 2 de `test_n9_integrity` |
| `test_license_access.py` + `test_system_access.py` | 70/70 en SQLite y en PostgreSQL | nuevas |
| `ruff check` · `mypy` (ficheros tocados) | limpios | |
| Frontend `vitest` | **459/459** en 34 ficheros (447 + 12 nuevas) | 447 |
| `tsc -b --noEmit` · `eslint --max-warnings 0` · `vite build` | limpios | |

## 12. Deudas

**Cerradas:** `LICENCIA-STATUS-SIN-SESION`, `LICENCIA-LECTURA-SIN-PERMISO`, `HEALTH-LIVE-VERSION`
(local, entendida, sin consumidor de `version`).

**Nuevas, registradas sin absorber:**

| Deuda | Qué es | Dueña |
|---|---|---|
| `OFFLINE-NAIVE-EN-SQLITE` | `verify_offline` compara `last_reliable_date` (SQLite la devuelve sin zona) con UTC: `/licensing/overview` y `/offline-status` responden 500 sobre SQLite con fecha confiable; sobre PostgreSQL no. `test_licensing_central.py` no lo ve porque no recarga el objeto. Las pruebas de acceso dejan la fecha en nulo para no depender de ello (P21) | 004 |
| `PANEL-VERSION-VACIA` | la tarjeta «Versión» del panel lee `version` de `/health/ready`, que nunca la trajo («—» siempre); `HealthResponse` no coincide con `ready`. Decidir si la lee del diagnóstico para quien puede o desaparece | 001 |
| `LICENCIA-IMPORT-SIN-SESION` | `POST /license/activate` e `/import` aceptan sin sesión una licencia firmada: la firma y la ligadura son la autoridad, pero una licencia antigua de esta instalación se reimporta sin credenciales. Escrituras, fuera de este alcance; decisión de la dueña | 004 |

**Abiertas que aparecieron:** `E2E-PANTALLA-SIN-PINTAR` (tercera observación, global 2; fila
actualizada). `BACKEND-KEEPALIVE-5S` no apareció.

## 13. Veredicto

**`LICENCIA-STATUS-SIN-SESION`, `LICENCIA-LECTURA-SIN-PERMISO` y `HEALTH-LIVE-VERSION`: cerradas.**
El estado de la licencia sigue público porque la pantalla de acceso lo necesita, pero dice solo
`mode` y `license_url`, por lista explícita y cerrado ante error; todo lo detallado —el nuevo
`/license/detail`, el historial, la solicitud de activación y las lecturas centrales— exige
sesión y `license:view` en el backend, que es la autoridad, y lo respetan la pantalla, el menú y
el enlace del aviso. `/health/live` ya no publica la versión; `/health/ready` sigue mínimo. Sin
permiso nuevo, sin rol nuevo, sin esquema, sin migración, sin tocar vigencia, zona horaria, firma
ni identidad.

| | |
|---|---|
| `ANONYMOUS_LICENSE_DETAIL_ACCESS` · `AUTHENTICATED_UNAUTHORIZED_LICENSE_READ` · `FRONTEND_ONLY_SECURITY` · `ROLE_NAME_HARDCODE` | 0 |
| `SECOND_SOURCE_OF_TRUTH` (`login_allowed`) · `FAIL_OPEN_DEFAULT` · `SERIALIZE_AND_EXCLUDE` | 0 |
| `TENANT_LEAK` · `COMPANY_LEAK` | 0 (la cabecera de empresa no concede ni cambia nada) |
| `PUBLIC_HEALTH_BROKEN` · `HEALTH_VERSION_DISCLOSURE` · `HEALTH_CONSUMER_BROKEN` | 0 (Docker, `setup.sh`, lanzador y panel: inventariados; nadie parseaba `version`) |
| `PRODUCT_SCHEMA_CHANGE` · `PRODUCT_MIGRATION` · `NEW_PERMISSION` · `NEW_ROLE` · `LICENSE_RULE_CHANGE` · `CRYPTO_CHANGE` | 0 |
| `RETRY_WORKAROUND` · `SLEEP_WORKAROUND` · `SKIP_WORKAROUND` · `TIMEOUT_RAISED` | 0 |
| `E2E_FRESH_DB_REGRESSION` · bases de corrida al cierre | 0 · 0 |
| `STATUS` | **`CONVERGED`** |

## 14. `analyze` final y trazabilidad

| Requisito | Prueba o evidencia | |
|---|---|---|
| FR-010-102, 103 contrato mínimo por lista explícita | LIC-01, 03, 16; E2E-LIC-01; M-01, M-09; `despues.txt` | ✅ |
| FR-010-104 `mode` única fuente | LIC-16 (`login_allowed` no sale), LIC-10/15 (mismo modo en público y detalle); E2E-LIC-07 | ✅ |
| FR-010-105 cerrado ante error | LIC-02 (`PENDING`), LIC-16b (sin `mode` → 500) | ✅ |
| FR-010-106 el token no cambia el contrato | LIC-04, 05, 14; E2E-LIC-03, 10 | ✅ |
| FR-010-107 `/license/detail` protegido | LIC-06..10; E2E-LIC-02, 03, 07; M-02 | ✅ |
| FR-010-108 nueve lecturas con `license:view` | LIC-11..13; E2E-LIC-02, 03, 07; M-03, M-03b, M-08 | ✅ |
| FR-010-109 401/403 canónicos sin fuga | LIC-06..09, 11, 12 (`SENSIBLE`); E2E-LIC-02, 03 | ✅ |
| FR-010-110 cabecera de empresa | LIC-14 | ✅ |
| FR-010-111 escrituras sin cambio | diff de `licensing/api.py` (solo `GET`) | ✅ |
| FR-010-112 contexto tipado | F-01, F-01b, F-02, F-02b; M-10; `tsc` | ✅ |
| FR-010-113 pantalla con permiso antes de pedir | F-03, F-04, F-04b; E2E-LIC-04, 05; M-05, M-05b, M-11 | ✅ |
| FR-010-114 menú y enlace del aviso | NAV-03, 05, 06; F-06, F-06b, F-07; E2E-LIC-04, 05, 10; M-06, M-07, M-07b | ✅ |
| FR-010-115 URL directa, prohibido, recarga | E2E-LIC-04, 06, 08 | ✅ |
| FR-010-116..118 health | HEALTH-01..05, SYS-07, SYS-08; E2E-LIC-09, E2E-DIAG-07/08; M-04 | ✅ |
| FR-010-119 consumidores de health | inventario §2; tres globales con el lanzador (`/health/ready`) | ✅ |
| FR-010-120, 121 pruebas | 21 casos / 56 ejecuciones backend en dos motores; 12 frontend; 10 E2E | ✅ |
| FR-010-122 sin esquema, migración, permiso, rol, reglas | diff: `service.py`, `models.py`, `alembic/`, `setup/api.py` sin cambios | ✅ |
| FR-010-123 contratos y pruebas al día | `api-contracts.md`, `openapi-routes.json`, SYS-07, E2E-DIAG-07 | ✅ |
| FR-010-124 nada se reabre | suites completas (§11); globales 216/0/40 ×2 | ✅ |

`BLOCKER` · `CRITICAL` · `CONTRADICTIONS` · `OWNER CONFLICT` = 0; huérfanos = 0; `MATERIAL OQ` = 0;
`UNKNOWN` = 0; trazabilidad 100 %.
