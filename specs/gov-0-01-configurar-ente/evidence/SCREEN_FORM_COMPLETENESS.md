# GOV-0-01 · ficha de pantalla y formulario (2026-10-30)

| Campo | GE-UI-01 Configuración del ente `/gobierno/ente` (ficha) | GE-UI-02 Formulario del ente (alta / edición / modificación) | GE-UI-03 Confirmación de activación |
|---|---|---|---|
| PROCESS_ID | ORG-01 Configurar el ente (GOV-ORG-001) | ORG-01 | ORG-01 |
| BUSINESS_PURPOSE | Ver la identidad, naturaleza y acto de creación del ente, qué falta para activarlo, su documento y su historial | Registrar o corregir los datos del ente | Fijar el ente: desde aquí cada cambio exige motivo |
| PRIMARY_USER_GOAL | Saber en qué estado está el ente y qué le falta | Completar los datos sin errores | Activar con conocimiento del efecto |
| ACTORS | Responsable de configuración institucional; consulta | Responsable (create / edit) | Responsable (activate) |
| ROLE_ACTION_MATRIX | `view`: ver ficha, documento e historial. `edit`: Editar (borrador) / Modificar (activo). `activate`: Activar (borrador). Sin capacidad: el botón no se pinta | `create`: alta. `edit`: edición y modificación | `activate` |
| ENTRY / PRE | Menú Gobierno › Configuración del ente; licencia con `gobierno`; contenedor activo | Desde la ficha o el estado vacío | Borrador sin faltantes |
| POST | — | Ente BORRADOR v1 (alta) o versión + 1 | Ente ACTIVO, versión + 1 |
| FIELDS | F01–F12 en lectura (rótulos de catálogo, fecha DD/MM/AAAA), estado, versión, activado el | F01 Denominación*, F02 Siglas, F03 RIF, F04 Nivel, F05 Forma, F06 Órgano (si forma ≠ central), F07 Entidad (si estadal/municipal), F08 Municipio (si municipal), F09 Tipo de acto, F10 Número, F11 Fecha, F12 Publicación; F14 Motivo* solo en modificación | — |
| ACTIONS | Configurar el ente, Editar, Activar el ente, Modificar; en el panel: Adjuntar, Descargar, Desvincular | Guardar, Cancelar | Activar, Cancelar |
| STATES | Cargando; módulo no habilitado; sin acceso; sin configurar (con o sin botón según `create`); error con reintento; borrador con faltantes (Activar deshabilitado y descrito por la lista); borrador completo; activo; conflicto de versión | Normal; error por campo (local y del servidor); «No hay cambios que guardar»; guardando | Abierto; activando |
| VALIDATIONS | — | Cliente: denominación 3–200, motivo 5–255. Servidor: longitudes, RIF `[JGVEP]-dddddddd-d` normalizado, catálogos cerrados, fecha sin hora y no futura (Caracas), campos desconocidos → 422 | Servidor: completo + documento ACTIVE de la misma empresa |
| PERMISSIONS / BACKEND_AUTHORIZATION | `require_permission("gobierno_ente","view")` → contexto de empresa → `require_module("gobierno")` | `create` / `edit` con el mismo orden; `require_write_allowed` | `activate` |
| COMPANY_SCOPE | El ente del contenedor activo (`company_id` único) | Igual; la empresa la fija el contexto, nunca el cuerpo | Igual |
| TENANT_SCOPE | Otro tenant: 404 `COMPANY_NOT_FOUND` | Igual | Igual |
| DOCUMENTS | Panel 046 «Documento del acto de creación» (`GovernmentEntity`); la carga real pasa por el analizador; un documento de otra empresa no cuenta | — | Exige documento ACTIVE vinculado |
| REPORTS | N/A justificado (Spec §2) | N/A | N/A |
| AUDIT_EFFECT | Ninguno (lectura) | `GOV_ENTITY_CREATED` / `GOV_ENTITY_UPDATED` (antes/después, motivo) | `GOV_ENTITY_ACTIVATED` |
| DB_API_UI_PARITY | `gov_entities` ↔ `EnteOut` ↔ ficha; `gov_entity_versions` ↔ `VersionesOut` ↔ historial | Campo a campo (mismos nombres F01–F12) | `status`/`activated_at` ↔ insignia y «Activado el» |
| ERROR_HANDLING | 403 módulo / acceso, 404, error genérico con reintento | 422 por campo, 422 motivo, 422 incompleto (lista), 422 sin cambios, 409 versión vieja → aviso de conflicto y recarga, 403 | 422 incompleto, 409 estado, 409 versión |
| SECURITY | El frontend solo proyecta; el backend decide | Esquemas `extra="forbid"`; un tipo inválido es 422, nunca 500 | — |
| CONCURRENCY | — | `If-Match` obligatorio (428 sin él), 409 con versión vieja, bloqueo de fila | Igual |
| RESPONSIVE | 320 px sin desbordamiento (GOV-E2E-05) | Rejilla 1 → 2 columnas | Diálogo del sistema |
| ACCESSIBILITY | Un `<h1>`, `<h2>` por sección, regiones con nombre, axe sin violaciones serias a 1280 y 320 | `fieldset`/`legend`, rótulos asociados, `aria-invalid`, errores bajo su campo | Diálogo con título |
| E2E | GOV-E2E-01, -02, -05 (×3 navegadores) | GOV-E2E-01 | GOV-E2E-01 |
| UNIT / COMPONENT | GEP-01..10, GSB-01..03 | GEF-01..07 | GEP-05, -08, -09 |
| STATUS | ver certificación | ver certificación | ver certificación |

Faltantes de la ficha: 0 pantallas, 0 formularios, 0 campos, 0 acciones y 0 estados requeridos sin cubrir.
Deuda de rótulo no bloqueante: la compuerta «Seleccione una empresa» (varios contenedores y ninguno activo) aún dice «empresa» (GOV0-UI-01).
