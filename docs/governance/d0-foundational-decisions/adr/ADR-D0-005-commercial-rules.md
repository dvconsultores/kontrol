# ADR-D0-005 — Reglas comerciales: precios, descuentos, condiciones y crédito

| Campo | Valor |
|---|---|
| ID | D0-05 |
| Estado | **APPROVED** (arquitectura) · reglas de negocio pendientes de validación empresarial |
| Fecha | 2026-08-29 |
| Responsable | Arquitecto de datos · Gerente de ventas · Especialista de crédito · Product Owner |
| Specs afectadas | **012** (propietaria) · 009, 029, 030, 034, 036, 037 |

## Problema

`Customer.price_list`, `.zone`, `.payment_term` y `.salesperson` son `String(120)` de texto libre.
`SalesQuote.price_list` también. El descuento es un monto tecleado por línea. No hay maestro, no hay
regla, no hay vigencia y no hay fuente.

Esto contraviene directamente el **Principio 8** de la Constitución: *«No se hardcodean impuestos,
alícuotas, tasas, monedas, rubros, categorías, plazos fiscales, reglas regulatorias, permisos, roles,
estados transaccionales ni límites contratados. Todas las reglas críticas son versionadas y con fuente.»*

## Por qué debe decidirse ahora

Cada cotización y cada pedido que se emita con el modelo actual queda con un precio cuyo origen no
puede reconstruirse: no se sabe de qué lista salió, ni con qué vigencia, ni quién autorizó el
descuento. Es deuda que se encarece con cada documento emitido y que ninguna migración posterior
puede reparar.

## Evidencia

- `master_data/models.py:85-96` — `Customer` con cuatro campos comerciales de texto libre.
- `sales/models.py:33` — `SalesQuote.price_list` como texto.
- `sales/models.py:46,70` — `discount` como monto por línea, sin regla ni autorización.
- `docs/roadmap/spec-equivalence-map.md` — la Spec maestra 012 no tiene Spec actual equivalente.
- Vol. 1 §7 y Vol. 2 §1 — rama «Maestros / Comercial» exigida.

## Alternativas

**A. Convertir los campos de texto en catálogos simples (tablas de códigos).**
Barata. Descartada: resuelve la integridad referencial pero no el Principio 8 — seguiría sin
vigencia, sin regla de precedencia y sin snapshot. Sería un maestro sin motor.

**B. Motor de reglas de precio versionado con snapshot obligatorio.** ← **RECOMENDADA**
Cumple P8, permite reconstruir cualquier documento histórico y admite la complejidad real
(volumen, segmento, presentación) sin rediseño.

**C. Motor de reglas genérico y configurable por expresión.**
Máxima flexibilidad. Descartada por ahora: un motor de expresiones arbitrarias es difícil de
auditar y de explicar a un contador. La precedencia declarativa cubre el caso real y es verificable.

## Modelo conceptual

```
PriceList (empresa · moneda · vigencia · segmento · versión · estado)
 └── PriceListItem (producto | categoría · presentación · rango de volumen · precio)

PriceRule        (condición → efecto sobre el precio · precedencia · vigencia)
DiscountPolicy   (ámbito · límite · requiere aprobación · acumulable · incompatibilidades)
PaymentTerm      (código · descripción · cuotas · días · % anticipo)
CreditPolicy     (límite · exposición · bloqueo · excepción)
CommercialZone   (zona · ruta · vendedor asignado)
SalesCommissionPolicy + CommissionRule   → FUTURE CAPABILITY
```

## Precedencia de precio

> **R-D0-05-1.** La precedencia es **declarativa, versionada y configurable por empresa**. No está
> codificada en el software.

KONTROL entrega un **orden por defecto documentado**, que cada empresa puede reordenar:

1. Precio contractual del cliente
2. Lista específica del cliente
3. Lista del segmento del cliente
4. Lista de la sucursal
5. Lista general de la empresa

> **R-D0-05-2.** Cuando dos reglas de la misma precedencia son aplicables, la resolución es
> **determinista y explícita** (la de vigencia más reciente; y a igualdad, la de menor precio).
> Un empate no resuelto es un error de configuración que el sistema debe reportar, no resolver al azar.

