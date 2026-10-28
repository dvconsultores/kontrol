# SPEC 001 · DELTA DIRIGIDO AUDIT-CATALOG — CATÁLOGO CERRADO, CONTEXTO DE EMPRESA, RECHAZO DEL ANÁLISIS QUE PERSISTE E INMUTABILIDAD EN LA BASE

> Delta transversal dentro de la Spec 001 (Fundación), dueña de `AuditEvent`, de `record_audit`
> (`app/shared/audit.py`), de `GET /audit/events` y de la pantalla `/auditoria` (FR-001-070..072,
> ADR-012). Ciclo **SHARED-CORE-P0-HARDENING-04** (2026-10-28).
>
> Specs afectadas, con contrato, prueba y evidencia propios:
> - **046** (Documentos): rechazo del analizador, FR-046-073/084, y contexto de empresa de sus eventos.
> - **009** (Reportes y auditoría): `/reporting/audit/timeline`, FR-009-022, que muestra la hora en Caracas.
> - **002** (MFA y reset), **003** (autoridad) y **045** (aprobaciones): emisores clasificados en el catálogo.
> - **011** y **012**, maestros (UoM) y almacenes: contexto de empresa.
>
> No se crea una Spec nueva.

## 0. Identidad y estado

| Campo | Valor |
|---|---|
| Ciclo | SHARED-CORE-P0-HARDENING-04 · AUDIT CATALOG + AUDIT-EVENTS-WITHOUT-COMPANY + SCAN-REJECTION AUDIT PERSISTENCE + AUDIT SCREEN COMPLETENESS |
| HEAD de entrada | `2c8c11d` (== origin/develop; precedido por `b24b121`, ciclo 03 CLOSED/CONVERGED) |
| Rama | `develop` (sin ramas nuevas) |
| Árbol de entrada | solo `?? requerimientos/KONTROL_SNAT_2026_00093.docx` (material de la dueña: no se toca, no se lee, no se confirma) |
| Decisiones de la dueña aplicadas | **OD-AUD-01..09** (ratificadas en el encargo 04) |
| Autorización de `implement` | El encargo 04, para SHARED-CORE-P0-HARDENING-04 (Constitución P2) |
| Estado | **IMPLEMENTED — VERIFIED — CONVERGED** (2026-10-28) |

## 1. Conciliación de gobierno del ciclo 03 (encargo §6 y §7)

- **PDD-TIME-11.** El encargo pide no representar como decisión de la dueña lo que el repositorio no
  ratifica. Por eso OD-TIME-11 pasa a ser **PDD-TIME-11**, una decisión de diseño del proyecto que
  implementa FR-009-015 con el bloqueo legal de los libros. Se corrigió en el delta 03, en ADR-020, en la
  evidencia `business-civil-date/` y en la memoria. El comportamiento no cambia y no se toca código.
- **REPORT-PERIOD-NOT-APPLIED queda CERRADA.**
  - `executive_ventas` es el único reporte no fiscal en el que aplica un mes, y filtra.
  - `operational_inventario`, `financial_aging` y `regulatory_evaluaciones` son fotos «a hoy»: el mes no
    aplica y la respuesta lo declara con `period_applied=false`.
  - Lo pendiente es solo fiscal y vive en una única deuda, **FISCAL-BOOK-PERIOD-RULE** (HIGH,
    LEGAL_VALIDATION_REQUIRED).
  - Hueco nuevo, registrado como deuda **REPORT-PERIOD-INPUT-ON-SNAPSHOT-REPORTS** (LOW): el Centro deja
    escribir un período en esos tres reportes y no avisa de que no se aplica.

## 2. Arqueología (medida, no supuesta)

### 2.1 Emisión

**Inventario estático.** `read/inventario_auditoria.py` hace un análisis AST de `app/`, resuelve los
posicionales de cada envoltorio y encuentra **195 llamadas**: 21 `record_audit`, 164 `_audit`,
9 `_auditar` y 1 `AuditEvent(`. Las 18 emiten a través de una única función, `app/shared/audit.py:record_audit`.
- Sin validación: cualquier `action` o `entity_type` se acepta, y `before`, `after` y `evidence` son
  diccionarios libres.
- Única excepción parcial: `mfa_service._audit_mfa`, que ya filtra sus claves (`AUDIT_EVIDENCE_KEYS`).

**Inventario de ejecución.** La suite SQLite completa corre con un plugin de solo lectura (`before_insert`
sobre `AuditEvent`) que registra cada par (acción, entidad), su origen, la presencia de empresa, tenant,
correlación y actor, y las claves. El detalle está en `evidence/audit-catalog/AUDIT_EMISSION_INVENTORY.md`.

**Hallazgos (H):**

| H | Dónde | Hecho medido | Clase |
|---|---|---|---|
| H1 | `documents/api.py:_audit` y `documents/service.py:_audit` | Los 17 eventos de documentos se emiten con `company_id=None`, aunque `Document.company_id` y `DocumentType.company_id` son NOT NULL | COMPANY_EVENT_MISSING_CONTEXT (OD-AUD-02) |
| H2 | `master_data/uom_api.py:_audit` | 14 eventos de UoM, presentaciones y conversiones con `company_id=None`. Las unidades nacen con `company_id=ctx.company_id` y el modelo es `Scope.COMPANY` | COMPANY_EVENT_MISSING_CONTEXT |
| H3 | `documents/api.py` | `DOCUMENT_TYPE_CREATED` y `DOCUMENT_TYPE_UPDATED` se registran con `entity_type="Document"` y el id de un tipo documental | Entidad mal rotulada: en el catálogo es LEGACY y se emite como `DocumentType` |
| H4 | `identity_access/service.py:confirm_password_reset` | `PASSWORD_RESET_FAILED` sale sin tenant incluso cuando el token es conocido (USED, EXPIRED o usuario inactivo) y el tenant se puede determinar desde `reset.user_id` | TENANT_EVENT_MISSING_CONTEXT; con token desconocido (INVALID) es legítimo |
| H5 | `documents/service.py:upload_version` | Ante un rechazo del analizador hace `record_audit` y `flush` y lanza 422; `get_db` cierra con rollback y **el evento se pierde** (deuda DOCUMENT-SCAN-REJECTION-AUDIT-NOT-PERSISTED) | R4 |
| H6 | ídem | El evento y la respuesta 422 llevan `signature`, el nombre crudo de la amenaza | Contra OD-AUD-09 y §40 |
| H7 | Toda la tabla | Ningún trigger ni regla: `pg_trigger` sobre `audit_events` da `[]` en la base sembrada. Un `UPDATE` o `DELETE` directo se acepta | R5 · OD-AUD-05 |
| H8 | `record_audit` | `request_id` solo llega cuando el llamante lo pasa (identidad y MFA); el resto de módulos no lo pasa aunque el middleware lo asigna | GOV-CTL-003 |
| H9 | Pruebas y guiones de QA | Hay sondas con acciones inventadas: `AUDCOUNT_PROBE`, `AUDTEN_PROBE`/`Probe`, `qa.css.created`/`QA_CSS` y `EXPORT`/`REPORT`, esta última construida directamente | Con un catálogo cerrado, las pruebas se adaptan a acciones catalogadas (T05) |

### 2.2 Datos de QA (AUDIT_DATA_PROFILE)

