# GOVERNMENT-START-READINESS REPORT (2026-10-25)

Ciclo de planificación y readiness. **Ninguna implementación de Gobierno.** Base: `develop` `91eae11`. Las fuentes de Gobierno
(`requerimientos/gobierno/`, SHA-256 `8f86615f…` y `4a980bb9…`, iguales al registro de 9a41503) se leyeron sin modificarlas.
Clasificación de hallazgos: OFFICIAL_REQUIREMENT / PROJECT_REQUIREMENT / INDUSTRY_BEST_PRACTICE / BENCHMARK_FEATURE /
CLAUDE_RECOMMENDATION.

## Verdict
**GOVERNMENT_START_READINESS = BLOCKED.** Tres bloqueos independientes; los tres son explícitos y verificables:
1. **Certificación de release:** la condición de entrada exige SPEC054 = CLOSED / CONVERGED con la última corrida canónica en RC 0, y SPEC054 está en `IMPLEMENTED — CERTIFICATION PENDING` porque no hay anfitrión dedicado (OD-CERT-27/30).
2. **Fuentes y sponsor:** las dos fuentes están en `SPONSOR REVIEW — NO AUTORIZA DESARROLLO`; D-GOV-01..08 siguen abiertas, el checklist de freeze de la Biblioteca (§9) está en 0 de 10 y 12 de los 40 instrumentos son de clase C (sin pin oficial).
3. **Núcleo compartido frente a los RNF-GOV P0:** siete requisitos P0 de Gobierno no los cubre hoy el núcleo compartido (§ Shared Core Readiness). Cinco de ellos dependen de decisiones ya abiertas en la matriz de deuda.

## Repository
- `develop` = `origin/develop` = `91eae11`.
- SPEC054 en `c0216e8` (IMPLEMENTED — CERTIFICATION PENDING).
- SPEC046 S3 en `91eae11`.
- 9a41503 intacto; el `.docx` SNAT, sin tocar.
- MASTER57 = 57 filas; SPEC057 PLANNED / NOT STARTED.

## Release Certification Baseline
| Puerta | Estado | Evidencia |
|---|---|---|
| Orden canónica única | READY | `python3 qa/certificar-release.py`; portabilidad G1–G4 CLOSED |
| Última corrida oficial RC 0 | **FAIL** | ninguna: 8 corridas en la estación quedaron invalidadas por memoria; falta un anfitrión dedicado (`certification-host-requirements.md` v2) |
| Backend SQLite / PostgreSQL (diagnóstico) | PASS | 2138/0/1062 y 3182/0/18 (árbol `91eae11`) |
| E2E (diagnóstico) | PASS | 284 passed (12 CPU) |
| OpenAPI | PASS | deriva 0 frente a la referencia |
| Seguridad de dependencias | PASS (última medida) | pip-audit 0/0 en los dos locks (corrida de T4a) |

## Shared Core Readiness
Requisitos no funcionales de Gobierno (Ingeniería de Requerimientos §10, OFFICIAL/PROJECT_REQUIREMENT) contra el núcleo actual:

