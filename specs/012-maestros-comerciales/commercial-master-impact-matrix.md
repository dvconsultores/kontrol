# MATRIZ DE IMPACTO DE LOS MAESTROS COMERCIALES — SPEC 012

**Obligatoria.** Existe para demostrar que 012 es una autoridad transversal y no
un CRUD con cinco pantallas. Construida leyendo el código, no los nombres.

## 1. Quién consume qué

| Spec | Qué necesita de 012 | Contrato | ¿Bloqueada hoy? |
|---|---|---|---|
| **029 · Pedido comercial** | Precio desde el maestro, condición, zona, canal, validación de descuento | `resolve_price`, `validar_descuento` | **Sí** — hoy el precio se teclea |
| **030 · Crédito, aprobación y reserva** | `CreditPolicy` y condición del cliente | Contrato de crédito | **Sí** — hoy `credit_limit` es un número suelto sin política |
| **034 · Facturación** | Snapshot comercial congelado para reimprimir con fidelidad | Columnas de snapshot | **Sí** para la reimpresión explicable |
| **036 · Devoluciones, NC y ND** | Precio y condición del documento original | Snapshot | Parcial — puede heredar la línea |
| **037 · Cuentas por cobrar** | Condición de pago para calcular vencimientos | `PaymentTerm` estructurado | **Sí** — hoy «30 días» es texto |
| **009 · Terceros** | Referencias en lugar de texto libre | FK en `customer_commercial_terms` | No bloquea: 009 opera hoy |
| **016 · RFQ y ofertas** | Condición de pago del proveedor | `PaymentTerm` compartido | Parcial |
| **028 · Cuentas por pagar y pagos** | Condición del proveedor para programar pagos | ídem | Parcial |

### Recuento

| ¿012 bloquea? | Specs |
|---|---|
| **Sí** | **029, 030, 034, 037** — 4 |
| Parcial | 016, 028, 036 — 3 |
| No | 009 — 1 |

## 2. Qué gobierna cada parte

| 012 gobierna | El consumidor gobierna |
|---|---|
| Cuánto vale una línea y por qué | Si esa línea se emite |
| El límite de descuento | Si se pide la aprobación |
| La estructura de la condición de pago | Cuándo vence de verdad el documento |
| La política de crédito | La exposición en tiempo real |
| La zona y el canal | Qué hace el proceso con ellos |

012 **no** decide que una cotización deba aprobarse. Provee el dato con el que
029 lo decide.

## 3. Frontera con las Specs ya cerradas

| Spec cerrada | Frontera |
|---|---|
| **011 · Unidades** | 012 **usa** su motor de conversión; no crea otro. El precio se declara sobre presentación y se convierte con `uom.py` |
| **045 · Aprobaciones** | 012 **consume** el motor cuando se excede un descuento. No construye una segunda vía |
| **046 · Documental** | Un contrato de precio pactado podría adjuntarse con `link(...)`. 012 no guarda archivos |
| **008 · Almacenes** | **Ninguna.** `CommercialZone` ≠ `WarehouseZone`. Sin FK, sin vista común |

## 4. Columnas que dejan de ser texto libre

| Tabla | Columna | Pasa a | El texto original |
|---|---|---|---|
| `customers` | `price_list` | FK → `price_lists` | se conserva en `legacy_price_list` |
| `customers` | `payment_term` | FK → `payment_terms` | `legacy_payment_term` |
| `customers` | `zone` | FK → `commercial_zones` | `legacy_zone` |
| `customers` | `salesperson` | FK → `users` | `legacy_salesperson` |
| `suppliers` | `payment_term` | FK → `payment_terms` | `legacy_payment_term` |
| `sales_quotes` | `price_list` | FK → `price_list_versions` | `legacy_price_list` |

**Ninguna se borra.** Es la misma decisión que 046 tomó con las 12 columnas
documentales heredadas.

## 5. Lo que 012 deja explícitamente fuera

| Spec | Motivo |
|---|---|
| **Comisiones** | `FUTURE CAPABILITY` en `ADR-D0-005`. El modelo reserva el hueco; la Spec no lo llena |
| **Promociones y campañas** | Alternativa C descartada en el ADR |
| **Precio de compra negociado** | Es de 016 |
| **Exposición crediticia** | Es de 030 |
