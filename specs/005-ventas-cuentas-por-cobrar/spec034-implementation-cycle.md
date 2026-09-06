# SPEC 034 — LIBERACIÓN Y FACTURACIÓN · CICLO DE IMPLEMENTACIÓN

> 2026-09-06, sobre `fe92cf3`. Ciclo completo desde `/speckit.specify`.
> **`MATERIAL OQ = 0`.** El ciclo enumeraba catorce preguntas materiales. Todas tienen autoridad, y
> tres fuentes distintas se reparten el trabajo: el proceso fuente dice **qué pasa**, `ADR-D0-012`
> dice **en qué estados**, y el backlog maestro fija **los criterios de aceptación**.

## 1. La fuente

**Proceso 7 · Liberación para facturación**

| ¶ | Texto |
|---|---|
| 83 | El Área de Confirmación **autoriza** que el pedido puede facturarse. |
| 84 | **Se genera la solicitud de facturación.** |
| 85 | Facturación recibe el pedido confirmado. |
| 86-90 | «Almacén prepara. Confirmación verifica. Facturación factura sobre un pedido previamente confirmado. Eso establece una separación funcional adecuada.» |

**Proceso 8 · Facturación**

| ¶ | Texto |
|---|---|
| 92 | Facturación recibe la solicitud. |
| 93 | Verifica los datos comerciales y fiscales correspondientes. |
| 94 | Verifica el pedido autorizado. |
| 95 | **Genera la factura.** |
| 96 | **Asocia la factura al pedido.** |
| 97 | **Se emite el documento fiscal correspondiente.** |
| 99 | Salida: **Pedido facturado**. |

El ¶95 y el ¶97 son **dos actos**, y esa separación no es cosmética: generar la factura es
comercial, emitir el documento fiscal es lo que consume correlativo y número de control.

## 2. Qué decide cada autoridad

| Pregunta del ciclo | Autoridad | Respuesta |
|---|---|---|
| §21 ¿Qué es *release*? | ¶83-84 · `ADR-D0-012` | Autorizar y **generar la solicitud de facturación**. El estado que la expresa es `READY_FOR_BILLING`, declarado por el ADR y que la Spec 033 dejó expresamente para esta |
| §22 ¿Qué estados? | `ADR-D0-012` | «`RESERVED → PREPARING → PREPARED → CONFIRMED → READY_FOR_BILLING → INVOICED → DISPATCHED → CLOSED`». Esta Spec añade los dos suyos y deja `DISPATCHED` para la 035 |
| §23 ¿De dónde sale la cantidad? | ¶93-95 · Spec 033 | De la **línea del pedido**, con su precio, descuento, presentación y factor congelados. La 033 ya probó que lo preparado coincide con lo pedido: si no, no habría `CONFIRMED` |
| §24 ¿Facturación parcial? | `B-007` · `ADR-D0-012` | **No.** «No se puede facturar dos veces la misma orden», y la máquina es lineal: un `INVOICED` |
| §25 ¿Cardinalidad? | `B-007` | **Una factura por pedido**, impuesto por índice único |
| §26 ¿Qué documento? | `FiscalDocument.document_type` | `INVOICE`, del catálogo fiscal; no se codifica la palabra |
| §27 ¿Quién numera? | Spec 042 · `reserve_number` | La serie fiscal, atómicamente. No hay contador propio |
| §28 ¿Número de control? | Spec 042 · `assign_control` / `use_control` | Del lote de control, atómicamente |
| §29 ¿Cuándo nace el documento fiscal? | ¶97 | Al emitir, no al generar la factura. `emit_document` consume las dos numeraciones en una transacción |
| §32-33 ¿Precios y descuentos? | Spec 029 | Los congelados en la línea del pedido. El maestro actual no reinterpreta una venta ya cerrada |
| §34-35 ¿Impuestos? | Spec 039 · `calculate_tax` | Regla **versionada y fechada**, con snapshot. Ni una tasa escrita en esta Spec |
| §19 ¿Cuentas por cobrar? | `FR-005-040` | `transition_invoice` a `EMITTED` **ya** crea el `OpenItem` de cobro. No se duplica |
| §41-42 ¿Unidad y presentación? | Spec 011 | `SalesInvoiceLine` ya conserva unidad, presentación, factor y cantidad base. Se copian, no se recalculan |