**Base E2E sembrada.** Medida con `qa/e2e-run.py --sin-frontend --orden` sobre una base efímera que se
elimina al terminar (corrida `r20261028t111440p681815n66e816`):
- 45 eventos en 2 tenants, todos con `company_id` NULL y tenant presente;
- 41 `USER_CREATED/User` sin actor (siembra);
- 1 `USER_CREATED/User` con actor;
- 2 `ROLE_ASSIGNED/UserRole` con origen `SETUP`;
- 1 `MFA_CHALLENGE_ISSUED/User`.

Los cuatro pares son de tenant y legítimos (§4). La base sembrada no tiene ningún evento de empresa: los
crea la E2E. El perfil posterior a la E2E está en §12.

### 2.3 Analizador (Spec 046)

| Resultado | Origen | `details.reason` |
|---|---|---|
| `CLEAN` | — | — |
| `INFECTED` | `signature` de ClamAV | — |
| `SCAN_FAILED` | `ClamAVScanner` | `scanner_unavailable`, `TimeoutExpired`, `OSError` (nombre de la clase), `scanner_error` (con `code`) |
| `SCAN_FAILED` | `ClamdScanner` | `scanner_unavailable`, `timeout`, `connection_refused`, `stream_interrupted`, `truncated_response`, `scanner_error`/`protocol_error` (con `response`) |
| `SKIPPED` | `DisabledScanner` | `scanning_disabled` |

- No hay ningún estado «no soportado / no analizable» en el contrato, así que no se inventa.
- La **versión del motor no se captura** hoy.
- El endpoint confirma la fase de lectura antes de analizar (`DOCUMENT-UPLOAD-HOLDS-DB-CONNECTION-DURING-SCAN`):
  cuando llega el rechazo, la sesión no tiene escrituras de negocio pendientes.

### 2.4 Lectura

- `GET /audit/events`:
  - el alcance de tenant va primero;
  - las empresas son las que tienen `audit:view`, y los eventos sin empresa solo se ven con
    `has_tenant_wide_capability`, lo que **ya cumple OD-AUD-01**;
  - filtros `entity_type`, `entity_id` y `action`;
  - orden `event_time DESC` **sin desempate** (AUDIT-ORDEN-SIN-DESEMPATE) y **sin índice** (tenant_id,
    event_time) (AUDIT-PAGINA-SIN-INDICE-DE-ORDEN);
  - responde `id`, `action`, `entity_type`, `entity_id`, `user_id`, `request_id`, `source` y
    `event_time`: sin empresa, sin alcance, sin actor legible y sin detalle (AUDIT-DETAIL-NO-IMPLEMENTADO).
- `GET /reporting/audit/timeline` (009): la empresa del contexto, con límite de 200.
- **`ReportesAuditoriaPage` pinta `event_time` como ISO crudo**, que contraviene la regla DISPLAY de ADR-020.
  El inventario de 03 no lo vio porque no hay ni `toLocale` ni corte: es una omisión de la guarda.
- `AuditoriaPage` envía `q`, que el servidor no declara (UI-BUSQUEDA-MUERTA): la caja no filtra nada.

## 3. Requisitos

### 3.1 Gobierno (releído del PDF antes del diseño)

Fichero `Ingenieria_de_Requerimientos_KONTROL_Gobierno_v1.0.pdf`, sha256 `8f86615f…`, sin cambio.

| Requisito | Prioridad | Qué exige | Qué toma este ciclo |
|---|---|---|---|
| GOV-CTL-002 | P0 | Bitácora append-only de autenticación, consultas sensibles, cambios, aprobaciones, rechazos y acciones financieras | Inmutabilidad en la base; el rechazo se audita y persiste |
| GOV-CTL-003 | P0 | Autor, actor efectivo, rol, unidad, IP/sesión, timestamp y correlación | Correlación automática; actor; IP y sesión ya existen como columnas. Rol y unidad: DEPENDENCY (Gobierno) |
| GOV-CTL-005 | P0 | Muestreo y consulta de solo lectura para auditor interno o externo, sin alterar la evidencia | **Filtros de fecha**, actor, acción, entidad, ámbito/empresa y correlación; solo lectura; base inmutable |
| GOV-CTL-010 | P0 | Historial de cambios de maestros sensibles | El catálogo clasifica los eventos de maestros; DT-06 sigue abierta |
| RNF-GOV-004 | P0 | Lo definitivo no se edita destructivamente | Triggers de `UPDATE`, `DELETE` y `TRUNCATE` |
| RNF-GOV-005 | P0 | El 100 % de las transacciones P0 con actor, autoridad, fuente, soporte, timestamp y correlación | Contexto obligatorio por entrada del catálogo |
| RNF-GOV-009 | P0 | Trazabilidad de cifras | No afectado |
| GOV-DOC-010 | P1 | Paquete de auditoría exportable | FUTURE_SPEC (Gobierno); el catálogo es su prerrequisito |

GOV-CTL-005 convierte **AUDIT-DATE-FILTER-MISSING** en un requisito de este ciclo (encargo §35).

### 3.2 Requisitos funcionales del delta

