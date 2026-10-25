# GOVERNMENT-ARCHITECTURE-BASELINE (2026-10-25)

> Línea base de **planificación y arquitectura** de KONTROL Gobierno, autorizada por OD-GSR-1 = B. **No autoriza
> implementación**, no crea GOV-SPEC y no inicia GOV-0. Base: `develop` `f036bd3`.

**Etiquetas de cada conclusión:**

| Etiqueta | Origen |
|---|---|
| **[OFF]** | OFFICIAL_REQUIREMENT, citando la norma N.. de la Biblioteca |
| **[PRJ]** | PROJECT_REQUIREMENT: Ingeniería de Requerimientos (IR) o documentación KONTROL |
| **[OWN]** | OWNER_DECISION |
| **[BP]** | INDUSTRY_BEST_PRACTICE |
| **[BM]** | BENCHMARK_FEATURE |
| **[REC]** | CLAUDE_RECOMMENDATION |

**Cómo leer [OFF] y [PRJ].** Ninguna norma se ha leído en su texto original para esta línea base. Las citas N.. son las que la propia IR asigna a cada requisito. Por eso [OFF] significa «exigido por la IR con esa norma como fuente», no una interpretación jurídica propia.

## Verdict
**GOVERNMENT_ARCHITECTURE_BASELINE_STATUS = CLOSED / PLANNING_BASELINE.**
- **GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0.**
- La línea base fija fronteras, contextos, contratos transversales y políticas.
- Todo lo que depende del sponsor (D-GOV-01..08), del freeze normativo (0/10) o de las fuentes de clase C queda marcado como BLOCKED o como LEGAL_VALIDATION_REQUIRED, sin inventar reglas.

## Repository
- `develop` = `origin/develop` = `f036bd3`.
- SPEC054 en IMPLEMENTED — CERTIFICATION PENDING (`c0216e8`).
- SPEC046 S3 con fallo cerrado (`91eae11`).
- Readiness BLOCKED (`a0ce7d7`, `f036bd3`).
- 9a41503 y el `.docx` SNAT intactos.

## Authority and Sources
Jerarquía (tu §4):
1. **Nivel 1:** fuentes oficiales venezolanas (inventario N01..N40 de la Biblioteca Normativa v1.0: 26 A · 2 B · 12 C).
2. **Nivel 2:** documentación KONTROL. En particular, la IR v1.0 (§1–17) y `docs/roadmap/kontrol-gobierno-source-register.md`.
3. **Nivel 3:** decisiones ratificadas de la dueña (OD-GOV-START-01, OD-S3-01, OD-GSR-1/2, OD-CERT-27..30).
4. **Nivel 4:** buenas prácticas y referencias de la industria. Nunca prevalecen sobre el nivel 1.

Fuentes leídas en solo lectura, con SHA-256 iguales al registro:
- `Ingenieria_de_Requerimientos_KONTROL_Gobierno_v1.0.pdf` (`8f86615f…`);
- `Biblioteca_Normativa_Oficial_KONTROL_Gobierno_v1.0.pdf` (`4a980bb9…`).

Además: la readiness, la matriz de deuda y el código del núcleo (`audit_events`, `KontrolError`, `storage`).

Las fuentes de clase C (N07–N10, N14–N17, N36–N38, N40) **no sustentan ninguna regla P0** hasta que haya pin oficial
(Biblioteca §1, regla de freeze). Para todas: **LEGAL_VALIDATION_REQUIRED = 1**.

## Product-Line Boundaries
- **[PRJ] P-02 (IR §1–2):** separación Empresarial/Gobierno.
  - No se añaden filas 058+ a MASTER57 ni flags «gobierno» dentro de las Specs empresariales.
  - «Reutilizar componentes técnicos de KONTROL Empresarial no implica reutilizar automáticamente reglas de negocio» (IR §6).
- **[PRJ] Exclusiones v1.0 (IR §3.1):** tributación municipal integral, nómina completa (queda en Atenea), BIM, gestión judicial, plataforma ciudadana completa y requisitos propios de un organismo convertidos en comportamiento global.
- **[REC] Forma de entrega:**
  - Gobierno es un **perfil de instalación** con módulos propios (`gov_*`), sobre el núcleo compartido;
  - los módulos privados no se activan en una instalación de Gobierno salvo que una decisión lo apruebe expresamente;
  - el licenciamiento por instalación (004) distingue la línea.
  - Es un compromiso de arquitectura, y su ratificación entra en el paquete de preguntas: OQ-GAB-1.

Clasificación de capacidades (tu §5):

| Capacidad | Clase |
|---|---|
| Identidad, sesiones, MFA | SHARED_CORE |
| RBAC (permisos, roles, alcance) | SHARED_CORE (motor) · el alcance institucional es GOVERNMENT_ONLY |
| Aprobaciones, SoD (045) | SHARED_CORE (motor) · las matrices por proceso son GOVERNMENT_ONLY |
| Auditoría (006/051) | SHARED_CORE, tras el endurecimiento |
| Documentos, ClamAV (046) | SHARED_CORE · el expediente y los actos administrativos son GOVERNMENT_ONLY |
| Notificaciones y tareas (047) | SHARED_CORE |
| Licenciamiento por instalación (004) | SHARED_CORE |
| Certificación de release (054) | SHARED_CORE |
| Organización | SHARED_CONTRACT_DIFFERENT_IMPLEMENTATION (empresa frente a organismo, ente y unidad) |
| Almacenes | SHARED_CONTRACT_DIFFERENT_IMPLEMENTATION (comercial frente a consumo) |
| Activos | SHARED_CONTRACT_DIFFERENT_IMPLEMENTATION (057 frente a bienes públicos) |
| Tesorería y bancos | SHARED_CONTRACT_DIFFERENT_IMPLEMENTATION |
| Reportes (050) | SHARED_CORE (motor y PDF) · los reportes institucionales son GOVERNMENT_ONLY |
| Presupuesto, contratación pública, contabilidad pública, rendición, trámites | GOVERNMENT_ONLY |
| Ventas, compras comerciales, fiscal SENIAT 039–043, importaciones | PRIVATE_ONLY |

## Context Map
Contextos de la IR §6 [PRJ]. Las entidades vienen del modelo lógico preliminar de la IR §9 [PRJ]; los eventos y las fronteras son [REC].

