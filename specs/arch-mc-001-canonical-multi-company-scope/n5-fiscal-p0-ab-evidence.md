# FISCAL P0 — EVIDENCIA A/B

PostgreSQL 18.6 · **13 pruebas** · Veredicto: **PASS**

Ninguna prueba toca un cálculo.

## Por qué este bloque es distinto

Aquí una confusión de empresa deja de ser un problema de software. Cada empresa
es un contribuyente distinto ante el SENIAT: su RIF, sus series de numeración,
sus rangos de control autorizados por la imprenta, sus libros.

Un número de A usado por B no es un registro mal etiquetado: es una factura que
la autoridad no reconoce.

## Prerrequisito

Se entró solo después de que sus autoridades —empresa, sucursal, factura de
venta, factura de proveedor, tesorería— tuvieran evidencia A/B propia. Estar
implementadas no bastaba.

## Cobertura

| Comprobación | Resultado |
|---|---|
| Series propias por empresa, sin intersección | PASS |
| Rangos de control sin mezcla | PASS |
| Los números heredan la empresa de su lote | PASS |
| Emitir con la serie de otra empresa | BLOCKED |
| Emitir con el rango de control de otra empresa | BLOCKED |
| Amparar fiscalmente una venta de otra empresa | BLOCKED |
| Emisión legítima, con su empresa y su prefijo | PASS |
| El correlativo de una empresa no avanza al emitir en la otra | PASS |
| Leer o imprimir un documento fiscal ajeno | BLOCKED |
| Notas de crédito y débito sobre un documento ajeno | BLOCKED |
| Contaminación del libro de ventas | PASS |
| Retenciones del agente que las practica | PASS |
| Periodos fiscales propios; cerrar el ajeno | BLOCKED |
| Ninguna fila hacia una empresa inexistente (11 tablas) | PASS |

## La prueba de libros, y cómo estuvo mal

La primera versión pedía el libro por `IVA` y **pasaba en vacío**: dos libros sin
filas no se contaminan, y el aislamiento habría quedado demostrado por no haber
datos. Es exactamente la clase de evidencia falsa que esta fase existe para
evitar.

La versión definitiva pide `VENTAS`, exige que ambos libros tengan filas, y
resuelve cada número contra PostgreSQL para comprobar a qué empresa pertenece el
documento que lo lleva. Un libro que incluyera facturas ajenas declararía ante el
SENIAT ventas de otro contribuyente.

## Paridad de cálculo

Ningún cambio toca bases imponibles, alícuotas, totales, IGTF ni retenciones.
Solo cambia de quién es cada documento. La suite fiscal existente pasa sin
modificaciones.