| FR | Requisito | Origen |
|---|---|---|
| FR-001-257 | Existe un catálogo cerrado y versionado de acciones de auditoría, con clave (acción, entidad). Cada entrada declara: módulo y Spec dueños, ámbito (`TENANT` o `COMPANY`), clase de seguridad, clase transaccional, contexto obligatorio, claves de detalle permitidas, política de retención, ciclo de vida (`ACTIVE`, `DEPRECATED` o `LEGACY`), origen de la emisión y descripción | OD-AUD-04, §8, §46 |
| FR-001-258 | `record_audit` rechaza (falla cerrado, `AuditContractError`) un par fuera del catálogo o en estado `LEGACY` | OD-AUD-04 |
| FR-001-259 | Un evento `COMPANY` exige `company_id`; uno `TENANT` exige `company_id` NULL. El tenant es obligatorio salvo en las entradas que declaran sujeto no resoluble | OD-AUD-02/03 |
| FR-001-260 | Las claves de primer nivel de `before`, `after` y `evidence` deben pertenecer a las permitidas por la entrada. En cualquier nivel se rechazan los nombres prohibidos (secretos, tokens, OTP, códigos de recuperación, firma de amenaza, contenido, rutas, URL, nombre original) y los valores binarios | OD-AUD-08/09, §25/26 |
| FR-001-261 | Dentro de una petición HTTP, todo evento lleva el `request_id` de la petición aunque el llamante no lo pase | GOV-CTL-003, §30 |
| FR-001-262 | PostgreSQL rechaza `UPDATE`, `DELETE` y `TRUNCATE` sobre `audit_events`, y SQLite rechaza `UPDATE` y `DELETE`. La protección nace con la tabla (`create_all`) y con la migración 0061 | OD-AUD-05, RNF-GOV-004 |
| FR-001-263 | Los eventos de documentos, UoM y presentaciones llevan la empresa del objeto. `PASSWORD_RESET_FAILED` lleva el tenant cuando el sujeto es conocido | OD-AUD-02, H1/H2/H4 |
| FR-001-264 | `GET /audit/events` acepta, además de lo existente: `desde` y `hasta` (fechas de negocio de Caracas, inclusivas, convertidas a límites UTC semiabiertos; si `desde > hasta`, 422 `INVALID_DATE_RANGE`), `username`, `company_id` (solo estrecha), `scope` (`TENANT`/`COMPANY`) y `request_id`. Ordena por `event_time DESC, id DESC` | GOV-CTL-005, §35/36 |
| FR-001-265 | Cada item añade `company_id`, `company_name`, `scope`, `action_label`, `username`, `reason` y `details`. `details` es la proyección segura de `before`/`after`/`evidence` limitada a las claves que la entrada permite; para una fila no catalogada es `{}` | §34, AUDIT-DETAIL-NO-IMPLEMENTADO |
| FR-001-266 | `GET /audit/filters` (con `audit:view`) devuelve la versión del catálogo, las acciones (código, entidad, etiqueta, ámbito y ciclo de vida), las empresas donde se audita y si la autoridad es de todo el tenant | §36, §77 |
| FR-001-267 | La pantalla Auditoría: <ul><li>filtra por Desde, Hasta, Acción, Entidad, Usuario, Ámbito/Empresa y Correlación;</li><li>muestra fecha (Caracas), acción legible, entidad, usuario, ámbito y correlación;</li><li>abre el detalle seguro de cada evento;</li><li>distingue Tenant, Empresa y «Empresa no registrada (evento histórico)»;</li><li>tiene estados de carga, vacío, error, permiso denegado y validación;</li><li>es accesible y responsive;</li><li>deja de enviar `q`.</li></ul> | §33–43, UI-BUSQUEDA-MUERTA |
| FR-009-022 (parcial) | La línea de tiempo de Reportes › Auditoría muestra la fecha en Caracas (ADR-020) | §34 |
| FR-046-073 | Un rechazo del analizador (`INFECTED`, `SCAN_FAILED` o `SKIPPED` con análisis obligatorio) deja `DOCUMENT_SCAN_REJECTED/Document`: <ul><li>con empresa, actor, tenant y correlación;</li><li>con `evidence` = categoría normalizada, `reason_code` seguro, motor, versión del motor, sha256, tamaño, MIME detectado y tipo documental;</li><li>**sobrevive** al rollback de la carga;</li><li>sin firma, contenido, nombre original ni rutas.</li></ul>La respuesta 422 lleva `scan_result` y `category`, nunca `signature` | OD-AUD-07/08/09, §18–24 |
| FR-046-089 | El usuario ve tres estados seguros y distintos: rechazo por seguridad, servicio de análisis no disponible y fallo o tiempo agotado del análisis. Ninguno afirma malware si lo que falló fue la infraestructura | §39/40 |

## 4. Decisiones de la dueña aplicadas

| OD | Aplicación |
|---|---|
| OD-AUD-01 | Se conserva el filtro vigente: un evento sin empresa solo lo ve quien tiene `audit:view` en todas las empresas del tenant (`has_tenant_wide_capability`). Lo prueban la API y la E2E |
| OD-AUD-02 | H1 y H2 se corrigen en la emisión. El catálogo marca `COMPANY` y `record_audit` exige la empresa |
| OD-AUD-03 | Los eventos de tenant (identidad, sesiones, MFA, reset, roles, denegaciones de autoridad, `COMPANY_SCOPE_DENIED/Tenant`) se quedan con `company_id` NULL. No se fuerza ninguna empresa |
| OD-AUD-04 | Catálogo cerrado. Fallo cerrado en tiempo de ejecución (`AuditContractError`) y guarda AST antes de ejecutar |
| OD-AUD-05 | Triggers en la base (§5, AD-5). Nada reescribe filas |
| OD-AUD-06 | Sin backfill. Las filas históricas sin empresa se clasifican en la evidencia, y la UI las rotula «Empresa no registrada (evento histórico)» |
| OD-AUD-07 | El rechazo se confirma en una transacción propia, después de deshacer la transacción de la carga rechazada (AD-6) |
| OD-AUD-08 | `evidence` contiene solo: `category`, `reason_code`, `engine`, `engine_version`, `sha256`, `size_bytes`, `detected_mime` y `document_type_id`. Actor, tenant, empresa, correlación y hora van en sus columnas |
| OD-AUD-09 | Ni firma ni nombre de la amenaza, ni en el evento ni en la respuesta. La categoría normalizada es `MALWARE_DETECTED` |

## 5. Diseño (Claude)

### AD-1 · Unidad del catálogo: el par (acción, entidad)

El repositorio emite códigos genéricos (`CREATE`, `UPDATE`, `DELETE`, `ACTIVE`…) para entidades de ámbitos
distintos, y renombrarlos reescribiría el significado de la historia. Por eso la clave es el par
`(action, entity_type)`.

Cada entrada, `AuditActionSpec` (inmutable), tiene estos campos:

| Campo | Valores o contenido |
|---|---|
| `code` | La acción |
| `entity_type` | La entidad |
| `owner_module` | Módulo dueño |
| `owner_spec` | Spec dueña |
| `scope` | `COMPANY` o `TENANT` |
| `tenant_required` | Bool |
| `security_class` | `SECURITY`, `AUTHORITY`, `FINANCIAL`, `FISCAL`, `REGULATORY`, `DOCUMENT`, `MASTER_DATA` u `OPERATIONAL` |
| `transaction_class` | `BUSINESS_COMMIT`, `REJECTION` o `SECURITY_DENIAL` |
| `detail_keys` | Conjunto cerrado de claves de primer nivel |
| `lifecycle` | `ACTIVE`, `DEPRECATED` o `LEGACY` |
| `emission` | `STATIC`, `DYNAMIC`, `MIGRATION`, `SETUP` o `RESERVED`, con el sitio que emite |
| `retention` | `PRESERVE_UNTIL_RETENTION_POLICY_RATIFIED` para todas: no hay norma ratificada y no se borra nada (§27) |
| `label` | Etiqueta legible en español |

Reglas del conjunto:
- `CATALOG_VERSION = "2026-10-28.1"`.
- No se añade un tercer ámbito.
- El único caso con sujeto no resoluble, `PASSWORD_RESET_FAILED` con token desconocido, se modela con
  `tenant_required=False`.

### AD-2 · Validación en `record_audit` (fallo cerrado)

En orden:
1. Búsqueda del par. Si falta o es `LEGACY`, `AuditContractError("AUDIT_ACTION_UNCATALOGUED" | "AUDIT_ACTION_LEGACY")`.
2. Tenant deducido de la empresa, como hasta ahora.
3. Ámbito: `COMPANY` sin `company_id` da `AUDIT_COMPANY_REQUIRED`; `TENANT` con `company_id` da
   `AUDIT_SCOPE_MISMATCH`. Sin tenant y con `tenant_required`, `AUDIT_TENANT_REQUIRED`.
4. Detalle: `before`, `after` y `evidence` tienen que ser `dict` o `None`.
   - Las claves de primer nivel deben estar en `detail_keys`; si no, `AUDIT_DETAIL_KEY_NOT_ALLOWED`.
   - En cualquier nivel se rechaza un nombre prohibido (`AUDIT_DETAIL_FORBIDDEN`). Se compara en minúsculas:
     `password`, `password_hash`, `new_password`, `current_password`, `token`, `access_token`,
     `refresh_token`, `reset_token`, `secret`, `totp_secret`, `mfa_secret`, `otp`, `otp_code`, `totp_code`,
     `recovery_code`, `recovery_codes`, `authorization`, `bearer`, `cookie`, `api_key`, `private_key`,
     `signature`, `threat_name`, `malware_signature`, `content`, `file_content`, `raw`, `bytes`, `body`,
     `storage_key`, `path`, `file_path`, `local_path`, `temp_path`, `url`, `temporary_url`,
     `presigned_url`, `original_name` y `filename`.
   - En cualquier nivel se rechazan los valores `bytes`, `bytearray` y `memoryview`.

