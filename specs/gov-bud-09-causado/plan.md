# Plan · GOV-BUD-09 Causado

## Constitution gate

| Compuerta | Estado |
|---|---|
| Autorización expresa que nombra BUD-09 | PASS (encargo 2026-11-17) |
| MATERIAL OQ | 0 (OD-BUD09-01/02 decididas) |
| Contradicciones | 0. WARN de CTL-01 se difiere por decisión de la dueña |
| Migración | Sí: `0123_gov_bud09_causado`. No se toca ninguna migración publicada |
| Cero hardcode | Diseño paramétrico (§2). Sin valores institucionales |

## 1. Modelo de datos (migración 0123)

| Tabla | Propósito | Claves |
|---|---|---|
| `gov_budget_cause_settings` | Configuración del ente: patrón de numeración | 1 fila por empresa; `patron` con marcadores `{ANIO}` y `{NUMERO:n}`, y prefijo libre |
| `gov_budget_causing_policies` | CAUSING_POLICY versionada | `codigo`, `tipo_gasto`, `nombre`, `disparador`, `requiere_recepcion/valuacion/conformidad`, `competencia_accion`/`competencia_materia`, `vigente_desde/hasta`, `fundamento`, `acto_id` (opcional), `tipo_regla`, `estado`, `version` |
| `gov_budget_causing_policy_documents` | RequiredDocument | `document_type_id`, `obligatorio`, `etapa` (PREPARACION, FORMALIZACION), `condicion` |
| `gov_budget_causing_policy_history` | Historia inmutable de la política | Instantánea por cambio |
| `gov_budget_causes` | El causado | `commitment_id` (FK, obligatorio), `policy_id` + instantánea de versión, `numero`, `codigo` (al formalizar), `estado` BORRADOR/FORMALIZADO/ANULADO, `fecha_efectiva`, `registrado_en`, `moneda` (= la del compromiso), `monto`, `concepto`, `beneficiario`, `source_resource_type/id`, autoridad (cargo y funcionario, en instantánea), `formalizado_por/en`, `snapshot`, `huella`, anulación, `version` |
| `gov_budget_cause_lines` | Imputación a líneas del compromiso | `commitment_line_id`, `monto > 0`, única por causado y línea |
| `gov_budget_cause_evidences` | Evidencias tipadas | `resource_type` ∈ {CONTRACT_RECEIPT, CONTRACT_VALUATION, CONTRACT_DELIVERY, CONTRACT_INVOICE, DOCUMENT}, `resource_id`, `snapshot` (estado, fecha, título, sha256) |
| `gov_budget_cause_history` | Historia append-only del causado | Evento, actor, instantánea |

**Protección de la historia.** En PostgreSQL, disparadores de inmutabilidad para el causado formalizado, sus líneas y evidencias y las historias, siguiendo el patrón de `GOV_BUDGET_COMMITMENTS_IMMUTABLE_PG`. La única transición permitida tras formalizar es FORMALIZADO → ANULADO.

**CTL-01.** `PROCESOS_SOD` gana `BUD-09`: la migración reemplaza su CHECK. El catálogo de CTL-01 añade el proceso BUD-09 con las acciones `BUD08_COMPROMETER` y `BUD09_CAUSAR`. El actor de `BUD08_COMPROMETER` sale de un resolvedor (`emitido_por` del compromiso), porque BUD-08 audita la emisión sobre el ejercicio.

## 2. Parametrización (clase de cada regla)

| Regla | Clase | Dónde |
|---|---|---|
| R1 compromiso existente; R2 no exceder; R4 fecha efectiva ≠ registro y dentro del ejercicio; R6 inmutabilidad | Invariante de plataforma (integridad presupuestaria, N03) | Código |
| Disparador, recepción/valuación/conformidad, documentos exigidos, competencia | INSTITUTIONAL_POLICY | `gov_budget_causing_policies` (+ documentos) |
| Separación comprometer/causar | INSTITUTIONAL_POLICY (CTL-01; pasará a LEGAL_MANDATORY si una norma verificada lo exige) | `gov_sod_rules` |
| Patrón de numeración | OPERATIONAL_CONFIGURATION | `gov_budget_cause_settings` |
| Asiento contable (N36) | Fuera de alcance; futura NormativeRule | — |