| RNF-GOV | Prio. | Núcleo compartido hoy | Estado | Bloquea el inicio |
|---|---|---|---|---|
| 001 Aislamiento tenant/ente con pruebas hostiles | P0 | multiempresa con pruebas de cruce (25 ficheros de prueba); N10 corrigió tres cruces. El concepto «ente» no existe (GOVERNMENT_ONLY). Abiertas: WAREHOUSE-CROSS-COMPANY-FILAS-EXISTENTES, WAREHOUSE-BRANCH-* (D) y API-COMPANY-ID-EN-CONSULTA (F) | READY_WITH_GAPS | no para planificar; sí para implementar GOV-0 |
| 002 Decimal para dinero | P0 | NUMERIC en dinero; DT-09: quedan 4 columnas Float aceptadas por ADR-012 (una de cantidad) | READY (verificar las 4 columnas al diseñar GOV-1) | no |
| 003 Fecha civil America/Caracas | P0 | POLICY-CLOCK-LOCAL (C) y **FECHAS-ZONA-DE-PRESENTACION (D, abierta)** | **GAP** | sí (decisión transversal pendiente) |
| 004 Inmutabilidad (reverso, no edición) | P0 | patrón presente en módulos convergidos; sin política transversal verificada | NOT_MEASURED | se evalúa en ARCHITECTURE-BASELINE |
| 005 Auditabilidad del 100 % de P0 | P0 | 006 y 051 PARTIALLY_IMPLEMENTED; **DT-06** (catálogo de eventos, D), AUDIT-DETAIL-NO-IMPLEMENTADO (A), DOCUMENT-SCAN-REJECTION-AUDIT-NOT-PERSISTED (D) | **GAP** | sí |
| 006 Autorización en backend | P0 | RBAC en backend, motor de aprobaciones y SoD (045 COMPLETE) | READY | no |
| 007 Idempotencia | P0 | no inventariada en esta readiness | NOT_MEASURED | se evalúa en ARCHITECTURE-BASELINE |
| 010 RTO/RPO y backup/restore validados | P0 | 053: `backup.sh`/`restore.sh` **sin verificación de restauración** | **GAP** | sí, antes de producción |
| 011 MFA para roles privilegiados | P0 | solo la columna `users.mfa_enabled`; **MFA no construido** | **GAP** | sí |
| 012 Mínimo privilegio / sin autoridad transversal | P0 | **ROLES-SIN-TECHO-DE-DELEGACION (D, abierta)**: un actor puede delegar permisos que no posee | **GAP** | sí |
| 013 Listados server-side paginados | P1 | canon 1..100 en el núcleo; ADDITIONAL_UNBOUNDED_LISTING (D) | READY_WITH_GAPS | no |
| 014 Accesibilidad | P1 | `e2e/accessibility.spec.ts` (axe) en la E2E canónica; DATATABLE-CAPTION (A) | READY_WITH_GAPS | no |
| 015 API versionada y errores deterministas | P0 | `/api/v1`, `KontrolError` con código; **API-QUERY-SILENCIOSA (D)** ignora parámetros no declarados; LISTADOS-SIN-RESPONSE-MODEL (A) | **GAP** | sí (decisión de contrato pendiente) |
| 017 Observabilidad | P0 | logs estructurados (`KONTROL_LOG_JSON`); 006 parcial | READY_WITH_GAPS | no |

## Government Source Register
- Registro: `docs/roadmap/kontrol-gobierno-source-register.md`.
- Fuentes v1.0, corte normativo 16-10-2026; los SHA-256 coinciden.
- GOV-0..7 son ciclos de planificación, no Specs.
- MASTER57 no cambia.
- SNAT/2026/00093 = DEFERRED_NORMATIVE_IMPLEMENTATION: no bloquea y no entra en el alcance.

## Normative Source Readiness
| Puerta (Biblioteca §9, freeze) | Estado |
|---|---|
| Copia custodiada y SHA-256 de cada fuente P0 | **FAIL**: solo las dos fuentes del proyecto; ninguna Gaceta ni instructivo custodiado en el repositorio |
| Vigencia verificada (G.O. 7.018/2026, 6.699/2022, Decreto 2.174, SUDEBIP 43.077) | NOT_STARTED |
| Clase C (N07–N10, N14–N17, N36, N37, N38, N40) con pin oficial | **FAIL** (12 de 40) |
| Normativa del piloto (D-GOV-01) | BLOCKED (sponsor) |
| Edición ONAPRE/ONCOP del ejercicio (D-GOV-02/04) | BLOCKED (sponsor) |
| SNC / SUDEBIP (D-GOV-03/05) | BLOCKED (sponsor) |
| Retenciones del pagador público (N38) | BLOCKED: clase C, cruce con 039–043 (BLOCKED_BY_LEGAL_VALIDATION) |
| Trámites tras G.O. 7.018/2026 (D-GOV-06) | BLOCKED (sponsor) |
| Matriz requisito → fuente | NOT_STARTED |
| Aprobación del sponsor y de su asesor jurídico | **FAIL** (`SPONSOR REVIEW`) |