| Contexto | Responsabilidad | Agregados (frontera) | Fuente de verdad | Estados (IR §8) | Comandos | Eventos | Dependencias externas | Normas | Núcleo |
|---|---|---|---|---|---|---|---|---|---|
| **Government Core** | ente, ejercicio, unidades, autoridades, actos, configuración normativa | GovernmentEntity, GovernmentUnit, AuthorityGrant, AppointmentAct, NormativeSource/Version, RuleBinding, TenantPolicy | Government Core | autoridad con vigencia (desde/hasta), versionada | crear ente o unidad; otorgar/revocar autoridad; registrar acto; publicar versión normativa | AuthorityGranted/Revoked, NormativeVersionPublished | — | N01–N03, N24, N25 | identidad, RBAC, auditoría |
| **Budget Ledger** | plan, clasificadores, presupuesto, disponibilidad, modificaciones, compromiso, causado, ejecución | FiscalYear, BudgetClassifierVersion, BudgetVersion, BudgetCredit, BudgetModification, BudgetLedgerEntry (append-only) | Budget Ledger | presupuesto DRAFT→PROPOSED→APPROVED→OPEN→CLOSED; obligación COMMITTED→ACCRUED→PAYMENT_ORDERED→PAID | certificar disponibilidad; comprometer; causar; modificar | AvailabilityCertified, Committed, Accrued, BudgetModified | ONAPRE (exportación) | N03, N04, N07–N10 (C) | auditoría, aprobaciones, numeración |
| **Procurement** | requisición, procedimiento, oferta, evaluación, adjudicación, contrato, garantía | Requisition, ProcurementProcedure, Offer, Evaluation, AwardDecision, PublicContract, ContractAmendment, Guarantee, Milestone, AcceptanceAct | Procurement | requisición, contratación y contrato (IR §8) | registrar necesidad; abrir procedimiento; evaluar; adjudicar; contratar | RequisitionBudgetValidated, Awarded, Contracted, MilestoneAccepted | SNC/RNC (P1) | N11, N12 | documentos, aprobaciones, SoD |
| **Treasury & Public Accounting** | causado, pago, banco, retención, asiento, cierres, conciliación | Obligation, PaymentOrder, TreasuryPayment, BankAccount, BankReconciliation, PublicLedgerAccount, JournalEntry, ClosingPeriod | T&PA | obligación (IR §8); asientos inmutables (reverso) | ordenar pago; pagar (maker-checker); asentar; cerrar | PaymentOrdered, Paid, JournalPosted, PeriodClosed | bancos (P0), ONCOP | N03, N05, N06, N35, N36 (C), N38 (C) | auditoría, aprobaciones |
| **Public Assets** | bienes públicos, etiquetado, custodia, inventario físico, revalorización, baja | PublicAsset, AssetTag, AssetCustody, AssetLocation, AssetRevaluation, AssetDisposal | Public Assets | PROPOSED→INCORPORATED→ACTIVE→…→DISPOSED; nunca DELETED | incorporar; asignar custodio; transferir; revalorizar; desincorporar | AssetIncorporated, CustodyAssigned, AssetDisposed | SUDEBIP (P1, sin API inventada) | N13 (B), N14–N17 (C), N34 | documentos, auditoría |
| **Records & Audit** | expediente, documentos, firmas, auditoría, rendición, hallazgos, legal hold | AdministrativeCase, AdministrativeAct, Notification, SignatureEvidence, AuditEvent, AccountRenderingPackage, Finding, CorrectiveAction | R&A | expediente y hallazgo (IR §8) | abrir expediente; notificar; formar rendición; registrar hallazgo | CaseDecided, ActNotified, FindingOpened | firma electrónica (P1, D-GOV-08) | N18–N23, N25, N29 (B) | documentos y ClamAV, auditoría |
| **Digital Government** | trámites, interoperabilidad, notificaciones, contratos de datos | ProcedureCatalog, ProcedureRequest, InteropContract, ExternalDataReceipt | DG | trámite: solicitud→requisitos→subsanación→decisión→notificación→cierre (E2E-05) | solicitar; subsanar; decidir; notificar | ProcedureDecided, DataReceived | interoperabilidad del Estado (P0) | N25–N28, N40 (C) | notificaciones, documentos |
| **Integration Layer** | Atenea, bancos, SNC/RNC, SUDEBIP, ONAPRE/ONCOP, solo con contratos versionados | InteropContract, ExternalDataReceipt, IntegrationBatch | IL (procedencia) | lote recibido→validado→aplicado o rechazado (idempotente) | recibir lote; validar; aplicar | BatchReceived/Applied/Rejected | todas | N28, N40 (C) | idempotencia, auditoría |

**[REC] Reglas del mapa:**
- cada contexto es dueño de sus tablas;
- la comunicación entre contextos va por comandos de servicio o eventos de dominio dentro de la misma transacción cuando hace falta atomicidad (p. ej. Committed en Budget Ledger, a la vez que la orden en Procurement);
- ningún contexto escribe tablas de otro.

## Government Organization Model
Hipótesis de planificación de tu §6, **contrastada** con la IR:

| Concepto | Respaldo | Contrato conceptual [REC] |
|---|---|---|
| ORGANISMO / ENTE | [PRJ] GOV-ORG-001/002: tipo de ente nacional, estadal, municipal, instituto, servicio desconcentrado o descentralizado | `GovernmentEntity` = **unidad de aislamiento** (el «tenant» de Gobierno). Un organismo agrupa entes solo si D-GOV-01 lo confirma |
| UNIDAD EJECUTORA / ESTRUCTURA | [PRJ] GOV-ORG-002/008: órgano, unidad administrativa, unidad ejecutora local, dependencia, sede, centro gestor, con vigencia y por ejercicio | `GovernmentUnit` jerárquica y versionada por ejercicio (no reescribe expedientes cerrados) |
| AUTORIDAD | [PRJ] GOV-ORG-003/004: competencias y límites por **cargo**; delegación, suplencia y encargaduría con acto, vigencia y emisor | `AuthorityGrant` (cargo → competencia, límite, vigencia, acto) con soporte `AppointmentAct` |
| ROL / ALCANCE | [PRJ] GOV-ORG-005/007 | ver Roles × Actions |
| PRESUPUESTO / PARTIDA | [PRJ] GOV-BUD-*; [OFF] N03, N04, N10 (C) | Budget Ledger; la partida es `BudgetCredit` sobre una `BudgetClassifierVersion` |
| COMPROMISO / CAUSADO / PAGADO | [PRJ] GOV-BUD-012/013, IR §8 (obligación) | eventos del ledger; los reversos son eventos separados |
| CONTRATACIÓN PÚBLICA | [PRJ] GOV-PROC/CNT; [OFF] N11, N12 | Procurement |
| BIENES PÚBLICOS | [PRJ] GOV-AST; [OFF] N13 (B), N14–N17 (C) | Public Assets |
| RESPONSABILIDAD ADMINISTRATIVA | [PRJ] GOV-ORG-006 (responsables con historia), GOV-CTL-011 (actas de entrega) | responsabilidad registrada con historia sobre cada objeto custodiado |
| RENDICIÓN / CONTROL | [PRJ] GOV-CTL-006/007; [OFF] N18, N21 | Records & Audit |

**Reconciliación.**
- La cadena de tu §6 es coherente con el flujo del caso E2E-01 de la IR:

  ```
  necesidad → disponibilidad → procedimiento → evaluación → adjudicación → contrato
            → recepción → causado → pago → asiento → rendición
  ```

- Hay dos matices:
  - la contratación **precede** al compromiso definitivo, y la disponibilidad se certifica antes (GOV-BUD-010, GOV-REQ-002);
  - los bienes públicos nacen de la recepción o de otros orígenes (GOV-AST-004), no solo del pago.
- El orden exacto entre compromiso y contrato en cada modalidad es **LEGAL_VALIDATION_REQUIRED** (N03, N11, N12).

