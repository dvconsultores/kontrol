# SPEC 037 · CUENTAS POR COBRAR

> Ciclo completo desde `/speckit.specify`. Estado de entrada:
> `DEPENDENCY UNBLOCKED · NOT READY_FOR_IMPLEMENTATION`, con **una** pregunta
> material abierta, heredada de la Spec 036.

## 0. Pre-flight: los dos deltas de la 036

| Delta | Dueña | Estado al empezar | Acción |
|---|---|---|---|
| A · `issue_invoice` no creaba la cuenta por cobrar | **034** | convergido en `spec034-convergence.md` | se completó su fila de trazabilidad (`IMP-034-041`) |
| B · `emit_document` solo sabía emitir `INVOICE` | **042** (`007-nucleo-fiscal`) | **corregido en código, no convergido en su dueña** | delta dirigido ejecutado: requisito `FR-007-020-D1`, convergencia y evidencia en `specs/007-nucleo-fiscal/` |

El delta B estaba solo en documentos de la 036. Eso no es converger en el dueño:
quien lea la Spec del núcleo fiscal tiene que poder saber que su motor emite hoy
los tres tipos de documento y por qué. Ya está escrito allí.

## 1. La autoridad

| Fuente | Nivel | Qué aporta |
|---|---|---|
| `02_Kontrol_Arquitectura_Funcional` §9 | 3 | **La fórmula del saldo**, las aplicaciones, los reversos y las diferencias cambiarias |
| `02_Kontrol_Arquitectura_Funcional` §10 | 3 | La frontera con tesorería: «cobros y pagos **separados** de la factura y de la obligación» |
| `02_Kontrol_Arquitectura_Funcional` §11 | 3 | «Notas referencian factura y limitan cantidades y montos al **saldo ajustable**» |
| `03_Kontrol_Modelo_de_Datos` §9 | 3 | `OpenItem`, `Payment`, `PaymentInstrument`, `Application`, `Advance` |
| `01_Kontrol_Documento_Maestro` | 3 | «Los saldos **no se editan**; se calculan desde movimientos y aplicaciones» |

Lo decisivo, literal:

> **CxC** — Saldo = documentos + débitos − cobros − retenciones − créditos.
> Soporta parcial, múltiple, anticipos, aging y gestión.
>
> **Aplicaciones** — Cada aplicación relaciona origen, destino, moneda, tasa,
> monto nominal, monto fiscal y fecha.
>
> **Reversos** — No eliminan; crean evento inverso y reapertura controlada.
>
> **Diferencias cambiarias** — Se calculan al aplicar o valorar según política;
> no alteran el IVA original por sí solas.

Y el modelo de datos nombra las cuatro procedencias de una aplicación:

> `Application` — source **payment/credit/withholding/advance**, target
> open_item, amounts in source/target/fiscal currency, rate, date.

## 2. OQ-037-01, cerrada

**Pregunta.** Cuando una nota de crédito se emite contra una factura ya
totalmente cobrada, ¿cómo representa KONTROL el importe que queda a favor del
cliente?

**Respuesta con autoridad.** Como un **crédito sin aplicar sobre su propia
nota**, que resta del saldo del cliente y puede aplicarse a otros documentos por
cobrar suyos. No hace falta inventar nada:

1. La fórmula del saldo ya **resta los créditos**: «Saldo = documentos + débitos
   − cobros − retenciones − **créditos**». Un cliente cuyos créditos superan sus
   documentos tiene saldo a favor, y eso es aritmética de la propia fórmula, no
   una entidad nueva.
2. El modelo declara que una aplicación puede tener por origen un **crédito**, y
   por destino **cualquier** documento por cobrar. Es decir: el crédito de una
   nota puede imputarse a otra factura del mismo cliente.
3. CxC «soporta **parcial, múltiple**»: la aplicación puede ser parcial y puede
   haber varias.
4. El remanente ya tiene dónde vivir: `SalesCreditNote.amount` menos
   `applied`. No se crea un segundo libro de dinero.

**Lo que esto descarta**, y por qué:

| Representación descartada | Por qué |
|---|---|
| Factura negativa | La nota **es** el documento; una factura negativa sería un documento fiscal inventado |
| Pago falso | Un pago es movimiento de dinero. El crédito de una nota tiene otra procedencia y no entró dinero |
| Reapertura de la factura pagada | La factura cobrada es historia; `CREDITED`/`PAID` son terminales |
| Reverso del cobro | El cobro ocurrió. «Los reversos crean evento inverso», y aquí no hay nada que revertir |
| Saldo negativo escrito en el documento | «Los saldos no se editan; se calculan» |

**Lo que queda fuera, declarado y no inventado:**

- **Reembolso en dinero.** Ninguna fuente dice que un crédito a favor pueda
  devolverse en efectivo. No se implementa. Si algún día se decide, la
  *habilitación* será de esta Spec y el *movimiento* de tesorería (038).
- **Aplicación entre monedas distintas.** La aplicación lleva moneda y tasa, así
  que el modelo lo contempla; pero la diferencia cambiaria se calcula «según
  **política**» y esa política no existe todavía. Se restringe a la misma moneda
  y se declara la frontera.

## 3. Lo que la investigación encontró

La 037 no está vacía: el motor de la Spec 004 ya tiene `OpenItem`, `Payment`,
`Application`, `Advance` y `aging`, y las cuatro procedencias están declaradas en
`Application.source_type`. Lo que falta es que **las cuentas por cobrar lo usen
bien**.

| Defecto | Qué dice la autoridad |
|---|---|
| `apply_credit_note` **no crea ninguna aplicación**: muta `applied` en los dos lados y no deja rastro | «Cada aplicación relaciona origen, destino, moneda, tasa, monto nominal, monto fiscal y fecha» |
| `apply_credit_note` **no comprueba el cliente**: la nota de un cliente puede aplicarse al documento de otro dentro de la misma empresa | Un crédito es del cliente que lo tiene |
| No existe **reverso** de una aplicación | «Los reversos no eliminan; crean evento inverso y reapertura controlada» |
| El saldo se calcula en **`float`** | «Los saldos no se editan; se calculan desde movimientos y aplicaciones», y el dinero no se calcula en coma flotante |
| No hay **estado de cuenta** del cliente | CxC: «Documentos; Cobros; Anticipos; Aplicaciones; Aging; **Cobranza**» |

El segundo es el más grave: es una fuga de dinero entre clientes que ninguna
prueba veía.

## 4. Fronteras

La 037 gobierna el **derecho de cobro**: su saldo, sus aplicaciones y su
trazabilidad. **No** mueve dinero —eso es de la 038—, **no** emite documentos
fiscales —de la 036 y la 042—, **no** recalcula impuestos y **no** decide la
aprobación de crédito comercial, que sigue siendo de la 030.
