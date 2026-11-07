# Matriz autoritativa de deudas técnicas

Rederivada el 2026-10-19 sobre `develop` `40b2277` (Ruta B, solo lectura). Fuentes: roadmap, next-spec-decision, deltas, evidencia y **código de HEAD**; sustituye a las matrices parciales anteriores (p. ej. `specs/008-almacenes-fisicos/evidence/warehouse-branch-cross-company/candidate-matrix.md`). Sin cambios de producto, pruebas ni QA; DeepSeek 0.

## Recuento

| Categoría | Nº |
|---|---|
| A · PROVEN_FIXABLE | 10 |
| B · PROVEN_NEEDS_DIAGNOSIS | 1 |
| C · OBSERVATION_NEEDS_REPRODUCTION | 6 |
| D · BLOCKED_BY_OWNER_DECISION | 27 |
| E · BLOCKED_BY_EXTERNAL_EVIDENCE | 1 |
| F · BLOCKED_BY_DEPENDENCY | 10 |
| G · NOT_A_DEFECT / SUPERSEDED | 10 |
| **Total** | **65** |

## Selección

**SELECTED_NEXT_TECHNICAL_CANDIDATE = CERTIFICATION-ENVIRONMENT-DEPENDENCY-DRIFT** (dueña 054; apoyo 001, 052; categoría B). Riesgo de producción y de seguridad sobre **toda** la certificación: desde el 2026-09-30 se certifica con Python 3.11 y versiones anteriores a la corrección de CVE (FastAPI 0.115.6, Starlette 0.41.3, PyJWT 2.10.1, cryptography 44.0.0, python-multipart 0.0.20), mientras la imagen instala Python 3.13 con FastAPI 0.141.1, Starlette **1.3.1** (versión mayor), PyJWT 2.13.0, cryptography 46.0.6 y python-multipart 0.0.31. Sin decisión de la dueña (ADR-014 y la matriz de dependencias fijan las versiones), independiente de OBS-09 y diagnosticable ya (uv, CPython 3.13 del sistema, PyPI accesible).

Segunda: **ALMACENES-DESPLEGABLES-TRUNCADOS** (categoría A, dueña 008): defecto funcional demostrado y corregible sin decisión, de radio menor (empresas con más de 50 almacenes).

Hallazgo acoplado a OBS-09: **PRODUCTION-IMAGE-WITHOUT-LIBMAGIC** — la imagen no instala python-magic ni libmagic; F01, F03 y F04 de la evidencia Docker de OBS-09 fallarían por `MIME_MISMATCH` antes del analizador. Su alcance (dentro de OBS-09 o ciclo propio) es decisión de la dueña.

## Resumen

| Deuda | Cat. | Dueña | Elegible ahora | Motivo / decisión pendiente |
|---|---|---|---|---|
| CERTIFICATION-ENVIRONMENT-DEPENDENCY-DRIFT | B | 054 | 1 | — |
| ALMACENES-DESPLEGABLES-TRUNCADOS | A | 008 | 1 | segunda en prioridad (ver selección) |
| EMPRESAS-PLACEHOLDER-GENERICO | A | 001 | 1 | prioridad 9 |
| AUDIT-DETAIL-NO-IMPLEMENTADO | A | 001 | 1 | funcionalidad nueva declarada; prioridad inferior |
| TEST-MIGRACIONES-VENV-FIJO | A | 052/054 | 1 | prioridad 9; la deriva lo hará visible al reconstruir el entorno |
| E2E-APPROVALS-LIMIT-NO-DECLARADO | A | 054 | 1 | prioridad 9 |
| AUDIT-PAGINA-SIN-INDICE-DE-ORDEN | A | 001 | 1 | exige migración; prioridad 8 |
| AUDIT-OPENAPI-SIN-RESPONSE-MODEL | A | 001 | 1 | subsumida en LISTADOS-SIN-RESPONSE-MODEL; response_model filtra campos: cambio con riesgo |
| AUDITORIA-TIMELINE-FECHA-CRUDA | A | 009/012 | 1 | prioridad 9 |
| LISTADOS-SIN-RESPONSE-MODEL | A | 001 | 1 | response_model filtra campos y cambia el documento publicado; prioridad 7 |
| DATATABLE-CAPTION-EN-MODO-MANUAL | A | 001/012 | 1 | prioridad 9 |
| OBS-09 · PRODUCTION-IMAGE-WITHOUT-SCANNER | E | 046 | 0 | espera evidencia Docker externa; además PRODUCTION-IMAGE-WITHOUT-LIBMAGIC hará fallar F01/F03/F04 |
| PRODUCTION-IMAGE-WITHOUT-LIBMAGIC | F | 046 | 0 | depende de OBS-09 (mismo fichero y misma evidencia de runtime) y de Docker |
| API-COMPANY-ID-EN-CONSULTA | F | 001 | 0 | depende de API-QUERY-SILENCIOSA |
| LOCK-SIN-REPORTLAB-MAGIC | F | 001/052 | 0 | se resuelve con la deriva (CERTIFICATION-ENVIRONMENT-DEPENDENCY-DRIFT) y la imagen (PRODUCTION-IMAGE-WITHOUT-LIBMAGIC) |
| FECHAS-FORMATO-A-MANO | F | 001 | 0 | depende de FECHAS-ZONA-DE-PRESENTACION |
| DT-10 | F | registro original | 0 | compose.yaml:13,29,36,78; el fichero está en vuelo con OBS-09 y el defecto de desarrollo es deliberado (cabecera :3) |
| DT-11 | CERRADA (núcleo) | 001 (delta backup-restore-verification) | 0 | 2026-10-28, ciclo 06: copia y restauración verificadas y certificación real PASS; quedan BACKUP-SCHEDULE-RPO, BACKUP-PG-TOOLS-IN-OPS-IMAGE y BACKUP-RTO-DATOS-REALES |
| DT-13 | F | registro original | 0 | programa de cobertura (8 de 108 páginas): alcance de ola |
| DT-14 | F | registro original | 0 | programa de rendimiento con volumen: alcance de ola |
| DT-15 | F | registro original | 0 | alcance de la Spec 055 |
| DT-17 | F | registro original | 0 | UnsavedChangesGuard existe y solo lo usa ProductoNuevoPage: programa por formulario (Spec 005) |
| AUDIT-ORDEN-SIN-DESEMPATE | C | 001 | 1 (diagnóstico) | no manifestado (0 instantes repetidos); prioridad 8 |
| AUTH-MC-INTERMITENTE | C | 054 | 0 | no reproducida en las 12 últimas corridas completas |
| POLICY-CLOCK-LOCAL | C | 013/052 | 0 | observación coherente con el despliegue documentado; el cambio toca fiscal |
| EJECUTOR-ABREVIA-EL-CONTEXTO | C | 001 (gobernanza) | 0 | no reproducido después |
| VITEST-MOCKCLEAR-EN-HOOK | C | 054 | 0 | observación de herramienta |
| DT-18 | C | registro original | 0 | no se localizaron los cuatro documentos (el informe ejecutivo no aparece); verificar antes de actuar |
| ADDITIONAL_UNBOUNDED_LISTING | D | varias (008, 011, 046, aprobaciones, fiscales) | 0 | ¿autorizan las dueñas aplicar el tope canónico 1..100 y 422 a sus listados, con inventario de consumidores por listado? |
| API-QUERY-SILENCIOSA | D | 001 | 0 | ¿rechazar (422) o ignorar los parámetros no declarados? (rompe 27/224 E2E) |
| BUSQUEDA-Q-SIN-ESCAPE | D | 001 | 0 | ¿escapar comodines en todos los q (convención transversal)? |
| AUDITORIA-OFFSET-EN-BITACORA-VIVA | D | 001 | 0 | ¿paginación por cursor en la bitácora (cambio de contrato)? |
| FECHAS-ZONA-DE-PRESENTACION | D | 001 | 0 | ¿fijar una zona de presentación (p. ej. America/Caracas) en nueve pantallas? |
| EMPRESAS-STATUS-SORT | D | 001 | 0 | ¿se añade (funcionalidad nueva)? |
| E2E-PANTALLA-SIN-PINTAR | D | 054 | 0 | ¿debe el arnés abortar o invalidar una corrida con red cambiada o reloj saltado? |
| POLITICA-E2E-RED-RELOJ-MEMORIA | D | 054 | 0 | ¿aborta, invalida o solo anota el arnés ante cambio de red, salto de reloj o presión de memoria? |
| ROLES-SIN-TECHO-DE-DELEGACION | D | 003 | 0 | ¿techo de delegación «solo permisos que el actor posee»? |
| EMISOR-DE-LICENCIAS-SIN-IMPLEMENTAR | D | 004 | 0 | ¿alcance y calendario de las fases 2+ (activación, pago, revocación)? |
| AUDITORIA-PANTALLA-DUPLICADA | D → UX_PRODUCT_DECISION (2026-10-28) | 012 | 0 | ¿unificar o renombrar las dos pantallas? Decisión de producto aún no tomada; LOW; no bloqueante |
| MOVTYPE-GLOBAL-SIN-UNICIDAD | D | 023 | 0 | ¿pueden dos tipos globales compartir código? |
| SEED-EMPRESA-CODIGO-NO-UNICO | D | 007 | 0 | ¿el código de empresa identifica o etiqueta? |
| DOCUMENT-ARCHIVE-LOST-UPDATE-DURING-UPLOAD | D | 046 | 0 | ¿qué ocurre si se archiva un documento mientras su carga está en análisis? A) 409 al persistir con revalidación/bloqueo de fila (recomendada) · B) permitir versión sin reactivar · C) bloquear el archivado durante la carga |
| DOCUMENT-DELETE-DURING-UPLOAD-ORPHAN-500 | D | 046 | 0 | ¿qué responde una carga cuyo documento se eliminó durante el análisis? A) 404 DOCUMENT_NOT_FOUND + limpiar binario (recomendada) · B) 409 DOCUMENT_DELETED + limpiar · C) 404 y limpieza diferida |
| DOCUMENT-SCAN-REJECTION-AUDIT-NOT-PERSISTED | D | 046 (con 001) | 0 | ¿debe persistir DOCUMENT_SCAN_REJECTED aunque la carga termine en 422? A) sesión independiente · B) commit explícito antes del 422 (recomendada) · C) aceptar que no persista |
| ALMACENES-PAGINACION-LIMIT-OFFSET | D | 008 | 0 | ¿renombrar al canon page/page_size (rompe 12 pantallas y 10 suites)? |
| OBS-04 · SPEC-SEGURIDAD-SIN-CARPETA | D | inventario | 0 | ¿se crea la carpeta o se reasigna en el inventario? |
| WAREHOUSE-CROSS-COMPANY-FILAS-EXISTENTES | D | 008 | 0 | ciclo 07: MEDIBLE con `python -m app.ops.scope_scan` (solo lectura), 0 filas en las bases de QA; la ejecución en una instalación real y cualquier reparación siguen pendientes de OD |
| WAREHOUSE-BRANCH-ALCANCE-DE-USUARIO (branch_ids) | D | 008 | 0 | ciclo 07: LATENT (sin escritor ni consumidor en el producto); ¿debe el alcance de sucursales del usuario limitar las sucursales de almacén cuando exista un escritor? |
| WAREHOUSE-BRANCH-FK-COMPUESTA | D | 008 | 0 | ¿se autoriza la migración de defensa en profundidad? |
| WAREHOUSE-CATALOG-TIPOS-INACTIVOS | D | 008 | 0 | ¿puede una ubicación o zona usar un tipo inactivo? |
| DT-04 | D | registro original | 0 | necesita tabla, FK, migración y backfill: alcance de Spec 007 sin priorizar |
| DT-06 | D | registro original | 0 | faltan altas de empresas, sucursales, establecimientos y maestros; el catálogo de eventos (acción y carga) no está fijado: contrato de 006/051 |
| DT-07 | D | registro original | 0 | ¿usar o retirar? retirar es migración |
| DT-12 | D | registro original | 0 | arquitectura (cola) de 048/050 |
| DT-16 | D | registro original | 0 | política de seguridad nueva (límites por ruta): Spec 055 |
| TEST-PG-CATALOGO-MARCA-DE-AGUA | G | 054 | 0 | NO_EFFECT: no crece entre corridas y autovacuum lo devuelve (medido en este mismo periodo) |
| AUDIT-TOTAL-MATERIALIZA | G | 001 | 0 | SUPERSEDED: audit/api.py:53 calcula COUNT en SQL (AUDIT-TOTAL-CARGA-TODO) |
| LICENCIA-MIDDLEWARE-BD-EN-EL-BUCLE | G | 004 | 0 | SUPERSEDED por LICENSE-MIDDLEWARE-BLOCKS-EVENT-LOOP (0e2cb7b; middleware.py:58 run_in_threadpool) |
| OBS-03 · TESTCLIENT-RELANZA-EN-HILO | G | 054 | 0 | guía, no defecto |
| DT-01 | G | registro original | 0 | SUPERSEDED: sales/models.py:509 FK order_id (255f039, Spec 034) |
| DT-02 | G | registro original | 0 | SUPERSEDED: FK en todas las líneas (a7afd6b, Spec 011) |
| DT-03 | G | registro original | 0 | SUPERSEDED en lo exigible: source/target_location_id (Spec 022); la recepción no ubica por diseño (purchasing/service.py:679) |
| DT-05 | G | registro original | 0 | SUPERSEDED: customer_commercial_terms con FK (Spec 012); el texto legado se conserva por FR-012-080 |
| DT-08 | G | registro original | 0 | SUPERSEDED: test_el_orm_y_la_base_no_difieren_en_nada (N10) y qa/pg-migration-validation.sh |
| DT-09 | G | registro original | 0 | SUPERSEDED: quedan 4 columnas Float (una de cantidad: transfer_lines.difference), aceptado por ADR-012 |

