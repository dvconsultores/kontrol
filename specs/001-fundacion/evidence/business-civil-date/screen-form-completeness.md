# BUSINESS CIVIL DATE (03) · Screen / Form completeness (2026-10-28)

## TEMPORAL_SCREEN_MATRIX

| SCREEN_ID | Pantalla | Módulo | Campos temporales | Clase | Por defecto | Presentación | Entrada | Validación | Filtro | Efecto en reportes | FIX | Prueba |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TS-01 | Auditoría | 001 | `event_time` | INSTANT | — | Caracas es-VE (`formatearFecha`) | — | — | Sin filtro de fecha (no existe; FUTURE_SPEC) | — | Sí | AuditoriaPage.fecha (DATE-03 en Caracas bajo 3 zonas), BD-E2E-01, auditoria-fecha.spec |
| TS-02 | Notificaciones: alertas, tareas, detalle y centro | 001 | `created_at`, `resolved_at`, `due_at`, `occurred_at` | INSTANT | — | Caracas (`formatearFecha`) | — | — | — | — | Sí (vía i18n) | guarda + F10 |
| TS-03 | Aprobaciones: bandeja, políticas y delegaciones | 045 | `due_at`, `valid_from`, `valid_to` | INSTANT | — | Caracas | `valid_to` («Hasta», `date`) | Opcional | — | — | Sí | BD-E2E-02, guarda, F12 |
| TS-04 | Homologación: línea de tiempo y versiones | 010 | `created_at`, `released_at` | INSTANT | — | Caracas | — | — | — | — | Sí | guarda |
| TS-05 | Licenciamiento: renovación, eventos, derechos, configuración y Mi licencia | 001 | `created_at`, `taken_at`, `ran_at`, `period_start`, `period_end`, `read_only_start` | INSTANT / límite de PERIOD | — | Caracas | — | — | — | — | Sí | guarda |
| TS-06 | Inventario: movimientos, kardex y reservas | 005/031 | `occurred_at`, `expires_at` | INSTANT | — | Caracas | — | — | — | — | Sí | guarda, F11 |
| TS-07 | Seguridad: MFA y sesiones | 002 | `activated_at`, `expires_at` | INSTANT / DURATION | — | Caracas | — | — | — | — | Sí | guarda |
| TS-08 | Ventas: órdenes, despacho, devoluciones, preparación, confirmación y estado de cuenta | 029–037 | `expires_at`, `dispatched_at`, `reentered_at`, `released_at`, `updated_at`, `checked_at`, `date` | INSTANT / BUSINESS_DATE | — | Caracas; el estado de cuenta, la fecha de negocio del backend | — | — | — | El estado de cuenta ordena por día y por instante | Sí | test_business_civil_date_statement, guarda, B12/B19 |
| TS-09 | Compras: recepciones | 019 | `arrival_at`, `inspected_at`, `record_issued_at`, `unloading_scheduled_at` | INSTANT | — | Caracas | `datetime-local` | Opcional | — | — | Sí | guarda, F13 (patrón) |
| TS-10 | Tesorería: tasas, fuentes y reembolsos | 013/038/048 | `effective_at`, `last_success_at`, `created_at`, `requested_at` | INSTANT | `effective_at` = hora actual de Caracas | Caracas | `datetime-local` | Obligatoria | Consulta por instante | — | Sí | BD-E2E-03, test_business_civil_date_rates, F13 |
| TS-11 | Maestros: presentaciones | 011 | `valid_from`, `valid_to` | INSTANT (vigencia) | — | Día de Caracas | — | — | — | — | Sí | guarda, F14 (patrón) |
| TS-12 | Documentos: detalle | 046 | `created_at` de versión; `issued_at`/`expiration_date` (Date) | INSTANT / BUSINESS_DATE | — | Día de Caracas / texto | — | — | — | Vencido derivado en Caracas (B3) | Sí | test_business_civil_date_documents, B11 |
| TS-13 | Reportes: Centro y Exportaciones | 009 | `period`, `exported_at` | PERIOD / INSTANT | «» = todos | Caracas | Texto «AAAA-MM» | 422 `INVALID_PERIOD`; error accesible | Mes de Caracas, semiabierto | `executive_ventas` filtra; los libros declaran que no | Sí | CR-08/09/10, BD-E2E-04/05, reports, B04/B05/B18, F07/F08 |
| TS-14 | Fiscal: libros | 007 | `period` | PERIOD | «» | — | Texto | No filtra (bloqueo normativo) | — | `period_applied: false` | Sí | LIB-01/02, B17, F09 |
| TS-15 | Inputs `date` ya correctos: biblioteca, cotizaciones, CxP, regulatorio, lotes, fuentes, cambio, línea de recepción | varios | BUSINESS_DATE | BUSINESS_DATE | «» | Texto «AAAA-MM-DD» | `date` tal cual | — | — | — | No (ya correctos) | guarda (sin `Date`) |

