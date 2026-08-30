# INVESTIGACIÓN — SPEC 012

Todo lo que sigue se midió sobre el código y la base, no se supuso.

## 1. Inventario del código — 2026-08-30

### Campos comerciales existentes

| Tabla | Columna | Tipo | Naturaleza |
|---|---|---|---|
| `customers` | `price_list` | `String(120)` | texto libre |
| `customers` | `payment_term` | `String(120)` | texto libre |
| `customers` | `zone` | `String(120)` | texto libre |
| `customers` | `salesperson` | `String(200)` | texto libre |
| `customers` | `credit_days` | `Integer` | dato suelto, sin política |
| `customers` | `credit_limit` | `Numeric(18,2)` | dato suelto, sin política |
| `customers` | `blocked` / `block_reason` | `Boolean` / `String(255)` | bloqueo sin trazabilidad de autor |
| `suppliers` | `payment_term` | `String(120)` | texto libre |
| `suppliers` | `category`, `buyer`, `withholding_profile` | `String` | texto libre |
| `sales_quotes` | `price_list` | `String(120)` | texto libre |
| `sales_quote_lines` | `unit_price`, `discount` | `Numeric(18,2)` | tecleados, sin origen |
| `sales_order_lines` | `unit_price`, `discount` | `Numeric(18,2)` | tecleados, sin origen |
| `purchase_*_lines` | `discount` | `Numeric(18,2)` | tecleado |

### Lo que no existe

Ni una tabla de: `price_lists`, `price_list_versions`, `price_list_items`,
`price_rules`, `payment_terms`, `commercial_zones`, `sales_channels`,
`discount_policies`, `credit_policies`, `commission_*`.

### Comprobaciones que sí salieron bien

| Comprobación | Resultado |
|---|---|
| `price_1`..`price_5` o `precio_N` | **0 apariciones**. El antipatrón clásico no está |
| `treasury.commission` | Es una **comisión bancaria** sobre `treasury_transfers`, no comisión de ventas. No confundir |
| Maestro monetario | `currencies` y `exchange_rates` ya existen y son reutilizables |
| Método de pago | `payment_methods` existe y es **distinto** de condición de pago |

## 2. Volumen de datos legados

Medido sobre una instalación recién inicializada (`kontrol_e2e`):

| Columna | Filas no vacías |
|---|---:|
| `customers.price_list` | 0 |
| `customers.payment_term` | 0 |
| `customers.zone` | 0 |
| `customers.salesperson` | 0 |
| `suppliers.payment_term` | 0 |
| `sales_quotes.price_list` | 0 |

**Cero en este entorno.** Eso no significa cero en producción: la migración debe
medir sobre la instalación real y reportar, no asumir. Es exactamente lo que
hizo `0024` en la Spec 046.

## 3. Lecciones aplicables de las Specs ya cerradas

| Spec | Lección | Cómo se aplica en 012 |
|---|---|---|
| **011 Unidades** | El dato no se pierde: **nunca se captura**. `Float` en magnitudes fue un error caro | Todo importe en `Numeric`; el origen del precio se captura al emitir (`P23`) |
| **011** | Congelar el factor en la línea permite reimprimir sin consultar el maestro | Congelar la **versión de lista** permite explicar el precio sin consultar el maestro |
| **046 Documental** | Anotar el legado ≠ convertirlo. Un texto suelto no basta para afirmar un hecho | «30 días» no se convierte solo; se anota y se revisa (`FR-012-081`) |
| **046** | Los catálogos **nacen vacíos** y eso es una funcionalidad, no una carencia | Ningún plazo ni porcentaje de fábrica |
| **046** | Registro **cerrado** mejor que polimorfismo libre | La precedencia es una lista declarada, no una expresión arbitraria |
| **045 Aprobaciones** | Una sola autoridad transversal; nadie construye la suya | El descuento excesivo va al motor 045, no a una aprobación propia |
| **008 Almacenes** | Una jerarquía opcional se declara por entidad, no se impone | La precedencia se declara por empresa, no se impone |

## 4. Por qué no un motor de expresiones

`ADR-D0-005` descartó la alternativa C. La investigación lo confirma: un motor de
expresiones arbitrarias es difícil de auditar y **imposible de explicar a un
contador**. La precedencia declarativa cubre el caso real venezolano —lista por
cliente, por segmento, por sucursal, general— y es verificable línea a línea.

## 5. Riesgo de confusión detectado

`WarehouseZone` (Spec 008, **implementada**) y `CommercialZone` (esta Spec)
comparten la palabra «zona». La Spec 008 dejó `warehouse_zones` con
`zone_type_id`, pasillo, rack y nivel: es geometría de almacén.

Reutilizarla para territorio de ventas produciría un modelo donde un vendedor
tiene pasillo. Se declara explícitamente prohibido (`FR-012-041`).
