# Matriz de trazabilidad (FR-O06 → evidencia / prueba)
| Requisito | Evidencia | Prueba |
|---|---|---|
| FR-001…003 inventarios de definiciones y consumidores | `path-definition-inventory.md`, `consumer-matrix.md`, `writer-inventory.md` | — |
| FR-004, 021…023 producto, migraciones y esquema intactos | `implementation.md` | O06-14, O06-20 |
| FR-005…008 igualdad de rutas, visibilidad, colisión | `d1…d3` | O06-01…04 |
| FR-009…010 persistencia y su valoración | `d4`, `d5`, `cleanup-contract.md` | O06-09, O06-10 |
| FR-011…013 raíz única por proceso y consistente dentro | `d6`, `implementation.md` | O06-01, 02, 05…07 |
| FR-014 creada antes de la configuración | `d8`, `configuration-lifetime.md` | O06-05, O06-08 |
| FR-015…016 ni por petición ni por fixture | `implementation-decision.md` | O06-05, O06-08 |
| FR-017…020 limpieza en el límite correcto, propia, sin globs | `d7` | O06-09…12, O06-19 |
| FR-024…029 sin sleep/retry/skip/reorden/timeouts/paralelismo | `implementation.md` | O06-19 |
| FR-030 analizador intacto | — | O06-17 |
| FR-031…032 OBS-12 y legado | `obs12-telemetry.md` | O06-18, O12-09, O12-10 |
| FR-033 aserciones funcionales intactas | — | O06-15, O06-16; regresiones documentos/reporting |
| FR-034…036 MASTER57, SPEC057, NEXT | roadmap, `convergence.md` | — |
Huérfanos: requisitos 0, tareas 0. Trazabilidad 100 %.