Este orden por defecto es una **propuesta que requiere confirmación** — ver OQ-06.

## Descuentos

| Aspecto | Decisión de producto |
|---|---|
| Ámbito | Existen descuento **de línea** y descuento **de documento**, y son entidades distintas |
| Límite | `DiscountPolicy` define el máximo permitido por rol, producto o categoría |
| Autorización | Superar el límite genera `ApprovalRequest` (ADR-D0-002) — no se bloquea, se aprueba |
| Acumulación | Configurable: acumulable o excluyente; las incompatibilidades se declaran |
| Registro | Todo descuento guarda la política y el nivel de autorización aplicados |

**No se define ningún porcentaje máximo.** Ver OQ-06.

## Condiciones de pago y crédito

> **R-D0-05-3.** `PaymentTerm` es un maestro, nunca una cadena. Sus valores (contado, 15/30/45 días,
> anticipo parcial, cuotas) son **datos de cada empresa**, no alternativas del producto.
>
> **R-D0-05-4.** Condición de pago y política de crédito son **cosas distintas**: la condición
> describe *cuándo se paga*; la política describe *cuánto riesgo se admite*. Un cliente de contado
> puede tener límite de crédito cero y seguir teniendo política; un cliente a 30 días puede estar
> bloqueado por exposición.

## Comisiones

**FUTURE CAPABILITY.** El modelo reserva `SalesCommissionPolicy` y `CommissionRule` para que su
incorporación no exija rediseño, pero **la Spec 012 no está obligada a implementarlas**.
No se inventa ninguna regla de comisión. Ver OQ-06.

## Snapshot comercial

> **R-D0-05-5.** Al aprobarse un documento transaccional, éste conserva: precio unitario, descuento
> aplicado, política de descuento y versión, condición de pago, moneda, tasa de cambio, **y el
> identificador de la versión de lista o regla que produjo el precio**.
>
> **R-D0-05-6.** Modificar un maestro comercial **nunca** altera un documento ya aprobado. La
> reconstrucción histórica se hace desde el snapshot, jamás recalculando contra el maestro vigente.

## Impacto

| Dimensión | Impacto |
|---|---|
| Frontend | Rama de menú «Maestros / Comercial» completa; precio automático en cotización; solicitud de aprobación al exceder descuento |
| Backend | Módulo nuevo `commercial`; `sales` deja de aceptar precio libre sin justificación |
| Base de datos | ~9 tablas nuevas; 4 columnas de texto de `customers` migran a FK |
| Integraciones | Ninguna |
| QA | Resolución de precedencia; empates; snapshot inmutable ante cambio del maestro |
| Seguridad | El límite de descuento se valida en backend (P6) |
| Fiscal | Indirecto: el precio y el descuento forman la base imponible |

## Migración / compatibilidad

**`BACKFILL_REQUIRED`** con **`MANUAL_REVIEW_REQUIRED`**.

Los valores de texto existentes (`price_list`, `zone`, `payment_term`) se extraen a catálogos
preservando la cadena original en un campo `legacy_value`. Los documentos históricos **no reciben
snapshot inventado**: se marcan `pricing_source = LEGACY_FREETEXT`. No se puede reconstruir lo que
nunca se registró, y fingir lo contrario sería peor que admitirlo.

## Criterios de aceptación

- [ ] Ningún campo comercial es texto libre en documentos nuevos.
- [ ] El precio de una cotización procede de una lista o regla identificable.
- [ ] Cambiar la lista no altera cotizaciones ya aprobadas (probado).
- [ ] Exceder el límite de descuento genera solicitud de aprobación, no un bloqueo.
- [ ] Un empate de precedencia se reporta como error de configuración.
- [ ] La precedencia es dato, no código.

## Preguntas pendientes

**BUSINESS_VALIDATION_REQUIRED** — OQ-06: confirmación del orden de precedencia, límites de
descuento por rol, alcance de comisiones, política de crédito.

## Estado final

**APPROVED** — arquitectura cerrada.
Clasificación de cierre: **CLOSED_WITH_CONFIGURATION_PENDING**.