LEGAL_VALIDATION_REQUIRED = 1 para todo el inventario de clase C.

## Architecture Boundaries
Clasificación preliminar, a fijar en GOVERNMENT-ARCHITECTURE-BASELINE (CLAUDE_RECOMMENDATION):

| Clase | Capacidades |
|---|---|
| SHARED_CORE | identidad, sesiones y RBAC; aprobaciones y SoD; auditoría; documentos y ClamAV; notificaciones; licenciamiento por instalación; certificación |
| SHARED_CONTRACT_DIFFERENT_IMPLEMENTATION | organización (empresa frente a organismo, ente y unidad ejecutora); almacenes (comerciales frente a consumo); activos fijos 057 frente a bienes públicos LOBP/SUDEBIP; tesorería; reportes |
| GOVERNMENT_ONLY | presupuesto (compromiso → causado → pagado); contratación pública (SNC); contabilidad pública ONCOP; rendición y control (CGR); trámites |
| PRIVATE_ONLY | ventas, compras comerciales, fiscal empresarial SENIAT (039–043), importaciones |

La cadena ORGANISMO → … → RENDICIÓN es una hipótesis que hay que contrastar con las fuentes, no un requisito.

## Tenant / Organization Isolation
- **READY_WITH_GAPS.** El aislamiento por instalación y empresa está probado.
- Gobierno exige aislar también **llaves y configuración** por ente, y pruebas hostiles E2E-06 (OFFICIAL/PROJECT). Eso es un modelo propio (GOVERNMENT_ONLY), no se puede copiar la multiempresa.
- Las deudas D de almacenes (cruces de empresa y sucursal) tienen que resolverse antes de reutilizar esos patrones.

## Authentication / Authorization
- **GAP:** MFA no construido (RNF-GOV-011, P0).
- **GAP:** el techo de delegación sigue abierto (RNF-GOV-012, P0).
- Sesiones (002) y alcances sin UI (003): PARTIALLY_IMPLEMENTED.

## Audit Readiness
**GAP.** 006 y 051 están parciales; DT-06 (catálogo de eventos) depende de una decisión; hay que persistir los rechazos de análisis. Gobierno exige bitácora append-only con actor, autoridad, fuente, soporte y correlación en el 100 % de los P0 (GOV-CTL-002, RNF-GOV-005).

## Document Infrastructure
- **READY.** 046 RECONVERGED; ClamAV real.
- S3 = NOT_SUPPORTED_BY_PRODUCT_BASELINE, con fallo cerrado (`91eae11`).
- OBS-09 (evidencia Docker de la imagen con analizador) sigue como puerta externa.
- Firma electrónica (GOV-DOC-006, P1): no existe (D-GOV-08).

## Database Readiness
- **READY.** PostgreSQL 16.2 de QA fijado y verificado; migraciones a la cabeza; 3182/0/18.
- Restauración no verificada: el gap está en 053 (ver RNF-GOV-010).

## API Architecture
**READY_WITH_GAPS.** `/api/v1` y OpenAPI estable (544 operaciones). Errores deterministas: abierta API-QUERY-SILENCIOSA (D). Falta `response_model` en los listados (A).

## Frontend Architecture
**READY_WITH_GAPS.**
- Design System y navegación (005) parciales; i18n presente (`src/i18n`, es).
- E2E canónica solo en Chromium; el humo cruzado de navegadores no es portable (CROSS_BROWSER_SMOKE_LOCAL_PATH_NONPORTABLE).

## Security
**READY_WITH_GAPS.**
- 055 sin Spec propietaria (OBS-04, D).
- pip-audit 0/0.
- Los gaps P0 de MFA y delegación están arriba.