**SCREENS_REVIEWED_COUNT = 15 grupos (≈ 40 pantallas) · FORMS_REVIEWED_COUNT = 5** (Delegaciones, Tasas, Recepciones, Centro y Libros).

## Field contract · campos tocados

| FIELD_ID | LABEL | Significado | Clase | DB | API | OpenAPI | TS | Zona | Origen | Por defecto | Formato | Validación | Futuro | Pasado | Visibilidad / edición | Backend | Error | Ayuda | Auditoría | Reporte | Prueba |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FC-01 `delegation.valid_to` | «Hasta» | Último día de vigencia (incluido) | INSTANT (fin del día D en Caracas) | timestamptz | ISO Z | date-time | string | Caracas → UTC | Usuario | — (sin límite) | `date` → 23:59:59.999 de Caracas | Opcional | Sí | Sí (lo rechaza el backend) | `aprobaciones:delegate` | `_as_utc(valid_to) < now` → expirada | Del backend | «Incluido: vence al final de ese día, hora de Caracas» | Evento de delegación sin cambio | — | BD-E2E-02, F12 |
| FC-02 `exchange_rate.effective_at` | «Vigente desde» | Desde cuándo rige la tasa | INSTANT | timestamptz | ISO Z | date-time | string | Caracas → UTC | Usuario | Hora actual de Caracas | `datetime-local` | Obligatoria | Sí (la política decide) | Sí | `tesoreria:create` | `_momento` normaliza a UTC; `rate_date` = día de Caracas | Del backend | «Hora de Caracas» | Sin cambio | Selección de tasa | BD-E2E-03, rates, B06/B07, F13 |
| FC-03 CSV `effective_at` | Columna de importación | Igual que FC-02 | INSTANT | timestamptz | — | — | — | Fecha suelta → 00:00 de Caracas; hora sin zona → Caracas; desfase → tal cual | Fichero | — | ISO | INVALID_ROW si no es ISO | Sí | Sí | `tesoreria:create` | `_fecha` | Por fila | Texto de la sección «Importar» | Lote auditado | — | rates e/f/g, B09/B10 |
| FC-04 `receipt.unloading_scheduled_at` | «Descarga programada» | Cuándo se programa la descarga | INSTANT | timestamptz | ISO Z | date-time | string | Caracas → UTC | Usuario | — | `datetime-local` | Opcional | Sí | Sí | `compras:create` | Sin cambio | Del backend | «Etapa 2 del proceso · hora de Caracas» | Sin cambio | — | guarda |
| FC-05 `report.period` | «Período» | Mes de negocio | PERIOD | — | query «AAAA-MM» | string | string | Caracas | Usuario | «» (todos) | «AAAA-MM» | Mes 01–12; si no, error | — | — | `reportes:view` + origen | `limites_del_periodo_utc`; 422 `INVALID_PERIOD` | «Formato AAAA-MM, mes 01 a 12.» (`aria-invalid` + `aria-describedby`) | «Mes de Caracas, AAAA-MM. Vacío: todos los períodos.» | Exportación auditada con `filters.period` | `executive_ventas` filtrado; `period_applied` | CR-08/09/10, BD-E2E-04/05, reports, B15/B18, F07 |
| FC-06 `fiscal.books.period` | «Período» | Período del libro | PERIOD (no aplicado) | — | query | string | string | — | Usuario | «» | Texto | Ninguna (no filtra) | — | — | `fiscal:view` | `period_applied: false`, `period_rule` | — | «Mes de Caracas, AAAA-MM.» + aviso de bloqueo normativo (`role="status"`) | — | Muestra todos los registros | LIB-01/02, B17, F09 |
| FC-07 `customer_statement.entries[].date` | Fecha (tabla) | Fecha de negocio del movimiento | BUSINESS_DATE | — | «AAAA-MM-DD» | (dict sin esquema) | string | Caracas | Sistema | — | AAAA-MM-DD | — | — | — | `ventas:view` | `hoy_de_negocio(instante)` | — | — | — | Orden por día y por instante | statement, B12/B19 |
| FC-08 instantes en pantalla (todos) | Columnas «Fecha», «vence», etc. | Momento del hecho | DISPLAY de INSTANT | — | — | — | — | Caracas explícito | Sistema | — | es-VE `toLocaleString` / DD/MM/AAAA / AAAA-MM-DD | Inválido → «Invalid Date»; nulo → «—» (DATE-13) | — | — | La de cada pantalla | — | — | — | — | — | fecha-de-negocio.test (4 zonas), guarda, F01–F06, F11, F14, F15 |

