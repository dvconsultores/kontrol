# GOV-CTL-01 · CTL01_SCREEN_FORM_MATRIX (ficha de pantallas y formularios)

CTL-01 se compone de:
- cuatro pantallas: reglas, nueva regla, ficha de la regla y conflictos;
- la alerta `ConflictoSoD`, integrada en la ficha del acto (DOC-02) y en la del hallazgo (CTL-06);
- tres formularios de escritura: alta de la regla, edición del borrador y cierre con motivo. La activación es una acción sin formulario.

| Campo | S1 · Segregación de funciones | S2 · Nueva regla | S3 · Regla | S4 · Conflictos | Alerta en DOC-02 / CTL-06 |
|---|---|---|---|---|---|
| SCREEN_ID | `ReglasSodPage` | `NuevaReglaSodPage` | `ReglaSodPage` | `ConflictosSodPage` | `ConflictoSoD` en `ActoPage` y `HallazgoPage` |
| USER_GOAL | ver las reglas y su estado, y el pulso de conflictos de 30 días | declarar una incompatibilidad entre dos acciones | revisar, editar el borrador, activar o cerrar la regla y ver su historia | auditar quién intentó qué, sobre qué objeto y por qué regla | entender por qué no puede hacer la acción y qué hacer |
| MENU_PATH | Gobierno › Segregación de funciones (`/gobierno/sod`) | S1 › «Nueva regla» (`/gobierno/sod/nueva`) | código de la regla en S1 (`/gobierno/sod/:id`) | S1 › «Ver conflictos» o S3 › «Ver conflictos de esta regla» (`/gobierno/sod/conflictos`) | ficha del acto o del hallazgo, al intentar la acción |
| ROLE | `gobierno_sod:view`; «Nueva regla» con `:manage` | `gobierno_sod:manage` | `:view`; editar con `:manage`; activar y cerrar con `:activate` (SENSITIVE, MFA) | `gobierno_sod:view` | el permiso propio de la acción de DOC-02 o CTL-06 |
| SOURCE | `GET /gobierno/sod/reglas` | `GET /gobierno/sod/acciones` · `POST /gobierno/sod/reglas` | `GET /reglas/{id}` · `PATCH` · `POST /activar` · `POST /cerrar` | `GET /gobierno/sod/conflictos` (+ catálogo) | 409 `GOV_SOD_CONFLICT` con `details` |
| FIELDS | indicadores (vigentes, borradores, cerradas, conflictos 30 días); filtros Estado y Proceso; tabla: código, nombre, proceso, «A →/⇄ B», vigencia, estado | R04 Proceso, R05 Acción A, R06 Acción B (sin la creadora si es en un solo sentido), R07 En ambos sentidos, R08 Alcance (fijo), R02 Nombre, R03 Razón, R09 Vigente desde, R10 Vigente hasta | R01–R13 en datos; historia (fecha, cambio, usuario, detalle); edición: R02, R03, R09, R10; cierre: R12 Motivo | filtros: regla (URL), proceso, acción intentada, usuario exacto, desde y hasta; tabla: fecha, usuario, regla, proceso, acción intentada, acción previa, objeto con enlace | regla (código y nombre), acción previa, acción intentada, siguiente paso |
| ACTIONS | Nueva regla, Ver conflictos, abrir regla, filtrar por indicador | Registrar regla, Cancelar | Editar borrador / Guardar, Activar regla, Cerrar regla / Confirmar cierre, Ver conflictos | Aplicar filtros, Limpiar, Quitar filtro de regla, paginación, Abrir acto / Abrir hallazgo | Entendido |
| STATES | sin acceso, cargando, módulo no habilitado, 403, error con reintento, vacío | sin acceso, cargando catálogo, error con reintento, errores de campo, error general (`role=alert`) | sin acceso, cargando, módulo no habilitado, no encontrada, error con reintento, conflicto de versión (`role=alert`), duplicada (`role=alert`), estado inválido (aviso y recarga), «aún no en vigor» | sin acceso, cargando, módulo no habilitado, 403, error con reintento, vacío | persistente hasta «Entendido»; la ficha se recarga |
| PERMISSIONS | guardas del backend: permiso → empresa → módulo | ídem; la guarda `gate-coverage` exige puerta en el fichero | ídem; If-Match obligatorio (428 / 409 STALE) | ídem | la guarda no concede autoridad: solo impide |
| DOCUMENTS | — | — | — | — | — |
| AUDIT | — | GOV_SOD_RULE_CREATED | GOV_SOD_RULE_UPDATED / _ACTIVATED / _CLOSED | lee GOV_SOD_CONFLICT_BLOCKED | GOV_SOD_CONFLICT_BLOCKED (REJECTION) |
| ERRORS | 403 / 422 | 422 VALIDATION_ERROR / GOV_SOD_RULE_INVALID, 403 | 404 GOV_SOD_RULE_NOT_FOUND, 409 STALE / INVALID_STATE / DUPLICATE, 422, 428 | 422 | 409 GOV_SOD_CONFLICT |
| RESPONSIVE | indicadores en rejilla 1/2/4; tabla en región con desplazamiento; 320 px sin desbordar | campos apilados | datos en rejilla 1/2; historia en región | filtros en rejilla 1/2; tabla en región | bloque de ancho completo |
| ACCESSIBILITY | h1/h2, caption, región «Tabla de reglas…», enlaces «Abrir la regla …», `aria-pressed` en indicadores, `role=search` | rótulos con «(obligatorio)», `aria-invalid`, ayuda por campo | h1 «Regla SOD-…», regiones con nombre, `scope=col` | caption, región «Tabla de conflictos…», `role=search` | `role=alert` con `aria-labelledby` |
| E2E | SOD-E2E-01, 03 (axe 1280/768/320) | SOD-E2E-01, 03 | SOD-E2E-01, 03 | SOD-E2E-01, 02, 03 | SOD-E2E-01 (hallazgo) y 02 (acto) |

MISSING_REQUIRED_FIELDS = 0 · formularios de escritura: 3 · faltantes: 0.