## Test Infrastructure
- **READY.** Orden canónica, mutaciones, suites SQLite y PostgreSQL, E2E con procedencia de intérpretes y política de entorno.
- Falta el anfitrión dedicado para la corrida oficial.

## Cross-Browser Infrastructure
**NOT_READY** para Gobierno: CROSS_BROWSER_SMOKE_LOCAL_PATH_NONPORTABLE; la E2E canónica es solo Chromium (decisión de SPEC054). El trabajo cruzado de navegadores está previsto como calidad de Gobierno.

## Accessibility Infrastructure
READY_WITH_GAPS: axe en la E2E canónica; DATATABLE-CAPTION (A).

## S3 Decision
**RESOLVED:** OD-GOV-START-01 + OD-S3-01. S3_PROVIDER_SUPPORTED = 0; S3_CONFIGURATION_GUARDED = 1 (`91eae11`).

## External Gates
- Anfitrión dedicado de certificación (proveedor sin conectar).
- OBS-09: evidencia Docker; no se cierra en silencio.
- Freeze del sponsor y D-GOV-01..08.
- Validación jurídica de las fuentes de clase C.

## Blocking Debts
Bloquean el inicio de la **implementación** de Gobierno; no bloquean la planificación:
- RC 0 oficial de SPEC054;
- MFA (RNF-011);
- techo de delegación (ROLES-SIN-TECHO-DE-DELEGACION);
- zona de presentación America/Caracas (FECHAS-ZONA-DE-PRESENTACION);
- catálogo de auditoría (DT-06) y persistencia del rechazo de análisis;
- contrato de errores deterministas (API-QUERY-SILENCIOSA);
- verificación de restauración (053).

## Non-Blocking Debts
- ADDITIONAL_UNBOUNDED_LISTING;
- LISTADOS-SIN-RESPONSE-MODEL;
- DATATABLE-CAPTION;
- E2E-RESULT-MANIFEST-POST-VALIDITY-SEMANTICS;
- PG-MIGRATION-VALIDATION-VENV;
- mypy global de `app`;
- EJECUTOR-ABREVIA-EL-CONTEXTO;
- deudas A de prioridad baja de la matriz.

## Material Owner Questions
**MATERIAL_OQ = 1. Un solo paquete, tres preguntas.**

**OQ-GSR-1 — ¿Se puede avanzar a la GOVERNMENT-ARCHITECTURE-BASELINE con la certificación oficial pendiente?**
- *Hechos:* la condición de entrada exige el RC 0 de SPEC054; la arquitectura base es solo planificación y documentación, sin código.
- *Opciones:*
  - **A:** esperar al anfitrión dedicado;
  - **B:** autorizar solo la planificación (ARCHITECTURE-BASELINE); la implementación sigue bloqueada hasta el RC 0.
- *Impacto y riesgo:* B no toca el producto. Si la certificación oficial revelara un defecto del núcleo, la línea base podría necesitar ajustes.
- *Recomendación:* **B**.

**OQ-GSR-2 — ¿Qué secuencia se sigue para cerrar los gaps P0 del núcleo compartido antes de implementar Gobierno?**
- *Hechos:* MFA, techo de delegación, zona de presentación, catálogo de auditoría, errores deterministas y verificación de restauración son SHARED_CORE. Cinco esperan decisiones ya abiertas en la matriz (D).
- *Opciones:*
  - **A:** un programa de endurecimiento del núcleo (deltas en las Specs dueñas 002/003, 001, 006/051, 053) antes de GOV-0;
  - **B:** absorberlos en GOV-0 Foundation.
- *Impacto y riesgo:* con B se mezclaría la semántica de Gobierno con el núcleo, contra P-02 y la separación de la línea.
- *Recomendación:* **A**, con las decisiones D pendientes en un único paquete:
  - techo de delegación: «solo permisos que el actor posee»;
  - zona de presentación: America/Caracas;
  - parámetros no declarados: 422;
  - catálogo de eventos de 006/051;
  - auditoría del rechazo de análisis: sesión independiente.

