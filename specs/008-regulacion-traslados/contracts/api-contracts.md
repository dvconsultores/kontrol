# CONTRATOS DE API — 008-REGULACION-TRASLADOS

| Campo | Valor |
|---|---|
| Iniciativa | 008-regulacion-traslados |
| Versión | 1.0 (contratos v1) |
| Fecha | 2026-08-04 |
| Ruta | `specs/008-regulacion-traslados/contracts/api-contracts.md` |

> Autenticación/contexto: `X-Company-Id`, `Authorization: Bearer`. Respuesta estándar `{data, meta}` o `{error}`. Idempotencia en POST críticos.

## 1. Maestros regulatorios

- `GET/POST /regulatory/authorities` — body: `{code, name, validation_method?}`.
- `GET/POST /regulatory/permit-types` — body: `{authority_id, code, name, scope?, validation_method?}`.
- `GET/POST /regulatory/official-registrations` — body: `{authority_id, scope, ref_number, issued_at?, expires_at?, file_ref?}`.
- `GET/POST /regulatory/profiles` — body: `{rubric_id?, product_id?, operation, origin?, destination?, required_documents, validity?, version?}`.
- `GET/POST /regulatory/vehicles` — body: `{plate, type, capacity?, owner_party_id?, documents?}`.
- `GET/POST /regulatory/drivers` — body: `{party_id, license?, documents?}`.

## 2. Permisos y guías

- `GET/POST /regulatory/permits` — body: `{permit_type_id, number, issued_at, expires_at?, origin?, destination?, products?, lots?, quantity?, vehicle_id?, file_ref?}`.
- `POST /regulatory/permits/{id}/transition` — `{target}` (REGISTERED/VERIFIED/APPROVED_FOR_USE/USED/EXPIRED/REJECTED/CANCELLED).
- `GET/POST /regulatory/official-documents` — body: `{kind: SICA|SIGESAI|SACS|OTRO, authority_id, number, issued_at?, expires_at?, file_ref?}` (registro y validación; no emisión).

## 3. Evaluación y bloqueo del despacho

- `POST /regulatory/evaluations` — `{shipment_id}` → evalúa cada línea de despacho de 005 y consolida requisitos.
- `GET /regulatory/evaluations?shipment_id=` — resultados, bloqueos y anulaciones.
- `POST /regulatory/evaluations/{id}/override` — `{reason, allowed_by}` → anula bloqueo (auditado).
- `GET /regulatory/shipment-status/{shipment_id}` — estado regulatorio del despacho (bloqueado/aprobado).

## 4. Contingencias y aprobaciones

- `GET/POST /regulatory/contingencies` — body: `{rule_ref, reason, allowed_by?}` (solo con regla oficial versionada).
- `POST /regulatory/approval-requests` — body: `{object_ref, rule_ref, risk?, amount?, deadline?}`.
- `POST /regulatory/approval-requests/{id}/transition` — decisión.

## 5. Contratos de integración (consumidos — v1)

| Contrato | Origen | Uso |
|---|---|---|
| `Shipment` / `ShipmentLine` | 005 | Objeto de la evaluación regulatoria y bloqueo |
| `parties`, `catalog_items` | 002 | Vehículos/conductores y rubros |
| Lotes/seriales/cantidades | 003 | Coincidencia en el bloqueo |

## 6. Endpoints (resumen estimado)

~20 rutas bajo `/regulatory`. Se verificarán tras implementación con `app.openapi()['paths']`.