## Shared Core Classification
| Componente | Clasificación | Motivo |
|---|---|---|
| identity | REUSABLE_AFTER_SHARED_CORE_DELTA | falta MFA (RNF-GOV-011) |
| sessions (002) | REUSABLE_AFTER_SHARED_CORE_DELTA | política de sesión para roles privilegiados, junto con MFA |
| RBAC (003) | REUSABLE_AFTER_SHARED_CORE_DELTA | techo de delegación (OD-GSR-2) y alcance por autoridad o cargo |
| approvals (045) | REUSABLE_AS_IS (motor) | las matrices y los niveles por proceso son GOVERNMENT_ONLY |
| SoD (045) | REUSABLE_AS_IS (motor) | las reglas SoD por proceso (GOV-CTL-001) son GOVERNMENT_ONLY |
| audit (006/051) | REUSABLE_AFTER_SHARED_CORE_DELTA | catálogo de eventos (DT-06); faltan autoridad institucional, versión normativa, estado de flujo y correlación |
| documents (046) | REUSABLE_AS_IS (almacén, versiones, enlaces) | expediente y actos son GOVERNMENT_ONLY; la retención y el legal hold necesitan contrato (RNF-GOV-018) |
| ClamAV (046) | REUSABLE_AS_IS | OBS-09 sigue como puerta externa de la imagen |
| notifications (047) | REUSABLE_AS_IS | la notificación administrativa con lapsos (GOV-DOC-005) es GOVERNMENT_ONLY |
| licensing (004) | REUSABLE_AS_IS | perfil de instalación Gobierno (OQ-GAB-1) |
| release certification (054) | REUSABLE_AS_IS | pendiente del RC 0 oficial; cruzado de navegadores por eliminar (ver Cross-Browser) |
| database baseline | REUSABLE_AS_IS | PostgreSQL 16, una cabeza de migración, NUMERIC |
| API infrastructure | REUSABLE_AFTER_SHARED_CORE_DELTA | 422 ante parámetros no declarados (OD-GSR-2) |
| frontend shell (005) | REUSABLE_AFTER_SHARED_CORE_DELTA | estados de pantalla de tu §16, `UnsavedChangesGuard` (DT-17) y zona America/Caracas |
| i18n | REUSABLE_AS_IS | `src/i18n` (es) |
| reporting (050) | SHARED_CONTRACT_DIFFERENT_IMPLEMENTATION | motor y PDF compartidos; reportes, trazabilidad y paquete de auditoría de Gobierno |

## Shared Core Hardening Dependencies
**SHARED_CORE_HARDENING_DEPENDENCY_MAP** (OD-GSR-2 = A: se resuelve antes de GOV-0, en las Specs dueñas, sin código en este ciclo):

| # | Gap | Spec dueña | Deuda | Decisión | Delta requerida | Dependencia de Gobierno | Etapa que bloquea |
|---|---|---|---|---|---|---|---|
| 1 | RNF-GOV-011 MFA para roles privilegiados | 002 / 003 | MFA no construido (`users.mfa_enabled` sin uso) | [OWN] obligatorio en Gobierno; la política exacta (TOTP u otro, recuperación, roles) entra en OQ-GAB-2 | MFA en el núcleo con política por rol privilegiado | GOV-ORG-005, GOV-CTL-004, RNF-GOV-011 | GOV-0 |
| 2 | RNF-GOV-012 techo de delegación | 003 | ROLES-SIN-TECHO-DE-DELEGACION | [OWN] solo se delegan permisos que el actor posee | validar la delegación contra los permisos efectivos del delegante, más pruebas hostiles | GOV-ORG-003/004, RNF-GOV-012 | GOV-0 |
| 3 | RNF-GOV-003 America/Caracas | 001 / 005 | FECHAS-ZONA-DE-PRESENTACION, POLICY-CLOCK-LOCAL | [OWN] fecha civil de negocio = America/Caracas; timestamps técnicos en UTC | una política transversal de día civil en backend y presentación | todo el Budget Ledger y los cierres | GOV-0 |
| 4 | RNF-GOV-005 auditabilidad completa | 006 / 051 (+046) | DT-06, AUDIT-DETAIL-NO-IMPLEMENTADO, DOCUMENT-SCAN-REJECTION-AUDIT-NOT-PERSISTED | [OWN] catálogo de eventos de 006/051; el rechazo de análisis se audita en sesión independiente | catálogo, campos de contexto y append-only (ver Audit Architecture) | GOV-CTL-002/003/010, RNF-GOV-005 | GOV-0 |
| 5 | RNF-GOV-015 errores deterministas | 001 | API-QUERY-SILENCIOSA, LISTADOS-SIN-RESPONSE-MODEL | [OWN] parámetros no declarados → 422 (rompe 27 de 224 E2E, que se adaptan) | validación de consulta en la capa API y `response_model` en los listados | RNF-GOV-015, GOV-DIG-004 | GOV-0 |
| 6 | RNF-GOV-010 backup/restore y RTO/RPO | 053 | «sin verificación de restauración» | sin decisión pendiente; las cifras RTO/RPO dependen del contrato de instalación (no se inventan) | restauración verificada y automatizada, con evidencia (E2E-08) | RNF-GOV-010, E2E-08 | antes de producción de GOV-0 (piloto) |
| 7 | RNF-GOV-001 aislamiento por ente | 003 / 007 / 008 (requisitos previos del núcleo) + modelo GOVERNMENT_ONLY | WAREHOUSE-CROSS-COMPANY-FILAS-EXISTENTES, WAREHOUSE-BRANCH-*, API-COMPANY-ID-EN-CONSULTA | las D de almacenes siguen abiertas (fuera del paquete OD-GSR-2) | contratos de alcance de esta línea base y arnés de pruebas hostiles reutilizable | GOV-ORG-001/007, E2E-06 | GOV-0 |

**[REC] Orden del programa SHARED-CORE-GOVERNMENT-P0-HARDENING:**