### Lo que el backlog fija como criterio de aceptación

- **`B-007`** (P0): «`SalesInvoice` sin `order_id`» → «factura trazable a su pedido; **migración
  aditiva con FK nullable**; nueva factura **exige orden**; **no se puede facturar dos veces la
  misma orden**».
- **`B-060`** (P0): «sin compuerta de liberación» → «**solo se factura un pedido `CONFIRMED`**;
  solicitud de facturación explícita; factura asociada al pedido; **imposible doble facturación**».

Eso es, literalmente, el alcance de este ciclo.

## 3. Lo que ya existe y no hay que construir

| Capacidad | Dueña | Estado |
|---|---|---|
| Factura y sus líneas, con unidad, presentación y factor congelados | Spec 005/011 | completas |
| Ciclo de vida de la factura `DRAFT → VALIDATED → APPROVED → EMITTED → …` | Spec 005 | completo |
| Cuenta por cobrar al emitir | Spec 005/037 | `transition_invoice` crea el `OpenItem` |
| Reglas de impuesto versionadas y fechadas | Spec 039 | `calculate_tax`, `TaxRuleVersion` |
| Series de numeración con reserva atómica | Spec 042 | `reserve_number` |
| Lotes y números de control | Spec 042 | `create_control_batch`, `assign_control`, `use_control` |
| Emisión fiscal atómica e idempotente | Spec 042 | `emit_document`, idempotente por `INVOICE:{id}` |
| Confirmación independiente y su compuerta | Spec 033 | `billing_eligibility` |

**Lo que falta es el gobierno**: hoy cualquiera puede crear una factura para un cliente sin pedido,
sin confirmación y dos veces.

## 4. Lo que este ciclo construye

1. `SalesInvoice.order_id` y `confirmation_id`, **nullable y aditivos** (`B-007`), con índice único
   parcial: un pedido, una factura viva.
2. `READY_FOR_BILLING` e `INVOICED` en la máquina del pedido, con sus sellos.
3. La solicitud de facturación: `CONFIRMED → READY_FOR_BILLING`, que exige confirmación vigente.
4. La generación de la factura desde las líneas del pedido, con su snapshot comercial completo.
5. La emisión, que consume la Spec 042 y lleva el pedido a `INVOICED`.

## 5. Fronteras

La 034 **no** recoge, no consolida, no verifica de nuevo, no toca inventario ni reserva, no despacha,
no calcula una tasa de impuesto por su cuenta, no lleva su propio correlativo y no construye un
segundo libro de cuentas por cobrar.

**Delta de inventario y de reserva esperado: 0.**

## 6. La desviación fiscal, dicha en voz alta

`D0-07` mantiene las Specs 039-043 en `BLOCKED_BY_LEGAL_VALIDATION`. El registro de bloqueos separa
las dos cosas: «arquitectura fiscal **construible**» frente a «**liberación legal**», y dice que
«039-043 pueden construirse; lo que no puede es **emitirse** sin confirmación normativa».

Este ciclo construye y prueba el camino completo contra el motor fiscal existente. **No afirma que
la emisión esté legalmente homologada**: eso sigue pendiente de `D0-07` y no es de esta Spec.

## 7. Fuera de alcance

Despacho y traslado (035) · notas de crédito y débito y correcciones post-emisión (036) · el ledger
de cuentas por cobrar (037) · retenciones (040) · IGTF (041) · libros y cierres (043) · facturación
parcial · edición de una factura emitida.