## Detalle por deuda (campos del encargo §7 y §11)

### CERTIFICATION-ENVIRONMENT-DEPENDENCY-DRIFT — PROVEN_NEEDS_DIAGNOSIS
- **TITLE:** La certificación corre con versiones distintas de las fijadas para producción
- **OWNER_SPEC:** 054
- **SUPPORTING_SPECS:** 001, 052
- **CURRENT_STATUS:** NUEVA (registrada en este ciclo)
- **CATEGORY:** B · PROVEN_NEEDS_DIAGNOSIS
- **SOURCE_PATH:** Dockerfile.backend:7,19-20 · resources/backend/requirements.txt · requirements.lock · docs/evidence/cve-review.md:14 · specs/001-fundacion/dependency-matrix.md:65
- **EVIDENCE_PATH:** medición 2026-10-19: venv de QA Python 3.11.16 · fastapi 0.115.6 · starlette 0.41.3 · PyJWT 2.10.1 · cryptography 44.0.0 · python-multipart 0.0.20; fijado: Python 3.13 (imagen) · fastapi 0.141.1 · starlette 1.3.1 · PyJWT 2.13.0 · cryptography 46.0.6 · python-multipart 0.0.31
- **DEFECT_REPRODUCED:** 1 (la deriva, medida)
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1 (el venv de QA se reparó a mano el 2026-09-30 y nunca se reconstruyó desde los pines) / impacto 0 (no se sabe si el producto funciona con los pines)
- **CONTRACT_CONFIRMED:** 1 (ADR-014 versiones fijadas; P14; dependency-matrix: versiones finales)
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** LOCK-SIN-REPORTLAB-MAGIC (el lock no trae reportlab ni python-magic); TEST-MIGRACIONES-VENV-FIJO (10 pruebas con ruta fija a .venv)
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0 (uv 0.12.17, CPython 3.13 del sistema, PyPI accesible 200)
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** seguridad 1 (se certifican versiones anteriores a la corrección de CVE) · producción 1 (Starlette 1.x es versión mayor) · QA 1
- **BLAST_RADIUS:** todo el backend y toda certificación desde 2026-09-30
- **ESTIMATED_SIZE:** M (diagnóstico); la corrección depende de lo que mida
- **REPRODUCIBLE_NOW:** 1
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** tareas de código que el diagnóstico destape
- **CLAUDE_ONLY:** diagnóstico, gate y certificación
- **ELIGIBLE_NOW:** 1
- **EXCLUSION_REASON:** —
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 1

### ALMACENES-DESPLEGABLES-TRUNCADOS — PROVEN_FIXABLE
- **TITLE:** Ocho pantallas muestran solo los 50 primeros almacenes en su desplegable
- **OWNER_SPEC:** 008
- **SUPPORTING_SPECS:** 022
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** A · PROVEN_FIXABLE
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md (fila ALMACENES-DESPLEGABLES-TRUNCADOS)
- **EVIDENCE_PATH:** evidence/e2e-flaky/putaway-corte-500.txt; HEAD: Ubicaciones, Ajustes, Transferencias, Conteos, Reservas, OrdenesVentas, Movimientos y Seriales llaman /organization/warehouses sin paginar (defecto 50, warehouse_api.py:317); solo PutAway y Preparacion usan listAllWarehouses
- **DEFECT_REPRODUCED:** 1 (2026-10-01, putaway 2/2)
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 1 (listAllWarehouses es el consumidor canónico de LISTADOS-SIN-TOPE)
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** producción 1 (no se puede operar con el almacén 51+) · integridad 0
- **BLAST_RADIUS:** 8 pantallas de inventario, ventas y organización
- **ESTIMATED_SIZE:** S
- **REPRODUCIBLE_NOW:** 1 (sembrando >50 almacenes)
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** 1
- **CLAUDE_ONLY:** 0
- **ELIGIBLE_NOW:** 1
- **EXCLUSION_REASON:** segunda en prioridad (ver selección)
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0 (estructural)

### AUDIT-DETAIL-NO-IMPLEMENTADO — PROVEN_FIXABLE
- **TITLE:** GET /audit/events/{id} declarado y no implementado
- **OWNER_SPEC:** 001
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** A · PROVEN_FIXABLE
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 1
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** contrato (aislamiento por tenant si se implementa)
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** S
- **REPRODUCIBLE_NOW:** 1
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** 1
- **CLAUDE_ONLY:** 0
- **ELIGIBLE_NOW:** 1
- **EXCLUSION_REASON:** funcionalidad nueva declarada; prioridad inferior
- **STILL_PRESENT:** 1 (sin ruta /events/{id})
- **MEASURED_NOW:** 1

### AUDIT-OPENAPI-SIN-RESPONSE-MODEL — PROVEN_FIXABLE
- **TITLE:** /audit/events sin response_model
- **OWNER_SPEC:** 001
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** A · PROVEN_FIXABLE
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 1
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** contrato documental
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** S
- **REPRODUCIBLE_NOW:** 1
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** 1
- **CLAUDE_ONLY:** 0
- **ELIGIBLE_NOW:** 1
- **EXCLUSION_REASON:** subsumida en LISTADOS-SIN-RESPONSE-MODEL; response_model filtra campos: cambio con riesgo
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### AUDIT-PAGINA-SIN-INDICE-DE-ORDEN — PROVEN_FIXABLE
- **TITLE:** sin índice (tenant_id, event_time)
- **OWNER_SPEC:** 001
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** A · PROVEN_FIXABLE
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 1
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** rendimiento (14 ms con 13 577 eventos)
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** S
- **REPRODUCIBLE_NOW:** 1
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 1
- **SCHEMA_CHANGE_EXPECTED:** 1
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** 1
- **CLAUDE_ONLY:** 0
- **ELIGIBLE_NOW:** 1
- **EXCLUSION_REASON:** exige migración; prioridad 8
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### AUDITORIA-TIMELINE-FECHA-CRUDA — PROVEN_FIXABLE
- **TITLE:** ReportesAuditoriaPage pinta event_time crudo
- **OWNER_SPEC:** 009/012
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** A · PROVEN_FIXABLE
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 1
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** cosmético
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** S
- **REPRODUCIBLE_NOW:** 1
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** 1
- **CLAUDE_ONLY:** 0
- **ELIGIBLE_NOW:** 1
- **EXCLUSION_REASON:** prioridad 9
- **STILL_PRESENT:** 1 (ReportesAuditoriaPage.tsx:31)
- **MEASURED_NOW:** 1

### DATATABLE-CAPTION-EN-MODO-MANUAL — PROVEN_FIXABLE
- **TITLE:** caption y aria-label cuentan la página, no el total
- **OWNER_SPEC:** 001/012
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** A · PROVEN_FIXABLE
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 1
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** accesibilidad
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** S
- **REPRODUCIBLE_NOW:** 1
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** 1
- **CLAUDE_ONLY:** 0
- **ELIGIBLE_NOW:** 1
- **EXCLUSION_REASON:** prioridad 9
- **STILL_PRESENT:** 1 (DataTable.tsx:60)
- **MEASURED_NOW:** 1

### E2E-APPROVALS-LIMIT-NO-DECLARADO — PROVEN_FIXABLE
- **TITLE:** approvals.spec.ts envía ?limit=200 a /audit/events
- **OWNER_SPEC:** 054
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** A · PROVEN_FIXABLE
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 1
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** QA
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** S
- **REPRODUCIBLE_NOW:** 1
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** 1
- **CLAUDE_ONLY:** 0
- **ELIGIBLE_NOW:** 1
- **EXCLUSION_REASON:** prioridad 9
- **STILL_PRESENT:** 1 (approvals.spec.ts:301)
- **MEASURED_NOW:** 1

### EMPRESAS-PLACEHOLDER-GENERICO — PROVEN_FIXABLE
- **TITLE:** «Buscar en esta pantalla…» en Empresas
- **OWNER_SPEC:** 001
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** A · PROVEN_FIXABLE
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 1
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** cosmético
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** S
- **REPRODUCIBLE_NOW:** 1
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** 1
- **CLAUDE_ONLY:** 0
- **ELIGIBLE_NOW:** 1
- **EXCLUSION_REASON:** prioridad 9
- **STILL_PRESENT:** 1 (SearchInput.tsx:13; EmpresasPage sin placeholder propio)
- **MEASURED_NOW:** 1