**OQ-GSR-3 — Sponsor de Gobierno (fuera del alcance de Claude).**
- El freeze de la línea base, D-GOV-01..08 y la validación jurídica de la clase C los resuelve el sponsor.
- Hasta entonces no se crea ninguna GOV-SPEC (`BLOCKED BY OWNER DECISION`).

## Final Analyze
| Campo | Valor |
|---|---|
| GOVERNMENT_START_READINESS | BLOCKED |
| SPEC054_STATUS | IMPLEMENTED — CERTIFICATION PENDING |
| CANONICAL_RUN_RC (último oficial) | NOT EXECUTED (sin anfitrión) |
| S3_PROVIDER_SUPPORTED / S3_CONFIGURATION_GUARDED | 0 / 1 |
| GOVERNMENT_SOURCES_STATUS | SPONSOR REVIEW — NO AUTORIZA DESARROLLO |
| D-GOV-01..08 | 8 OPEN |
| NORMATIVE_FREEZE_CHECKLIST | 0 / 10 |
| NORMATIVE_CLASS_C | 12 / 40 (LEGAL_VALIDATION_REQUIRED = 1) |
| SHARED_CORE_P0_GAPS | 7 (RNF-GOV-003, 005, 010, 011, 012, 015 y RNF-GOV-001 parcial) |
| BLOCKING_P0_FOR_IMPLEMENTATION | 7 |
| BLOCKING_FOR_PLANNING | 0 (pendiente de OQ-GSR-1) |
| GOVERNMENT_SPEC_STARTED | 0 |
| MASTER57 / SPEC057 | 57 / PLANNED — NOT STARTED |
| OBS09_STATUS | BLOCKED BY ENVIRONMENT, puerta externa |
| SNAT | DEFERRED_NORMATIVE_IMPLEMENTATION |
| DEEPSEEK_CALLS | 0 (ciclo de planificación, sin código) |
| PRODUCTION_TOUCHED | 0 |
| MATERIAL_OQ | 1 paquete (OQ-GSR-1..3) |

## Closure / Blocker
BLOCKED por el RC 0 oficial de SPEC054, por el freeze del sponsor con D-GOV-01..08 y por los gaps P0 del núcleo. No se inicia ninguna Spec de Gobierno.

## Next Planning
- Con OQ-GSR-1 = B: GOVERNMENT-ARCHITECTURE-BASELINE (planificación).
- En paralelo, con OQ-GSR-2 = A: el paquete de decisiones D del núcleo y las deltas de endurecimiento en sus Specs dueñas.
- La certificación oficial, cuando haya anfitrión, cerrará SPEC054 y la delta S3.

## Decisiones de la dueña (2026-10-25)
- **OD-GSR-1 = B:** se autoriza GOVERNMENT-ARCHITECTURE-BASELINE solo como planificación y documentación. La implementación de Gobierno sigue bloqueada hasta el RC 0 oficial de SPEC054.
- **OD-GSR-2 = A:** los gaps P0 del núcleo compartido se cierran **antes** de GOV-0, con deltas en sus Specs dueñas (002/003, 001, 006/051, 053). El paquete de decisiones D toma los valores de la opción aprobada:
  - ROLES-SIN-TECHO-DE-DELEGACION: «solo permisos que el actor posee»;
  - FECHAS-ZONA-DE-PRESENTACION: America/Caracas;
  - API-QUERY-SILENCIOSA: 422 ante parámetros no declarados (impacto conocido: rompe 27 de 224 E2E, que se adaptan en la delta);
  - DT-06: catálogo de eventos de 006/051;
  - DOCUMENT-SCAN-REJECTION-AUDIT-NOT-PERSISTED: sesión independiente.
- OQ-GSR-3 sigue en manos del sponsor.
