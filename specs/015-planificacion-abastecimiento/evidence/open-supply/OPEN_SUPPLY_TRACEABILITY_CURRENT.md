# Suministro abierto por almacén · cadena actual

**Ciclo:** `OPEN_SUPPLY_BY_WAREHOUSE`, 2026-11-13.
**HEAD reconciliado:** `c93311a`.
**Cabeza Alembic:** `0105_receipt_temporary_zone`.

**Fuentes leídas:**
- `planning/{engine,replenishment,requisitions,models}.py`;
- `purchasing/{models,service}.py`;
- `imports/models.py`;
- `specs/004-compras-cuentas-por-pagar/evidence/quote-award/EVIDENCE.md`.

## Cadena nodo a nodo

| NODE | PRIMARY_KEY | STRUCTURED_PARENT | WAREHOUSE_AUTHORITY | PRODUCT_AUTHORITY | QUANTITY_AUTHORITY | STATUS_AUTHORITY | MISSING_LINK |
|---|---|---|---|---|---|---|---|
| ReplenishmentNeed | `replenishment_needs.id` | (empresa, almacén, producto); episodio ACTIVE único | `warehouse_id` (NOT NULL) | `product_id` | `current_recommended_quantity` (instantánea del plan) | ACTIVE / RESOLVED | — |
| PurchaseRequisition | `purchase_requisitions.id` | — (la necesidad se vincula por `requisition_line_plans`) | `warehouse_id` en la cabecera, **nullable** | — | — | DRAFT → SUBMITTED → APPROVED → CLOSED; REJECTED; CANCELLED | — |
| RequisitionLine | `purchase_requisition_lines.id` | `requisition_id` | heredada de la cabecera | `product_id` | `quantity` / `base_quantity` | la de la cabecera | — |
| RequisitionLinePlan | `requisition_line_plans.id` | `requisition_line_id` (único) | — | — | instantánea del plan (`open_supply` hoy NULL) | OK / INSUFFICIENT_HISTORY / PLAN_NOT_CONFIGURED | — |
| SupplierQuote / QuoteLine | `supplier_quotes.id` / `supplier_quote_lines.id` | **ninguno hacia la requisición** | **ninguna** | `product_id` | `quantity` | ACTIVE → AWARDED → CONVERTED | **QUOTE-REQUISITION-LINK** |
| PurchaseOrder | `purchase_orders.id` | `quote_id` (opcional, único) | **ninguna** | — | — | DRAFT → SUBMITTED → APPROVED → PARTIALLY_RECEIVED / RECEIVED → CLOSED; CANCELLED (DRAFT o APPROVED); REJECTED | — |
| PurchaseOrderLine | `purchase_order_lines.id` | `order_id` | **ninguna** | `product_id` | `quantity_ordered` y `quantity_received` (y sus `base_*`); no hay cantidad cancelada | la de la cabecera | **sin origen de requisición y sin almacén destino** |
| GoodsReceipt | `goods_receipts.id` | `order_id` | `warehouse_id` (NOT NULL), **elegido libremente en cada recepción** | — | — | DRAFT → … → CLOSED; CANCELLED | — |
| GoodsReceiptLine | `goods_receipt_lines.id` | `receipt_id` (y la línea de la orden) | la de la recepción | `product_id` | recibida, aceptada y rechazada | — | — |
| ImportFile | `import_files.id` | `order_id` (opcional) | ninguna | — | — | — | — |

## Hallazgos

```text
ONE_PURCHASE_ORDER_ONE_WAREHOUSE=0
  (create_receipt acepta cualquier almacén operable de la empresa en cada recepción de la misma orden)
REQUISITION_LINE_TO_PO_LINE_STRUCTURED=0
  (requisición ↛ cotización ↛ orden: la cotización no guarda su requisición; create_order/add_order_line no reciben origen)
PO_LINE_DESTINATION_WAREHOUSE=NONE
ORDERED_QUANTITY_AUTHORITY=purchase_order_lines.quantity_ordered (base_quantity_ordered)
RECEIVED_QUANTITY_AUTHORITY=purchase_order_lines.quantity_received (base_quantity_received), mantenida por la recepción
CANCELLED_QUANTITY_AUTHORITY=estado de la cabecera: CANCELLED (antes de recibir) o CLOSED (el saldo ya no llegará); no hay cancelación parcial por línea
OPEN_SUPPLY_REQUIRES_QUOTE_REQUISITION_LINK=depende de la opción elegida (ver la decisión)
WAREHOUSE_AUTHORITY_CLEAR=0  →  MATERIAL_DECISION_REQUIRED=1
```

Hoy no se puede saber de forma inequívoca a qué almacén va una cantidad pedida y aún no recibida. Inferirlo desde la requisición por texto, el último almacén usado, la primera recepción o un almacén por defecto está prohibido (§13). Por eso no se escribe código que dependa de esa autoridad hasta que la dueña decida.

## Lo que sí es independiente de la decisión

- **Fórmula por línea:** `max(0, ordenado_base − recibido_base)`, solo en órdenes APPROVED o PARTIALLY_RECEIVED. Quedan fuera DRAFT, SUBMITTED, REJECTED, CANCELLED, RECEIVED y CLOSED.
- **Integración:** el motor ya expone `open_supply` y `open_supply_available` (hoy `None` y `False`), y `condition_met` decide sobre `available`.
- **Datos históricos:** no tienen almacén estructurado. Quedan como `NO_ATTRIBUTION`: no se atribuyen y no se rellenan por coincidencia.

## Decisión de la dueña (2026-11-13)

Se le preguntó dónde vive la autoridad del almacén destino de una línea de orden. Opciones:
- **A.** En la línea de la orden.
- **B.** En el origen, la requisición (exige QUOTE-REQUISITION-LINK).
- **C.** Un híbrido de las dos.

Respuestas:
- Eligió **A, la línea de la orden**.
- Si se intenta recibir en otro almacén: **se bloquea**.
- Tras medir el impacto (unas 33 pruebas de backend, unas 15 E2E y la siembra aprueban órdenes sin almacén), la obligación queda **en pantalla**: el backend acepta el campo como opcional y una línea sin destino no cuenta.

```text
WAREHOUSE_AUTHORITY=purchase_order_lines.destination_warehouse_id
OPEN_SUPPLY_REQUIRES_QUOTE_REQUISITION_LINK=0
MATERIAL_DECISION_REQUIRED=0
```
