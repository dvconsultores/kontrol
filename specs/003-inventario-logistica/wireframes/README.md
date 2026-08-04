# WIREFRAMES — 003-INVENTARIO-LOGISTICA

| Campo | Valor |
|---|---|
| Iniciativa | 003-inventario-logistica |
| Versión | 1.0 |
| Ruta | `specs/003-inventario-logistica/wireframes/README.md` |

## Principio

Las pantallas de inventario reutilizan el **sistema de diseño** y los patrones de wireframe de la fundación (WF-01 a WF-09) definidos en `specs/001-fundacion/wireframes/` y las pantallas de referencia de DOC-04. No se introducen variantes locales (Constitución P7, ADR-015).

## Mapeo pantalla → patrón

| Pantalla 003 | Patrón base | Referencia DOC-04 | Notas |
|---|---|---|---|
| Existencias | WF-01 Listado | Pantalla 04 (detalle producto: resumen de inventario) | Filtros producto/almacén/ubicación/lote/serial/estado; paginación; `allowed_actions` |
| Kardex | WF-03 Detalle | — | Historial de movimientos con saldos acumulados; solo consulta |
| Transferencia | WF-04 Documento | — | Solicitud → aprobación → envío → recepción; diferencias por línea |
| Conteo | WF-05 Matriz | — | Plan, líneas (esperado/contado/diferencia), congelamiento, aprobación |
| Ajuste | WF-02 Formulario | Pantalla 12 (preparación y despacho) | Motivo, evidencia, costo, aprobación; genera movimiento |
| Almacenes/Ubicaciones | WF-02 Formulario | — | Maestros de custodia con estados |

## Reglas de frontend aplicadas (DOC-08)

- Pantallas completas, sin modales (ADR-015).
- DataTable **sin scroll horizontal**; búsqueda asíncrona para catálogos grandes.
- Estados: loading, vacío, error, forbiden, conflicto (componentes compartidos de 001).
- Estados vacíos con título y descripción accionable.
- `allowed_actions` calculadas en backend; el frontend solo las muestra.