### LISTADOS-SIN-RESPONSE-MODEL — PROVEN_FIXABLE
- **TITLE:** 17 listados sin response_model
- **OWNER_SPEC:** 001
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** A · PROVEN_FIXABLE
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 1
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** contrato documental (OpenAPI)
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** S
- **REPRODUCIBLE_NOW:** 1
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** 1
- **CLAUDE_ONLY:** 0
- **ELIGIBLE_NOW:** 1
- **EXCLUSION_REASON:** response_model filtra campos y cambia el documento publicado; prioridad 7
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### TEST-MIGRACIONES-VENV-FIJO — PROVEN_FIXABLE
- **TITLE:** pruebas con ruta fija a .venv/bin/alembic
- **OWNER_SPEC:** 052/054
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** A · PROVEN_FIXABLE
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 1
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** QA
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** S
- **REPRODUCIBLE_NOW:** 1
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** 1
- **CLAUDE_ONLY:** 0
- **ELIGIBLE_NOW:** 1
- **EXCLUSION_REASON:** prioridad 9; la deriva lo hará visible al reconstruir el entorno
- **STILL_PRESENT:** 1 (10 ficheros)
- **MEASURED_NOW:** 1

### OBS-09 · PRODUCTION-IMAGE-WITHOUT-SCANNER — BLOCKED_BY_EXTERNAL_EVIDENCE
- **TITLE:** imagen de producción sin analizador (clamd)
- **OWNER_SPEC:** 046
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** E · BLOCKED_BY_EXTERNAL_EVIDENCE
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 1
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 1
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** seguridad · producción
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** espera evidencia Docker externa; además PRODUCTION-IMAGE-WITHOUT-LIBMAGIC hará fallar F01/F03/F04
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### API-COMPANY-ID-EN-CONSULTA — BLOCKED_BY_DEPENDENCY
- **TITLE:** company_id en la consulta, ignorado
- **OWNER_SPEC:** 001
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** F · BLOCKED_BY_DEPENDENCY
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 1
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** ver motivo
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** contrato
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** depende de API-QUERY-SILENCIOSA
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### DT-10 — BLOCKED_BY_DEPENDENCY
- **TITLE:** KONTROL_IMAGE_TAG por defecto latest
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** F · BLOCKED_BY_DEPENDENCY
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 1
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** L
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** compose.yaml:13,29,36,78; el fichero está en vuelo con OBS-09 y el defecto de desarrollo es deliberado (cabecera :3)
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 1

### DT-11 — CLOSED_SHARED_CORE (2026-10-28, ciclo 06)
- **CIERRE:** `specs/001-fundacion/spec001-backup-restore-verification-delta.md` · `evidence/backup-restore/certificacion.md` (corrida 20261028T194821Z-a8fdf8 PASS). Deudas derivadas: BACKUP-SCHEDULE-RPO, BACKUP-PG-TOOLS-IN-OPS-IMAGE, BACKUP-RTO-DATOS-REALES, BACKUP-RESTORED-UI-SMOKE. El registro original se conserva debajo.
- **TITLE:** backup/restore nunca ejecutado
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** F · BLOCKED_BY_DEPENDENCY
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 1
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** L
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** Spec 053 sin iniciar; exige entorno de despliegue (Docker)
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 1

### DT-13 — BLOCKED_BY_DEPENDENCY
- **TITLE:** pruebas de página frontend
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** F · BLOCKED_BY_DEPENDENCY
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** L
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** programa de cobertura (8 de 108 páginas): alcance de ola
- **STILL_PRESENT:** parcial
- **MEASURED_NOW:** 1

### DT-14 — BLOCKED_BY_DEPENDENCY
- **TITLE:** rendimiento sobre base vacía
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** F · BLOCKED_BY_DEPENDENCY
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** L
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** programa de rendimiento con volumen: alcance de ola
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 1

### DT-15 — BLOCKED_BY_DEPENDENCY
- **TITLE:** sin SBOM
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** F · BLOCKED_BY_DEPENDENCY
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** L
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** alcance de la Spec 055
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 1

### DT-17 — BLOCKED_BY_DEPENDENCY
- **TITLE:** sin protección de cambios sin guardar
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** F · BLOCKED_BY_DEPENDENCY
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** L
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** UnsavedChangesGuard existe y solo lo usa ProductoNuevoPage: programa por formulario (Spec 005)
- **STILL_PRESENT:** parcial
- **MEASURED_NOW:** 1

### FECHAS-FORMATO-A-MANO — BLOCKED_BY_DEPENDENCY
- **TITLE:** toLocaleString a mano en ocho pantallas
- **OWNER_SPEC:** 001
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** F · BLOCKED_BY_DEPENDENCY
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 1
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** ver motivo
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** cosmético
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** depende de FECHAS-ZONA-DE-PRESENTACION
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### LOCK-SIN-REPORTLAB-MAGIC — BLOCKED_BY_DEPENDENCY
- **TITLE:** el lock no trae reportlab ni python-magic
- **OWNER_SPEC:** 001/052
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** F · BLOCKED_BY_DEPENDENCY
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 1
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** ver motivo
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** entorno QA; producción vía PRODUCTION-IMAGE-WITHOUT-LIBMAGIC
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** se resuelve con la deriva (CERTIFICATION-ENVIRONMENT-DEPENDENCY-DRIFT) y la imagen (PRODUCTION-IMAGE-WITHOUT-LIBMAGIC)
- **STILL_PRESENT:** 1 (lock sin ambos; requirements.txt sin python-magic)
- **MEASURED_NOW:** 1

### PRODUCTION-IMAGE-WITHOUT-LIBMAGIC — BLOCKED_BY_DEPENDENCY
- **TITLE:** La imagen backend no instala python-magic ni libmagic: toda carga documental cae en 422 MIME_MISMATCH
- **OWNER_SPEC:** 046
- **SUPPORTING_SPECS:** 052
- **CURRENT_STATUS:** NUEVA (registrada en este ciclo)
- **CATEGORY:** F · BLOCKED_BY_DEPENDENCY
- **SOURCE_PATH:** Dockerfile.backend:15-20 (solo curl; pip -r requirements.txt) · requirements.txt (sin python-magic) · app/modules/documents/service.py:85-92,173-191 · qa/compose_qa.py:579,685-708
- **EVIDENCE_PATH:** sonda en proceso 2026-10-19: PDF real → application/pdf con python-magic; application/octet-stream sin él → 422
- **DEFECT_REPRODUCED:** 1 (mecanismo, en proceso) / imagen 0 (sin Docker)
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1 (estructural)
- **CONTRACT_CONFIRMED:** 1 (§19 MIME por contenido; fail-closed correcto)
- **OWNER_DECISION_REQUIRED:** 0 para la corrección; alcance frente a OBS-09 = decisión de la dueña
- **OWNER_DECISION_EXACT_QUESTION:** ¿se trata dentro de OBS-09 (mismo Dockerfile y misma evidencia F01-F04) o en un ciclo propio antes de su evidencia Docker?
- **DEPENDENCY_OBS09:** 1 (F01, F03 y F04 de OBS-09 suben PDF: fallarían por MIME antes del analizador)
- **DEPENDENCY_OTHER_DEBT:** LOCK-SIN-REPORTLAB-MAGIC
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 1 (verificar la imagen exige Docker)
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** producción 1 (gestión documental inservible en la imagen) · integridad 0 (falla cerrada)
- **BLAST_RADIUS:** toda carga documental en producción; evidencia de OBS-09
- **ESTIMATED_SIZE:** S (Dockerfile + requirements)
- **REPRODUCIBLE_NOW:** 1 en proceso / 0 en imagen
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** 1 (Dockerfile/requirements)
- **CLAUDE_ONLY:** gate y certificación con Docker
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** depende de OBS-09 (mismo fichero y misma evidencia de runtime) y de Docker
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 1

### AUDIT-ORDEN-SIN-DESEMPATE — OBSERVATION_NEEDS_REPRODUCTION
- **TITLE:** orden solo por event_time
- **OWNER_SPEC:** 001
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** C · OBSERVATION_NEEDS_REPRODUCTION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 1
- **ROOT_CAUSE_PROVEN:** 0
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** contrato menor
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 1 (diagnóstico)
- **EXCLUSION_REASON:** no manifestado (0 instantes repetidos); prioridad 8
- **STILL_PRESENT:** 1 (audit/api.py:55)
- **MEASURED_NOW:** 1

### AUTH-MC-INTERMITENTE — OBSERVATION_NEEDS_REPRODUCTION
- **TITLE:** 401 esporádico en tandas largas del arnés multiempresa
- **OWNER_SPEC:** 054
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** C · OBSERVATION_NEEDS_REPRODUCTION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 1
- **ROOT_CAUSE_PROVEN:** 0
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** QA
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** no reproducida en las 12 últimas corridas completas
- **STILL_PRESENT:** 0 observado
- **MEASURED_NOW:** 0

### DT-18 — OBSERVATION_NEEDS_REPRODUCTION
- **TITLE:** 4 documentos de estado desfasados
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** C · OBSERVATION_NEEDS_REPRODUCTION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** no se localizaron los cuatro documentos (el informe ejecutivo no aparece); verificar antes de actuar
- **STILL_PRESENT:** probable
- **MEASURED_NOW:** 1

### EJECUTOR-ABREVIA-EL-CONTEXTO — OBSERVATION_NEEDS_REPRODUCTION
- **TITLE:** el puente abrevió contexto en 4/9 delegaciones
- **OWNER_SPEC:** 001 (gobernanza)
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** C · OBSERVATION_NEEDS_REPRODUCTION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 1
- **ROOT_CAUSE_PROVEN:** 0
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** herramientas
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** no reproducido después
- **STILL_PRESENT:** 0 observado
- **MEASURED_NOW:** 0

### POLICY-CLOCK-LOCAL — OBSERVATION_NEEDS_REPRODUCTION
- **TITLE:** active_policy usa el día civil del servidor
- **OWNER_SPEC:** 013/052
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** C · OBSERVATION_NEEDS_REPRODUCTION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 1
- **ROOT_CAUSE_PROVEN:** 0
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** fiscal bajo (coherente con servidor en UTC, ADR-D0-001)
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** observación coherente con el despliegue documentado; el cambio toca fiscal
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### VITEST-MOCKCLEAR-EN-HOOK — OBSERVATION_NEEDS_REPRODUCTION
- **TITLE:** mockClear en beforeEach con rechazo
- **OWNER_SPEC:** 054
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** C · OBSERVATION_NEEDS_REPRODUCTION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 1
- **ROOT_CAUSE_PROVEN:** 0
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** QA
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** observación de herramienta
- **STILL_PRESENT:** 0 medido
- **MEASURED_NOW:** 0

