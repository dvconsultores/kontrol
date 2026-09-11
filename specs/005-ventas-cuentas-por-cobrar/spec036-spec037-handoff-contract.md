# SPEC 036 → SIGUIENTE · CONTRATO DE ENTREGA

> Qué queda tras la devolución y la nota, y qué le corresponde a quién. No
> implementa ninguna Spec posterior.

## Lo que la Spec 036 deja

| Dato | Dónde |
|---|---|
| Qué se devolvió y contra qué factura | `SalesReturn.invoice_id` · `SalesReturnLine.invoice_line_id` |
| Cuánto queda por devolver | `GET /sales/devoluciones/elegibles/{invoice_id}` |
| Quién hizo cada acto y cuándo | `requested_*` · `received_*` · `inspected_*` · `approved_*` · `reentered_*` |
| A dónde fue cada línea | `SalesReturnLine.disposition` y `accepted_base_quantity` |
| Dónde está físicamente | `warehouse_id` · `location_id`, con su procedencia en el ledger |
| Qué se acreditó y cuánto queda | `GET /sales/notas/acreditable/{invoice_id}` |
| El documento fiscal de la nota | `invoice_number` · `control_number` · `fiscal_document_id` |
| El efecto financiero | `OpenItem` de la factura reducido; el de la nota de débito, propio |

## Lo que **no** decide la 036, con su dueño

| Cuestión | Dueño | Por qué no se decide aquí |
|---|---|---|
| Qué hacer con la mercancía de una devolución **denegada** | requiere autoridad | Se queda en `DEVUELTO`, que es custodia real. Devolvérsela al cliente sería una salida nueva y ninguna fuente la declara |
| Un crédito a favor sobre una factura ya cobrada | **037** CxC · **038** tesorería | La norma no condiciona la nota a que la factura esté pendiente; qué se hace con el saldo es de CxC |
| El reembolso en dinero | **038** | La 036 no mueve caja |
| El libro de ventas | **043** | «Las notas deben registrarse en el mes calendario en que sean emitidas» |
| El catálogo canónico de tipos de documento fiscal | **042** | `FiscalNumberSeries.document_type` no tiene restricción ni vocabulario declarado |
| `RECHAZADO · CUARENTENA → DESECHO` | **025** | Es una baja de inventario, con su aprobación |
| La reposición al cliente (nueva entrega) | **029/030** | Sería un pedido nuevo, con su reserva nueva. `D0-03`: «nueva fila, nunca reactivación» |

## La reserva

La reserva original queda **`FULFILLED` e inmutable**. La 036 no la reabre, no
la libera y no crea ninguna. Si la mercancía devuelta se compromete después, será
una reserva nueva con su propia fila, y la creará la Spec dueña de ese pedido.

## D0-07

Sigue abierto. La nota de crédito y la de débito están certificadas **técnica y
funcionalmente** contra el motor fiscal existente. **No** hay homologación fiscal
ni liberación legal para producción.
