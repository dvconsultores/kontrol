# Government Process Engine · baseline de arquitectura (GOV-ROADMAP-REBASELINE-02)

**Autoridad sobre:** el modelo horizontal de procesos versionados de KONTROL Gobierno.
**Estado:** diseño de referencia; **no se implementa en este ciclo**. Cada proceso nuevo adopta los componentes que necesite. Los 44 ya construidos se adaptan según la auditoría de P2.
**Relación con lo existente:** amplía «Workflow Policy» y «State Machine Policy» de `government-architecture-baseline.md`; no las contradice. El código es el intérprete y la definición del proceso es dato versionado del ente (`GOVERNMENT_PARAMETERIZATION_POLICY.md` §3).

## 1. Componentes

| Grupo | Componente | Qué define | Pieza existente que lo anticipa |
|---|---|---|---|
| Definición | `ProcessDefinition` | El proceso como producto (p. ej. «Causado») y su código estable | Catálogo de procesos (`GOVERNMENT_PRODUCT_COMPLETENESS_MATRIX.csv`) |
| | `ProcessVersion` | La versión publicada que usa el ente, con vigencia; las instancias vivas conservan su versión | Versionado de cargos, unidades, actos y programación de caja |
| | `StageDefinition` | Etapas y estados, incluidos los finales | Máquinas de estado por proceso (tabla de transiciones en backend) |
| | `TransitionDefinition` | Transiciones permitidas, precondiciones y efecto; los finales no se reabren en silencio | Transiciones de expediente, contrato y hallazgo |
| Responsabilidad | `ResponsibilityBinding` | Quién responde de un objeto (cargo, persona o ambos, por tipo de recurso), con historia | Supervisor (CNT-04), autorizados (TRE-01), responsables del expediente (PROC-03); base de ORG-05 |
| | `AuthorityBinding` | Qué competencia (acción × materia × límite) exige cada transición | Matriz de autoridad ORG-03/ORG-07 |
| | `ApprovalRule` | Aprobaciones necesarias, orden y umbrales | Límites de firma de ORG-03 |
| Evidencia | `RequiredDocument` | Documentos exigidos por etapa y tipo | Documentos del expediente y de los actos |
| | `EvidenceRequirement` | Evidencia mínima para avanzar o cerrar | Paquetes de auditoría (DOC-08, CNT-08) |
| Control | `ControlRule` | Controles que impiden avanzar o cerrar | CTL-10 (`GovernmentClosurePolicy`), CTL-07 |
| | `SegregationRule` | Incompatibilidades del mismo actor en el mismo objeto | CTL-01 (`GovernmentSoDRule`), PROC-11 |
| Tiempo | `DeadlineRule` | Lapsos por etapa en días hábiles o continuos | Lapsos del expediente (PROC-03), alertas (CNT-09) |
| | `BusinessCalendar` | Días hábiles y feriados del ente, con procedencia | Nuevo: desbloquea DOC-03 |
| | `SuspensionRule` / `ExtensionRule` | Suspensiones y prórrogas como eventos | Prórrogas de contrato (CNT-02) |
| Excepciones | `ExceptionRule` / `EscalationRule` | Excepciones motivadas y escalamiento | Overrides con fundamento (REP-10) |
| | `NotificationRule` | A quién y cuándo se notifica | Alertas de contrato (`GovernmentContractAlertPolicy`) |
| Ente | `TenantPolicyProfile` | Paquete de políticas institucionales versionado | `GovernmentIdentityPolicy`, `GovernmentClosurePolicy` (precedentes) |
| | `TenantProcessConfiguration` | Qué versión de cada proceso usa el ente y con qué parámetros | Nuevo |
| Ejecución | `ProcessInstance` | Una ejecución concreta ligada a su `ProcessVersion` | Expediente de contratación, contrato, compromiso |
| | `ProcessHistory` | Historia append-only de transiciones con actor, autoridad y correlación | Bitácora institucional (CTL-02), historias por objeto |

## 2. Reglas de diseño

1. **El motor no conoce instituciones.** Resuelve actores por capacidad y competencia, nunca por nombre de unidad.
2. **Versión pinneada.** Una instancia termina con la versión con la que empezó. Una versión nueva rige para las instancias nuevas.
3. **Append-only.** Las correcciones son eventos o reversos; ningún estado final se reabre en silencio.
4. **Las reglas legales mandan** sobre la política del ente; la validación ocurre al publicar la versión (ver el motor normativo).
5. **El dominio sigue siendo dueño de sus datos.** Presupuesto, contrato y tesorería guardan sus objetos; el motor orquesta etapas, responsables, plazos y controles.
6. **Concurrencia:** cada transición bloquea su instancia (`FOR UPDATE` en PostgreSQL), como hoy.

## 3. Experiencia de usuario

**Funcionario.** Cada instancia responde:
- **qué debo hacer**: tarea y etapa;
- **qué necesito**: documentos y datos;
- **qué me falta**: requisitos sin cumplir;
- **quién revisa**: siguiente responsable;
- **qué sigue**: próxima etapa y plazo.

**Administración funcional.** El flujo es `GuidedConfiguration → Template → Validate → Preview → PublishVersion → Rollback`:
- se configura con asistentes y plantillas;
- se valida y se previsualiza antes de publicar;
- revertir es publicar la versión anterior como nueva.

No se entrega un editor BPMN vacío como producto.

## 4. Documentación institucional como salida

El mismo modelo alimenta `ProcessSheet`, `ProcedureManual`, `FlowDiagram`, `ResponsibilityMatrix`, `NormativeMatrix`, `ControlMatrix`, `EvidenceMatrix`, `RequiredDocuments` e `Indicators`. La documentación y el software salen de la misma definición, así que no divergen.

## 5. Adopción

- **Procesos nuevos.** Toda GOV-SPEC nueva declara qué componentes usa. El primero en adoptar `ResponsibilityBinding`, `DeadlineRule` y `ControlRule` fija el patrón.
- **Procesos construidos.** Se clasifican con la auditoría de P2 y se marcan en la matriz como `PROCESS_ENGINE_IMPACT = ADOPTION_PENDING` hasta entonces. Su estado OWNER_UAT_READY **no cambia** por la adopción futura (`CURRENT_PRODUCT_STATUS ≠ FUTURE_ARCHITECTURE_STATUS`).
- **Implementación del motor.** Será incremental, dentro de los procesos que lo consuman. Este baseline no autoriza un refactor grande.
