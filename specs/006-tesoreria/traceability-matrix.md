# MATRIZ DE TRAZABILIDAD — 006-TESORERIA

| Campo | Valor |
|---|---|
| Iniciativa | 006-tesoreria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/006-tesoreria/traceability-matrix.md` |

| FR | US | AC | T | TP | CHK | Notas |
|---|---|---|---|---|---|---|
| FR-006-001 | US-006-001 | AC-006-001 | T-006-02 | TP-006-01 | CHK-006-01 | CashSession |
| FR-006-002 | US-006-001 | AC-006-002 | T-006-02 | TP-006-02 | CHK-006-02 | Ciclo de caja |
| FR-006-003 | US-006-002 | AC-006-003 | T-006-02 | TP-006-03 | CHK-006-03 | Cierre con diferencia |
| FR-006-004 | US-006-002 | AC-006-004 | T-006-02 | TP-006-04 | CHK-006-04 | Arqueo |
| FR-006-010 | US-006-003 | AC-006-010 | T-006-03 | TP-006-05 | CHK-006-05 | BankTransaction |
| FR-006-011 | US-006-003 | AC-006-011 | T-006-03 | TP-006-06 | CHK-006-06 | Cuentas |
| FR-006-012 | — | AC-006-012 | T-006-01 | TP-006-07 | CHK-006-07 | Maestros financieros |
| FR-006-020 | US-006-003 | AC-006-020 | T-006-03 | TP-006-08 | CHK-006-08 | Ingreso/egreso |
| FR-006-021 | US-006-004 | AC-006-021 | T-006-03 | TP-006-09 | CHK-006-09 | Varios medios |
| FR-006-022 | US-006-003 | AC-006-022 | T-006-03 | TP-006-10 | CHK-006-10 | Idempotencia |
| FR-006-023 | US-006-005 | AC-006-023 | T-006-04 | TP-006-11 | CHK-006-11 | Transferencias |
| FR-006-030 | US-006-006/007 | AC-006-030 | T-006-05 | TP-006-12 | CHK-006-12 | Conciliación asistida |
| FR-006-031 | US-006-006 | AC-006-031 | T-006-05 | TP-006-13 | CHK-006-13 | Reconciliation |
| FR-006-032 | US-006-009 | AC-006-032 | T-006-05 | TP-006-14 | CHK-006-14 | Comisiones/dif. cambiarias |
| FR-006-033 | US-006-011 | AC-006-033 | T-006-05 | TP-006-15 | CHK-006-15 | Cierre de período |
| FR-006-040 | US-006-008 | AC-006-040 | T-006-06 | TP-006-16 | CHK-006-16 | IGTF regla/evento |
| FR-006-041 | US-006-008 | AC-006-041 | T-006-06 | TP-006-17 | CHK-006-17 | Reglas versionadas |
| FR-006-050 | US-006-003 | AC-006-050 | T-006-08 | TP-006-18 | CHK-006-18 | Integración 004/005 |
| FR-006-051 | US-006-010 | AC-006-051 | T-006-08 | TP-006-19 | CHK-006-19 | Anticipos |
| FR-006-052 | — | AC-006-052 | T-006-03 | TP-006-20 | CHK-006-20 | Snapshot tasa |
| FR-006-100 | — | AC-006-100 | T-006-12 | TP-006-21 | CHK-006-21 | Multiempresa/idempotencia |
| FR-006-101 | — | AC-006-101 | T-006-09/10/11 | TP-006-22 | CHK-006-22 | Frontend |

## Cobertura de historias

| US | FRs cubiertos |
|---|---|
| US-006-001 | FR-006-001, FR-006-002 |
| US-006-002 | FR-006-003, FR-006-004 |
| US-006-003 | FR-006-010, FR-006-011, FR-006-020, FR-006-022, FR-006-050 |
| US-006-004 | FR-006-021 |
| US-006-005 | FR-006-023 |
| US-006-006 | FR-006-030, FR-006-031 |
| US-006-007 | FR-006-030 |
| US-006-008 | FR-006-040, FR-006-041 |
| US-006-009 | FR-006-032 |
| US-006-010 | FR-006-051 |
| US-006-011 | FR-006-033 |
