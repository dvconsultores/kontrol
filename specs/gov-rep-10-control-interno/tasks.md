# Tasks · REP-10

Tope global del ciclo: 8 llamadas (política §6). Reintentos: 2 por subproblema.

| Id | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 ✔ | Reconciliación, métricas, matriz de candidatos y selección | CLAUDE | n-a | no | n-a | 0 | — | recálculo desde las matrices | REP-10 elegido; ningún P0 elegible |
| T002 ✔ | Fuentes, decisiones PDD-REP10-01..09, spec y plan con la compuerta | CLAUDE | n-a | no | n-a | 0 | specs/gov-rep-10-control-interno/* | revisión | CONSTITUTION_GATE PASS, MATERIAL_DECISION_REQUIRED=0 |
| T003 ✔ | R1 backend: servicio, API, main, catálogo (+1) y pruebas PG | DEEPSEEK | deepseek-v4-pro | sí (aislamiento, permisos por sección) | sí | 2 | service_reporte_control.py, api_reporte_control.py, main.py, audit_catalog_entries.py, test_audit_catalog_backup.py, test_gov_rep10_control_interno.py | pytest PG; ruff; mypy | Servicio aplicado; pruebas inventadas → C1 |
| T004 ✔ | C1/C2 (reintentos 1 y 2): totales reales, ids str, CSV completo, pruebas reescritas | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | service_reporte_control.py, test_gov_rep10_control_interno.py | pytest PG | C1 rechazado; C2 aplicado con defectos nuevos → C3 |
| T005 ✔ | R2 frontend: pantalla, menú, rutas, pantallas, humo UAT y Vitest | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | ReporteControlInternoPage(.test).tsx, router, Sidebar, pantallas, uat-humo-gobierno.spec.ts | tsc, eslint, vitest | Aplicado; F1..F4 → C3 |
| T006 ✔ | C3 corrección combinada (D1..D4 backend, T1..T3 pruebas, F1..F5 frontend) | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | los cuatro ficheros | PG, vitest | 19/21 aplicados |
| T007 ✔ | R3 E2E de usuario + P1/P2 | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | e2e/gobierno-control-interno.spec.ts, pruebas | qa/e2e-run.py | Aplicado; E1..E4 y F6 → C4 |
| T008 ✔ | C4/C5 (reintentos 1 y 2 del subproblema E2E/pantalla), C6 y C7 (9/8 y 10/8, autorizadas por la dueña) | DEEPSEEK | deepseek-v4-pro / v4-flash | no | sí | 2 | pantalla, prueba de pantalla, E2E, prueba backend | tsc, eslint, vitest, PG, E2E | Todo verde |
| T009 ✔ | Integración: suite PG completa, E2E, commit, push, UAT, tarjeta y matrices | CLAUDE | n-a | no | n-a | 0 | specs/.../evidence, docs/roadmap | suites | HEAD == origin/develop |
