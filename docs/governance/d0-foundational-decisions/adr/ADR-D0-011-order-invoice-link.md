# ADR-D0-011 — Vínculo estructural entre pedido y factura

| Campo | Valor |
|---|---|
| ID | D0-11 · Estado **APPROVED** · 2026-08-29 |
| Responsable | Arquitecto de datos · Auditor interno · Contador público · Gerente de ventas |
| Specs afectadas | **034** (propietaria) · 029, 030, 033, 035, 036, 037, 042 |
| Riesgo histórico | **ALTO** |

## Problema

`SalesInvoice` (`sales/models.py:123`) no tiene `order_id`, ni vínculo a despacho, ni a picking.
Sus líneas tampoco referencian líneas de pedido. La factura de venta es un documento suelto.

La asimetría es reveladora: la cadena de compras **sí** está trazada
(`SupplierInvoiceLine.order_line_id`, `.receipt_line_id`, tabla `triple_matches`). Mismo equipo,
mismo patrón, resultado opuesto. Es omisión, no diseño.

## Consecuencias verificables hoy

Nada impide facturar dos veces el mismo pedido · nada impide facturar cantidades superiores a las
pedidas · nada impide facturar un pedido nunca preparado ni confirmado · no se puede responder
«¿qué pedido facturó esta factura?» desde la base de datos.

## Decisión

> **R-D0-11-1.** `SalesInvoice.order_id` es **nullable a nivel de esquema** y
> **obligatorio a nivel de regla** cuando la factura deriva de un pedido.
>
> **R-D0-11-2.** `SalesInvoiceLine.order_line_id` es igualmente nullable en el esquema y obligatorio
> cuando la línea deriva de una línea de pedido. Sin el vínculo a nivel de línea no puede controlarse
> la cantidad facturada.
>
> **R-D0-11-3.** **Facturación directa**: sigue existiendo como caso legítimo (venta de mostrador,
> servicio sin pedido previo). Requiere permiso explícito y una política de empresa que la habilite,
> y la factura se marca `origin = DIRECT`. No es el modo por defecto ni un atajo del operador.
>
> **R-D0-11-4.** **Control de cantidad**: la suma facturada por línea de pedido no puede exceder la
> cantidad autorizada. El límite es la cantidad **confirmada** cuando la empresa exige confirmación
> (ADR-D0-012), y la cantidad pedida cuando no.
>
> **R-D0-11-5.** El control se implementa en la **base de datos y la transacción**, no solo en el
> servicio: la validación debe resistir dos solicitudes concurrentes de facturación del mismo pedido.
>
> **R-D0-11-6.** Anular una factura devuelve la cantidad al saldo facturable del pedido. Una nota de
> crédito **no** lo hace: la nota corrige el efecto económico, no reabre el derecho a facturar
> (regla del Vol. 1 §5: «la devolución física no sustituye una nota de crédito»).

## Impacto

Frontend: la factura muestra su pedido; facturar desde el pedido con cantidades pendientes ·
Backend: `sales` valida origen y cantidades · DB: 2 FK nuevas + índice · QA: doble facturación
concurrente, exceso de cantidad, anulación vs. nota · Fiscal: mejora la trazabilidad exigible en
fiscalización.

## Migración

**`BACKFILL_REQUIRED`** con **`DATA_LOSS_RISK`** ya materializado.

Las facturas existentes quedan con `order_id = NULL` y `origin = LEGACY_UNLINKED`. **El vínculo no
puede reconstruirse**: nunca se registró. Cada factura emitida desde hoy hasta que se aplique esta
decisión engrosa ese conjunto irrecuperable — motivo por el cual la FK se adelanta a la **Ola 0**
del roadmap, antes que el resto de la Spec 034.

## Criterios de aceptación

- [ ] Una factura derivada de pedido no puede guardarse sin vínculo.
- [ ] Facturar dos veces el mismo pedido es imposible, incluso concurrentemente (probado).
- [ ] Facturar más de lo autorizado es imposible (probado).
- [ ] La factura directa exige permiso y política, y queda marcada.
- [ ] Anular devuelve saldo facturable; la nota de crédito no.

## Estado final

**APPROVED** — **CLOSED**.
