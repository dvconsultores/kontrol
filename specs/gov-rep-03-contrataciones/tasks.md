# Tasks · REP-03

Tope del ciclo: 8 llamadas (política §6). Reintentos: 2 por subproblema real.

| Id | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN | TRAZA |
|---|---|---|---|---|---|---|---|---|---|---|
| T001 ✔ | Reconciliación, métricas, candidatos, matriz de desbloqueo y selección | CLAUDE | n-a | no | n-a | 0 | — | recálculo | REP-03 elegido; P0 = 0 elegibles; N37 BLOCKED_EXTERNAL_SOURCE | §11-§17 del encargo |
| T002 ✔ | Spec y plan con la compuerta | CLAUDE | n-a | no | n-a | 0 | specs/gov-rep-03-contrataciones/* | revisión | CONSTITUTION_GATE PASS | FR-01..10, AC-01..06 |
| T003 ✔ | R1 backend: servicio, API, main, catálogo y pruebas PG | DEEPSEEK | deepseek-v4-pro | sí (aislamiento) | sí | 2 | service/api_reporte_contrataciones.py, main.py, audit_catalog_entries.py, test_audit_catalog_backup.py, test_gov_rep03_contrataciones.py | pytest PG; ruff; mypy | 1.ª llamada vacía («Traceback»); la 2.ª aplicada salvo el catálogo | FR-02..10 |
| T004 ✔ | C1 corrección del backend (tipos, CSV, record_audit, catálogo, pruebas) | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | servicio, pruebas, catálogo | PG 18/19 | Verde salvo 2 restos → C2 | AC-01..05 |
| T005 ✔ | R2 frontend: pantalla, Vitest, pantallas, humo (+PROC-11) | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | ReporteContratacionesPage(.test).tsx, pantallas.ts, uat-humo | tsc, eslint, vitest | Router y Sidebar rechazados → C2 | FR-01, AC-06 |
| T006 ✔ | C2: cableado, restos del backend y E2E | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | router, Sidebar, humo, servicio, prueba, e2e/gobierno-reporte-contrataciones.spec.ts | E2E | Selectores ambiguos y mypy → C3 | AC-01..06 |
| T007 ✔ | C3 y C4: `exact` en la E2E, guarda de tipo y colisión de nombre (causa nueva) | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | E2E, servicio | E2E 2/2 con 4 workers; mypy = línea base | Todo verde | — |
| T008 ✔ | Integración: suite PG completa, commit, push, UAT (REP-03 y PROC-11), tarjeta y matrices | CLAUDE | n-a | no | n-a | 0 | evidencias, docs/roadmap | suites, humo | HEAD == origin/develop | — |
