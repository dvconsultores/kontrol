# POL-D0-002 — Política de reserva de inventario

> Deriva de `ADR-D0-003`. Vinculante para las Specs 023, 029, 030, 031, 032, 034, 035.

## 1. Definiciones

| Término | Significado |
|---|---|
| Físico | Unidades presentes en el almacén, cualquiera sea su estado |
| Reservado | Unidades comprometidas a un documento y no consumidas |
| Bloqueado | Unidades retenidas por incidencia, cuarentena o disputa |
| **Disponible** | `físico − reservado − bloqueado` |

Ningún proceso, pantalla o consulta puede presentar el físico como disponible.

## 2. Disparador

`reservation_trigger` por empresa ∈ `{ORDER_RELEASED (defecto), ORDER_CREATED, CREDIT_APPROVED, QUOTE_APPROVED, MANUAL}`.

Justificación del defecto: `ORDER_RELEASED` es el primer punto de la cadena con compromiso comercial
formal y documento no editable.

## 3. Concurrencia — regla dura

Dos operaciones **no pueden** reservar la misma unidad. La garantía es de base de datos dentro de la
transacción: bloqueo de la fila de saldo más restricción que impide `reservado > físico`.
El frontend no es autoridad sobre disponibilidad.

Debe existir prueba automatizada sobre PostgreSQL de dos transacciones concurrentes sobre la última
unidad, con exactamente una ganadora.

## 4. Vigencia

Toda reserva expira. La duración es configuración por empresa. Al expirar se libera automáticamente
y el evento queda auditado. La renovación es explícita y auditada.

## 5. Dimensión

La reserva se hace a la mínima dimensión conocida: almacén, y además lote, serial o ubicación cuando
el producto o el pedido lo determinen. Una reserva sin dimensión suficiente no puede consumirse en
picking dirigido.

## 6. Consumo y liberación

| Evento | Efecto |
|---|---|
| Despacho (salida física) | Consume la reserva |
| Facturación | **No** consume reserva ni mueve inventario |
| Cancelación del pedido | Libera |
| Expiración | Libera |
| Picking parcial | Libera la diferencia y **genera incidencia** — nunca ajusta el pedido en silencio |

## 7. Capacidades futuras

Backorder · sustitución de producto · prioridad entre pedidos · reserva sobre mercancía en tránsito.
El modelo debe admitirlas; la Spec 030 no está obligada a implementarlas.

## 8. Pendiente

**BUSINESS_VALIDATION_REQUIRED** — OQ-03: disparador elegido, duración de vigencia, prioridad.
