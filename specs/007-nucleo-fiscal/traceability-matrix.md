# MATRIZ DE TRAZABILIDAD — 007-NUCLEO-FISCAL

| Campo | Valor |
|---|---|
| Iniciativa | 007-nucleo-fiscal |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/007-nucleo-fiscal/traceability-matrix.md` |

| FR | US | AC | T | TP | CHK | Notas |
|---|---|---|---|---|---|---|
| FR-007-001 | US-007-001 | AC-007-001 | T-007-01 | TP-007-01 | CHK-007-01 | TaxRuleVersion |
| FR-007-002 | US-007-001 | AC-007-002 | T-007-01 | TP-007-02 | CHK-007-02 | LegalSource |
| FR-007-003 | US-007-002 | AC-007-003 | T-007-01 | TP-007-03 | CHK-007-03 | TaxProfile |
| FR-007-004 | US-007-001 | AC-007-004 | T-007-01 | TP-007-04 | CHK-007-04 | TaxCalculation |
| FR-007-010 | US-007-003 | AC-007-010 | T-007-02 | TP-007-05 | CHK-007-05 | Series atómicas |
| FR-007-011 | US-007-003 | AC-007-011 | T-007-02 | TP-007-06 | CHK-007-06 | Lotes de control |
| FR-007-012 | US-007-003 | AC-007-012 | T-007-02 | TP-007-07 | CHK-007-07 | ControlNumber |
| FR-007-020 | US-007-004 | AC-007-020 | T-007-03 | TP-007-08 | CHK-007-08 | Emisión atómica |
| FR-007-021 | US-007-004 | AC-007-021 | T-007-03 | TP-007-09 | CHK-007-09 | FiscalDocument + hash |
| FR-007-020-D1 | US-007-006 | AC-007-020 | T-007-03 | TP-007-08 | CHK-007-08 | **Delta 2026-09-11**: la emisión acepta los tres tipos de documento, no solo `INVOICE` |
| FR-007-022 | US-007-005 | AC-007-022 | T-007-03 | TP-007-10 | CHK-007-10 | PrintEvent |
| FR-007-023 | US-007-005 | AC-007-023 | T-007-03 | TP-007-11 | CHK-007-11 | Contingencia |
| FR-007-030 | US-007-006 | AC-007-030 | T-007-04 | TP-007-12 | CHK-007-12 | Notas |
| FR-007-031 | US-007-006 | AC-007-031 | T-007-04 | TP-007-13 | CHK-007-13 | Límites de nota |
| FR-007-040 | US-007-007 | AC-007-040 | T-007-05 | TP-007-14 | CHK-007-14 | WithholdingRule |
| FR-007-041 | US-007-007 | AC-007-041 | T-007-05 | TP-007-15 | CHK-007-15 | Ciclo retención |
| FR-007-050 | US-007-008 | AC-007-050 | T-007-06 | TP-007-16 | CHK-007-16 | Libros |
| FR-007-051 | US-007-009 | AC-007-051 | T-007-06 | TP-007-17 | CHK-007-17 | Períodos |
| FR-007-052 | US-007-009 | AC-007-052 | T-007-06 | TP-007-18 | CHK-007-18 | Declaraciones |
| FR-007-060 | US-007-010 | AC-007-060 | T-007-06 | TP-007-19 | CHK-007-19 | Homologación/trazabilidad |
| FR-007-061 | US-007-004 | AC-007-061 | T-007-08 | TP-007-20 | CHK-007-20 | Integración 004/005/006 |
| FR-007-100 | — | AC-007-100 | T-007-11 | TP-007-21 | CHK-007-21 | Multiempresa/atómico |
| FR-007-101 | — | AC-007-101 | T-007-09/10 | TP-007-22 | CHK-007-22 | Frontend |

## Cobertura de historias

| US | FRs cubiertos |
|---|---|
| US-007-001 | FR-007-001, FR-007-002, FR-007-004 |
| US-007-002 | FR-007-003 |
| US-007-003 | FR-007-010, FR-007-011, FR-007-012 |
| US-007-004 | FR-007-020, FR-007-021, FR-007-061 |
| US-007-005 | FR-007-022, FR-007-023 |
| US-007-006 | FR-007-030, FR-007-031 |
| US-007-007 | FR-007-040, FR-007-041 |
| US-007-008 | FR-007-050 |
| US-007-009 | FR-007-051, FR-007-052 |
| US-007-010 | FR-007-060 |
