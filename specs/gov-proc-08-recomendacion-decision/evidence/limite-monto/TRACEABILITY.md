# AAL · Trazabilidad

| Requisito | Código | Prueba |
|---|---|---|
| AAL-01 Alcance ADJUDICADA | `service_decision_resolver.registrar_decision`, rama ADJUDICADA → `exigir_limite` | T1–T4, T6 |
| AAL-02 Total declarado | `evaluar_limite` (`total_con_tributos` de la versión vigente) | T1 (casos 1–3) y T7 |
| AAL-03 Actor efectivo | `exigir_autoridad_funcional`, sin cambios | Suite PROC-08 existente |
| AAL-04 Cargo efectivo y fecha del acto | `_cargo_del_acto` y `acto.fecha` | T8 (versión en vigor en la fecha del acto) |
| AAL-05 Competencia APROBAR × CONTRATACIONES | `competencia_aprobar_contrataciones` → `competencias_en_vigor` | T1–T8 |
| AAL-06 Sin límite | estado `SIN_LIMITE` antes que `MONTO_NO_DECLARADO` | T3 (caso 5) y T4 (segunda parte); mutación M4 |
| AAL-07 Misma moneda, ≤ | `Decimal` sin redondeo | T1 casos 1 y 2; mutación M1 |
| AAL-08 Exceso → 409 | `GOV_DECISION_AUTHORITY_AMOUNT_EXCEEDED` con `details` | T1 caso 3 y E2E |
| AAL-09 Moneda distinta → 409 | `GOV_DECISION_AUTHORITY_CURRENCY_MISMATCH` | T2 (caso 4) y T7; mutación M2 |
| AAL-10 Sin monto → 409 | `GOV_DECISION_OFFER_AMOUNT_REQUIRED` | T4 (caso 6) y T7 |
| AAL-11 Sin override | No hay campo ni permiso; el botón llega al backend | E2E (bloqueo y luego otro acto) |
| AAL-12 Otros resultados | DESIERTA, TERMINADA y NULIDAD no llaman a `exigir_limite` | T5 (caso 7) |
| AAL-13 Confidencialidad | La auditoría lleva acto, oferta, causal y resultado, sin importes | T6 |
| AAL-14 Concurrencia | Expediente `FOR UPDATE` + estructura `FOR UPDATE`, con recálculo al registrar | T8, T9 y T10 (carrera); mutación M3 |
| AAL-15 Pantalla, E2E y UAT | `ControlLimiteAutoridad.tsx`, `gobierno-decision.spec.ts` y la tarjeta | Vitest, E2E con Axe a 1280/390/320, humo UAT |

Cobertura: 15 de 15 requisitos (100 %).
