# COMPRAS Y CxP — EVIDENCIA A/B

PostgreSQL 18.6 · **17 pruebas** · Veredicto: **PASS**

## El caso que da sentido al bloque

Un pago de la empresa B cancelando una obligación de la empresa A. La API
respondía **200**.

No deja síntoma. Los saldos cuadran a ambos lados porque el dinero salió de una
caja y la deuda se extinguió en otra; ningún informe se descuadra y nadie lo
nota. La única forma de descubrirlo es intentarlo a propósito.

## Causa

`apply_source` comprobaba que el documento de **destino** perteneciera a la
empresa del contexto, pero no la **fuente**. Corregido con `_require_source`,
que exige la misma empresa para pago, anticipo, nota de crédito y retención.

Son dos personas jurídicas distintas: si una paga por la otra, eso es un
préstamo entre empresas y necesita su propio documento.

## Segundo defecto: la idempotencia

La búsqueda por clave de idempotencia no acotaba empresa. A pedía un pago con
una clave que B ya había usado y recibía **el pago de B**: el identificador de
otra empresa entregado como propio. Corregido acotando por empresa, que es lo
que la clave siempre quiso decir.

El mismo patrón aparecía en facturas de proveedor y de venta y en movimientos de
inventario. Los cuatro corregidos.

## Cobertura

| Comprobación | Resultado |
|---|---|
| Órdenes de A y B con su empresa, verificado en la base | PASS |
| Listado sin intersección | PASS |
| Leer, anotar o transicionar la orden ajena | BLOCKED |
| Comprar a un proveedor de otra empresa | BLOCKED |
| Recibir mercancía de A en el almacén de B | BLOCKED |
| Recibirla en el almacén correcto | PASS |
| Tocar la factura de proveedor ajena | BLOCKED |
| El pago guarda su empresa | PASS |
| Pagar a un proveedor de otra empresa | BLOCKED |
| Pago de B → deuda de A | BLOCKED |
| Pago de A → deuda de B | BLOCKED |
| Aplicación legítima | PASS |
| Idempotencia entre empresas | BLOCKED |
| Alcance desde el otro tenant | BLOCKED |
| Auditoría `CXP_APPLICATION` con la empresa real | PASS |

El cruce se prueba **en las dos direcciones**. Y la aplicación legítima también,
sin la cual los dos bloqueos podrían deberse a que nada funciona.
