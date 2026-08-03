# MATRIZ DE TRAZABILIDAD — 002-MAESTROS

| Campo | Valor |
|---|---|
| Iniciativa | 002-maestros |
| Versión | 1.0 |
| Ruta | `specs/002-maestros/traceability-matrix.md` |

Formato: | Requisito | Historia | Diseño | Contrato | Tarea | Prueba |

| Requisito | Historia | Diseño | Contrato | Tarea | Prueba |
|---|---|---|---|---|---|
| FR-002-001 | US-002-001 | data-model §2 | api-contracts | T-002-006 | Test Party |
| FR-002-002 | US-002-010 | data-model §2/§6 | api-contracts | T-002-006 | Test duplicidad RIF |
| FR-002-003 | US-002-001 | data-model §2 | api-contracts | T-002-009 | Test validez |
| FR-002-004 | US-002-001 | data-model §2 | api-contracts | T-002-007 | Test Customer |
| FR-002-005 | US-002-003/011 | data-model §2 | api-contracts | T-002-007 | Test aprobación |
| FR-002-006 | — | data-model §2 | api-contracts | T-002-008 | Test extensión |
| FR-002-007 | US-002-010 | research §1.2 | — | T-002-010 | Test formatos |
| FR-002-010 | US-002-002 | data-model §3 | api-contracts | T-002-002 | Test árbol |
| FR-002-011 | US-002-002 | data-model §3 | api-contracts | T-002-003 | Test atributos |
| FR-002-012 | US-002-002 | data-model §3 | api-contracts | T-002-003 | Test aplicabilidad |
| FR-002-013 | US-002-002 | data-model §3 | api-contracts | T-002-003 | Test valores |
| FR-002-014 | US-002-002 | research §1.1 | — | T-002-003 | Test sin migración |
| FR-002-015 | US-002-002 | research §1.1 | — | T-002-003 | Test EAV prohibido |
| FR-002-020 | US-002-004/007 | data-model §4 | api-contracts | T-002-004 | Test CatalogItem |
| FR-002-021 | US-002-004 | data-model §4 | api-contracts | T-002-004 | Test Product |
| FR-002-022 | US-002-005/015 | data-model §4 | api-contracts | T-002-004/017 | Test Service |
| FR-002-023 | US-002-005 | research §1.6 | — | T-002-004 | Test línea mixta |
| FR-002-024 | US-002-007 | data-model §3 | — | T-002-005 | Test plantillas |
| FR-002-025 | US-002-014 | data-model §4 | api-contracts | T-002-011 | Test barcode unique |
| FR-002-030 | US-002-013 | data-model §4 | api-contracts | T-002-001 | Test conversión |
| FR-002-031 | US-002-006 | data-model §5 | api-contracts | T-002-005 | Test versiones |
| FR-002-032 | US-002-015 | research §1.4 | — | T-002-005 | Test concepto ISLR |
| FR-002-033 | US-002-002 | Constitución P8 | — | T-002-003 | Test no hardcode |
| FR-002-040 | US-002-007 | WF-002-A | api-contracts | T-002-014 | E2E asistente |
| FR-002-041 | US-002-008 | WF-03 | api-contracts | T-002-015 | Component/E2E |
| FR-002-042 | US-002-010 | WF-01 | api-contracts | T-002-012/020 | E2E listado |
| FR-002-043 | US-002-010 | research §1.5 | api-contracts | T-002-019 | Vitest + E2E |
| FR-002-044 | US-002-009 | DOC-08 §12 | — | T-002-020 | Component test |
| FR-002-045 | US-002-012 | DOC-01 | api-contracts | T-002-013 | Test auditoría |

## Reglas

- No existe requisito sin prueba. ✔
- No existe tarea sin requisito. ✔
- Cada historia US tiene al menos un requisito. ✔

## Estado

| Elemento | Estado |
|---|---|
| Requisito → Historia/Diseño/Contrato/Tarea/Prueba | ✔ |
| Evidencia de implementación | Pendiente (implementación) |