**Disparadores.** Catálogo de producto de las evidencias que el sistema sabe verificar: `RECEIPT_ACCEPTED`, `VALUATION_APPROVED`, `DELIVERY_ACCEPTED`, `INVOICE_CONFORMED` y `DOCUMENTARY` (solo documentos de los tipos configurados). Es mecánica de plataforma, ampliable con nuevos tipos de evidencia. El ente elige cuál aplica a cada tipo de gasto.

## 3. API (`/api/v1/gobierno/presupuesto`)

| Método | Ruta | Permiso | MFA |
|---|---|---|---|
| GET/PUT | `/causados/configuracion` | view / cause_policy | — |
| GET/POST | `/politicas-causado` | view / cause_policy | — |
| GET/PUT | `/politicas-causado/{id}` (PUT con If-Match, solo BORRADOR) | view / cause_policy | — |
| POST | `/politicas-causado/{id}/activar` · `/cerrar` | cause_policy | sí |
| GET | `/ejercicios/{year_id}/causados` (filtros) · `.csv` | view | — |
| GET | `/ejercicios/{year_id}/causados/opciones` (compromisos con saldo por línea, políticas vigentes, evidencias candidatas, documentos, cargos) | view | — |
| POST | `/ejercicios/{year_id}/causados` (borrador) | cause | — |
| GET/PUT | `/causados/{id}` (PUT If-Match, solo BORRADOR) | view / cause | — |
| GET | `/causados/{id}/controles` | view | — |
| POST | `/causados/{id}/formalizar` · `/anular` | cause | sí |

Las acciones nuevas del catálogo de permisos son `gobierno_presupuesto:cause` y `gobierno_presupuesto:cause_policy`, ambas con MFA para las operaciones críticas. Se actualizan la política MFA, la delegación y las semillas, igual que con `commit`.

## 4. Frontend

| Pieza | Ruta | Contenido |
|---|---|---|
| Menú | Gobierno › «Causados» y «Políticas de causado» | Superficie GOVERNMENT (segmento `gobierno`) |
| CausadosPage | `/gobierno/presupuesto/causados` | Selector de ejercicio, filtros, tabla, CSV y «Nuevo causado» |
| CausadoFormulario | dentro de la página (diálogo o panel) | Compromiso → saldo por línea → política → montos → fecha efectiva → evidencias → documentos → guardar borrador |
| CausadoDetallePage | `/gobierno/presupuesto/causados/:id` | Qué, contra qué compromiso, cuánto, cuánto queda, qué lo respalda, qué falta (controles), autoridad, qué sigue; formalizar y anular; historia |
| PoliticasCausadoPage | `/gobierno/presupuesto/politicas-causado` | Lista, crear/editar borrador, documentos exigidos, activar/cerrar con fundamento (+ acto opcional) y numeración |

Se reutilizan `LoadingState`, `EmptyState`, `ErrorState`, `ConfirmationDialog`, `Button`, `AdjuntosPanel` y el flujo canónico de reautenticación de `apiFetch`.

## 5. Compatibilidad con el motor de procesos

| Componente | En BUD-09 |
|---|---|
| ProcessDefinition / Version | Política de causado versionada (definición por tipo de gasto) |
| Stages / Transitions | BORRADOR → FORMALIZADO → ANULADO (tabla de transiciones en el servicio) |
| AuthorityBinding | Competencia de la política, con validación de vigencia |
| DOCUMENT_RULES / EVIDENCE_RULES | Documentos exigidos y `requiere_*` + disparador |
| CONTROL_RULES | Controles R1–R4 de «revisar controles» |
| SOD_RULES | CTL-01 (proceso BUD-09) |
| RESPONSIBILITY_BINDING | Autoridad en instantánea (cargo, funcionario, unidad, vigencia) |
| NORMATIVE_BINDING | `fundamento` + `tipo_regla`; NormativeRule futura (N36) |
| TENANT_POLICY | Política, configuración y regla SoD por empresa |

## 6. Pruebas

- **Backend:** los casos del encargo §31; carrera de dos formalizaciones sobre el último saldo (solo PG); disparadores de inmutabilidad (PG); anulación de compromiso con causados (409).
- **Mutaciones:** sobre-causado, evidencia, autoridad, tenant y bloqueo.
- **Vitest:** los estados del encargo §33.
- **E2E `gobierno-causado`:** la dueña configura la política, prepara, formaliza, consulta el detalle y la historia, y prueba el exceso y la falta de evidencia; a 1280/390/320 px con Axe.
- **Humo UAT:** añadir las dos pantallas a la lista fija.
