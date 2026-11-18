# Puntero · PROC-07/PROC-08-COMMISSION-POLICY (2026-11-17)

Este proceso ya no calcula su propia regla de comisión. Consume la autoridad única `service_comision_regla.py`:

- el quórum y la mayoría salen de la política del ente, congelada en la comisión al activarse;
- se excluye al miembro con inhibición aceptada en el expediente;
- se exigen los documentos de la etapa que fije la política;
- sin comisión (expediente que declaró que no interviene), actúan los responsables del expediente (OD-CP-02).

El delta, sus requisitos (FR-CP-04, 05, 07, 08 y 09), las decisiones OD-CP-01 a 04 y la evidencia viven en la Spec dueña:

- `specs/gov-proc-02-comisiones/spec002-commission-policy-delta.md`;
- `specs/gov-proc-02-comisiones/evidence/commission-policy/`.

La decisión OD-PROC07-01 (mayoría simple) queda como **regla histórica** de las comisiones activadas antes de las políticas. Las comisiones nuevas siguen la política del ente.