`AuditContractError` hereda de `ValueError`, siguiendo el precedente de `_audit_mfa`, y lleva un `code`.
Un error de catálogo es un defecto de programación: la operación falla y no se descarta el evento en
silencio.

### AD-3 · Correlación (GOV-CTL-003)

- Una `ContextVar` `request_id_actual` en `app/core/logging.py` (junto a `new_request_id`).
- `RequestIDMiddleware` la fija antes de `call_next` y la restaura al salir.
- `record_audit` usa `request_id or request_id_actual.get()`.
- Fuera de una petición (tareas, migraciones, siembra) vale `None`, y eso no es un error: no se finge
  correlación.

### AD-4 · Contexto de empresa y tenant (H1–H4)

| Sitio | Cambio |
|---|---|
| `documents/api.py:_audit` y `documents/service.py:_audit` | Reciben `company_id`: la del documento, o la del tipo para los eventos de tipo |
| Eventos de tipo documental | `DOCUMENT_TYPE_*` se emiten con `entity_type="DocumentType"`; los pares con `Document` quedan `LEGACY` |
| `uom_api.py:_audit` | Recibe `company_id`: la del objeto, o `ctx.company_id` |
| `confirm_password_reset` | Pasa `tenant_id` del usuario conocido en USED, EXPIRED e inactivo |

### AD-5 · Inmutabilidad en la base (OD-AUD-05)

**PostgreSQL:**
- función `kontrol_audit_events_inmutable()` que hace `RAISE EXCEPTION 'AUDIT_EVENT_IMMUTABLE'` con
  `ERRCODE` `'P0001'`;
- triggers `trg_audit_events_no_update` (BEFORE UPDATE) y `trg_audit_events_no_delete` (BEFORE DELETE),
  los dos `FOR EACH ROW`;
- `trg_audit_events_no_truncate` (BEFORE TRUNCATE, `FOR EACH STATEMENT`).

**SQLite:** `trg_audit_events_no_update` y `trg_audit_events_no_delete` con `RAISE(ABORT,
'AUDIT_EVENT_IMMUTABLE')`. SQLite no tiene `TRUNCATE`. Es el equivalente soportado: la autoridad es
PostgreSQL.

**Instalación por dos caminos:**
- `event.listen(AuditEvent.__table__, "after_create", DDL(...).execute_if(dialect=...))`, para que
  `create_all` (pruebas y arranque) cree la protección con la tabla;
- la migración `0061_spec001_audit_immutability`, que la crea en bases existentes (`upgrade`) y la quita
  en `downgrade`.

**Índice.** La misma migración y el modelo añaden `ix_audit_events_tenant_event_time` (tenant_id,
event_time). Es el camino del filtro de fecha y del orden de página, y cierra AUDIT-PAGINA-SIN-INDICE-DE-ORDEN;
se absorbe porque el filtro de este ciclo depende de él.

**Lo que no se toca:** filas existentes, otras tablas y migraciones anteriores (ninguna muta `audit_events`).

### AD-6 · Rechazo del análisis que sobrevive (OD-AUD-07/08/09)

**Helper.** `record_audit_after_rollback(db, **campos)` en `app/shared/audit.py`:
1. `db.rollback()`, porque la transacción de la operación rechazada no se confirma;
2. `record_audit(...)`;
3. `db.commit()`.

Es el patrón ya establecido de `_denegar` y `require_capability_in_company` (clase `SECURITY_DENIAL`),
ahora con nombre, para la clase `REJECTION`.

**Por qué no una conexión independiente:** las pruebas trabajan dentro de una transacción externa (PG) o
de una conexión única (`StaticPool` en SQLite); una conexión aparte no vería la empresa y violaría la FK.
En el camino real la carga ya confirmó su fase de lectura antes de analizar (guarda `RuntimeError`), así
que el rollback no descarta nada legítimo.

**`upload_version`, si el análisis no es `CLEAN` y el tipo lo exige:**
1. Captura antes del rollback los ids, el sha256, el tamaño, el MIME, la categoría y el `reason_code`.
2. Emite `DOCUMENT_SCAN_REJECTED/Document` con `company_id` del documento, `reason=category` y esta
   `evidence`: `category`, `reason_code`, `engine`, `engine_version`, `sha256`, `size_bytes`,
   `detected_mime` y `document_type_id`.
3. Lanza el 422 con `details={"scan_result", "category"}`.

**Categoría y `reason_code`:**

| Resultado | Categoría | `reason_code` |
|---|---|---|
| `INFECTED` | `MALWARE_DETECTED` | `threat_detected` |
| `SCAN_FAILED` con `scanner_unavailable` o `connection_refused` | `SCANNER_UNAVAILABLE` | el motivo |
| `SCAN_FAILED` con `timeout` o `TimeoutExpired` | `SCAN_TIMEOUT` | `timeout` |
| Otro `SCAN_FAILED` | `SCAN_ERROR` | `stream_interrupted`, `truncated_response`, `scanner_error` o `protocol_error`; si no, `os_error` o `scanner_error` |
| `SKIPPED` | `SCANNER_UNAVAILABLE` | `scanning_disabled` |

**Versión del motor.** `FileSecurityScanner.engine_version()` es un método no abstracto que por defecto
devuelve `None`, de modo que los dobles de prueba existentes no se rompen:
- `ClamAVScanner` ejecuta `[binary, "--version"]` (con `--database` si existe), con 10 s de tope, y toma
  la primera línea recortada a 120 caracteres;
- `ClamdScanner` usa `zVERSION`;
- `DisabledScanner` devuelve `"disabled"`;
- cualquier fallo da `None` y la evidencia dice `"unknown"`.

La versión solo se pide en el camino del rechazo, no en cada análisis.

### AD-7 · API de lectura

**`GET /audit/events`.**
- Parámetros declarados:
  - nuevos: `desde`/`hasta` (`date`), `username`, `company_id`, `scope` (`Literal["TENANT","COMPANY"]`) y `request_id`;
  - existentes: `page`, `page_size` ≤100, `entity_type`, `entity_id` y `action`.
- Límites del día con `limites_del_dia_utc` (ADR-020): `event_time >= inicio(desde)` y `< fin(hasta)`.
- `desde > hasta` da 422 `INVALID_DATE_RANGE`.
- `company_id` fuera de las empresas auditables devuelve el conjunto vacío: estrecha, no amplía y no revela
  que la empresa exista.
- `scope=TENANT` equivale a `company_id IS NULL`, y solo trae algo con autoridad de todo el tenant (OD-AUD-01).
- Orden `event_time DESC, id DESC`.
- Proyección por página:
  - una consulta de nombres de usuario del tenant y otra de nombres de empresa, sin N+1;
  - `scope` sale del catálogo, o `UNCATALOGUED`;
  - `details` sale de `detail_keys` sobre `before`, `after` y `evidence`, y omite los nombres prohibidos.

