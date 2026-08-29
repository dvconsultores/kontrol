# ADR-D0-009 — Unidad, presentación y conversión en toda transacción

| Campo | Valor |
|---|---|
| ID | D0-09 · Estado **APPROVED** · 2026-08-29 |
| Responsable | Arquitecto de datos · Supervisor de inventario · Gerente de compras · Gerente de ventas |
| Specs afectadas | **011** (propietaria) · 015-023, 025, 026, 029, 032, 034, 035, 036 |
| Riesgo histórico | **MÁXIMO** — ver `D0-historical-data-risk.md` |

## Problema

`units_of_measure`, `unit_conversions` y `presentations` existen como maestros. **Ninguna línea de
documento los referencia**: todas tienen solo `quantity`. La distinción entre producto base, unidad
de inventario, presentación de compra, de venta y de despacho existe en la configuración y
desaparece en la transacción.

## Por qué debe decidirse ahora

Es la deuda que más rápido se encarece. Una línea escrita hoy sin unidad es una línea que **nunca
podrá interpretarse con certeza**: si el factor de conversión del producto cambia mañana, no habrá
forma de saber qué significaba «10» en un documento de ayer. Ninguna migración futura repara eso,
porque la información no se perdió — nunca se capturó.

## Principio

```
Producto base ≠ unidad de inventario ≠ presentación de compra
              ≠ presentación de venta ≠ unidad de despacho
```

Ejemplo: **TORNILLO X** · base `UND` · compra `CAJA × 100` · venta `BOLSA × 20` · despacho en caja,
bolsa o unidad según el pedido.

## Regla definitiva

> **R-D0-09-1.** Toda línea transaccional relevante conserva: `item_id`, `uom_id`,
> `presentation_id` (cuando aplique), `quantity`, **`conversion_factor_snapshot`**,
> **`base_quantity`**, `price`, `currency`.
>
> **R-D0-09-2.** `base_quantity` se **calcula al escribir y se almacena**. Jamás se recalcula desde
> el maestro vigente. Reconstruir una transacción histórica no puede depender de la configuración
> actual del producto (P4, P5).
>
> **R-D0-09-3.** El inventario se lleva **siempre** en unidad base. La presentación es la forma en
> que se compra, se vende o se despacha; no es una unidad de existencia paralela.
>
> **R-D0-09-4.** Cambiar el factor de conversión de un producto **no** altera ningún documento
> emitido y **no** recalcula ningún saldo histórico.
>
> **R-D0-09-5.** Una conversión que no sea exacta en la unidad base (fracciones) debe declararse
> explícitamente en el producto. El sistema no redondea en silencio.

## Documentos alcanzados

Requisición · RFQ · oferta · orden de compra · expediente de importación · packing list ·
recepción · movimiento de inventario · transferencia · conteo · ajuste · cotización · pedido ·
picking · despacho · factura · nota de crédito y débito · devolución.

## Impacto

Frontend: selector de unidad y presentación en cada línea, con cantidad base visible · Backend:
resolución y congelado del factor al escribir · DB: **~4 columnas nuevas en ~15 tablas de línea** ·
QA: comprar en cajas y vender en unidades reproducible; cambio de factor no altera histórico ·
Fiscal: la base imponible se calcula sobre la presentación facturada, con su factor congelado.

## Migración

**`BACKFILL_REQUIRED`** con **`MANUAL_REVIEW_REQUIRED`**.

Las líneas existentes se rellenan con la unidad base del producto y `conversion_factor_snapshot = 1`,
marcadas `uom_source = LEGACY_ASSUMED_BASE`. **Es una suposición, y queda registrada como tal.**
Si alguna línea histórica se registró en una presentación distinta de la base, ese dato es
irrecuperable — razón por la que esta decisión no puede esperar.

## Criterios de aceptación

- [ ] Ninguna línea nueva puede escribirse sin `uom_id` y `base_quantity`.
- [ ] Comprar 5 cajas de 100 y vender 3 bolsas de 20 arroja el saldo base correcto (probado).
- [ ] Cambiar el factor del producto no altera documentos ni saldos anteriores (probado).
- [ ] Las líneas heredadas están marcadas y son distinguibles de las capturadas correctamente.

## Estado final

**APPROVED** — **CLOSED**. Prioridad de implementación por riesgo histórico, no por severidad nominal.
