# CRITERIOS DE ACEPTACIÓN — 007-NUCLEO-FISCAL

| Campo | Valor |
|---|---|
| Iniciativa | 007-nucleo-fiscal |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/007-nucleo-fiscal/acceptance-criteria.md` |

> Cada AC-007-XXX se enlaza a su FR en `traceability-matrix.md`. "Verde" = criterio demostrable con prueba automatizada o evidencia.

| ID | FR | Criterio de aceptación | Verde |
|---|---|---|---|
| AC-007-001 | FR-007-001 | Las reglas fiscales se versionan con vigencia y fuente legal; no hay solape de versiones activas para la misma clave. | ⬜ |
| AC-007-002 | FR-007-002 | `LegalSource` registra autoridad, tipo, número, gaceta, publicación, vigencias, archivo y hash. | ⬜ |
| AC-007-003 | FR-007-003 | Se asigna un perfil fiscal por empresa/tercero/rubro con clasificaciones y vigencia. | ⬜ |
| AC-007-004 | FR-007-004 | El cálculo fiscal por documento/línea conserva snapshot de base, tasa, monto y redondeo. | ⬜ |
| AC-007-010 | FR-007-010 | La serie asigna el siguiente correlativo de forma atómica (lock); `Unique(company, establishment, document_type, fiscal_number)`. | ⬜ |
| AC-007-011 | FR-007-011 | El lote de control registra imprenta, rango, recibido, estado y conteos. | ⬜ |
| AC-007-012 | FR-007-012 | Un número de control tiene estado y no lo comparte un documento activo; `Unique(batch, value)`. | ⬜ |
| AC-007-020 | FR-007-020 | La emisión consume correlativo y número de control en transacción atómica (sin huecos ni duplicados). | ⬜ |
| AC-007-021 | FR-007-021 | `FiscalDocument` se emite con `hash` e inalterabilidad; numeración/control no editables. | ⬜ |
| AC-007-022 | FR-007-022 | Cada impresión/reimpresión queda registrada con motivo, usuario, copia y hora. | ⬜ |
| AC-007-023 | FR-007-023 | La contingencia de facturación se registra con modalidad y requisitos. | ⬜ |
| AC-007-030 | FR-007-030 | Una nota referencia obligatoriamente la factura, indica causal y limita al saldo ajustable. | ⬜ |
| AC-007-031 | FR-007-031 | Una nota no ajusta por encima de cantidades/base/IVA pendientes del original. | ⬜ |
| AC-007-040 | FR-007-040 | `WithholdingRule` define concepto/código, condiciones, base, tasa, mínimo y sustraendo. | ⬜ |
| AC-007-041 | FR-007-041 | La retención recorre CALCULATED→APPROVED→PRACTICED→CERTIFICATE_ISSUED→DECLARED→PAID→RECONCILED; REVERSED. | ⬜ |
| AC-007-050 | FR-007-050 | Los libros se generan desde documentos/eventos (no tablas editables) con equivalentes en bolívares, tasas y períodos. | ⬜ |
| AC-007-051 | FR-007-051 | El período fiscal pasa OPEN→CLOSED→REOPENED con aprobaciones; la reapertura queda auditada. | ⬜ |
| AC-007-052 | FR-007-052 | `TaxReturnBatch` registra archivos, totales, presentación, pago y conciliación. | ⬜ |
| AC-007-060 | FR-007-060 | La versión fiscal está identificada con registro de eventos e integridad; no se declara homologación sin acto formal. | ⬜ |
| AC-007-061 | FR-007-061 | 007 consume documentos de 004/005, retenciones y eventos IGTF de 006 vía contrato v1 sin duplicar lógica. | ⬜ |
| AC-007-100 | FR-007-100 | Aislamiento multiempresa; idempotencia; decimal exacto; asignación bajo lock/transacción. | ⬜ |
| AC-007-101 | FR-007-101 | Pantallas fiscales funcionales sin scroll horizontal. | ⬜ |