**`GET /audit/filters`.** Con `audit:view`. Devuelve `catalog_version`, `actions` (las `ACTIVE`, `DEPRECATED`
y `LEGACY`, para poder interpretar la historia), `companies` (`id`, `code` y `name` de las empresas con
`audit:view`) y `tenant_wide`. **No** expone `detail_keys`. Es la única ruta nueva (420 → 421).

**`/reporting/audit/timeline`.** No cambia. Es la decisión pendiente AUDITORIA-PANTALLA-DUPLICADA.

### AD-8 · Pantalla Auditoría (`/auditoria`)

**Filtros:**

| Filtro | Control |
|---|---|
| Desde, Hasta | `type="date"`, viajan tal cual (OD-TIME-08) |
| Acción | `select` agrupado del catálogo |
| Entidad | Texto exacto |
| Usuario | Nombre de usuario exacto |
| Ámbito / Empresa | `select`: «Todas», «Tenant», si hay autoridad de todo el tenant, y cada empresa auditable |
| Correlación | Texto |

Los filtros se aplican con un botón «Aplicar», vuelven a la página 1 y se pueden limpiar. Se elimina la
caja `q`.

**Columnas:** Fecha (`formatearFecha`, Caracas) · Acción (etiqueta + código) · Entidad (tipo + id) · Usuario
(nombre o «Sistema») · Ámbito («Tenant», nombre de la empresa o «Empresa no registrada (evento histórico)») ·
Correlación · «Ver detalle».

**Detalle:** un panel que se pliega y despliega, con `aria-expanded`/`aria-controls`. Muestra motivo, origen
y la lista clave–valor de `details`. No muestra IP ni sesión (minimización: son técnicas, y GOV-CTL-003
las conserva en la base).

**Estados:**
- cargando;
- vacío con filtros;
- error de red, con «Reintentar»;
- 403: «No tiene autoridad de auditoría»;
- 422 de rango, que se valida antes en cliente;
- actualizando (`isFetching` con datos).

**Responsive:** la tabla queda en un contenedor con desplazamiento horizontal propio y la página no se
desborda a 320 px.

### AD-9 · Reportes › Auditoría

La columna Fecha usa `formatearFecha` (Caracas). Se corrige la omisión de 03, y la guarda temporal no
cambia.

### AD-10 · Pantalla de documento

`uploadErrorMessage` cubre los dos códigos:
- `FILE_INFECTED`: «El archivo fue rechazado por seguridad: el análisis lo identificó como malicioso. No
  se guardó.»
- `SCAN_FAILED`, según `details.category`:
  - `SCANNER_UNAVAILABLE`: «El servicio de análisis no está disponible. El archivo no se guardó; inténtelo
    más tarde.»
  - `SCAN_TIMEOUT`: «El análisis tardó demasiado. El archivo no se guardó; inténtelo de nuevo.»
  - otra categoría: «No se pudo verificar la seguridad del archivo. Inténtelo de nuevo más tarde.»

El estado «Verificando el archivo…» (`role="status"`) cubre UPLOADING y SCANNING: es una sola petición
síncrona y el cliente no puede distinguirlos. CANCELLED y RETRYING automático no existen (el reintento lo
hace la persona). Se registran como NOT_APPLICABLE con ese motivo.

### AD-11 · Guarda del catálogo (antes de ejecutar)

`tests/test_audit_catalog_guard.py`, un análisis AST de `app/`:
- (a) todo par literal de `record_audit` y de sus envoltorios está en el catálogo y no es `LEGACY`;
- (b) `AuditEvent(` solo se construye en `app/shared/audit.py`;
- (c) toda entrada `ACTIVE` con `emission=STATIC` tiene su literal en `app/`; las `DYNAMIC`, su sitio
  generador declarado; las `MIGRATION`, su revisión; las `RESERVED`, su justificación
  (CATALOGUED_NEVER_EMITTED_UNEXPLAINED = 0);
- (d) ninguna entrada se borra mientras haya historia: las acciones `LEGACY` siguen en el catálogo.

### AD-12 · Pruebas sonda (H9)

`audit_world.py`, `test_audit_tenant_isolation.py`, `test_company_scope_surfaces.py` y `test_reporting.py`
pasan a usar pares catalogados con claves permitidas, sin cambiar lo que prueban.

Las construcciones directas de `AuditEvent(` en pruebas se mantienen: simulan historia, que es lo que
quieren probar.

`qa/repro-audit-*.py` son guiones de reproducción de ciclos cerrados y no forman parte de ninguna suite.
Se marcan como históricos en la evidencia y no se tocan.

## 6. Modelo de amenazas (encargo §52)

| # | Amenaza | Control | Requisito | Prueba (R = rojo previo) |
|---|---|---|---|---|
| A1 | Evento no catalogado o acción inventada | AD-2 (1) y AD-11 (a) | FR-001-257/258 | catálogo: desconocido rechazado (R1); guarda AST |
| A2 | Evento de empresa sin empresa | AD-2 (3) y AD-4 | FR-001-259/263 | `COMPANY` sin empresa rechazado; documentos/UoM con empresa (R2) |
| A3 | Evento de tenant rotulado como de empresa | AD-2 (3) y AD-7 `scope` | FR-001-259/265 | `TENANT` con empresa rechazado; la API rotula `scope` |
| A4 | Un auditor de empresa ve eventos de tenant | Filtro vigente (OD-AUD-01) y `scope=TENANT` | FR-001-264 | API y E2E con auditor de D1 (R3) |
| A5 | Lectura cruzada entre empresas o tenants | Alcance de tenant y empresa existente; `company_id` solo estrecha | FR-001-264 | D1 no ve D2; `company_id` ajeno da vacío; otro tenant da vacío |
| A6 | `UPDATE` o `DELETE` de auditoría | Triggers (AD-5) | FR-001-262 | PG y SQLite: `UPDATE`/`DELETE` rechazados (R5); `TRUNCATE` en PG |
| A7 | Secreto, token, OTP, código de recuperación, bytes, ruta o contenido en el detalle | AD-2 (4) | FR-001-260 | Negativas por clase de dato (R6) |
| A8 | El rechazo se pierde con el rollback | AD-6 | FR-046-073 | Persistencia tras el rollback (R4) |
| A9 | Un fallo de infraestructura clasificado como malware | Tabla de categorías (AD-6) | FR-046-073/089 | Categoría por resultado; mensaje de UI |
| A10 | Firma de la amenaza filtrada | Sin `signature` en el evento ni en la respuesta; nombre prohibido | OD-AUD-09 | Evento y 422 sin firma |
| A11 | Historia reescrita | Triggers; sin backfill | OD-AUD-05/06 | Fila histórica intacta tras la operación |
| A12 | Acción del catálogo eliminada que deja la historia sin interpretar | AD-11 (d): ciclo de vida `LEGACY` | §46 | Las acciones `LEGACY` siguen catalogadas y la API las rotula |
| A13 | Acceso directo a la API | El backend decide (`require_permission` y alcance) | RNF-GOV-006 | Pruebas de API sin UI |
| A14 | Listado sin límite | `page_size` ≤100; filtros por igualdad e índice | §49/81 | `page_size=101` da 422 |
| A15 | Correlación ausente | AD-3 | FR-001-261 | `request_id` del evento == `X-Request-ID` de la respuesta |