## Puerta (§47) y análisis de huecos (§86)

| Hueco | Estado |
|---|---|
| MISSING_TIMEZONE_EXPLANATION | FIXED: los campos de entrada dicen «hora de Caracas» |
| MISSING_VALIDATIONS (período) | FIXED (Centro); Libros: EXPLICITLY_OUT_OF_SCOPE, porque no filtra |
| MISSING_PERIOD_RULES (libros fiscales) | LEGAL_VALIDATION_REQUIRED (OD-TIME-11) |
| MISSING_REPORT_FILTERS (bitácora por día) | FUTURE_SPEC: no existe filtro de fecha en la bitácora y ningún requisito aprobado lo pide; con ADR-020, cuando exista, usará `limites_del_dia_utc` |
| MISSING_DEFAULTS (inputs `date` sin «hoy») | EXPLICITLY_OUT_OF_SCOPE: ningún requisito pide «hoy» por defecto; si se añade, `hoyDeNegocio()` |
| MISSING_ERROR_STATES (INVALID_DATE, INVALID_RANGE, OUT_OF_PERIOD, PERIOD_CLOSED) | Período: FIXED (INVALID_PERIOD). Rangos y período cerrado no existen en estas pantallas → NOT_APPLICABLE |
| MISSING_RESPONSIVE | BD-E2E-05 (320 px, sin desbordamiento) |
| MISSING_ACCESSIBILITY | Error asociado (`aria-invalid`, `aria-describedby`), aviso `role="status"`, axe sin críticos ni graves en `main` (BD-E2E-05) |
| MISSING_E2E | BD-E2E-01..05 en 3 navegadores × 3 zonas |

**Estados del período (§51):** NORMAL, LOADING, ERROR y VALIDATION_ERROR (INVALID_PERIOD), y NORMATIVE_BLOCKED (libros), presentes. EMPTY: «Sin datos para el reporte…».

**SCREEN_FORM_COMPLETENESS_GATE = PASS · UNEXPLAINED_UI_FUNCTIONAL_GAPS = 0 · DB_API_UI_CONTRACT_PARITY = PASS** (la fecha que ve la UI es la que el backend define en Caracas).
