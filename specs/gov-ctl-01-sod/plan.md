# Plan · GOV-CTL-01 Matriz de segregación de funciones (CTL-01, GOV-CTL-001)

## Decisiones de arquitectura

| Id | Decisión | Razón |
|---|---|---|
| AD-CTL01-01 | `service_sod.py` (reglas, catálogo, guarda y consulta), `schemas_sod.py` y `api_sod.py` bajo `/gobierno/sod`; guardas permiso → empresa → módulo | Patrón de Gobierno |
| AD-CTL01-02 | El catálogo de acciones vive en código (`CATALOGO_SOD`), cerrado y por proceso, con la acción de auditoría que prueba cada una | Sin acciones en texto libre; extensible por proceso |
| AD-CTL01-03 | Una sola guarda, `evaluar_antes_de_actuar`. Los servicios de DOC-02 y CTL-06 la llaman justo antes de mutar, después de sus validaciones de dominio | Sin lógica SoD duplicada; el invariante de dominio prevalece |
| AD-CTL01-04 | La evidencia de la acción previa y del intento bloqueado es `AuditEvent`. No hay tabla de conflictos | El ledger ya es inmutable, por empresa y con actor; no se duplica |
| AD-CTL01-05 | La guarda bloquea la fila del objeto (`FOR UPDATE`) antes de evaluar | Serializa dos acciones del mismo objeto; impide pasar ambas a la vez |
| AD-CTL01-06 | Dos tablas (`gov_sod_rules` sin borrado; `gov_sod_rule_history` inmutable). Estados BORRADOR → VIGENTE → CERRADA; las reglas vigentes no se editan | Historia no destructiva (P-06); decisiones explicables con la regla de su momento (versión en el evento) |
| AD-CTL01-07 | El bloqueo se registra con `record_audit_after_rollback` (clase REJECTION) y responde 409 `GOV_SOD_CONFLICT` | Patrón OD-AUD-07: el intento sobrevive al rechazo |

## Decisiones de diseño (de Claude, dentro de las de la dueña)

- **PDD-CTL01-01:** el código es `SOD-<año de Caracas>-<nnnn>` por empresa. Si choca por concurrencia, 409 `GOV_SOD_RULE_CONFLICT`.
- **PDD-CTL01-02:** una acción creadora no puede ser B en una regla unidireccional.
- **PDD-CTL01-03:** no puede haber dos reglas VIGENTES con el mismo par en el mismo proceso. El par invertido cuenta si alguna de las dos es bidireccional.
- **PDD-CTL01-04:** la vigencia se evalúa con la fecha de negocio de Caracas (`hoy_de_negocio`). Una regla futura no bloquea todavía; una vencida ya no bloquea.
- **PDD-CTL01-05:** `view` y `manage` son STANDARD; `activate` es SENSITIVE.
- **PDD-CTL01-06:** el resumen de S1 cuenta los conflictos de los últimos 30 días de negocio.

## Puerta de la Constitución

| Compuerta | Valor |
|---|---|
| Rama / remotas / HEAD == origin | develop / 1 / 1 (`9dd2fe6`) |
| CTL01_REQUIREMENTS_COMPLETE · FULL_PROCESS_IMPLEMENTABLE | 1 · 1 |
| ORG06 · CTL02_DEPENDENCY_REQUIRED · SPEC045_WHOLE_ENGINE_REQUIRED | 0 · 0 · 0 |
| CRITICAL_ACTION_INVENTORY · INITIAL_INTEGRATION_MATRIX · SOD_RULE_CONTRACT · ACTION_CATALOG | 1 · 1 · 1 · 1 |
| SCOPE · PREVENTIVE_CHECK · ROLE_MATRIX · MENU · SCREEN_FORM_MATRIX · ERROR · CONCURRENCY · AUDIT · OWNER_UAT_SCENARIO | 1 (todos) |
| MATERIAL_BLOCKER · MATERIAL_OQ · UNKNOWN · CONTRADICTIONS | 0 · 0 · 0 · 0 |

**GATE = PASS.** Autorización de `implement`: el encargo GOV-CTL-FUNCTIONAL-03 de la dueña, que nombra CTL-01.