## 7. Gate de la Constitución (antes de implementar)

| Condición | Estado |
|---|---|
| Inventario de emisión | Estático completo; el de ejecución completa el detalle de §8 |
| Modelo de catálogo | AD-1/AD-2 |
| Clasificación de ámbito | §8 (catálogo) |
| Política de eventos de tenant | OD-AUD-01 |
| Contexto de empresa | OD-AUD-02/AD-4 |
| Contrato del rechazo | OD-AUD-07/08/09 y AD-6 |
| Inmutabilidad | Medida (H7) y AD-5 |
| Pantallas | §9 |
| Pruebas diseñadas | §6 y §10 |
| Trazabilidad | §3 → §6 → §10 |
| MATERIAL_OQ en el alcance | **0** |
| BLOCKER, CRITICAL, CONTRADICTIONS y OWNER CONFLICT | **0** |

Una sola cuestión sigue abierta y fuera del alcance: AUDITORIA-PANTALLA-DUPLICADA, que la dueña decide.
No bloquea porque la línea de tiempo no cambia de contrato.

**Gate: PASS.**

## 8. Tareas (clasificación tarea por tarea)

**Valores comunes a todas las tareas:**
- `EXECUTOR` es DeepSeek (regla suprema: DeepSeek escribe todo el código y las pruebas). Claude diseña,
  audita, aplica tal cual y certifica.
- `RETRY_MAX: 2`.
- `EGRESS_SAFE`: sí en todas. Ningún encargo lleva secretos, rutas personales, datos reales ni el contenido
  de EICAR (se nombra `EICAR_TEST_FIXTURE`).

Las tareas que tocan la autoridad, la inmutabilidad o la migración son CLAUDE_ONLY **en su diseño**, que
queda fijado en AD-1..AD-12 y en el catálogo de §8.1. La codificación es mecánica sobre ese diseño.

| Tarea | Contenido | MODEL | SECURITY_SENSITIVE | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|
| C04-T01 | Núcleo del catálogo: tipos, validación, proyección segura y búsqueda | pro | sí | `app/shared/audit_catalog.py`, `tests/test_audit_catalog.py` | ídem | Unitarias en verde, rojo de R1 medido en T03 |
| C04-T02a/b | Entradas del catálogo (transcripción de §8.1, en dos mitades) | pro | sí | `app/shared/audit_catalog_entries.py` | T01 + T09 | Comparación automática contra §8.1 = 0 diferencias |
| C04-T03 | Integración en `record_audit`, `ContextVar` de correlación, middleware y `record_audit_after_rollback` | pro | sí | `app/shared/audit.py`, `app/core/logging.py`, `app/core/middleware.py`, `tests/test_audit_record_contract.py` | ídem | R1/R6 en rojo antes y en verde después |
| C04-T04 | Contexto de empresa y tenant (AD-4) | pro | sí | `documents/api.py`, `documents/service.py`, `master_data/uom_api.py`, `identity_access/service.py`, `tests/test_audit_company_context.py` | ídem | R2 en rojo antes y en verde después |
| C04-T05 | Adaptación de las pruebas sonda (AD-12) | flash | no | 4 ficheros de `tests/` | Esos mismos | Pasan las pruebas, que siguen probando lo mismo |
| C04-T06 | Inmutabilidad: DDL del modelo, migración 0061 e índice | pro | sí | `audit/models.py`, `alembic/versions/0061_…py`, `tests/test_audit_immutability.py` | ídem + migraciones | R5 en rojo antes y en verde después en PG y SQLite; `upgrade`/`downgrade` |
| C04-T07 | Versión del motor y rechazo del análisis que persiste | pro | sí | `documents/scanning.py`, `documents/service.py`, `tests/test_document_scan_rejection_audit.py` | ídem + documentos | R4 en rojo antes y en verde después; sin firma |
| C04-T08 | API: filtros, proyección y `/audit/filters` | pro | sí | `audit/api.py`, `tests/test_audit_events_filters.py` | ídem + auditoría | Filtros, 422 y alcance |
| C04-T09 | Guarda AST del catálogo | pro | sí | `tests/test_audit_catalog_guard.py` | ídem | (a)–(d) en verde |
| C04-T10 | Frontend: tipos, `api/audit.ts` y `AuditoriaPage` | pro | no | `src/api/types.ts`, `src/api/audit.ts`, `src/pages/AuditoriaPage.tsx` + pruebas | vitest | Filtros, columnas, detalle y estados |
| C04-T11 | Fecha de Reportes › Auditoría y mensajes de rechazo | flash | no | `ReportesAuditoriaPage.tsx`, `documentos/types.ts` + pruebas | vitest | Caracas; tres mensajes |
| C04-T12 | AUDIT-E2E y SCAN-REJECTION-E2E | pro | no | `e2e/audit-catalog.spec.ts` | Playwright × 3 | En verde en 3 navegadores |
| C04-T13 | Contratos de API de 001 y 046 | flash | no | `specs/…/contracts/api-contracts.md` | — | Documentado |

### 8.1 Catálogo (diseño)

El catálogo completo está en `evidence/audit-catalog/catalogo.md`:
- **231 entradas**: 195 `COMPANY` y 36 `TENANT`;
- por emisión: 163 `STATIC`, 65 `DYNAMIC`, 1 `MIGRATION` y 2 `RESERVED`;
- por ciclo de vida: 229 `ACTIVE` y 2 `LEGACY` (`DOCUMENT_TYPE_*`/`Document`).

Cómo se construyó:
- unión del inventario estático (164 pares literales), de las familias dinámicas enumeradas desde el código (estados y decisiones: aprobaciones, cotizaciones, picking, confirmaciones, devoluciones, reembolsos, reservas, tareas, UoM, ubicaciones y niveles de almacén) y del perfil de ejecución de la suite (129 pares);
- las claves de detalle se resolvieron también desde las cargas dinámicas (bloqueos de borrado, jerarquías, política de aprobación y reservas).

Transcripción a `app/shared/audit_catalog_entries.py`, verificada por comparación automática: **231 = 231, 0 diferencias**.

## 9. Pantallas (AUDIT_SCREEN_MATRIX)

| SCREEN_ID | Pantalla | Proceso | Actores | Datos | Filtros | Estados | Permisos y ámbito | Corrección | Prueba |
|---|---|---|---|---|---|---|---|---|---|
| AS-01 | Auditoría (`/auditoria`) | Muestreo y consulta de solo lectura (GOV-CTL-005) | Auditor de todo el tenant; auditor de empresas | Fecha en Caracas, acción legible y código, entidad e id, usuario, ámbito, correlación, detalle seguro | Desde, Hasta, Acción, Entidad, Usuario, Ámbito/Empresa, Correlación | Cargando, vacío, error con reintento, 403, rango inválido, actualizando | `audit:view` por empresa; eventos de tenant solo con autoridad de todo el tenant (OD-AUD-01) | AD-8; fin de `q` | FIL-01..10, AUDIT-E2E-01..05 |
| AS-02 | Reportes › Auditoría | Línea de tiempo por empresa (FR-009-022) | Auditor de la empresa activa | Fecha (Caracas) y lo demás sin cambio | Entidad, Acción | Cargando, vacío, error | `audit:view` en la empresa del contexto | AD-9 | ReportesAuditoriaPage.test |
| AS-03 | Documento (detalle y carga) | Carga con análisis | Quien tiene `documentos:upload` | Estado de la carga y mensaje seguro | — | Verificando (carga y análisis), aceptado, rechazado por seguridad, servicio no disponible, tiempo agotado, fallo | `documentos:upload` en la empresa | AD-10 | documentos.test, SCAN-E2E-01 |