### ADDITIONAL_UNBOUNDED_LISTING — BLOCKED_BY_OWNER_DECISION
- **TITLE:** 85 listados sin tope o con sobre falso
- **OWNER_SPEC:** varias (008, 011, 046, aprobaciones, fiscales)
- **SUPPORTING_SPECS:** 001
- **CURRENT_STATUS:** REGISTRADA (spec008-listados-sin-tope-delta.md §13)
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** specs/008-almacenes-fisicos/spec008-listados-sin-tope-delta.md §13
- **EVIDENCE_PATH:** HEAD: warehouse_api.py:773,798,1035 · uom_api.py:189 · approvals/api.py:370 · documents/api.py:347 aceptan limit/offset sin límites
- **DEFECT_REPRODUCED:** 0 en estos (1 en el precedente de almacenes: offset negativo → 500 en PostgreSQL)
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1 (estructural)
- **CONTRACT_CONFIRMED:** parcial (tope canónico de la Spec 001), con consumidores sin inventariar y dueñas fiscales intocables
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿autorizan las dueñas aplicar el tope canónico 1..100 y 422 a sus listados, con inventario de consumidores por listado?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** rendimiento 1 · producción bajo (500 con parámetros negativos)
- **BLAST_RADIUS:** 85 listados
- **ESTIMATED_SIZE:** L
- **REPRODUCIBLE_NOW:** 1
- **DIAGNOSABLE_NOW:** 1
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** por listado
- **CLAUDE_ONLY:** contrato
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** decisión de las dueñas registrada en el precedente
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### ALMACENES-PAGINACION-LIMIT-OFFSET — BLOCKED_BY_OWNER_DECISION
- **TITLE:** 8 listados con limit/offset y sobre {total,limit,offset,items}
- **OWNER_SPEC:** 008
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OBSERVACIÓN REGISTRADA
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** spec008-listados-sin-tope-delta.md §13
- **EVIDENCE_PATH:** spec008-listados-sin-tope-delta.md §13
- **DEFECT_REPRODUCED:** 0
- **OBSERVATION_ONLY:** 1
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿renombrar al canon page/page_size (rompe 12 pantallas y 10 suites)?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** decisión de las dueñas
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### API-QUERY-SILENCIOSA — BLOCKED_BY_OWNER_DECISION
- **TITLE:** parámetros de consulta no declarados aceptados con 200
- **OWNER_SPEC:** 001
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿rechazar (422) o ignorar los parámetros no declarados? (rompe 27/224 E2E)
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** contrato público
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** MATERIAL_DECISION_REQUIRED
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### AUDITORIA-OFFSET-EN-BITACORA-VIVA — BLOCKED_BY_OWNER_DECISION
- **TITLE:** OFFSET sobre un registro vivo repite eventos
- **OWNER_SPEC:** 001
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿paginación por cursor en la bitácora (cambio de contrato)?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** contrato
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** decisión de contrato
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### AUDITORIA-PANTALLA-DUPLICADA — BLOCKED_BY_OWNER_DECISION
- **RECLASIFICACIÓN 2026-10-28 (SHARED-CORE-P0-HARDENING-05 §6):** no existe decisión de la dueña. Estado: OPEN · CATEGORY = UX_PRODUCT_DECISION · SEVERITY = LOW · BLOCKING = 0. No se fusiona, renombra ni retira ninguna pantalla hasta una decisión de producto expresa.
- **TITLE:** dos entradas «Auditoría» en el menú
- **OWNER_SPEC:** 012
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿unificar o renombrar las dos pantallas?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** UX
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** decisión de producto
- **STILL_PRESENT:** 1 (Sidebar.tsx:217,251)
- **MEASURED_NOW:** 1

### BUSQUEDA-Q-SIN-ESCAPE — BLOCKED_BY_OWNER_DECISION
- **TITLE:** % y _ actúan como comodín en los q
- **OWNER_SPEC:** 001
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿escapar comodines en todos los q (convención transversal)?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** búsqueda (no inyección SQL)
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** convención transversal
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### DOCUMENT-ARCHIVE-LOST-UPDATE-DURING-UPLOAD — BLOCKED_BY_OWNER_DECISION
- **TITLE:** archivar durante una carga se pierde
- **OWNER_SPEC:** 046
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿qué ocurre si se archiva un documento mientras su carga está en análisis? A) 409 al persistir con revalidación/bloqueo de fila (recomendada) · B) permitir versión sin reactivar · C) bloquear el archivado durante la carga
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** integridad
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** BLOCKED_BY_OWNER_DECISION
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### DOCUMENT-DELETE-DURING-UPLOAD-ORPHAN-500 — BLOCKED_BY_OWNER_DECISION
- **TITLE:** borrar durante una carga da 500 y deja huérfano
- **OWNER_SPEC:** 046
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿qué responde una carga cuyo documento se eliminó durante el análisis? A) 404 DOCUMENT_NOT_FOUND + limpiar binario (recomendada) · B) 409 DOCUMENT_DELETED + limpiar · C) 404 y limpieza diferida
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** integridad
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** BLOCKED_BY_OWNER_DECISION
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### DOCUMENT-SCAN-REJECTION-AUDIT-NOT-PERSISTED — BLOCKED_BY_OWNER_DECISION
- **TITLE:** la auditoría de rechazo de malware no persiste
- **OWNER_SPEC:** 046 (con 001)
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿debe persistir DOCUMENT_SCAN_REJECTED aunque la carga termine en 422? A) sesión independiente · B) commit explícito antes del 422 (recomendada) · C) aceptar que no persista
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** seguridad (rastro)
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** BLOCKED_BY_OWNER_DECISION
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### DT-04 — BLOCKED_BY_OWNER_DECISION
- **TITLE:** cost_center_id String(36) sin tabla
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** necesita tabla, FK, migración y backfill: alcance de Spec 007 sin priorizar
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** L
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 1
- **SCHEMA_CHANGE_EXPECTED:** 1
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** necesita tabla, FK, migración y backfill: alcance de Spec 007 sin priorizar
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 1

### DT-06 — BLOCKED_BY_OWNER_DECISION
- **TITLE:** organization/master_data sin auditoría
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** faltan altas de empresas, sucursales, establecimientos y maestros; el catálogo de eventos (acción y carga) no está fijado: contrato de 006/051
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** L
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** faltan altas de empresas, sucursales, establecimientos y maestros; el catálogo de eventos (acción y carga) no está fijado: contrato de 006/051
- **STILL_PRESENT:** parcial
- **MEASURED_NOW:** 1

### DT-07 — BLOCKED_BY_OWNER_DECISION
- **TITLE:** outbox_events y feature_flags muertas
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿usar o retirar? retirar es migración
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** L
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 1
- **SCHEMA_CHANGE_EXPECTED:** 1
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** ¿usar o retirar? retirar es migración
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 1

### DT-12 — BLOCKED_BY_OWNER_DECISION
- **TITLE:** report_jobs en proceso
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** arquitectura (cola) de 048/050
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** L
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** arquitectura (cola) de 048/050
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 1

### DT-16 — BLOCKED_BY_OWNER_DECISION
- **TITLE:** sin rate limiting global
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** política de seguridad nueva (límites por ruta): Spec 055
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** L
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** política de seguridad nueva (límites por ruta): Spec 055
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 1

### E2E-PANTALLA-SIN-PINTAR — BLOCKED_BY_OWNER_DECISION
- **TITLE:** página sin pintar con backend sano
- **OWNER_SPEC:** 054
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿debe el arnés abortar o invalidar una corrida con red cambiada o reloj saltado?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** QA/entorno
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** política pendiente de la dueña
- **STILL_PRESENT:** 0 reproducido desde 2026-10-13
- **MEASURED_NOW:** 0

### EMISOR-DE-LICENCIAS-SIN-IMPLEMENTAR — BLOCKED_BY_OWNER_DECISION
- **TITLE:** fases posteriores de la Autoridad Central
- **OWNER_SPEC:** 004
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿alcance y calendario de las fases 2+ (activación, pago, revocación)?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** negocio
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** fase 1 implementada; el resto es alcance de negocio (D0-06)
- **STILL_PRESENT:** 1 (parcial)
- **MEASURED_NOW:** 1

### EMPRESAS-STATUS-SORT — BLOCKED_BY_OWNER_DECISION
- **TITLE:** status y sort no implementados en Empresas
- **OWNER_SPEC:** 001
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿se añade (funcionalidad nueva)?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** funcionalidad nueva, no defecto
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### FECHAS-ZONA-DE-PRESENTACION — BLOCKED_BY_OWNER_DECISION
- **TITLE:** zona de presentación de instantes
- **OWNER_SPEC:** 001
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿fijar una zona de presentación (p. ej. America/Caracas) en nueve pantallas?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** contrato
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** MATERIAL_DECISION_REQUIRED
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### MOVTYPE-GLOBAL-SIN-UNICIDAD — BLOCKED_BY_OWNER_DECISION
- **TITLE:** tipos de movimiento globales duplicables
- **OWNER_SPEC:** 023
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿pueden dos tipos globales compartir código?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** integridad
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** MATERIAL_DECISION_REQUIRED (identidad de negocio)
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### OBS-04 · SPEC-SEGURIDAD-SIN-CARPETA — BLOCKED_BY_OWNER_DECISION
- **TITLE:** la Spec 002 de seguridad no tiene carpeta propia
- **OWNER_SPEC:** inventario
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OBSERVACIÓN REGISTRADA
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** OBSERVACIONES.md:8
- **EVIDENCE_PATH:** OBSERVACIONES.md:8
- **DEFECT_REPRODUCED:** 0
- **OBSERVATION_ONLY:** 1
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿se crea la carpeta o se reasigna en el inventario?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** documental, dueña del inventario
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### POLITICA-E2E-RED-RELOJ-MEMORIA — BLOCKED_BY_OWNER_DECISION
- **TITLE:** política del arnés ante red, reloj y memoria del equipo
- **OWNER_SPEC:** 054
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿aborta, invalida o solo anota el arnés ante cambio de red, salto de reloj o presión de memoria?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** QA/entorno
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** misma decisión que E2E-PANTALLA-SIN-PINTAR
- **STILL_PRESENT:** 1 (solo se anota)
- **MEASURED_NOW:** 1

