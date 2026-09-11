# SPEC 036 · CONTRATOS

> Qué promete cada acto y qué deja para otro. Un solo documento en vez de once:
> lo que la metodología pide es que los contratos existan y sean consultables,
> no que se repartan en ficheros que digan lo mismo.

## 1. Autorización y solicitud de devolución

| | |
|---|---|
| Autoridad | Norma §15 «Solicitud»; `CreditDebitNote`/`Return` del modelo de datos |
| Entrada | Factura emitida, motivo, líneas con cantidad **base** |
| Efecto físico | **ninguno** |
| Efecto fiscal | ninguno |
| Efecto financiero | ninguno |
| Estado | `REQUESTED` |
| Lo que comprueba | que el pedido salió del almacén; que la línea es de esa factura; que la cantidad no excede lo despachado **menos lo ya devuelto** |
| Lo que **no** hace | no aparta inventario, no reserva, no emite documento |

No hay plazo de devolución. Ninguna fuente lo declara y no se inventa uno: un
plazo escrito a mano sería una regla de negocio nacida de la nada.

## 2. Recepción física

| | |
|---|---|
| Autoridad | `D0-10` `DESPACHADO → DEVUELTO` · 036; arquitectura funcional «recepción» |
| Efecto físico | `DESPACHADO → DEVUELTO` en cantidad base, con lote y serial, en el almacén del pedido; traslado a la ubicación de devoluciones con `putaway` |
| Estado de la mercancía | `DEVUELTO`, que **no es vendible** (`R-D0-10-3`) |
| Estado | `RECEIVED` |
| Idempotencia | `received_at` corta antes de tocar nada |

El saldo `DESPACHADO` se reclasifica **donde está**: el Área de Confirmación del
plan que se consolidó, que es de donde la Spec 035 lo sacó. De allí se traslada
al área de devoluciones, que es un movimiento de ubicación y no de estado.

## 3. Inspección

| | |
|---|---|
| Autoridad | Norma §15 «Verificación física»; `D0-10` «requiere la inspección previa al reingreso que 036 define» |
| Dimensiones | cantidad aceptada por línea y destino por línea |
| Destinos | **`DISPONIBLE`** y **`RECHAZADO`**, los dos que `D0-10` concede |
| Estado | `INSPECTED` |
| Lo que **no** hace | no mueve inventario: dictamina |

`CUARENTENA` no está: su arista de entrada es de la Spec 020, por resolución de
incidencia. `DESECHO` tampoco: `RECHAZADO · CUARENTENA → DESECHO` es una baja de
la Spec 025, con su aprobación. Y «reparación» no es un estado de mercancía —en
la norma es un motivo de traslado de una guía de despacho—, así que no se crea.

## 4. Aprobación

| | |
|---|---|
| Autoridad | Norma §15 «Aprobación», entre la verificación y la entrada |
| Estado | `APPROVED` o `REJECTED` |
| Denegar | exige motivo |

**Lo que queda fuera y no se decide aquí:** qué hacer con la mercancía de una
devolución denegada. Se queda en `DEVUELTO`, que es custodia de la empresa y es
la verdad. Devolvérsela al cliente sería una salida nueva y ninguna fuente la
declara.

## 5. Entrada de inventario

| | |
|---|---|
| Autoridad | Norma §15 «Entrada de inventario», el cuarto acto |
| Efecto físico | `DEVUELTO → DISPONIBLE` o `DEVUELTO → RECHAZADO`, por línea y por lo **aceptado** |
| Estado | `CLOSED` |
| Idempotencia | `reentered_at` corta antes de tocar nada |

Lo no aceptado se queda en `DEVUELTO`. Un solo evento físico, un solo efecto de
inventario: no hay ajuste que sume por segunda vez.

## 6. Nota de crédito

| | |
|---|---|
| Autoridad | Norma §5 |
| Causas | devolución de mercancía, anulación, descuento posterior, bonificación, corrección de precio en exceso, disminución de cantidad, devolución de envases, reversión — «**entre otros casos**», así que el motivo se exige y no se encierra en un conjunto cerrado |
| Referencia | factura original, con su fecha, número y control |
| Base e IVA | **proporcionales** a la factura; se reparte el impuesto que ya lleva |
| Clasificación tributaria | la de la operación original: no se vuelve a clasificar |
| Tasa de cambio | la de la factura. La Providencia considera alteración fiscal el «cambio retroactivo del tipo de cambio» |
| Tope | lo **pendiente** del original, acumulativo |
| Numeración | Spec 042: consecutivo propio y número de control |
| Efecto físico | **ninguno** |
| Efecto financiero | reduce el documento por cobrar de la factura |
| Cardinalidad | varias notas por factura, mientras quede pendiente; una nota puede no tener devolución |

**Si la factura ya está cobrada** no hay saldo que reducir y la nota queda sin
aplicar. No es un error: la norma no condiciona la nota a que la factura esté
pendiente. Qué hacer con ese crédito a favor —imputarlo a otra factura,
devolverlo— es de CxC (**037**) y de tesorería (**038**), y **no se decide aquí**.

## 7. Nota de débito

| | |
|---|---|
| Autoridad | Norma §6 |
| Causas | diferencia de precio, incremento de cantidad, flete posterior gravado, intereses o recargos, corrección de base inferior |
| Referencia | factura original, **obligatoria**: «no puede utilizarse como una factura independiente ni para encubrir una nueva venta» |
| Efecto físico | **ninguno**: su flujo no tiene una sola etapa física |
| Efecto financiero | crea su **propio** documento por cobrar |
| Tope | ninguno: una nota de débito suma |

## 8. Reserva

La reserva original queda **`FULFILLED` e inmutable**. `D0-03` §H: «re-reservar
tras liberar = **nueva fila, nunca reactivación**», y `FULFILLED` no es siquiera
una liberación sino un consumo. La devolución crea disponibilidad por la entrada
de inventario, no resucitando el compromiso de una venta que sí ocurrió. Si esa
mercancía se compromete después, será una reserva nueva.

## 9. Período cerrado

«Las notas de débito y crédito deben registrarse en el mes calendario en que
sean **emitidas** o recibidas». La nota se registra en su propio mes, no en el de
la factura. El libro es de la Spec 043.

## 10. Aprobación y evidencia

El motor de aprobaciones (**045**) y el de documentos (**046**) se consumen por
sus contratos existentes. No se construye ningún motor paralelo de aprobación de
devoluciones ni ningún almacén de evidencia propio.
