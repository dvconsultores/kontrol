# Wireframes — 001-FUNDACION

| Campo | Valor |
|---|---|
| Fuente | DOC-08 (§6), DOC-04 |
| Ruta | `specs/001-fundacion/wireframes/` |

## Patrones base (WF-01..WF-09)

| ID | Patrón | Estructura | Archivo |
|---|---|---|---|
| WF-01 | Listado | PageHeader + búsqueda/filtro + DataTable + paginación | `WF-01-listado.md` |
| WF-02 | Formulario de alta/edición | PageHeader + secciones + barra sticky + guard | `WF-02-formulario.md` |
| WF-03 | Detalle de entidad | Resumen + estado + pestañas + timeline | `WF-03-detalle.md` |
| WF-04 | Documento transaccional | Cabecera + tercero + líneas + totales + timeline | `WF-04-documento.md` |
| WF-05 | Matriz | Encabezado + contexto + grupos + columnas compactas | `WF-05-matriz.md` |
| WF-06 | Asistente | Pasos + validación por paso + resumen | `WF-06-asistente.md` |
| WF-07 | Dashboard | Filtros + KPI + alertas + tablas cortas | `WF-07-dashboard.md` |
| WF-08 | Reporte | Parámetros + vista previa + exportación + auditoría | `WF-08-reporte.md` |
| WF-09 | Solo consulta | Banner licencia + escritura bloqueada + lectura permitida | `WF-09-solo-consulta.md` |

> Regla: toda pantalla nueva selecciona un patrón base; cualquier desviación requiere ADR y aprobación (DOC-08 §6).