**Huecos (encargo §84):**

| Hueco | Estado |
|---|---|
| MISSING_DATE_FILTER | FIXED |
| MISSING_FILTERS (actor, empresa, ámbito, correlación) | FIXED |
| MISSING_SCOPE_CONTEXT | FIXED (columna Ámbito) |
| MISSING_AUDIT_INFORMATION (detalle) | FIXED: cierra AUDIT-DETAIL-NO-IMPLEMENTADO |
| IP y sesión en pantalla | EXPLICITLY_OUT_OF_SCOPE_WITH_RATIONALE: minimización; se conservan en la base para GOV-CTL-003 |
| Rol y unidad del actor | DEPENDENCY (Gobierno, GOV-CTL-003) |
| Paquete exportable | FUTURE_SPEC (GOV-DOC-010) |
| Pantalla duplicada | AUDITORIA-PANTALLA-DUPLICADA: decisión de la dueña pendiente |
| Estados CANCELLED y RETRYING de la carga | NOT_APPLICABLE: carga síncrona y sin reintento automático |
| OFFLINE | Cubierto por el estado de error de red con «Reintentar» |

## 10. Inventario de suites obligatorias (RS)

| RS | Suite |
|---|---|
| RS-01 | Conciliación del repositorio |
| RS-02 | Corrección de gobierno PDD-TIME-11 |
| RS-03 | Conciliación de la deuda de período |
| RS-04 | Lectura del PDF de Gobierno (diseño y cierre) |
| RS-05 | Inventario de emisión (estático y de ejecución) |
| RS-06 | Perfil de datos de QA (siembra y tras la E2E) |
| RS-07 | Arqueología del analizador |
| RS-08 | Pruebas dirigidas en PostgreSQL |
| RS-09 | Pruebas dirigidas en SQLite |
| RS-10 | Catálogo (CAT, REC, guarda) |
| RS-11 | Inmutabilidad (IMM-01..07) |
| RS-12 | Rechazo del análisis (SCAN-01..05) |
| RS-13 | Frontend dirigido |
| RS-14 | PostgreSQL completo con analizador |
| RS-15 | SQLite completo con analizador |
| RS-16 | vitest completo |
| RS-17 | tsc |
| RS-18 | eslint |
| RS-19 | build |
| RS-20 | ruff |
| RS-21 | mypy (≤154, 0 nuevos) |
| RS-22 | Alembic, cabeza 0061 |
| RS-23 | OpenAPI (420 → 421, deriva explicada) |
| RS-24 | AUDIT-E2E en 3 navegadores |
| RS-25 | SCAN-E2E en 3 navegadores |
| RS-26 | Regresiones E2E (auditoría, documentos, lectura, alcance, delegación, UI con empresa, descargas, fecha de negocio, MFA, reset) |
| RS-27 | E2E canónica |
| RS-28 | Mutaciones de 04 |
| RS-29 | Base tras la E2E |
| RS-30 | Accesibilidad |
| RS-31 | Responsive |
| RS-32 | Puerta de pantallas y formularios |
| RS-33 | Barrido de secretos |
| RS-34 | Residuos |

## 11. Ejecución (C04-T01..T13, con reclasificaciones)

El detalle por tarea, con reintentos, rechazos y causas, está en `evidence/audit-catalog/orchestration.md`.

**Rojo atribuible**, medido antes de cada corrección (`evidence/audit-catalog/rojo.md`):

| Rojo | Prueba | Qué falló |
|---|---|---|
| R1 y R6 | REC-01..04 | `record_audit` aceptaba un par inventado, claves libres, `token` y `password` |
| Ámbito | REC-02/03 | Ídem para empresa ausente y tenant con empresa |
| Correlación | REC-07 | Sin `request_id` automático |
| R2 | CTX-01..06 | Con el catálogo ya activo, documentos y UoM fallaban cerrados (`AUDIT_ACTION_LEGACY`, `AUDIT_COMPANY_REQUIRED`) |
| R4 | SCAN-01..05 | 25 fallos: el camino antiguo emitía `after.signature` y perdía el evento con el rollback |
| R5 | IMM-01..06 | `UPDATE`, `DELETE` y `TRUNCATE` aceptados (SQLite: 4 fallos; PG: 5) |
| Lectura | AF-01..11 | 10 fallos: ruta y parámetros inexistentes |
| UI | FIL, CR y documentos | 3 fallos: fecha ISO cruda y mensajes de rechazo |

**R3** (auditor de empresa frente a evento de tenant) era **verde de control**: el filtro vigente ya cumplía OD-AUD-01, y lo fijan AF-05, AUD-TENANT-09 y AUDIT-E2E-02.

## 12. Resultados

| Suite | Resultado |
|---|---|
| Catálogo, registro, inmutabilidad, contexto, rechazo, filtros y guarda (dirigidas) | Verde en SQLite y PG |
| SQLite completo con analizador | **2603/0** (1100 omitidas) · salto de reloj NO · `r20261028t132643p1474949nd2f381` |
| PostgreSQL completo con analizador | **3685/0** (18 omitidas = línea base) · salto de reloj NO · anomalía NORMAL · `r20261028t134043p1594920nd4039e` |
| vitest | **683/683** (60 ficheros) |
| tsc / eslint | 0 / 0 |
| ruff | limpio |
| mypy | **154 = 154** (0 nuevos) |
| Alembic | cabeza `0061_spec001_audit_immutability` |
| OpenAPI | 420 → **421** rutas: `+/audit/filters` y `GET /audit/events` con parámetros nuevos; 0 esquemas cambiados; deriva sin explicar 0 |
| Mutaciones 04 | **24/24 muertas** · 0 equivalentes · 0 supervivientes (`evidence/audit-catalog/mutaciones.md`) |
| AUDIT-E2E y SCAN-E2E (3 navegadores) | **51/51**, junto con documentos y auditoría de fecha y de sobre (`r20261028t123632p…`, `r20261028t123839p1043456n05bc89`) |
| Canónica con analizador | **376/376** (370 + 6 nuevas) · `r20261028t145823p41475n6cb783` (ver §12.1) |

### 12.1 Corridas E2E

| Corrida | Resultado |
|---|---|
| Canónica 1 (`r20261028t145129p13021nf7ce51`) | 371 pasan · 1 falla · 4 no corren |
| Canónica 2 (`r20261028t145823p41475n6cb783`) | **376/376** |
| Regresiones en Firefox y WebKit | **171/171** (57 × 3; Chromium lo cubre la canónica) · `r20261028t150928p86119n1547d9` |
| Base tras la E2E | **PASS** (`evidence/audit-catalog/post-e2e.md`) |

Detalle de la canónica 1:
- la que falla es AUDITORIA-SOBRE ENV-01/02, con «no hay paso TOTP libre para admin_w1»: el arnés MFA no espera, y la prueba fuerza `iniciarSesion(identidad("admin"))` mientras otra prueba del mismo worker, probablemente SCAN-E2E-01 (entra como `USER`), ya usó ese paso de 30 s;
- las 4 que no corren son la cadena de licencias, que depende de que Chromium termine limpio;
- se registra como deuda E2E-TOTP-PASO-COMPARTIDO.

