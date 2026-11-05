# GOV-TRE-02 · TRE02_SCREEN_FORM_MATRIX

| Campo | S1 · Programación financiera | S2 · Nuevo programa | S3 · Programa | S4 · Rubros de caja |
|---|---|---|---|---|
| SCREEN_ID | `ProgramasPage` | `NuevoProgramaPage` | `ProgramaPage` | `RubrosPage` |
| USER_GOAL | ver programas por ejercicio, moneda y estado | abrir el programa de un ejercicio y moneda | declarar, programar, ver la disponibilidad, activar, reprogramar, cerrar y revisar versiones | mantener los rubros |
| MENU_PATH | Gobierno · Tesorería › Programación financiera (`/gobierno/tesoreria/programacion`) | S1 › «Nuevo programa» (`…/nuevo`) | «Abrir el programa PF-…» (`…/:programaId`) | Gobierno · Tesorería › Rubros de caja (`/gobierno/tesoreria/rubros`) |
| ROLE | `gobierno_caja:view`; crear con `:manage` | `:manage` | `:view`; escritura con `:manage`; activar y cerrar con `:activate` (MFA) | `:view`; escritura con `:manage` |
| FIELDS | indicadores por estado; filtros ejercicio, moneda, estado; tabla: código, ejercicio, moneda, estado, versión vigente, disponibilidad inicial | P02 ejercicio, P03 moneda, P04 mes inicial | datos; declaraciones D01–D04; tabla mensual inicial, ingresos, desembolsos, final; líneas L01–L03; versiones; historia | R01 código, R02 nombre, R03 tipo, R04 estado |
| ACTIONS | Nuevo programa, Rubros de caja, abrir, filtrar | Crear programa, Cancelar | Declarar, Quitar, Añadir línea, Cambiar, Quitar, Activar, Reprogramar, Descartar borrador, Cerrar, ver versión | Registrar, Editar, Guardar, Cancelar, Inactivar, Activar |
| STATES | sin acceso, cargando, módulo no habilitado, 403, error, vacío, vacío con filtros | sin acceso, errores de campo, duplicado, error general | sin acceso, cargando, no encontrado, error, déficit proyectado, mes pasado, conflicto de versión, faltantes, conflicto SoD, cerrado, versión anterior de solo lectura | sin acceso, cargando, error, vacío, conflicto de versión |
| PERMISSIONS | backend: permiso → empresa → módulo | ídem | ídem + If-Match | ídem + If-Match |
| AUDIT | — | GOV_CASH_PROGRAM_CREATED | _UPDATED, _ACTIVATED, _REVISED, _DISCARDED, _CLOSED | GOV_CASH_ITEM_CREATED, _UPDATED |
| ERRORS | 403, 422 | 409 _DUPLICATE, 422 | 404, 409 _STALE, _INVALID_STATE, _NOT_READY, _PAST_MONTH, _DRAFT_OPEN, _EXERCISE_ENDED, duplicados, GOV_SOD_CONFLICT, 422, 428 | 409 _ITEM_DUPLICATE, _STALE, 404, 422 |
| RESPONSIVE | rejilla de indicadores y filtros; tabla en región | campos apilados | tablas en región con desplazamiento; 320 px sin desbordar | formulario apilado; tabla en región |
| ACCESSIBILITY | h1, caption, región, `aria-pressed`, `role=search` | rótulos obligatorios, `aria-invalid` | h1 «Programa PF-…», regiones con nombre, `role=alert`, `scope=col` | región «Tabla de rubros» |
| E2E | PF-E2E-01, 03 | PF-E2E-01, 03 | PF-E2E-01, 02, 03 | PF-E2E-01, 03 |

Respuestas de S3: período (ejercicio y mes inicial), cuentas y fuentes (declaraciones y rubros), moneda, caja prevista y disponible (tabla mensual), programado (líneas), versión vigente, quién cambió y cuándo (historia).

MISSING_REQUIRED_SCREENS = 0.
