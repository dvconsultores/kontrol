# CONTRATOS DE API — 007-NUCLEO-FISCAL

| Campo | Valor |
|---|---|
| Iniciativa | 007-nucleo-fiscal |
| Versión | 1.0 (contratos v1) |
| Fecha | 2026-08-04 |
| Ruta | `specs/007-nucleo-fiscal/contracts/api-contracts.md` |

> Autenticación/contexto: `X-Company-Id`, `Authorization: Bearer`. Respuesta estándar: `{data, meta}` o `{error: {code, message, details}}`. Idempotencia: `Idempotency-Key` en POST críticos (emisión). Montos con decimal exacto.

## 1. Reglas y perfiles fiscales

- `GET/POST /fiscal/legal-sources` — body: `{authority, source_type, number, gazette?, publication_date, effective_from, effective_to?}`.
- `GET/POST /fiscal/tax-rule-versions` — body: `{tax_code, tax_type, legal_source_id, effective_from, effective_to?, params}`; valida **sin solape** de vigentes.
- `GET/POST /fiscal/tax-profiles` — body: `{scope, party_id?, item_id?, classifications, validity?}`.
- `GET /fiscal/tax-calculations` — lecturas por documento/línea (snapshot).

## 2. Numeración y números de control

- `GET/POST /fiscal/number-series` — body: `{establishment, document_type, prefix}` → `next_number` con `lock_version`.
- `GET/POST /fiscal/control-batches` — body: `{establishment, printer, range_from, range_to, received_at}`.
- `GET /fiscal/control-numbers` — lista por lote/estado.
- `POST /fiscal/number-series/{id}/reserve` — reserva atómica del siguiente número (interno, idempotente).

## 3. Emisión e impresión

- `POST /fiscal/documents/emit` — `{business_document: "INVOICE:{id}"}` → consume serie + control en **transacción atómica** y genera `FiscalDocument` con `hash`. **Idempotente** (una sola emisión por documento).
- `GET /fiscal/documents` · `GET /fiscal/documents/{id}` — FiscalDocuments con serie, número, control, moneda fiscal, tasa, hash, estado.
- `POST /fiscal/documents/{id}/print` — `{copy_type, printer, reason?}` → `PrintEvent`.
- `POST /fiscal/contingency` — `{document_type, modality, reason, notes?}` (FR-007-023).

## 4. Notas fiscales

- `POST /fiscal/credit-debit-notes` — `{original_document: "INVOICE:{id}", cause, amount, inventory_effect?, financial_effect?}` → valida límite al **saldo ajustable** (FR-007-031).
- `GET /fiscal/credit-debit-notes` — lista por factura original.

## 5. Retenciones

- `GET/POST /fiscal/withholding-rules` — body: `{tax_type, concept, code, conditions?, base, rate, minimum?, subtractor?}`.
- `GET /fiscal/withholdings` · `POST /fiscal/withholdings/{id}/transition` — ciclo CALCULATED→APPROVED→PRACTICED→CERTIFICATE_ISSUED→DECLARED→PAID→RECONCILED; REVERSED.
- `POST /fiscal/withholdings/{id}/certificate` — emite comprobante (lectura).

## 6. Períodos, declaraciones y libros

- `GET/POST /fiscal/periods` — body: `{tax_type, start, end, deadlines?}`; `POST /fiscal/periods/{id}/transition` (OPEN→CLOSED→REOPENED con aprobación).
- `GET/POST /fiscal/tax-return-batches` — body: `{tax_type, period, files?, totals?}`.
- `GET /fiscal/books/{tax_type}?period={mes-año}` — libro reconstruible (ventas/compras/retenciones) con equivalentes en Bs. **No filtra por período** hasta la validación legal: el período del libro lo fija el perfeccionamiento del hecho imponible (Ley del IVA, G.O. 6.507 Ext., arts. 13 y 56), no solo la fecha de emisión; la respuesta lo declara con `period_applied: false` y `period_rule: "LEGAL_VALIDATION_REQUIRED"` (OD-TIME-11).

## 7. Contratos de integración (consumidos de 004/005/006 — v1)

| Contrato | Origen | Uso |
|---|---|---|
| Factura venta emitible | 005 `SalesInvoice` | Envuelto por `FiscalDocument` (FR-007-020) |
| Factura proveedor | 004 `SupplierInvoice` | Libro de compras y retenciones |
| Notas de crédito/débito | 004/005 | `CreditDebitNote` con límites |
| Retenciones practicadas/sufridas | 004/005 `Withholding` | Ciclo 007 |
| Eventos IGTF | 006 `IgftEvent` | Libros/declaraciones (CL-007-09) |

## 8. Endpoints (resumen estimado)

~24 rutas bajo `/fiscal` (+ maestros). Se verificarán tras implementación con `app.openapi()['paths']`.
