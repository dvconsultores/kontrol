# CTL-01 · matriz de integración inicial de la guarda SoD (OD-CTL01-03)

Inventario de acciones críticas actuales de Gobierno, según el catálogo de auditoría (53 acciones `gov-*`):
- **Excluidas por ser de lectura o exportación:** `*_EXPORTED`, `GOV_AUDIT_PACKAGE_DOWNLOADED`.
- **Escrituras reales:** 45. Pertenecen a ORG-01 (3), ORG-02 (7), ORG-03 (8), DOC-02 (8), DOC-04 (6), CTL-04 (1), CTL-06 (9) y DOC-08 (3).
- **CURRENT_CRITICAL_ACTION_COUNT:** 45.

| Proceso | Función de servicio | Código SoD | Acción de auditoría (evidencia) | Objeto | Integrada en este ciclo |
|---|---|---|---|---|---|
| DOC-02 | `crear_acto` | DOC02_REGISTRAR | GOV_ACT_CREATED | GovernmentAct | Sí (solo como A: crea el objeto) |
| DOC-02 | `modificar_acto` | DOC02_EDITAR | GOV_ACT_UPDATED | GovernmentAct | Sí |
| DOC-02 | `emitir_acto` | DOC02_EMITIR | GOV_ACT_ISSUED | GovernmentAct | Sí |
| DOC-02 | `registrar_eficacia` | DOC02_EFICACIA | GOV_ACT_EFFECTIVENESS_RECORDED | GovernmentAct | Sí |
| DOC-02 | `corregir_acto` | DOC02_CORREGIR | GOV_ACT_CORRECTED | GovernmentAct | Sí |
| DOC-02 | `revocar_acto` | DOC02_REVOCAR | GOV_ACT_REVOKED | GovernmentAct | Sí |
| DOC-02 | `anular_acto` | DOC02_ANULAR | GOV_ACT_NULLIFIED | GovernmentAct | Sí |
| CTL-06 | `registrar` | CTL06_REGISTRAR | GOV_FINDING_CREATED | GovernmentFinding | Sí (solo como A) |
| CTL-06 | `agregar_recomendacion` | CTL06_RECOMENDAR | GOV_FINDING_RECOMMENDATION_ADDED | GovernmentFinding | Sí |
| CTL-06 | `agregar_accion` | CTL06_ACCION | GOV_CORRECTIVE_ACTION_ADDED | GovernmentFinding | Sí |
| CTL-06 | `registrar_plan` | CTL06_PLAN | GOV_FINDING_PLAN_REGISTERED | GovernmentFinding | Sí |
| CTL-06 | `iniciar_ejecucion` | CTL06_EJECUCION | GOV_FINDING_REMEDIATION_STARTED | GovernmentFinding | Sí |
| CTL-06 | `registrar_avance` | CTL06_AVANCE | GOV_CORRECTIVE_ACTION_PROGRESS_RECORDED | GovernmentFinding | Sí |
| CTL-06 | `presentar` | CTL06_PRESENTAR | GOV_FINDING_SUBMITTED | GovernmentFinding | Sí |
| CTL-06 | `verificar` | CTL06_VERIFICAR | GOV_FINDING_VERIFIED | GovernmentFinding | Sí (además del maker-checker de dominio, que prevalece) |
| CTL-06 | `devolver` | CTL06_DEVOLVER | GOV_FINDING_RETURNED | GovernmentFinding | Sí |
| ORG-01/02/03, DOC-04, CTL-04, DOC-08 | — | — | — | — | No en este ciclo; el catálogo es extensible |

**Resultado:**
- INITIAL_SOD_INTEGRATED_PROCESSES = 2 (DOC-02 y CTL-06).
- INITIAL_SOD_INTEGRATED_ACTIONS = 16.
