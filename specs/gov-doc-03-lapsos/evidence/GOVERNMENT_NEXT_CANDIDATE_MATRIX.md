# GOVERNMENT_NEXT_CANDIDATE_MATRIX

Fuente: `GOVERNMENT_PRODUCT_COMPLETENESS_MATRIX.csv` y requisitos, a `f48e98b`. 41 P0 y 13 P1 NOT_STARTED revisados, y 1 P2. Las dependencias son juicio de Claude sobre el requisito y los modelos existentes en `government/models.py`.

| PROCESS_ID | PRIORITY | STATUS | BLOCKERS | DEPENDENCIES | LEGAL_READY | PRODUCT_READY_TO_START | WHY_ELIGIBLE |
|---|---|---|---|---|---|---|---|
| **CTL-08** | P0 | NOT_STARTED | Ninguno declarado | Maestros existentes: cuentas, bancos, reglas SoD. Proveedores y clasificadores aún no existen | Sí: N20, N23 clase A | SÍ, sujeto a su gate | Único P0 que opera sobre objetos que ya existen |
| DOC-03 | P0 | BLOCKED | DOC-01, calendario | Ver gate | No | NO | — |
| CTL-09 | P0 | NOT_STARTED | Corte de bienes, contratos y expedientes | AST-01, CNT-01, DOC-01 | Sí | NO | Sin bienes, contratos ni expedientes |
| CTL-05 | P0 | NOT_STARTED | Piezas de la cuenta | DOC-01, BUD, ACC | Sí | NO | Sin operaciones que rendir |
| PROC-02 | P0 | NOT_STARTED | Miembros e impedimentos son personales | ORG-06, BLOCKED | Sí | NO | Mismo límite que TRE-08 |
| REQ-02, 04, 05 | P0 | NOT_STARTED | Requisición | REQ-01, BLOCKED | Sí | NO | — |
| PROC-03, 06, 07, 08, 10, 11, 12 | P0 | NOT_STARTED | Proceso de contratación | PROC-01, BLOCKED | Sí | NO | — |
| CNT-01..05, 07, 08 | P0 | NOT_STARTED | Contrato | PROC-*, BLOCKED | Sí | NO | — |
| BUD-06, 08, 11, 12 | P0 | NOT_STARTED | Presupuesto | BUD-01..03, BLOCKED | Sí | NO | — |
| WH-02..05 | P0 | NOT_STARTED | Almacén | WH-01, BLOCKED | Sí | NO | — |
| AST-03, 04, 05, 11 | P0 | NOT_STARTED | Bienes | AST-01, BLOCKED | Sí | NO | — |
| TRE-03, 06, 07, 10 | P0 | NOT_STARTED | Pago y obligación | BUD, ACC | Sí | NO | — |
| ACC-03, 05 | P0 | NOT_STARTED | Contabilidad | ACC-01, BLOCKED | Sí | NO | — |
| INT-02 | P0 | NOT_STARTED | Contrato con el banco | Tercero | n/a | NO | — |
| P1 y P2 restantes | P1, P2 | NOT_STARTED | Dependen de los anteriores | — | — | NO | CTL-07 y REP-10 valen menos que un P0 elegible |

**SELECTED_NEXT_GOVERNMENT_TARGET = CTL-08** (GOV-CTL-010).

Riesgo declarado: GOV-CTL-010 nombra proveedores y clasificadores, que aún no existen como maestros de Gobierno. El siguiente ciclo debe decidir en su propio gate si su producto queda completo sobre los maestros existentes. Si no, se bloquea sin reducir alcance.
