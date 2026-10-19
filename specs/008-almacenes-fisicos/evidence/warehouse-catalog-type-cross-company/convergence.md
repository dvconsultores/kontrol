# `/speckit.converge` · WAREHOUSE-CATALOG-TYPE-CROSS-COMPANY — final analyze
| Campo | Valor |
|---|---|
| ROUTE_SELECTED | C (dedicada); la E2E se ejecutó al volverse apto el equipo |
| CATALOG_DEFECT_REPRODUCED · ROOT_CAUSE_PROVEN · OWNER_SPEC_CONFIRMED · CONTRACT_CONFIRMED · OWNER_DECISION_REQUIRED · SCOPE_BOUNDED | 1 · 1 · 1 (008) · 1 (ADR-D0-014) · 0 · 1 |
| LOCATION_TYPE_CREATE / BULK / PATCH_FIXED · ZONE_TYPE_CREATE / PATCH_FIXED | 1 / 1 / 1 · 1 / 1 |
| CROSS_COMPANY_LOCATION_TYPE before → after · CROSS_COMPANY_ZONE_TYPE · CROSS_TENANT_TYPE_AFTER · NONEXISTENT_TYPE_AFTER | 200 → 404 · 200 → 404 · 404 · 404 idéntico |
| MULTI_COMPANY_LEAK before → after | 1 → 0 |
| OBS01_TESTS_ADAPTED · OBS01_CONTRACT_PRESERVED · WAREHOUSE_BRANCH_DIRECTED_REGRESSION | 3 (monkeypatch, sin cambiar aserciones) · 1 · 0 |
| DIRECTED total / pass / fail / skip | 28 / 28 / 0 / 0, ×2 motores |
| MUTATIONS meaningful / killed / survived / equivalent | 17 / 17 / 0 / 0 |
| SQLITE_RUN1 · RUN2 · POSTGRES_RUN · OPENAPI | 1859/0/1046 · 1859/0/1046 · 2879/0/26 · 544/533/11 |
| E2E_RESULT · E2E_ENVIRONMENT_SUITABLE | 273/7 + 4 sin ejecutar (firma ambiental nueva, no atribuible) · 1 al empezar, paginación durante la corrida |
| PRODUCT_CHANGE · TEST_CHANGE | 1 fichero · 1 nuevo + O01-07/08/09 |
| MIGRATION · SCHEMA · OPENAPI · TIMEOUT · BUSY_TIMEOUT · RETRY · SLEEP · SKIP · XFAIL · REORDER · PARALLEL | 0 · 0 · 0 · 0 · 0 · 0 · 0 · 0 · 0 · 0 · 0 |
| OTHER_DEBT_ABSORBED · regresiones OBS-01/09/07/06/12/otras | 0 · 0/0/0/0/0/0 |
| DEEPSEEK tasks · briefs · calls · retries · audit failures | 3 · 4 · 4 · 1 (después, reclasificación) · 2 |
| SPEC057 · NEXT_MASTER_SPEC · SECRET_EXPOSURE · PRODUCTION_TOUCHED | 0 · 0 · 0 · 0 |
| BLOCKER | 1 — E2E no verde (EXTERNAL_ENVIRONMENT · HOST_PAGING_BURST) |
| CRITICAL · CONTRADICTIONS · MATERIAL_OQ · UNKNOWN · TRACEABILITY | 0 · 0 · 0 · 0 · 100 % |
**IMPLEMENTED — E2E CERTIFICATION BLOCKED BY ENVIRONMENT.** Para cerrar: una E2E verde, 284/0/0, con el equipo estable
durante toda la corrida. Esa misma corrida cierra también WAREHOUSE-BRANCH-CROSS-COMPANY, porque está en el mismo árbol.
