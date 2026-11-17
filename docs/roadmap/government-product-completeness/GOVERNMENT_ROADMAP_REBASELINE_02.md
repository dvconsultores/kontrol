# Rebaseline 02 del roadmap de KONTROL Gobierno (GOV-ROADMAP-REBASELINE-02)

| Campo | Valor |
|---|---|
| Fecha | 2026-11-16 |
| Programador | P1 |
| Entrada | `39a1db0` (alembic `0122_gov_cnt07_terminacion`, 1 cabeza) |
| Ciclo | Arquitectura, roadmap, clasificación y documentación |
| Producto nuevo | 0. Este ciclo no implementa ningún proceso, motor ni migración |

KONTROL Gobierno queda definido como un **producto nacional para la Administración Pública venezolana**:
- cero hardcode institucional;
- procesos y normativa versionados;
- configuración por tenant e integraciones desacopladas;
- capacidad de ayudar a cada institución a definir, corregir, documentar, parametrizar y automatizar sus procesos.

Todo ello sin convertir la realidad particular de Naguanagua, el primer tenant, en código de producto.

## 1. Mapa de autoridades (sin duplicados)

| Concepto | Autoridad | Nota |
|---|---|---|
| Estado de cada uno de los 122 procesos | `GOVERNMENT_PRODUCT_COMPLETENESS_MATRIX.csv` | `CURRENT_REAL_STATUS` (histórico) y `REBASELINE_02_STATUS` (vigente para planificar). El `.md` se genera |
| Reauditoría de los 48 BLOCKED | `GOVERNMENT_BLOCKED_REAUDIT.csv` (+ `.md`) | Una fila por proceso con los campos del encargo |
| Reauditoría de los 30 NOT_STARTED | `GOVERNMENT_NOT_STARTED_REAUDIT.csv` (+ `.md`) | Con nivel DAG |
| Qué es configuración y qué código | `GOVERNMENT_PARAMETERIZATION_POLICY.md` | Vinculante para toda GOV-SPEC |
| Motor de procesos | `GOVERNMENT_PROCESS_ENGINE_BASELINE.md` | Diseño, no implementado |
| Motor normativo | `GOVERNMENT_NORMATIVE_ENGINE_BASELINE.md` | Diseño, no implementado |
| Configuración por ente y organización | `GOVERNMENT_TENANT_CONFIGURATION_MODEL.md` | Diseño, no implementado |
| Arquitectura general de Gobierno | `docs/roadmap/government-architecture-baseline.md` | Sigue vigente; los tres baselines la amplían |
| Corpus normativo N01..N40 y clases | `docs/roadmap/kontrol-gobierno-source-register.md` | Sin cambio de clases |
| Catálogo de procesos listos | `OWNER_UAT_READY_CATALOG.md` | Sin cambio (44) |

## 2. Línea base canónica de entrada

```text
TOTAL_GOVERNMENT_PROCESSES=122   OWNER_UAT_READY=44 (incluye CNT-07 de P2)   BLOCKED=48   NOT_STARTED=30
OWNER_ACCEPTED (procesos de Gobierno)=0   OWNER_ACCEPTED_LICENSE_PROFILE=YES (frente de licencia, no es un proceso de los 122)
```

## 3. Resultado de la rebaseline

```text
De 122 procesos:
  44 están construidos y OWNER_UAT_READY (sin cambio).
  21 pueden construirse inmediatamente (BUILDABLE_NOW): todas sus dependencias internas ya son OWNER_UAT_READY.
  43 dependen solo de otros procesos KONTROL (WAITING_INTERNAL_DEPENDENCY).
   0 esperan solo configuración del ente (TENANT_CONFIGURATION_PENDING): la configuración no bloquea construir.
   4 necesitan validación normativa antes de que el proceso tenga valor (NORMATIVE_VALIDATION_PENDING).
  10 necesitan una integración externa real (EXTERNAL_INTEGRATION_PENDING); su capacidad genérica sí es construible.
   0 están verdaderamente bloqueados (TRUE_BLOCKED).
```

