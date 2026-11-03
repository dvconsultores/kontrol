# GOV-ORG-07 · ORG07_SCREEN_FORM_MATRIX (ficha de pantallas y formularios)

ORG-07 es un proceso de consulta: no tiene formularios de escritura (N/A legítimo). Hay una pantalla con un panel de detalle.

| Campo | S1 · Matriz de autoridad | S2 · Detalle del cargo (panel en S1) |
|---|---|---|
| SCREEN_ID | `MatrizAutoridadPage` | sección `detalle-cargo-titulo` |
| USER_GOAL | Saber qué cargo puede qué, sobre qué materia, en qué unidad, hasta cuánto, con qué acto y vigencia, a una fecha | Ver el acto soporte y el historial del cargo y qué versión usa la matriz |
| MENU_PATH | Gobierno › Matriz de autoridad (`/gobierno/autoridad`) | «Ver detalle» en una fila (`?detalle=<cargo>`) |
| ACTOR | Control Interno, auditor, Máxima autoridad (`gobierno_autoridad:view`) | ídem |
| FIELDS | M01–M11 (spec §5): cargo, unidad y ruta, acción, materia, límite, fundamento, vigencia, estado, acto soporte, versión, origen | cargo, unidad y ruta, estado, vigencia, acto soporte (títulos), versiones (n.º, estado, registrada el, motivo, competencias) |
| FILTERS | Ejercicio, A la fecha, Unidad (con subunidades), Cargo, Acción, Materia, Buscar (al enviar); «Limpiar filtros» | — |
| ACTIONS | Exportar CSV (filtros activos), Ver detalle, paginación | Cerrar el detalle; «Abrir el cargo» solo con `gobierno_cargos:view` |
| STATES | cargando; sin acceso; módulo no habilitado; sin estructuras; sin autoridad a la fecha; ningún resultado del filtro; fecha fuera del ejercicio (error de campo); error con reintento | cargando; error con reintento |
| PERMISSIONS | `gobierno_autoridad:view` (STANDARD); sin él, sin menú y «Sin acceso» sin peticiones | ídem; el enlace al cargo exige además `gobierno_cargos:view` |
| DATA_SOURCE | `GET /gobierno/autoridad/{ej}` (proyección de ORG-03), `/ejercicios`, `/{ej}/filtros` | `GET /gobierno/autoridad/{ej}/cargos/{id}` |
| AUDIT | Exportación: `GOV_AUTHORITY_MATRIX_EXPORTED` (ejercicio, fecha, filtros, filas); los cambios de autoridad los audita ORG-03 | trazabilidad: versión → historial de ORG-03 |
| REPORT | CSV `autoridad-<ej>-<fecha>.csv` con las columnas de §5 + `fecha_corte` | — |
| ERRORS | 422 fecha fuera del ejercicio, 422 filtro ajeno, 404 sin estructura, 403 sin permiso / módulo | 404 cargo ajeno, BORRADOR o de otra empresa |
| RESPONSIVE | 1280/768/320: tabla en contenedor con desplazamiento propio; la página no desborda | ídem |
| ACCESSIBILITY | labels, caption, `aria-live` en el resumen, error asociado al campo, estado con texto («Inactivo») | heading, caption «Historial del cargo», botón con aria-label |
| E2E | ORG7-E2E-01..05 (×3 navegadores) | ORG7-E2E-01, -03, -05 |

MISSING_REQUIRED_FIELDS = 0 · formularios de escritura: N/A (consulta) · faltantes: 0.
