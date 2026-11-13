# FUENTES · PROC-11 (GOV-PROC-017)

| Fuente | Ubicación | Qué se toma | Verificación |
|---|---|---|---|
| IR v1.0 §7.4 | `requerimientos/gobierno/Ingenieria_de_Requerimientos_KONTROL_Gobierno_v1.0.pdf`, pág. 10 | **GOV-PROC-017**: «Detectar conflictos SoD: solicitante/evaluador/adjudicador/receptor/pagador incompatibles según matriz institucional.» Fuente N20, N23. Prioridad P0. | SHA-256 del PDF en `docs/roadmap/kontrol-gobierno-source-register.md` (`8f86615f…`) |
| IR v1.0 §13 | mismo PDF, pág. 24 | **E2E-07 Hostil SoD**: «Mismo usuario intenta solicitar, adjudicar y pagar donde la política lo prohíbe: bloqueo backend y evento de auditoría.» | ídem |
| IR v1.0 §7.11 | mismo PDF, pág. 17 | **GOV-CTL-001** (matriz SoD por proceso, bloqueo previo) y **GOV-CTL-003** (autor, actor efectivo, rol) delimitan qué ya existe y no se duplica | ídem |
| N20 · Normas Generales de Control Interno | `requerimientos/gobierno/Biblioteca_Normativa_Oficial_KONTROL_Gobierno_v1.0.pdf` (ficha N20) | Deber de segregar funciones y de prever el conflicto de interés. **No fija pares concretos**: la matriz es institucional y la declara Control Interno. | clase A según el registro de fuentes |
| N23 · Ley contra la Corrupción | ídem (ficha N23) | Deber de prevención del conflicto de interés en la contratación pública. Tampoco fija pares. | clase A |
| Constitución P2 · DoD de producto | `docs/governance/product-completeness-and-owner-uat-policy.md` | Compuertas de producto completa y UAT de la dueña | — |
| Spec dueña de la SoD por acción | `specs/gov-ctl-01-sod/spec.md` | Motor de bloqueo por par de acciones sobre el mismo objeto, capacidad `gobierno_sod` y semántica de activación con MFA. **No se duplica**: se reutiliza la capacidad y el patrón de ciclo de vida. | — |
| Spec dueña del expediente | `specs/gov-proc-03-expediente/spec.md` | Dónde se registran responsable, comisión, ofertas, apertura, evaluación, recomendación y decisión | — |

## Lectura material

- La norma no enumera los pares: **es la institución quien los declara**. Igual que en CTL-01 (OD-CTL01-02/04), esto no
  exige una decisión material nueva: es configuración de Control Interno, versionada, activada con MFA y no editable una
  vez vigente.
- El requisito pide **detección**; este diseño añade el **bloqueo previo** porque E2E-07 lo exige («bloqueo backend y
  evento de auditoría») y porque el backend es la autoridad (P-05).
- `PAGADOR` no se construye: el pago es GOV-TRE-004 y no existe en Gobierno. Ver `DECISIONES.md` PDD-PROC11-02.
