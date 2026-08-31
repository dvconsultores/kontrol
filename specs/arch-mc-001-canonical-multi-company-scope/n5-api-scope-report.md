# ALCANCE DE API — EVIDENCIA N5

## 1. Contrato

**294 rutas** en OpenAPI, el mismo número que antes de N5. Ninguna se perdió y
ninguna se añadió: esta fase acota lo que ya existía, no amplía la superficie.

## 2. «Registrada» no es «probada»

La distinción que costó `REM-046-001`: allí había 19 tipos de recurso
registrados y uno solo probado. Esta matriz separa las dos columnas a propósito.

| Capacidad | Alcance declarado | Prueba A/B | Propiedad en la base | Relación cruzada | Auditoría |
|---|---|---|---|---|---|
| Cuentas y bancos | COMPANY | sí | sí | sí | — |
| Movimientos bancarios | COMPANY | sí | sí | sí | — |
| Conciliación | COMPANY | sí | sí | sí | sí |
| Sesiones de caja | COMPANY | sí | sí | sí | sí |
| Transferencias de tesorería | COMPANY | sí | sí | **bloqueada** | — |
| Órdenes de compra | COMPANY | sí | sí | sí | — |
| Recepciones | COMPANY | sí | sí | **bloqueada** | — |
| Facturas de proveedor | COMPANY | sí | sí | sí | — |
| Pagos y aplicaciones CxP | COMPANY | sí | sí | **bloqueada** | sí |
| Órdenes de venta | COMPANY | sí | sí | **bloqueada** | — |
| Picking y despacho | COMPANY | sí | sí | **bloqueada** | — |
| Facturas de venta | COMPANY | sí | sí | sí | — |
| Cobros y aplicaciones CxC | COMPANY | sí | sí | **bloqueada** | sí |
| Almacenes y ubicaciones | COMPANY | sí | sí | sí | sí |
| Movimientos de inventario | COMPANY | sí | sí | sí | — |
| Transferencias de inventario | COMPANY | sí | sí | **bloqueada** | — |
| Lotes, series, conteos, costos | COMPANY | sí | sí | sí | — |
| Permisos y flota | COMPANY | sí | sí | **bloqueada** | — |
| Documentos oficiales | COMPANY | sí | sí | sí | — |
| Series y rangos fiscales | COMPANY | sí | sí | **bloqueada** | — |
| Documentos fiscales | COMPANY | sí | sí | **bloqueada** | — |
| Libros fiscales | COMPANY | sí | sí | — | — |
| Retenciones y periodos | COMPANY | sí | sí | sí | — |
| Políticas de aprobación (045) | COMPANY | sí | sí | sí | sí |
| Solicitudes y delegaciones (045) | COMPANY | sí | sí | sí | sí |
| Documentos y versiones (046) | COMPANY | sí | sí | sí | sí |
| Sucursales | COMPANY | sí | sí | sí | sí |
| Terceros y catálogo | COMPANY | sí | sí | sí | **no audita** |

Los guiones de la última columna no son omisiones: son dominios cuyo contrato no
exige auditoría para esa acción. Se anota lo que hay, no lo que convendría.

`Unknown` = **0**.

## 3. Un hueco de contrato que pertenece a N8

`X-Kontrol-Company` no aparece en OpenAPI. La dependencia lee la cabecera del
`Request` en vez de declararla como parámetro, así que FastAPI no puede
documentarla.

Funciona —112 pruebas la usan— pero un consumidor que lea solo el contrato no
sabría que existe. **Declararla es trabajo de N8**, que es la fase de contrato;
se registra aquí para que no se pierda.
