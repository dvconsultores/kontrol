# GOV-DOC-08 · DOC08_SCREEN_FORM_MATRIX (ficha de pantallas y formularios)

DOC-08 se compone de:
- tres pantallas: generación, listado con verificación y ficha;
- un panel de verificación, dentro del listado;
- una sección «Paquetes de esta muestra» y el botón «Generar paquete de auditoría» en la ficha de la muestra de CTL-04;
- dos formularios de escritura: generar (propósito) y verificar (archivo).

| Campo | S1 · Generar paquete | S2 · Paquetes de auditoría | S2b · Verificar un paquete (en S2) | S3 · Paquete | Ficha de muestra (CTL-04) |
|---|---|---|---|---|---|
| SCREEN_ID | `GenerarPaquetePage` | `PaquetesPage` | `VerificarPaquete` | `PaquetePage` | `MuestraPage` + `PaquetesDeLaMuestra` |
| USER_GOAL | ver el alcance antes de generar y generar con un propósito | consultar el historial de paquetes | comprobar si una copia está íntegra | ver código, huellas y contenido; descargar el paquete y el manifiesto; ver las verificaciones | lanzar la generación y ver los paquetes de la muestra |
| MENU_PATH | ficha de muestra › «Generar paquete de auditoría» | Gobierno › Paquetes de auditoría | sección de S2 | código del paquete en S2 o en la ficha de muestra | Gobierno › Auditoría institucional › muestra |
| ROLE | `gobierno_paquetes:generate` (SENSITIVE, MFA) | `gobierno_paquetes:view` | `gobierno_paquetes:view` | `gobierno_paquetes:view`; descargar exige además `documentos:download` y poder leer cada documento incluido | botón con `:generate`; sección con `:view` |
| SOURCE | muestra inmutable de CTL-04 (`/vista-previa`) | `GET /gobierno/paquetes` | ZIP subido (`POST /paquetes/verificar`) | `GET /gobierno/paquetes/{id}` | `GET /gobierno/paquetes?muestra_id=` |
| FIELDS | muestra (código, título, método, semilla, población, tamaño, registrada por/el); eventos, incluidos, excluidos, hallazgos, tamaño estimado; documentos (id, estado, motivo, versión, tamaño, referencias); P05 Propósito | P01, P02 (código de muestra), P06, P09, P10 y P07 abreviada | V01 Archivo; V02 Resultado; V03 Motivos; V04 Huella / idéntico | P01–P11 (manifiesto sin nombres de documento); eventos, documentos y hallazgos; historial de verificaciones | código, fecha, tamaño y huella de cada paquete |
| ACTIONS | Generar paquete, Cancelar | Abrir paquete, paginación | Verificar | Descargar paquete, Descargar manifiesto | Generar paquete de auditoría |
| STATES | sin acceso, cargando, módulo no habilitado, muestra no encontrada, error con reintento, límite superado (`role=alert`, botón deshabilitado), sin documentos, paquetes previos | sin acceso, cargando, módulo no habilitado, vacío, error con reintento | sin permiso (no se muestra), archivo rechazado (`role=alert`), resultado (`role=status`) | sin acceso, cargando (h1 «Paquete» sin código), módulo no habilitado, no encontrado, error con reintento, sin verificaciones, sin hallazgos | cargando, vacío, error |
| PERMISSIONS | guardas del backend: permiso → empresa → módulo | ídem | ídem; la guarda `gate-coverage` exige puerta en el fichero | ídem; 403 GOV_PACKAGE_DOCUMENTS_FORBIDDEN | ídem |
| DOCUMENTS | evalúa la inclusión con la regla de la Spec 046 | — | — | copia de los documentos incluidos dentro del ZIP | — |
| AUDIT | GOV_AUDIT_PACKAGE_GENERATED | — | GOV_AUDIT_PACKAGE_VERIFIED / _VERIFICATION_FAILED | GOV_AUDIT_PACKAGE_DOWNLOADED (paquete o manifiesto) | — |
| ERRORS | 404, 409 GOV_PACKAGE_CONFLICT / GOV_PACKAGE_IDEMPOTENCY_CONFLICT, 422 VALIDATION_ERROR / GOV_PACKAGE_TOO_LARGE | 403 / 422 | 422 GOV_PACKAGE_UPLOAD_INVALID | 403 GOV_PACKAGE_DOCUMENTS_FORBIDDEN, 404 GOV_PACKAGE_NOT_FOUND, 500 STORAGE_HASH_MISMATCH | — |
| RESPONSIVE | tarjetas apiladas; tabla en región con desplazamiento propio; 320 px sin desbordar | tabla en región; 320 px sin desbordar | campos apilados | huellas con `break-all`; tablas en región | lista simple |
| ACCESSIBILITY | h1/h2, caption, región con nombre, «Propósito (obligatorio)», `role=alert` | caption, región «Tabla de paquetes de auditoría», enlaces con nombre propio | etiqueta «Archivo del paquete (obligatorio)», `role=status` con `aria-live`, lista «Motivos» | regiones «Eventos/Documentos/Hallazgos del paquete», captions | h2 «Paquetes de esta muestra» |
| E2E | DOC8-E2E-01 y 03 | DOC8-E2E-01, 02 y 03 | DOC8-E2E-01 (válido e inválido) y 02 | DOC8-E2E-01 y 03 | DOC8-E2E-01 y 02 |

MISSING_REQUIRED_FIELDS = 0 · formularios de escritura: 2 · faltantes: 0.