### ROLES-SIN-TECHO-DE-DELEGACION — BLOCKED_BY_OWNER_DECISION
- **TITLE:** sin techo de delegación de permisos
- **OWNER_SPEC:** 003
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿techo de delegación «solo permisos que el actor posee»?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** seguridad
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** política de seguridad nueva: decisión de la dueña
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### SEED-EMPRESA-CODIGO-NO-UNICO — BLOCKED_BY_OWNER_DECISION
- **TITLE:** companies sin unicidad (tenant_id, code)
- **OWNER_SPEC:** 007
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿el código de empresa identifica o etiqueta?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** integridad
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** MATERIAL_DECISION_REQUIRED
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### WAREHOUSE-BRANCH-ALCANCE-DE-USUARIO (branch_ids) — BLOCKED_BY_OWNER_DECISION
- **TITLE:** CompanyContext.branch_ids no limita la sucursal del almacén
- **OWNER_SPEC:** 008
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OBSERVACIÓN REGISTRADA
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** spec008-warehouse-branch-cross-company-delta.md §10
- **EVIDENCE_PATH:** spec008-warehouse-branch-cross-company-delta.md §10
- **DEFECT_REPRODUCED:** 0
- **OBSERVATION_ONLY:** 1
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿debe el alcance de sucursales del usuario limitar las sucursales de almacén?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** multiempresa
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** no medido si debe; contrato no definido
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### WAREHOUSE-BRANCH-FK-COMPUESTA — BLOCKED_BY_OWNER_DECISION
- **TITLE:** sin FK compuesta (company_id, branch_id)
- **OWNER_SPEC:** 008
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OBSERVACIÓN REGISTRADA
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** spec008-warehouse-branch-cross-company-delta.md §10
- **EVIDENCE_PATH:** spec008-warehouse-branch-cross-company-delta.md §10
- **DEFECT_REPRODUCED:** 0
- **OBSERVATION_ONLY:** 1
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿se autoriza la migración de defensa en profundidad?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** multiempresa
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 1
- **SCHEMA_CHANGE_EXPECTED:** 1
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** migración no autorizada
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### WAREHOUSE-CATALOG-TIPOS-INACTIVOS — BLOCKED_BY_OWNER_DECISION
- **TITLE:** tipos inactivos de la propia empresa aceptados
- **OWNER_SPEC:** 008
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OBSERVACIÓN REGISTRADA
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** spec008-warehouse-catalog-type-cross-company-delta.md §2
- **EVIDENCE_PATH:** spec008-warehouse-catalog-type-cross-company-delta.md §2
- **DEFECT_REPRODUCED:** 0
- **OBSERVATION_ONLY:** 1
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿puede una ubicación o zona usar un tipo inactivo?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** multiempresa
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** otra semántica
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### WAREHOUSE-CROSS-COMPANY-FILAS-EXISTENTES — BLOCKED_BY_OWNER_DECISION
- **TITLE:** filas cruzadas previas a las correcciones de almacenes
- **OWNER_SPEC:** 008
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OBSERVACIÓN REGISTRADA
- **CATEGORY:** D · BLOCKED_BY_OWNER_DECISION
- **SOURCE_PATH:** spec008-warehouse-branch-cross-company-delta.md §10
- **EVIDENCE_PATH:** spec008-warehouse-branch-cross-company-delta.md §10
- **DEFECT_REPRODUCED:** 0
- **OBSERVATION_ONLY:** 1
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** 0
- **OWNER_DECISION_REQUIRED:** 1
- **OWNER_DECISION_EXACT_QUESTION:** ¿se autoriza una consulta de solo lectura por instalación (y, si aparecen, una reparación)?
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** multiempresa
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 1
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** backfill no autorizado
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### AUDIT-TOTAL-MATERIALIZA — NOT_A_DEFECT / SUPERSEDED
- **TITLE:** total por len(...all())
- **OWNER_SPEC:** 001
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN → SUPERSEDED
- **CATEGORY:** G · NOT_A_DEFECT / SUPERSEDED
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 1
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** SUPERSEDED: audit/api.py:53 calcula COUNT en SQL (AUDIT-TOTAL-CARGA-TODO)
- **STILL_PRESENT:** 0
- **MEASURED_NOW:** 0

### DT-01 — NOT_A_DEFECT / SUPERSEDED
- **TITLE:** SalesInvoice sin FK a sales_orders
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** G · NOT_A_DEFECT / SUPERSEDED
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** SUPERSEDED: sales/models.py:509 FK order_id (255f039, Spec 034)
- **STILL_PRESENT:** 0
- **MEASURED_NOW:** 1

### DT-02 — NOT_A_DEFECT / SUPERSEDED
- **TITLE:** líneas sin uom_id/presentation_id
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** G · NOT_A_DEFECT / SUPERSEDED
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** SUPERSEDED: FK en todas las líneas (a7afd6b, Spec 011)
- **STILL_PRESENT:** 0
- **MEASURED_NOW:** 1

### DT-03 — NOT_A_DEFECT / SUPERSEDED
- **TITLE:** location_id nullable
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** G · NOT_A_DEFECT / SUPERSEDED
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** SUPERSEDED en lo exigible: source/target_location_id (Spec 022); la recepción no ubica por diseño (purchasing/service.py:679)
- **STILL_PRESENT:** parcial (por diseño)
- **MEASURED_NOW:** 1

### DT-05 — NOT_A_DEFECT / SUPERSEDED
- **TITLE:** price_list/zone/payment_term texto
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** G · NOT_A_DEFECT / SUPERSEDED
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** SUPERSEDED: customer_commercial_terms con FK (Spec 012); el texto legado se conserva por FR-012-080
- **STILL_PRESENT:** 0
- **MEASURED_NOW:** 1

### DT-08 — NOT_A_DEFECT / SUPERSEDED
- **TITLE:** alembic check nunca contra PostgreSQL
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** G · NOT_A_DEFECT / SUPERSEDED
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** SUPERSEDED: test_el_orm_y_la_base_no_difieren_en_nada (N10) y qa/pg-migration-validation.sh
- **STILL_PRESENT:** 0
- **MEASURED_NOW:** 1

### DT-09 — NOT_A_DEFECT / SUPERSEDED
- **TITLE:** 36 cantidades en Float
- **OWNER_SPEC:** registro original
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** REGISTRO ORIGINAL (sin columna de estado)
- **CATEGORY:** G · NOT_A_DEFECT / SUPERSEDED
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md líneas 3-22
- **EVIDENCE_PATH:** verificación en HEAD 2026-10-19
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** —
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** SUPERSEDED: quedan 4 columnas Float (una de cantidad: transfer_lines.difference), aceptado por ADR-012
- **STILL_PRESENT:** 0 (residual)
- **MEASURED_NOW:** 1

### LICENCIA-MIDDLEWARE-BD-EN-EL-BUCLE — NOT_A_DEFECT / SUPERSEDED
- **TITLE:** la licencia consulta la base dentro del bucle
- **OWNER_SPEC:** 004
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN → SUPERSEDED
- **CATEGORY:** G · NOT_A_DEFECT / SUPERSEDED
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 1
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** SUPERSEDED por LICENSE-MIDDLEWARE-BLOCKS-EVENT-LOOP (0e2cb7b; middleware.py:58 run_in_threadpool)
- **STILL_PRESENT:** 0
- **MEASURED_NOW:** 0

### OBS-03 · TESTCLIENT-RELANZA-EN-HILO — NOT_A_DEFECT / SUPERSEDED
- **TITLE:** TestClient relanza el 500 en el hilo
- **OWNER_SPEC:** 054
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OBSERVACIÓN REGISTRADA
- **CATEGORY:** G · NOT_A_DEFECT / SUPERSEDED
- **SOURCE_PATH:** evidence/auth-rotacion-sqlite-hilos/OBSERVACIONES.md:7
- **EVIDENCE_PATH:** evidence/auth-rotacion-sqlite-hilos/OBSERVACIONES.md:7
- **DEFECT_REPRODUCED:** 0
- **OBSERVATION_ONLY:** 1
- **ROOT_CAUSE_PROVEN:** —
- **CONTRACT_CONFIRMED:** 1
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** —
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** guía, no defecto
- **STILL_PRESENT:** 1
- **MEASURED_NOW:** 0

### TEST-PG-CATALOGO-MARCA-DE-AGUA — NOT_A_DEFECT / SUPERSEDED
- **TITLE:** ~170 MB de catálogo reutilizable en ktest
- **OWNER_SPEC:** 054
- **SUPPORTING_SPECS:** —
- **CURRENT_STATUS:** OPEN → NO_EFFECT
- **CATEGORY:** G · NOT_A_DEFECT / SUPERSEDED
- **SOURCE_PATH:** docs/roadmap/technical-debt-roadmap.md
- **EVIDENCE_PATH:** ver fila del roadmap
- **DEFECT_REPRODUCED:** —
- **OBSERVATION_ONLY:** 0
- **ROOT_CAUSE_PROVEN:** 1
- **CONTRACT_CONFIRMED:** 1
- **OWNER_DECISION_REQUIRED:** 0
- **OWNER_DECISION_EXACT_QUESTION:** —
- **DEPENDENCY_OBS09:** 0
- **DEPENDENCY_OTHER_DEBT:** 0
- **DEPENDENCY_EXTERNAL_ENVIRONMENT:** 0
- **RISKS (seguridad · multitenant · integridad · dinero/fiscal · producción · rendimiento · QA):** ninguno
- **BLAST_RADIUS:** —
- **ESTIMATED_SIZE:** —
- **REPRODUCIBLE_NOW:** —
- **DIAGNOSABLE_NOW:** —
- **MIGRATION_EXPECTED:** 0
- **SCHEMA_CHANGE_EXPECTED:** 0
- **MATERIAL_OQ_EXPECTED:** 0
- **DEEPSEEK_ELIGIBLE:** —
- **CLAUDE_ONLY:** —
- **ELIGIBLE_NOW:** 0
- **EXCLUSION_REASON:** NO_EFFECT: no crece entre corridas y autovacuum lo devuelve (medido en este mismo periodo)
- **STILL_PRESENT:** 0 (sin efecto)
- **MEASURED_NOW:** 0


## Actualización 2026-10-19 — diagnóstico de CERTIFICATION-ENVIRONMENT-DEPENDENCY-DRIFT

Fuente: `specs/012-auditoria-integral-e2e/spec054-certification-environment-drift-diagnosis-delta.md`.

| Deuda | Cat. | Dueña | Elegible ahora | Estado |
|---|---|---|---|---|
| CERTIFICATION-ENVIRONMENT-DEPENDENCY-DRIFT | B → diagnosticada | 054 | — | DIAGNOSIS COMPLETE (MIXED); 0 incompatibilidades funcionales; RELEASE_DEPLOYMENT_PARITY_CERTIFIED = 0 |
| **DEPLOYMENT-PARITY-TEST-INCOMPATIBILITIES** (nueva) | A | 054 | **1 — SELECCIONADA** | OAS-14, ACS-08 y U03/U04 fallan con las versiones de despliegue por causas de prueba demostradas |
| FASTAPI-YIELD-TEARDOWN-AFTER-RESPONSE (nueva) | A | 001 (054) | 1 | impacto medido despreciable; se decide dentro de la seleccionada |
| PRODUCTION-IMAGE-WITHOUT-LIBMAGIC | F → reproducida | 052 (001, 046) | 0 | 31 fallos en V1; independiente (OD-CERT-02); prerrequisito de OBS-09 |
| PRODUCTION-IMAGE-BUILT-FROM-DEV-STAGE (nueva) | F | 052 | 0 | estructural; verificar exige Docker |
| PRODUCTION-DEPENDENCIES-UNPINNED-TRANSITIVES (nueva) | A | 052 (001) | 1 | lock no consumido; Starlette 1.9.0 en un build de hoy |
| E2E-HARNESS-INTERPRETER-FIXED (nueva) | A | 054 | 1 | parcial (alembic de la autoridad central) |


## Actualización 2026-10-20 — normalización de pruebas para la paridad de despliegue

Fuente: `specs/012-auditoria-integral-e2e/spec054-deployment-parity-test-normalization-delta.md`.

| Deuda | Cat. | Estado |
|---|---|---|
| DEPLOYMENT-PARITY-TEST-INCOMPATIBILITIES | — | **CLOSED / CONVERGED** (V0 y V2 en verde; producto sin cambio) |
| FASTAPI-YIELD-TEARDOWN-AFTER-RESPONSE | G (recomendada) | recomendada NOT_A_DEFECT / ACCEPTED_FRAMEWORK_SEMANTIC; pendiente de cierre formal |
| CERTIFICATION-ENVIRONMENT-DEPENDENCY-DRIFT | F | V2 verde; espera las deudas de artefacto y la canonicalización |
| PRODUCTION-BASE-IMAGE-FLOATING-TAG (nueva) | A | `python:3.13-slim` sin parche ni digest |

### Orden rederivado de la ingeniería de release (seguridad + reproducibilidad + despliegue + capacidad de certificación)

