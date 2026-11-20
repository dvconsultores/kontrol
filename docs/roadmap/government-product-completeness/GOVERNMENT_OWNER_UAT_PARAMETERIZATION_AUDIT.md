# KONTROL Gobierno · Auditoría de parametrización de los procesos OWNER_UAT_READY

**GOV-PARAMETERIZATION-AUDIT-01 · P2 · 2026-11-16.** Insumo técnico para la rebaseline GOV-ROADMAP-REBASELINE-02 de P1. No cambia el estado funcional de ningún proceso: `CURRENT_FUNCTIONAL_STATUS` y `FUTURE_ARCHITECTURE_COMPLIANCE` se reportan por separado (§24 del encargo).

- **Corte:** `39a1db0a` (cabeza `0122_gov_cnt07_terminacion`).
- **Lista de procesos:** se tomó de `GOVERNMENT_PRODUCT_COMPLETENESS_MATRIX.csv` (`OWNER_UAT_READY=YES`): 44 procesos.
- **Pregunta guía:** ¿puede este proceso funcionar en otra institución pública venezolana sin cambiar código?
- **Datos por proceso:** el CSV hermano `GOVERNMENT_OWNER_UAT_PARAMETERIZATION_AUDIT.csv` lleva, para cada proceso, cada hallazgo con su fichero, línea y símbolo.

## Métricas

```text
OWNER_UAT_READY_AUDITED=44
KEEP_AS_IS=6  ADAPT_TO_PROCESS_ENGINE=9  REFACTOR_HARDCODED_POLICY=29
INSTITUTION_SPECIFIC_CODE_FINDINGS=0  NAGUANAGUA_SPECIFIC_CODE_FINDINGS=0  NAGUANAGUA_SPECIFIC_EXECUTABLE_CODE=0
ORGANIZATION_HARDCODE_FINDINGS=1
AUTHORITY_HARDCODE_FINDINGS=22
WORKFLOW_HARDCODE_FINDINGS=41
DOCUMENT_HARDCODE_FINDINGS=14
DEADLINE_HARDCODE_FINDINGS=28
AMOUNT_HARDCODE_FINDINGS=13
CATALOG_HARDCODE_FINDINGS=43
NUMBERING_HARDCODE_FINDINGS=22
REPORT_HARDCODE_FINDINGS=19
INTEGRATION_HARDCODE_FINDINGS=2
NORMATIVE_HARDCODE_RISK_FINDINGS=81
PRIORIDAD: P0=2  P1=28  P2=9  NONE=5   (auditoría original: P0=9  P1=23; los 2 P0 que quedan, BUD-01 y BUD-05, son refactor de régimen sin defecto de producto vigente)
CURRENT_PRODUCT_DEFECTS=1   (auditoría original: 11; CNT-04 corregido en CNT-04-EFFECTIVE-TERM-01; CTL-07 y REP-10 corregidos en GOV-SOD-COVERAGE-01; PROC-07 y PROC-08 corregidos en PROC-07/PROC-08-COMMISSION-POLICY; ORG-04 corregido en ORG-04-AUTHORITY-ASSIGNMENT-POLICY; CTL-09 corregido en CTL-09-DELIVERY-ACT-POLICY; ORG-07 corregido en ORG-07-EFFECTIVE-AUTHORITY-MATRIX; CTL-02 y CTL-04 corregidos en CTL-02-AUDIT-PROCESS-RESOLUTION)
```

**Qué se cuenta como hallazgo:**

- Solo los valores o reglas que pueden variar legítimamente por institución o por versión normativa. No se cuentan los marcados PLATFORM_INVARIANT (seguridad, aislamiento, append-only, concurrencia, hash, MFA, auditoría, estados técnicos), aunque figuran en la evidencia.
- Las dimensiones auxiliares de los informes se pliegan así: CONTROL → WORKFLOW y SOD → AUTHORITY.
- `NORMATIVE_HARDCODE_RISK` cuenta las reglas o catálogos legales que viven como constante, enum o CHECK sin `SOURCE/VERSION/EFFECTIVE_FROM/EFFECTIVE_TO`, aunque hoy sean correctos.

## Método y normalización

1. **Lectura de código, sin cambios.** Cinco auditorías de solo lectura, una por grupo (ORG/CTL-03, BUD/TRE, PROC/REP-03, CNT, DOC/CTL/REP-10), con una rúbrica común: dimensiones A–J del encargo, clase de cada regla y componentes del motor con sus nombres canónicos.
2. **Verificación de Claude:**
   - el ensamblador comprueba que todo fichero citado exista y que cada línea quede dentro de su longitud (0 errores);
   - una muestra aleatoria de 10 hallazgos se contrastó línea a línea (10/10);
   - cada defecto actual se verificó leyendo el código.
3. **Clasificación:**
   - **REFACTOR_HARDCODED_POLICY:** al menos un valor institucional u operativo fijo que otra institución necesitaría cambiar, o una regla legal de un solo régimen (municipal) aplicada a cualquier tipo de ente;
   - **ADAPT_TO_PROCESS_ENGINE:** sin hardcode institucional, pero con workflow codificado en el servicio;
   - **KEEP_AS_IS:** datos o configuración puros, o vistas de solo lectura.
   - Una corrección sobre los informes: BUD-05 pasa de ADAPT a REFACTOR, porque el cuadre LOPPM art. 240 es municipal y se aplica a todo ente.
4. **Prioridad (§15 del encargo):**
   - **P0:** regla de régimen aplicada a cualquier ente (BUD-01, BUD-05, ORG-04, CTL-09) o defecto actual que produce un resultado incorrecto;
   - **P1:** el resto de REFACTOR, o un defecto actual menor;
   - **P2:** ADAPT sin defecto;
   - **NONE:** KEEP sin defecto.

## Resultado por proceso

