# CRITERIOS DE ACEPTACIÓN — 008-REGULACION-TRASLADOS

| Campo | Valor |
|---|---|
| Iniciativa | 008-regulacion-traslados |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/008-regulacion-traslados/acceptance-criteria.md` |

> Cada AC-008-XXX se enlaza a su FR en `traceability-matrix.md`. "Verde" = criterio demostrable con prueba automatizada o evidencia.

| ID | FR | Criterio de aceptación | Verde |
|---|---|---|---|
| AC-008-001 | FR-008-001 | Se registran autoridades (SENIAT, SUNAGRO, INSAI, SACS…) con código y método de validación. | ⬜ |
| AC-008-002 | FR-008-002 | Se definen tipos de permiso por autoridad con alcance y validación. | ⬜ |
| AC-008-003 | FR-008-003 | Los registros oficiales conservan número, autoridad, fechas, archivo y estado. | ⬜ |
| AC-008-004 | FR-008-004 | Vehículos y conductores se registran con identificación, capacidad y documentos. | ⬜ |
| AC-008-005 | FR-008-005 | El perfil regulatorio exige documentos según rubro/operación/origen/destino. | ⬜ |
| AC-008-010 | FR-008-010 | `PermitInstance` registra número, vigencia, origen/destino, productos/lotes/cantidad, transporte, archivo y verificación. | ⬜ |
| AC-008-011 | FR-008-011 | El permiso recorre DRAFT→REGISTERED→VERIFIED→APPROVED_FOR_USE→USED→EXPIRED; REJECTED/CANCELLED. | ⬜ |
| AC-008-012 | FR-008-012 | Las guías SICA/SIGESAI/SACS se registran y validan; Kontrol no fabrica permisos externos. | ⬜ |
| AC-008-013 | FR-008-013 | Cada documento conserva número, organismo, emisión, vigencia, archivo, hash, verificación, estado y auditoría. | ⬜ |
| AC-008-014 | FR-008-014 | No hay eliminación física de permisos; corrección por documento vinculado. | ⬜ |
| AC-008-020 | FR-008-020 | La regulación evalúa cada línea de despacho y consolida requisitos del movimiento. | ⬜ |
| AC-008-021 | FR-008-021 | `RegulatoryEvaluation` registra requisitos, resultados, bloqueos y anulación. | ⬜ |
| AC-008-022 | FR-008-022 | El despacho se bloquea si falta un documento, está vencido o no coincide con producto/lote/cantidad/origen/destino/vehículo/conductor. | ⬜ |
| AC-008-023 | FR-008-023 | La aplicabilidad se determina por rubro, presentación, actor, actividad, origen, destino, establecimiento, cantidad, unidad, operación y vigencia. | ⬜ |
| AC-008-024 | FR-008-024 | Un despacho puede requerir simultáneamente documento fiscal, Guía SICA, permiso SIGESAI y guía SACS. | ⬜ |
| AC-008-025 | FR-008-025 | `ApprovalRequest` registra solicitante, aprobadores, riesgo, monto, plazo, decisión y estado. | ⬜ |
| AC-008-030 | FR-008-030 | Las contingencias se habilitan solo con regla oficial versionada. | ⬜ |
| AC-008-031 | FR-008-031 | El picking no ampara el traslado físico; la guía fiscal no sustituye SICA/SIGESAI/SACS. | ⬜ |
| AC-008-032 | FR-008-032 | 008 consume los despachos de 005 vía contrato v1 sin duplicar lógica. | ⬜ |
| AC-008-100 | FR-008-100 | Aislamiento multiempresa; idempotencia; decimal exacto; reglas versionadas. | ⬜ |
| AC-008-101 | FR-008-101 | Pantallas regulatorias funcionales sin scroll horizontal. | ⬜ |
