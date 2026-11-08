# Documentos activos que bloquean (EDGE-002-02)

Fuente de los estados: tablas `*_TRANSITIONS` de cada servicio. Activo es lo que aún tiene transiciones vivas de negocio. No bloquea el histórico cerrado.

| Módulo | Documento | Campo | Rol | Estados activos | Terminales | Bloquea |
|---|---|---|---|---|---|---|
| ventas | SalesQuote | customer_id | CLIENTE | DRAFT, SENT, ACCEPTED | REJECTED, EXPIRED, CONVERTED, CANCELLED | sí |
| ventas | SalesOrder | customer_id | CLIENTE | DRAFT, SUBMITTED, RELEASED, PREPARING, PREPARED, CONFIRMED, READY_FOR_BILLING, INVOICED, SHIPPED | CLOSED, CANCELLED, REJECTED, EXPIRED | sí |
| ventas | SalesInvoice | customer_id | CLIENTE | DRAFT, VALIDATED, APPROVED, EMITTED, DELIVERED, PARTIALLY_PAID | PAID (ya sin saldo), CREDITED, VOIDED, REJECTED, CANCELLED | sí |
| ventas | SalesReturn | customer_id | CLIENTE | DRAFT, REQUESTED, RECEIVED, INSPECTED, APPROVED | CLOSED, REJECTED, CANCELLED | sí |
| compras | SupplierQuote | supplier_id | PROVEEDOR | ACTIVE | otros | sí |
| compras | PurchaseOrder | supplier_id | PROVEEDOR | DRAFT, SUBMITTED, APPROVED, PARTIALLY_RECEIVED, RECEIVED | CLOSED, CANCELLED, REJECTED | sí |
| compras | SupplierInvoice | supplier_id | PROVEEDOR | DRAFT, VALIDATED, MATCHED, EXCEPTION, APPROVED, POSTED, PARTIALLY_PAID | PAID, REVERSED, REJECTED, CANCELLED | sí |
| CxC y CxP | OpenItem | party_id | según `direction` | OPEN | CLOSED | sí |
| CxC y CxP | Payment | party_id | según `direction` | DRAFT, SUBMITTED, APPROVED | POSTED, REJECTED, CANCELLED | sí |
| CxC y CxP | Advance | party_id | según `direction` | ACTIVE | otros | sí |
| CxP | PaymentSchedule | party_id | PROVEEDOR | PENDING | otros | sí |
| CxP y fiscal | Withholding | party_id | cualquiera | CALCULADA, PRACTICADA, EMITIDA, DECLARADA, PAGADA | CONCILIADA, REVERSADA | sí |
| tesorería | TreasuryRefund | customer_id | CLIENTE | REQUESTED, APPROVED | SETTLED, REJECTED | sí |
| regulatorio | TransportDriver | party_id | CONDUCTOR | ACTIVE | otros | sí |
| regulatorio | TransportVehicle | owner_party_id | cualquiera | ACTIVE | otros | sí |

Notas de ventas y compras: `SalesInvoice` y `SupplierInvoice` en PAID tienen transiciones técnicas de reversión, pero ya no hay obligación viva y `OpenItem` cierra la deuda: se consideran terminales para este bloqueo. `SalesCreditNote`, `SalesDebitNote` y `SupplierCreditNote` no bloquean por sí mismas: ajustan facturas y, si dejan saldo, éste vive en `OpenItem`.

Respuesta: 409 `PARTY_HAS_ACTIVE_DOCUMENTS` con `details.documents` = [{module, document, count}]. Sin cambio de estado (EDGE-002-02: estado conservado).