| Estado | Procesos |
|---|---|
| BUILDABLE_NOW (21) | ORG-05 BUD-07 BUD-09 BUD-10 BUD-11 REQ-01 PROC-01 PROC-04 PROC-05 CNT-06 WH-02 ACC-01 ACC-06 AST-01 DOC-01 DOC-06 DOC-07 CTL-08 DIG-01 HR-01 REP-04 |
| WAITING_INTERNAL_DEPENDENCY (43) | BUD-12 REQ-02..05 PROC-12 CNT-05 WH-01 WH-03..05 TRE-03..08 TRE-10 ACC-02..05 ACC-07 AST-03..11 DOC-03 DIG-02 HR-03 REP-01 REP-02 REP-05..09 REP-11 |
| NORMATIVE_VALIDATION_PENDING (4) | BUD-13 (ONAPRE), PROC-09 (conflicto LCP 31 / RLCP 35), AST-02 (SUDEBIP), INT-05 (formatos ONAPRE/ONCOP) |
| EXTERNAL_INTEGRATION_PENDING (10) | ACC-08 DOC-05 DIG-03 HR-02 INT-01 INT-02 INT-03 INT-04 INT-06 INT-07 |

**Contraste con la hipótesis de la dueña (≈28 / ≈12 / ≈8):**
- **Construibles: 21, no ≈28.** Siete procesos que parecían construibles dependen de otro proceso aún no hecho: tesorería necesita la orden de pago y esta el causado; contabilidad necesita el plan de cuentas; bienes y almacén necesitan su modelo base. Contarlos como construibles habría ocultado el orden real.
- **WAITING_INTERNAL_DEPENDENCY: 43.** La cifra crece porque ahora incluye los 26 NOT_STARTED que esperan cadena.
- **Externos: 10, cerca de ≈8.** Se suman DOC-05 y HR-02, cuya razón de ser es el conector.

**`TRUE_BLOCKED = 0`.** Ningún proceso carece de todo avance seguro. Los 4 normativos y los 10 externos tienen capacidad genérica construible. Lo que no puede hacerse es activar la regla legal concreta o conectar el servicio real.

## 4. Nuevo modelo de estado

Columnas añadidas a la matriz canónica, sin destruir las históricas:

```text
REBASELINE_02_STATUS  PRODUCT_IMPLEMENTATION_STATUS  TENANT_CONFIGURATION_STATUS  NORMATIVE_VALIDATION_STATUS
EXTERNAL_INTEGRATION_STATUS  PROCESS_ENGINE_IMPACT  NORMATIVE_ENGINE_IMPACT  TENANT_CONFIGURATION_IMPACT
DOCUMENTATION_OUTPUT  HARDCODE_AUDIT  DAG_LEVEL
```

`CURRENT_PRODUCT_STATUS ≠ FUTURE_ARCHITECTURE_STATUS`. Un proceso sigue OWNER_UAT_READY aunque esté `PROCESS_ENGINE_IMPACT = ADOPTION_PENDING`.

**Métricas** (separadas, sin porcentaje único):

```text
TOTAL_GOVERNMENT_PROCESSES=122   OWNER_UAT_READY=44   OWNER_ACCEPTED=0
BUILDABLE_NOW=21   WAITING_INTERNAL_DEPENDENCY=43   TENANT_CONFIGURATION_PENDING=0
NORMATIVE_VALIDATION_PENDING=4   EXTERNAL_INTEGRATION_PENDING=10   TRUE_BLOCKED=0
PROCESS_ENGINE_ADOPTION_PENDING=44 (los construidos, hasta la auditoría de P2)
ZERO_HARDCODE_COMPLIANT=NOT_YET_MEASURED (lo mide GOV-PARAMETERIZATION-AUDIT-01 de P2; aquí no se inventa)
NORMATIVE_VALIDATION_STATUS=PENDING en 37 procesos (9 de ellos ya OWNER_UAT_READY): citan alguna fuente de clase C
```

## 5. Cadena administrativa prioritaria

```text
REQUISICIÓN → DISPONIBILIDAD/RESERVA → CONTRATACIÓN → CONTRATO → RECEPCIÓN → CAUSADO → ORDEN DE PAGO → PAGO
→ CONTABILIDAD → ALMACÉN/BIENES → RENDICIÓN → REPORTES
```

| Eslabón | Ya READY | Falta para el recorrido E2E institucional |
|---|---|---|
| Requisición | — | **REQ-01** (BUILDABLE_NOW); REQ-02 (WAITING) |
| Disponibilidad / reserva | BUD-06 (certificación) | BUD-07 reserva (BUILDABLE_NOW, opcional por ente: D02-D) |
| Contratación | PROC-02, 03, 06, 07, 08, 10, 11 | **PROC-01** modalidad, **PROC-04** pliego, **PROC-05** contratistas (BUILDABLE_NOW) |
| Contrato | CNT-01, 02, 03, 04, 07, 08, 09; BUD-08 compromiso | CNT-06 términos económicos (BUILDABLE_NOW) |
| Recepción | CNT-03 (recepciones y valuaciones) | WH-01 ingreso a almacén (tras WH-02) |
| **Causado** | — | **BUD-09** (BUILDABLE_NOW): es la pieza que más desbloquea |
| Orden de pago → Pago | TRE-01, TRE-02, TRE-09 | TRE-03 → TRE-04 (+ TRE-05 retenciones) |
| Contabilidad | — | ACC-01 (BUILDABLE_NOW) → ACC-02 |
| Almacén / bienes | — | WH-02, AST-01 (BUILDABLE_NOW) |
| Rendición | CTL-05, CTL-09 | REP-09 (tras ORG-05) |
| Reportes | REP-03, REP-10 | REP-04 (BUILDABLE_NOW); REP-01 tras BUD-09/10 |