| # | Deuda | Dueña | Por qué en este puesto | Certificable sin Docker |
|---|---|---|---|---|
| 1 | **PRODUCTION-IMAGE-WITHOUT-LIBMAGIC** | 052 (001, 046) | la imagen rechaza toda carga documental (31 fallos en V1) y es prerrequisito de la evidencia de OBS-09, la deuda de seguridad abierta | la capa Python sí (entorno V1 con el requirements corregido); el paquete de sistema de la imagen, no |
| 2 | PRODUCTION-IMAGE-BUILT-FROM-DEV-STAGE | 052 | se publica la etapa `dev` (`--reload`, pruebas y herramientas dentro): superficie y estabilidad en producción | no (estático sí) |
| 3 | PRODUCTION-DEPENDENCIES-UNPINNED-TRANSITIVES + LOCK-SIN-REPORTLAB-MAGIC | 052 (001) | reproducibilidad: un build de hoy instala Starlette 1.9.0 y no 1.3.1; el lock no se consume | sí (pip con el lock en un entorno V1) |
| 4 | PRODUCTION-BASE-IMAGE-FLOATING-TAG | 052 | reproducibilidad del intérprete y del sistema | no |
| 5 | TEST-MIGRACIONES-VENV-FIJO | 052/054 | las pruebas de migraciones corren con el alembic de V0 | sí |
| 6 | E2E-HARNESS-INTERPRETER-FIXED | 054 | la autoridad central se migra con el alembic de V0 | sí |
| 7 | CANONICALIZE-CERTIFICATION-ENVIRONMENT | 054 | solo cuando 1–6 dejen un artefacto estable y reproducible (OD-CERT-01) | — |

**NEXT_RELEASE_ENGINEERING_DEBT = PRODUCTION-IMAGE-WITHOUT-LIBMAGIC.** Es la única que deja **inservible** una función
de producción en la imagen, y bloquea por sí sola la certificación de OBS-09 (OD-CERT-02). OBS-09 vuelve a prioridad 1
si llega su evidencia.


## Actualización 2026-10-20 — PRODUCTION-IMAGE-WITHOUT-LIBMAGIC implementada

