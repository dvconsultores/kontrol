# READ-PERMISSION ENFORCEMENT · Screen / Form completeness (2026-10-27)

Superficies afectadas por el nuevo contrato de lectura (AD-1..AD-8).
- **Pantallas de módulo** (`/inventario/*`, `/compras/*`, `/ventas/*`, `/tesoreria/*`, `/fiscal/*`, `/regulatorio/*`, `/maestros/*` y `/organizacion/*`). El registro de pantallas de 02C ya exigía `<módulo>:view`, y su lectura principal exige ahora la misma capacidad. La paridad la prueba `authority-surfaces.test.ts`, con la instantánea regenerada.
- **Pantallas que cambian en este ciclo:** las cinco de la tabla.

| Campo | Inicio (tablero) | Centro de reportes | Exportaciones | Reportes · Auditoría | Selectores entre módulos |
|---|---|---|---|---|---|
| SCREEN_ID / ruta | `""` → `/` | `reportes/centro` | `reportes/exportaciones` | `reportes/auditoria` | Cliente o proveedor en 14 pantallas; moneda en Listas de precio; ubicaciones de put-away en Preparación |
| PROCESS_ID | FR-009-001/002 | FR-009-010..015 | FR-009-020 (KAUD-002/003) | FR-009 auditoría | Procesos de ventas, compras, tesorería, fiscal y regulatorio |
| Propósito | Resumen de la instalación y de los módulos | Vista previa y exportación auditada de reportes | Listado de exportaciones y trabajos; descarga | Línea de auditoría de la empresa | Elegir una entidad de referencia |
| Actores | Todo usuario (la sesión); indicadores según capacidad | Quien tiene `reportes:view` | Quien tiene `reportes:view`; descarga con `reportes:export` | Quien tiene `audit:view` | Roles de negocio |
| Datos leídos | `/reporting/dashboard` | `/reporting/reports/{key}` | `/reporting/exports`, `/jobs`, `/exports/{id}/download` | `/reporting/audit/timeline` | `/maestros/terceros`, `/treasury/currencies`, `/inventory/putaway/ubicaciones` |
| Capacidad de lectura declarada | `dashboard:view` + origen por indicador (AD-4) | `reportes:view` + origen por reporte (AD-5) | `reportes:view`; descarga `reportes:export` + origen | `audit:view` | La del módulo dueño (AD-3) |
| Alcance de empresa / tenant | Empresa activa / tenant autenticado | idem | idem | idem | idem |
| Campos | 7 indicadores y 3 vencimientos, cada uno solo si su capacidad de origen está | Categorías, período, total, filas | Reporte, formato, archivo, autor, fecha, estado | Sin cambios | Sin cambios |
| Acciones | Ninguna nueva | Exportar CSV (puerta `POST /reporting/exports`) | Ejecutar trabajo (puerta), Descargar (puerta `GET …/_/download`) | Ninguna | Ninguna |
| Estados | Sin capacidad: no pide ni pinta las secciones · CARGANDO: sin secciones · ERROR: `role="alert"` «No se pudieron cargar los indicadores.» · sección vacía: no se pinta | Sin ningún reporte: «No tiene autoridad para ver ningún reporte en esta empresa.» y nada más · categorías solo las disponibles | Sin `reportes:export`: la celda de descarga queda vacía (AD-6 de 02C: ocultar) | Sin `audit:view`: la guarda pinta «Acceso prohibido» o «Sin autoridad en esta empresa» sin pedir datos | La lectura denegada muestra el error de la API (deuda CROSS-MODULE-SELECTOR-COMPOSITION) |
| Permisos y autorización en backend | AD-4, RPE-08/09 | AD-5, RPE-10 | AD-5, RPE-11/16 | AD-6, RPE-12 | AD-1/AD-3, RPE-01..05 |
| Paridad DB/API/UI | Las claves presentes son las que el backend calcula | La tabla de capacidades llega por la instantánea (`report_capabilities`, CR-04) | La puerta usa el catálogo | El registro coincide con la capacidad de la ruta (EXP-03) | La UI no se cambia: el backend decide |
| Errores | 403 sin `dashboard:view` → la consulta ni se lanza | 403 de la vista previa imposible desde la UI (solo pide lo disponible); 404 de clave desconocida | 403/404 sin cambios | Guarda de 02C | 403 visible en el selector |
| Seguridad | GOV-CTL-004: ADMIN recibe un tablero sin cifras (READ-E2E-05) | Sin fuga por vista previa ni exportación | Descarga solo con export + origen | `audit:view` (§34) | Fail closed (OD-READ-06) |
| Responsive | 320 px sin desbordamiento (READ-E2E-09) | 320 px sin desbordamiento (READ-E2E-09) | Sin cambios de maquetación | Sin cambios | Sin cambios |
| Accesibilidad | axe WCAG 2.0/2.1 AA sin violaciones graves en `main` (READ-E2E-09); alerta con `role="alert"` | axe (READ-E2E-09); botones con `aria-pressed` sobre la categoría efectiva | Botón con `label` | Denegación con h1 y `role="alert"` (READ-E2E-02) | — |
| E2E | READ-E2E-05, 09 | READ-E2E-08, 09 | API: RPE-11/16 | READ-E2E-02/04 (guarda) | READ-E2E-03, 07 |
| STATUS | **PASS** | **PASS** | **PASS**, con la deuda REPORT-EXPORT-DOWNLOAD-ANCHOR registrada (preexistente: el enlace no lleva el token y falla cerrado) | **PASS** | **PASS**, con la deuda LOW registrada |

## Puerta (§79)

| Criterio | Resultado |
|---|---|
| PROCESS_COMPLETE · FIELDS_COMPLETE · VALIDATIONS_COMPLETE · PERMISSIONS_COMPLETE · READ_AUTHORIZATION_COMPLETE · COMPANY_SCOPE_COMPLETE | PASS |
| DB_API_UI_PARITY · SECURITY_COMPLETE · ERROR_HANDLING_COMPLETE · RESPONSIVE_COMPLETE · ACCESSIBILITY_COMPLETE · E2E_COMPLETE · TRACEABILITY_COMPLETE | PASS |
| **SCREEN_FORM_COMPLETENESS_GATE** | **PASS** |
| UNEXPLAINED_UI_FUNCTIONAL_GAPS | 0 (los dos huecos conocidos están registrados como deuda con evidencia) |

## Field contract (textos exactos)

| Superficie | Texto |
|---|---|
| Inicio, error del tablero | «No se pudieron cargar los indicadores.» |
| Centro de reportes, sin ningún reporte | «No tiene autoridad para ver ningún reporte en esta empresa.» |
| Inicio, secciones | «Indicadores» · «Vencimientos y alertas» |
| Etiquetas de indicadores (sin cambios) | Ventas, Compras, Tesorería (banco), CxC, CxP, Documentos fiscales, Despachos bloqueados, Open items vencidos, Períodos fiscales abiertos, Permisos activos |
