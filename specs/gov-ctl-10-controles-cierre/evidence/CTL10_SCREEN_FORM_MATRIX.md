# GOV-CTL-10 · CTL10_SCREEN_FORM_MATRIX

| Campo | S1 · Controles de cierre | S2 · Nueva política | S3 · Política | S4 · Cierres bloqueados | P1 · Panel BloqueoDeCierre |
|---|---|---|---|---|---|
| SCREEN_ID | `PoliticasPage` | `NuevaPoliticaPage` | `PoliticaPage` | `BloqueosPage` | `BloqueoDeCierre` (componente) |
| USER_GOAL | ver las políticas por acción y estado | abrir una política de cierre | definir controles, activar, retirar y revisar la historia | ver los cierres que el sistema impidió | entender por qué no se pudo cerrar |
| MENU_PATH | Gobierno › Controles de cierre (`/gobierno/cierres`) | S1 › «Nueva política» (`/gobierno/cierres/nueva`) | «Abrir la política PC-…» (`/gobierno/cierres/:politicaId`) | S1 › «Cierres bloqueados» (`/gobierno/cierres/bloqueos`) | EstructuraPage y ProgramaPage ante el 409 GOV_MATERIAL_CLOSE_BLOCKED |
| ROLE | `gobierno_cierre:view`; crear con `:manage` | `:manage` | `:view`; escritura `:manage`; activar y retirar `:activate` (MFA) | `:view` | el permiso de la pantalla de origen |
| FIELDS | indicadores por estado; filtros acción y estado; tabla: código, nombre, acción, estado, vigente desde, efectiva hoy | C01 nombre, C02 acción de cierre, C03 fundamento, C04 vigente desde, C05 vigente hasta | datos; controles K01 tipo, K02 riesgo mínimo, K03 materialidad; historia | filtros acción, desde, hasta; tabla: instante, política, proceso, objeto, ejercicio, usuario, total | qué lo impide, por qué es material, pendientes con enlaces, ruta de lista, dueño «Control Interno» |
| ACTIONS | Nueva política, Cierres bloqueados, abrir, filtrar | Crear política, Cancelar | Editar, Guardar, Añadir control, Quitar control, Activar, Retirar | filtrar, abrir política, abrir objeto | abrir pendiente, ir a la lista, cerrar el aviso |
| STATES | sin acceso, cargando, módulo no habilitado, 403, error, vacío, vacío con filtros | sin acceso, errores de campo, error general | sin acceso, cargando, no encontrado, error, conflicto de versión, activa existente, sin controles, MFA requerida, solo lectura | sin acceso, cargando, error, vacío, vacío con filtros | bloqueado con pendientes, más de 5 pendientes |
| PERMISSIONS | backend: autenticación → permiso → empresa → módulo | ídem | ídem + If-Match | ídem | el 409 lo decide el servidor |
| AUDIT | — | GOV_CLOSURE_POLICY_CREATED | _UPDATED, _CONTROL_ADDED, _CONTROL_REMOVED, _ACTIVATED, _RETIRED | lee GOV_MATERIAL_CLOSE_BLOCKED | GOV_MATERIAL_CLOSE_BLOCKED, GOV_MATERIAL_CLOSE_ALLOWED (servidor) |
| ERRORS | 403, 422 | 422 | 404, 409 _STALE, _INVALID_STATE, _ACTIVE_EXISTS, 422, 428 | 403, 422 | 409 GOV_MATERIAL_CLOSE_BLOCKED |
| RESPONSIVE | rejilla de indicadores y filtros; tabla en región | campos apilados | tablas en región con desplazamiento; 320 px sin desbordar | tabla en región | bloque apilado; enlaces con área táctil |
| ACCESSIBILITY | h1, caption, región, `aria-pressed`, `role=search` | rótulos obligatorios, `aria-invalid` | h1 «Política PC-…», regiones con nombre, `role=alert`, `scope=col` | h1, caption, región con nombre | `role=alert`, lista de enlaces con nombre accesible |
| E2E | CIE-E2E-01, 03 | CIE-E2E-01, 03 | CIE-E2E-01, 02, 03 | CIE-E2E-01, 03 | CIE-E2E-01 (flujo A), 02 (flujo B), 03 |

Respuestas de S3: acción que controla, tipos de control con su materialidad, vigencia, quién activó y cuándo, quién retiró y por qué, historia completa. Respuestas de P1: qué lo impide, por qué es material, qué queda pendiente, quién es dueño.

MISSING_REQUIRED_SCREENS = 0. Reportes y documentos: NOT_APPLICABLE.

## Escenario de la dueña (OWNER_UAT_SCENARIO_DEFINED = 1)

1. Control Interno entra en Gobierno › Controles de cierre y crea «PC-001» para cerrar la estructura, con el control de hallazgos abiertos de riesgo MEDIO o superior y su materialidad.
2. La activa con MFA. Intenta crear una segunda activa para la misma acción: ve el aviso.
3. Con un hallazgo ALTO abierto, cierra la estructura de un ejercicio pasado: ve el panel de bloqueo con el hallazgo y su enlace, y el intento en Cierres bloqueados.
4. Cierra el hallazgo en Hallazgos y repite: el cierre procede.
5. Crea y activa una política para cerrar el programa con el control de actos sin eficacia; con un acto emitido en el ejercicio, el cierre del programa se bloquea (flujo B).
6. Retira la política con MFA y motivo: el cierre vuelve a proceder; la historia lo muestra.