| Proceso | Clasificación | Prioridad | Hallazgos (dimensión) | Riesgo normativo | Defecto actual |
|---|---|---|---|---|---|
| ORG-01 Configurar el ente y su tipo | ADAPT | P2 | Document 1, Catalog 4 | YES(4) | no |
| ORG-02 Estructura organizativa por ejercicio (órgano, u | REFACTOR | P1 | Workflow 1, Deadline 1, Catalog 3, Numbering 1, Report 1 | YES(1) | no |
| ORG-03 Cargos con competencias y límites de firma/aprob | REFACTOR | P1 | Authority 1, Workflow 1, Amount 2, Catalog 2 | YES(2) | no |
| ORG-04 Delegaciones, suplencias, encargadurías y design | REFACTOR | P1 | Authority 2, Workflow 2, Deadline 2, Catalog 2, Numbering 1 | YES(6) | sí |
| ORG-06 Vincular usuario con identidad, cargo, unidad y  | ADAPT | P2 | Workflow 2, Numbering 1 | NO | no |
| ORG-07 Matriz auditable de quién puede solicitar, compr | KEEP | NONE | Deadline 1 | YES(1) | no (corregido) |
| BUD-01 Ejercicio económico-financiero | REFACTOR | P0 | Workflow 1, Deadline 3, Catalog 2, Numbering 1, Report 1 | YES(6) | no |
| BUD-02 Clasificador presupuestario versionado | KEEP | P1 | Deadline 1, Catalog 1, Numbering 1 | YES(1) | sí |
| BUD-03 Plan, programas, proyectos, metas físicas e indi | KEEP | NONE | Amount 1 | NO | no |
| BUD-04 Fuentes de financiamiento y restricciones | ADAPT | P2 | Deadline 1, Catalog 1 | YES(2) | no |
| BUD-05 Formulación: anteproyecto, proyecto y presupuest | REFACTOR | P0 | Workflow 2, Deadline 1, Amount 1, Report 1 | YES(4) | no |
| BUD-06 Disponibilidad y certificación de disponibilidad | REFACTOR | P1 | Authority 1, Document 1, Deadline 1, Numbering 1, Report 2 | YES(3) | no |
| BUD-08 Compromiso presupuestario | REFACTOR | P1 | Authority 1, Workflow 2, Document 1, Deadline 1, Amount 1, Numbering 1, Report 1 | YES(3) | no |
| PROC-02 Comisión de contrataciones (miembros, suplentes, | REFACTOR | P1 | Authority 1, Workflow 2, Document 1, Deadline 1, Catalog 3 | YES(5) | no |
| PROC-03 Expediente único de contratación con cronología  | ADAPT | P2 | Workflow 1, Document 2, Deadline 1, Amount 1, Catalog 1 | YES(3) | no |
| PROC-06 Recepción y apertura de ofertas | ADAPT | P2 | Workflow 2, Deadline 1, Catalog 1 | YES(3) | no |
| PROC-07 Evaluación técnica, económica y legal con matriz | REFACTOR | P1 | Workflow 4, Catalog 2 | YES(2) | sí |
| PROC-08 Recomendación, decisión, adjudicación, desierta, | REFACTOR | P1 | Authority 2, Workflow 3, Catalog 1, Numbering 1, Report 1 | YES(3) | sí |
| PROC-10 Garantías y cauciones | REFACTOR | P1 | Authority 1, Deadline 1, Amount 1, Catalog 1 | YES(2) | no |
| PROC-11 Conflictos SoD en contratación | ADAPT | P2 | — | NO | no |
| CNT-01 Crear contrato u orden desde la adjudicación | REFACTOR | P1 | Authority 1, Document 1, Amount 1, Catalog 1, Numbering 2 | YES(2) | no |
| CNT-02 Adendas, prórrogas y variaciones versionadas | REFACTOR | P1 | Authority 1, Workflow 1, Deadline 1, Amount 1, Catalog 1, Numbering 1 | YES(2) | no |
| CNT-03 Ejecución: hitos, entregables, valuaciones, rece | REFACTOR | P1 | Organization 1, Authority 2, Workflow 2, Document 1, Numbering 1 | YES(3) | no |
| CNT-04 Designación del supervisor del contrato | REFACTOR | P1 | Authority 1, Workflow 1 | NO | corregido (CNT-04-EFFECTIVE-TERM-01) |
| CNT-07 Terminación, resolución o rescisión | REFACTOR | P1 | Authority 1, Workflow 1, Document 1, Deadline 1, Amount 1, Catalog 2, Numbering 1, Report 1, Integration 1 | YES(5) | no |
| CNT-08 Expediente contractual completo | KEEP | NONE | — | NO | no |
| CNT-09 Alertas de vencimientos | REFACTOR | P1 | Workflow 2, Deadline 2 | NO | no |
| TRE-01 Cuentas bancarias públicas con autorizados y act | REFACTOR | P1 | Authority 2, Document 1, Catalog 3, Numbering 1 | YES(1) | no |
| TRE-02 Programación financiera y disponibilidad de caja | REFACTOR | P1 | Workflow 1, Deadline 2, Catalog 1, Numbering 1 | YES(1) | no |
| TRE-09 Provenance de tasas BCV | ADAPT | P2 | Workflow 1, Catalog 1, Integration 1 | YES(2) | no |
| DOC-02 Actos administrativos con autoridad, motivación  | REFACTOR | P1 | Authority 1, Workflow 1, Document 1, Deadline 1, Catalog 1 | YES(4) | no |
| DOC-04 Notificaciones administrativas con constancia de | ADAPT | P2 | Workflow 2, Deadline 1, Catalog 1, Report 1 | YES(3) | no |
| DOC-08 Paquete de auditoría exportable | REFACTOR | P1 | Amount 1, Numbering 1, Report 1 | NO | no |
| CTL-01 Matriz SoD por proceso y detección previa | REFACTOR | P1 | Authority 1, Workflow 1, Catalog 2, Numbering 1 | NO | no |
| CTL-02 Bitácora institucional append-only con actor, au | KEEP | NONE | — | NO | no (corregido) |
| CTL-03 Administrador técnico sin autoridad funcional | KEEP | NONE | Workflow 1, Report 1 | NO | no |
| CTL-04 Consulta y muestreo read-only del auditor | REFACTOR | P1 | Amount 1, Catalog 1, Numbering 1 | NO | no (corregido) |
| CTL-05 Expediente de cuenta y reportes de rendición | REFACTOR | P1 | Authority 1, Workflow 1, Deadline 1, Numbering 1, Report 1 | YES(2) | no |
| CTL-06 Hallazgos y planes de acción correctiva | REFACTOR | P1 | Authority 1, Workflow 1, Document 1, Deadline 1, Catalog 1, Numbering 1, Report 1 | NO | no |
| CTL-07 Alertas de operaciones atípicas | REFACTOR | P1 | Workflow 1, Amount 1, Catalog 1 | YES(1) | corregido (GOV-SOD-COVERAGE-01) |
| CTL-09 Actas de entrega por cambio de responsable o aut | REFACTOR | P1 | Authority 1, Workflow 1, Document 2, Deadline 1, Numbering 1, Report 1 | YES(3) | sí |
| CTL-10 Controles materiales que impiden cerrar ejercici | REFACTOR | P1 | Catalog 2, Numbering 1 | NO | no |
| REP-03 Contrataciones por modalidad, estado, unidad, pr | ADAPT | P2 | Deadline 1, Catalog 1, Report 2 | YES(1) | no |
| REP-10 Control interno: overrides, conflictos SoD, dupl | REFACTOR | P1 | Report 2 | NO | corregido (GOV-SOD-COVERAGE-01) |

## Verificación previa · PG completa sobre el árbol final de CNT-07

- **Inconsistencia resuelta:** el cierre de CNT-07 llamaba «árbol final convergido» a `2e6c5504`. Ese árbol era la primera fusión con P1. El árbol funcional final es `26e23ecb` (segunda fusión); `39a1db0a` solo añade documentación. Sobre ese árbol exacto no existía PG completa. `CIERRE.md` queda corregido.
- **Ejecución en este ciclo:** PG completa sobre `39a1db0a` (18:15–21:04): 5710 pruebas, 5688 pasan, 18 se saltan y 4 fallan, las cuatro de la línea base (`test_n10_convergence`, `test_naive_datetime_input` y `test_spec019_receipt` ×2). NEW_BACKEND_FAILURES=0. OWNER_UAT_READY_REGRESSIONS=0.
- **Intento descartado:** un primer intento dio «Connection refused» masivo (1809 pasan). El servidor de QA había recibido «smart shutdown» al cerrarse la sesión anterior. Es INVALID_ENVIRONMENT: no se cuenta y se repitió con el servidor desacoplado.

```
CNT07_FINAL_TREE=26e23ecb (código) / 39a1db0a (cabeza documental)
FULL_PG_EXACT_TREE=39a1db0a
FULL_PG_EXECUTED_THIS_CYCLE=YES
FULL_PG_RESULT=PASS_WITH_BASELINE (5688 passed, 18 skipped, 4 baseline failures, 0 new)
```

## CNT-07 · auditoría especial

**Clasificación:** REFACTOR_HARDCODED_POLICY (P1). Sin defecto actual: lo construido coincide con C07-01..28. Se preserva el comportamiento.

| Elemento | Hoy | Clase | Destino |
|---|---|---|---|
| 3 figuras de LCP 145 y 12 causales | Tuplas + CHECK (`models.py:5520-5521, 5561-5562`) y `CATALOGO` con citas (`service_contratos_terminacion.py:73-110`), duplicadas en `situacion_contractual.ETIQUETA_FIGURA` y en el frontend | LEGAL_MANDATORY, riesgo normativo | NORMATIVE_VERSIONED_CONFIGURATION: catálogo (figura, causal, fuente, vigencia) con FK al vigente en la fecha del acto. RLCP 193 admite además causales «establecidas en el contrato» |
| Notificación al contratista | Requisito NOTIFICACION_CONTRATISTA (`_requisitos`, 459-497) | LEGAL_MANDATORY (LOPA 73-74; LCP 152) | NOTIFICATIONS + NORMATIVE_BINDING |
| Notificación a garantes | «Al menos otra notificación NOTIFICADA» si hay garantías vigentes | La obligación es LEGAL (LCP 152, 156); el rigor del cotejo es una decisión de la dueña (OD-CNT07-03) | NOTIFICATIONS (obligación legal) + TENANT_POLICY (cotejo por garante y cesionario) |
| Acto eficaz DOC-02/DOC-04 | `_acto_valido` (227-245) y `fecha_eficacia` | LEGAL_MANDATORY | Se mantiene; pasa a DOCUMENT_RULES/EVIDENCE_RULES del motor |
| Competencia APROBAR × CONTRATACIONES | Par fijo en `_acto_valido`, `formalizar` y `vista` (227-245, 770, 1000-1001) | INSTITUTIONAL_POLICY: la ley dice «el contratante» o la máxima autoridad; el par es de diseño (D07-03) | AUTHORITY_BINDING por proceso y operación en TENANT_POLICY |
| Saldo no ejecutado | monto vigente − valuado conformado (`_consecuencias`); los tramos de indemnización son solo texto (`REGLA_INDEMNIZACION`, 111-115) | LEGAL_MANDATORY (RLCP 191, 194), riesgo normativo | La fórmula como NORMATIVE_BINDING; la tabla de tramos versionada, que debe existir antes de que CNT-06 calcule |
| Fecha de eficacia | `acto.fecha_eficacia` (notificación DOC-04), separada del registro | Invariante de dominio derivado de los datos | No se parametriza |
| Guardas post-extinción | `exigir_vigente_en` y `exigir_vigente_para_modificacion`, llamadas en 8 puntos de CNT-02/03/04 | Invariante de dominio | CONTROL_RULES del motor (guarda común de vigencia) |
| Numeración `{codigo}/TER` | `service_contratos_terminacion.py:781` | OPERATIONAL_CONFIGURATION | TENANT_POLICY de series |
| Obligaciones SNC (LCP 8 y 51) | Textos y citas literales (962-977) | LEGAL_MANDATORY, riesgo normativo | NORMATIVE_BINDING + NOTIFICATIONS |

**Observación OBS-CNT07-CONCLUSION-CNT02-01.** No es un defecto demostrado. Con conclusión autorizada, `_hechos_posteriores` compara las modificaciones CNT-02 contra `conclusion_hasta` (service_contratos_terminacion.py:330-337, 526). La guarda de CNT-02 compara contra la eficacia (situacion_contractual.py:91). Queda para la decisión de la dueña junto con OQ-CNT07-01.

## Hallazgos de hardcode por dimensión

- **ORGANIZATION (1):** No hay nombres de unidades ni de cargos en el código. Lo único fijo es el órgano que aprueba el cierre de CNT-03 (Comisión o Unidad Contratante, por norma). Unidades, cargos y jerarquías son datos por company_id (ORG-02/03).
- **AUTHORITY (22):** Pares de competencia fijos en código (FIRMAR×PRESUPUESTO, COMPROMETER×PRESUPUESTO, FIRMAR×CONTRATACIONES, APROBAR×CONTRATACIONES) en BUD-06/08, CNT-01..04/07, PROC-08/10 y DOC-02. Vocabulario cerrado de 10 acciones × 6 materias (ORG-03), sin RRHH, tributos ni urbanismo. Pares SoD cableados fuera de CTL-01 (BUD-08, PROC-02, CTL-05, CTL-06, PROC-08). Sin régimen de firma mancomunada en TRE-01.
- **WORKFLOW (41):** Ciclos de estados y transiciones en los servicios (ORG-02/03/04/06, BUD-05, PROC-03/06/07/08, CNT-03, DOC-02/04, CTL-05/06/09). Quórum de mayoría simple fijo (PROC-07/08, decisión de la dueña). Alcance y modo SoD únicos (CTL-01).
- **DOCUMENT (14):** Requisitos documentales fijos (actos habilitantes, folios RLCP 32, anexos N34, motivación LOPA, soportes de CDP y compromiso).
- **DEADLINE (28):** Ejercicio fijado al 1-ene–31-dic en literales (ORG-02/07, BUD-01..08, REP-03). Plazos legales literales: LOPPM 234/236 y 87, LEFP 72, LOPA 76 (15 días), N21 (90 días). 15 días de preaviso de garantías (PROC-10/CNT-09). No hay calendario hábil.
- **AMOUNT (13):** Cuadre LOPPM 240 (BUD-05). Límites de firma solo como monto por operación en VES/USD/EUR, sin UT, vigencia ni acumulado (ORG-03). Porcentajes de garantías versionados, pero en código (PROC-10). Topes operativos (20 líneas de compromiso, tamaños de muestra y de paquete).
- **CATALOG (43):** Catálogos legales en enums y CHECK: tipos de ente, figuras de ocupación, modalidades, causales, tipos de acto y de notificación, tipos de instrumento y de modificación, figuras de terminación. Catálogos institucionales cerrados: tipos de unidad, tipos de cuenta, monedas, escala de riesgo de hallazgos, tipos de alerta y de control de cierre.
- **NUMBERING (22):** Series fijas «PREFIJO-AAAA-NNNN»: CT/OC/OS, CDP, CP, CB, PF, AE, CTA, HA, PA, SOD, MU, PC, FUN/ASG/VIN, AD/PR/MO/VA y /TER. Solo el número de expediente (PROC-03) es libre por ente.
- **REPORT (19):** PDF y CSV con títulos, columnas y citas legales fijas. Casi ninguno lleva denominación ni logo del ente (usan Company.legal_name o nada).
- **INTEGRATION (2):** No hay acoplamiento técnico (sin URL, scraping ni API) a BCV, SNC, ONAPRE, SUDEBIP, Atenea, banco ni firma. Hay fuente «BCV» como CHECK (TRE-09) y obligaciones SNC como texto (CNT-07). La arquitectura futura IntegrationContract/Adapter/Mapping/Transport/CredentialReference no tiene deuda de acoplamiento que pagar.

## Adopción del motor de procesos

Número de procesos que necesitan cada componente:

| Componente | Procesos |
|---|---|
| TENANT_POLICY | 30 |
| NORMATIVE_BINDING | 26 |
| STAGES | 21 |
| DOCUMENT_RULES | 20 |
| CONTROL_RULES | 20 |
| SOD_RULES | 19 |
| TRANSITIONS | 18 |
| AUTHORITY_BINDING | 13 |
| DEADLINES | 13 |
| APPROVAL_RULES | 12 |
| PROCESS_DEFINITION | 11 |
| BUSINESS_CALENDAR | 11 |
| EVIDENCE_RULES | 11 |
| PROCESS_VERSION | 9 |
| RESPONSIBILITY_BINDING | 4 |
| NOTIFICATIONS | 4 |
| EXCEPTIONS | 3 |
| ESCALATIONS | 2 |

```text
PROCESS_ENGINE_ADOPTION_REQUIRED=38/44
NORMATIVE_ENGINE_ADOPTION_REQUIRED=30/44
```

**Componentes horizontales de mayor retorno:**

1. **TENANT_POLICY de numeración**: una sola tabla de series para unas 22 series fijas.
2. **NORMATIVE_BINDING**: catálogo normativo versionado con fuente y vigencia, que sustituye los CHECK de BD.
3. **BUSINESS_CALENDAR**: ejercicio, días hábiles y plazos legales.
4. **AUTHORITY_BINDING** por operación, que libera los pares de competencia fijos.
5. **SOD_RULES**: llevar a CTL-01 los pares cableados.

## Hallazgos de versionamiento normativo

81 hallazgos con `NORMATIVE_HARDCODE_RISK`, en 30 procesos. Solo dos modelos tienen hoy versión normativa real:

- **BUD-02 · clasificador:** `edicion`, `fecha_edicion`, `procedencia`, `documento_sha256` y vigencia por partida.
- **PROC-10 · reglas de garantías:** `codigo`, `version`, `fuente`, `gaceta` y `vigente_desde/hasta`, con instantánea en cada requisito. Viven en código Python, así que una norma nueva exige desplegar.

Las demás reglas legales tienen fuente citada en la Spec o en un comentario, pero no `SOURCE/VERSION/EFFECTIVE_FROM/EFFECTIVE_TO` en el modelo. Entre ellas: LCP 14, 78, 92, 95, 110, 145-156; RLCP 18, 32, 33, 191-194; LOPA 9, 18, 72-76; LOPPM 87, 229-250; LEFP 72; LOAP 34-41; N21; N34.

Las reglas de un solo régimen aplicadas a cualquier ente son el riesgo P0 de esta sección:

- BUD-01: ordenanza y reconducción LOPPM;
- BUD-05: cuadre LOPPM 240;
- ORG-04: base legal LOPPM 87/88.7;
- CTL-09: anexos A17 por nivel territorial (corregido en CTL-09-DELIVERY-ACT-POLICY).

## Preparación multiinstitución

Para los procesos KEEP_AS_IS, la demostración es estructural: Tenant A (Alcaldía de Naguanagua) y Tenant B (otra alcaldía) se diferencian solo por datos con `company_id`.

- **ORG-07:** Proyección de solo lectura sin tablas propias. Lee gov_structures (company_id, exercise), gov_units (company_id, structure_id, code, name, parent_id), gov_positions (company_id, structure_id, code, name, unit_id), gov_position_versions.snapshot con las competencias, límites y fundamento de cada company_id, y document_links (company_id) del acto; desde ORG-07-EFFECTIVE-AUTHORITY-MATRIX, además, la autoridad efectiva de gov_assignments y gov_assignment_competencies resuelta por ORG-04 a la fecha de corte. Tenant A y Tenant B con unidades, cargos, competencias y límites distintos obtienen matrices distintas sin cambiar código. Lo único fijo es el vocabulario acción × materia heredado de ORG-03.
- **BUD-02:** gov_budget_classifiers (company_id, year_id UNIQUE, edicion, fecha_edicion, procedencia, documento_id, documento_sha256: models.py:1166-1178) y gov_budget_classifier_items (company_id, classifier_id, tipo, codigo, denominacion, nivel, parent_id, vigente_desde, vigente_hasta: models.py:1181-1202). No se precarga ningún catálogo ONAPRE; cada tenant carga su edición por ejercicio (alta manual o CSV) y la congela al fijar. Tenant A y B pueden usar ediciones, códigos y profundidades distintas sin cambiar código.
- **BUD-03:** gov_budget_plans (company_id, year_id UNIQUE, denominacion, documento_id, documento_sha256: models.py:1243-1253), gov_budget_objectives (company_id, year_id, codigo libre, descripcion: models.py:1256-1269), gov_budget_goals (company_id, category_id, unidad_medida libre, cantidad, indicador, formula: models.py:1272-1289) y gov_budget_categories.unit_id/objective_id, que apuntan a gov_units de la estructura VIGENTE del ente (service_presupuesto_plan.py:36-56). Unidades, objetivos, metas e indicadores son datos de cada tenant.
- **CNT-08:** Es una proyección de solo lectura de datos ya acotados por company_id: gov_contracts, gov_contract_amendments, gov_contract_supervisors, gov_contract_execution_acts y demás tablas de CNT-03, gov_contract_terminations, gov_procurement_files, las garantías PROC-10 y la CDP y el compromiso BUD-06/BUD-08. Sus tablas propias también llevan company_id: gov_contract_dossier_packages (UNIQUE company_id+codigo, contract_id+numero_generacion, company_id+idempotency_key; models.py 4978-5005) y gov_contract_dossier_package_verifications (models.py 5017). Cargos, unidades, firmantes, actos y documentos se leen de las tablas ORG/DOC del ente. ORDEN_PROCESO y FUENTES_FUTURAS (service_expediente_contractual.py 71-78) describen los módulos de la plataforma, no la organización del ente. Los permisos (gobierno_contratos:view, gobierno_auditoria:view, gobierno_paquetes:*) son datos RBAC asignables.
- **CTL-02:** Vista de solo lectura sobre audit_events filtrada por tenant_id/company_id (service_bitacora._alcance, líneas 61-83) y gov_user_official_links.company_id. El catálogo de acciones es de plataforma (app/shared/audit_catalog_entries.py, owner_module="government"); no hay organización, cargos, numeración ni política en el código. Tenant A y Tenant B difieren solo por datos.
- **CTL-03:** Vista GET de solo lectura sin tablas propias. La separación se configura en roles y user_roles (tenant_id, company_id), gov_role_categories (company_id, role_id, categoria), gov_identity_policies (company_id único, exige_identidad), gov_sod_rules (tenant_id, company_id, proceso='ORG-06') y gov_user_official_links (company_id). Los únicos fijos son TECHNICAL_CAPABILITIES, SECURITY_ADMIN_CAPABILITIES y los roles protegidos ADMIN y FUNCIONAL_COMPLETO (resources/backend/app/modules/identity_access/authority.py:19-30), que son RBAC de plataforma (PLATFORM_INVARIANT).

**Fuera de KEEP:**

- Organización, unidades, cargos, competencias asignadas, límites por cargo, numeración de expedientes y preavisos de contratos (CNT-09) ya son datos por ente en los 44 procesos.
- Lo que impide un Tenant B distinto sin código es lo listado en REFACTOR: series fijas, pares de competencia, catálogos cerrados y reglas municipales.
- Un Tenant B que no sea municipio (gobernación, instituto, fundación) choca además con los cuatro P0 de régimen.

## Barrido de nombres institucionales

Términos buscados en `resources/backend/app`, `alembic` y `resources/frontend/src`: Naguanagua, Dirección de Administración, Dirección de Hacienda, Tesorería Municipal, Planificación y Control, Talento Humano, Auditoría Interna, Bienes Públicos, Consultoría Jurídica, Alcaldía, Carabobo y Municipio.

- **Código ejecutable: 0 nombres institucionales.**
- **Lo que aparece y no es lógica de producto:**
  - el campo de datos `municipio` del ente (ORG-01);
  - la ayuda «Ministerio, gobernación o alcaldía de adscripción» (EnteFormulario.tsx:230);
  - la etiqueta de materia «Bienes públicos» (api.ts:354).
- **Datos de prueba** (no ejecutables en producto):
  - «Dirección de Administración» en Vitest de estructura, cargos, actos y autoridad;
  - «Naguanagua» en 4 ficheros de prueba backend o E2E (org04_ayudantes.py, org06_guarda.py, test_gov_org06_separacion.py y test_gov_cnt07_terminacion.py).

```text
NAGUANAGUA_SPECIFIC_EXECUTABLE_CODE=0  INSTITUTION_SPECIFIC_EXECUTABLE_CODE=0
```

## Defectos actuales encontrados (verificados en el código; no corregidos en este ciclo)

Ninguno es de seguridad ni de aislamiento entre empresas, así que según §11 del encargo no se corrigen aquí. Se priorizan para ciclos dirigidos. No retiran OWNER_UAT_READY (§24); lo decide la rebaseline con la dueña.

| Proceso | Prioridad | Defecto |
|---|---|---|
| ORG-04 | CORREGIDO | **Corregido el 2026-11-18 en ORG-04-AUTHORITY-ASSIGNMENT-POLICY** (`specs/gov-org-04-ocupacion-cargos/spec004-assignment-policy-delta.md`): autoridad única `service_asignacion_regla.py` con pisos legales versionados por régimen (LOAP y LEFP en todo nivel; LOPPM art. 87 solo MUNICIPAL) más la política del ente por figura, congelada al activar; la UI pide la regla (`GET /gobierno/ocupacion/regla`) y solo muestra la autorización que la regla exige. Antes: base legal LOPPM (municipal) para cualquier ente en FIGURAS (service_ocupacion.py:49-110); la UI pedía «Autorización del Concejo» en toda suplencia de máxima autoridad (NuevaAsignacionPage.tsx:836-865), aunque el backend solo lo aplicaba a MUNICIPAL |
| ORG-07 | CORREGIDO | **Corregido el 2026-11-19 en ORG-07-EFFECTIVE-AUTHORITY-MATRIX** (`specs/gov-org-07-matriz-autoridad/spec007-effective-authority-delta.md`): la matriz proyecta la autoridad efectiva a la fecha de corte que resuelve ORG-04 (`service_ocupacion.autoridad_efectiva_en`): quien ejerce el cargo (titular o figura temporal) y filas propias por delegación con sus límites, fuente trazable y CSV con el mismo universo; las personas se reservan sin `gobierno_ocupacion:view` (OD-EA-01). Antes: la matriz solo proyectaba la autoridad del cargo ("origen": "CARGO", service_autoridad.py:343) y la UI decía que ORG-04 «llegaría» |
| BUD-02 | P1 | La validación del padre no comprueba el nivel inmediatamente anterior: `existentes` se indexa por (tipo, codigo). Ver service_presupuesto.py:843, 872-873 |
| PROC-07 | CORREGIDO | **Corregido el 2026-11-17 en PROC-07/PROC-08-COMMISSION-POLICY** (`specs/gov-proc-02-comisiones/spec002-commission-policy-delta.md`): la apertura usa la regla de la política (`service_comision_regla`), excluye a los inhibidos en el expediente y, sin comisión, la hacen los responsables del expediente. Antes: la apertura exige committee_id (service_evaluacion.py:325-326), aunque la recepción admite comision_no_aplica_motivo (service_ofertas.py:302); un procedimiento sin comisión no puede abrir ni evaluar. Tampoco se excluye al miembro con inhibición ACEPTADA |
| PROC-08 | CORREGIDO | **Corregido el 2026-11-17 en PROC-07/PROC-08-COMMISSION-POLICY**: la recomendación usa quórum y mayoría de la política (incluida base y voto dirimente), excluye inhibidos y, sin comisión, firman los responsables del expediente. Antes: la recomendación exige committee_id (service_decision.py:842-843); un procedimiento sin comisión no llega a adjudicación ni a desierta |
| CNT-04 | CORREGIDO | **Corregido el 2026-11-16 en CNT-04-EFFECTIVE-TERM-01** (`specs/gov-cnt-04-supervisor/spec004-effective-term-delta.md`): `designar()` usa `terminos_efectivos(db, contrato, desde)` de `service_contratos_terminos.py`. Antes: el máximo de la fecha de designación usa contrato.fecha_fin original (service_contratos_supervision.py:309) y no el plazo efectivo con prórrogas CNT-02 (terminos_efectivos) |
| CTL-02 | CORREGIDO | **Corregido el 2026-11-19 en CTL-02-AUDIT-PROCESS-RESOLUTION** (`specs/gov-ctl-02-bitacora-institucional/spec002-audit-process-resolution-delta.md`): la bitácora resuelve proceso y módulo con la autoridad única `app/modules/government/procesos.py`, a partir de la metadata del catálogo de eventos (`owner_spec`), con una guardia que falla ante un evento de Gobierno sin proceso. Antes: `service_auditoria.PROCESOS` solo registraba 19 procesos y 125 de los 317 eventos de Gobierno salían sin proceso |
| CTL-04 | CORREGIDO | **Corregido el 2026-11-19 en CTL-02-AUDIT-PROCESS-RESOLUTION** (OD-PR-01): el filtro y el catálogo de procesos consumen la misma autoridad única. Antes: el filtro rechazaba con GOV_AUDIT_INVALID_FILTER los procesos ausentes de `service_auditoria.PROCESOS` |
| CTL-07 | CORREGIDO | **Corregido el 2026-11-17 en GOV-SOD-COVERAGE-01** (`specs/gov-ctl-07-alertas-atipicas/spec007-sod-coverage-delta.md`): CTL-07 consume la autoridad única `service_sod_eventos.py`, que registra CTL-01, PROC-11 y BUD-08. Antes: ACCIONES_SOD (service_alertas.py:32) no incluye GOV_BUDGET_COMMITMENT_SOD_BLOCKED (service_presupuesto_compromiso.py:597): los bloqueos SoD de BUD-08 nunca generan alerta |
| CTL-09 | CORREGIDO | **Corregido el 2026-11-18 en CTL-09-DELIVERY-ACT-POLICY** (`specs/gov-ctl-09-actas-de-entrega/spec009-delivery-act-policy-delta.md`): la autoridad única `service_actas_regla.py` aplica el catálogo legal versionado de N34; los arts. 12–17 rigen solo donde la política del ente los declara (entidad o unidad). Antes: los anexos A17 (alcaldía o hacienda municipal) se exigían a todo ente MUNICIPAL con ámbito ENTE sin mirar el órgano (service_actas.py:788-789); un instituto o una fundación municipal los recibía como obligatorios |
| REP-10 | CORREGIDO | **Corregido el 2026-11-17 en GOV-SOD-COVERAGE-01**: REP-10 cuenta y agrupa los tres productores desde `service_sod_eventos.py`. Antes: la sección de conflictos SoD solo cuenta GOV_SOD_CONFLICT_BLOCKED (service_reporte_control.py:92); omite GOV_SOD_ROLE_CONFLICT_BLOCKED (PROC-11) y GOV_BUDGET_COMMITMENT_SOD_BLOCKED (BUD-08) |

## Backlog priorizado

- **P0 (2):** BUD-01, BUD-05, por refactor de régimen sin defecto de producto vigente (CNT-04, CTL-07, REP-10, PROC-07, PROC-08, ORG-04 y CTL-09 bajaron a P1 al corregirse su defecto). CURRENT_PRODUCT_DEFECT P0 = 0
- **P1 (28):** CNT-04, CTL-07, REP-10, PROC-07, PROC-08, ORG-04, CTL-09, ORG-02, ORG-03, BUD-02, BUD-06, BUD-08, PROC-02, PROC-10, CNT-01, CNT-02, CNT-03, CNT-07, CNT-09, TRE-01, TRE-02, DOC-02, DOC-08, CTL-01, CTL-04, CTL-05, CTL-06, CTL-10
- **P2 (9):** ORG-01, ORG-06, BUD-04, PROC-03, PROC-06, PROC-11, TRE-09, DOC-04, REP-03
- **Sin acción (5):** BUD-03, CNT-08, CTL-03, ORG-07 y CTL-02 (KEEP; sus defectos se corrigieron en ORG-07-EFFECTIVE-AUTHORITY-MATRIX y CTL-02-AUDIT-PROCESS-RESOLUTION)

## Detalle por proceso

### ORG-01 · Configurar el ente y su tipo

- **Clasificación:** ADAPT_TO_PROCESS_ENGINE
- **Prioridad:** P2
- **Motor:** NORMATIVE_BINDING DOCUMENT_RULES PROCESS_VERSION
- **Resumen:** Cada company_id tiene un ente (gov_entities, versionado en gov_entity_versions), así que denominación, RIF, adscripción, entidad federal y municipio son datos. Las tipologías legales (nivel territorial, forma organizativa, tipo de acto, prefijos de RIF) son enums cerrados repetidos en modelo, Pydantic, migración y frontend, sin fuente ni vigencia. La forma organizativa no incluye fundación, empresa del Estado ni asociación civil del Estado, y el nivel territorial no incluye uno distrital o metropolitano. Hoy esos entes solo caben en el genérico ENTE_DESCENTRALIZADO.
  - **CATALOG · LEGAL_MANDATORY:** nivel ∈ {NACIONAL, ESTADAL, MUNICIPAL}; forma ∈ {ADMINISTRACION_CENTRAL, INSTITUTO_PUBLICO, SERVICIO_DESCONCENTRADO, ENTE_DESCENTRALIZADO}; acto ∈ {LEY, DECRETO, ORDENANZA, RESOLUCION, OTRO}
    - Evidencia: `resources/backend/app/modules/government/models.py:23-31, 46-55` (NIVELES_TERRITORIALES, FORMAS_ORGANIZATIVAS, TIPOS_DE_ACTO (+CHECK gov_entities)).
    - Por qué puede variar: Fundaciones, empresas del Estado, asociaciones civiles del Estado y el nivel distrital o metropolitano no tienen un valor propio; la tipología cambia con la norma
    - Destino: LEGAL_VERSIONED_CATALOG (código, etiqueta, fuente, vigencia desde/hasta) referenciado por FK
    - Fuente: N01/N02/N24 citados en la Spec sin artículo (specs/gov-0-01-configurar-ente/spec.md:77-78)
  - **CATALOG · LEGAL_MANDATORY:** los mismos literales congelados en un CHECK de BD
    - Evidencia: `resources/backend/alembic/versions/0063_gov0_entes.py:69-74` (CHECK nivel_territorial / forma_organizativa).
    - Por qué puede variar: añadir una forma o un nivel exige migración y código
    - Destino: tabla de catálogo con FK en lugar de CHECK
    - Fuente: NONE
  - **CATALOG · LEGAL_MANDATORY:** Literal duplicados; prefijos de RIF fijos [JGVEP]
    - Evidencia: `resources/backend/app/modules/government/schemas.py:13-22` (NivelTerritorial, FormaOrganizativa, TipoDeActo, _RIF_RE).
    - Por qué puede variar: SENIAT puede añadir prefijos (p. ej. C, consejos comunales); los catálogos deben venir de datos
    - Destino: validación contra el catálogo versionado
    - Fuente: NONE
  - **CATALOG · LEGAL_MANDATORY:** catálogo y etiquetas repetidos en la UI
    - Evidencia: `resources/frontend/src/modules/gobierno/api.ts:13-19, 89-94` (NivelTerritorial, FormaOrganizativa, TipoDeActo, ETIQUETA_FORMA).
    - Por qué puede variar: igual que arriba
    - Destino: catálogo servido por la API
    - Fuente: NONE
  - **DOCUMENT · LEGAL_MANDATORY:** requisitos de activación fijos: adscripción si forma ≠ ADMINISTRACION_CENTRAL, entidad federal si ESTADAL/MUNICIPAL, municipio si MUNICIPAL, acto, publicación y documento obligatorios
    - Evidencia: `resources/backend/app/modules/government/service.py:55-82` (faltantes_para_activar).
    - Por qué puede variar: los requisitos dependen de la forma y el nivel elegidos; un catálogo nuevo necesita sus propias reglas
    - Destino: DOCUMENT_RULES por tipo de ente
    - Fuente: OD-GOV0-02 (decisión de la dueña)

### ORG-02 · Estructura organizativa por ejercicio (órgano, unidad ejecutora, dependencia, sede, centro gestor)

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** STAGES TRANSITIONS DOCUMENT_RULES CONTROL_RULES PROCESS_VERSION TENANT_POLICY
- **Resumen:** Unidades, códigos, nombres y jerarquía son datos por company_id y ejercicio (gov_structures, gov_units, gov_unit_versions). Sin embargo, la tipología de unidad es un catálogo cerrado de 6 valores por decisión de producto, no por ley. El ciclo BORRADOR→VIGENTE→CERRADA (con acto obligatorio y cierre desde el 1 de enero siguiente) y el ejercicio de año calendario están en el servicio.
  - **CATALOG · INSTITUTIONAL_POLICY:** ORGANO, UNIDAD_ADMINISTRATIVA, UNIDAD_EJECUTORA_LOCAL, DEPENDENCIA, SEDE, CENTRO_GESTOR
    - Evidencia: `resources/backend/app/modules/government/models.py:99-106, 148` (TIPOS_DE_UNIDAD (+CHECK unit_type)).
    - Por qué puede variar: una gobernación (secretarías), un instituto (gerencias, coordinaciones) o una fundación usan otra tipología
    - Destino: TENANT_CONFIGURABLE_CATALOG de tipos de unidad por company_id
    - Fuente: GOV-ORG-002 (requisito), sin ley
  - **CATALOG · INSTITUTIONAL_POLICY:** los mismos 6 literales en un CHECK de BD
    - Evidencia: `resources/backend/alembic/versions/0064_gov0_estructuras.py:87` (CHECK unit_type).
    - Por qué puede variar: añadir un tipo exige migración
    - Destino: FK a catálogo configurable
    - Fuente: NONE
  - **CATALOG · INSTITUTIONAL_POLICY:** Literal duplicado (también en resources/frontend/src/modules/gobierno/api.ts:166-172)
    - Evidencia: `resources/backend/app/modules/government/schemas_estructura.py:13-20` (TipoDeUnidad).
    - Por qué puede variar: igual
    - Destino: catálogo servido por la API
    - Fuente: NONE
  - **DEADLINE · LEGAL_MANDATORY:** ejercicio = 1 ene–31 dic; solo se cierra si ejercicio < año actual; CHECK exercise BETWEEN 2000 AND 2100 (models.py:118)
    - Evidencia: `resources/backend/app/modules/government/service_estructura.py:154-156, 945-950` (_rango, cerrar).
    - Por qué puede variar: el calendario fiscal es normativo (la Spec reconoce que no tiene artículo verificado)
    - Destino: BUSINESS_CALENDAR / FiscalYear versionado
    - Fuente: NONE (OD-ORG02-01; N03 sin artículo)
  - **WORKFLOW · INSTITUTIONAL_POLICY:** publicar exige al menos 1 unidad, documento del acto y ente activo; motivo obligatorio en VIGENTE; copia del ejercicio anterior
    - Evidencia: `resources/backend/app/modules/government/service_estructura.py:31-43, 875-970` (faltantes_para_publicar, publicar, cerrar).
    - Por qué puede variar: quién aprueba la estructura y qué soporte se exige varía (resolución, ordenanza, acuerdo de junta directiva)
    - Destino: STAGES TRANSITIONS DOCUMENT_RULES
    - Fuente: OD-ORG02-02/03
  - **NUMBERING · OPERATIONAL_CONFIGURATION:** referencia f"EST-{ejercicio}"
    - Evidencia: `resources/backend/app/modules/government/service_estructura.py:952` (cerrar → evaluar_cierre).
    - Por qué puede variar: convención de numeración
    - Destino: TENANT_POLICY de numeración
    - Fuente: NONE
  - **REPORT · OPERATIONAL_CONFIGURATION:** columnas y encabezados del CSV fijos
    - Evidencia: `resources/backend/app/modules/government/service_estructura.py:981-983` (exportar_csv).
    - Por qué puede variar: formato de entrega por institución
    - Destino: plantilla de reporte
    - Fuente: NONE

### ORG-03 · Cargos con competencias y límites de firma/aprobación

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** AUTHORITY_BINDING APPROVAL_RULES DOCUMENT_RULES STAGES TRANSITIONS NORMATIVE_BINDING TENANT_POLICY
- **Resumen:** Cargos, competencias y límites son datos por company_id y estructura (gov_positions, gov_position_competencies, gov_position_versions). Los límites de firma/aprobación son configurables por cargo y competencia, pero solo como «monto máximo por operación» en VES/USD/EUR: no existe UT ni otra unidad de referencia, ni vigencia del límite, ni límite acumulado o por periodo. El vocabulario de competencias (10 acciones × 6 materias) es cerrado y lo usan por código fijo otros procesos.
  - **CATALOG · INSTITUTIONAL_POLICY:** 10 acciones y 6 materias (PRESUPUESTO, CONTRATACIONES, TESORERIA, CONTABILIDAD, BIENES, EXPEDIENTE)
    - Evidencia: `resources/backend/app/modules/government/models.py:192-193, 251-252` (ACCIONES_COMPETENCIA, MATERIAS_COMPETENCIA (+CHECK action/subject)).
    - Por qué puede variar: faltan materias como RRHH/nómina, ingresos/tributos municipales o almacén; otra institución necesita competencias propias
    - Destino: catálogo de competencias (acción × materia) versionado, con extensiones por company_id
    - Fuente: OD-ORG03-02 (decisión de la dueña), GOV-ORG-010
  - **CATALOG · INSTITUTIONAL_POLICY:** Literal duplicados (también en schemas_ocupacion.py:44-65 y resources/frontend/src/modules/gobierno/api.ts:260-279)
    - Evidencia: `resources/backend/app/modules/government/schemas_cargos.py:16-19` (AccionCompetencia, MateriaCompetencia, TipoDeLimite, MonedaDeLimite).
    - Por qué puede variar: igual
    - Destino: catálogo servido por la API
    - Fuente: NONE
  - **AMOUNT · LEGAL_MANDATORY:** límite = SIN_LIMITE o MONTO por operación en VES/USD/EUR; no hay UT, unidad de cuenta ni tipo de referencia, ni vigencia, ni acumulado
    - Evidencia: `resources/backend/app/modules/government/models.py:194-195, 253-257` (TIPOS_DE_LIMITE, MONEDAS_LIMITE, CHECK limite_coherente).
    - Por qué puede variar: los límites de firma y aprobación suelen fijarse en ordenanzas o resoluciones en UT u otra unidad que cambia con la norma; hoy cada cambio de valor obliga a reescribir los montos a mano
    - Destino: AUTHORITY_BINDING con unidad de referencia versionada (valor, fuente, vigencia) y modalidad (por operación, mensual o anual)
    - Fuente: OD-ORG03-03 (sin artículo)
  - **AMOUNT · LEGAL_MANDATORY:** monedas VES/USD/EUR en un CHECK de BD
    - Evidencia: `resources/backend/alembic/versions/0065_gov0_cargos.py:97` (CHECK limit_currency).
    - Por qué puede variar: reconversión o unidades de cuenta nuevas
    - Destino: FK a catálogo de monedas/unidades
    - Fuente: NONE
  - **AUTHORITY · INSTITUTIONAL_POLICY:** los consumidores exigen pares codificados (APROBAR × CONTRATACIONES; también FIRMAR × CONTRATACIONES en service_contratos.py:577, 645)
    - Evidencia: `resources/backend/app/modules/government/service_decision_limite.py:54-57` (competencia_aprobar_contrataciones).
    - Por qué puede variar: qué competencia habilita cada acto depende del reglamento interno
    - Destino: AUTHORITY_BINDING por paso del PROCESS_DEFINITION
    - Fuente: NONE
  - **WORKFLOW · INSTITUTIONAL_POLICY:** VIGENTE exige estructura VIGENTE, al menos 1 competencia y documento del acto; en VIGENTE, cambiar competencias exige el permiso de publicar
    - Evidencia: `resources/backend/app/modules/government/service_cargos.py:45-57, 300-308` (faltantes_para_activar, _exigir_autoridad).
    - Por qué puede variar: el soporte exigido y quién aprueba los cambios de autoridad varían
    - Destino: STAGES TRANSITIONS DOCUMENT_RULES APPROVAL_RULES
    - Fuente: OD-ORG03-04

### ORG-04 · Delegaciones, suplencias, encargadurías y designaciones con acto

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1 (era P0 por el defecto, corregido)
- **Estado tras ORG-04-AUTHORITY-ASSIGNMENT-POLICY (2026-11-18):** CURRENT_PRODUCT_DEFECT=NO. Plazos, autorización especial, medio del acto, emisor, competencias permitidas, avocación y documentos pasan a pisos legales versionados (NORMATIVE_BINDING por nivel territorial) y política del ente por figura (TENANT_POLICY con versiones y congelación). Quedan como PLATFORM_INVARIANT las 6 figuras y su grupo (D-AP-01) y la numeración ASG-/FUN-. FUTURE_ARCHITECTURE_REFACTOR=STILL_PENDING para el motor de procesos general.
- **Motor:** NORMATIVE_BINDING AUTHORITY_BINDING DEADLINES DOCUMENT_RULES SOD_RULES STAGES TRANSITIONS CONTROL_RULES TENANT_POLICY
- **Resumen:** Funcionarios, asignaciones, actos y competencias delegadas se guardan por company_id (gov_officials, gov_assignments, gov_assignment_competencies, gov_*_history). Las figuras de ocupación, su base legal, los plazos (15 y 90 días LOPPM, 1 año LEFP) y las reglas LOAP 34/35/40/41 son literales en el código sin versión. La base legal es solo municipal y se aplica a cualquier tipo de ente.
  - **CATALOG · LEGAL_MANDATORY:** 6 figuras con grupo, base_legal, exige_fin, exige_cargo_origen y exige_gaceta fijos; TITULAR «LOPPM art. 88.7», ENCARGADURIA y SUPLENCIA «LOPPM art. 87» para todos los niveles
    - Evidencia: `resources/backend/app/modules/government/service_ocupacion.py:49-110` (FIGURAS).
    - Por qué puede variar: un ente nacional o estadal se rige por LOAP/LEFP, la Constitución estadal o leyes de consejos legislativos, no por la LOPPM
    - Destino: NORMATIVE_BINDING por nivel territorial, catálogo de figuras versionado (fuente, vigencia)
    - Fuente: LOPPM arts. 87, 88.7; LEFP arts. 71-72; LOAP arts. 34, 35, 37, 40
  - **DEADLINE · LEGAL_MANDATORY:** suplencia de máxima autoridad MUNICIPAL: más de 15 días exige autorización del Concejo y más de 90 días se rechaza; ninguna regla para el nivel ESTADAL/NACIONAL
    - Evidencia: `resources/backend/app/modules/government/service_ocupacion.py:723-745` (validar (paso 7)).
    - Por qué puede variar: plazos legales que cambian con la norma y otros regímenes por nivel
    - Destino: DEADLINES + NORMATIVE_BINDING por nivel
    - Fuente: LOPPM art. 87
  - **DEADLINE · LEGAL_MANDATORY:** comisión de servicio de 1 año como máximo
    - Evidencia: `resources/backend/app/modules/government/service_ocupacion.py:711-721` (validar (paso 6)).
    - Por qué puede variar: plazo legal
    - Destino: DEADLINES versionados
    - Fuente: LEFP art. 72
  - **AUTHORITY · LEGAL_MANDATORY:** delegación publicada en GACETA; DELEGACION_FIRMA solo FIRMAR; solo se delega lo que tiene el cargo; lo delegado no se delega; el delegado depende del delegante; avocación solo de delegaciones
    - Evidencia: `resources/backend/app/modules/government/service_ocupacion.py:515-525, 606-661, 747-764, 1096-1097` (_exigir_acto, _competencias_a_delegar, _exigir_emisor, validar (paso 8), avocar).
    - Por qué puede variar: reglas LOAP correctas hoy pero sin vigencia; los estatutos de entes descentralizados pueden regular la delegación de otra forma
    - Destino: NORMATIVE_BINDING + AUTHORITY_BINDING
    - Fuente: LOAP arts. 34, 35, 40, 41
  - **WORKFLOW · INSTITUTIONAL_POLICY:** la vigencia de toda asignación, también la de TITULAR, debe caber en el año del ejercicio del cargo
    - Evidencia: `resources/backend/app/modules/government/service_ocupacion.py:498-504` (_exigir_cargo_utilizable).
    - Por qué puede variar: las designaciones de titulares duran varios años; obliga a registrarlas de nuevo cada ejercicio
    - Destino: STAGES/TRANSITIONS con traspaso entre ejercicios
    - Fuente: NONE
  - **WORKFLOW · LEGAL_MANDATORY:** «Autorización del Concejo» y la ayuda LOPPM art. 87 se muestran en toda suplencia de máxima autoridad, sin condicionar a nivel MUNICIPAL
    - Evidencia: `resources/frontend/src/modules/gobierno/ocupacion/NuevaAsignacionPage.tsx:839-865` (campo autorizacion_concejo).
    - Por qué puede variar: solo aplica a alcaldías
    - Destino: campos dinámicos según NORMATIVE_BINDING del ente
    - Fuente: LOPPM art. 87
  - **CATALOG · LEGAL_MANDATORY:** figuras y reglas en CHECK de BD (también en alembic/versions/0076_gov_org04_ocupacion.py:128-149); columna con nombre municipal
    - Evidencia: `resources/backend/app/modules/government/models.py:2213-2214, 2299-2313, 2330` (FIGURAS_ASIGNACION, GRUPOS_ASIGNACION, CHECK grupo_de_figura / temporal_con_fin / delegacion_completa; columna autorizacion_concejo).
    - Por qué puede variar: una figura nueva o un órgano autorizante distinto (Consejo Legislativo, junta directiva) exige migración
    - Destino: catálogo de figuras versionado + «autorización del órgano competente» genérica
    - Fuente: LOPPM art. 87
  - **SOD · INSTITUTIONAL_POLICY:** cuatro ojos fijo (quien registra no activa; nadie registra su propia ocupación); el resto va por evaluar_antes_de_actuar con reglas configurables
    - Evidencia: `resources/backend/app/modules/government/service_ocupacion.py:881-888, 1005-1011` (activar, _exigir_no_autoridad_propia).
    - Por qué puede variar: razonable como invariante, pero es política de segregación
    - Destino: SOD_RULES
    - Fuente: NONE
  - **NUMBERING · OPERATIONAL_CONFIGURATION:** prefijos FUN-/ASG- con correlativo de 5 dígitos por conteo
    - Evidencia: `resources/backend/app/modules/government/service_ocupacion.py:172-193` (_siguiente_codigo_funcionario, _siguiente_codigo_asignacion).
    - Por qué puede variar: convención de numeración institucional
    - Destino: TENANT_POLICY de numeración
    - Fuente: NONE

### ORG-06 · Vincular usuario con identidad, cargo, unidad y alcance; separación de roles

- **Clasificación:** ADAPT_TO_PROCESS_ENGINE
- **Prioridad:** P2
- **Motor:** STAGES TRANSITIONS SOD_RULES CONTROL_RULES TENANT_POLICY
- **Resumen:** El vínculo cuenta–funcionario, las categorías por rol, la política de exigencia de identidad y las incompatibilidades entre categorías son datos por company_id (gov_user_official_links, gov_role_categories, gov_identity_policies.exige_identidad, gov_sod_rules con proceso='ORG-06'). Lo que está en código es el ciclo del vínculo con cuatro ojos y el catálogo cerrado de 5 categorías de separación. La exigencia de identidad viene desactivada por defecto.
  - **CATALOG · PLATFORM_INVARIANT:** OPERATIVO, APROBADOR, CONTROL_INTERNO, AUDITORIA, ADMINISTRACION_TECNICA (también en models.py:2246, schemas_identidad.py:16-18 y en service_sod.py:109-113 como ORG06_CAT_*)
    - Evidencia: `resources/backend/app/modules/government/service_identidad.py:44-54` (CATEGORIAS_IDENTIDAD).
    - Por qué puede variar: poco; una institución con tesorería o custodia separadas podría querer más categorías
    - Destino: catálogo de categorías extensible por company_id (opcional)
    - Fuente: NONE
  - **WORKFLOW · INSTITUTIONAL_POLICY:** BORRADOR→ACTIVO→CERRADO/REVOCADO; quien registra no activa; nadie actúa sobre su propio vínculo
    - Evidencia: `resources/backend/app/modules/government/service_identidad.py:228-249, 511-525` (_exige_no_autovinculo, activar).
    - Por qué puede variar: las transiciones y la aprobación son workflow que debería declararse
    - Destino: STAGES TRANSITIONS SOD_RULES
    - Fuente: NONE
  - **WORKFLOW · OPERATIONAL_CONFIGURATION:** si no hay política, exige_identidad=False: las acciones protegidas no comprueban el cargo
    - Evidencia: `resources/backend/app/modules/government/service_identidad.py:1375-1378, 1478-1483` (politica, exigir_autoridad_funcional).
    - Por qué puede variar: es configurable por ente (gov_identity_policies), pero el valor por defecto es permisivo
    - Destino: TENANT_POLICY con valor por defecto explícito por perfil de Gobierno
    - Fuente: OD-ORG06-09
  - **NUMBERING · OPERATIONAL_CONFIGURATION:** prefijo VIN- con correlativo de 5 dígitos
    - Evidencia: `resources/backend/app/modules/government/service_identidad.py:97-106` (_siguiente_codigo_vinculo).
    - Por qué puede variar: convención de numeración
    - Destino: TENANT_POLICY de numeración
    - Fuente: NONE

### ORG-07 · Matriz auditable de quién puede solicitar, comprometer, causar, pagar, custodiar, aprobar y auditar

- **Clasificación:** KEEP_AS_IS
- **Prioridad:** NONE (antes P1)
- **Motor:** NONE
- **Estado tras ORG-07-EFFECTIVE-AUTHORITY-MATRIX (2026-11-19):** CURRENT_PRODUCT_DEFECT=NO. La matriz sigue siendo una proyección sin tablas propias: consume la autoridad del cargo (ORG-03) y la efectiva que resuelve ORG-04 a la fecha de corte (titular, encargaduría, suplencia, comisión de servicio y delegaciones con sus límites). `origen` usa el vocabulario de ORG-04 y cada fila derivada lleva su fuente (asignación, vigencia, acto y cargo de origen). Se quitó el aviso «llegarán». Las personas solo se ven con `gobierno_ocupacion:view` (OD-EA-01).
- **Resumen (auditoría original):** Vista correcta respecto a la parametrización, porque todo sale de los datos de ORG-03. Tiene un defecto funcional actual: no integra la autoridad delegada ni la ocupación.
  - **AUTHORITY · PLATFORM_INVARIANT:** "origen": "CARGO" constante; no lee gov_assignments ni gov_assignment_competencies
    - Evidencia: `resources/backend/app/modules/government/service_autoridad.py:290-345` (_filas_filtradas).
    - Por qué puede variar: no es variación institucional: es un defecto de completitud
    - Destino: sumar las filas de origen DELEGACION/SUPLENCIA/ENCARGADURIA desde ORG-04
    - Fuente: NONE
  - **REPORT · PLATFORM_INVARIANT:** texto desactualizado «llegarán con ORG-06 / ORG-04»
    - Evidencia: `resources/frontend/src/modules/gobierno/autoridad/MatrizAutoridadPage.tsx:620-622` (aviso de origen).
    - Por qué puede variar: no varía; está obsoleto
    - Destino: quitar el aviso al integrar ORG-04/06
    - Fuente: NONE
  - **DEADLINE · LEGAL_MANDATORY:** ejercicio = año calendario (date(ejercicio,12,31))
    - Evidencia: `resources/backend/app/modules/government/service_autoridad.py:29-45, 292` (_fecha_corte, _filas_filtradas).
    - Por qué puede variar: depende del calendario fiscal normativo
    - Destino: BUSINESS_CALENDAR / FiscalYear
    - Fuente: NONE (OD-ORG02-01)
  - **REPORT · OPERATIONAL_CONFIGURATION:** orden por el índice del catálogo de acciones y materias; columnas del CSV fijas
    - Evidencia: `resources/backend/app/modules/government/service_autoridad.py:111-118, 419-440` (_clave_orden, exportar_matriz_csv).
    - Por qué puede variar: formato de reporte
    - Destino: plantilla de reporte
    - Fuente: NONE

### BUD-01 · Ejercicio económico-financiero

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P0
- **Motor:** PROCESS_DEFINITION PROCESS_VERSION STAGES TRANSITIONS DOCUMENT_RULES DEADLINES BUSINESS_CALENDAR NORMATIVE_BINDING TENANT_POLICY
- **Resumen:** Los niveles programáticos y las categorías son datos por company_id/year_id (gov_budget_program_levels, gov_budget_categories). Pero el acto de aprobación (ORDENANZA), las fechas de reconducción y cierre (LOPPM 234/236/248) y el calendario 1 ene–31 dic están en literales y CHECK, así que el proceso solo sirve para el régimen municipal.
  - **CATALOG · LEGAL_MANDATORY:** el acto de fijación solo puede ser ("ORDENANZA","RECONDUCCION")
    - Evidencia: `resources/backend/app/modules/government/models.py:1020,1123` (TIPOS_FUNDAMENTO_PRESUPUESTARIO / GovernmentBudgetYearFoundation CHECK tipo).
    - Por qué puede variar: una gobernación aprueba por ley estadal del Consejo Legislativo; un instituto autónomo o una fundación aprueba por acto de su órgano de adscripción o directivo
    - Destino: catálogo de tipos de acto de aprobación por régimen normativo (NORMATIVE_BINDING + TENANT_POLICY por tipo de ente)
    - Fuente: LOPPM art. 229 (spec.md:20)
  - **WORKFLOW · LEGAL_MANDATORY:** aprobar crea siempre un fundamento "ORDENANZA" y pone el estado APROBADO
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto.py:1219,1259` (_fijar / aprobar).
    - Por qué puede variar: el acto y su emisor dependen del tipo de ente
    - Destino: PROCESS_DEFINITION por régimen con su acto requerido
    - Fuente: LOPPM art. 229
  - **DEADLINE · LEGAL_MANDATORY:** la reconducción solo procede tras el 15-dic del año anterior y con fecha desde el 16-dic
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto.py:1295-1302` (reconducir).
    - Por qué puede variar: los plazos de sanción y reconducción difieren en la normativa estadal y en la de entes descentralizados
    - Destino: DEADLINES + NORMATIVE_BINDING con vigencia
    - Fuente: LOPPM art. 234
  - **DEADLINE · LEGAL_MANDATORY:** la reconducción es definitiva a partir del 31 de marzo del año
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto.py:347,456` (listar / detalle (reconduccion_definitiva)).
    - Por qué puede variar: el plazo es municipal (LOPPM 236) y no es universal
    - Destino: DEADLINES por régimen
    - Fuente: LOPPM art. 236 (spec.md:48)
  - **DEADLINE · LEGAL_MANDATORY:** el ejercicio va del 1-ene al 31-dic en literales date(anio,1,1)/date(anio,12,31), sin modelo de calendario
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto.py:880-881,1246,1346,1379` (aprobar / cerrar / cambiar_precompromiso / _validar_partida).
    - Por qué puede variar: el ejercicio coincide con el año civil por ley, pero la fuente no está versionada ni vinculada (LOPPM 248/250 para municipios, otra ley para otros entes)
    - Destino: BUSINESS_CALENDAR + NORMATIVE_BINDING (fecha_inicio/fecha_fin del ejercicio)
    - Fuente: LOPPM arts. 248, 250
  - **CATALOG · OPERATIONAL_CONFIGURATION:** entre 1 y 8 niveles programáticos, cada nombre de 1 a 80 caracteres
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto.py:510 (y models.py:1141)` (configurar_niveles / GovernmentBudgetProgramLevel CHECK orden).
    - Por qué puede variar: la estructura programática (sector, programa, subprograma, proyecto, actividad...) varía por ente y por instructivo ONAPRE
    - Destino: TENANT_POLICY (máximo de niveles)
    - Fuente: NONE
  - **NUMBERING · OPERATIONAL_CONFIGURATION:** el código de segmento es [0-9A-Za-z-]{1,20} y el código completo se arma con separador "."
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto.py:36,605` (RE_CODIGO_CATEGORIA / crear_categoria).
    - Por qué puede variar: el formato de la categoría programática (separador, longitud fija por nivel, ceros a la izquierda) varía por instructivo e institución
    - Destino: TENANT_POLICY con máscara por nivel (longitud y separador)
    - Fuente: NONE
  - **REPORT · LEGAL_MANDATORY:** textos "Ordenanza de presupuesto sancionada" y "Reconducción ... (LOPPM art. 234)"; también api.ts:40 (tipo "ORDENANZA"|"RECONDUCCION") y api.ts:311 ("Aprobado por ordenanza")
    - Evidencia: `resources/frontend/src/modules/gobierno/presupuesto/AccionesEjercicio.tsx:167,177` (textos de acción).
    - Por qué puede variar: el nombre del acto y la norma citada dependen del régimen del ente
    - Destino: etiquetas derivadas de NORMATIVE_BINDING
    - Fuente: LOPPM arts. 229, 234

### BUD-02 · Clasificador presupuestario versionado

- **Clasificación:** KEEP_AS_IS
- **Prioridad:** P1
- **Motor:** NONE
- **Resumen:** El clasificador está versionado por ejercicio y ente, con edición, procedencia, documento con sha256 y vigencia por partida. Solo quedan fijos el par RECURSO/EGRESO y límites amplios de nivel y longitud.
  - **CATALOG · PLATFORM_INVARIANT:** ("RECURSO","EGRESO")
    - Evidencia: `resources/backend/app/modules/government/models.py:1021` (TIPOS_PARTIDA_CLASIFICADOR).
    - Por qué puede variar: no varía: es la estructura dual del presupuesto público
    - Destino: NONE
    - Fuente: NONE
  - **CATALOG · LEGAL_MANDATORY:** nada normativo: el modelo SÍ tiene versión y vigencia (edicion, fecha_edicion, procedencia, documento_sha256, vigente_desde, vigente_hasta)
    - Evidencia: `resources/backend/app/modules/government/models.py:1166-1202` (GovernmentBudgetClassifier / GovernmentBudgetClassifierItem).
    - Por qué puede variar: el clasificador ONAPRE cambia por edición; ya está cubierto
    - Destino: NONE
    - Fuente: specs/gov-bud-01-02-ejercicio-clasificador (BUD12-*)
  - **NUMBERING · OPERATIONAL_CONFIGURATION:** código [0-9A-Za-z.-]{1,40}, nivel de 1 a 12, sin máscara de formato
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto.py:37,860 (y models.py:1200)` (RE_CODIGO_PARTIDA / _validar_partida).
    - Por qué puede variar: límites amplios; una máscara ONAPRE (p. ej. 4.01.01.01.00) no se valida y queda a cargo del tenant
    - Destino: opcional: máscara por edición en GovernmentBudgetClassifier
    - Fuente: NONE
  - **DEADLINE · LEGAL_MANDATORY:** la vigencia de la partida queda forzada dentro del 1-ene–31-dic del año
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto.py:880-881,916-919` (_validar_partida).
    - Por qué puede variar: depende del calendario del ejercicio de BUD-01
    - Destino: BUSINESS_CALENDAR del ejercicio
    - Fuente: LOPPM art. 250

### BUD-03 · Plan, programas, proyectos, metas físicas e indicadores

- **Clasificación:** KEEP_AS_IS
- **Prioridad:** NONE
- **Motor:** NONE
- **Resumen:** Son datos puros por company_id/year_id, con unidades derivadas de la estructura organizativa vigente del ente. No hay etapas, aprobadores ni catálogos fijos.
  - **ORGANIZATION · PLATFORM_INVARIANT:** la unidad ejecutora se toma de GovernmentStructure con exercise == ejercicio.anio y estado VIGENTE
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_plan.py:36-56` (_unidades_disponibles).
    - Por qué puede variar: no varía: se deriva de ORG del tenant
    - Destino: NONE
    - Fuente: NONE
  - **AMOUNT · OPERATIONAL_CONFIGURATION:** la meta debe ser > 0, < 1e14 y con un máximo de 4 decimales
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_plan.py:434-443` (_validar_cantidad).
    - Por qué puede variar: solo es un límite técnico de precisión
    - Destino: NONE
    - Fuente: NONE

### BUD-04 · Fuentes de financiamiento y restricciones

- **Clasificación:** ADAPT_TO_PROCESS_ENGINE
- **Prioridad:** P2
- **Motor:** CONTROL_RULES NORMATIVE_BINDING
- **Resumen:** Las fuentes son datos libres por ejercicio y ente (código, denominación, procedencia, documento, vigencia), sin un catálogo de tipos fijo. Pero la única restricción expresable es una lista blanca de partidas de egreso, y su "fundamento" es texto libre sin vínculo normativo.
  - **CATALOG · PLATFORM_INVARIANT:** nada: no hay enum de tipos de fuente (ordinario, situado, FCI, etc.) y cada tenant los registra
    - Evidencia: `resources/backend/app/modules/government/models.py:1292-1311` (GovernmentBudgetFundingSource).
    - Por qué puede variar: -
    - Destino: NONE
    - Fuente: NONE
  - **CATALOG · LEGAL_MANDATORY:** una restricción es solo descripcion + fundamento (texto) + lista de partidas; no admite porcentajes, montos, categorías ni unidades
    - Evidencia: `resources/backend/app/modules/government/models.py:1314-1323` (GovernmentBudgetFundingRestriction).
    - Por qué puede variar: hay restricciones legales por fuente que se expresan como porcentaje o destino (p. ej. mínimo de inversión de transferencias) y varían por ley y por ejercicio
    - Destino: CONTROL_RULES tipadas (partida, categoría, porcentaje mínimo o máximo) con NORMATIVE_BINDING y vigencia
    - Fuente: NONE
  - **CATALOG · PLATFORM_INVARIANT:** las restricciones solo admiten partidas de tipo EGRESO
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_fuentes.py:80` (_normalizar_partidas).
    - Por qué puede variar: -
    - Destino: NONE
    - Fuente: NONE
  - **DEADLINE · LEGAL_MANDATORY:** la vigencia por defecto es el 1-ene y debe caer dentro del año del ejercicio
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_fuentes.py:161-165` (_validar_fechas).
    - Por qué puede variar: depende del calendario del ejercicio
    - Destino: BUSINESS_CALENDAR
    - Fuente: LOPPM art. 250

### BUD-05 · Formulación: anteproyecto, proyecto y presupuesto aprobado con su acto

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P0
- **Motor:** CONTROL_RULES NORMATIVE_BINDING PROCESS_VERSION STAGES DOCUMENT_RULES
- **Resumen:** Ingresos, créditos (categoría × partida × fuente) y existencias son datos por ente. La regla de cuadre municipal (créditos ≤ ingresos + ½ existencias) está fija en código y no tiene versión. Anteproyecto y proyecto como etapas están en LATER_PHASE.
  - **AMOUNT · LEGAL_MANDATORY:** holgura = existencias/2; exige 2·Σcréditos ≤ 2·Σingresos + existencias
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_aprobado.py:843,915-918` (_totales_para_verificar / verificar_para_fijar).
    - Por qué puede variar: el factor y la regla de equilibrio son propios de la LOPPM; los entes estadales y descentralizados tienen otra regla
    - Destino: CONTROL_RULES parametrizada (factor de existencias) con NORMATIVE_BINDING y vigencia
    - Fuente: LOPPM art. 240
  - **CONTROL · LEGAL_MANDATORY:** todo crédito exige categoría programática
    - Evidencia: `resources/backend/app/modules/government/models.py:1394` (GovernmentBudgetCredit.category_id nullable=False).
    - Por qué puede variar: la Spec la deriva de "cuando la norma local exija" (LOPPM 239); otro régimen podría no exigirla
    - Destino: CONTROL_RULES por régimen
    - Fuente: LOPPM art. 239 (spec gov-bud-05 línea 13)
  - **DEADLINE · OPERATIONAL_CONFIGURATION:** la fecha de corte de las existencias va del 1-ene del año anterior a hoy
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_aprobado.py:743-745` (registrar_existencias).
    - Por qué puede variar: la fecha de corte exigible depende del calendario de formulación del ente
    - Destino: TENANT_POLICY / DEADLINES
    - Fuente: NONE
  - **WORKFLOW · LEGAL_MANDATORY:** sin etapas anteproyecto ni proyecto: solo BORRADOR→APROBADO/RECONDUCIDO (GOV-BUD-006/007 en LATER_PHASE)
    - Evidencia: `resources/backend/app/modules/government/models.py:1019` (ESTADOS_EJERCICIO_PRESUPUESTARIO).
    - Por qué puede variar: las etapas de formulación y sus actos (presentación, discusión, sanción) varían por régimen
    - Destino: PROCESS_DEFINITION + PROCESS_VERSION + STAGES
    - Fuente: LOPPM arts. 229 ss.
  - **REPORT · LEGAL_MANDATORY:** textos "Transcriba la ordenanza de presupuesto" y "Cuadre (LOPPM art. 240)"
    - Evidencia: `resources/frontend/src/modules/gobierno/presupuesto/PresupuestoAprobadoEjercicio.tsx:119,510,616` (sección Cuadre).
    - Por qué puede variar: el acto y la norma dependen del régimen
    - Destino: etiquetas desde NORMATIVE_BINDING
    - Fuente: LOPPM art. 240

### BUD-06 · Disponibilidad y certificación de disponibilidad

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** AUTHORITY_BINDING DOCUMENT_RULES NORMATIVE_BINDING BUSINESS_CALENDAR TENANT_POLICY
- **Resumen:** La fórmula de disponibilidad es un invariante de dominio. La competencia del firmante (FIRMAR × PRESUPUESTO), el formato del número CDP-AAAA-NNNN, la cita legal del PDF y la exigencia de expediente están fijos en código.
  - **AUTHORITY · INSTITUTIONAL_POLICY:** el firmante debe tener la competencia codificada FIRMAR × PRESUPUESTO (_autoridad_valida + exigir_autoridad_funcional)
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_certificacion.py:613-621` (emitir).
    - Por qué puede variar: quién certifica (Dirección de Presupuesto, Administración, Planificación) y con qué acción lo decide cada ente
    - Destino: AUTHORITY_BINDING configurable por proceso y operación
    - Fuente: NONE
  - **NUMBERING · INSTITUTIONAL_POLICY:** codigo = f"CDP-{anio}-{numero:04d}", correlativo por ejercicio
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_certificacion.py:634-640` (emitir).
    - Por qué puede variar: el prefijo, el relleno y la serie por unidad son de cada institución
    - Destino: TENANT_POLICY de series de numeración
    - Fuente: NONE
  - **DEADLINE · LEGAL_MANDATORY:** solo se certifica si hoy.year == ejercicio.anio
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_certificacion.py:555-557` (emitir).
    - Por qué puede variar: depende del calendario y del régimen
    - Destino: BUSINESS_CALENDAR + NORMATIVE_BINDING
    - Fuente: LOPPM art. 250
  - **DOCUMENT · INSTITUTIONAL_POLICY:** exige un expediente de contratación o una referencia de 3 a 120 caracteres, y un concepto de 10 a 500
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_certificacion.py:582-604` (emitir).
    - Por qué puede variar: que el soporte sea obligatorio y de qué tipo (expediente, requisición, nómina) varía por ente
    - Destino: DOCUMENT_RULES
    - Fuente: NONE
  - **REPORT · LEGAL_MANDATORY:** título fijo y pie "Certificación emitida conforme a LOPPM art. 242"; sin logo y con encabezado solo de Company.legal_name
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_certificacion.py:284,324` (_render_pdf).
    - Por qué puede variar: la norma citada, el formato institucional y el logo varían por ente
    - Destino: plantilla de reporte por TENANT_POLICY + NORMATIVE_BINDING
    - Fuente: LOPPM art. 242
  - **REPORT · LEGAL_MANDATORY:** cita "(LOPPM art. 242)"
    - Evidencia: `resources/frontend/src/modules/gobierno/presupuesto/DisponibilidadEjercicio.tsx:133` (texto de ayuda).
    - Por qué puede variar: depende del régimen
    - Destino: NORMATIVE_BINDING
    - Fuente: LOPPM art. 242

### BUD-08 · Compromiso presupuestario

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** AUTHORITY_BINDING SOD_RULES CONTROL_RULES STAGES DOCUMENT_RULES BUSINESS_CALENDAR TENANT_POLICY NORMATIVE_BINDING
- **Resumen:** El límite de la autoridad sale de competencias por ente y usa la tasa BCV de TRE-09. Pero la competencia COMPROMETER × PRESUPUESTO, la regla SoD "quien certifica no compromete", la CDP previa obligatoria, el tope de 20 líneas y el número CP-AAAA-NNNN están en código. La política de precompromiso de BUD-01 no se consulta.
  - **AUTHORITY · INSTITUTIONAL_POLICY:** exige la competencia codificada COMPROMETER × PRESUPUESTO
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_compromiso.py:232-238,421,638-648` (emitir / opciones / verificacion_limite).
    - Por qué puede variar: quién compromete (máxima autoridad o delegatario) y bajo qué acción lo fija cada ente
    - Destino: AUTHORITY_BINDING
    - Fuente: NONE
  - **WORKFLOW · LEGAL_MANDATORY:** SoD fija: si el actor (o un usuario o funcionario equivalente) emitió o firmó la CDP, la operación se bloquea; está en código y no en las reglas de service_sod
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_compromiso.py:584-609` (emitir).
    - Por qué puede variar: el alcance de la incompatibilidad (emisor, firmante, unidad) puede variar; la Spec la declara vinculante (B08-16, ARCH §8) sin artículo ni versión
    - Destino: SOD_RULES con NORMATIVE_BINDING
    - Fuente: spec gov-bud-08 B08-16 (CTL-01); sin artículo citado
  - **WORKFLOW · INSTITUTIONAL_POLICY:** todo compromiso consume CDP VIGENTES (no hay ruta directa contra el crédito), y GovernmentBudgetYear.precompromiso_activo no se lee
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_compromiso.py:519-561` (emitir).
    - Por qué puede variar: hay entes que comprometen directamente contra la disponibilidad sin certificación previa
    - Destino: STAGES/CONTROL_RULES opcionales por TENANT_POLICY (usar precompromiso_activo)
    - Fuente: NONE
  - **AMOUNT · OPERATIONAL_CONFIGURATION:** entre 1 y 20 líneas de imputación
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_compromiso.py:520-521` (emitir).
    - Por qué puede variar: un compromiso de nómina o multipartida puede necesitar más
    - Destino: TENANT_POLICY
    - Fuente: NONE
  - **NUMBERING · INSTITUTIONAL_POLICY:** codigo = f"CP-{anio}-{numero:04d}"
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_compromiso.py:698-704` (emitir).
    - Por qué puede variar: la serie y el formato son institucionales
    - Destino: TENANT_POLICY de series
    - Fuente: NONE
  - **DEADLINE · LEGAL_MANDATORY:** solo se compromete si hoy.year == ejercicio.anio
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_compromiso.py:350,511-513` (emitir / opciones).
    - Por qué puede variar: depende del calendario y del régimen
    - Destino: BUSINESS_CALENDAR + NORMATIVE_BINDING
    - Fuente: LOPPM art. 248
  - **DOCUMENT · INSTITUTIONAL_POLICY:** todas las CDP deben compartir expediente, y el documento de soporte es obligatorio
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_compromiso.py:574-581,694` (emitir).
    - Por qué puede variar: los requisitos documentales del compromiso (orden de compra, contrato, nómina) varían
    - Destino: DOCUMENT_RULES
    - Fuente: NONE
  - **REPORT · LEGAL_MANDATORY:** pie "Compromiso registrado conforme a LOPPM arts. 242 y 248"
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_compromiso.py:206` (_render_pdf_compromiso).
    - Por qué puede variar: depende del régimen
    - Destino: plantilla + NORMATIVE_BINDING
    - Fuente: LOPPM arts. 242, 248

### PROC-02 · Comisión de contrataciones (miembros, suplentes, impedimentos)

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** SOD_RULES CONTROL_RULES DOCUMENT_RULES DEADLINES BUSINESS_CALENDAR NORMATIVE_BINDING TENANT_POLICY
- **Resumen:** La composición de la comisión (número impar de principales, las 3 áreas, un suplente por principal, secretario y su suplente, acto en gaceta) y las causales de inhibición son reglas legales escritas como literales, sin versión en el modelo. Además el código obliga a que otra persona active la comisión y resuelva la inhibición. Esto no pasa por las reglas CTL-01 (PROC02_ACTIVAR), así que una institución no puede desactivarlo.
  - **AUTHORITY · INSTITUTIONAL_POLICY:** Quien registró la comisión no puede activarla y quien declaró la inhibición no puede resolverla (usuarios_equivalentes), fijo en código y aparte de las reglas SoD configurables
    - Evidencia: `resources/backend/app/modules/government/service_comisiones.py:887-891, 1353-1357` (activar / resolver_inhibicion).
    - Por qué puede variar: Un ente pequeño con un solo operador, o con otra política de cuatro ojos, necesita activarlo o desactivarlo. El spec lo pone como decisión de diseño, no como norma
    - Destino: SOD_RULES (regla CTL-01 PROC02_REGISTRAR→PROC02_ACTIVAR por company_id) + TENANT_POLICY
    - Fuente: NONE
  - **WORKFLOW · LEGAL_MANDATORY:** Principales en número impar, un principal por cada área, suplente para cada principal, secretario y su suplente
    - Evidencia: `resources/backend/app/modules/government/service_comisiones.py:281-305` (_faltantes).
    - Por qué puede variar: Composición mínima tomada de LCP 2014. Una reforma cambia la regla y exige desplegar código
    - Destino: NORMATIVE_BINDING + CONTROL_RULES versionadas (source/version/effective_from/to)
    - Fuente: LCP art. 14
  - **CATALOG · LEGAL_MANDATORY:** Áreas JURIDICA, TECNICA y ECONOMICO_FINANCIERA en una tupla y en un CHECK de la base
    - Evidencia: `resources/backend/app/modules/government/models.py:2225, 2435` (AREAS_COMISION / CheckConstraint area).
    - Por qué puede variar: Catálogo legal sin vigencia, y el CHECK de BD obliga a migrar si la norma cambia
    - Destino: NORMATIVE_BINDING (catálogo legal versionado)
    - Fuente: LCP art. 14
  - **CATALOG · LEGAL_MANDATORY:** 4 causales de inhibición y 4 causas de fin de miembro (también en models.py:2227-2228)
    - Evidencia: `resources/backend/app/modules/government/service_comisiones.py:64-69, 79-96` (CAUSALES / ETIQUETAS["causas"]).
    - Por qué puede variar: Vienen del RLCP 2009, que puede sustituirse
    - Destino: NORMATIVE_BINDING
    - Fuente: RLCP art. 18
  - **DOCUMENT · LEGAL_MANDATORY:** El acto de creación debe estar EFICAZ y su medio debe ser "GACETA"
    - Evidencia: `resources/backend/app/modules/government/service_comisiones.py:244-249` (_acto_valido).
    - Por qué puede variar: El medio de publicación exigible depende del tipo de ente y de la versión de la norma
    - Destino: DOCUMENT_RULES + NORMATIVE_BINDING
    - Fuente: RLCP art. 15
  - **CATALOG · LEGAL_MANDATORY:** La versión de la norma es el literal "LCP-2014+RLCP-2009". Se guarda en la comisión al activarla (línea 909), pero el conjunto de reglas no tiene vigencia propia
    - Evidencia: `resources/backend/app/modules/government/service_comisiones.py:40, 51-54` (REGLA_VERSION / FUENTE_REGLA).
    - Por qué puede variar: Con una norma nueva no pueden convivir dos versiones de regla
    - Destino: PROCESS_VERSION + NORMATIVE_BINDING
    - Fuente: LCP art. 14; RLCP arts. 15, 18, 20
  - **DEADLINE · LEGAL_MANDATORY:** La notificación al SNC solo se marca pendiente; no se calcula el plazo legal de 5 días (OD-PROC02-06)
    - Evidencia: `resources/backend/app/modules/government/service_comisiones.py:767` (detalle (snc_pendiente)).
    - Por qué puede variar: Contar el plazo en días hábiles o continuos requiere un calendario por ente
    - Destino: DEADLINES + BUSINESS_CALENDAR
    - Fuente: LCP art. 14
  - **WORKFLOW · LEGAL_MANDATORY:** La inhibición se guarda con un asunto en texto libre y no se enlaza al expediente. Una inhibición ACEPTADA no impide al miembro asistir a la apertura, evaluar ni firmar en PROC-07/08
    - Evidencia: `resources/backend/app/modules/government/models.py:2452` (GovernmentProcurementCommitteeConflict.asunto).
    - Por qué puede variar: La inhibición debe excluir al miembro de ese procedimiento (fuera de alcance declarado, OD-PROC02-05)
    - Destino: CONTROL_RULES
    - Fuente: RLCP art. 18

### PROC-03 · Expediente único de contratación con cronología y lapsos

- **Clasificación:** ADAPT_TO_PROCESS_ENGINE
- **Prioridad:** P2
- **Motor:** PROCESS_DEFINITION STAGES TRANSITIONS DOCUMENT_RULES DEADLINES BUSINESS_CALENDAR NORMATIVE_BINDING
- **Resumen:** La numeración del expediente es libre por ente: el usuario la escribe y se valida única por company_id (service_expedientes.py:1252-1260), así que no hay hardcode de numeración. Las modalidades, las clases de folio (RLCP 32) y la secuencia de pendientes y siguiente acción están fijas en código, no se calculan lapsos ni hay umbrales de monto por modalidad.
  - **CATALOG · LEGAL_MANDATORY:** 4 modalidades (CONCURSO_ABIERTO, CONCURSO_CERRADO, CONSULTA_PRECIOS, CONTRATACION_DIRECTA) y 3 tipos, también en CHECK (models.py:2525-2526) y en etiquetas (service_expedientes.py:40-50)
    - Evidencia: `resources/backend/app/modules/government/models.py:2231-2232` (MODALIDADES_DECLARADAS / TIPOS_CONTRATACION).
    - Por qué puede variar: Catálogo legal de la LCP 2014 sin versión ni vigencia
    - Destino: NORMATIVE_BINDING (catálogo de modalidades versionado)
    - Fuente: NONE (no se cita en la constante)
  - **AMOUNT · LEGAL_MANDATORY:** La modalidad es la que declara la unidad, con fundamento obligatorio. No hay umbrales (UT/TCMMV) ni comprobación de monto frente a la modalidad
    - Evidencia: `resources/backend/app/modules/government/service_expedientes.py:174-176` (_AVISO_MODALIDAD).
    - Por qué puede variar: Los umbrales legales cambian con la norma y con el valor de la unidad de cálculo
    - Destino: NORMATIVE_BINDING + CONTROL_RULES (umbral por modalidad y tipo con vigencia)
    - Fuente: NONE
  - **DOCUMENT · LEGAL_MANDATORY:** 23 clases de folio con su artículo y su marca de condicional (también en el CHECK de models.py:2236, 2616)
    - Evidencia: `resources/backend/app/modules/government/service_expedientes.py:144-168` (CLASES_FOLIO).
    - Por qué puede variar: El contenido mínimo del expediente viene del RLCP 2009, sin versión
    - Destino: DOCUMENT_RULES + NORMATIVE_BINDING
    - Fuente: RLCP art. 32
  - **DOCUMENT · LEGAL_MANDATORY:** Siempre pide PLIEGO, LLAMADO_INVITACION, ACTA_RECEPCION y las demás clases de selección no condicionales, sea cual sea la modalidad
    - Evidencia: `resources/backend/app/modules/government/service_expedientes.py:170-172, 1015-1022` (_CLASES_SELECCION_NO_CONDICIONAL / siguiente_accion).
    - Por qué puede variar: Los documentos exigibles dependen de la modalidad (por ejemplo, la contratación directa no tiene llamado)
    - Destino: DOCUMENT_RULES condicionadas por modalidad
    - Fuente: RLCP art. 32
  - **WORKFLOW · LEGAL_MANDATORY:** Secuencia fija de pendientes: PARTES, RESPONSABLE, MODALIDAD, COMISION, HITOS, SOLICITUD, INICIO, y luego APERTURA_PENDIENTE → EVALUACION_PENDIENTE → RECOMENDACION_PENDIENTE (invariante de dominio)
    - Evidencia: `resources/backend/app/modules/government/service_expedientes.py:896-1004` (detalle (pendientes)).
    - Por qué puede variar: Las etapas y transiciones cambian según la modalidad y la versión del procedimiento
    - Destino: STAGES + TRANSITIONS + PROCESS_VERSION
    - Fuente: LCP art. 19; RLCP art. 33
  - **DEADLINE · LEGAL_MANDATORY:** Los hitos solo comparan fecha prevista con hoy. No se calculan lapsos en días hábiles o continuos
    - Evidencia: `resources/backend/app/modules/government/service_expedientes.py:177-179, 938-945` (_AVISO_LAPSOS / HITO_SUPERADO).
    - Por qué puede variar: Cada modalidad tiene sus lapsos y cada ente su calendario
    - Destino: DEADLINES + BUSINESS_CALENDAR
    - Fuente: NONE

### PROC-06 · Recepción y apertura de ofertas

- **Clasificación:** ADAPT_TO_PROCESS_ENGINE
- **Prioridad:** P2
- **Motor:** CONTROL_RULES DOCUMENT_RULES DEADLINES NORMATIVE_BINDING
- **Resumen:** Los canales, los tipos de sobre y el sello obligatorio por modalidad son reglas legales fijas sin versión. La recepción se cierra a mano y no hay fecha límite configurable.
  - **CATALOG · LEGAL_MANDATORY:** 3 canales y 3 tipos de sobre, también en CHECK (models.py:2767-2768)
    - Evidencia: `resources/backend/app/modules/government/service_ofertas.py:46-55` (_CANALES / _TIPOS_SOBRE).
    - Por qué puede variar: Catálogo legal (sobres separados, LCP art. 78) que puede cambiar, por ejemplo hacia la contratación electrónica
    - Destino: NORMATIVE_BINDING
    - Fuente: LCP art. 78
  - **WORKFLOW · LEGAL_MANDATORY:** Sello obligatorio en concursos y también cuando no hay modalidad declarada (esta parte es default de producto, FR-007). En las demás modalidades decide la unidad con motivo
    - Evidencia: `resources/backend/app/modules/government/service_ofertas.py:56, 296-307` (_MODALIDADES_SELLO_OBLIGATORIO / recibir_oferta).
    - Por qué puede variar: La exigencia de sello depende de la modalidad y de la versión de la norma
    - Destino: CONTROL_RULES por modalidad + NORMATIVE_BINDING
    - Fuente: LCP art. 92
  - **WORKFLOW · LEGAL_MANDATORY:** Un concurso exige comisión vinculada o declarar que no interviene
    - Evidencia: `resources/backend/app/modules/government/service_ofertas.py:301-303` (recibir_oferta).
    - Por qué puede variar: Literal legal sin vigencia
    - Destino: CONTROL_RULES
    - Fuente: LCP art. 92; RLCP art. 33
  - **DEADLINE · LEGAL_MANDATORY:** La recepción se cierra manualmente. No hay fecha y hora límite del llamado ni rechazo de ofertas que lleguen tarde
    - Evidencia: `resources/backend/app/modules/government/service_ofertas.py:425-437` (concluir_recepcion).
    - Por qué puede variar: El lapso de recepción depende de la modalidad y del pliego, en días hábiles o continuos
    - Destino: DEADLINES + BUSINESS_CALENDAR
    - Fuente: NONE

### PROC-07 · Evaluación técnica, económica y legal con matriz bloqueada

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** STAGES TRANSITIONS RESPONSIBILITY_BINDING APPROVAL_RULES CONTROL_RULES EVIDENCE_RULES TENANT_POLICY NORMATIVE_BINDING
- **Defecto actual (PROC-07/PROC-08-COMMISSION-POLICY, 2026-11-17):** antes YES, ahora NO. El quórum de apertura sale de la política del ente (TENANT_POLICY versionada); se excluye al miembro inhibido en el expediente y, sin comisión, abren los responsables del expediente. Siguen pendientes los aspectos y las escalas de evaluación como catálogos fijos.
  - FUTURE_ARCHITECTURE_REFACTOR=STILL_PENDING
- **Resumen:** El quórum de mayoría simple es una decisión de la dueña, no una norma, y está fijo en backend y frontend. El acto de apertura está atado a la comisión aunque haya modalidades sin comisión. Los aspectos y las escalas de evaluación son catálogos fijos.
  - **WORKFLOW · INSTITUTIONAL_POLICY:** quorum = miembros_con_voto // 2 + 1, repetido en resources/frontend/src/modules/gobierno/contrataciones/ExpedienteEvaluacion.tsx:1011
    - Evidencia: `resources/backend/app/modules/government/service_evaluacion.py:387-390` (abrir_ofertas (quorum_requerido)).
    - Por qué puede variar: El spec FR-003 lo marca como «decisión de la dueña». El reglamento interno de cada comisión puede fijar otro quórum
    - Destino: APPROVAL_RULES + TENANT_POLICY (quórum por comisión o ente)
    - Fuente: NONE
  - **WORKFLOW · LEGAL_MANDATORY:** La apertura exige comisión vinculada y vigente. No hay camino para la unidad contratante cuando no interviene comisión (también resources/backend/app/modules/government/service_evaluacion_resultados.py:78)
    - Evidencia: `resources/backend/app/modules/government/service_evaluacion.py:325-326` (abrir_ofertas).
    - Por qué puede variar: El responsable de la apertura cambia con la modalidad
    - Destino: RESPONSIBILITY_BINDING por modalidad + STAGES
    - Fuente: RLCP art. 33
  - **CATALOG · LEGAL_MANDATORY:** TECNICO, ECONOMICO y LEGAL, y la matriz exige criterios en los 3
    - Evidencia: `resources/backend/app/modules/government/service_evaluacion.py:42, 288` (_ASPECTOS / bloquear_matriz).
    - Por qué puede variar: Literal legal sin versión
    - Destino: NORMATIVE_BINDING + EVIDENCE_RULES
    - Fuente: NONE en código
  - **CATALOG · OPERATIONAL_CONFIGURATION:** Solo dos escalas (PUNTAJE con máximo, CUMPLE). La ponderación es opcional y no se agrega (FR-006: sin fórmulas)
    - Evidencia: `resources/backend/app/modules/government/service_evaluacion.py:189-196` (anadir_criterio).
    - Por qué puede variar: Cada pliego o ente usa sus métodos (porcentaje, umbral mínimo de calificación, precio evaluado)
    - Destino: CONTROL_RULES (catálogo de escalas y agregación por ente)
    - Fuente: NONE
  - **WORKFLOW · LEGAL_MANDATORY:** Tras la primera oferta no se pueden cambiar criterios; solo se acepta una transcripción de un pliego incorporado antes
    - Evidencia: `resources/backend/app/modules/government/service_evaluacion.py:131-134, 181-186` (anadir_criterio / crear_matriz).
    - Por qué puede variar: Literal legal sin vigencia
    - Destino: CONTROL_RULES + NORMATIVE_BINDING
    - Fuente: LCP art. 95
  - **WORKFLOW · LEGAL_MANDATORY:** Los asistentes son los miembros con fin_efectivo nulo. No se excluyen los que tienen inhibición ACEPTADA
    - Evidencia: `resources/backend/app/modules/government/service_evaluacion.py:95-106` (_miembros_comision).
    - Por qué puede variar: El miembro inhibido no debe actuar en ese procedimiento
    - Destino: CONTROL_RULES
    - Fuente: RLCP art. 18

### PROC-08 · Recomendación, decisión, adjudicación, desierta, anulación o rechazo

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** STAGES TRANSITIONS AUTHORITY_BINDING APPROVAL_RULES SOD_RULES CONTROL_RULES EXCEPTIONS NORMATIVE_BINDING TENANT_POLICY
- **Defecto actual (PROC-07/PROC-08-COMMISSION-POLICY, 2026-11-17):** antes YES, ahora NO. Quórum y mayoría de la recomendación (base, voto del presidente y voto dirimente) salen de la política del ente; se excluye al inhibido y, sin comisión, firman los responsables del expediente. Siguen pendientes las causales y los pares de competencia de la decisión.
  - FUTURE_ARCHITECTURE_REFACTOR=STILL_PENDING
- **Resumen:** El límite de monto de la autoridad sí sale de las competencias que configura cada ente (service_decision_limite.py:60-78). Lo fijo en código es la competencia exigida APROBAR×CONTRATACIONES, el quórum de firmantes (decisión de la dueña), las causales legales sin versión, el máximo de tres opciones y el formato del informe PDF.
  - **WORKFLOW · INSTITUTIONAL_POLICY:** Los firmantes con voto deben ser mayoría simple de los principales, repetido en resources/frontend/src/modules/gobierno/contrataciones/ExpedienteDecision.tsx:398
    - Evidencia: `resources/backend/app/modules/government/service_decision.py:880-883` (emitir_recomendacion (quorum_requerido)).
    - Por qué puede variar: PDD-PROC08-10 dice «misma regla de quórum que la apertura (decisión de la dueña)». Varía según el reglamento interno
    - Destino: APPROVAL_RULES + TENANT_POLICY
    - Fuente: NONE
  - **WORKFLOW · LEGAL_MANDATORY:** La recomendación siempre exige comisión vinculada
    - Evidencia: `resources/backend/app/modules/government/service_decision.py:842-843` (emitir_recomendacion).
    - Por qué puede variar: En las modalidades sin comisión recomienda otro órgano (la unidad contratante)
    - Destino: RESPONSIBILITY_BINDING por modalidad + TRANSITIONS
    - Fuente: RLCP art. 33
  - **AUTHORITY · LEGAL_MANDATORY:** El acto debe ser EMITIDO o EFICAZ, PARTICULAR y con competencia_accion=="APROBAR" y competencia_materia=="CONTRATACIONES" (también en resources/backend/app/modules/government/service_decision.py:199-203)
    - Evidencia: `resources/backend/app/modules/government/service_decision_resolver.py:154-179` (registrar_decision).
    - Por qué puede variar: La competencia la asigna cada ente, pero el par de competencias exigido está escrito en código
    - Destino: AUTHORITY_BINDING (competencia exigida por acción en la definición del proceso)
    - Fuente: NONE en código (PDD-PROC08-04)
  - **CATALOG · LEGAL_MANDATORY:** 5 causales de desierta, 14 de rechazo y 2 de nulidad, también en models.py:2241-2245
    - Evidencia: `resources/backend/app/modules/government/service_decision.py:60-95` (CAUSALES_DESIERTA / CAUSALES_RECHAZO / CAUSALES_NULIDAD).
    - Por qué puede variar: Cada causal cita su artículo pero no tiene versión ni vigencia
    - Destino: NORMATIVE_BINDING
    - Fuente: LCP arts. 76, 112, 113; RLCP art. 102
  - **WORKFLOW · LEGAL_MANDATORY:** Máximo 3 opciones. Pasar a la siguiente opción solo procede tras una nulidad por INFORMACION_FALSA (service_decision_resolver.py:257-260)
    - Evidencia: `resources/backend/app/modules/government/service_decision.py:935-936` (emitir_recomendacion).
    - Por qué puede variar: Literal legal sin vigencia
    - Destino: EXCEPTIONS + NORMATIVE_BINDING
    - Fuente: LCP art. 110
  - **AUTHORITY · LEGAL_MANDATORY:** Quien firmó la recomendación no puede decidir. Solo aplica con la política de identidad del ente activa
    - Evidencia: `resources/backend/app/modules/government/service_decision_resolver.py:183-199` (registrar_decision).
    - Por qué puede variar: Regla SoD en código, fuera de la matriz SoD
    - Destino: SOD_RULES
    - Fuente: LCP arts. 14-15 (PDD-PROC08-11)
  - **REPORT · OPERATIONAL_CONFIGURATION:** PDF tamaño carta con título fijo «Informe de recomendación», sin membrete, sin nombre del ente ni logo
    - Evidencia: `resources/backend/app/modules/government/service_decision.py:661-677` (_render_informe).
    - Por qué puede variar: Cada institución usa su membrete y su formato
    - Destino: TENANT_POLICY (plantilla de informe por ente)
    - Fuente: NONE
  - **NUMBERING · OPERATIONAL_CONFIGURATION:** Referencias "DEC-{n:02d}", "REC-{n:02d}" y "O-{n:02d}". La misma oferta es "R-{n:04d}" en service_ofertas.py:67-68, así que la referencia no es coherente
    - Evidencia: `resources/backend/app/modules/government/service_decision.py:160-166` (_parte_decision).
    - Por qué puede variar: Formato fijo e incoherente entre procesos
    - Destino: TENANT_POLICY (serie de numeración)
    - Fuente: NONE

### PROC-10 · Garantías y cauciones

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** NORMATIVE_BINDING AUTHORITY_BINDING DEADLINES NOTIFICATIONS TENANT_POLICY
- **Resumen:** Los porcentajes legales están en un catálogo con codigo, version, fuente, gaceta y vigente_desde/hasta, y cada requisito guarda una instantánea de la regla (gov_guarantee_requirements.regla_codigo y regla, models.py:3755-3756). Ese catálogo vive en código, así que una norma nueva exige desplegar. El umbral «por vencer» de 15 días es una decisión de la dueña. Limitación declarada: base_disponible() devuelve None (garantias_reglas.py:386-388), así que los requisitos porcentuales salen NO_EVALUABLE.
  - **AMOUNT · LEGAL_MANDATORY:** Mantenimiento de oferta 1,50–2,50 %; anticipo 100 %; fiel cumplimiento mínimo 20 % con retención alternativa del 10 %; laboral hasta 10 % con retención del 5 %
    - Evidencia: `resources/backend/app/modules/government/garantias_reglas.py:136-137, 208-209, 232-238, 257-262` (REGLAS).
    - Por qué puede variar: Cambian con la reforma de la LCP/RLCP. Tienen versión y vigencia, pero en código Python, no en datos
    - Destino: NORMATIVE_BINDING persistido (tabla normativa con source/version/effective_from/to)
    - Fuente: LCP arts. 63-64, 71, 122-124; RLCP arts. 91, 135-136
  - **DEADLINE · OPERATIONAL_CONFIGURATION:** 15 días naturales para «por vencer» (se usa en service_garantias.py:655)
    - Evidencia: `resources/backend/app/modules/government/garantias_reglas.py:37-38` (DIAS_POR_VENCER).
    - Por qué puede variar: Es un preaviso operativo (PDD-PROC10-07, decisión de la dueña). Cada ente fija su anticipación
    - Destino: DEADLINES + NOTIFICATIONS + TENANT_POLICY
    - Fuente: NONE
  - **AUTHORITY · LEGAL_MANDATORY:** Liberar y ejecutar exigen un acto con competencia APROBAR×CONTRATACIONES (también en la línea 982)
    - Evidencia: `resources/backend/app/modules/government/service_garantias.py:161-177` (validación del acto de liberar/ejecutar).
    - Por qué puede variar: La competencia exigida está en código. Un ente puede asignar la liberación a otra competencia o materia, por ejemplo administración
    - Destino: AUTHORITY_BINDING
    - Fuente: LCP arts. 122-123, 151; RLCP art. 194 (PDD-PROC10-12)
  - **CATALOG · LEGAL_MANDATORY:** 6 tipos, 3 etapas y 4 tipos de emisor. La laboral solo admite BANCO, ASEGURADORA o SGR. Los tipos están en CHECK de BD (models.py:3775-3777)
    - Evidencia: `resources/backend/app/modules/government/garantias_reglas.py:12-25, 259` (TIPOS_GARANTIA / ETAPAS_GARANTIA / TIPOS_EMISOR).
    - Por qué puede variar: Las reglas tienen versión pero los catálogos no
    - Destino: NORMATIVE_BINDING
    - Fuente: LCP art. 124

### PROC-11 · Conflictos SoD en contratación

- **Clasificación:** ADAPT_TO_PROCESS_ENGINE
- **Prioridad:** P2
- **Motor:** SOD_RULES RESPONSIBILITY_BINDING PROCESS_DEFINITION STAGES
- **Resumen:** La matriz de incompatibilidades es configurable por ente, con vigencia y versión (gov_sod_role_rules: company_id, rol_a, rol_b, vigente_desde/hasta, estado; models.py:943-972). El catálogo de funciones y la forma de deducir quién ejerce cada función desde los registros de PROC-02/03/06/07/08 están fijos en código y atados a PROC-03.
  - **CATALOG · PLATFORM_INVARIANT:** SOLICITANTE, RECEPTOR, EVALUADOR y ADJUDICADOR; PAGADOR no está disponible. Lo replica el CHECK de BD (models.py:925, 971-972)
    - Evidencia: `resources/backend/app/modules/government/service_sod_funciones.py:48-79` (FUNCIONES).
    - Por qué puede variar: Si el motor define otras etapas, por ejemplo de garantías o contratos, harán falta funciones nuevas sin migrar
    - Destino: SOD_RULES + STAGES
    - Fuente: NONE
  - **WORKFLOW · PLATFORM_INVARIANT:** Correspondencia fija de registro a función: creador y REQUIRENTE son SOLICITANTE; oferta, RECEPTOR; miembros, asistentes, aportes, recomendación y firmantes, EVALUADOR; decisión, ADJUDICADOR
    - Evidencia: `resources/backend/app/modules/government/service_sod_funciones.py:429-635` (ocupacion).
    - Por qué puede variar: Qué actuación cuenta como qué función depende de la definición del proceso
    - Destino: RESPONSIBILITY_BINDING
    - Fuente: NONE
  - **CATALOG · PLATFORM_INVARIANT:** proceso = 'PROC-03'
    - Evidencia: `resources/backend/app/modules/government/models.py:970` (CheckConstraint proceso).
    - Por qué puede variar: Impide aplicar la matriz a otros procesos
    - Destino: PROCESS_DEFINITION
    - Fuente: NONE
  - **AUTHORITY · PLATFORM_INVARIANT:** Catálogo cerrado de acciones SoD (PROC02_*, PROC03_*) unidas a eventos de auditoría concretos. Además hay reglas SoD en código fuera de este catálogo (service_comisiones.py:887-891, 1353-1357)
    - Evidencia: `resources/backend/app/modules/government/service_sod.py:24-158` (CATALOGO_SOD).
    - Por qué puede variar: Agregar acciones o etapas exige cambiar código
    - Destino: SOD_RULES
    - Fuente: NONE

### CNT-01 · Crear contrato u orden desde la adjudicación

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** PROCESS_DEFINITION STAGES TRANSITIONS AUTHORITY_BINDING APPROVAL_RULES DOCUMENT_RULES CONTROL_RULES SOD_RULES NORMATIVE_BINDING TENANT_POLICY
- **Resumen:** El límite del firmante ya sale de la competencia de cada cargo (limite_de_competencia, configurable por ente). En cambio, la numeración CT/OC/OS-AAAA-NNNN y la competencia FIRMAR×CONTRATACIONES están en código. El catálogo legal de instrumentos y las reglas de cobertura (exacta y de un solo ejercicio) también son fijos, y la propia Spec dice que esas reglas son decisión pendiente.
  - **NUMBERING · INSTITUTIONAL_POLICY:** Prefijos CT, OC y OS
    - Evidencia: `resources/backend/app/modules/government/models.py:4533` (PREFIJOS_INSTRUMENTO_CONTRATO).
    - Por qué puede variar: Cada ente tiene su propia serie y nomenclatura de contratos y órdenes
    - Destino: TENANT_POLICY de numeración (serie, prefijo, reinicio anual y plantilla)
    - Fuente: NONE
  - **NUMBERING · INSTITUTIONAL_POLICY:** Formato "{prefijo}-{anio}-{numero:04d}", secuencia por ente, tipo y año (columna String(20), models.py 4548). También la referencia de oferta "R-{numero:04d}" (893)
    - Evidencia: `resources/backend/app/modules/government/service_contratos.py:1306-1317` (formalizar codigo).
    - Por qué puede variar: El formato, el reinicio anual y el ancho de la secuencia son política del ente
    - Destino: TENANT_POLICY de numeración
    - Fuente: NONE
  - **CATALOG · LEGAL_MANDATORY:** CONTRATO, ORDEN_COMPRA y ORDEN_SERVICIO como enum y CHECK, sin vigencia
    - Evidencia: `resources/backend/app/modules/government/models.py:4531, 4584` (TIPOS_INSTRUMENTO_CONTRATO (+CHECK tipo)).
    - Por qué puede variar: Deriva de LCP art. 6 num. 32 y puede cambiar con la norma. Está duplicado en el frontend (resources/frontend/src/modules/gobierno/contratos/api.ts 4, 264-268; expedientes-contractuales/ExpedientesContractualesPage.tsx 156)
    - Destino: NORMATIVE_VERSIONED_CONFIGURATION
    - Fuente: LCP art. 6 num. 32
  - **AUTHORITY · INSTITUTIONAL_POLICY:** El firmante debe tener FIRMAR×CONTRATACIONES. El límite se lee de la competencia del cargo, y eso sí es configurable
    - Evidencia: `resources/backend/app/modules/government/service_contratos.py:577-578, 1248-1254` (control_firmante, formalizar).
    - Por qué puede variar: La acción y la materia exigidas son un binding fijo; otro ente puede separar la firma de contratos y la de órdenes, o usar otra materia
    - Destino: AUTHORITY_BINDING por tipo de instrumento en TENANT_POLICY
    - Fuente: NONE
  - **AMOUNT · INSTITUTIONAL_POLICY:** La cobertura CDP debe ser exactamente igual al monto del contrato y todas las CDP del mismo ejercicio
    - Evidencia: `resources/backend/app/modules/government/service_contratos.py:1025-1026, 1209-1214` (asignaciones / formalizar).
    - Por qué puede variar: LCP 74 (párr. 3) y 75 admiten contratos por el monto disponible y plurianuales; la Spec lo deja abierto (OQ-CNT01-01: «decisión de la dueña o jurídica»)
    - Destino: CONTROL_RULES + TENANT_POLICY (modo de cobertura, plurianualidad) con NORMATIVE_BINDING
    - Fuente: LCP arts. 74, 75
  - **DOCUMENT · LEGAL_MANDATORY:** Obligatorios: plazo, referencia del instrumento, documento firmado y cobertura completa
    - Evidencia: `resources/backend/app/modules/government/service_contratos.py:668-678` (pendientes de formalización).
    - Por qué puede variar: Otro ente puede exigir más soportes, por ejemplo un dictamen jurídico o el visto bueno de control interno
    - Destino: DOCUMENT_RULES
    - Fuente: NONE

### CNT-02 · Adendas, prórrogas y variaciones versionadas

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** PROCESS_DEFINITION PROCESS_VERSION STAGES TRANSITIONS AUTHORITY_BINDING APPROVAL_RULES DOCUMENT_RULES CONTROL_RULES SOD_RULES NORMATIVE_BINDING TENANT_POLICY
- **Resumen:** No hay topes porcentuales de variación (OQ-CNT02-01: no se inventan); el único límite es el del firmante sobre el monto efectivo nuevo, que viene de la competencia del cargo. Son fijos la numeración AD/PR/MO/VA, el bloqueo de contratos vencidos (que la Spec dice que la dueña puede relajar), la no retroactividad y el catálogo legal de tipos.
  - **CATALOG · LEGAL_MANDATORY:** ADENDA, PRORROGA, MODIFICACION y VARIACION, sin vigencia
    - Evidencia: `resources/backend/app/modules/government/models.py:4702, 4758` (TIPOS_MODIFICACION_CONTRATO (+CHECK tipo)).
    - Por qué puede variar: Deriva de LCP 130-135 y cambia con la norma. Duplicado en el frontend (contratos/api.ts 129, 270-275)
    - Destino: NORMATIVE_VERSIONED_CONFIGURATION
    - Fuente: LCP arts. 130-135
  - **NUMBERING · INSTITUTIONAL_POLICY:** "{codigo_contrato}/{AD|PR|MO|VA}-{numero:03d}", una secuencia por contrato
    - Evidencia: `resources/backend/app/modules/government/service_contratos_modificaciones.py:1373-1374 (models.py 4704)` (formalizar codigo; PREFIJOS_MODIFICACION_CONTRATO).
    - Por qué puede variar: La nomenclatura de adendas y prórrogas es propia de cada ente
    - Destino: TENANT_POLICY de numeración
    - Fuente: NONE
  - **WORKFLOW · INSTITUTIONAL_POLICY:** Se bloquea toda modificación si el plazo efectivo ya venció
    - Evidencia: `resources/backend/app/modules/government/service_contratos_modificaciones.py:382, 1090-1095` (GOV_CONTRACT_AMENDMENT_CONTRACT_EXPIRED).
    - Por qué puede variar: La Spec lo marca como opción conservadora que la dueña puede relajar (OQ-CNT02-03); otro ente puede admitir prórrogas tramitadas a tiempo pero formalizadas tarde
    - Destino: CONTROL_RULES + TENANT_POLICY
    - Fuente: NONE
  - **DEADLINE · INSTITUTIONAL_POLICY:** fecha_instrumento ≤ hoy, vigente_desde ≥ hoy (sin retroactividad) y vigente_desde ≥ fecha_instrumento
    - Evidencia: `resources/backend/app/modules/government/service_contratos_modificaciones.py:413-424, 1145` (validación de fechas).
    - Por qué puede variar: La no retroactividad es una decisión de diseño (C02-17), no una norma citada; otro ente puede necesitar registrar modificaciones con efectos ya producidos
    - Destino: CONTROL_RULES/TENANT_POLICY
    - Fuente: NONE
  - **AUTHORITY · INSTITUTIONAL_POLICY:** Firmante con FIRMAR×CONTRATACIONES; el límite se compara con el monto efectivo nuevo (C02-15)
    - Evidencia: `resources/backend/app/modules/government/service_contratos_modificaciones.py:1300-1308` (formalizar).
    - Por qué puede variar: El binding acción/materia es fijo; otro ente puede exigir otra autoridad para las variaciones
    - Destino: AUTHORITY_BINDING por tipo de modificación
    - Fuente: NONE
  - **AMOUNT · LEGAL_MANDATORY:** No hay topes de aumento ni plazos de solicitud: ausencia deliberada, sin modelo para incorporarlos
    - Evidencia: `specs/gov-cnt-02-adendas-variaciones/spec.md:78` (OQ-CNT02-01).
    - Por qué puede variar: El RLCP puede fijar topes porcentuales o plazos y una reforma puede añadirlos; hoy exigirían código
    - Destino: NORMATIVE_VERSIONED_CONFIGURATION (topes de variación por tipo y vigencia)
    - Fuente: N12 RLCP (sin copia local, según la Spec)

### CNT-03 · Ejecución: hitos, entregables, valuaciones, recepciones y cierre; factura contra recepción

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** PROCESS_DEFINITION PROCESS_VERSION STAGES TRANSITIONS RESPONSIBILITY_BINDING AUTHORITY_BINDING APPROVAL_RULES DOCUMENT_RULES EVIDENCE_RULES CONTROL_RULES SOD_RULES NORMATIVE_BINDING TENANT_POLICY
- **Resumen:** El flujo de ejecución (inicio, terminación de obra, recepciones, cierre) está codificado por tipo OBRAS o BIENES_SERVICIOS. El representante en las recepciones de obra debe tener APROBAR×CONTRATACIONES, y el aprobador del cierre (Comisión o Unidad Contratante) se fija según haya comité. No hay retenciones ni porcentajes en las valuaciones (son de CNT-06); el único porcentaje es el del hito, de 0 a 100.
  - **WORKFLOW · LEGAL_MANDATORY:** INICIO, TERMINACION y CIERRE; PARCIAL, PROVISIONAL y DEFINITIVA; estados de valuación
    - Evidencia: `resources/backend/app/modules/government/models.py:5044, 5048-5049` (TIPOS_ACTUACION_EJECUCION, TIPOS_RECEPCION_CONTRATO, ESTADOS_VALUACION).
    - Por qué puede variar: Derivan de LCP 127, 146-151 y RLCP 177; la secuencia de recepciones cambia con la norma
    - Destino: STAGES/TRANSITIONS con NORMATIVE_BINDING (PROCESS_VERSION)
    - Fuente: LCP arts. 127, 147, 151
  - **WORKFLOW · LEGAL_MANDATORY:** OBRAS frente a BIENES_SERVICIOS decide la terminación de obra, la recepción parcial y la obligación del representante
    - Evidencia: `resources/backend/app/modules/government/service_contratos_ejecucion.py:114-115, 1124-1129, 1194-1199, 1327-1338` (_flujo, terminar_obra, registrar_recepcion).
    - Por qué puede variar: Es una variante de proceso por tipo de contratación que debería declararse en la definición del proceso y no con if
    - Destino: PROCESS_DEFINITION por tipo de contratación
    - Fuente: LCP arts. 146-151
  - **AUTHORITY · INSTITUTIONAL_POLICY:** El representante del contratante en la aceptación provisional o la recepción definitiva de obras debe tener APROBAR×CONTRATACIONES
    - Evidencia: `resources/backend/app/modules/government/service_contratos_ejecucion.py:1348-1360, 2303-2309` (registrar_recepcion (representante), opciones).
    - Por qué puede variar: La competencia exigida es una decisión de diseño; otro ente puede delegar la recepción a una dirección técnica con otra competencia
    - Destino: AUTHORITY_BINDING
    - Fuente: NONE
  - **ORGANIZATION · LEGAL_MANDATORY:** Aprueba la COMISION si el expediente tiene comité y, si no, la UNIDAD_CONTRATANTE (unidad_nombre del expediente)
    - Evidencia: `resources/backend/app/modules/government/service_contratos_ejecucion.py:1715-1725 (models.py 5045)` (cerrar (aprobador_tipo); APROBADORES_CIERRE).
    - Por qué puede variar: El órgano que aprueba el cierre sale de la norma (FUENTES CNT-07: «Comisión o Unidad Contratante») y puede variar con la reforma o con la organización del ente
    - Destino: RESPONSIBILITY_BINDING/APPROVAL_RULES con NORMATIVE_BINDING
    - Fuente: LCP art. 151
  - **DOCUMENT · LEGAL_MANDATORY:** El cierre exige recepción DEFINITIVA conforme y dos documentos distintos (acta de aprobación y evaluación)
    - Evidencia: `resources/backend/app/modules/government/service_contratos_ejecucion.py:1688-1706` (cerrar).
    - Por qué puede variar: El conjunto documental del cierre puede ampliarse por norma o por política (finiquito, solvencias)
    - Destino: DOCUMENT_RULES
    - Fuente: LCP arts. 51, 151
  - **NUMBERING · OPERATIONAL_CONFIGURATION:** Referencias por contrato "HIT-NN", "ENT-NN", "VAL-NN", "REC-NN" y "FAC-NN"
    - Evidencia: `resources/backend/app/modules/government/service_contratos_ejecucion.py:580, 713, 995, 1440, 1634` (referencias HIT/ENT/VAL/REC/FAC).
    - Por qué puede variar: La numeración de valuaciones y actas puede seguir la serie propia del ente
    - Destino: TENANT_POLICY de numeración
    - Fuente: NONE
  - **AUTHORITY · LEGAL_MANDATORY:** Solo el supervisor vigente en la fecha puede conformar
    - Evidencia: `resources/backend/app/modules/government/service_contratos_ejecucion.py:182-202` (_conformante).
    - Por qué puede variar: Viene de la supervisión de LCP 137 y RLCP 177; un ente puede admitir una conformación por un inspector suplente
    - Destino: RESPONSIBILITY_BINDING
    - Fuente: LCP art. 137

### CNT-04 · Designación del supervisor del contrato

- **Clasificación:** REFACTOR_HARDCODED_POLICY (sin cambio: los hallazgos de autoridad y flujo siguen abiertos)
- **Prioridad:** P1 (era P0 por el defecto, corregido)
- **Defecto actual:** CURRENT_PRODUCT_DEFECT_BEFORE=YES · CURRENT_PRODUCT_DEFECT_AFTER=NO (CNT-04-EFFECTIVE-TERM-01, 2026-11-16)
- **Motor:** RESPONSIBILITY_BINDING AUTHORITY_BINDING APPROVAL_RULES DOCUMENT_RULES CONTROL_RULES SOD_RULES TENANT_POLICY
- **Resumen:** El funcionario, la ocupación y el acto salen de los datos del ente (ORG y DOC-02), pero la autoridad que designa queda fijada a APROBAR×CONTRATACIONES por decisión de la dueña (OD-CNT04-02). Tiene además un defecto real con contratos prorrogados.
  - **DEADLINE · PLATFORM_INVARIANT:** maximo = contrato.fecha_fin (plazo original) en vez del plazo efectivo CNT-01+CNT-02
    - Evidencia: `resources/backend/app/modules/government/service_contratos_supervision.py:310` (designar (maximo)).
    - Por qué puede variar: Es un defecto, no una política: debe usar terminos_efectivos(db, contrato, desde)["fecha_fin"]
    - Destino: CONTROL_RULES (plazo efectivo común)
    - Fuente: NONE
  - **AUTHORITY · INSTITUTIONAL_POLICY:** El acto de designación debe venir de un cargo con APROBAR×CONTRATACIONES («No se crea la acción DESIGNAR»)
    - Evidencia: `resources/backend/app/modules/government/service_contratos_supervision.py:264, 353, 361` (opciones de actos, designar).
    - Por qué puede variar: La ley (LCP 136-138) solo dice «el contratante»; la competencia es OD-CNT04-02 y otro ente puede tener una competencia DESIGNAR o delegarla en otra dirección
    - Destino: AUTHORITY_BINDING en TENANT_POLICY
    - Fuente: NONE (spec OD-CNT04-02)
  - **WORKFLOW · INSTITUTIONAL_POLICY:** Mínimo: lo más temprano entre el inicio y la formalización, o el «desde» del vigente + timedelta(days=1); motivo obligatorio al sustituir; no se reutiliza el acto
    - Evidencia: `resources/backend/app/modules/government/service_contratos_supervision.py:307-320` (designar).
    - Por qué puede variar: Son decisiones de diseño (FR-08 «decisión de diseño del 2026-11-15»); otro ente puede admitir una sustitución el mismo día
    - Destino: CONTROL_RULES/TENANT_POLICY
    - Fuente: NONE
  - **CATALOG · PLATFORM_INVARIANT:** Etiquetas de tipos de acto (DECRETO…CIRCULAR) duplicadas fuera del catálogo de DOC-02
    - Evidencia: `resources/backend/app/modules/government/service_contratos_supervision.py:33-40` (ETIQUETA_TIPO_ACTO).
    - Por qué puede variar: Si el catálogo de actos del ente cambia, la etiqueta queda desalineada
    - Destino: Leer del catálogo DOC-02
    - Fuente: NONE

### CNT-07 · Terminación, resolución o rescisión

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** PROCESS_DEFINITION PROCESS_VERSION STAGES TRANSITIONS AUTHORITY_BINDING APPROVAL_RULES DOCUMENT_RULES EVIDENCE_RULES CONTROL_RULES SOD_RULES NOTIFICATIONS NORMATIVE_BINDING TENANT_POLICY
- **Resumen:** Las figuras y causales legales (LCP 145, 152, 154 y 155; RLCP 193) son correctas hoy, pero viven en tuplas, CHECK de BD y textos sin fuente, versión ni vigencia en el modelo. Cambiar la norma exige código y migración. Además quedan fijas en código decisiones de diseño o de la dueña: la competencia APROBAR×CONTRATACIONES (D07-03, no viene de la ley), la regla de notificar a garantes (OD-CNT07-03), los límites de motivación y la numeración «/TER».
  - **CATALOG · LEGAL_MANDATORY:** 3 figuras y 12 causales como enum y CHECK de BD, sin SOURCE/VERSION/EFFECTIVE_FROM/EFFECTIVE_TO
    - Evidencia: `resources/backend/app/modules/government/models.py:5520-5521, 5561-5562` (FIGURAS_TERMINACION_CONTRATO, CAUSALES_TERMINACION_CONTRATO (+CheckConstraint figura/causal)).
    - Por qué puede variar: Es LEGAL_MANDATORY, pero una reforma de la LCP o del RLCP (el RLCP 2009 aún cita el art. 127 de la LCP 2009) cambia figuras, causales y numerales. RLCP 193 admite causales «establecidas en el contrato». No debe ser un enum inmutable
    - Destino: NORMATIVE_VERSIONED_CONFIGURATION: catálogo normativo versionado (figura, causal, fuente, vigencia) con NORMATIVE_BINDING; la CHECK se sustituye por una FK al catálogo vigente en la fecha del acto
    - Fuente: LCP art. 145, 152, 154, 155 num. 1-9; RLCP art. 193
  - **CATALOG · LEGAL_MANDATORY:** Mapa figura→causales con etiqueta y cita legal literal; LCP_155_9 restringida a OBRAS en _requisitos
    - Evidencia: `resources/backend/app/modules/government/service_contratos_terminacion.py:73-110` (CATALOGO, RESCISIONES).
    - Por qué puede variar: Duplica el enum de models.py y tiene las citas incrustadas en el código; un cambio de numeración legal obliga a editar dos sitios. Las etiquetas también están duplicadas en situacion_contractual.py ETIQUETA_FIGURA (16-20) y en el frontend (resources/frontend/src/modules/gobierno/contratos/api.ts 294-297)
    - Destino: NORMATIVE_VERSIONED_CONFIGURATION (la misma tabla del hallazgo anterior; el frontend ya consume catalogo.figuras de la vista)
    - Fuente: LCP arts. 152-156; RLCP arts. 190-194
  - **AMOUNT · LEGAL_MANDATORY:** Tramos de indemnización del 10 % al 5 % según avance, solo como texto (no se calculan; CONSECUENCIA_PENDIENTE_CNT06). Saldo no ejecutado = monto vigente − valuado conformado (FINANCIAL_EXECUTION_BASE)
    - Evidencia: `resources/backend/app/modules/government/service_contratos_terminacion.py:111-115, 365-378, 385` (REGLA_INDEMNIZACION; _consecuencias).
    - Por qué puede variar: Los porcentajes y tramos son reglamentarios y cambian con el RLCP. La base del saldo es una interpretación de RLCP 191.a que puede cambiar con la norma o con un criterio de control fiscal. Cuando CNT-06 los calcule, no pueden quedar como literales
    - Destino: NORMATIVE_VERSIONED_CONFIGURATION (tabla de tramos con vigencia; fórmula de saldo como NORMATIVE_BINDING)
    - Fuente: RLCP arts. 191, 194; LCP art. 154
  - **AUTHORITY · INSTITUTIONAL_POLICY:** El acto decisorio y el de apertura deben tener competencia_accion APROBAR y materia CONTRATACIONES, y el cargo emisor debe tenerla en su fecha
    - Evidencia: `resources/backend/app/modules/government/service_contratos_terminacion.py:227-245, 770, 1000-1001` (_acto_valido, _autoridad, formalizar, vista).
    - Por qué puede variar: La ley solo dice «el contratante» o la máxima autoridad (LCP 152 y 155). APROBAR×CONTRATACIONES es una decisión de diseño (spec D07-03). Otro ente puede atribuir la rescisión a otra competencia o materia, o exigir un acto de la máxima autoridad distinto del de las aprobaciones ordinarias. No es LEGAL_MANDATORY
    - Destino: AUTHORITY_BINDING por empresa y proceso (acción, materia, cargo o rol) en TENANT_POLICY
    - Fuente: NONE (spec D07-03; ley: LCP 152, 155)
  - **WORKFLOW · INSTITUTIONAL_POLICY:** Siempre se exige una notificación NOTIFICADA al contratista (por clave de documento). En las rescisiones con garantías vigentes basta «cualquier otra notificación NOTIFICADA»: no se coteja con el emisor de la garantía ni con cesionarios. La rescisión imputable exige un acto de apertura eficaz anterior al decisorio
    - Evidencia: `resources/backend/app/modules/government/service_contratos_terminacion.py:459-497` (_requisitos (NOTIFICACION_CONTRATISTA, NOTIFICACION_GARANTES, APERTURA)).
    - Por qué puede variar: La base es legal (LCP 152: «garantes según corresponda»; LCP 156: «garantes y cesionarios»; LOPA 73-74). La regla concreta «al menos una a otro destinatario» es de la dueña (OD-CNT07-03) y otro ente puede exigir una por garante o por cesionario. La regla del acto de apertura es LEGAL_MANDATORY (LCP 155: sustanciación previa)
    - Destino: NOTIFICATIONS + DOCUMENT_RULES versionados (NORMATIVE_BINDING para la obligación; TENANT_POLICY para el rigor del cotejo)
    - Fuente: LCP arts. 152, 155, 156; RLCP 193; LOPA 73-74
  - **DOCUMENT · OPERATIONAL_CONFIGURATION:** Hechos y fundamento de 20 a 4000 caracteres; alcance de la conclusión de 10 a 1000; referencia de cláusula de hasta 200; el mutuo acuerdo exige un documento con integridad verificada
    - Evidencia: `resources/backend/app/modules/government/service_contratos_terminacion.py:419-431, 499-523, 608` (_requisitos (MOTIVACION, DOCUMENTO_ACUERDO, CONCLUSION), _aplicar).
    - Por qué puede variar: LOPA 9 exige motivar pero no fija longitudes: los umbrales son operativos. El documento del acuerdo deriva de LCP 154 y es LEGAL_MANDATORY
    - Destino: DOCUMENT_RULES/EVIDENCE_RULES del motor; umbrales en TENANT_POLICY
    - Fuente: LOPA art. 9; LCP art. 154
  - **NUMBERING · OPERATIONAL_CONFIGURATION:** Código "{codigo_contrato}/TER", sufijo único para las tres figuras
    - Evidencia: `resources/backend/app/modules/government/service_contratos_terminacion.py:781 (columna String(20) en models.py 5550)` (formalizar codigo).
    - Por qué puede variar: Cada ente numera sus actuaciones (series por figura o por año, prefijos propios). Hoy cabe en 20 caracteres solo porque el código CNT-01 tiene longitud fija
    - Destino: TENANT_POLICY de numeración (serie y plantilla por tipo de documento)
    - Fuente: NONE
  - **DEADLINE · LEGAL_MANDATORY:** Fecha de eficacia = acto.fecha_eficacia (DOC-02/DOC-04, service_contratos_terminacion.py 767-769, 816). El contrato queda EXTINGUIDO si eficacia ≤ fecha. CNT-03/CNT-04 se bloquean si fecha > límite (conclusión autorizada o eficacia). CNT-02 se bloquea si vigente_desde ≥ eficacia
    - Evidencia: `resources/backend/app/modules/government/situacion_contractual.py:35-44, 77-96` (situacion_contractual, fecha_limite, exigir_vigente_en, exigir_vigente_para_modificacion).
    - Por qué puede variar: Es un invariante de dominio derivado de los datos (LOPA 73-74; LCP 152 y 156: paralización desde la notificación), sin literales. No debe pasar a configuración versionada; sí debe exponerse como guarda común (las llamadas están dispersas en service_contratos_ejecucion.py 434, 513, 675, 792, 933, 1133; service_contratos_supervision.py 314; service_contratos_modificaciones.py 1138)
    - Destino: CONTROL_RULES del motor (guarda de vigencia reutilizable)
    - Fuente: LOPA arts. 73-74; LCP arts. 152, 156
  - **INTEGRATION · LEGAL_MANDATORY:** Obligaciones informativas hacia el SNC con textos y citas literales; sin integración
    - Evidencia: `resources/backend/app/modules/government/service_contratos_terminacion.py:962-977` (vista obligaciones (EVALUACION_DESEMPENO_SNC, PUBLICACION_SNC)).
    - Por qué puede variar: La obligación y el organismo destinatario dependen de la ley vigente (LCP 51 y 8); si cambia el canal del SNC hay que tocar código
    - Destino: NORMATIVE_BINDING + NOTIFICATIONS (obligaciones externas versionadas)
    - Fuente: LCP arts. 8, 51
  - **REPORT · OPERATIONAL_CONFIGURATION:** 16 columnas fijas y nombre de archivo fijo; sin identificación del ente
    - Evidencia: `resources/backend/app/modules/government/service_contratos_terminacion.py:902-921, 946` (reporte_csv).
    - Por qué puede variar: Cada órgano de control interno o externo pide su propio formato
    - Destino: TENANT_POLICY de reportes (plantilla de columnas)
    - Fuente: NONE

### CNT-08 · Expediente contractual completo

- **Clasificación:** KEEP_AS_IS
- **Prioridad:** NONE
- **Motor:** NONE
- **Resumen:** No tiene workflow ni reglas variables propias: la numeración, las autoridades y los catálogos que muestra son los de CNT-01/02/07 y se corrigen allí. El código de paquete "EC-AAAA-NNNN" identifica un artefacto técnico de exportación de KONTROL, no un número oficial del ente.
  - **NUMBERING · PLATFORM_INVARIANT:** Código del paquete "EC-{año}-{n:04d}" por empresa
    - Evidencia: `resources/backend/app/modules/government/service_expediente_paquetes.py:95-103` (_siguiente_codigo).
    - Por qué puede variar: Solo variaría si el ente quisiera que el paquete lleve su propia numeración oficial; hoy es un identificador técnico con unicidad por company_id
    - Destino: Ninguno (si se pide, TENANT_POLICY de numeración)
    - Fuente: NONE
  - **REPORT · PLATFORM_INVARIANT:** LEEME y manifiesto con marca «KONTROL», company_id y formato fijo (FORMATO/VERSION_MANIFIESTO, 62-63); sin nombre ni logo del ente
    - Evidencia: `resources/backend/app/modules/government/service_expediente_paquetes.py:297-307, 316-335` (leeme, manifiesto).
    - Por qué puede variar: Es el formato verificable del paquete (DOC-08) y no debe variar por ente; la identidad del ente puede añadirse como dato sin cambiar la regla
    - Destino: Ninguno
    - Fuente: NONE

### CNT-09 · Alertas de vencimientos

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** DEADLINES BUSINESS_CALENDAR NOTIFICATIONS ESCALATIONS TENANT_POLICY
- **Resumen:** El preaviso de contratos, hitos y entregables ya es una política por empresa (gov_contract_alert_policies: company_id, fuente, activo, dias_anticipacion entre 1 y 365, UNIQUE company_id+fuente; models.py 5496-5516). En cambio, el de garantías está fijo en 15 días naturales (DIAS_POR_VENCER de PROC-10, decisión PDD-PROC10-07), y las severidades y las fases por defecto también están en código.
  - **DEADLINE · INSTITUTIONAL_POLICY:** Preaviso de garantías = 15 días naturales, consumido por CNT-09 (service_contratos_alertas.py 22, 375)
    - Evidencia: `resources/backend/app/modules/government/garantias_reglas.py:37-38` (DIAS_POR_VENCER).
    - Por qué puede variar: Es una decisión de diseño (PDD-PROC10-07), no legal; cada ente fija con cuánta antelación gestiona renovaciones de fianzas
    - Destino: TENANT_POLICY: añadir la fuente GARANTIA a gov_contract_alert_policies
    - Fuente: NONE
  - **DEADLINE · OPERATIONAL_CONFIGURATION:** Días naturales, sin calendario hábil; UPCOMING solo entre 1 y N días
    - Evidencia: `resources/backend/app/modules/government/service_contratos_alertas.py:66-73` (fase).
    - Por qué puede variar: Un ente puede querer el preaviso en días hábiles según su calendario
    - Destino: BUSINESS_CALENDAR + DEADLINES
    - Fuente: NONE
  - **WORKFLOW · OPERATIONAL_CONFIGURATION:** Severidades por fase (INFO, WARNING, CRITICAL) y filtro por defecto DUE_TODAY y OVERDUE
    - Evidencia: `resources/backend/app/modules/government/service_contratos_alertas.py:62-63, 375` (SEVERIDAD, SEVERIDAD_GARANTIA, fases_por_defecto).
    - Por qué puede variar: La criticidad y la escalada son ajustes operativos del ente
    - Destino: ESCALATIONS/NOTIFICATIONS en TENANT_POLICY
    - Fuente: NONE
  - **CATALOG · PLATFORM_INVARIANT:** Fuentes CONTRATO, HITO y ENTREGABLE; tope de 1 a 365 días (también en schemas_contratos_alertas.py 9 y en el frontend AlertasPoliticaPage.tsx 188)
    - Evidencia: `resources/backend/app/modules/government/models.py:5496, 5506-5507` (FUENTES_POLITICA_ALERTA; CheckConstraint dias).
    - Por qué puede variar: El rango de 365 días es un ajuste operativo; las fuentes son módulos de la plataforma
    - Destino: TENANT_POLICY (rango)
    - Fuente: NONE
  - **WORKFLOW · LEGAL_MANDATORY:** Un contrato EXTINGUIDO a la fecha de la corrida deja de generar alertas, también los hitos y entregables, aunque exista una conclusión autorizada hasta una fecha posterior (C07-19)
    - Evidencia: `resources/backend/app/modules/government/service_contratos_alertas.py:130-133` (condiciones).
    - Por qué puede variar: Con conclusión autorizada (LCP 152 y 156) siguen corriendo plazos de la parte autorizada; si un ente quiere alertas sobre ella, hoy no puede
    - Destino: CONTROL_RULES (usar fecha_limite_ejecucion)
    - Fuente: LCP arts. 152, 156

### TRE-01 · Cuentas bancarias públicas con autorizados y acto habilitante

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** APPROVAL_RULES AUTHORITY_BINDING DOCUMENT_RULES CONTROL_RULES TENANT_POLICY
- **Resumen:** El catálogo de bancos es por ente (gov_banks, sin códigos precargados), los autorizados son cargos ORG-03 con acto y el SoD pasa por evaluar_antes_de_actuar. Los tipos de cuenta (cerrados por "decisión de producto"), las monedas, el formato de 20 dígitos y la numeración CB-AAAA-NNNN están en código. No hay modelo de firma mancomunada (régimen de firmas, mínimo de firmantes, clases A/B).
  - **CATALOG · INSTITUTIONAL_POLICY:** ("CORRIENTE","AHORRO") como lista cerrada; la Spec OD-TRE01-05 dice "decisión de producto y no norma"
    - Evidencia: `resources/backend/app/modules/government/models.py:1685,1757 (schemas_cuentas.py:10)` (TIPOS_CUENTA_BANCARIA (+ schemas_cuentas.TipoCuenta)).
    - Por qué puede variar: hay entes que manejan cuentas recaudadoras, de fideicomiso, de fondos de terceros o en divisas especiales
    - Destino: TENANT_CONFIGURABLE_CATALOG
    - Fuente: NONE
  - **CATALOG · OPERATIONAL_CONFIGURATION:** ("VES","USD","EUR")
    - Evidencia: `resources/backend/app/modules/government/models.py:195,1758 (schemas_cuentas.py:11)` (MONEDAS_LIMITE (+ schemas_cuentas.MonedaCuenta)).
    - Por qué puede variar: se pueden abrir cuentas en otras divisas que el BCV cotiza
    - Destino: catálogo de monedas habilitadas por tenant
    - Fuente: NONE
  - **CATALOG · LEGAL_MANDATORY:** código de banco de 4 dígitos y número de 20 dígitos que empieza por el código del banco, como CHECK y literal
    - Evidencia: `resources/backend/app/modules/government/service_cuentas.py:50-59 (y models.py:1759)` (_validar_codigo_banco / _validar_numero).
    - Por qué puede variar: es el estándar nacional de código cuenta cliente, pero vive sin fuente ni versión
    - Destino: NORMATIVE_BINDING del formato de cuenta
    - Fuente: NONE
  - **AUTHORITY · INSTITUTIONAL_POLICY:** un autorizado es un cargo sin rol ni clase de firma; para activar basta 1 autorizado en vigor; no hay régimen de firma conjunta o mancomunada ni mínimo configurable
    - Evidencia: `resources/backend/app/modules/government/service_cuentas.py:379,1112-1158` (autorizar / _faltantes).
    - Por qué puede variar: cada ente define firmas conjuntas (p. ej. alcalde + tesorero) y cuántas se requieren
    - Destino: APPROVAL_RULES / AUTHORITY_BINDING (régimen de firmas por cuenta)
    - Fuente: NONE
  - **AUTHORITY · INSTITUTIONAL_POLICY:** cualquier cargo VIGENTE de la estructura de hoy.year es autorizable; no se exige ninguna competencia
    - Evidencia: `resources/backend/app/modules/government/service_cuentas.py:172-197` (_condiciones_cargo / _cargo_autorizable).
    - Por qué puede variar: el ente puede exigir una competencia de firma bancaria o de pago
    - Destino: AUTHORITY_BINDING
    - Fuente: NONE
  - **DOCUMENT · INSTITUTIONAL_POLICY:** activar la cuenta y dar de alta cada autorizado exigen un acto DOC-02 EMITIDO o EFICAZ (cualquier tipo)
    - Evidencia: `resources/backend/app/modules/government/service_cuentas.py:156-169,374-386,1129` (_faltantes / _acto_con_efecto / autorizar).
    - Por qué puede variar: el tipo de acto habilitante (resolución, decreto, acuerdo) lo define la norma interna
    - Destino: DOCUMENT_RULES con tipo de acto requerido
    - Fuente: NONE
  - **NUMBERING · INSTITUTIONAL_POLICY:** f"CB-{hoy.year}-{n:04d}"
    - Evidencia: `resources/backend/app/modules/government/service_cuentas.py:330-340` (_siguiente_codigo).
    - Por qué puede variar: el formato es institucional
    - Destino: TENANT_POLICY de series
    - Fuente: NONE

### TRE-02 · Programación financiera y disponibilidad de caja

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** PROCESS_VERSION APPROVAL_RULES BUSINESS_CALENDAR DEADLINES NORMATIVE_BINDING TENANT_POLICY
- **Resumen:** Rubros y programas son datos por ente, con versionado y reprogramación, y el SoD pasa por evaluar_antes_de_actuar. La periodicidad es mensual fija (1..12) aunque la propia Spec cita que los subperíodos los determina la Oficina Nacional del Tesoro. La activación no tiene aprobador ni acto, y el código PF y las monedas son literales.
  - **DEADLINE · LEGAL_MANDATORY:** subperíodo = mes calendario, con mes_inicial de 1 a 12 y range(mes_inicial, 13)
    - Evidencia: `resources/backend/app/modules/government/service_caja.py:232-247,594 (models.py:1924; schemas_caja.py mes Field(ge=1, le=12))` (detalle / _validar_mes).
    - Por qué puede variar: según el Reglamento N.º 3 de la LOAFSP art. 63, los subperíodos los determina la ONT (podrían ser quincenas o trimestres); los municipios tienen otro régimen
    - Destino: BUSINESS_CALENDAR con subperíodos configurables + NORMATIVE_BINDING
    - Fuente: Reglamento N.º 3 LOAFSP arts. 61, 63 (spec gov-tre-02 línea 14)
  - **WORKFLOW · INSTITUTIONAL_POLICY:** Tesorería activa y reprograma solo con MFA, sin aprobador interno ni acto (OD-TRE02-04)
    - Evidencia: `resources/backend/app/modules/government/service_caja.py:933-1006` (activar / reprogramar).
    - Por qué puede variar: el art. 64 asigna la aprobación de cuotas y reprogramaciones a un órgano externo; un ente puede exigir aprobación de la máxima autoridad o un acto
    - Destino: APPROVAL_RULES + DOCUMENT_RULES
    - Fuente: Reglamento N.º 3 LOAFSP art. 64
  - **DEADLINE · OPERATIONAL_CONFIGURATION:** el ejercicio debe ser ≥ año actual − 1
    - Evidencia: `resources/backend/app/modules/government/service_caja.py:764` (crear).
    - Por qué puede variar: política de ventana
    - Destino: TENANT_POLICY
    - Fuente: NONE
  - **NUMBERING · INSTITUTIONAL_POLICY:** codigo = f"PF-{ejercicio}-{moneda}"
    - Evidencia: `resources/backend/app/modules/government/service_caja.py:767` (crear).
    - Por qué puede variar: el formato es institucional
    - Destino: TENANT_POLICY de series
    - Fuente: NONE
  - **CATALOG · OPERATIONAL_CONFIGURATION:** Literal["VES","USD","EUR"]
    - Evidencia: `resources/backend/app/modules/government/schemas_caja.py:11 (models.py:195 MONEDAS_LIMITE)` (MonedaPrograma).
    - Por qué puede variar: depende de las divisas que maneje el ente
    - Destino: catálogo de monedas por tenant
    - Fuente: NONE
  - **CATALOG · PLATFORM_INVARIANT:** ("INGRESO","DESEMBOLSO")
    - Evidencia: `resources/backend/app/modules/government/models.py:1829` (TIPOS_RUBRO_CAJA).
    - Por qué puede variar: no varía; los rubros concretos son datos del tenant (gov_cash_items por company_id)
    - Destino: NONE
    - Fuente: NONE

### TRE-09 · Provenance de tasas BCV

- **Clasificación:** ADAPT_TO_PROCESS_ENGINE
- **Prioridad:** P2
- **Motor:** APPROVAL_RULES EVIDENCE_RULES SOD_RULES NORMATIVE_BINDING
- **Resumen:** No hay acoplamiento técnico al BCV: no hay URL, scraping ni HTTP; la captura es manual, con evidencia documental y maker-checker, por company_id. La fuente "BCV", la cotización en VES y las monedas USD/EUR son CHECK y Literal sin versión. La tasa aplicable no tiene antigüedad máxima.
  - **INTEGRATION · LEGAL_MANDATORY:** fuente = 'BCV' y moneda_cotizacion = 'VES' como CHECK y literal; hay captura manual y no hay ninguna URL del BCV
    - Evidencia: `resources/backend/app/modules/government/models.py:1633-1634 (service_tasas.py:190-193,256-259)` (GovernmentOfficialExchangeRate CHECK fuente/cotizacion).
    - Por qué puede variar: la fuente oficial la fija la norma cambiaria vigente (N39); hoy es correcta pero no tiene fuente ni vigencia en el modelo
    - Destino: NORMATIVE_BINDING (fuente oficial con vigencia)
    - Fuente: N39 (spec gov-tre-09 línea 5)
  - **CATALOG · LEGAL_MANDATORY:** ("USD","EUR")
    - Evidencia: `resources/backend/app/modules/government/models.py:1599,1632 (schemas_tasas.py:15)` (MONEDAS_TASA (+ schemas_tasas Literal)).
    - Por qué puede variar: el BCV publica más divisas oficiales (p. ej. CNY, TRY, RUB) y la lista cambia
    - Destino: LEGAL_VERSIONED_CATALOG de monedas cotizables
    - Fuente: NONE
  - **CONTROL · OPERATIONAL_CONFIGURATION:** usa la APROBADA con la mayor fecha_efectiva ≤ fecha, sin límite de antigüedad
    - Evidencia: `resources/backend/app/modules/government/service_tasas.py:446-473` (tasa_aplicable).
    - Por qué puede variar: un ente puede exigir una tasa del día hábil o con antigüedad máxima de N días
    - Destino: CONTROL_RULES (antigüedad máxima) + BUSINESS_CALENDAR
    - Fuente: N39 (T09-10)
  - **WORKFLOW · PLATFORM_INVARIANT:** maker-checker "quien captura no aprueba" y evidencia documental obligatoria
    - Evidencia: `resources/backend/app/modules/government/service_tasas.py:336-347` (aprobar).
    - Por qué puede variar: - (control de integridad)
    - Destino: SOD_RULES / EVIDENCE_RULES del motor común
    - Fuente: NONE
  - **CATALOG · PLATFORM_INVARIANT:** VED→VES
    - Evidencia: `resources/backend/app/modules/government/monedas.py:9,21-22` (canonical_currency).
    - Por qué puede variar: -
    - Destino: NONE
    - Fuente: NONE

### DOC-02 · Actos administrativos con autoridad, motivación y eficacia

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** PROCESS_DEFINITION PROCESS_VERSION STAGES TRANSITIONS AUTHORITY_BINDING DOCUMENT_RULES EVIDENCE_RULES SOD_RULES DEADLINES BUSINESS_CALENDAR NORMATIVE_BINDING TENANT_POLICY
- **Resumen:** La autoridad se deriva bien de las competencias vigentes del cargo (ORG-03/ORG-06), y el número y el lugar los teclea el usuario. Pero el catálogo de materias de competencia es cerrado (6 valores), y los catálogos LOPA, los requisitos de motivación, los medios de eficacia y el plazo de prensa son constantes sin versión.
  - **AUTHORITY · INSTITUTIONAL_POLICY:** Un acto solo puede fundarse en 10 acciones × 6 materias (PRESUPUESTO, CONTRATACIONES, TESORERIA, CONTABILIDAD, BIENES, EXPEDIENTE); se repite como Literal en schemas_cargos.py:16-17
    - Evidencia: `resources/backend/app/modules/government/models.py:192-193, 306-307` (ACCIONES_COMPETENCIA, MATERIAS_COMPETENCIA, CheckConstraint competencia_accion/competencia_materia).
    - Por qué puede variar: Una alcaldía o gobernación dicta actos en RRHH, urbanismo, hacienda, servicios, etc.; esos actos no tienen competencia que se pueda registrar
    - Destino: TENANT_CONFIGURABLE_CATALOG de materias y acciones por company_id, ligado a AUTHORITY_BINDING
    - Fuente: NONE
  - **CATALOG · LEGAL_MANDATORY:** Tipos de acto (jerarquía LOPA), titularidad, carácter y medios como tuplas más CHECK, sin SOURCE/VERSION/EFFECTIVE_FROM; duplicados en schemas_actos.py:14-19
    - Evidencia: `resources/backend/app/modules/government/models.py:196-199` (TIPOS_ACTO_ADMINISTRATIVO, TITULARIDADES, CARACTERES_ACTO, MEDIOS_EFICACIA).
    - Por qué puede variar: Si cambia la norma o una ordenanza local fija formas propias (p. ej. "acuerdo"), hay que cambiar el código y migrar
    - Destino: LEGAL_VERSIONED_CATALOG con NORMATIVE_BINDING
    - Fuente: LOPA arts. 14, 17, 72-76
  - **DOCUMENT · LEGAL_MANDATORY:** Requisitos para emitir: documento, hechos y fundamentos (salvo simple trámite), decisión, destinatario si es PARTICULAR, y autoridad
    - Evidencia: `resources/backend/app/modules/government/service_actos.py:43-50, 297-320` (ORDEN_FALTANTES_ACTO, faltantes_para_emitir).
    - Por qué puede variar: Son requisitos legales de motivación y contenido; deberían vivir en reglas documentales versionadas, no en el servicio
    - Destino: DOCUMENT_RULES con NORMATIVE_BINDING
    - Fuente: LOPA arts. 9, 18
  - **WORKFLOW · LEGAL_MANDATORY:** GENERAL solo admite GACETA; PARTICULAR se desvía a DOC-04; GACETA/PRENSA exigen referencia
    - Evidencia: `resources/backend/app/modules/government/service_actos.py:1100-1120` (registrar_eficacia (reglas de medio)).
    - Por qué puede variar: Regla legal fija en el servicio; el medio oficial (Gaceta Municipal o Estadal) depende del ente
    - Destino: TRANSITIONS + EVIDENCE_RULES por PROCESS_VERSION
    - Fuente: LOPA art. 72
  - **DEADLINE · LEGAL_MANDATORY:** Eficacia por prensa = publicación + 15 días corridos
    - Evidencia: `resources/backend/app/modules/government/service_actos.py:1137-1138` (timedelta(days=15)).
    - Por qué puede variar: Plazo legal sin versión; no se cuenta con un calendario hábil y la Spec no decide si son días corridos o hábiles (posible discusión con LOPA art. 42)
    - Destino: DEADLINES + BUSINESS_CALENDAR
    - Fuente: LOPA art. 76
  - **WORKFLOW · PLATFORM_INVARIANT:** Puntos de control SoD cableados por acción (las reglas son configurables en CTL-01)
    - Evidencia: `resources/backend/app/modules/government/service_actos.py:537, 1034, 1152, 1224, 1317` (evaluar_antes_de_actuar("DOC02_*")).
    - Por qué puede variar: Solo cambia la lista de acciones controlables al adoptar un motor
    - Destino: SOD_RULES
    - Fuente: NONE

### DOC-04 · Notificaciones administrativas con constancia de recepción

- **Clasificación:** ADAPT_TO_PROCESS_ENGINE
- **Prioridad:** P2
- **Motor:** STAGES TRANSITIONS EVIDENCE_RULES DOCUMENT_RULES DEADLINES BUSINESS_CALENDAR NOTIFICATIONS NORMATIVE_BINDING
- **Resumen:** Los destinatarios, los recursos y las constancias son datos por company_id. Los canales, la secuencia "personal fallida → prensa" y el plazo de 15 días son reglas LOPA fijas en el servicio y en el frontend, sin versión normativa.
  - **CATALOG · LEGAL_MANDATORY:** Solo los canales PERSONAL y PRENSA, con CHECK; el canal electrónico queda excluido (OD-DOC04-01); duplicados en schemas_notificaciones.py:15-18
    - Evidencia: `resources/backend/app/modules/government/models.py:201-204` (ESTADOS_NOTIFICACION, MEDIOS_NOTIFICACION, RESULTADOS_INTENTO, TIPOS_PERSONA).
    - Por qué puede variar: Una reforma o la habilitación de la notificación electrónica exige cambiar el código
    - Destino: LEGAL_VERSIONED_CATALOG de medios con NORMATIVE_BINDING
    - Fuente: LOPA arts. 75-76
  - **WORKFLOW · LEGAL_MANDATORY:** La prensa exige al menos un intento PERSONAL FALLIDO previo
    - Evidencia: `resources/backend/app/modules/government/service_notificaciones.py:864-882` (registrar_intento (GOV_NOTIFICATION_PRESS_REQUIRES_FAILED_ATTEMPT)).
    - Por qué puede variar: Transición legal fija en el servicio
    - Destino: TRANSITIONS por PROCESS_VERSION
    - Fuente: LOPA art. 76
  - **DEADLINE · LEGAL_MANDATORY:** Notificada = publicación + 15 días corridos; se repite en el frontend como DIAS_PRENSA=15 (resources/frontend/src/modules/gobierno/api.ts:736)
    - Evidencia: `resources/backend/app/modules/government/service_notificaciones.py:912-915` (timedelta(days=15)).
    - Por qué puede variar: Plazo legal sin versión y sin calendario hábil
    - Destino: DEADLINES + BUSINESS_CALENDAR
    - Fuente: LOPA art. 76
  - **WORKFLOW · LEGAL_MANDATORY:** El acto pasa a EFICAZ cuando todos los destinatarios están notificados; se toma la fecha más tardía
    - Evidencia: `resources/backend/app/modules/government/service_notificaciones.py:542-565` (propagación de eficacia al acto).
    - Por qué puede variar: Regla de dominio entre procesos (DOC-04 → DOC-02) que conviene expresar como transición del motor
    - Destino: TRANSITIONS
    - Fuente: LOPA arts. 73-74
  - **REPORT · OPERATIONAL_CONFIGURATION:** 9 columnas fijas, sin encabezado del ente
    - Evidencia: `resources/backend/app/modules/government/service_notificaciones.py:696-707` (exportar CSV).
    - Por qué puede variar: Formato de salida
    - Destino: TENANT_POLICY de reportes
    - Fuente: NONE

### DOC-08 · Paquete de auditoría exportable

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** EVIDENCE_RULES TENANT_POLICY
- **Resumen:** El manifiesto, el hash y los límites anti-zip-bomb son invariantes de plataforma. Los topes de contenido del paquete y la numeración PA-AAAA-NNNN están fijos en el código.
  - **AMOUNT · OPERATIONAL_CONFIGURATION:** 500 eventos, 200 documentos y 250 MB por paquete
    - Evidencia: `resources/backend/app/modules/government/service_paquetes.py:60-62, 308-314` (MAX_EVENTOS, MAX_DOCUMENTOS, MAX_BYTES).
    - Por qué puede variar: Un ente grande o un auditor externo puede necesitar paquetes mayores; es un ajuste operativo
    - Destino: TENANT_POLICY (límites de exportación por company_id)
    - Fuente: NONE
  - **NUMBERING · INSTITUTIONAL_POLICY:** Prefijo "PA-{año}-" y correlativo de 4 dígitos
    - Evidencia: `resources/backend/app/modules/government/service_paquetes.py:752-761` (_siguiente_codigo).
    - Por qué puede variar: Cada ente tiene sus propias series de correspondencia o archivo
    - Destino: TENANT_POLICY de series de numeración
    - Fuente: NONE
  - **REPORT · PLATFORM_INVARIANT:** Formato del manifiesto y límites de seguridad de la verificación
    - Evidencia: `resources/backend/app/modules/government/service_paquetes.py:56-59, 63-66` (FORMATO, VERSION_MANIFIESTO, ALGORITMO_HASH, MAX_SUBIDA, MAX_ENTRADAS, MAX_DESCOMPRIMIDO, MAX_RAZON).
    - Por qué puede variar: No varían (seguridad e integridad)
    - Destino: Ninguno
    - Fuente: NONE
  - **REPORT · OPERATIONAL_CONFIGURATION:** Columnas del índice (ruta, tipo, referencia, descripcion, bytes, sha256)
    - Evidencia: `resources/backend/app/modules/government/service_paquetes.py:661-662` (INDICE.csv).
    - Por qué puede variar: Formato menor; aceptable como invariante del formato versionado
    - Destino: Ninguno (opcional TENANT_POLICY)
    - Fuente: NONE

### CTL-01 · Matriz SoD por proceso y detección previa

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** SOD_RULES CONTROL_RULES EXCEPTIONS PROCESS_DEFINITION TENANT_POLICY
- **Resumen:** Los pares incompatibles son configurables por company_id (gov_sod_rules, con vigencia e historia). Pero el universo de procesos y acciones controlables, el alcance y el modo están fijos en el código, y BUD-08 aplica un par SoD cableado fuera de la matriz.
  - **CATALOG · PLATFORM_INVARIANT:** Catálogo cerrado de acciones controlables por proceso
    - Evidencia: `resources/backend/app/modules/government/service_sod.py:24-157` (CATALOGO_SOD).
    - Por qué puede variar: Está ligado a los puntos de control del código; debería registrarlo cada proceso en el motor
    - Destino: SOD_RULES + PROCESS_DEFINITION (acciones declaradas por proceso)
    - Fuente: NONE
  - **CATALOG · INSTITUTIONAL_POLICY:** Solo 9 procesos admiten reglas (DOC-02, CTL-06, TRE-01, TRE-02, CTL-10, ORG-04, ORG-06, PROC-02, PROC-03); BUD-06/08 y CNT-* quedan fuera
    - Evidencia: `resources/backend/app/modules/government/models.py:846` (PROCESOS_SOD).
    - Por qué puede variar: Otra institución necesitará segregar otros procesos que ya existen (presupuesto, contratos)
    - Destino: SOD_RULES sobre PROCESS_DEFINITION
    - Fuente: NONE
  - **WORKFLOW · INSTITUTIONAL_POLICY:** Alcance único MISMO_OBJETO y modo único BLOQUEAR, sin excepción ni override (OD-CTL01-01/02); también service_sod.py:432 modo="BLOQUEAR"
    - Evidencia: `resources/backend/app/modules/government/models.py:844-845` (ALCANCES_REGLA_SOD, MODOS_REGLA_SOD).
    - Por qué puede variar: Es una decisión de la dueña, no una norma (la Spec dice que N20/N23 no prescriben pares); otra institución puede requerir alcance por expediente o ejercicio, o excepciones autorizadas
    - Destino: SOD_RULES + EXCEPTIONS + TENANT_POLICY
    - Fuente: NONE
  - **AUTHORITY · INSTITUTIONAL_POLICY:** Par SoD certificar/comprometer cableado en el servicio BUD-08, fuera de la matriz CTL-01 y no configurable
    - Evidencia: `resources/backend/app/modules/government/service_presupuesto_compromiso.py:584-608` (regla "Quien certifica no compromete").
    - Por qué puede variar: El par lo debería definir Control Interno en la matriz; otra institución puede querer otros pares o ninguno
    - Destino: SOD_RULES (regla semilla por defecto en TENANT_POLICY)
    - Fuente: NONE
  - **CATALOG · INSTITUTIONAL_POLICY:** Funciones SoD de procedimiento (SOLICITANTE, RECEPTOR, EVALUADOR, ADJUDICADOR) fijas y solo para PROC-03; también models.py:925
    - Evidencia: `resources/backend/app/modules/government/service_sod_funciones.py:44-81` (FUNCIONES, PROCESO).
    - Por qué puede variar: Otras funciones o procesos según el ente
    - Destino: SOD_RULES + RESPONSIBILITY_BINDING
    - Fuente: NONE
  - **NUMBERING · INSTITUTIONAL_POLICY:** Prefijo "SOD-{año}-NNNN"
    - Evidencia: `resources/backend/app/modules/government/service_sod.py:403-415` (_siguiente_codigo).
    - Por qué puede variar: Series propias del ente
    - Destino: TENANT_POLICY de numeración
    - Fuente: NONE

### CTL-02 · Bitácora institucional append-only con actor, autoridad, unidad y correlación

- **Clasificación:** KEEP_AS_IS
- **Prioridad:** NONE (era P1 por el defecto, corregido)
- **Motor:** NONE
- **Resumen:** Consulta append-only sin reglas institucionales. Lo único que había que corregir era el mapa de procesos compartido con CTL-04.
- **Estado tras CTL-02-AUDIT-PROCESS-RESOLUTION (2026-11-19):** CURRENT_PRODUCT_DEFECT=NO. El proceso y el módulo de cada evento salen de la autoridad única `app/modules/government/procesos.py` (metadata `owner_spec` del catálogo de eventos), que también consumen CTL-04, CTL-05, CTL-07 y REP-10. Una guardia (`test_ctl02_p05_*`) falla ante un evento de Gobierno sin proceso registrado.
  - **CATALOG · PLATFORM_INVARIANT:** Acciones de autenticación y clases de resultado
    - Evidencia: `resources/backend/app/modules/government/service_bitacora.py:30-50` (ACCIONES_AUTENTICACION, RESULTADOS).
    - Por qué puede variar: No varían (seguridad)
    - Destino: Ninguno
    - Fuente: NONE
  - **CATALOG · PLATFORM_INVARIANT:** ~~Depende de PROCESOS de service_auditoria (incompleto)~~. Resuelto: registro único de procesos con guardia
    - Evidencia: `resources/backend/app/modules/government/procesos.py` (PROCESOS, resolver_proceso).
    - Por qué puede variar: crece con cada proceso; la guardia exige registrarlo
    - Destino: PROCESS_DEFINITION (registro único, ya en uso)
    - Fuente: NONE

### CTL-03 · Administrador técnico sin autoridad funcional

- **Clasificación:** KEEP_AS_IS
- **Prioridad:** NONE
- **Motor:** NONE
- **Resumen:** Muestra si los administradores técnicos tienen permisos funcionales y autoridad institucional, con datos de cada ente. Por defecto, la separación efectiva depende de que el ente active exige_identidad.
  - **CONTROL · OPERATIONAL_CONFIGURATION:** sin política, «basta el permiso funcional y el acto competente»: un admin técnico con rol funcional actúa sin cargo
    - Evidencia: `resources/backend/app/modules/government/service_separacion.py:97-111` (_exigencia).
    - Por qué puede variar: configurable por ente; solo el valor por defecto (desactivado) es una decisión
    - Destino: TENANT_POLICY con valor por defecto del perfil de Gobierno
    - Fuente: OD-ORG06-09
  - **REPORT · OPERATIONAL_CONFIGURATION:** últimos 500 eventos y 50 denegaciones; el encabezado usa company.legal_name y no GovernmentEntity.denominacion
    - Evidencia: `resources/backend/app/modules/government/service_separacion.py:356, 376, 417` (_denegaciones, separacion).
    - Por qué puede variar: ventana de consulta y rótulo institucional
    - Destino: parámetros de reporte; usar la denominación del ente
    - Fuente: NONE

### CTL-04 · Consulta y muestreo read-only del auditor

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** PROCESS_DEFINITION EVIDENCE_RULES TENANT_POLICY
- **Resumen:** El muestreo es reproducible con semilla y read-only. Los tamaños máximos de población y de muestra y la numeración MU- están fijos en el código.
- **Estado tras CTL-02-AUDIT-PROCESS-RESOLUTION (2026-11-19):** CURRENT_PRODUCT_DEFECT=NO (OD-PR-01). El filtro y el catálogo de procesos consumen la autoridad única `app/modules/government/procesos.py`. Sigue en P1 por los límites de muestreo y la numeración.
  - **AMOUNT · OPERATIONAL_CONFIGURATION:** Población máxima de 2000 para TODAS; muestra aleatoria y específica de 1 a 500 (también en schemas_auditoria.py:124-125)
    - Evidencia: `resources/backend/app/modules/government/service_auditoria.py:610-616, 630-636` (registrar muestra (TODAS/ALEATORIA)).
    - Por qué puede variar: La metodología de auditoría (tamaño por riesgo o nivel de confianza) y el volumen del ente varían
    - Destino: TENANT_POLICY (límites de muestreo) + CONTROL_RULES
    - Fuente: NONE
  - **CATALOG · LEGAL_MANDATORY:** TODAS, ESPECIFICA, ALEATORIA
    - Evidencia: `resources/backend/app/modules/government/models.py:205` (METODOS_MUESTREO).
    - Por qué puede variar: Otros métodos (estratificado, por monto)
    - Destino: TENANT_CONFIGURABLE_CATALOG
    - Fuente: NONE
  - **CATALOG · PLATFORM_INVARIANT:** ~~Lista manual de procesos y owner_spec, desfasada respecto del catálogo de auditoría~~. Resuelto en CTL-02-AUDIT-PROCESS-RESOLUTION
    - Evidencia: `resources/backend/app/modules/government/procesos.py` (PROCESOS, es_proceso, owner_specs_de).
    - Por qué puede variar: crece con cada proceso; la guardia exige registrarlo
    - Destino: PROCESS_DEFINITION (registro único, ya en uso)
    - Fuente: NONE
  - **NUMBERING · INSTITUTIONAL_POLICY:** Prefijo "MU-{año}-NNNN"
    - Evidencia: `resources/backend/app/modules/government/service_auditoria.py:644-655` (código de muestra).
    - Por qué puede variar: Series propias del ente o de la UAI
    - Destino: TENANT_POLICY de numeración
    - Fuente: NONE

### CTL-05 · Expediente de cuenta y reportes de rendición

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** STAGES TRANSITIONS DEADLINES SOD_RULES EVIDENCE_RULES NORMATIVE_BINDING TENANT_POLICY
- **Resumen:** El responsable se deriva de ORG-04 y las piezas de la bitácora. El ciclo de estados N21, el plazo de 90 días, la numeración CTA- y el formato del informe están fijos en el código.
  - **WORKFLOW · LEGAL_MANDATORY:** EN_FORMACION→FORMADA→PARTICIPADA→CALIFICADA→FENECIDA/SUSTITUIDA, también como CHECK en models.py
    - Evidencia: `resources/backend/app/modules/government/service_rendicion.py:57, 810-818, 845-888` (ESTADOS, _participar, _calificar, _fenecer).
    - Por qué puede variar: Ciclo de la Res. CGR, sin versión normativa
    - Destino: STAGES + TRANSITIONS por PROCESS_VERSION
    - Fuente: Res. CGR 01-00-000167 (N21) arts. 12-16, 33
  - **DEADLINE · LEGAL_MANDATORY:** Vencimiento de la participación = periodo_hasta + 90 días continuos (en la línea 818 la variable _vence se calcula y no se usa)
    - Evidencia: `resources/backend/app/modules/government/service_rendicion.py:818, 1021` (timedelta(days=90)).
    - Por qué puede variar: Plazo legal sin versión ni vigencia
    - Destino: DEADLINES + NORMATIVE_BINDING
    - Fuente: N21 art. 13
  - **AUTHORITY · INSTITUTIONAL_POLICY:** Quien formó la cuenta o el cuentadante no registran la calificación (par SoD cableado, fuera de CTL-01)
    - Evidencia: `resources/backend/app/modules/government/service_rendicion.py:836-842` (_verificar_actor_calificacion).
    - Por qué puede variar: Es SoD institucional y debería ser configurable
    - Destino: SOD_RULES
    - Fuente: NONE
  - **NUMBERING · INSTITUTIONAL_POLICY:** Prefijo "CTA-{año}-"
    - Evidencia: `resources/backend/app/modules/government/service_rendicion.py:199-200` (_siguiente_codigo).
    - Por qué puede variar: Series propias del ente
    - Destino: TENANT_POLICY de numeración
    - Fuente: NONE
  - **REPORT · OPERATIONAL_CONFIGURATION:** Título = código del expediente, columnas fijas, sin membrete ni logo del ente en la cabecera
    - Evidencia: `resources/backend/app/modules/government/service_rendicion.py:627, 635, 1115` (_pdf_desde_snapshot, CSV).
    - Por qué puede variar: Cada ente presenta su cuenta con su identidad institucional y el formato que pida su órgano de control
    - Destino: TENANT_POLICY de plantilla de reportes
    - Fuente: NONE

### CTL-06 · Hallazgos y planes de acción correctiva

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** STAGES TRANSITIONS APPROVAL_RULES SOD_RULES EVIDENCE_RULES DEADLINES ESCALATIONS TENANT_POLICY
- **Resumen:** Los plazos de las acciones los fija el usuario (fecha_objetivo), así que no hay plazo cableado. La escala de riesgo, el ciclo de cinco estados, la regla de vencimiento y la numeración HA- están fijos.
  - **CATALOG · INSTITUTIONAL_POLICY:** Escala ALTO/MEDIO/BAJO y origen MUESTRA/INDEPENDIENTE (también Literal en schemas_hallazgos.py:30-31)
    - Evidencia: `resources/backend/app/modules/government/models.py:556-557` (RIESGOS_HALLAZGO, ORIGENES_HALLAZGO).
    - Por qué puede variar: Las metodologías de riesgo de cada UAI difieren (4-5 niveles, "crítico")
    - Destino: TENANT_CONFIGURABLE_CATALOG
    - Fuente: NONE
  - **WORKFLOW · INSTITUTIONAL_POLICY:** ABIERTO→PLAN_DE_ACCION→EN_REMEDIACION→EVIDENCIA_PRESENTADA→CERRADO, con devolución; también models.py:558
    - Evidencia: `resources/backend/app/modules/government/service_hallazgos.py:43-47, 838-870, 1015-1030` (ESTADO_* y transiciones).
    - Por qué puede variar: Algunas instituciones exigen aprobar el plan por la máxima autoridad o hacer un seguimiento intermedio
    - Destino: STAGES + TRANSITIONS + APPROVAL_RULES
    - Fuente: NONE
  - **DOCUMENT · INSTITUTIONAL_POLICY:** Cada recomendación exige al menos una acción correctiva
    - Evidencia: `resources/backend/app/modules/government/service_hallazgos.py:815-836` (registrar_plan (GOV_FINDING_PLAN_INCOMPLETE)).
    - Por qué puede variar: Regla de completitud de la política del ente
    - Destino: CONTROL_RULES
    - Fuente: NONE
  - **DEADLINE · OPERATIONAL_CONFIGURATION:** Vencida = fecha_objetivo < hoy y no COMPLETADA, sin margen ni días hábiles ni escalamiento
    - Evidencia: `resources/backend/app/modules/government/service_hallazgos.py:137-139` (_accion_vencida (R14)).
    - Por qué puede variar: Margen, preaviso y escalamiento son política
    - Destino: DEADLINES + ESCALATIONS + BUSINESS_CALENDAR
    - Fuente: NONE
  - **AUTHORITY · INSTITUTIONAL_POLICY:** Quien presentó o registró avances no verifica (SoD cableada, además de CTL-01)
    - Evidencia: `resources/backend/app/modules/government/service_hallazgos.py:141-165` (_exigir_otro_verificador).
    - Por qué puede variar: Debería ser una regla SoD configurable
    - Destino: SOD_RULES
    - Fuente: NONE
  - **NUMBERING · INSTITUTIONAL_POLICY:** Prefijo "HA-{año}-"
    - Evidencia: `resources/backend/app/modules/government/service_hallazgos.py:599` (código de hallazgo).
    - Por qué puede variar: Series propias de la UAI
    - Destino: TENANT_POLICY de numeración
    - Fuente: NONE
  - **REPORT · OPERATIONAL_CONFIGURATION:** 13 columnas fijas
    - Evidencia: `resources/backend/app/modules/government/service_hallazgos.py:1123-1140` (exportar CSV).
    - Por qué puede variar: Formato de salida
    - Destino: TENANT_POLICY de reportes
    - Fuente: NONE

### CTL-07 · Alertas de operaciones atípicas

- **Clasificación:** REFACTOR_HARDCODED_POLICY (sin cambio: los tipos y criterios de alerta siguen fijos en el código)
- **Prioridad:** P1 (era P0 por el defecto, corregido)
- **Defecto actual:** CURRENT_PRODUCT_DEFECT_BEFORE=YES · CURRENT_PRODUCT_DEFECT_AFTER=NO (GOV-SOD-COVERAGE-01, 2026-11-17) · FUTURE_ARCHITECTURE_REFACTOR=STILL_PENDING
- **Motor:** CONTROL_RULES SOD_RULES TENANT_POLICY NORMATIVE_BINDING
- **Resumen:** Los tipos de alerta y sus criterios de detección están fijos en el código, sin activación ni parámetros por company_id. Solo las revisiones se guardan por ente.
  - **CATALOG · INSTITUTIONAL_POLICY:** 5 tipos con disponible True/False cableado (FRACCIONAMIENTO y OVERRIDE_FRECUENTE apagados); también models.py:4449
    - Evidencia: `resources/backend/app/modules/government/service_alertas.py:39-81` (TIPOS).
    - Por qué puede variar: Cada institución activa las alertas según su mapa de riesgos
    - Destino: CONTROL_RULES + TENANT_POLICY (activación por tipo)
    - Fuente: NONE
  - **WORKFLOW · INSTITUTIONAL_POLICY:** Duplicidad = misma unidad + objeto normalizado idéntico, sin ventana temporal ni similitud (OD-CTL07-02)
    - Evidencia: `resources/backend/app/modules/government/service_alertas.py:115-152` (_duplicidades).
    - Por qué puede variar: El criterio, la ventana y la tolerancia son política del ente
    - Destino: CONTROL_RULES parametrizables
    - Fuente: NONE
  - **AMOUNT · LEGAL_MANDATORY:** Alerta apagada por falta de umbrales de modalidad en U.T. con fuente legal
    - Evidencia: `resources/backend/app/modules/government/service_alertas.py:61-70` (TIPOS["FRACCIONAMIENTO"]).
    - Por qué puede variar: Los umbrales son legales y versionados (LCP, valor de la U.T.); requieren una tabla con vigencia
    - Destino: NORMATIVE_BINDING (umbrales versionados) + CONTROL_RULES
    - Fuente: LCP (umbrales de modalidad, N38 según la Spec)
  - **CATALOG · PLATFORM_INVARIANT:** Lista manual de eventos SoD (incompleta; ver defecto)
    - Evidencia: `resources/backend/app/modules/government/service_alertas.py:32` (ACCIONES_SOD).
    - Por qué puede variar: Debe derivarse del catálogo de auditoría (clase SoD)
    - Destino: SOD_RULES (evento único de bloqueo)
    - Fuente: NONE

### CTL-09 · Actas de entrega por cambio de responsable o autoridad

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1 (era P0 por el defecto, corregido)
- **Estado tras CTL-09-DELIVERY-ACT-POLICY (2026-11-18):** CURRENT_PRODUCT_DEFECT=NO. Los anexos de los arts. 11–17, los testigos del art. 9 y los plazos de los arts. 4, 21 y 22 pasan a un catálogo legal versionado (NORMATIVE_BINDING `N34-2009`, con fuente y vigencia). Los supuestos de los arts. 12–17 se declaran en la política del ente, para la entidad o para una unidad (TENANT_POLICY, OD-AE-01), junto con requisitos con tipo de evidencia (DOCUMENT_RULES y EVIDENCE_RULES), testigos en la entrega, plazos internos, cargo de máxima autoridad y numeración. El acta congela su regla, y saliente y receptor se resuelven con la autoridad de ORG-04 (RESPONSIBILITY_BINDING). Queda BUSINESS_CALENDAR pendiente (DOC-03): los plazos hábiles se muestran sin vencimiento calculado. FUTURE_ARCHITECTURE_REFACTOR=STILL_PENDING para el motor de procesos general.
- **Motor:** STAGES TRANSITIONS DOCUMENT_RULES EVIDENCE_RULES DEADLINES BUSINESS_CALENDAR SOD_RULES NORMATIVE_BINDING TENANT_POLICY
- **Resumen:** El saliente y el receptor se derivan de ORG-04. El contenido obligatorio del acta (anexos de los arts. 11 y 17, testigos del art. 9) está fijo en el código sin versión normativa, y aplica mal el art. 17. La numeración AE- también es fija.
  - **DOCUMENT · LEGAL_MANDATORY:** A11_1..A11_6 y A17_1..A17_5, con su carácter obligatorio y generable, como listas en el código
    - Evidencia: `resources/backend/app/modules/government/service_actas.py:47-62` (ANEXOS_CATALOGO, ANEXOS_MUNICIPALES).
    - Por qué puede variar: Una nueva resolución de la CGR cambiaría el contenido; no hay SOURCE, VERSION ni EFFECTIVE_FROM
    - Destino: DOCUMENT_RULES + NORMATIVE_BINDING (catálogo versionado)
    - Fuente: Normas para Regular la Entrega (N34, G.O. 39.229) arts. 10, 11, 17
  - **DOCUMENT · LEGAL_MANDATORY:** Los A17 se añaden si ente.nivel_territorial == "MUNICIPAL" y ámbito ENTE
    - Evidencia: `resources/backend/app/modules/government/service_actas.py:787-790` (crear acta (condición A17)).
    - Por qué puede variar: Debe depender del tipo de ente (alcaldía o hacienda municipal) o de una regla configurable, no solo del nivel territorial (ver defecto)
    - Destino: DOCUMENT_RULES condicionadas por tipo de ente
    - Fuente: N34 art. 17
  - **WORKFLOW · LEGAL_MANDATORY:** La modalidad LEVANTADA_POR_RECEPTOR exige exactamente 2 testigos y un auditor interno
    - Evidencia: `resources/backend/app/modules/government/service_actas.py:361-381` (_validar_testigos).
    - Por qué puede variar: Requisito legal sin versión
    - Destino: EVIDENCE_RULES + NORMATIVE_BINDING
    - Fuente: N34 art. 9
  - **AUTHORITY · LEGAL_MANDATORY:** Ámbito ENTE si la asignación es de máxima autoridad; si no, UNIDAD
    - Evidencia: `resources/backend/app/modules/government/service_actas.py:746` (ámbito).
    - Por qué puede variar: Se deriva bien de ORG-04; cabe en RESPONSIBILITY_BINDING
    - Destino: RESPONSIBILITY_BINDING
    - Fuente: N34 art. 6
  - **DEADLINE · LEGAL_MANDATORY:** No se calculan los plazos hábiles de los arts. 4 (3 días), 21 (5 días) y 22 (120 días); solo se registran las fechas (PDD-CTL09-08)
    - Evidencia: `resources/backend/app/modules/government/service_actas.py:-` ((ausente)).
    - Por qué puede variar: Requieren calendario hábil por ente
    - Destino: DEADLINES + BUSINESS_CALENDAR
    - Fuente: N34 arts. 4, 21, 22
  - **NUMBERING · INSTITUTIONAL_POLICY:** Prefijo "AE-{año}-"
    - Evidencia: `resources/backend/app/modules/government/service_actas.py:122-123` (_siguiente_codigo).
    - Por qué puede variar: Series propias del ente
    - Destino: TENANT_POLICY de numeración
    - Fuente: NONE
  - **REPORT · OPERATIONAL_CONFIGURATION:** Título "Acta de entrega {codigo}"; el órgano = la unidad del saliente; sin denominación del ente ni logo
    - Evidencia: `resources/backend/app/modules/government/service_actas.py:978-983` (_pdf_desde_acta).
    - Por qué puede variar: El acta oficial lleva la identidad del organismo (art. 10)
    - Destino: TENANT_POLICY de plantilla
    - Fuente: N34 art. 10

### CTL-10 · Controles materiales que impiden cerrar ejercicio o proceso

- **Clasificación:** REFACTOR_HARDCODED_POLICY
- **Prioridad:** P1
- **Motor:** CONTROL_RULES PROCESS_DEFINITION TRANSITIONS TENANT_POLICY
- **Resumen:** Las políticas y los controles son datos por company_id (gov_closure_policies y gov_closure_controls, con riesgo mínimo y materialidad). Pero qué cierres se pueden guardar (2) y qué controles existen (2) está fijo en el código. El cierre del ejercicio presupuestario (service_presupuesto.cerrar) no pasa por la guarda; fue así por alcance de la Spec (FR-026), pero hoy BUD ya existe.
  - **CATALOG · INSTITUTIONAL_POLICY:** Solo ORG02_CERRAR_ESTRUCTURA y TRE02_CERRAR_PROGRAMA; también models.py:2039
    - Evidencia: `resources/backend/app/modules/government/service_cierres.py:33-36` (ACCIONES_CIERRE).
    - Por qué puede variar: Otra institución querrá bloquear el cierre del ejercicio presupuestario (service_presupuesto.py:1333-1351 no llama a evaluar_cierre), de expedientes o de contratos
    - Destino: CONTROL_RULES sobre TRANSITIONS de PROCESS_DEFINITION
    - Fuente: NONE
  - **CATALOG · INSTITUTIONAL_POLICY:** Solo HALLAZGOS_ABIERTOS (con riesgo mínimo) y ACTOS_SIN_EFICACIA; también models.py:2040-2041
    - Evidencia: `resources/backend/app/modules/government/service_cierres.py:38-47` (TIPOS_CONTROL).
    - Por qué puede variar: Los controles materiales (notificaciones pendientes, actas sin verificar, cuentas sin rendir) varían por ente
    - Destino: CONTROL_RULES declarativas
    - Fuente: NONE
  - **WORKFLOW · PLATFORM_INVARIANT:** Llamadas explícitas a la guarda en cada servicio (también service_caja.py:1098)
    - Evidencia: `resources/backend/app/modules/government/service_estructura.py:952` (evaluar_cierre("ORG02_CERRAR_ESTRUCTURA")).
    - Por qué puede variar: Cada cierre nuevo exige tocar el código
    - Destino: TRANSITIONS con CONTROL_RULES del motor
    - Fuente: NONE
  - **NUMBERING · INSTITUTIONAL_POLICY:** Prefijo "PC-NNN" (3 dígitos, no anual)
    - Evidencia: `resources/backend/app/modules/government/service_cierres.py:398-406` (_siguiente_codigo).
    - Por qué puede variar: Series propias del ente
    - Destino: TENANT_POLICY de numeración
    - Fuente: NONE

### REP-03 · Contrataciones por modalidad, estado, unidad, proveedor, monto y tiempos

- **Clasificación:** ADAPT_TO_PROCESS_ENGINE
- **Prioridad:** P2
- **Motor:** STAGES BUSINESS_CALENDAR NORMATIVE_BINDING TENANT_POLICY
- **Resumen:** Es un reporte de solo lectura filtrado por company_id. Las unidades salen de GovernmentUnit de cada ente y los proveedores y montos de los datos. Los tiempos se miden en días continuos entre cuatro etapas fijas, y las secciones y columnas del CSV son fijas y sin encabezado institucional.
  - **DEADLINE · LEGAL_MANDATORY:** Tramos inicio→recepción→evaluación→decisión y inicio→cierre medidos con (a-b).days, en días continuos
    - Evidencia: `resources/backend/app/modules/government/service_reporte_contrataciones.py:57-60, 182-190` (_dias / tiempos).
    - Por qué puede variar: Los lapsos legales se cuentan en días hábiles según el calendario del ente, y las etapas cambian por modalidad
    - Destino: STAGES + BUSINESS_CALENDAR
    - Fuente: NONE
  - **CATALOG · LEGAL_MANDATORY:** Agrupa por las 4 modalidades importadas de _ETIQUETAS_MODALIDAD, sin versión
    - Evidencia: `resources/backend/app/modules/government/service_reporte_contrataciones.py:121-124, 178` (por_modalidad / metrica_por_modalidad).
    - Por qué puede variar: Una reforma del catálogo de modalidades rompe el agrupamiento histórico
    - Destino: NORMATIVE_BINDING
    - Fuente: NONE
  - **REPORT · OPERATIONAL_CONFIGURATION:** Título «Reporte de contrataciones» sin nombre del ente ni logo. Secciones y columnas fijas; Proveedores no trae monto
    - Evidencia: `resources/backend/app/modules/government/service_reporte_contrataciones.py:386-436` (exportar_csv).
    - Por qué puede variar: Las instituciones piden encabezado propio y columnas distintas para sus órganos de control
    - Destino: TENANT_POLICY (plantilla de reporte)
    - Fuente: NONE
  - **REPORT · LEGAL_MANDATORY:** El periodo por defecto empieza el 1 de enero del año en curso
    - Evidencia: `resources/backend/app/modules/government/service_reporte_contrataciones.py:47-48` (_inicio_periodo).
    - Por qué puede variar: Coincide con el ejercicio fiscal nacional, que la ley fija. El código no cita la fuente
    - Destino: BUSINESS_CALENDAR
    - Fuente: NONE

### REP-10 · Control interno: overrides, conflictos SoD, duplicados, hallazgos

- **Clasificación:** REFACTOR_HARDCODED_POLICY (sin cambio: secciones, columnas y textos siguen fijos en el código)
- **Prioridad:** P1 (era P0 por el defecto, corregido)
- **Defecto actual:** CURRENT_PRODUCT_DEFECT_BEFORE=YES · CURRENT_PRODUCT_DEFECT_AFTER=NO (GOV-SOD-COVERAGE-01, 2026-11-17) · FUTURE_ARCHITECTURE_REFACTOR=STILL_PENDING
- **Motor:** SOD_RULES CONTROL_RULES EXCEPTIONS TENANT_POLICY
- **Resumen:** Lee datos por company_id, pero las secciones, los eventos fuente, las columnas y los textos de "no aplica" están fijos en el código, y el reporte no lleva la identificación del ente.
  - **REPORT · PLATFORM_INVARIANT:** Un único action por sección, cableado (ver defecto)
    - Evidencia: `resources/backend/app/modules/government/service_reporte_control.py:92, 160, 198` (_seccion_conflictos_sod, _seccion_bloqueos_identidad, _seccion_bloqueos_cierre).
    - Por qué puede variar: Debe incluir todos los eventos de clase SoD o bloqueo del catálogo
    - Destino: SOD_RULES (evento normalizado) + CONTROL_RULES
    - Fuente: NONE
  - **REPORT · INSTITUTIONAL_POLICY:** Textos fijos: "No aplica" (porque no existe override) y "No disponible" (porque faltan TRE-03/TRE-04); no usa las alertas DUPLICIDAD de CTL-07
    - Evidencia: `resources/backend/app/modules/government/service_reporte_control.py:362-369` (overrides, operaciones_duplicadas).
    - Por qué puede variar: Si un ente habilita excepciones o si existen pagos, la sección cambia; depende de la política de EXCEPTIONS
    - Destino: EXCEPTIONS + TENANT_POLICY
    - Fuente: NONE
  - **REPORT · OPERATIONAL_CONFIGURATION:** Cabecera "Reporte de control interno" + fechas, sin denominación del ente ni logo; columnas fijas por sección
    - Evidencia: `resources/backend/app/modules/government/service_reporte_control.py:413-476` (exportar CSV).
    - Por qué puede variar: Cada UAI presenta su informe con su identidad y formato
    - Destino: TENANT_POLICY de plantilla de reportes
    - Fuente: NONE
  - **CATALOG · PLATFORM_INVARIANT:** Copias locales de los catálogos de CTL-06 (riesgo ALTO/MEDIO/BAJO)
    - Evidencia: `resources/backend/app/modules/government/service_reporte_control.py:34-36` (ESTADOS_HALLAZGO, RIESGOS_HALLAZGO, ESTADOS_ACCION).
    - Por qué puede variar: Si CTL-06 hace configurable la escala de riesgo, este reporte se rompe
    - Destino: TENANT_CONFIGURABLE_CATALOG compartido
    - Fuente: NONE
  - **CATALOG · PLATFORM_INVARIANT:** Las etiquetas de proceso dependen de la lista incompleta de CTL-04
    - Evidencia: `resources/backend/app/modules/government/service_reporte_control.py:39-45` (_etiqueta_proceso (usa PROCESOS de service_auditoria)).
    - Por qué puede variar: Debe usar un registro único
    - Destino: PROCESS_DEFINITION
    - Fuente: NONE

## Relación con P1

Este documento y su CSV son ficheros nuevos de P2: no editan las matrices principales que P1 reescribe en GOV-ROADMAP-REBASELINE-02.

- **P1:** el roadmap de los 122 procesos (48 bloqueados y 30 sin empezar) y la arquitectura global.
- **P2:** los 44 procesos ya construidos.

El solape funcional es 0.
