# Spec 019 · delta RECEPCION-FUNCTIONAL-CLOSURE

Delta dirigido dentro de la Spec 004, capacidad 019. Autorizado por el encargo RECEPCION-FUNCTIONAL-CLOSURE-03 (2026-11-07). Evidencia: `evidence/recepcion-functional-closure/`.

## Requisitos

| ID | Requisito |
|---|---|
| FR-019-025 | La recepción recorre FR-004-031 entera: ningún estado exigido queda inalcanzable |
| FR-019-026 | Calidad toma la recepción confirmada (QUALITY_PENDING) y el veredicto solo se da ahí |
| FR-019-027 | Aceptar distingue aceptación total y parcial; sin nada aceptado no se acepta |
| FR-019-028 | Una recepción aceptada se cierra tras confirmar su inventario; una rechazada, sin incidencias vivas |
| FR-019-029 | Un borrador se anula con motivo; ningún otro estado se anula |
| FR-019-030 | Toda transición queda auditada; la pantalla sigue lo que publica el backend |

## API

Altas autorizadas: `POST /purchasing/receipts/{id}/close` y `POST /purchasing/receipts/{id}/cancel`. Cambio: `/quality` acepta el cuerpo sin veredicto. Nuevo en las respuestas: `allowed_actions`. Errores nuevos: `QUALITY_NOT_PENDING`, `RECEIPT_NOTHING_ACCEPTED`, `RECEIPT_NOT_RECONCILED`, `RECEIPT_INCIDENTS_OPEN`, `RECEIPT_CLOSED`, `REASON_REQUIRED`. Evento nuevo: `RECEIPT_TRANSITIONED`.

Cambio de contrato para los consumidores: aceptar desde `CONFIRMED` ya no es posible, porque FR-004-031 exige pasar por calidad. Se actualizaron las pruebas, las E2E y los guiones de QA que lo hacían.

## Constitution gate

Sin migración ni esquema; el motivo de anulación vive en la auditoría. Multiempresa conservada, con 404 en las operaciones nuevas para otra empresa. Sin backfill. BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0 · MATERIAL OQ 0.

## Trazabilidad

| Requisito | Pruebas |
|---|---|
| FR-019-025 | `test_la_maquina_es_la_de_fr004031`, E1 a E4 |
| FR-019-026 | QP-01 a QP-09 |
| FR-019-027 | PA-01 a PA-03 |
| FR-019-028 | CL-01 a CL-08, `test_cerrada_no_admite_incidencias` |
| FR-019-029 | CN-01 a CN-08 |
| FR-019-030 | AU-01, AU-09, `allowed_actions`, `RecepcionesMaquina.test.tsx` |
