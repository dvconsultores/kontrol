# VENTAS Y CxC — EVIDENCIA A/B

PostgreSQL 18.6 · **17 pruebas** · Veredicto: **PASS**

## Dos errores distintos

Del lado del cobro, el error es simétrico al de compras: si un cobro de A cancela
una factura de B, dos empresas se reparten el mismo ingreso y ninguna cuadra mal.

Del lado del despacho, el error es físico: mercancía saliendo de un almacén que
no pertenece a la empresa que vendió.

## Lo que ya estaba cerrado

El cruce de aplicaciones no requirió trabajo nuevo: ventas delega en el mismo
`apply_source` que se corrigió en compras. Reutilizar el servicio hizo que una
corrección valiera para dos dominios. Se comprueba igualmente, en ambas
direcciones, porque delegar no es lo mismo que estar probado.

## Cobertura

| Comprobación | Resultado |
|---|---|
| Órdenes de venta con su empresa, en la base | PASS |
| Listado sin intersección | PASS |
| Leer, anotar o transicionar la orden ajena | BLOCKED |
| Vender a un cliente de otra empresa | BLOCKED |
| Vender desde el almacén de otra empresa | BLOCKED |
| Preparar el pedido en el almacén ajeno | BLOCKED |
| Despachar desde el almacén ajeno | BLOCKED |
| Despachar una orden ajena | BLOCKED |
| Facturas de venta con su empresa | PASS |
| Tocar la factura de venta ajena | BLOCKED |
| Idempotencia de facturas entre empresas | BLOCKED |
| El cobro guarda su empresa | PASS |
| Cobrar a un cliente de otra empresa | BLOCKED |
| Cobro de B → cuenta por cobrar de A | BLOCKED |
| Cobro de A → cuenta por cobrar de B | BLOCKED |
| Cobro legítimo | PASS |
| Cuentas por cobrar sin mezcla | PASS |
| Auditoría `CXC_APPLICATION` con la empresa real | PASS |

## Idempotencia de facturas: el peor de los tres casos

A pedía una factura con una clave que B ya había usado y recibía **la factura
fiscal de B**, con su número y su total, como si fuera propia.

## Una prueba que pasaba por el motivo equivocado

La primera versión de la prueba de picking dejaba la orden en borrador. El
rechazo llegaba por el estado —«la orden no está en condiciones de
prepararse»— y no por la empresa, sin haber tocado nunca la comprobación que
pretendía interrogar. Ahora la orden se lleva hasta `RESERVED` antes de intentar
el almacén ajeno.