| Deuda | Estado |
|---|---|
| PRODUCTION-IMAGE-WITHOUT-LIBMAGIC | **IMPLEMENTED — IMAGE RUNTIME CERTIFICATION BLOCKED BY ENVIRONMENT** (sin Docker; todo lo demás verde en V0 y V1') |
| OBS-09 · prerrequisito MIME | ya no la bloquea a nivel de dependencias: los ficheros de F01-F04 superan la fase MIME en V1'. La evidencia Docker de OBS-09 puede servir también de evidencia de imagen para cerrar esta deuda |
| LOCK-SIN-REPORTLAB-MAGIC | +1 de deriva: `python-magic` ya está en `requirements.txt` y sigue fuera del lock |

**NEXT_RELEASE_ENGINEERING_DEBT = PRODUCTION-IMAGE-BUILT-FROM-DEV-STAGE.** OBS-09 vuelve a prioridad 1 si llega su
evidencia.

## Actualización 2026-10-20 — PRODUCTION-IMAGE-BUILT-FROM-DEV-STAGE implementada

| Deuda | Estado |
|---|---|
| PRODUCTION-IMAGE-BUILT-FROM-DEV-STAGE | **IMPLEMENTED — IMAGE RUNTIME CERTIFICATION BLOCKED BY ENVIRONMENT**: etapa final `runtime`, `target: runtime` en la publicación, `dev` solo explícita; 14/14 mutaciones; V0 y V1' en verde (SQLite 1900/0/1056 · PostgreSQL 2930/0/26 · E2E 284/0/0) |
| PRODUCTION-IMAGE-CONTAINS-TEST-QUALITY-DEPENDENCIES (nueva) | **OPEN**, F, dueña 052 (apoyo 001): `requirements.txt` instala pytest, httpx, ruff y mypy en `base` y, por tanto, en `runtime` |
| PRODUCTION-IMAGE-WITHOUT-LIBMAGIC | sin cambio (IMPLEMENTED, imagen pendiente); libmagic preservada en `runtime` (M08) |

Orden de ingeniería de release restante:
1. PRODUCTION-DEPENDENCIES-UNPINNED-TRANSITIVES + LOCK-SIN-REPORTLAB-MAGIC (determinar si son una raíz o dos).
2. PRODUCTION-BASE-IMAGE-FLOATING-TAG.
3. TEST-MIGRACIONES-VENV-FIJO.
4. E2E-HARNESS-INTERPRETER-FIXED.
5. CANONICALIZE-CERTIFICATION-ENVIRONMENT.

PRODUCTION-IMAGE-CONTAINS-TEST-QUALITY-DEPENDENCIES se valora con el reparto de requirements del primer paso, sin
absorberla.

**NEXT_RELEASE_ENGINEERING_DEBT = PRODUCTION-DEPENDENCIES-UNPINNED-TRANSITIVES + LOCK-SIN-REPORTLAB-MAGIC.** OBS-09 vuelve a
prioridad 1 si llega su evidencia.

## Actualización 2026-10-20 — conjunto de dependencias de despliegue reproducible

| Deuda | Estado |
|---|---|
| LOCK-SIN-REPORTLAB-MAGIC | **CLOSED / CONVERGED**: el lock se regenera con un comando canónico y determinista, tiene 49 paquetes (con `reportlab` y `python-magic`) y lo protege IDL |
| PRODUCTION-DEPENDENCIES-UNPINNED-TRANSITIVES | **CLOSED / CONVERGED**: la imagen instala el lock con `--no-deps` y `pip check`; V3 freeze = lock; V0 y V3 en verde (SQLite 1907/0/1056 · PostgreSQL 2937/0/26 · E2E 284/0/0) |
| IMAGE-INSTALLED-DEPENDENCY-SET-NOT-RUNTIME-CERTIFIED (nueva) | **BLOCKED BY ENVIRONMENT**, puerta externa |
| BACKEND-DIRECT-DEPENDENCIES-KNOWN-VULNERABILITIES (nueva) | **OPEN**, seguridad, dueña 001: PyJWT 2.13.0 y cryptography 46.0.6 con avisos publicados después de `cve-review.md` |
| LOCK-WITHOUT-ARTIFACT-HASHES (nueva) | **OPEN**, menor, dueña 052 |
| CERTIFICATION-ENVIRONMENT-DEPENDENCY-DRIFT | sigue OPEN hasta la canonicalización; V3 ya es el entorno de despliegue fijado por el lock |

**ROOT_COUNT = 2** (lock sin mecanismo frente a imagen sin lock), con implementación común.

Orden de ingeniería de release restante:
1. PRODUCTION-BASE-IMAGE-FLOATING-TAG.
2. TEST-MIGRACIONES-VENV-FIJO.
3. E2E-HARNESS-INTERPRETER-FIXED.
4. PRODUCTION-IMAGE-CONTAINS-TEST-QUALITY-DEPENDENCIES.
5. CANONICALIZE-CERTIFICATION-ENVIRONMENT.

**BACKEND-DIRECT-DEPENDENCIES-KNOWN-VULNERABILITIES es una deuda de seguridad.** Se propone a la dueña adelantarla
como siguiente ciclo técnico. Su decisión de prioridad es de la dueña; el ciclo no la reordena por su cuenta.

**NEXT_RELEASE_ENGINEERING_DEBT = PRODUCTION-BASE-IMAGE-FLOATING-TAG.** OBS-09 tiene prioridad 1 si llega su evidencia.

## Actualización 2026-10-20 — dependencias directas de autenticación y criptografía sin vulnerabilidades conocidas

| Deuda | Estado |
|---|---|
| BACKEND-DIRECT-DEPENDENCIES-KNOWN-VULNERABILITIES | **CLOSED / CONVERGED**: PyJWT 2.15.0 y cryptography 50.0.2; pip-audit en 0; V0 y V4 en verde (SQLite 1921/0/1056 · PostgreSQL 2951/0/26 · E2E 284/0/0) |
| CRYPTO-KEY-LOADING-UNSUPPORTED-ALGORITHM-UNWRAPPED (nueva) | **OPEN**, menor, previa, de entrada de operador, falla cerrado; dueña 010 |
| PRODUCTION-BASE-IMAGE-FLOATING-TAG | OPEN; aplazada un ciclo por OD-SEC-01 y ahora siguiente |

Orden de ingeniería de release:
1. PRODUCTION-BASE-IMAGE-FLOATING-TAG.
2. TEST-MIGRACIONES-VENV-FIJO.
3. E2E-HARNESS-INTERPRETER-FIXED.
4. PRODUCTION-IMAGE-CONTAINS-TEST-QUALITY-DEPENDENCIES.
5. CANONICALIZE-CERTIFICATION-ENVIRONMENT.

**NEXT_RELEASE_ENGINEERING_DEBT = PRODUCTION-BASE-IMAGE-FLOATING-TAG.** OBS-09 tiene prioridad 1 si llega su evidencia.

## Actualización 2026-10-21 — PRODUCTION-BASE-IMAGE-FLOATING-TAG: decisión de la dueña requerida

| Deuda | Estado |
|---|---|
| PRODUCTION-BASE-IMAGE-FLOATING-TAG | **BLOCKED BY OWNER DECISION — MATERIAL_OQ**. Ningún candidato cumple a la vez CPYTHON_MATCH = 1 y no tener bloqueante de seguridad. Recomendada B: `python:3.13.16-slim-trixie@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f` más recertificación V5 con CPython 3.13.16 |
| CERTIFICATION-ENVIRONMENT-DEPENDENCY-DRIFT | **hallazgo nuevo**: lo desplegado (3.13.16) ya no coincide con el intérprete certificado (3.13.15) |

**NEXT_RELEASE_ENGINEERING_DEBT = PRODUCTION-BASE-IMAGE-FLOATING-TAG** (pendiente de la decisión OD-CERT-07).

Si la dueña elige B, ese ciclo implementa el `FROM` y recertifica en V5. Después sigue TEST-MIGRACIONES-VENV-FIJO.

## Actualización 2026-10-21 (2) — OD-CERT-07 = B: bloqueante de seguridad en el candidato

| Deuda | Estado |
|---|---|
| PRODUCTION-BASE-IMAGE-FLOATING-TAG | **BLOCKED BY OWNER DECISION — OD-CERT-08**. B revalidado sin cambios, pero su almacén de CA contiene las raíces retiradas por DSA-6572-1. Recomendada R1: B + `ca-certificates=20250419+deb13u1` explícito |
| BASE-IMAGE-CA-STORE-DSA-6572 (nueva) | **OPEN**, seguridad, aplicable al TLS de licencias; también afecta a lo que produce hoy la etiqueta flotante |
| PRODUCTION-IMAGE-APT-PACKAGES-UNPINNED (nueva) | OPEN, menor, observación |

**NEXT_RELEASE_ENGINEERING_DEBT = PRODUCTION-BASE-IMAGE-FLOATING-TAG con OD-CERT-08.**

## Actualización 2026-10-21 (3) — base fijada y almacén de CA corregido

| Deuda | Estado |
|---|---|
| BASE-IMAGE-CA-STORE-DSA-6572 | **CLOSED / CONVERGED** (`ca-certificates=20250419+deb13u1`, verificado) |
| PRODUCTION-BASE-IMAGE-FLOATING-TAG | **IMPLEMENTED**: fijada `python:3.13.16-slim-trixie@sha256:70729b46…`; V5 IMAGE_ROOTFS verde; cierre pendiente de LOCK-CERTIFI-PYSEC-2026-4320 |
| LOCK-CERTIFI-PYSEC-2026-4320 (nueva) | OPEN; aplicabilidad 0 medida; requiere mover el corte del lock |
| BASE-IMAGE-RUNTIME-CONTENTS-NOT-CERTIFIED | puerta externa (Docker) |

**Línea base vigente de compatibilidad del intérprete de despliegue: V5** (CPython 3.13.16 de la imagen). V4 queda
histórica.

**NEXT_RELEASE_ENGINEERING_DEBT = LOCK-CERTIFI-PYSEC-2026-4320.** Es un ciclo corto y cierra a la vez la base. Después:
1. TEST-MIGRACIONES-VENV-FIJO.
2. E2E-HARNESS-INTERPRETER-FIXED.
3. PRODUCTION-IMAGE-CONTAINS-TEST-QUALITY-DEPENDENCIES.
4. CANONICALIZE-CERTIFICATION-ENVIRONMENT.

## Actualización 2026-10-21 (4) — certifi corregido en el lock; base de imagen cerrada

| Deuda | Estado |
|---|---|
| LOCK-CERTIFI-PYSEC-2026-4320 | **CLOSED / CONVERGED** (corte +8655,073 s; solo certifi; pip-audit 0) |
| PRODUCTION-BASE-IMAGE-FLOATING-TAG | **CLOSED / CONVERGED** |
| BASE-IMAGE-CA-STORE-DSA-6572 | CLOSED / CONVERGED |
| TEST-DOCUMENTS-CATALOG-ORDER-DEPENDENT (nueva) | OPEN, menor, previa |
| BASE-IMAGE-UPSTREAM-REBUILD-REPIN (nueva) | OPEN, oportunidad: volver a fijar en `cf50a4f6…` y retirar el pin de CA |

**Línea base vigente:** V0 y V5 con SQLite 1928/0/1056, PostgreSQL 2958/0/26, E2E 284/0/0 y pip-audit 0.

**NEXT_RELEASE_ENGINEERING_DEBT = TEST-MIGRACIONES-VENV-FIJO.** Orden posterior:
1. E2E-HARNESS-INTERPRETER-FIXED.
2. PRODUCTION-IMAGE-CONTAINS-TEST-QUALITY-DEPENDENCIES.
3. CANONICALIZE-CERTIFICATION-ENVIRONMENT.

BASE-IMAGE-UPSTREAM-REBUILD-REPIN se puede intercalar cuando la dueña lo decida. OBS-09 tiene prioridad 1 si llega su
evidencia.

## Actualización 2026-10-22 — alembic y arnés E2E con el intérprete que certifica

| Deuda | Estado |
|---|---|
| TEST-MIGRACIONES-VENV-FIJO | **CLOSED / CONVERGED** (0 rutas `.venv` en `tests/**`; sin `.venv` 140/0/0; migración hija en V5 = 3.13.16) |
| E2E-HARNESS-INTERPRETER-FIXED | **CLOSED / CONVERGED** (procedencia medida en el manifiesto; paridad 1 en V0 y en V5) |
| E2E-LICENSE-REVISION-ENVIRONMENT-LATENCY (nueva) | OPEN, menor: margen de ≈ 1,7× ante degradación del anfitrión; ENVIRONMENT, sin cambio de timeout |
| E2E-SPECS-PYTHON-HELPERS-VENV-FIXED (nueva) | OPEN, menor: 12 sitios `.venv/bin/python` en `e2e/*.ts` |
| TEST-MIGRATION-MODULES-ORDER-DEPENDENT · TEST-DOCUMENTS-CATALOG-ORDER-DEPENDENT | OPEN, previas, no tocadas |

**Línea base vigente:**
- V0: SQLite 1956/0/1062;
- V5: SQLite 1956/0/1062 y PostgreSQL 2992/0/26;
- E2E 284/0/0 en V0 y en V5, con paridad de intérprete medida;
- pip-audit 0/0; OpenAPI 544/533/11.

**NEXT_RELEASE_ENGINEERING_DEBT = PRODUCTION-IMAGE-CONTAINS-TEST-QUALITY-DEPENDENCIES.** Después:
1. CANONICALIZE-CERTIFICATION-ENVIRONMENT.

Quedan aparte:
- OBS-09: prioridad 1 automática si llega la evidencia Docker externa;
- BASE-IMAGE-UPSTREAM-REBUILD-REPIN: DEFERRED / NON-BLOCKING.

## Actualización 2026-10-23 — los ayudantes Python de las E2E corren con el intérprete que se certifica

| Deuda | Estado |
|---|---|
| E2E-SPECS-PYTHON-HELPERS-VENV-FIXED | **CLOSED / CONVERGED** (12 sitios → 0; lanzador central `e2e/helpers/python.ts` con `KONTROL_E2E_PYTHON` exportado por el arnés; ayudantes en V5 = 3.13.16, 113 de 113, medido) |
| E2E-LICENSE-REVISION-ENVIRONMENT-LATENCY | OPEN, menor, sin absorber. Recurrió con contención del anfitrión y alcanzó a las cargas con `clamscan`; candidata a ampliarse a una deuda de margen E2E ante contención del anfitrión |

**Línea base vigente:**
- SQLite V0 y V5: 1956/0/1064;
- PostgreSQL V5: 2994/0/26;
- E2E 284/0/0 en V0 y en V5, con paridad de arnés, migración y ayudantes = 1;
- pip-audit 0/0; OpenAPI 544/533/11.

**NEXT_RELEASE_ENGINEERING_DEBT = PRODUCTION-IMAGE-CONTAINS-TEST-QUALITY-DEPENDENCIES.** Después:
1. CANONICALIZE-CERTIFICATION-ENVIRONMENT.
2. Reevaluar la puerta de inicio de Gobierno.

Quedan aparte:
- OBS-09: prioridad 1 si llega la evidencia Docker;
- BASE-IMAGE-UPSTREAM-REBUILD-REPIN: DEFERRED / NON-BLOCKING.

## Actualización 2026-10-24 — la imagen de producción ya no lleva herramientas de prueba ni de calidad

| Deuda | Estado |
|---|---|
| PRODUCTION-IMAGE-CONTAINS-TEST-QUALITY-DEPENDENCIES | **CLOSED / CONVERGED**: runtime 38 paquetes (sin pytest, httpx, ruff, mypy ni sus 7 transitivas exclusivas); certificación 49 = runtime exacto + herramientas (`--constraint requirements.lock`, mismo corte); `dev` instala el lock de certificación fijado |
| PRODUCT-OPTIONAL-S3-PROVIDER-DEPENDENCY-UNDECLARED (nueva) | OPEN, dueña 046: el proveedor S3 opcional depende de `boto3`, que no está en ningún lock; decisión de producto |
| E2E-FLAKY-BAJO-CARGA | recurrió en `route-crawl.spec.ts:28` (4 rutas de menú) en una E2E V0 que se invalidó por el entorno (1,12 M páginas escritas en swap durante la corrida) |

**Modelo vigente de certificación:**
- **V6R:** runtime puro, el de producción;
- **V6C:** V6R exacto + herramientas;
- las E2E V6 arrancan el producto en V6R (`--python-de-producto`) y el arnés y los ayudantes en V6C.

**Línea base:**
- SQLite V0 y V6C: 1965/0/1070;
- PostgreSQL V6C: 3009/0/26;
- E2E 284/0/0 en V0 y en V6;
- OpenAPI 544/533/11;
- pip-audit 0/0 en los dos locks.

**NEXT_RELEASE_ENGINEERING_DEBT = CANONICALIZE-CERTIFICATION-ENVIRONMENT.** Después, la GOVERNMENT-START-READINESS GATE.

Quedan aparte:
- OBS-09: prioridad 1 si llega la evidencia Docker (que además certificaría el contenido exacto de la imagen);
- BASE-IMAGE-UPSTREAM-REBUILD-REPIN: DEFERRED / NON-BLOCKING.

## Actualización 2026-10-25 — orden canónica de certificación implementada; corrida oficial pendiente de anfitrión

Decisión de la dueña **OD-CERT-30**: se confirma en develop la implementación de SPEC054 como **IMPLEMENTED —
CERTIFICATION PENDING (dedicated host)**, sin marcarla como cerrada, y se abre SPEC046 S3. El cierre de SPEC054 llegará con la
primera corrida oficial con RC 0 en un anfitrión dedicado, que certificará también el trabajo posterior (el hash del árbol cubre
todo lo que haya en ese momento).

| Deuda | Estado |
|---|---|
| CANONICALIZE-CERTIFICATION-ENVIRONMENT | **IMPLEMENTED — CERTIFICATION PENDING**: `python3 qa/certificar-release.py` (V6R/V6C, 15 etapas, RC 0/1/3/4/70); 8 corridas en la estación multiproyecto: el producto en verde, pero la validez posterior (memoria) las invalida → OD-CERT-27 = A (entorno dedicado) |
| CERTIFICATION-HOST-PORTABILITY (G1–G4) | **CLOSED / CONVERGED**: workers 6 y retries 0 fijos; política de entorno v1; PostgreSQL de QA fijado (`qa/postgres_qa.json`, sin `.venv`); árbol certificado ligado al hash v2 |
| CERTIFICATION-HOST-INFRASTRUCTURE (nueva) | **BLOCKED_BY_PROVIDER_ACCESS**: no hay anfitrión dedicado ni cuenta cloud. Requisitos: Debian 13 amd64, 12 CPU lógicas o más, 16–24 GB, 25–50 GB SSD, swap ≥ 4 GiB |
| E2E-RESULT-MANIFEST-POST-VALIDITY-SEMANTICS (nueva) | OPEN, no bloqueante: si la validez posterior invalida la etapa 90, el manifiesto deja `E2E_RESULT = NOT_RUN` aunque la suite pase |
| PG-MIGRATION-VALIDATION-VENV (nueva) | OPEN, no canónica: `qa/pg-migration-validation.sh` sigue tomando PostgreSQL del `.venv` |

**NEXT TECHNICAL CYCLE = SPEC046 S3-UNSUPPORTED-CONFIGURATION-FAIL-CLOSED** (implementación y pruebas en la estación; la
certificación oficial queda pendiente del anfitrión). Después, GOVERNMENT-START-READINESS.

## Actualización 2026-10-25 — SPEC046 S3-UNSUPPORTED-CONFIGURATION-FAIL-CLOSED

| Deuda | Estado |
|---|---|
| PRODUCT-OPTIONAL-S3-PROVIDER-DEPENDENCY-UNDECLARED | **CLOSED — NOT_SUPPORTED_BY_PRODUCT_BASELINE / CONFIGURATION_GUARDED**: el adaptador S3 se retiró (OD-S3-01); el producto ya no importa `boto3`; `OPCIONALES_DEL_PRODUCTO` está vacío |
| DEUDA-046-1 | **CLOSED por retirada** |

S3_PROVIDER_SUPPORTED = 0; S3_CONFIGURATION_GUARDED = 1. La certificación oficial queda pendiente del anfitrión dedicado
(OD-CERT-30), junto con la de SPEC054.

**NEXT TECHNICAL CYCLE = GOVERNMENT-START-READINESS.**

## Actualización 2026-10-25 — GOVERNMENT-START-READINESS

Informe: `docs/roadmap/government-start-readiness.md`. **GOVERNMENT_START_READINESS = BLOCKED**:
- falta el RC 0 oficial de SPEC054;
- las fuentes siguen en SPONSOR REVIEW, con D-GOV-01..08 abiertas y el freeze en 0/10;
- hay 7 gaps P0 del núcleo compartido frente a los RNF de Gobierno (MFA, techo de delegación, zona America/Caracas, catálogo de auditoría, errores deterministas, verificación de restauración y aislamiento por ente).

Paquete de preguntas a la dueña: OQ-GSR-1..3. No se crea ninguna Spec de Gobierno.

Decisiones 2026-10-25: OD-GSR-1 = B (ARCHITECTURE-BASELINE solo como planificación) y OD-GSR-2 = A (endurecer el núcleo antes de GOV-0). Valores D aprobados: delegación «solo permisos que el actor posee», zona America/Caracas, 422 ante parámetros no declarados, catálogo de eventos 006/051 y rechazo de análisis auditado en sesión independiente. Detalle en `government-start-readiness.md`.

## Actualización 2026-10-25 — GOVERNMENT-ARCHITECTURE-BASELINE

`docs/roadmap/government-architecture-baseline.md` queda **CLOSED / PLANNING_BASELINE**, con GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0.

Contiene:
- mapa de contextos, modelo organizativo y contratos de alcance (tenant, organización y autoridad);
- contratos de auditoría y políticas de flujo, campos, concurrencia, numeración, tiempo y dinero;
- **SHARED_CORE_HARDENING_DEPENDENCY_MAP** con los 7 gaps;
- paquete D-GOV para el sponsor y checklist de freeze (0/10).

Preguntas a la dueña: OQ-GAB-1..3 (forma de entrega, MFA y sesión, inmutabilidad de la auditoría).

**NEXT TECHNICAL CYCLE = SHARED-CORE-GOVERNMENT-P0-HARDENING**, que empieza por MFA (002/003).

### Actualización 2026-10-25 — SHARED-CORE-P0-HARDENING-01 (MFA, gap n.º 1): diseño cerrado, bloqueado por decisión

`specs/001-fundacion/spec002-mfa-privileged-roles-delta.md` (dueñas 002 y 003; alojada en 001 porque OBS-04 sigue abierta) queda
**DESIGN COMPLETE — BLOCKED_BY_OWNER_DECISION**. Contiene:
- descubrimiento medido;
- requisitos A–M;
- 24 amenazas, cada una con su control y su prueba;
- política por capacidades;
- modelo de datos (`0058`), cifrado con anillo `KONTROL_MFA_KEYS`, API, auditoría, UX con los 15 estados y accesibilidad;
- gate y trazabilidad.

Hallazgos nuevos en el alcance:
- F1: el access token no se liga a la sesión;
- F2: cambiar o restablecer la contraseña no revoca las sesiones;
- F3: `mfa_enabled` no tiene dueño.

Hallazgo registrado fuera del alcance: F4, `login_rate_limit_per_minute` es configuración muerta (DT-16 / Spec 055).

Preguntas a la dueña:
- OQ-MFA-1: alcance obligatorio de la política;
- OQ-MFA-2: QR (dependencia nueva);
- OQ-MFA-3: arnés de pruebas frente a la antirrepetición.

DEEPSEEK CALLS = 0.

## Actualización 2026-11-06 — reconciliación Enterprise (P2, solo lectura)

Vista por línea de producto en `enterprise-baseline/`. Esta matriz sigue siendo la autoridad de cada deuda. Ninguna deuda se cierra ni se reabre.

Hallazgos nuevos, sin corregir: KONTROL-PY-UPDATE-NO-OP (MEDIUM propuesta), DOC-ESTADO-OBSOLETO-TRAS-HARDENING (LOW), ORCH-READINESS-FALSO-NEGATIVO (LOW) y ESTACION-SIN-CREDENCIAL-GIT (operativo). Detalle en `enterprise-baseline/ENTERPRISE_BASELINE_CURRENT.md` §9.

## Actualización 2026-11-06 (2) — prerrequisitos de T052

| Deuda | Estado |
|---|---|
| T052_PREREQUISITE_AUDIT_TRUTHFULNESS (BACKUP-MANUAL-AUDIT-ANTES-DE-VERIFY) | OPEN, prerrequisito de T052 por decisión de la dueña: `create` registra semántica de copia verificada antes de `verify` |
| BACKUP-PG-TOOLS-IN-OPS-IMAGE (T053) | OPEN, prerrequisito de T052: `T053_REQUIRED_FOR_T052 = 1` |
| RESTORE-DRILL-PERIODIC (nueva, propuesta) | OPEN: DOC-05 §11 pide prueba mensual y ejercicio trimestral de restauración |

## Actualización 2026-11-07 — defecto de arranque con el lock de producción

| Deuda | Estado |
|---|---|
| RUNTIME-LOCK-API-BOOT-FAILURE (nueva) | OPEN · P0 · SHARED_CORE · dueña 001/052: con `requirements.lock`, `import app.main` falla por `get_flat_dependant` en `app/core/query_contract.py`. Evidencia: `specs/001-fundacion/evidence/backup-rpo/RUNTIME_BOOT_DEFECT.md` |
| T052-A1 | BLOCKED: 2 reintentos semánticos agotados, nada aplicado. `specs/001-fundacion/evidence/backup-rpo/ATTEMPT_LOG.md` |

## Actualización 2026-11-07 (2) — arranque corregido en local, catálogo de operaciones abierto

| Deuda | Estado |
|---|---|
| RUNTIME-LOCK-API-BOOT-FAILURE | Contrato de consulta corregido en el árbol local, sin commit: arranque y 422 verificados con el lock |
| RUNTIME-LOCK-OPERATIONS-CATALOG-EMPTY (nueva) | OPEN · P0 · SHARED_CORE: `app/core/operaciones.py` recorre `app.routes` y con el lock devuelve 1 operación. Misma causa de inclusión perezosa, fuera de las rutas del ciclo. Afecta además a `qa/fixtures_de_frontend.py` y a guardas de pruebas |
| ENTORNO-SIN-ANALIZADOR-P2 (nueva) | Este puesto no tiene ClamAV: las pruebas documentales fallan con `SCAN_FAILED` |

## Actualización 2026-11-07 (3) — P0 de runtime certificados en local

| Deuda | Estado |
|---|---|
| RUNTIME-LOCK-API-BOOT-FAILURE | **FIXED** en local, sin publicar. Arranque y contrato estricto verificados con el lock |
| RUNTIME-LOCK-OPERATIONS-CATALOG-EMPTY | **FIXED** en local, sin publicar. Catálogo de 688 operaciones, una sola visión de rutas en `app/core/route_contexts.py` |
| ENTORNO-SIN-ANALIZADOR-P2 | **CLOSED**: `qa/clamav_qa.py provisionar` RC 0; suite SQLite con analizador real sin fallos |
| ISO-BARRIDOS-SIN-EJECUTAR-EN-RUNTIME (nueva) | OPEN · HIGH propuesta · SHARED_CORE · T061: los barridos de aislamiento de `test_iso_barridos.py` corrían en vacío con este runtime. Ya recorren las 613 rutas de empresa, pero solo se ejecutan en PostgreSQL, que este puesto no tiene. Sin ejecutar **no hay evidencia de aislamiento vigente en este runtime** |
| CATALOGO-CACHE-POR-ID (nueva) | OPEN · LOW: `_CATALOGOS` se indexa con `id(app)`; una app destruida puede ceder su `id`. Solo afecta a procesos con varias apps, como las pruebas |

## Actualización 2026-11-07 (4) — T052 implementada en local

| Deuda | Estado |
|---|---|
| BACKUP-SCHEDULE-RPO | **BLOCKED_BY_EXTERNAL_CERTIFICATION_GATES**: implementación local completa, certificación no PostgreSQL en verde. Faltan PostgreSQL, copia real, destino fuera del anfitrión, capacidad, E2E y publicación |
| BACKUP-PG-TOOLS-IN-OPS-IMAGE | Implementada; `T053_RUNTIME_CERTIFIED = NO`, sin Docker |
| ISO-BARRIDOS-SIN-EJECUTAR-EN-RUNTIME | **Reclasificada: `CERTIFICATION_GAP_NOT_YET_PROVEN_DEFECT`, T061**. No es un defecto demostrado. Debe correr primero cuando exista PostgreSQL |
| T052-A1-CLI-AUDIT-TEST (nueva) | OPEN · LOW propuesta: `audit_backup_event` por CLI sin prueba dirigida; `BLOCKED_BY_RETRY_POLICY` |
| RESTORE-LEDGER-RESET (nueva) | OPEN · MEDIUM propuesta: el ledger no se reinicia tras `restore`; exige tocar `backup_restore.py` |

## Actualización 2026-11-07 (5) — selectores de almacén

| Deuda | Estado |
|---|---|
| ALMACENES-DESPLEGABLES-TRUNCADOS | **`TECHNICAL_FIX_COMPLETE_LOCAL / FULL_RUNTIME_E2E_PENDING`**, sin publicar: E2E pendiente de PostgreSQL. Evidencia: `specs/008-almacenes-fisicos/evidence/almacenes-desplegables/` |
| RECEPCION-ALMACEN-TEXTO-LIBRE (nueva) | OPEN · MEDIUM propuesta · dueña compras: `RecepcionesPage` pide el almacén como identificador escrito a mano |
| ALMACENES-LISTADO-PRIMERA-PAGINA (nueva) | OPEN · LOW propuesta · 008: la tabla de Almacenes muestra los 50 primeros; se alcanzan por búsqueda. Relacionada con ALMACENES-PAGINACION-LIMIT-OFFSET |

## Actualización 2026-11-07 (6) — almacén de la recepción

| Deuda | Estado |
|---|---|
| RECEPCION-ALMACEN-TEXTO-LIBRE | **`TECHNICAL_FIX_COMPLETE_LOCAL / FULL_RUNTIME_E2E_PENDING`**, sin publicar. Evidencia: `specs/004-compras-cuentas-por-pagar/evidence/recepcion-almacen/` |
| RECEPCION-LINEA-ORDEN-TEXTO-LIBRE (nueva) | OPEN · HIGH propuesta · 004/019: recibir una línea exige escribir su identificador; **bloquea la recepción por interfaz** |
| IDENTIFICADORES-EN-TEXTO-LIBRE (nueva) | OPEN · POSSIBLE_DEFECT: Facturas en Devoluciones y Notas, Artículo en Listas de precio, Proveedor en Lotes, Producto en Valorización. Inventario en `FREE_TEXT_INTERNAL_ID_INVENTORY.md` |
| RECEPCION-ALMACEN-INACTIVO-ACEPTADO (nueva) | OPEN · POSSIBLE_DEFECT: `create_receipt` no comprueba el estado del almacén; decide la Spec 008 |
