# POL-D0-001 — Política de aprobaciones

> Deriva de `ADR-D0-002`. Vinculante para toda Spec que implemente una aprobación.

## 1. Alcance

Toda operación que requiera autorización de un tercero pasa por el motor único. Ningún módulo
implementa aprobación propia.

Procesos alcanzados: requisición · orden de compra · importación · recepción con desviación ·
factura de proveedor fuera de tolerancia · pago · descuento sobre límite · crédito y excepción de
crédito · ajuste de inventario · transferencia · devolución · nota de crédito y débito · anulación
de documento fiscal · reapertura de período fiscal · contingencia de facturación · override
regulatorio.

## 2. Qué define KONTROL

| Elemento | Definición de producto |
|---|---|
| Existencia del motor | Único y transversal |
| Entidades | `ApprovalPolicy`, `ApprovalRule`, `ApprovalLevel`, `ApprovalRequest`, `ApprovalStep`, `ApprovalDecision`, `ApprovalDelegation` |
| Versionado | Toda política se versiona; la solicitud congela la versión aplicada |
| Dimensiones de condición | Empresa, proceso, monto en moneda base, porcentaje, sucursal, centro de costo, almacén, rol, usuario, categoría, riesgo, condición comercial, marca de excepción |
| Estados | `DRAFT → PENDING → IN_REVIEW → {APPROVED, REJECTED, RETURNED, CANCELLED, OBSOLETE}` |
| Cuórum | Cualquiera · todos · N de M |
| Segregación | Configurable; cuando está activa, el creador no resuelve |
| Delegación | Acotada en ámbito y vigencia, revocable, auditada, no elude la segregación |
| Obsolescencia | Automática si cambia un campo que participa en la condición |
| Auditoría | Toda decisión con actor, momento, motivo y delegación de origen |

## 3. Qué configura cada empresa

Número de niveles por proceso · umbrales de monto · resolutor de cada nivel · si exige segregación ·
vencimiento de cada paso · delegaciones vigentes · qué dimensiones usa realmente.

**Ejemplo estrictamente ilustrativo, sin valores reales:**

```
Proceso: ORDEN_DE_COMPRA
  Nivel 1  hasta  <umbral_1>     → <rol_A>
  Nivel 2  de <umbral_1> a <umbral_2> → <rol_B>
  Nivel 3  sobre <umbral_2>      → <rol_C>
```

Los umbrales y los roles **no se definen en esta política**. Los define cada cliente al implantar.

## 4. Reglas de operación

1. El monto se evalúa sobre el equivalente en moneda base con la tasa snapshot del documento.
2. Un documento sin solicitud resuelta no avanza a su siguiente estado.
3. El rechazo devuelve el documento a estado editable y es terminal para esa solicitud.
4. `RETURNED` conserva el historial y permite corregir sin perder las decisiones previas.
5. Una solicitud `OBSOLETE` no puede aprobarse; debe volver a solicitarse.
6. Aprobar sin permiso sobre el nivel es imposible; la verificación es de backend (P6).
7. Las políticas no se borran: se cierran por vigencia.

## 5. Pendiente

**BUSINESS_VALIDATION_REQUIRED** — OQ-02. No impide construir el motor.