**Ruta crítica:** BUD-09 → TRE-03 → TRE-04 → {TRE-05, CNT-05, TRE-10, PROC-12, REP-01}. **BUD-09 desbloquea, de forma transitiva, 25 procesos.** El siguiente es AST-01, con 12.

## 6. Decisiones D-GOV sincronizadas

| D-GOV | Estado | Bloquea solo | No bloquea (se construye ya) |
|---|---|---|---|
| 01 Jurisdicción piloto | **CLOSED** (Naguanagua; lo local es parametrizable) | — | — |
| 02 Profundidad presupuestaria | **CLOSED** 2026-11-13 (A/1/1/1) | formulación completa (fase posterior) | modificaciones, reportes de ejecución, plantillas |
| 03 Alcance SNC | OPEN | conector real SNC/RNC (INT-03) y publicación SNC | expediente interno, pliego (PROC-04), maestro de contratistas (PROC-05), interfaz de adaptador, procedencia |
| 04 Plan de cuentas ONCOP | OPEN | plan oficial exacto, versión y exportación (ACC-08, INT-05) | libro mayor genérico, motor de mapeos, plan de cuentas versionado provisto por el ente (ACC-01) |
| 05 SUDEBIP 43.077 | OPEN | codificación oficial vigente y conector (AST-02, INT-04) | ciclo de vida genérico del bien (AST-01 y siguientes) |
| 06 Trámites tras G.O. 7.018 | OPEN | contenido del catálogo del ente | capacidad de catálogo versionado (DIG-01) |
| 07 Atenea | **SPONSOR_SCOPE_CLOSED**; TECHNICAL_CONTRACT_PENDING | importación de nómina (HR-02, INT-01) | estructura de cargos y plantillas presupuestarias de personal (HR-01) |
| 08 Firma e interoperabilidad | OPEN | firma real y servicios del Estado (DOC-05, INT-06/07, DIG-03) | evidencia de aprobación sin firma, capa de integración genérica |

```text
STALE_D_GOV_02_BLOCKERS=0
```

D-GOV-02 queda anotado como CLOSED en todas las autoridades vigentes de `docs/roadmap/`. Quedan como **evidencia histórica fechada, superada por esta rebaseline y sin reescribir**:
- las matrices de candidatos y desbloqueo de `specs/gov-0-06-identidad-usuarios/evidence/`, `specs/gov-norm-n40/evidence/` y `specs/gov-ctl-08-historial-maestros/evidence/`;
- `specs/gov-0-04-responsables/evidence/ORG05_TARGET_RESOURCE_MATRIX.md`;
- los cierres de PROC-11 y REP-03.

## 7. Integraciones: capacidad genérica frente a conector real

Arquitectura común:

```text
IntegrationContract  AdapterInterface  Mapping  Staging  Idempotency  RetryPolicy  Reconciliation  Audit
CredentialReference  Transport
```

La falta de un endpoint no impide construir la capacidad genérica (contrato, *staging*, idempotencia y conciliación). Solo el conector real espera. Las credenciales se guardan por ente, en secretos, nunca en código.

## 8. Los 44 OWNER_UAT_READY

- Se preservan sin cambio de estado.
- P2 los audita en `GOV-PARAMETERIZATION-AUDIT-01` (hardcode y parametrización). Cada uno quedará como `KEEP_AS_IS`, `ADAPT_TO_PROCESS_ENGINE` o `REFACTOR_HARDCODED_POLICY`.
- Hasta que P2 publique, la matriz marca `HARDCODE_AUDIT = PENDING_P2` y `PROCESS_ENGINE_IMPACT = ADOPTION_PENDING`. **No se inventa el resultado.**

## 9. Coordinación P1 / P2

