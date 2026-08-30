# MATRIZ DE IMPACTO TRANSACCIONAL — SPEC 011

**Obligatoria (§100).** Existe para impedir que se repita el patrón que motivó
esta Spec: *el maestro existe y la transacción lo ignora.*

Construida leyendo el código real, no los nombres. Fecha: 2026-08-30.

---

## 1. Hallazgo de partida

| Métrica | Valor |
|---|---:|
| Tablas con columna de cantidad | **23** |
| De ellas, líneas de documento transaccional | **21** |
| Que conservan `uom_id` | **2** (`inventory_movements`, `purchase_requisition_lines`) — ambas *nullable* |
| Que conservan `presentation_id` | **0** |
| Que conservan factor de conversión | **0** |
| Que conservan cantidad base | **0** |
| Columnas de cantidad o factor en `Float` | **31** |
| Columnas de cantidad o factor en `Numeric` | **0** |

`sales_invoice_lines.base_fiscal` **no** es cantidad base: es base imponible en
moneda. No hay una sola cantidad base en el esquema.

De las dos columnas `unit_id` existentes, **ninguna se escribe nunca**:
`inventory/service.py:382` pasa `unit_id=None` de forma literal, y la de
requisiciones solo se rellena si el cliente la envía.

---

## 2. Clasificación de impacto (§38)

| # | Dominio | Documento | Tabla de línea | Hoy guarda UOM | Cambio 011 | Migración | Spec propietaria | Clase |
|---|---|---|---|---|---|---|---|---|
| 1 | Inventario | Movimiento | `inventory_movements` | `unit_id` nullable, nunca escrito | 4 columnas + `NOT NULL` progresivo | `BACKFILL` | 023 | **MUST_HAVE_NOW** |
| 2 | Inventario | Saldo | `inventory_balances` | No | Ninguno: es **proyección** en unidad base | — | 023 | **NOT_APPLICABLE** |
| 3 | Inventario | Reserva | `reservations` | No | 4 columnas | `BACKFILL` | 003/023 | **MUST_HAVE_NOW** |
| 4 | Inventario | Transferencia | `transfer_lines` | No | 4 columnas | `BACKFILL` | 025 | **MUST_HAVE_NOW** |
| 5 | Inventario | Conteo | `stock_count_lines` | No | 4 columnas | `BACKFILL` | 025 | **MUST_HAVE_NOW** |
| 6 | Inventario | Ajuste | `inventory_adjustments` | No | 4 columnas | `BACKFILL` | 025 | **MUST_HAVE_NOW** |
| 7 | Inventario | Capa de costo | `cost_layers` | No | Ninguno: deriva del movimiento, siempre en base | — | 026 | **NOT_APPLICABLE** |
| 8 | Compras | Requisición | `purchase_requisition_lines` | `unit_id` nullable | 4 columnas; `unit_id` pasa a obligatorio | `BACKFILL` | 015 | **MUST_HAVE_NOW** |
| 9 | Compras | Oferta de proveedor | `supplier_quote_lines` | No | 4 columnas | `BACKFILL` | 016 | **MUST_HAVE_NOW** |
| 10 | Compras | Orden de compra | `purchase_order_lines` | No | 4 columnas ×2 cantidades | `BACKFILL` | 017 | **MUST_HAVE_NOW** |
| 11 | Compras | Recepción | `goods_receipt_lines` | No | 4 columnas ×3 cantidades | `BACKFILL` | 019 | **MUST_HAVE_NOW** |
| 12 | Compras | Factura de proveedor | `supplier_invoice_lines` | No | 4 columnas | `BACKFILL` + **revisión fiscal** | 027 | **MUST_HAVE_NOW** |
| 13 | Compras | Conciliación triple | `triple_matches` | No | Ninguno: compara cantidades ya base | — | 027 | **NOT_APPLICABLE** |
| 14 | Compras | Devolución | `purchase_return_lines` | No | 4 columnas | `BACKFILL` | 036 | **MUST_HAVE_NOW** |
| 15 | Ventas | Cotización | `sales_quote_lines` | No | 4 columnas | `BACKFILL` | 028 | **MUST_HAVE_NOW** |
| 16 | Ventas | Pedido | `sales_order_lines` | No | 4 columnas | `BACKFILL` | 029 | **MUST_HAVE_NOW** |
| 17 | Ventas | Picking | `pick_list_lines` | No | 4 columnas + unidad física de picking | `BACKFILL` | 032 | **MUST_HAVE_NOW** |
| 18 | Ventas | Despacho | `shipment_lines` | No | 4 columnas + contrato de empaque | `BACKFILL` | 035 | **MUST_HAVE_NOW** |
| 19 | Ventas | Factura | `sales_invoice_lines` | No | 4 columnas | `BACKFILL` + **revisión fiscal** | 034 | **MUST_HAVE_NOW** |
| 20 | Ventas | Devolución / NC | `sales_return_lines` | No | 4 columnas | `BACKFILL` | 036 | **MUST_HAVE_NOW** |
| 21 | Regulatorio | Permiso | `permit_instances` | No | `uom_id` únicamente | `BACKFILL` | 043 | **CONTRACT_ONLY** |

