# ADR-D0-010 — Estados de mercancía y su separación del estado del documento

| Campo | Valor |
|---|---|
| ID | D0-10 · Estado **APPROVED** · 2026-08-29 |
| Responsable | Arquitecto de procesos · Supervisor de almacén · Auditor interno |
| Specs afectadas | **021, 023** · 019, 020, 022, 024, 025, 030, 031, 032, 035, 036 |

## Problema

El motor de inventario ya tiene una máquina de estados (`inventory/service.py:102`):
`DISPONIBLE → {RESERVADO, TRANSITO, CUARENTENA}` etc. Pero el flujo de recepción **no la usa**:
`accept_receipt` escribe directamente en `DISPONIBLE`. Faltan los estados que el proceso documentado
exige entre la llegada y la disponibilidad: recibido, pendiente de validación, bloqueado por incidencia.

## Principio central

> **R-D0-10-1.** El estado del **documento** y el estado de la **mercancía** son dimensiones
> independientes y no se derivan uno del otro.

Una `GoodsReceipt` en estado `CONFIRMED` **no** implica que su mercancía esté `DISPONIBLE`. Puede
existir una recepción confirmada cuya mercancía está en cuarentena esperando conteo, o bloqueada por
una incidencia abierta. Confundir ambas dimensiones es el origen del salto que hoy lleva la
recepción directamente a stock disponible.

## Decisión sobre el vocabulario

El conjunto actual está en español y **ya está persistido** en `inventory_balances.state`. Renombrar
a inglés exigiría migrar datos vivos sin ganancia funcional.

> **R-D0-10-2.** Se **extiende** el conjunto existente en español en lugar de renombrarlo. La
> coherencia con los datos ya escritos pesa más que la uniformidad idiomática con el resto del código.
> Si la internacionalización llega a ser requisito, se abordará como cambio propio, con su migración.

## Conjunto de estados de mercancía

| Estado | Significado | Disponible para venta |
|---|---|---|
| `ESPERADO` | Comprometido en orden o embarque; aún no llegó | No · **FUTURE** (Spec 018) |
| `RECIBIDO` | **Nuevo.** Físicamente recibido, aún no conciliado | No |
| `PENDIENTE_CONFIRMACION` | **Nuevo.** En conteo o conciliación | No |
| `CUARENTENA` | Retenido por calidad o inspección | No |
| `BLOQUEADO` | **Nuevo.** Retenido por incidencia abierta o disputa | No |
| `DISPONIBLE` | Liberado formalmente | **Sí** |
| `RESERVADO` | Comprometido a un pedido | No |
| `PICKING` | **Nuevo.** En proceso de extracción | No |
| `PREPARADO` | **Nuevo.** Extraído y consolidado, pendiente de confirmación | No |
| `TRANSITO` | En traslado entre almacenes | No |
| `DESPACHADO` | **Nuevo.** Salió físicamente | No (fuera de existencia) |
| `DEVUELTO` | **Nuevo.** Reingresado, pendiente de inspección | No |
| `RECHAZADO` | No apto; no se incorpora | No |
| `DESECHO` | Destruido o descartado | No |
| `VENDIDO` | Consumido por venta | No |

Estados existentes conservados: `DISPONIBLE`, `RESERVADO`, `TRANSITO`, `CUARENTENA`, `RECHAZADO`,
`DESECHO`, `VENDIDO`. Estados nuevos: 7.

## Reglas

| ID | Regla |
|---|---|
| R-D0-10-3 | `disponible para venta` es **exclusivamente** `DISPONIBLE`. Ningún otro estado se ofrece al vendedor. |
| R-D0-10-4 | El paso a `DISPONIBLE` desde la cadena de recepción exige **liberación formal** (Spec 021). No es automático. |
| R-D0-10-5 | Toda transición de estado es un **movimiento de inventario**, no una edición de campo. El saldo se reconstruye desde movimientos (P5). |
| R-D0-10-6 | `BLOQUEADO` solo se libera cerrando la incidencia que lo originó. |
| R-D0-10-7 | Las transiciones no declaradas están prohibidas; el motor las rechaza. |
| R-D0-10-8 | `ESPERADO` no computa como existencia física en ningún saldo ni valoración. |

## Impacto

Frontend: el estado de mercancía debe ser visible y filtrable en existencias · Backend: máquina de
estados ampliada; recepción y picking dejan de escribir `DISPONIBLE` directamente · DB: sin tablas
nuevas; valores nuevos en `state` · QA: cada transición y cada prohibición · Fiscal: la mercancía en
cuarentena sigue siendo del inventario a efectos de valoración; la despachada no.

## Migración

**`SAFE_MIGRATION`** — los valores nuevos son aditivos. Los saldos existentes conservan su estado.
El cambio de comportamiento (recepción ya no salta a `DISPONIBLE`) llega con la Spec 021, no con esta decisión.

## Criterios de aceptación

- [ ] Existe una recepción confirmada con mercancía en cuarentena (probado).
- [ ] Un saldo `BLOQUEADO` no aparece como disponible en la consulta del vendedor.
- [ ] Toda transición genera movimiento y es reconstruible.
- [ ] Una transición no declarada se rechaza.

## Estado final

**APPROVED** — **CLOSED**.
