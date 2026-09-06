# SPEC 034 → SPEC 035 · CONTRATO DE ENTREGA

> Qué recibe el despacho y qué le queda por decidir. No implementa la Spec 035.

## La compuerta

```
GET /sales/facturacion/{order_id}/factura
```

El ¶103 dice que el despacho verifica que corresponda **«Pedido preparado +
Pedido confirmado + Factura emitida»**. Esto responde la tercera parte:

| Campo | Qué es |
|---|---|
| `invoiced` | `true` **si y solo si** el pedido tiene una factura viva en estado `EMITTED` |
| `order_status` | `INVOICED` tras la emisión |
| `invoice.invoice_number` · `control_number` | Lo que la Spec 042 asignó |
| `invoice.fiscal_document_id` | El documento fiscal emitido |
| `invoice.lines` | Cantidad comercial, cantidad base, presentación y factor congelados |

Las otras dos partes del ¶103 ya tienen su autoridad: la preparación en
`GET /sales/picking/{plan_id}/preparacion` (Spec 032) y la confirmación en
`GET /sales/confirmacion/{order_id}/facturable` (Spec 033).

## Lo que la Spec 034 no hace, a propósito

No marca despachado, no asigna vehículo ni conductor, no registra la salida
física, no emite guía de traslado ni resuelve permisos regulatorios, y **no
añade `DISPATCHED`** a la máquina del pedido: ese estado lo declara
`ADR-D0-012` y lo escribirá su dueña, igual que cada Spec de este tramo dejó el
suyo para la siguiente.

La reserva sigue **viva** en `INVOICED`: la consume la salida física
(`POL-D0-002` §8), que es de la 035.

## Lo que la Spec 035 tendrá que decidir

| Cuestión | Por qué no se decide aquí |
|---|---|
| Si `CONFIRMED → SHIPPED` debe cerrarse | Hoy la arista existe desde antes de este tramo. El ¶103 exige factura emitida antes de despachar, y **hacer cumplir eso es la compuerta de la 035**, con la autoridad que este contrato le entrega |
| Qué escribe `DISPATCHED` y cuándo | Es su estado |
| Cuándo se consume la reserva | `POL-D0-002` §8 dice «despacho (salida física)»; el momento exacto es suyo |
| Guías, permisos y regulación | Es su alcance |

## La emisión y la homologación legal no son lo mismo

`D0-07` mantiene las Specs 039-043 en `BLOCKED_BY_LEGAL_VALIDATION`. Este ciclo
construyó y probó el camino contra el motor fiscal existente; **no afirma que la
emisión esté legalmente homologada**. Esa confirmación normativa sigue pendiente
y no es de la 034 ni de la 035.