### Recuento

| Clase | Tablas |
|---|---:|
| **MUST_HAVE_NOW** | **17** |
| `CONTRACT_ONLY` | 1 |
| `NOT_APPLICABLE` | 3 |

### Justificación de las exclusiones

- **`inventory_balances`** — es una proyección del ledger, no una transacción.
  R-D0-09-3 fija que el saldo se lleva **siempre** en unidad base: añadirle
  presentación crearía una unidad de existencia paralela, que es exactamente lo
  que la regla prohíbe.
- **`cost_layers`** — se deriva de `inventory_movements`, ya en unidad base.
  Duplicar allí la presentación sería redundancia sin valor histórico.
- **`triple_matches`** — compara cantidades ya convertidas a base entre orden,
  recepción y factura. Es donde la conversión **se comprueba**, no donde se
  captura.
- **`permit_instances`** — cantidad autorizada por un permiso regulatorio. Necesita
  unidad, no presentación comercial. Pertenece a la Spec 043; 011 solo fija el
  contrato.

---

## 3. Las cuatro columnas

Sobre cada una de las 17 tablas `MUST_HAVE_NOW`, por cada cantidad transaccional:

| Columna | Tipo | Por qué |
|---|---|---|
| `uom_id` | FK `units_of_measure` | En qué unidad se expresó la cantidad (R-D0-09-1) |
| `presentation_id` | FK `product_presentations`, nullable | Qué presentación se usó; nulo = unidad base directa |
| `conversion_factor_snapshot` | `NUMERIC(18,6)` | El factor **congelado** en el momento de escribir (R-D0-09-2) |
| `base_quantity` | `NUMERIC(18,6)` | Cantidad en unidad base, calculada al escribir y almacenada |

Más, por línea, un `uom_source` que distingue lo capturado de lo supuesto
(§2 de `legacy-uom-migration-matrix.md`).

`goods_receipt_lines` tiene **tres** cantidades (recibida, aceptada, rechazada) y
`purchase_order_lines` y `transfer_lines` **dos**: la unidad y la presentación se
declaran **una vez por línea**, y la cantidad base se calcula **por cada
cantidad**. Declarar la unidad por cantidad permitiría que una línea aceptara en
cajas lo que recibió en unidades.

---

## 4. Contrato para las Specs consumidoras

| Spec | Qué obtiene de 011 |
|---|---|
| 015, 016, 017 | Requisición, oferta y orden con presentación de compra y factor congelado |
| 019, 021 | Recepción que verifica contra la presentación de la orden (§21) |
| 023 | Movimientos siempre convertidos a base antes de registrarse (R-D0-09-3) |
| 025 | Transferencias, conteos y ajustes en la unidad en que se operó |
| 026 | Capas de costo sobre cantidad base coherente |
| 027, 034 | Facturas que **nunca** recalculan: reimprimir usa el snapshot (§70) |
| 029 | Pedido con presentación comercial |
| 031, 032 | Picking conoce lo que pidió el cliente y lo que recorre físicamente |
| 035 | Despacho con empaque desacoplado de la presentación comercial (§20) |
| 036 | Devoluciones en la misma presentación de la venta original |

Ninguna de esas Specs se implementa aquí (§39).