| P1 (este ciclo) | P2 (en curso) |
|---|---|
| Roadmap de los 122, reauditoría de los 48 + 30, baselines de arquitectura (procesos, normativo, tenant) | Auditoría técnica de los 44 construidos, de hardcode y de parametrización |

`P1_P2_SCOPE_OVERLAP=0`. Cuando P2 publique, se integra su resultado en las columnas `HARDCODE_AUDIT` y `PROCESS_ENGINE_IMPACT` (merge ordinario).

## 10. Siguiente trabajo (candidatos; no se implementan en este ciclo)

```text
NEXT_P1_TARGET=BUD-09 Causado / devengado (P0, BUILDABLE_NOW, nivel DAG 1)
WHY=desbloquea 25 procesos (TRE-03 → TRE-04 → tesorería, contabilidad, reportes de ejecución, PROC-12); ruta crítica de la cadena
DEPENDENCIES=BUD-08 compromiso, CNT-03 valuaciones y recepciones (READY)
PARAMETERIZATION_REQUIREMENTS=documentos soporte para causar y momentos que lo activan, por tipo de gasto, como INSTITUTIONAL_POLICY del ente; sin constantes
PROCESS_ENGINE_COMPONENTS=StageDefinition/TransitionDefinition, AuthorityBinding (CAUSAR × PRESUPUESTO), RequiredDocument, ControlRule
  (no causar por encima de lo comprometido ni de lo recibido), SegregationRule (quien compromete no causa, si el ente lo adopta), ProcessHistory

NEXT_P2_TARGET=terminar GOV-PARAMETERIZATION-AUDIT-01; después, REQ-01 Requisición (P0, BUILDABLE_NOW), cabeza de la cadena E2E-01
WHY=sin requisición no hay recorrido completo; desbloquea REQ-02..05 y PROC-12; P2 conoce el dominio de contratación
DEPENDENCIES=ORG-02, ORG-07, BUD-06 (READY)
PARAMETERIZATION_REQUIREMENTS=tipos de requisición, campos por tipo, unidades solicitantes y aprobadores configurables
PROCESS_ENGINE_COMPONENTS=ProcessDefinition/Version, AuthorityBinding, ApprovalRule, RequiredDocument, NotificationRule
```

Ninguno de los dos solapa: P1 trabaja en presupuesto y tesorería; P2, en la auditoría y luego en la cabeza de contratación.

**Después, en orden de desbloqueo:**
- AST-01 (12 procesos);
- ACC-01 (9);
- ORG-05 (6; OQ-ORG05-01..03 CLOSED el 2026-11-16, `specs/gov-0-04-responsables/OWNER_DECISION.md`);
- WH-02 (4).

## 11. Ambiente de desarrollo

- kontrol-gob.globaldv.net es el ambiente de desarrollo de la dueña. Watchtower lo actualiza desde `:latest`; no es UAT formal.
- Este ciclo no toca `deploy/uat/*` ni el runbook, ni activa `UAT_DEPLOY_ENABLED`.
- Tras cada push se comprueba el build de `develop`. Si falla, Watchtower no actualiza el servidor.

## 12. Decisiones de la dueña posteriores (2026-11-16)

ORG-05 y CTL-08 quedan BUILDABLE_NOW sin condiciones:

```text
OQ-ORG05-01=CLOSED  PARAMETRIC_SUBJECT_TYPE (POSITION | PERSON | POSITION_AND_PERSON por resource_type y responsibility_type)
OQ-ORG05-02=CLOSED  TYPED_RESOURCE_ACCOUNT (BANK_ACCOUNT, ACCOUNTING_ACCOUNT, ACCOUNTABILITY_ACCOUNT; resource_type + resource_id; nunca cuenta_id sin tipo)
OQ-ORG05-03=CLOSED  DOMAIN_OWNERSHIP_PLUS_TRANSVERSAL_RESPONSIBILITY_BINDING (ONE_BUSINESS_AUTHORITY, MULTIPLE_READ_PROJECTIONS_ALLOWED)
OQ-CTL08-01=CLOSED  CONFIGURABLE_SENSITIVE_MASTER_TYPES (registro SensitiveMasterType; lista no cerrada en código)
```

Patrón común a los dos:

```text
DOMINIO PROPIETARIO → RECURSO TIPADO → BINDING / EVENTO TRANSVERSAL → CONFIGURACIÓN DEL TENANT → HISTORIA VERSIONADA
```

Las decisiones vinculantes están en `specs/gov-0-04-responsables/OWNER_DECISION.md` y `specs/gov-ctl-08-historial-maestros/OWNER_DECISION.md`. Son producto nacional: no se reinterpretan como reglas de Naguanagua.
