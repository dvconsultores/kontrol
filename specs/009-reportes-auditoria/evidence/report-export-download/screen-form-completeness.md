# REPORT / EXPORT DOWNLOAD · Screen / Form completeness (2026-10-27)

| Campo | Exportaciones (`reportes/exportaciones`) | Centro de reportes (`reportes/centro`) |
|---|---|---|
| PROCESS_ID | FR-009-020 (exportación auditada) · KAUD-002 (archivo real) | FR-009-010..015 (reportes) · FR-009-020 |
| Propósito | Ver el histórico auditado y descargar el archivo real de una exportación | Elegir reporte → período → vista previa → exportar y obtener el archivo |
| Actores | `reportes:view` ve el listado; `reportes:export` + la capacidad de origen descargan | `reportes:view` + la capacidad de origen ven la vista previa; `reportes:export` exporta |
| Fuente de datos | `GET /reporting/exports`, `GET /reporting/exports/{id}/download` | `GET /reporting/reports/{key}`, `POST /reporting/exports`, `GET …/download` |
| Campos | Reporte, Formato, Archivo, Exportado por, Fecha, Estado | Categoría, Período, total, filas |
| Acciones | «Descargar <archivo>» (botón con nombre accesible); «Ejecutar job» (sin cambios) | «Exportar CSV (auditado)» |
| Estados | NORMAL · LOADING · EMPTY («Sin exportaciones») · ERROR («No fue posible cargar las exportaciones.») · GENERATING (botón ocupado, `aria-busy`) · DOWNLOAD_READY (aviso `role="status"` «Archivo descargado» con el nombre) · DOWNLOAD_FAILED, PERMISSION_DENIED, COMPANY_SCOPE_FORBIDDEN y NETWORK_ERROR (aviso `role="alert"` con su texto) | NORMAL · LOADING · EMPTY («No tiene autoridad para ver ningún reporte en esta empresa.») · GENERATING (AsyncButton «Procesando…») · DOWNLOAD_READY · DOWNLOAD_FAILED («… La exportación quedó creada; puede descargarla desde Exportaciones.») · fallo de creación («No fue posible exportar») |
| Validaciones | No hay campos editables; el identificador es el de la fila | Período: texto libre, opcional (por defecto «0»); el backend lo trata como texto (sin cambios) |
| Permisos (UI) | Botón visible solo con `puede("GET", "/reporting/exports/_/download")` | Categorías según la capacidad de origen; exportar con `<Autorizado operacion={["POST", "/reporting/exports"]}>` |
| Autorización (backend) | `reportes:export` + capacidad de origen + empresa (AD-5 de 02D); sin cambios | Ídem al crear y al descargar |
| Empresa / tenant | Empresa activa (cabecera del cliente central); otra empresa → 403/404; otro tenant → 404 | Ídem |
| Contrato de descarga | `apiFetch(ruta, { responseType: "archivo" })` → `{ blob, contentDisposition }` → `nombreSeguro` → URL `blob:` → `<a download>` temporal → revocación; los errores JSON llegan como `ApiError` y nunca se guardan como archivo | Ídem, tras crear la exportación |
| Manejo de errores | `mensajeDeDescarga`: 5 textos distintos; nunca éxito sin `Blob` | Creación y descarga, por separado |
| Paridad DB/API/UI | El nombre mostrado es el `file_ref` y el descargado, el de `Content-Disposition`: coinciden (DOWNLOAD-E2E-01) | Las capacidades de reporte vienen de la instantánea del backend (CR-04) |
| Seguridad | Sin token en URL, query, nombre ni evidencia (DOWNLOAD-E2E-02); la URL es `blob:`; un nombre único impide mezclar archivos entre empresas (D-T05) | Ídem |
| Auditoría | La exportación se audita al crearse (`REPORT_EXPORTED`, sin cambios); la descarga no tiene evento propio (política vigente) | Ídem |
| Responsive | Tabla existente; sin cambios de maquetación (la deuda del shell sigue aparte) | 320 px sin desbordamiento (READ-E2E-09 de 02D, en la regresión) |
| Accesibilidad | Botón con nombre accesible; `disabled` + `aria-busy` mientras descarga; **el foco se conserva tras descargar** (FOCO-01: antes, el botón se volvía a montar); avisos con `role="alert"` (asertivo) y `role="status"` (cortés) | AsyncButton con `aria-busy`; avisos con rol; axe en READ-E2E-09 |
| E2E | DOWNLOAD-E2E-01..08 | DOWNLOAD-E2E-09 |
| STATUS | **PASS** | **PASS** |

## Field contract

| FIELD_ID | LABEL | Tipo | Visibilidad | Backend | API | Error |
|---|---|---|---|---|---|---|
| `descargar-exportacion` | `Descargar <archivo>` | botón | `reportes:export` | `reportes:export` + origen + empresa | `GET /reporting/exports/{id}/download` | Textos de DL-FR-06 |
| `exportar-csv` | «Exportar CSV (auditado)» | botón | `POST /reporting/exports` | `reportes:export` + origen | `POST /reporting/exports`, después `GET …/download` | «No fue posible exportar» / «No fue posible descargar» |
| `periodo` | «Período» | texto | `reportes:view` + origen | texto, por defecto «0» | query `period` | (sin cambios) |

## Puerta (§69)

| Criterio | Resultado |
|---|---|
| PROCESS_COMPLETE, FIELD_CONTRACT, PARAMETER_VALIDATION | PASS |
| AUTHORIZATION, DOWNLOAD_ACTION, DOWNLOAD_ERROR_HANDLING | PASS |
| COMPANY_SCOPE, TENANT_SCOPE, DB_API_UI_PARITY, SECURITY | PASS |
| RESPONSIVE, ACCESSIBILITY, E2E, TRACEABILITY | PASS |
| **SCREEN_FORM_COMPLETENESS_GATE** | **PASS** |

## Reconciliación final de pantallas (§70)

| Pregunta | Respuesta |
|---|---|
| ¿Un usuario autorizado completa la descarga? | Sí: desde Exportaciones y desde el Centro |
| ¿La dispara uno no autorizado? | No: no ve el botón y la API lo niega |
| ¿La UI muestra acciones imposibles? | No: la puerta oculta lo que la capacidad estática no permite. Lo que depende de la capacidad de origen lo deniega el backend con un aviso claro (DOWNLOAD-E2E-06) |
| ¿El backend sigue siendo la autoridad? | Sí, sin cambios |
| ¿Se conserva la empresa? | Sí: la cabecera la pone el cliente central |
| ¿Están representados todos los errores? | Sí |
| ¿Queda alguna descarga con ancla directa? | No: la guarda de arquitectura nueva prohíbe cualquier `/api/v1/` fuera del cliente |

**BROKEN_AUTHENTICATED_DOWNLOAD_SURFACES = 0 · UNEXPLAINED_UI_FUNCTIONAL_GAPS = 0.**
