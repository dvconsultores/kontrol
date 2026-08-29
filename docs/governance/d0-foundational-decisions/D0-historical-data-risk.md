# RIESGO SOBRE DATOS HISTÓRICOS

> Decisiones cuyo retraso hace **imposible** reconstruir la historia. No es deuda que se paga más
> cara: es información que no se captura y por tanto no existe.

## Criterio

Una deuda entra aquí cuando cumple las tres condiciones:

1. El dato se genera en cada transacción.
2. No puede derivarse después de otra fuente.
3. Su ausencia hace ambigua la interpretación del documento histórico.

## Riesgos activos

| # | Decisión | Dato que no se está capturando | Reconstruible | Ventana | Severidad |
|---|---|---|:--:|---|---|
| **H-01** | D0-09 | `uom_id`, `presentation_id`, `conversion_factor_snapshot`, `base_quantity` en cada línea | **No** | Cada línea emitida | **MÁXIMA** |
| **H-02** | D0-11 | `SalesInvoice.order_id` y `SalesInvoiceLine.order_line_id` | **No** | Cada factura emitida | **MÁXIMA** |
| **H-03** | D0-04 | `location_id` en movimientos, recepciones y picking | **No** | Cada movimiento | **ALTA** |
| **H-04** | D0-05 | Snapshot comercial: lista o regla que produjo el precio, política de descuento aplicada | **No** | Cada cotización y pedido | **ALTA** |
| **H-05** | D0-02 | Versión de política de aprobación aplicada | **No** | Cada aprobación | **ALTA** |
| **H-06** | D0-07 | Snapshot de la regla fiscal aplicada | Parcial | Cada documento fiscal | **ALTA** |
| **H-07** | D0-13 | Dimensiones organizacionales congeladas en el documento | Parcial | Cada documento | MEDIA |
| **H-08** | D0-10 | Trazabilidad del estado de mercancía por movimiento | Parcial | Cada movimiento | MEDIA |

## Por qué H-01 y H-02 son las peores

**H-01.** Una línea que dice `quantity = 10` sin unidad es ambigua para siempre. Si mañana el factor
de conversión del producto cambia de 100 a 50 por caja, no habrá forma de saber qué significaba ese
10. El backfill solo puede **suponer** unidad base, y una suposición registrada como dato es peor
que un dato ausente reconocido — por eso el backfill marca `uom_source = LEGACY_ASSUMED_BASE`.

**H-02.** El vínculo factura↔pedido nunca se escribió. No hay heurística válida: coincidencia de
cliente, fecha e importe produce falsos positivos, y un falso positivo en trazabilidad fiscal es
peor que un hueco declarado. Las facturas existentes quedan `LEGACY_UNLINKED` de forma permanente.

## Consecuencia para el roadmap

Estas dos deudas justifican **adelantar a la Ola 0** dos trabajos que por severidad nominal irían más
tarde:

| Trabajo | Ola original | Ola ajustada | Motivo |
|---|---|---|---|
| FK `SalesInvoice.order_id` + `SalesInvoiceLine.order_line_id` | 6 | **0** | Cada día de facturación amplía el conjunto irrecuperable |
| Columnas de UOM, presentación y factor en líneas | 2 | **0 (esquema) / 2 (uso)** | El esquema puede adelantarse aunque la funcionalidad completa llegue en la Ola 2 |

El resto de la Spec 034 y de la 011 se mantiene en su ola. Lo que se adelanta es **la captura del
dato**, no la funcionalidad.

## Regla derivada

> **R-D0-H-1.** Cuando una decisión implique capturar un dato que no puede derivarse a posteriori,
> la columna que lo captura se implementa en cuanto la decisión se aprueba, aunque la funcionalidad
> que lo explota llegue varias olas después.

Esta regla se propone incorporar a la Constitución — ver `D0-constitution-diff.md`, enmienda E-03.

## Riesgo si no se actúa

Con la operación actual, cada mes de uso añade documentos al conjunto irrecuperable. En una
plataforma cuya promesa central es la reconstrucción auditable de saldos y libros (Constitución P5,
Vol. 1 §2), un histórico ambiguo compromete el argumento de producto, no solo la funcionalidad.
