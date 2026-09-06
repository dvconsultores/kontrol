# SPEC 033 → SPEC 034 · CONTRATO DE ENTREGA

> Qué recibe facturación y bajo qué condición. No implementa la Spec 034.

## La compuerta

```
GET /sales/confirmacion/{order_id}/facturable
```

Devuelve la respuesta a la única pregunta que la 034 debe hacerse: **¿este pedido
tiene una confirmación independiente válida?**

| Campo | Qué es |
|---|---|
| `eligible_for_billing` | `true` **si y solo si** existe una confirmación `CONFIRMED` y el pedido está en `CONFIRMED` |
| `confirmation_id` · `confirmed_at` · `checked_by` | Quién firmó el control, cuándo, y sobre qué registro |
| `order_status` | El estado vigente del pedido |

Es una autoridad, no un indicio: el ¶89 dice que «Facturación factura sobre un
pedido previamente confirmado», y esto responde eso en un sitio. No hay que
recomponerlo de varios indicadores dispersos, que es exactamente como se pierde
un control.

## Por qué no basta con mirar el estado del pedido

Un pedido en `CONFIRMED` sin registro de confirmación no debería existir —el
índice único y la transición lo impiden— pero la compuerta comprueba **las dos
cosas**. Un control que se pueda satisfacer moviendo un estado a mano no es un
control.

## Lo que la Spec 033 no hace, a propósito

No emite factura, no calcula impuestos, no asigna ni consume número de control,
no genera libro de IVA ni cuentas por cobrar, y **no escribe
`READY_FOR_BILLING`**: ese estado lo declara `ADR-D0-012` y lo añadirá su dueña,
igual que la 032 dejó `CONFIRMED` para la 033 y la 031 dejó `PREPARED` para la
032.

## Lo que la Spec 034 tendrá que decidir

| Cuestión | Por qué no se decide aquí |
|---|---|
| Qué escribe `READY_FOR_BILLING` y cuándo | Es su estado |
| Qué pasa si la preparación cambia **después** de confirmar | Hoy no puede: un pedido `CONFIRMED` no vuelve a preparación por ningún camino. Si la 034 abriera uno, la confirmación tendría que invalidarse |
| Qué queda prohibido una vez empezada la facturación | Es su frontera |

## Un pedido rechazado no llega aquí

Rechazar deja el pedido en `PREPARING` y `eligible_for_billing` en `false`. Para
volver a intentarlo, la preparación tiene que devolverlo al control — y eso, hoy,
es la deuda abierta de la Spec 032: su plan queda `CLOSED` al consolidar y no
tiene camino de reapertura, ni existe la arista `PICKING → DISPONIBLE`.

**No bloquea a la 034**, que solo consume pedidos conformes. Bloquea la
corrección, y tiene dueña.
