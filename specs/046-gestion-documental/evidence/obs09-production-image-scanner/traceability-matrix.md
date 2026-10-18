# Matriz de trazabilidad (encargo OBS-09 → evidencia / prueba)
| Requisito del encargo | Evidencia | Prueba |
|---|---|---|
| §7 inventario real · §8 causa raíz | `current-state-inventory.md`, `root-cause.md`, `clamd-control-measurements.md` | — |
| §9 arquitectura (servicios distintos, contenido no rutas, sin montaje, puerto interno, DNS, sin IP, sin secretos, sin registrar contenido, falso seguro) | `architecture.md`, `compose-contract.md` | O09-08, 16, 17, 19; CLAMD-QA-04 |
| §10 abstracción mínima | `architecture.md` | O09-14, O09-15 (decisión en el servicio) |
| §11 protocolo INSTREAM (trozos, EOF, cierre, truncada, inválida, timeout, rechazo, caído, CLEAN, INFECTED) | `scanner-protocol.md`, `clamd-qa-report.json` | O09-01…09, 20…22, 25; CLAMD-QA-08 |
| §12 contrato de tamaño | `size-contract.md`, `clamd-qa-report.json` | O09-10, O09-11; CLAMD-QA-02 |
| §13 configuración explícita y validada | `configuration-contract.md` | O09-12, 13, 17, 18, 23 |
| §14 falso seguro inalterable | `scanner-protocol.md` | O09-03…07, 14, 15, 25 |
| §15 composición | `compose-contract.md` | CLAMD-QA-04 |
| §16 firmas en el dominio del analizador | `compose-contract.md`, `architecture.md` | O09-24; CLAMD-QA-04 |
| §17 healthcheck material | `compose-contract.md` | CLAMD-QA-04 |
| §18 QA de composición | `clamd-qa-report.json`, `implementation-decision.md` (runtime) | CLAMD-QA-01…11 |
| §19 pruebas O09-01…25 | `directed-tests.md` | O09 |
| §20 mutaciones ≥ 10 | `mutation-campaign.md` | — |
| §23–§27 regresiones y certificación | `directed-tests.md`, `sqlite-full-*.md`, `postgres-full.md`, `global-e2e.md`, `openapi.md` | — |
| §28–§29 OBS-12 y OBS-06 preservadas | `directed-tests.md` (O12, O06) | O12, O06 |
| §31 residuos | `convergence.md` | — |
Huérfanos: requisitos 0, tareas 0. Trazabilidad 100 %.
