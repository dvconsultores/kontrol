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
| DT-11 | F | registro original | 0 | Spec 053 sin iniciar; exige entorno de despliegue (Docker) |
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
| AUDITORIA-PANTALLA-DUPLICADA | D | 012 | 0 | ¿unificar o renombrar las dos pantallas? |
| MOVTYPE-GLOBAL-SIN-UNICIDAD | D | 023 | 0 | ¿pueden dos tipos globales compartir código? |
| SEED-EMPRESA-CODIGO-NO-UNICO | D | 007 | 0 | ¿el código de empresa identifica o etiqueta? |
| DOCUMENT-ARCHIVE-LOST-UPDATE-DURING-UPLOAD | D | 046 | 0 | ¿qué ocurre si se archiva un documento mientras su carga está en análisis? A) 409 al persistir con revalidación/bloqueo de fila (recomendada) · B) permitir versión sin reactivar · C) bloquear el archivado durante la carga |
| DOCUMENT-DELETE-DURING-UPLOAD-ORPHAN-500 | D | 046 | 0 | ¿qué responde una carga cuyo documento se eliminó durante el análisis? A) 404 DOCUMENT_NOT_FOUND + limpiar binario (recomendada) · B) 409 DOCUMENT_DELETED + limpiar · C) 404 y limpieza diferida |
| DOCUMENT-SCAN-REJECTION-AUDIT-NOT-PERSISTED | D | 046 (con 001) | 0 | ¿debe persistir DOCUMENT_SCAN_REJECTED aunque la carga termine en 422? A) sesión independiente · B) commit explícito antes del 422 (recomendada) · C) aceptar que no persista |
| ALMACENES-PAGINACION-LIMIT-OFFSET | D | 008 | 0 | ¿renombrar al canon page/page_size (rompe 12 pantallas y 10 suites)? |
| OBS-04 · SPEC-SEGURIDAD-SIN-CARPETA | D | inventario | 0 | ¿se crea la carpeta o se reasigna en el inventario? |
| WAREHOUSE-CROSS-COMPANY-FILAS-EXISTENTES | D | 008 | 0 | ¿se autoriza una consulta de solo lectura por instalación (y, si aparecen, una reparación)? |
| WAREHOUSE-BRANCH-ALCANCE-DE-USUARIO (branch_ids) | D | 008 | 0 | ¿debe el alcance de sucursales del usuario limitar las sucursales de almacén? |
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

### DT-11 — BLOCKED_BY_DEPENDENCY
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