| Orden | Gap | Por qué en este lugar |
|---|---|---|
| 1 | MFA (#1) | seguridad; sin dependencias |
| 2 | Techo de delegación (#2) | seguridad; usa el modelo de permisos efectivos |
| 3 | America/Caracas (#3) | toca muchas pantallas; conviene antes de tocar la auditoría |
| 4 | Auditoría (#4) | se apoya en el día civil (#3) para el campo de fecha de negocio |
| 5 | 422 (#5) | rompe 27 E2E; mejor tras estabilizar los contratos de auditoría |
| 6 | Restauración (#6) | independiente del resto |
| 7 | Aislamiento por ente (#7) | arnés hostil; depende de #2 y #4 |

Este orden coincide con tu §41. La única precisión es que #4 depende de #3.

## Tenant / Organization Isolation
- **[PRJ] RNF-GOV-001 (P0):** aislamiento de datos, llaves, configuración y permisos por ente, con pruebas hostiles obligatorias.
- **[PRJ] GOV-ORG-001:** «sin compartir reglas entre tenants por defecto».
- **[PRJ] GOV-ORG-007:** «el frontend nunca decide company/ente scope».

No se copia la multiempresa privada:
- la empresa privada es una **entidad comercial** dentro de una instalación;
- el ente es una **persona jurídica pública** con autoridad, presupuesto y normativa propios.

[REC] Contratos:

| Contrato | Definición |
|---|---|
| **TENANT_SCOPE_CONTRACT** | La instalación de Gobierno aloja uno o más `GovernmentEntity`. Cada fila de Gobierno lleva `entity_id NOT NULL` con FK; las consultas se filtran en el **backend** por el `entity_id` del contexto autenticado; no existe un parámetro de cliente que lo elija (en línea con API-COMPANY-ID-EN-CONSULTA). La configuración, el perfil normativo (`TenantPolicy`), la numeración, el espacio de documentos (`storage_key` con prefijo de ente) y la auditoría van **por ente**. Las llaves y secretos de integración son por ente cuando la integración lo sea (bancos) |
| **ORG_SCOPE_CONTRACT** | El alcance del usuario dentro del ente es un conjunto de `GovernmentUnit` (con herencia jerárquica explícita, nunca implícita), validado en el backend en cada comando y consulta |
| **AUTHORITY_SCOPE_CONTRACT** | Una acción que exige competencia (comprometer, causar, ordenar, pagar, adjudicar, desincorporar) requiere un `AuthorityGrant` **vigente** en la fecha civil de la operación, del cargo que ocupa el actor, dentro de su límite (monto, unidad, tipo) y con su acto soporte. Sin grant vigente, la acción se deniega con un error determinista y se audita |

**Requisitos de pruebas hostiles ([PRJ] E2E-06/07; [REC] matriz):**

| Escenario | Qué se prueba |
|---|---|
| cross-organismo | usuario de A sobre B |
| cross-ente | leer, aprobar, pagar o desincorporar en B |
| cross-unidad-ejecutora | fuera del alcance de unidad |
| cross-authority | operar sin grant, con el grant vencido o por encima del límite |

En cada caso el resultado esperado es 100 % denegado en el backend, con un evento de auditoría y sin filtrar datos en el error.

## Authentication
- **[PRJ] RNF-GOV-011:** MFA para roles privilegiados, secretos fuera del código, rotación de credenciales.
- **[OWN] OD-GSR-2:** se resuelve en el núcleo antes de GOV-0.
- **[REC] Frontera:** la autenticación es SHARED_CORE (identidad única por persona); Gobierno añade la vinculación persona → cargo → ente.
- **[REC] Roles privilegiados:**
  - administrador técnico, administradores de seguridad y cualquier rol con competencia para comprometer, pagar o desincorporar;
  - tienen MFA obligatorio, sesión de vida más corta y reautenticación para acciones irreversibles.
- **[BP]** Los valores exactos de vida de sesión entran en OQ-GAB-2.

## Authorization
- **[PRJ] RNF-GOV-006:** toda autorización crítica se valida en el backend, sin confiar en la UI ni en claims sin verificación contextual.
- **[PRJ] RNF-GOV-012:** los roles predefinidos no conceden autoridad transversal.
- **[PRJ] GOV-CTL-004:** el administrador técnico no recibe autoridad funcional (IR §5).

[REC] Modelo de decisión: **permiso (RBAC del núcleo) ∧ alcance (ORG_SCOPE) ∧ autoridad vigente (AUTHORITY_SCOPE) ∧ precondición de estado ∧ SoD ∧ aprobación cuando proceda.**

| Aspecto | Regla |
|---|---|
| Delegación | [OWN] solo permisos que el actor posee. [PRJ] GOV-ORG-004: delegación, suplencia y encargaduría con acto, vigencia y emisor. [REC] Delegación temporal con `valid_from/valid_to`; la revocación tiene efecto inmediato y no reescribe la historia (las operaciones ya hechas conservan el grant con que se hicieron) |
| SoD | [PRJ] GOV-CTL-001: matriz por proceso y conflictos configurables; motor de 045 |

## Roles × Actions
**Separación de roles:**
- **Roles de plataforma (SHARED_CORE):** administrador técnico, administrador de seguridad, auditor de plataforma.
- **Roles institucionales (GOVERNMENT_ONLY):** máxima autoridad, autoridad delegada, cuentadante y responsable patrimonial. Los nombres finales dependen de D-GOV-01 y de la normativa del ente.
- **Roles de proceso (GOVERNMENT_ONLY):** los actores de la IR §5, de presupuesto a control interno.

Matriz conceptual [PRJ] IR §5, GOV-ORG-010, GOV-CTL-001, E2E-07 · [REC] columnas. Los nombres son provisionales:

| Rol | Capacidad | Acción | Recurso | Alcance | Precondición | Aprobación | SoD | Evento de auditoría | Denegación |
|---|---|---|---|---|---|---|---|---|---|
| Unidad requirente | requisición | registrar o enviar | Requisition | unidades propias | ejercicio OPEN | no | ≠ adjudicador, ≠ pagador | REQUISITION_SUBMITTED | 403 determinista + auditado |
| Planificación/Presupuesto | disponibilidad | certificar | BudgetCredit | ente | crédito disponible ≥ monto | según nivel (GOV-BUD-015) | ≠ requirente del mismo caso | AVAILABILITY_CERTIFIED | 409 si no hay disponible |
| Planificación/Presupuesto | presupuesto | comprometer | Obligation | ente | disponibilidad certificada, contrato u orden | sí | ≠ pagador | BUDGET_COMMITTED | 409 / 403 |
| Comisión de contrataciones | evaluación | evaluar o recomendar | Evaluation | procedimiento asignado | sin impedimento (GOV-PROC) | — | ≠ oferente vinculado | EVALUATION_RECORDED | 403 + auditado |
| Máxima autoridad / autoridad delegada | adjudicación | decidir | AwardDecision | competencia vigente | recomendación registrada | — | ≠ comisión cuando la política lo exija | AWARD_DECIDED | 403 sin grant vigente |
| Contabilidad | causado | causar | Obligation | ente | recepción o hito aceptado | según política | ≠ pagador | OBLIGATION_ACCRUED | 409 |
| Tesorería | pago | ordenar o pagar (maker-checker) | PaymentOrder / TreasuryPayment | ente | causado; sin duplicado (GOV-TRE-010) | checker distinto del maker (GOV-TRE-004) | maker ≠ checker | PAYMENT_ORDERED, PAID | 409 duplicado / 403 |
| Bienes/Patrimonio | bien | incorporar, transferir, desincorporar | PublicAsset | ente | acta o soporte | desincorporación con aprobación | ≠ custodio receptor | ASSET_* | 403 / 409 |
| Control interno/Auditoría | consulta | leer y muestrear (read-only) | todo el ente | ente | — | — | sin escritura funcional | AUDIT_ACCESS | 403 en escritura |
| Administrador técnico | plataforma | operar | configuración técnica | instalación | — | — | **sin** autoridad funcional (GOV-CTL-004) | ADMIN_* | 403 ante acciones funcionales |

## Audit Architecture
Base actual (código): `audit_events` con tenant, company, user, session, request_id, action, entity_type/id, before/after, source, reason, evidence, ip y event_time.

Exigencias:
- **[PRJ] GOV-CTL-002:** bitácora append-only.
- **[PRJ] GOV-CTL-003:** autor, actor efectivo y autoridad.
- **[PRJ] RNF-GOV-005:** actor, autoridad, fuente, soporte, timestamp y correlación en el 100 % de los P0.
- **[PRJ] RNF-GOV-021:** minimizar datos personales.

[REC] Contratos (dependen del endurecimiento de 006/051, gap #4):

| Contrato | Definición |
|---|---|
| **AUDIT_EVENT_CONTRACT** | Añade a los campos actuales: `entity_scope` (ente o unidad), `authority_grant_id`, `effective_actor` (frente al autor delegado), `business_date` (America/Caracas), `normative_version_id`, `workflow_state_from/to`, `support_document_id`. **Nunca** secretos; los datos personales, solo por referencia |
| **AUDIT_CORRELATION_CONTRACT** | `correlation_id` de negocio (expediente o caso) además del `request_id` técnico; los eventos de un mismo caso se encadenan |
| **AUDIT_IMMUTABILITY_CONTRACT** | Para los eventos P0 de Gobierno: tabla sin UPDATE/DELETE para el rol de aplicación (privilegio en la base y prueba de la restricción); las correcciones se hacen con eventos compensatorios. **[BP]** Encadenado por hash opcional, a decidir en OQ-GAB-3 |

## Workflow Policy
**[PRJ] RNF-GOV-004 / GOV-ACC-005 / GOV-AST-013 / GOV-DOC-009:** ninguna operación definitiva se edita de forma destructiva. Se corrige con reverso, ajuste, acto de corrección o un registro que la sustituye.

**[REC] Cada flujo futuro define:**
- máquina de estados y transiciones permitidas;
- actor, permiso, alcance y autoridad;
- precondiciones y documentos;
- aprobación, SoD y concurrencia;
- evento de auditoría y numeración;
- errores deterministas y vía de reverso.

Todo ello en la GOV-SPEC, con trazabilidad requisito → norma.

## State Machine Policy
- **[PRJ] IR §8:** las máquinas mínimas de presupuesto, requisición, contratación, contrato, obligación, bien público, expediente y hallazgo son obligatorias tal como figuran.
- **[REC] Política:**
  - los estados y transiciones se declaran en el backend como tabla de transiciones;
  - cada transición registra un evento con `workflow_state_from/to`;
  - una modificación crea versión o evento y nunca reabre en silencio un estado final;
  - los subestados (subsanación, prórroga) son eventos.
- Las transiciones finas que dependen de la norma (p. ej. publicación SNC) son **BLOCKED** hasta D-GOV-03 y el freeze.

## Field Contract Policy
**[OWN]**, tu §15: cada GOV-SPEC incluye un *Field Contract* con:
- nombre y significado;
- tipo, obligatoriedad, fuente y **norma fuente**;
- validación, formato, precisión y valor por defecto;
- estado editable, visibilidad y edición por rol;
- auditoría;
- representación en API, base de datos y UI;
- error.

**[REC]** La validación es DB-FIRST (restricciones CHECK, NOT NULL y FK donde el modelo lo permita). Ninguna regla importante vive solo en el frontend. Las reglas con norma de clase C se marcan `normative_status = PENDING_PIN` y no se activan.

## Data Architecture
| Agregado | Clase |
|---|---|
| users, sessions, roles, permissions (identidad) | SHARED MODEL |
| documents, versions, stored files, links | SHARED MODEL (enlaces con los recursos de Gobierno registrados) |
| audit_events | SHARED MODEL + campos de contexto de Gobierno (contrato de arriba) |
| GovernmentEntity, GovernmentUnit, AuthorityGrant, AppointmentAct | NEW GOVERNMENT MODEL |
| NormativeSource, NormativeVersion, RuleBinding, TenantPolicy | NEW GOVERNMENT MODEL |
| Budget ledger (FiscalYear … BudgetLedgerEntry) | NEW GOVERNMENT MODEL |
| Procurement / contratos | NEW GOVERNMENT MODEL |
| Tesorería (Obligation, PaymentOrder, TreasuryPayment, BankAccount, conciliación) | SHARED CONTRACT / DIFFERENT STORAGE (las cuentas bancarias son un contrato común; obligaciones y pagos públicos van en tablas propias) |
| Contabilidad pública (PublicLedgerAccount, JournalEntry/Line, ClosingPeriod) | NEW GOVERNMENT MODEL (nunca en las tablas fiscales privadas) |
| Bienes públicos | NEW GOVERNMENT MODEL |
| Almacén de consumo | SHARED CONTRACT / DIFFERENT STORAGE |
| Expediente, actos, notificación, firma | NEW GOVERNMENT MODEL sobre documentos compartidos |
| Trámites e interoperabilidad | NEW GOVERNMENT MODEL |
| Fiscal SENIAT 039–043, ventas, compras comerciales | PRIVATE ONLY |

**[PRJ] RNF-GOV-019:** migraciones con una sola cabeza, clean install y upgrade probados en PostgreSQL. [REC] Los módulos `gov_*` comparten la cadena Alembic única del producto.

## API Architecture
- **[PRJ] RNF-GOV-015:** APIs versionadas, contrato de esquema, errores deterministas y trazabilidad de mensajes.
- **[OWN]:** parámetros no declarados → 422.

**[REC] Reglas:**
- `/api/v1/gov/...`;
- **se reutiliza el sobre de error del núcleo** `{code, message, field_errors, request_id, details}` (`app/core/errors.py`), que es suficiente;
- los códigos de negocio de Gobierno llevan prefijo `GOV_` (p. ej. `GOV_AUTHORITY_EXPIRED`, `GOV_BUDGET_UNAVAILABLE`);
- un error de negocio esperado **nunca** devuelve 500;
- `response_model` obligatorio;
- clave de idempotencia (`Idempotency-Key`) obligatoria en pagos, asientos, importaciones y lotes (RNF-GOV-007);
- OpenAPI con firma de referencia, como en SPEC054.

## UI/UX Architecture
- **[OWN]**, tu §16: interfaz sobria e institucional; responsive en escritorio y tableta, y móvil donde el proceso lo justifique.
- **[OWN] Estados por pantalla:** NORMAL, LOADING, EMPTY, ERROR, PERMISSION_DENIED, DISABLED, VALIDATION_ERROR, CONFLICT, OFFLINE, SAVE_SUCCESS, UNSAVED_CHANGES.
- **[REC] Cada flujo define:**
  - tarea principal y puntos de decisión;
  - acciones irreversibles, con confirmación explícita, resumen del efecto y reautenticación si el rol es privilegiado;
  - evidencia documental adjunta;
  - visibilidad de la auditoría (línea de tiempo del caso).
- **[REC]** Se reutiliza el shell y el Design System (005) tras su delta; `UnsavedChangesGuard` en todos los formularios (DT-17).

## Concurrency Policy
[REC] Patrón por proceso (no hay regla única); todos con revalidación de estado dentro de la transacción:

| Proceso | Mecanismo |
|---|---|
| Aprobación | bloqueo de fila del objeto + revalidación de estado y de autoridad vigente; una sola decisión por nivel (restricción única) |
| Edición de borrador | versión optimista (`version`) → 409 CONFLICT |
| Ejecución / transición | bloqueo de fila + tabla de transiciones |
| Asignación de número | contador por (ente, tipo, serie, ejercicio) con `SELECT … FOR UPDATE` + UNIQUE (ente, tipo, serie, ejercicio, número) |
| Reserva o certificación de disponibilidad | bloqueo de fila del `BudgetCredit` + recálculo del disponible en la transacción + evento en el ledger |
| Compromiso / causado | ídem, más idempotencia por documento origen |
| Pago | idempotency key + UNIQUE por (beneficiario, obligación, monto, documento) contra duplicados (GOV-TRE-010) + maker-checker |
| Versión de documento | mecanismo de 046 (CONC-046 ya convergido) |
| Operación sobre un bien | bloqueo de fila del bien + estado; una sola operación activa por bien |

## Institutional Numbering
- **[PRJ]:** los números institucionales no los genera el frontend.
- **[REC] Arquitectura:**
  - cada tipo documental tiene series por (ente, ejercicio);
  - `reserve → issue` (número definitivo al emitir);
  - las anulaciones y reversos conservan el número y registran el motivo;
  - no se reutilizan números;
  - control de huecos auditado (RNF-GOV-024: la contingencia se reconcilia sin crear huecos);
  - concurrencia como en la sección anterior;
  - cada emisión genera evento de auditoría.
- **SHARED_CONTRACT_DIFFERENT_IMPLEMENTATION** respecto a la numeración fiscal privada.
- Los formatos exactos de cada serie son BLOCKED hasta D-GOV-01 y la normativa local (N37, clase C).

## Document Lifecycle
- **[REC] Estados:** borrador, emitido o final, sustituido, anulado o cancelado, archivado y **legal hold** (RNF-GOV-018, GOV-DOC-007/009). Los estados finos por tipo de acto son BLOCKED hasta la normativa (N25 y normativa local).
- **[PRJ] GOV-DOC-009:** no se eliminan documentos de un expediente; la retención es configurable y el borrado solo procede con evidencia.
- **[REC]** Se reutiliza el almacén de 046 (sistema de archivos; S3 no soportado).

## Reporting
- **[PRJ] IR §12:** los reportes y tableros mínimos son los que figuran.
- **[PRJ] RNF-GOV-009:** toda cifra se reconstruye hasta las transacciones y los documentos fuente.

**[REC] Contrato de reporte:**
- cadena REPORTE → CÁLCULO → TRANSACCIÓN → DOCUMENTO → REGLA NORMATIVA;
- cada salida lleva ente, parámetros y filtros, versión normativa, fecha y hora de generación y actor;
- PDF imprimible institucional;
- paquete de auditoría (GOV-DOC-010) con manifiesto y hashes;
- profundización desde cada cifra.

Los formatos oficiales ONAPRE/ONCOP están BLOCKED (D-GOV-02/04, N07–N10 y N36, clase C).

## Time Policy
**[OWN] + [PRJ] RNF-GOV-003:**
- la fecha civil de negocio es America/Caracas;
- los timestamps técnicos van en UTC, conservando zona y origen.

[REC] Fechas separadas, cada una con su columna y su semántica:

| Fecha | Uso |
|---|---|
| `business_date` | día civil de la operación |
| `effective_date` | vigencia del acto o la autoridad |
| `accounting_date` | período contable |
| `document_date` | fecha del documento soporte |
| `created_at` / `event_time` | UTC técnico |
| `normative_effective_from/to` | vigencia de la norma |

Se apoya en el gap #3 del núcleo. Riesgo conocido: SQLite pierde la zona horaria, por lo que la autoridad es PostgreSQL y SQLite normaliza a UTC al persistir.

## Monetary Policy
- **[PRJ] RNF-GOV-002:** Decimal/NUMERIC para presupuesto, compromisos, causado, pagos, retenciones, contabilidad, valor patrimonial y contratos; **nunca** float binario.
- **[REC] Escala:** NUMERIC(20,2) para montos en VES, y la escala de las tasas según su fuente (N39).
- El redondeo se documenta por proceso y por norma, y queda **LEGAL_VALIDATION_REQUIRED** donde la norma lo fije (retenciones N38, clase C).
- **[PRJ] GOV-ACC-010:** multimoneda solo cuando la norma lo permita.
- **[PRJ] GOV-TRE-011:** se conserva la procedencia de las tasas.

## Normative Versioning
**[PRJ] RNF-GOV-008 / IR §9:** `NormativeSource`, `NormativeVersion`, `RuleBinding`, `TenantPolicy`.

[REC] Campos:
- `NormativeSource`: código N.., título, autoridad emisora, clase A/B/C;
- `NormativeVersion`: gaceta o identificador, `effective_from/to`, SHA-256 de la copia custodiada, fecha de obtención, estado de verificación (VERIFIED / PENDING_PIN / SUPERSEDED);
- `RuleBinding`: regla del producto → versión normativa, con efecto desde/hasta;
- `TenantPolicy`: el paquete normativo del ente (Biblioteca §6).

Una regla dependiente de ley o instructivo **no se activa** si su versión está en PENDING_PIN. No hay supuestos legales fijados en el código.

## Integrations
- **[PRJ] IR §11:** solo contratos versionados, siempre con procedencia y evidencia y sin inventar API (SUDEBIP).
- **[REC]** Integration Layer:
  - `InteropContract` versionado;
  - `ExternalDataReceipt` con fuente, finalidad, versión, respuesta y fallo;
  - lotes idempotentes;
  - credenciales por ente, en secretos;
  - toda aplicación de un lote es un comando auditado en el contexto dueño.

| Integración | Prioridad | Estado |
|---|---|---|
| Bancos | P0 | contrato técnico por banco |
| Interoperabilidad del Estado | P0 | N28 y N26 |
| SNC/RNC | P1 | D-GOV-03 |
| SUDEBIP | P1 | D-GOV-05 |
| ONAPRE/ONCOP | P1 | D-GOV-02/04 |
| Firma electrónica | P1 | D-GOV-08 |

## Atenea Boundary
**[PRJ] IR §3.1 y §11, GOV-HR-001..006, E2E-04:** la nómina vive en Atenea; KONTROL recibe lotes cerrados y aprobados y los convierte en compromiso, causado, asiento y orden de pago, con idempotencia por ente, período, tipo y versión. **D-GOV-07 sigue abierta.**

[REC] Frontera:

| Aspecto | Contrato |
|---|---|
| Identidad | referencia estable a la persona y al empleado de Atenea (identificador externo; sin duplicar la ficha completa) |
| Organización | vinculación a `GovernmentUnit` y a la categoría programática |
| Presupuesto y coste | el lote trae imputación por partida y fuente; KONTROL valida la disponibilidad y genera los eventos del ledger |
| Eventos y API | lote versionado con estados recibido → validado → aplicado o rechazado; rechazo con motivo |
| Auditoría | Atenea responde del cálculo; KONTROL, de la imputación, el registro y el pago, con maker-checker (GOV-HR-004) |

No hay nada más detallado sin D-GOV-07.

## Private Fixed Assets vs Public Assets
| Dimensión | Activos fijos privados (SPEC057, PLANNED) | Bienes públicos (LOBP/SUDEBIP) | Clase |
|---|---|---|---|
| Fuente de reglas | contable y fiscal privada | N13 (B), N14–N17 (C), N34 | GOVERNMENT_ONLY |
| Identificación / etiqueta | código interno | codificación y etiquetado SUDEBIP (GOV-AST-002) | componente de etiqueta SHARED; reglas GOVERNMENT_ONLY |
| Bien público frente a otros | — | distinguir (GOV-AST-003) | GOVERNMENT_ONLY |
| Origen | compra | compra, donación, transferencia… (GOV-AST-004) | GOVERNMENT_ONLY |
| Valor y revalorización | depreciación privada | revalorización con soporte (GOV-AST-009) | SHARED_CONTRACT_DIFFERENT_IMPLEMENTATION |
| Custodia y ubicación | opcional | obligatoria, con responsable e historia (GOV-AST-006, GOV-ORG-006) | GOVERNMENT_ONLY |
| Inventario físico | sí | con actas (GOV-AST-008/015) | componente de conteo SHARED; reglas GOVERNMENT_ONLY |
| Baja | venta o descarte | desincorporación y enajenación con acto (GOV-AST-012); **nunca borrado** (GOV-AST-013) | GOVERNMENT_ONLY |
| Componentes técnicos reutilizables | adjuntos (046), auditoría, importación por lotes, etiqueta y QR, conteo móvil | — | SHARED_CORE |

SPEC057 sigue PLANNED / NOT STARTED. Nada de Gobierno entra en ella.

## Warehouses Boundary
| Dimensión | Almacén privado (008, COMPLETE) | Almacén de consumo de Gobierno | Clase |
|---|---|---|---|
| Finalidad | comercial (stock para vender o producir) | consumo institucional y recepción de compras públicas (GOV-WH-001..008) | SHARED_CONTRACT_DIFFERENT_IMPLEMENTATION |
| Origen de entradas | compras y producción | recepción contra contrato u orden y acta (Procurement) | GOVERNMENT_ONLY |
| Valoración | costo comercial | registro patrimonial y contable público | GOVERNMENT_ONLY |
| Alcance | empresa y sucursal | ente y unidad (ORG_SCOPE) | GOVERNMENT_ONLY |
| Deudas abiertas del núcleo | WAREHOUSE-CROSS-COMPANY-FILAS-EXISTENTES, WAREHOUSE-BRANCH-ALCANCE-DE-USUARIO, WAREHOUSE-BRANCH-FK-COMPUESTA, WAREHOUSE-CATALOG-TIPOS-INACTIVOS (D) | **no se reutiliza el modelo privado** hasta que se resuelvan; el almacén de consumo usa los contratos de alcance de esta línea base | bloquean la reutilización, no la planificación |

## Fiscal Boundary
| Ámbito | Clase |
|---|---|
| IVA, ISLR e IGTF del contribuyente, documentos fiscales y libros (039–043, BLOCKED_BY_LEGAL_VALIDATION) | PRIVATE_ONLY |
| Retenciones del pagador público (GOV-TRE-006, N38 clase C) | GOVERNMENT_ONLY, **LEGAL_VALIDATION_REQUIRED** |
| Tabla de alícuotas y referencia de tasas (N39) | SHARED_CONTRACT (fuente versionada), con aplicación distinta |
| Presupuesto y contabilidad pública | GOVERNMENT_ONLY; nunca en tablas fiscales privadas |
| SNAT/2026/00093 | DEFERRED_NORMATIVE_IMPLEMENTATION; fuera de alcance |

## Security
**[PRJ] RNF-GOV-006/011/012/017/021/023 · [REC] Base:**
- MFA para roles privilegiados (gap #1);
- mínimo privilegio y techo de delegación (gap #2);
- secretos fuera del código, por ente cuando aplique, con rotación;
- TLS en tránsito;
- autorización en backend con alcance institucional;
- SoD;
- auditoría completa (gap #4);
- política de sesión para roles privilegiados;
- documentos con ClamAV (046) y S3 no soportado;
- credenciales de integración en secretos;
- límites por ruta en endpoints sensibles (DT-16, Spec 055);
- configuración regulatoria sin fijar en código y con cambios auditados (RNF-GOV-023).

**No se admite ningún bypass P0** (IR §16).

## Test Architecture
**[PRJ] RNF-GOV-020, IR §13 y §16 · [OWN]**, tu §31.

Capas:
- unitarias, de dominio, de servicio, de API y de restricciones de base de datos;
- SQLite donde aplique, con PostgreSQL como autoridad;
- negativas, de autorización y **hostiles entre tenants** (E2E-06/07);
- mutaciones en dominios críticos;
- E2E de los flujos E2E-01..08 y certificación de base de datos tras la E2E;
- OpenAPI, seguridad, cruzado de navegadores y accesibilidad;
- backup/restore (E2E-08), upgrade y clean install.

Hoy existen la orden canónica, las mutaciones, las suites SQLite y PostgreSQL y la E2E Chromium con axe. **No existen todavía** (no se declaran listas):
- pruebas hostiles entre entes;
- restauración verificada;
- cruzado de navegadores portable.

## Cross-Browser
- **Hoy:** la E2E canónica es solo Chromium; CROSS_BROWSER_SMOKE_LOCAL_PATH_NONPORTABLE = 1.
- **[OWN] Para la certificación funcional de Gobierno:** Chromium, Firefox y WebKit; Chrome y Edge reales donde se pueda; Safari real, o REAL_SAFARI_NOT_MEASURED con evidencia WebKit.
- **[REC] Cómo se elimina la deuda antes de la certificación funcional de Gobierno:**
  1. Un perfil Playwright canónico multinavegador en la orden de certificación, sin rutas locales: navegadores instalados por `npx playwright install` en el anfitrión dedicado.
  2. Chrome y Edge «reales» mediante `channel` en el anfitrión, cuando estén instalados.
  3. La medida de capacidad del anfitrión, reconsiderada para tres navegadores, que multiplican la huella medida de 7,6 GB.

  Es una delta de 054 que se planifica cuando exista la primera GOV-SPEC. Hoy no se toca el perfil Chromium certificado.

## Accessibility
- **[PRJ] RNF-GOV-014, GOV-DIG-007:** teclado, contraste, etiquetas y flujos comprensibles.
- **[OWN] Objetivo razonable:** WCAG 2.1 AA, con foco, estructura semántica, asociación de errores y usabilidad responsive.
- **[REC]** Se reutiliza axe (`e2e/accessibility.spec.ts`), ampliado con pruebas de teclado y foco por flujo.
- Sin declaración de certificación WCAG completa.

## Backup / Restore / DR
- **[PRJ] RNF-GOV-010 (P0):** RTO/RPO definidos por instalación y backup/restore validado antes de producción.
- **[PRJ] E2E-08:** backup → restauración → validación de integridad y continuidad de ledgers y documentos.

[REC] Requisitos:
- RPO y RTO **por contrato de instalación** (no se inventan cifras);
- backup cifrado donde aplique;
- restauración verificada automáticamente (checksums de ledgers y documentos, conteos por ente);
- aislamiento por ente durante la restauración (restaurar un ente no expone ni pisa otro);
- evidencia de DR auditada.

Depende del gap #6 (053).

## D-GOV-01..08 Dependency Matrix
**D-GOV OWNER DECISION PACKET.** Las decisiones son del **sponsor**; Claude no las responde.

| Decisión | Dependencia arquitectónica | Se puede decidir antes del sponsor | Queda bloqueado | Artefacto o evidencia para cerrarla |
|---|---|---|---|---|
| D-GOV-01 Jurisdicción piloto | tipo de ente, normativa local (N37), numeración, formatos | contratos de aislamiento y de autoridad, modelo de ente genérico | perfil normativo del piloto, series, ordenanzas | acta del sponsor con el ente piloto y las ordenanzas en copia custodiada |
| D-GOV-02 Profundidad presupuestaria | alcance de Budget Ledger (formulación frente a ejecución) | ledger de ejecución y eventos (compromiso, causado, pagado) | formulación, anteproyecto y formatos ONAPRE (N07–N10) | decisión del sponsor e instructivos ONAPRE del ejercicio en copia oficial |
| D-GOV-03 Alcance SNC | transiciones de contratación, integración SNC/RNC | expediente interno de contratación y máquina base | publicación e integración SNC | alcance confirmado y servicio autorizado documentado |
| D-GOV-04 Plan de cuentas ONCOP | Treasury & Public Accounting | ledger contable genérico e inmutabilidad | plan de cuentas y formatos (N36) | manual ONCOP del piloto en copia oficial |
| D-GOV-05 SUDEBIP 43.077 | Public Assets | ciclo de vida base del bien (IR §8) | codificación, etiquetado, actas y notificaciones (N14–N17) | copias oficiales completas de la G.O. 43.077 |
| D-GOV-06 Trámites tras G.O. 7.018/2026 | Digital Government | modelo de trámite y subsanación (E2E-05) | catálogo de trámites y reglas | catálogo del organismo revisado frente a N26 |
| D-GOV-07 Contrato con Atenea | Integration Layer, Budget Ledger | frontera e idempotencia (sección Atenea) | formato de lote, eventos y responsabilidades | contrato de integración congelado |
| D-GOV-08 Firma e interoperabilidad | Records & Audit, Integration Layer | evidencia de aprobación sin firma (RNF-GOV-022) | firma electrónica y servicios externos | infraestructura de certificados y operadores confirmada (N29) |

## Normative Freeze Requirements
**NORMATIVE_FREEZE_CHECKLIST = 0 / 10** (Biblioteca §9).

Checklist exacto para el sponsor y la validación jurídica:
1. Copia oficial o facsímil custodiado de cada Nxx P0.
2. SHA-256 y metadatos de obtención registrados.
3. Vigencia y supersesión revisadas al corte del freeze.
4. Ordenanzas y actos del tenant piloto incorporados.
5. Edición exacta de ONAPRE/ONCOP del ejercicio identificada.
6. Procedimientos y formatos vigentes de SNC/SUDEBIP del piloto confirmados.
7. Reglas tributarias de retención del pagador confirmadas.
8. Catálogo de trámites revisado frente a la G.O. 7.018/2026.
9. Matriz requisito → fuente completa para todos los P0.
10. El sponsor y el asesor jurídico o funcional del organismo aprueban la línea base antes de crear GOV-SPECs.

Fuentes de clase C (LEGAL_VALIDATION_REQUIRED = 1): N07, N08, N09, N10, N14, N15, N16, N17, N36, N37, N38, N40.

## Implementation Entry Gate
**GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0.** Se autoriza solo cuando **todo** esto se cumpla:
- [ ] RC 0 oficial de SPEC054 en el anfitrión dedicado;
- [ ] los 7 gaps P0 del núcleo cerrados (mapa de dependencias);
- [ ] freeze del sponsor aprobado (checklist 10/10);
- [ ] D-GOV-01..08 resueltas en lo que exija GOV-0;
- [ ] validación jurídica de las fuentes de clase C necesarias;
- [ ] 0 defectos P0/P1 bloqueantes de seguridad, autenticación, aislamiento o integridad;
- [ ] esta línea base ratificada, incluido OQ-GAB-1..3.

## Blocking Dependencies
- Certificación oficial de SPEC054 (anfitrión dedicado).
- Programa SHARED-CORE-GOVERNMENT-P0-HARDENING (7 gaps).
- Freeze del sponsor y D-GOV-01..08.
- Validación jurídica de la clase C.
- Ratificación de OQ-GAB-1..3.

## Non-Blocking Dependencies
- Eliminar CROSS_BROWSER_SMOKE_LOCAL_PATH_NONPORTABLE: bloquea la **certificación funcional** de Gobierno, no GOV-0.
- ADDITIONAL_UNBOUNDED_LISTING, DATATABLE-CAPTION, DT-17 (`UnsavedChangesGuard`).
- E2E-RESULT-MANIFEST-POST-VALIDITY-SEMANTICS.
- Deudas D de almacenes: bloquean la reutilización del modelo privado, no la planificación.
- OBS-09 como puerta externa.

## Material Owner Questions
**MATERIAL_OQ = 1.** Un solo paquete con tres decisiones de arquitectura irreversibles o de política. Las decisiones ya ratificadas no se repiten, y D-GOV es del sponsor.

**OQ-GAB-1 — Forma de entrega de la línea de Gobierno.**
- *Hechos:* P-02 exige separación; el licenciamiento es por instalación; la IR §3.1 excluye convertir requisitos de un organismo en comportamiento global.
- *Opciones:*
  - **A:** perfil de instalación de Gobierno, con módulos `gov_*` sobre el núcleo; los módulos privados no se activan sin aprobación.
  - **B:** una misma instalación mixta, empresarial y de Gobierno.
- *Impacto:* A simplifica el aislamiento, el licenciamiento y la certificación; B complica todo eso.
- *Riesgos:* B mezcla semánticas, contra P-02.
- *Recomendación:* **A**.

**OQ-GAB-2 — Política de MFA y de sesión para roles privilegiados** (gap #1, antes de su delta).
- *Hechos:* RNF-GOV-011 exige MFA para los privilegiados; hoy solo existe `users.mfa_enabled`.
- *Opciones:*
  - **A:** TOTP (RFC 6238) obligatorio para roles privilegiados, con códigos de recuperación de un solo uso y reautenticación para acciones irreversibles.
  - **B:** A + WebAuthn como segundo método opcional.
  - **C:** MFA obligatorio para todos los usuarios.
- *Impacto:* A es estándar, sin dependencias externas ni SMS; B es más robusto, pero con más alcance; C tiene más fricción operativa.
- *Riesgos:* C puede bloquear la adopción.
- *Recomendación:* **A** ahora, con B como evolución.

**OQ-GAB-3 — Grado de inmutabilidad de la auditoría P0.**
- *Hechos:* GOV-CTL-002 exige append-only; hoy ninguna migración protege `audit_events` en la base de datos (ni trigger, ni REVOKE, ni regla), así que el rol de aplicación podría hacer UPDATE o DELETE.
- *Opciones:*
  - **A:** append-only por privilegios de base de datos (sin UPDATE/DELETE para el rol de aplicación) y correcciones compensatorias.
  - **B:** A + encadenado por hash verificable en la exportación.
- *Impacto:* B da evidencia más fuerte ante la Contraloría, a cambio de una migración y algo de coste de escritura.
- *Riesgos:* B añade complejidad en la restauración.
- *Recomendación:* **A** en el endurecimiento de 006/051, con B diferible a GOV-5.

## Final Analyze
| Campo | Valor |
|---|---|
| ENTRY_HEAD / FINAL_HEAD | f036bd3 / (commit de este ciclo) |
| GOVERNMENT_START_READINESS | BLOCKED |
| OD_GSR_1 / OD_GSR_2 | B / A |
| GOVERNMENT_ARCHITECTURE_BASELINE_STATUS | CLOSED / PLANNING_BASELINE |
| GOVERNMENT_IMPLEMENTATION_AUTHORIZED | 0 |
| SPEC054_STATUS | IMPLEMENTED — CERTIFICATION PENDING |
| S3_PROVIDER_SUPPORTED / S3_CONFIGURATION_GUARDED | 0 / 1 |
| SHARED_CORE_P0_GAPS | 7 |
| D_GOV_OPEN_COUNT | 8 |
| NORMATIVE_FREEZE_CHECKLIST | 0 / 10 |
| NORMATIVE_CLASS_C_COUNT | 12 |
| LEGAL_VALIDATION_REQUIRED | 1 |
| GOVERNMENT_SOURCE_STATUS | SPONSOR REVIEW — NO AUTORIZA DESARROLLO |
| MASTER57_COUNT | 57 |
| SPEC057_STARTED / GOVERNMENT_SPEC_STARTED | 0 / 0 |
| DEEPSEEK_CALLS | 0 |
| PRODUCT / TEST / QA_CODE_CHANGED | 0 / 0 / 0 |
| PRODUCTION_TOUCHED | 0 |
| MATERIAL_OQ | 1 paquete (OQ-GAB-1..3) |
| UNKNOWN | 0 (lo no medido va marcado NOT_MEASURED o BLOCKED) |
| TRACEABILITY | contextos ← IR §6 · organización ← GOV-ORG · gaps ← RNF-GOV · D-GOV ← IR §15 · freeze ← Biblioteca §9 |

## Closure / Blocker
La línea base queda **CLOSED como documento de planificación**. La implementación de Gobierno sigue **BLOCKED** por la puerta de entrada (sección Implementation Entry Gate).

## Next Planning
1. Programa **SHARED-CORE-GOVERNMENT-P0-HARDENING** en las Specs dueñas, en el orden recomendado. Empieza por MFA, después de responder OQ-GAB-2.
2. En paralelo: la certificación oficial de SPEC054 espera al anfitrión dedicado.
3. Vía del sponsor: freeze, D-GOV-01..08 y validación jurídica.
4. No se inicia GOV-0 ni ninguna GOV-SPEC.

## Ratificaciones de la dueña (2026-10-25, Master Governance Prompt)
- **OQ-GAB-1 = A** (§85): el perfil de instalación de Gobierno queda separado del perfil funcional privado. El núcleo compartido está permitido; la semántica de negocio compartida exige clasificación explícita. Sin comportamiento mixto automático.
- **OQ-GAB-2 = A** (§34): TOTP obligatorio para roles privilegiados, con:
  - códigos de recuperación de un solo uso, nunca guardados en claro;
  - reautenticación para acciones irreversibles;
  - ningún OTP, código de recuperación ni secreto TOTP en logs ni en la auditoría.

  WebAuthn queda como evolución futura.
- **OQ-GAB-3 = A** (§36): la auditoría crítica es append-only, con inmutabilidad en la base de datos; el encadenado por hash queda como evolución de GOV-5, salvo que una Spec anterior lo exija.

Con esto **MATERIAL_OQ de esta línea base = 0**. La implementación de Gobierno sigue **no autorizada** (puerta de entrada sin cumplir).
