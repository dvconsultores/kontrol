# WIREFRAMES — 005-VENTAS-CUENTAS-POR-COBRAR

| Campo | Valor |
|---|---|
| Iniciativa | 005-ventas-cuentas-por-cobrar |
| Versión | 1.0 |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/wireframes/README.md` |

## Principio

Las pantallas de ventas reutilizan el **sistema de diseño** y los patrones de wireframe de la fundación (WF-01 a WF-09) y las pantallas de referencia de DOC-04. No se introducen variantes locales (Constitución P7, ADR-015).

## Mapeo pantalla → patrón

| Pantalla 005 | Patrón base | Referencia DOC-04 | Notas |
|---|---|---|---|
| Cotización / pedido | WF-02 Formulario | — | Sin reserva de inventario |
| Orden de venta | WF-04 Documento | Pantalla 11 | Crédito, margen y reserva separados |
| Preparación y despacho | WF-04 Documento | Pantalla 12 | Lotes/seriales y documentos regulatorios antes de salida |
| Factura de venta | WF-04 Documento | Pantalla 13 | Producto+servicio; base fiscal VES y tasa snapshot |
| Cobro multimoneda | WF-02 Formulario | Pantalla 14 | Múltiples medios y monedas; aplicación independiente |
| CxC / aging | WF-05 Matriz | — | Open items, cobros, buckets de vencimiento, cobranza |

## Reglas de frontend aplicadas (DOC-08)

- Pantallas completas, sin modales (ADR-015).
- DataTable **sin scroll horizontal**; búsqueda asíncrona para catálogos grandes.
- Estados: loading, vacío, error, forbiden, conflicto (componentes compartidos).
- `allowed_actions` calculadas en backend; el frontend solo las muestra.
