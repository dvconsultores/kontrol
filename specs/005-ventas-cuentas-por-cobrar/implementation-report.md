# SPEC 029 — INFORME DE IMPLEMENTACIÓN

## Qué se construyó

| Capa | Qué |
|---|---|
| Migración `0042` | 9 columnas de origen en cada línea, `price_list_id`, `quote_id`, precisión igualada |
| Modelos | Origen comercial en `SalesQuoteLine` y `SalesOrderLine`; índice único de conversión |
| Servicio | `_origen_comercial` consume la Spec 012; ciclo de la cotización; `convertir_en_pedido` |
| API | Detalle, transición y conversión de cotización; 3 rutas nuevas |
| Frontend | Precio automático con motivo para el manual; pantalla de detalle con el origen |

## Baseline

| | Antes | Después |
|---|---:|---:|
| Modelos · tablas | 177 | 177 |
| Migraciones | 41 | **42** |
| Claves foráneas | 356 | **366** |
| Rutas | 308 | **311** |
| Operaciones | 426 | **429** |
| Con contrato de empresa | 364 | **367** |

Las 3 operaciones nuevas declaran la empresa. Ninguna ruta se perdió, ninguna
tabla nueva: 029 completa lo que existía en vez de duplicarlo.

## Cuatro cosas que la implementación encontró

**El precio se truncaba al copiarse.** El maestro guarda cuatro decimales y la
línea guardaba dos. El origen habría apuntado a una versión cuyo precio no
coincide con el de la línea.

**La cotización nacía en un estado inexistente.** `status="ACTIVE"`, y `ACTIVE`
no aparecía en ninguna transición porque no había transiciones. El campo existía
y nada lo movía.

**El detalle del pedido no mostraba el origen.** Guardarlo y no poder enseñarlo
es tener la evidencia sin poder usarla; `order_dict` ahora lo expone.

**La reserva ya existía, y es de la Spec 030.** `_reserve_order` se dispara en
`APPROVED → RESERVED` desde la Spec 005. No se tocó: retirarla habría sido
decidir `D0-03` por eliminación.

## Lo que no se implementó, y de quién es

| Qué | Spec |
|---|---|
| Reserva de inventario y su momento | 030 · `D0-03` sin decidir |
| Evaluación y aprobación de crédito | 030 |
| Cola y ruta de preparación | 031 |
| Picking y consolidación | 032 |
| Confirmación independiente | 033 |
| Facturación | 034 |
| Despacho | 035 |
| Cuentas por cobrar | 037 |
| Precisión de `sales_invoice_lines` | 034 — anotado, no absorbido |

Dos pruebas comprueban que crear un pedido no reserva, no crea lista de
preparación y no factura. No es una promesa: es una medición antes y después.
