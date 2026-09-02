# SPEC 029 — CONVERSIÓN DE COTIZACIÓN A PEDIDO

## No existía

Antes de este ciclo no había ninguna conversión. `sales_quotes` y `sales_orders`
eran dos tablas sin relación: se creaba una cotización, y luego se creaba un
pedido a mano repitiendo los datos. Nada ataba lo que se ofreció con lo que se
pidió.

## Ciclo de vida de la cotización

Tampoco existía. `sales_quotes.status` era una columna que nada movía, con valor
inicial `ACTIVE`, un estado que no aparecía en ninguna transición.

```
DRAFT ──→ SENT ──→ ACCEPTED ──→ CONVERTED
  │        │  └──→ REJECTED
  │        └─────→ EXPIRED
  └──→ CANCELLED
```

`CONVERTED` es terminal. Una cotización que ya produjo su pedido no vuelve a
editarse: editarla cambiaría un documento que ya existe aguas abajo.

Y solo `DRAFT` admite líneas nuevas. Enviada una cotización, su contenido es lo
que el cliente vio.

## La regla que gobierna la conversión

**No se vuelve a resolver el precio.**

Sería lo cómodo: llamar otra vez al resolutor y tener el precio «al día». Y
sería un error. Entre la cotización y el pedido puede publicarse una versión
nueva, y el cliente aceptó la anterior. Reconvertir en silencio cambiaría lo
pactado sin que nadie lo pidiera.

La evidencia viaja entera —versión, ítem, origen, precio resuelto, motivo
manual, política de descuento y condición de pago congelada— y el precio del
pedido es el de la cotización.

`test_la_conversion_no_reprecia_en_silencio` lo comprueba publicando una versión
a 999 entre la aceptación y la conversión, y exigiendo que el pedido siga a 60.

## Cardinalidad: una cotización, un pedido

No estaba documentada. Se resuelve **1:1**, que es la lectura conservadora: se
puede ampliar después a 1:N si el negocio lo pide; un 1:N construido por defecto
no se puede estrechar sin romper datos.

Lo garantiza un índice único parcial sobre `sales_orders.quote_id`, no una
comprobación en Python: dos peticiones simultáneas ganarían la carrera a la
comprobación y perderían contra el índice.

## Idempotencia

Convertir dos veces **no crea dos pedidos**. Devuelve el que existe:

| Llamada | Código | `created` |
|---|---|---|
| Primera | `201` | `true` |
| Siguientes | `200` | `false` |

Un doble clic, un reintento de red o un reenvío del navegador producen el mismo
pedido. La respuesta distingue las dos situaciones para que la interfaz pueda
decir la verdad —«el pedido ya existía»— en vez de fingir que acaba de crearlo.

## Qué se valida antes de convertir

| Comprobación | Respuesta si falla |
|---|---|
| La cotización es de la empresa activa | `404` |
| Está `ACCEPTED` | `409 SALES_QUOTE_NOT_CONVERTIBLE` |
| No está vencida | `409 SALES_QUOTE_EXPIRED` |
| Tiene líneas | `409 SALES_QUOTE_EMPTY` |
| El almacén, si se indica, es de la empresa | `404` |

Una cotización sin líneas no produce un pedido: un pedido vacío no es un pedido.

## Vigencia

`validity_until` nula significa **sin vencimiento**, no «vencida». Se comprueba
al enviar y al aceptar, no solo al convertir: enviar al cliente una cotización
ya vencida es prometer un precio que no se sostiene.

## Lo que la conversión NO hace

| Qué | De quién es |
|---|---|
| Reservar inventario | Spec 030, y `D0-03` sigue sin decidir cuándo |
| Evaluar crédito | Spec 030 |
| Crear lista de preparación | Spec 031 |
| Facturar | Spec 034 |
| Despachar | Spec 035 |
| Crear cuenta por cobrar | Spec 037 |

El pedido nace en `DRAFT`. Dos pruebas lo comprueban midiendo el inventario
reservado antes y después, y contando listas de preparación y facturas.

**La reserva existente no se tocó.** `_reserve_order` se dispara en la
transición `APPROVED → RESERVED` y estaba ahí desde la Spec 005; es territorio
de la 030. Retirarla habría sido decidir `D0-03` por eliminación, que es una
forma de decidirlo.
