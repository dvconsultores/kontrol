# WIREFRAMES — 004-COMPRAS-CUENTAS-POR-PAGAR

| Campo | Valor |
|---|---|
| Iniciativa | 004-compras-cuentas-por-pagar |
| Versión | 1.0 |
| Ruta | `specs/004-compras-cuentas-por-pagar/wireframes/README.md` |

## Principio

Las pantallas de compras reutilizan el **sistema de diseño** y los patrones de wireframe de la fundación (WF-01 a WF-09) y las pantallas de referencia de DOC-04. No se introducen variantes locales (Constitución P7, ADR-015).

## Mapeo pantalla → patrón

| Pantalla 004 | Patrón base | Referencia DOC-04 | Notas |
|---|---|---|---|
| Requisición | WF-02 Formulario | — | Líneas + centro de costo + aprobación |
| Cotización / comparación | WF-05 Matriz | — | Comparación por precio/impuesto/disponibilidad/plazo/calidad |
| Orden de compra | WF-04 Documento | Pantalla 09 | Aprobación y totales por moneda; no sustituye recepción ni factura |
| Recepción | WF-04 Documento | — | Lotes/seriales/vencimientos/calidad; integra 003 |
| Factura del proveedor | WF-04 Documento | — | Validación de duplicidad; estados |
| Conciliación triple | WF-05 Matriz | Pantalla 10 | Diferencias explícitas y resolución auditada |
| Pago y retenciones | WF-02 Formulario | Pantalla 15 | Retenciones y neto conciliados; aprobación separada |
| CxP / aging | WF-05 Matriz | — | Open items, programación, buckets de vencimiento |

## Reglas de frontend aplicadas (DOC-08)

- Pantallas completas, sin modales (ADR-015).
- DataTable **sin scroll horizontal**; búsqueda asíncrona para catálogos grandes.
- Estados: loading, vacío, error, forbiden, conflicto (componentes compartidos).
- `allowed_actions` calculadas en backend; el frontend solo las muestra.
