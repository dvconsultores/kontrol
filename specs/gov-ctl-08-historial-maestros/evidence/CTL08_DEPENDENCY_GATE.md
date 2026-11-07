# CTL-08 — Gate de dependencias (GOV-CTL-FUNCTIONAL-05)

**Resultado: CTL08_FULL_PROCESS_IMPLEMENTABLE = 0, ruta B. No se construyó ningún producto reducido.**

## DT-06

| Campo | Valor |
|---|---|
| DT06_STATUS | BLOCKED_BY_OWNER_DECISION |
| CURRENT_SCOPE | `organization` y `master_data` privados sin auditoría; catálogo de eventos sin fijar (contrato 006/051) |
| OWNER_DECISION_STATUS | Pendiente |
| AFFECTS_CTL08 | Indirecto: `spec001-audit-catalog-delta.md` cita GOV-CTL-010 |
| DT06_BLOCKS_CTL08 | 0 para los maestros de Gobierno, que ya están catalogados |
| SHARED_CORE_CHANGE_REQUIRED | 0 |
| GOV_ONLY_PATH_AVAILABLE | 1 |

DT-06 no se absorbe.

## Maestros ausentes

| Contrato | Resultado | Motivo |
|---|---|---|
| CONTRACT_A | FALSO | Proveedores y clasificadores no existen; «cuentas» sin fijar; reglas de aprobación parciales |
| CONTRACT_B | SIN EVIDENCIA | GOV-CTL-010 enumera categorías concretas. Ni IR, ni N20, ni N23 lo definen como infraestructura aplicable a cualquier maestro. Un historial de tres categorías sería el producto reducido que el encargo prohíbe |

## Decisión

| Condición | Valor exigido | Valor medido |
|---|---|---|
| N20_N23_SUFFICIENT | 1 | 1 |
| MASTER_SCOPE_UNAMBIGUOUS | 1 | **0** (OQ-CTL08-01) |
| MASTERS_REQUIREMENT_FULLY_SATISFIABLE | 1 | **0** |
| DT06_BLOCKS_CTL08 | 0 | 0 |
| SHARED_CORE_CHANGE_REQUIRED | 0 | 0 |
| MATERIAL_OWNER_DECISIONS_PENDING | 0 | **1** (OQ-CTL08-01) |
| GENERIC_ENGINE_REQUIRED | 0 | 0 |
| SECURITY_BLOCKER | 0 | 0 |
| DATA_INTEGRITY_BLOCKER | 0 | 0 |
| TESTABILITY_BLOCKER | 0 | 0 |

| Campo | Valor |
|---|---|
| BLOCKER | Proveedores y clasificadores sin maestro de Gobierno; significado de «cuentas» sin fijar |
| EVIDENCE | `CTL08_MASTER_INVENTORY.md`, `CTL08_EXISTING_HISTORY_MATRIX.md` |
| DEPENDENCY | PROC-01 o GOV-ACC-009 (N37); BUD-02 (D-GOV-02, N10); ACC-01 (D-GOV-04, N36) si «cuentas» incluye las contables |
| DT06_IMPACT | Ninguno sobre esta decisión |
| SHARED_CORE_IMPACT | Ninguno |
| OWNER_DECISION_REQUIRED | OQ-CTL08-01. Además, las decisiones ya abiertas D-GOV-02 y D-GOV-04 |

## Reapertura

CTL-08 se reabre cuando existan los maestros de proveedores y clasificadores, y OQ-CTL08-01 esté resuelta, o si la dueña redefine GOV-CTL-010 por escrito. Esta última vía no se presume.
