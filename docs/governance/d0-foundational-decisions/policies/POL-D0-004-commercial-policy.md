# POL-D0-004 — Política comercial

> Deriva de `ADR-D0-005`. Vinculante para las Specs 012, 029, 030, 034, 036, 037.

## 1. Prohibición

Ningún dato comercial puede ser texto libre en un documento transaccional: lista de precios, zona,
ruta, condición de pago, política de crédito y política de descuento son **maestros con FK**.

## 2. Maestros

`PriceList` · `PriceListItem` · `PriceRule` · `DiscountPolicy` · `PaymentTerm` · `CreditPolicy` ·
`CommercialZone` · (`SalesCommissionPolicy` y `CommissionRule` → capacidad futura).

Toda lista y toda regla llevan **vigencia, versión, estado y empresa**.

## 3. Precedencia de precio

Declarativa, versionada y configurable. Orden **por defecto** que KONTROL entrega y cada empresa
puede reordenar:

1. Precio contractual del cliente
2. Lista específica del cliente
3. Lista del segmento
4. Lista de la sucursal
5. Lista general

Un empate de precedencia se resuelve por vigencia más reciente y, a igualdad, por menor precio.
Un empate irresoluble se **reporta como error de configuración**; no se resuelve al azar.

## 4. Descuentos

| Regla | Definición |
|---|---|
| Ámbito | Descuento de línea y descuento de documento son entidades distintas |
| Límite | `DiscountPolicy` fija el máximo por rol, producto o categoría |
| Exceso | Genera `ApprovalRequest` (POL-D0-001). **No se bloquea: se aprueba** |
| Acumulación | Configurable; las incompatibilidades se declaran explícitamente |
| Registro | Se guarda la política, la versión y el nivel de autorización aplicados |

**KONTROL no define ningún porcentaje máximo.**

## 5. Condición de pago frente a crédito

Son cosas distintas y no se sustituyen. La condición describe **cuándo se paga**; la política de
crédito describe **cuánto riesgo se admite**. Un cliente de contado puede tener política de crédito;
un cliente a plazo puede estar bloqueado por exposición.

## 6. Snapshot obligatorio

Al aprobarse un documento se congelan: precio unitario · descuento · política y versión de descuento ·
condición de pago · moneda · tasa de cambio · **identificador de la lista o regla que produjo el precio**.

Modificar un maestro **nunca** altera un documento aprobado. La reconstrucción histórica se hace
desde el snapshot, jamás recalculando contra el maestro vigente.

## 7. Pendiente

**BUSINESS_VALIDATION_REQUIRED** — OQ-06: confirmación de la precedencia, límites de descuento,
alcance de comisiones, parámetros de crédito.
