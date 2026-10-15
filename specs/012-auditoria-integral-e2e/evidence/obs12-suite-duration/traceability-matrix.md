# Matriz de trazabilidad (FR-O12 → evidencia / prueba)
| Requisito | Evidencia | Prueba |
|---|---|---|
| FR-001…003 duración monotónica, no solo pared, total registrado | `qa-measurement-contract.md`, `sqlite-profile.md`, `postgres-profile.md` | O12-01, O12-02 |
| FR-004…005 duraciones por prueba y familias lentas | `top30-sqlite.md`, `top30-postgres.md`, `classification-matrix.md` | O12-06 |
| FR-006…009 anfitrión sin cambiar producto; carga, memoria, CPU, disco; sin IP/VPN/credenciales; red solo saneada | `host-load-*.md`, `system-metrics-capability.md` | O12-03, O12-04, O12-05, O12-07 |
| FR-010…020 nada de timeouts, busy_timeout, sleep, retry, skip/xfail, reorden, paralelismo, producto, reloj, analizador; ClamAV real canónico | `implementation-decision.md`, diff | O12-13…O12-18, O12-20 |
| FR-021…023 coste del analizador válido | `scanner-cost-experiment.md`, `scanner-cost-model.md` | O12-08, O12-15 |
| FR-024…026 inventario de esperas, sin cambios | `wait-timeout-inventory.md` | O12-13, O12-14 |
| FR-027…028 clasificación, UNKNOWN 0 | `classification-matrix.md` | — |
| FR-029 cierre por caracterización | `historical-outlier-analysis.md`, `convergence.md` | O12-11, O12-12 |
| FR-030…032 STOP ante producto, paralelismo, analizador | `implementation-decision.md` | — |
| FR-033…035 MASTER57, SPEC057, NEXT | roadmap, `convergence.md` | — |
| Observabilidad reproducible (W19–W22) | `qa-measurement-contract.md`, `directed-tests.md`, `mutation-campaign.md` | O12-01…20 |
| Certificación (W23–W25) | `sqlite-certification-*.md`, `postgres-certification.md`, `global-e2e.md`, `openapi.md` | O12-19 |
Huérfanos: requisitos 0, tareas 0. Trazabilidad 100 %.