La canónica 2 se repitió UNA vez, sin cambiar código, para separar la colisión de un defecto.

Una canónica anterior la interrumpió un apagado del anfitrión (SIGTERM en la fase «comprobar», limpieza LIMPIA, sin base creada) y no cuenta.

## 13. Gobierno (relectura de cierre)

Fichero `Ingenieria_de_Requerimientos_KONTROL_Gobierno_v1.0.pdf`, sha256 `8f86615f…`, sin cambio. El de bibliografía, `4a980bb9…`, tampoco cambia.

| Requisito | Cobertura en el núcleo compartido |
|---|---|
| GOV-CTL-002 | Bitácora append-only en la base (AD-5) y rechazo auditado y persistente (AD-6) |
| GOV-CTL-003 | Actor, sesión e IP en columnas y correlación automática (AD-3). Rol y unidad: DEPENDENCY (Gobierno) |
| GOV-CTL-005 | Muestreo de solo lectura por fecha de Caracas, usuario, acción, entidad, ámbito/empresa y correlación (AD-7/8) |
| GOV-CTL-010 | Los maestros con auditoría quedan catalogados. DT-06, maestros sin auditoría, sigue abierta |
| RNF-GOV-004 | Triggers de `UPDATE`, `DELETE` y `TRUNCATE` |
| RNF-GOV-005 | Contexto obligatorio por entrada y fallo cerrado |
| GOV-DOC-010 | FUTURE_SPEC; el catálogo es su prerrequisito |

Contadores:
- ENGINEERING_REQUIREMENTS_RECONCILED = 1;
- APPLICABLE_REQUIREMENTS_COVERAGE = 100 %;
- UNEXPLAINED_REQUIREMENT_OMISSIONS = 0.

Gobierno no se implementa: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0.

## 14. Seguridad, normativa y residuos

**Seguridad.**
- Amenazas A1–A15 con control, requisito y prueba (§6), y 24 mutantes muertos.
- 0 secretos, 0 EICAR, 0 rutas personales y 0 contraseñas en el diff.
- La muestra de la E2E se lee en ejecución de `qa/clamav_qa.EICAR`.

**Normativa.** NORMATIVE_RESEARCH = **NOT_APPLICABLE**.
- Ninguna regla implementada depende de una norma venezolana de conservación, destrucción o privacidad.
- No se implementa retención ni borrado (`PRESERVE_UNTIL_RETENTION_POLICY_RATIFIED`).
- Un plazo de conservación futuro será LEGAL_VALIDATION_REQUIRED.

**Residuos.** CLEAN:
- bases de corrida: 0;
- puertos 8000/5173 libres;
- sin `.bak` ni sondas;
- la sonda temporal de depuración (`zz_sonda.test.tsx`) se borró en el acto.

**Reinicio del anfitrión** (15:46): se reprovisionó PostgreSQL de QA (`start` + `mkdb ktest`) y los guiones del scratchpad se rehicieron; el árbol no se vio afectado.

## 15. Deuda (al cerrar)

**Cerradas por este ciclo**, porque el ciclo dependía de ellas o las pedía el encargo:
- DOCUMENT-SCAN-REJECTION-AUDIT-NOT-PERSISTED;
- AUDIT-DETAIL-NO-IMPLEMENTADO;
- AUDIT-DATE-FILTER-MISSING;
- UI-BUSQUEDA-MUERTA en Auditoría (Existencias sigue abierta);
- AUDIT-ORDEN-SIN-DESEMPATE;
- AUDIT-PAGINA-SIN-INDICE-DE-ORDEN;
- DT-06 en la parte catalogada;
- REPORT-PERIOD-NOT-APPLIED (§1).

**Siguen abiertas:**

| Deuda | Severidad | Estado |
|---|---|---|
| DT-06 | MEDIUM | Maestros y organización sin auditoría (empresas, artículos, categorías documentales); GOV-CTL-010 |
| AUDITORIA-PANTALLA-DUPLICADA | — | Decisión de la dueña |
| AUDIT-OPENAPI-SIN-RESPONSE-MODEL | LOW | Abierta |
| FISCAL-BOOK-PERIOD-RULE | HIGH | Legal |
| Resto de §13 del encargo 03 | — | Sin cambio |

**Nuevas:**

| Deuda | Severidad | Qué es |
|---|---|---|
| DOCUMENT-UPLOAD-VALIDATION-REJECTION-NOT-AUDITED | MEDIUM | Las cargas rechazadas por MIME, suplantación o tamaño no se auditan; GOV-CTL-002 habla de «rechazos» |
| E2E-TOTP-PASO-COMPARTIDO | LOW | §12.1 |
| E2E-PAGINACION-RELLENO-INEFICAZ | LOW | El «relleno» de PAG-E2E crea eventos de tenant que `admin` (solo D1) no ve; pasa por los eventos de D1 de otras specs |
| AUDIT-TIMELINE-TOTAL-LIMITADO | LOW | `/reporting/audit/timeline` devuelve `total = len(items)` con tope de 200 |
| AUDIT-DYNAMIC-VALUES-NOT-STATIC | LOW | La guarda no puede verificar los valores de las familias f-string; el fallo cerrado en ejecución las cubre, y lo demostró en PG con SALES_RETURN |
| AUDIT-ROLE-UNIT-CONTEXT | DEPENDENCY Gobierno | Rol y unidad del actor, GOV-CTL-003 |
| AUDIT-RETENTION-POLICY | LEGAL_VALIDATION_REQUIRED | Plazo de conservación |
| QA-REPRO-AUDIT-PROBES | LOW | `qa/repro-audit-*.py`, de ciclos cerrados, usan acciones sonda que el catálogo cerrado ya rechaza |
| REPORT-PERIOD-INPUT-ON-SNAPSHOT-REPORTS | LOW | §1 |

## 16. Convergencia (equivalente explícito)

Contrastadas contra el código y las pruebas:
- FR-001-257..267, FR-009-022 (parcial), FR-046-073 y FR-046-089;
- AD-1..AD-12;
- OD-AUD-01..09.

| Requisito | Prueba y evidencia |
|---|---|
| FR-001-257/258 | CAT-01..14, REC-01, GUARD-A..D y A01–A03 |
| FR-001-259 | CAT-04..06, REC-02/03 y A04/A05 |
| FR-001-260 | CAT-07..10, REC-04, A06/A07 y la base tras la E2E |
| FR-001-261 | REC-07/08, SCAN-01 (`request_id == X-Request-ID`) y A08 |
| FR-001-262 | IMM-01..07 y A12–A15 |
| FR-001-263 | CTX-01..06 y A21 |
| FR-001-264..266 | AF-01..11, AUD-TENANT-11 y A16–A20/A22 |
| FR-001-267 | FIL-01..10, ENV, PAG, DATE, AUDIT-E2E-01..05 y F02 |
| FR-009-022 | ReportesAuditoriaPage.test |
| FR-046-073 | SCAN-01..05, SCAN-E2E-01, A09–A11 y la base tras la E2E |
| FR-046-089 | documentos.test, F01 y SCAN-E2E-01 |

Sin tareas huérfanas ni huecos sin explicar. **CONVERGED.**
