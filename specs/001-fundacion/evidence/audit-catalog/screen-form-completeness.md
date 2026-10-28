# AUDIT CATALOG (04) · puerta de pantallas y formularios (2026-10-28)

## Puerta por pantalla (§41)

| Campo | AS-01 Auditoría `/auditoria` | AS-02 Reportes › Auditoría | AS-03 Documento: carga y estado |
|---|---|---|---|
| PROCESS_ID | Muestreo y consulta de la bitácora (GOV-CTL-005) | Línea de tiempo por empresa (FR-009-022) | Carga con análisis (Spec 046) |
| BUSINESS_PURPOSE | Reconstruir quién hizo qué, cuándo, dónde y con qué correlación | Ver la actividad de la empresa activa | Guardar un archivo solo si está limpio |
| PRIMARY_USER_GOAL | Encontrar y entender un evento | Revisar la actividad reciente | Saber si el archivo quedó guardado y por qué no |
| ACTORS | Auditor de todo el tenant; auditor de empresas | Auditor de la empresa | Usuario con `documentos:upload` |
| ROLE_ACTION_MATRIX | `audit:view`: leer y filtrar. Nadie escribe | `audit:view` en la empresa | `documentos:upload`: cargar |
| ENTRY / PRE | Sesión con `audit:view` | Empresa activa con `audit:view` | Documento existente; tipo con análisis |
| POST | Ninguna (solo lectura) | Ninguna | Versión nueva (CLEAN) o evento `DOCUMENT_SCAN_REJECTED` |
| FIELDS | Desde, Hasta, Acción, Entidad, Usuario, Ámbito/Empresa, Correlación | Entidad, Acción | Archivo, motivo de reemplazo |
| ACTIONS | Aplicar filtros, Limpiar, Ver detalle, Cerrar detalle, Reintentar, paginar | Filtrar | Cargar |
| STATES | Normal, cargando, vacío, error con reintento, 403, rango inválido (cliente y 422), actualizando. OFFLINE = error de red. PROCESS_BLOCKED: N/A | Normal, cargando, vacío, error | Verificando (carga y análisis), aceptado, rechazado por seguridad, servicio no disponible, tiempo agotado, fallo. CANCELLED y RETRYING: N/A (síncrono, sin reintento automático) |
| VALIDATIONS | Desde ≤ Hasta (cliente y servidor); `page_size` ≤ 100 | — | Tipo, MIME, tamaño y análisis (backend) |
| PERMISSIONS / BACKEND_AUTHORIZATION | `require_permission("audit","view")` y alcance por empresa | Contexto de empresa y `audit:view` | `require_permission("documentos","upload")` y contexto |
| COMPANY_SCOPE | Solo empresas con `audit:view`; `company_id` solo estrecha | La empresa del contexto | La empresa del documento |
| TENANT_SCOPE | Eventos sin empresa solo con autoridad de todo el tenant (OD-AUD-01) | — | — |
| AUDIT_EFFECT | Ninguno (lectura) | Ninguno | `DOCUMENT_FILE_UPLOADED` o `DOCUMENT_SCAN_REJECTED` (persistente) |
| DB_API_UI_PARITY | Columna → item (`action_label`, `scope`, `company_name`, `username`, `details`) | `event_time` → `formatearFecha` | `details.category` → mensaje |
| ERROR_HANDLING | Mensajes de 403, 422 y red con «Reintentar» | Mensaje de error | Tres mensajes seguros; nunca la firma |
| SECURITY | Sin IP, sesión ni `before`/`after`/`evidence` crudos | Sin cambios | Sin firma, nombre original, ruta ni contenido |
| CONCURRENCY | Lectura con orden estable (`event_time`, `id`) | — | Rechazo confirmado aparte (OD-AUD-07) |
| RESPONSIVE | 320 px sin desbordamiento (AUDIT-E2E-05) | Tabla con desplazamiento propio | Cubierto por documents-a11y (320–1440) |
| ACCESSIBILITY | Etiquetas visibles, `aria-expanded`/`aria-controls`, foco al título y de vuelta, un solo `role="alert"`, axe sin violaciones serias ni críticas | — | Alerta asociada (`role="alert"`) y estado (`role="status"`) |
| E2E | AUDIT-E2E-01..05 (×3) | Canónica | SCAN-E2E-01 (×3) y documents.spec |
| STATUS | **PASS** | **PASS** | **PASS** |

## Contratos de campo (§42)

| Campo | Etiqueta | Significado | Tipo | Requerido | Origen | Por defecto | Formato | Validación | Backend | API | Ayuda |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F-01 `desde` | Desde | Primer día de negocio (Caracas) incluido | BUSINESS_DATE | No | Usuario | — | AAAA-MM-DD (`type=date`) | ≤ Hasta | `limites_del_dia_utc(desde)[0]` | query `desde` | «Día de Caracas, incluido» |
| F-02 `hasta` | Hasta | Último día de negocio incluido | BUSINESS_DATE | No | Usuario | — | AAAA-MM-DD | ≥ Desde | `< limites_del_dia_utc(hasta)[1]` | query `hasta` | ídem |
| F-03 `action` | Acción | Par del catálogo | Código + entidad | No | `/audit/filters` | «Todas» | `code\|entity` → `action` + `entity_type` | Valor del catálogo | igualdad | query | — |
| F-04 `entity_type` | Entidad | Tipo de entidad | Texto exacto | No | Usuario | — | — | — | igualdad | query | «Tipo exacto, p. ej. Document» |
| F-05 `username` | Usuario | Actor | Texto exacto | No | Usuario | — | — | — | subconsulta en el tenant | query | «Nombre de usuario exacto» |
| F-06 `scope`/`company_id` | Ámbito | Tenant o empresa auditable | Selección | No | `/audit/filters` | «Todas las que audito» | `TENANT` o `company:<id>` | Solo opciones permitidas | estrecha | query | — |
| F-07 `request_id` | Correlación | Petición de origen | Texto | No | Usuario | — | hex | — | igualdad | query | «Identificador de la petición (request ID)» |
| F-08 mensaje de carga | (alerta) | Resultado seguro del análisis | Texto | — | `code` + `details.category` | — | Tres textos | — | `clasificar_rechazo` | 422 `details` | — |

Lo que no se muestra en pantalla, por diseño:
- **IP y sesión**: minimización; se conservan en la base para GOV-CTL-003.
- **`entity_id`**: hay columna y está en el detalle; no se filtra por pantalla porque ningún requisito lo pide, aunque la API lo admite.

## Huecos

Ver §9 del delta. **UNEXPLAINED_UI_FUNCTIONAL_GAPS = 0 · SCREEN_FORM_COMPLETENESS_GATE = PASS · DB_API_UI_CONTRACT_PARITY = PASS.**
