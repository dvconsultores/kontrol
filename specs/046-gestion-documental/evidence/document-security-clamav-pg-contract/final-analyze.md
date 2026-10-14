# `/speckit.analyze` final

| Métrica | Valor |
|---|---|
| CLAMAV_REQUIREMENT_AMBIGUOUS | 0 (documentado: configurable por Spec; requerido de facto por la certificación; decisión de QA pendiente de la dueña, no ambigua) |
| SCANNER_BYPASS · MISSING_SCANNER_TREATED_AS_CLEAN · MALWARE_TEST_DISABLED_WITHOUT_REPLACEMENT | 0 · 0 · 0 (DOCENV-14/15; EICAR intactas) |
| DOCUMENT_RACE_ENGINE_AMBIGUITY · PG_SQL_EXECUTED_ON_SQLITE · PG_ONLY_TEST_WITHOUT_REASON | 0 · 0 · 0 (marcador con razón y autoridad; omisión verificada) |
| SQLITE_DOCUMENT_COVERAGE_REMOVED_SILENTLY | 0 (9 nodos omitidos con razón; ≥ 25 pruebas no concurrentes siguen) |
| REAL_SCANNER_INTEGRATION_MISSING | **sí, declarado** (bloqueado por decisión de la dueña) |
| CLAMAV_SKIP_MISCLASSIFIED | 0 (inventario corregido: 7 de `legacy_import` → OBS-10) |
| SCAN_FAILED_CONTRACT · TENANT_ISOLATION · DOCUMENT_VERSION_RACE regresiones | 0 · 0 · 0 (producto 0; aserciones intactas) |
| PRODUCT_CHANGE · MIGRATION_ADDED · SCHEMA_CHANGE | 0 · 0 · 0 |
| AUTH_ROTATION · WAREHOUSE · UOM · MOTOR_PARA_HILOS · PGLIFE · PG_SCHEMA · INSTALLATION_VOLUME · LISTADOS · E2E_HELPER · OPENAPI · LICENSING · CENTRAL_SYNC · PICKLIST_409 · KEEPALIVE_75 · VERSION_PANEL regresiones | 0 (suites idénticas a la base salvo las omisiones y +7; OpenAPI y E2E sin cambio) |
| PRODUCTION_502_SCOPE_EXPANSION · SPEC057_STARTED · NEXT_MASTER_SPEC_SELECTED · SECRET_EXPOSURE | 0 · 0 · 0 · 0 |
| BLOCKER | 0 para OBS-08 · **1** para ENTORNO-SIN-CLAMSCAN (decisión de la dueña, declarada) |
| CRITICAL · CONTRADICTIONS · OWNER CONFLICT · ORPHAN REQ · ORPHAN TASKS · UNKNOWN | 0 ×6 |
| MATERIAL OQ | 0 para OBS-08 · 1 para ENTORNO (abierta a la dueña) |
| TRACEABILITY | 100 % |
