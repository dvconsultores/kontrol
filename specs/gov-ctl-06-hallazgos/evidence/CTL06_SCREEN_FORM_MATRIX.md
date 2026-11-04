# GOV-CTL-06 · CTL06_SCREEN_FORM_MATRIX (ficha de pantallas y formularios)

CTL-06 tiene:
- tres pantallas: listado, alta y ficha;
- un componente de plan de acción, dentro de la ficha;
- cinco formularios de escritura: alta, recomendación, acción, avance y verificación/devolución;
- además, el botón «Registrar hallazgo» en la muestra de CTL-04.

| Campo | S1 · Hallazgos (listado) | S2 · Registrar hallazgo | S3 · Ficha del hallazgo | S4 · Plan de acción (en S3) |
|---|---|---|---|---|
| SCREEN_ID | `HallazgosPage` | `RegistrarHallazgoPage` | `HallazgoPage` | `PlanDeAccion` |
| PROCESS_STEP | consulta y seguimiento | ABIERTO (alta) | todas las transiciones | ABIERTO (plan) · EN_REMEDIACION (avances) |
| USER_GOAL | ver qué hay abierto, vencido o pendiente de verificar, y exportar el plan | registrar un hallazgo con su origen y sus atributos | seguir el hallazgo, avanzarlo de estado, verificarlo o devolverlo, y ver su historia | formular recomendaciones y acciones con responsable y fecha, registrar avances con evidencia |
| MENU_PATH | Gobierno › Hallazgos y acciones correctivas | «Registrar hallazgo» en S1 o en la muestra de CTL-04 (`?muestra=<id>`) | código del hallazgo en S1 | sección de S3 |
| ROLE | `gobierno_hallazgos:view` | `:manage` | `:view`; transiciones con `:manage`; verificar y devolver con `:verify` | `:manage` |
| PRECONDITIONS | módulo gobierno | cargo VIGENTE del ejercicio para el plan; muestra de la empresa para el origen MUESTRA | — | estado ABIERTO o EN_REMEDIACION |
| FIELDS | H01–H08 resumidos; acciones (total) y vencidas | H02–H11 (spec §5) | H01–H12, V01, V02 | R01, A01–A04, P01–P03 |
| FILTERS | Estado, Riesgo, Origen, Buscar, «Solo con acciones vencidas»; indicadores como filtro | — | — | — |
| ACTIONS | Registrar hallazgo, Exportar plan (CSV), paginación | Registrar hallazgo, Cancelar | Registrar plan, Iniciar ejecución, Presentar a verificación, Verificar y cerrar, Devolver | Añadir recomendación, Añadir acción correctiva, adjuntar evidencia, Registrar avance |
| STATES | cargando, sin acceso, módulo no habilitado, vacío con o sin filtros, error con reintento | sin acceso, errores de campo y generales (`role=alert`), muestra no disponible | cargando, no encontrado, módulo no habilitado, conflicto de versión, autoverificación rechazada | sin cargos vigentes, sin recomendaciones, sin acciones, vencida, completada |
| PERMISSIONS | backend: permiso → empresa → módulo | ídem; escritura permitida por la licencia | `:verify` es SENSITIVE (MFA) | ídem |
| DOCUMENTS | — | — | evidencia congelada al cerrar (`freeze_links`) | `AdjuntosPanel` (`GovernmentCorrectiveAction`, Spec 046, analizador) |
| AUDIT | `GOV_FINDINGS_EXPORTED` | `GOV_FINDING_CREATED` | PLAN_REGISTERED, REMEDIATION_STARTED, SUBMITTED, VERIFIED, RETURNED | RECOMMENDATION_ADDED, CORRECTIVE_ACTION_ADDED, CORRECTIVE_ACTION_PROGRESS_RECORDED |
| ERRORS | 403 / 422 de filtros | 422 VALIDATION_ERROR, GOV_FINDING_SOURCE_INVALID | 404, 409 STALE / INVALID_STATE / PLAN_INCOMPLETE / ACTIONS_INCOMPLETE / SELF_VERIFICATION, 428 | 422 RESPONSIBLE_INVALID / TARGET_DATE_INVALID / RECOMMENDATION_INVALID / PROGRESS_INVALID / EVIDENCE_REQUIRED / EVIDENCE_INVALID |
| RESPONSIVE | tabla en región con desplazamiento propio; 320 px sin desbordar | campos apilados | ídem | ídem |
| ACCESSIBILITY | caption, región «Tabla de hallazgos», `aria-pressed` en los indicadores | legend de origen y partidas; etiquetas con «(obligatorio)» | pasos con `aria-current="step"`, región «Historia del hallazgo …» | artículos por acción, `role=alert`, labels por acción |
| E2E | CTL6-E2E-02 a 04 | CTL6-E2E-01 | CTL6-E2E-01 y 04 | CTL6-E2E-01 |

MISSING_REQUIRED_FIELDS = 0 · formularios de escritura: 5 · faltantes: 0.
