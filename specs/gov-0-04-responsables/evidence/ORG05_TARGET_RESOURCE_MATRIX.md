# ORG05_TARGET_RESOURCE_MATRIX · GOV-ORG-006 (2026-11-01, HEAD `8ea3a92`)

Fuente del alcance: IR v1.0 §7.1, GOV-ORG-006 «Mantener responsables por unidad, programa, proyecto, cuenta, almacén, caja, banco,
contrato y bienes, conservando historia» (N03, N18, N20, N21; P0). Estado de cada proceso dueño: `GOVERNMENT_PRODUCT_COMPLETENESS_MATRIX.csv`.
Código: `resources/backend/app/modules/government/models.py` (solo `GovernmentEntity*`, `GovernmentStructure`, `GovernmentUnit*`,
`GovernmentPosition*`). Los equivalentes de Empresarial (`organization.Warehouse`, `treasury.Cashbox`, `treasury.FinancialAccount`,
`treasury.FinancialBank`, `master_data.PartyBankAccount`) son objetos privados: IR §6 («reutilizar componentes técnicos de Empresarial no
implica reutilizar reglas de negocio») y la línea base de arquitectura (custodia GOVERNMENT_ONLY) impiden usarlos como objetos de Gobierno.

| RESOURCE_CLASS | CANONICAL_REQUIREMENT | OWNING_GOV_MODULE (proceso) | CURRENT_MODEL_EXISTS | CURRENT_API_EXISTS | CURRENT_UI_EXISTS | CURRENT_OWNER_PROCESS | CURRENT_STATE | CAN_REFERENCE_WITH_DB_INTEGRITY | CAN_VALIDATE_SCOPE | CAN_VALIDATE_EXISTENCE | CAN_RUN_REAL_UAT | MATERIAL_DEPENDENCY | BLOCKER_CLASS | RATIONALE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| UNIT | GOV-ORG-002/008 | Government Core (ORG-02) | SÍ (`gov_units`) | SÍ (`/gobierno/estructuras`) | SÍ | ORG-02 | OWNER_UAT_READY | SÍ (FK compuesta a la estructura) | SÍ | SÍ | SÍ | — | — | Disponible; por sí sola no cierra GOV-ORG-006 |
| PROGRAM | GOV-BUD-003/004 | Budget Ledger (BUD-03) | NO | NO | NO | BUD-03 | BLOCKED (D-GOV-02; N07, N08 clase C) | NO | NO | NO | NO | BUD-03 | DOMAIN_DEPENDENCY + DATA_INTEGRITY (+ LEGAL heredado) | El programa no existe; referenciarlo exigiría texto libre o UUID sin integridad |
| PROJECT | GOV-BUD-003/004 | Budget Ledger (BUD-03) | NO | NO | NO | BUD-03 | BLOCKED (ídem) | NO | NO | NO | NO | BUD-03 | DOMAIN_DEPENDENCY + DATA_INTEGRITY (+ LEGAL heredado) | Ídem |
| ACCOUNT | ambiguo: GOV-ACC-002 (plan de cuentas), GOV-BUD (partida), GOV-CTL-006 / N21 (cuenta de rendición) | Treasury & Public Accounting (ACC-01) o Budget Ledger o Records & Audit | NO | NO | NO | ACC-01 / BUD-* / CTL-* | ACC-01 BLOCKED (D-GOV-04; N36 clase C); resto NOT_STARTED | NO | NO | NO | NO | ACC-01 o BUD-* o CTL-06 + OQ-ORG05-02 | DOMAIN_DEPENDENCY + DATA_INTEGRITY + semántica sin resolver | «Cuenta» se lista aparte de «banco»; la IR no dice si es contable, presupuestaria o de rendición |
| WAREHOUSE | GOV-WH-003 | Recepción, almacén e inventario (WH-02) | NO | NO | NO | WH-02 | NOT_STARTED | NO | NO | NO | NO | WH-02 | DOMAIN_DEPENDENCY + DATA_INTEGRITY | `organization.Warehouse` es de Empresarial |
| CASH_BOX | GOV-TRE-009 | Treasury (TRE-08) | NO | NO | NO | TRE-08 | NOT_STARTED | NO | NO | NO | NO | TRE-08 | DOMAIN_DEPENDENCY + DATA_INTEGRITY | `treasury.Cashbox` es de Empresarial |
| BANK_ACCOUNT | GOV-TRE-001 | Treasury (TRE-01) | NO | NO | NO | TRE-01 | NOT_STARTED | NO | NO | NO | NO | TRE-01 | DOMAIN_DEPENDENCY + DATA_INTEGRITY | `treasury.FinancialAccount` es de Empresarial; TRE-01 ya incluye «autorizados» |
| CONTRACT | GOV-CNT-001 (+ GOV-CNT-004) | Procurement (CNT-01) | NO | NO | NO | CNT-01 (tras la cadena PRC) | NOT_STARTED | NO | NO | NO | NO | CNT-01 | DOMAIN_DEPENDENCY + DATA_INTEGRITY | Sin contrato no hay supervisor; CNT-04 además pide designación con acto |
| PUBLIC_ASSET | GOV-AST-001 (+ GOV-AST-006) | Public Assets (AST-01, AST-03) | NO | NO | NO | AST-01 / AST-03 | AST-01 BLOCKED (D-GOV-05; N15, N17 clase C); AST-03 NOT_STARTED | NO | NO | NO | NO | AST-01 | DOMAIN_DEPENDENCY + DATA_INTEGRITY (+ LEGAL heredado) | Custodia GOVERNMENT_ONLY; el bien no existe |

Resumen: ORG05_TARGET_RESOURCE_COUNT = 9 · AVAILABLE = 1 (UNIT) · BLOCKED = 8 · UNCLASSIFIED = 0 · MATRIX_COMPLETE = 1.
