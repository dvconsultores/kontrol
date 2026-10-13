# Matriz de trazabilidad · LISTADOS-SIN-TOPE

| Eslabón | Artefacto | Prueba / evidencia |
|---|---|---|
| inventario de listados | `collection-inventory.md` (177 GET; 17/8/79; UNKNOWN 0) | — |
| tope canónico | `pagination-convention.md`, `limit-convention.md` (100, 422; Spec 001) | LT-01/02/09/10 |
| sobre canónico | `pagination-convention.md` | LT-04 |
| reproducción almacenes / pick-lists | `warehouses-before.md`, `picklists-before.md`, `large-dataset.md` | `repro.py` (1 100 / 300) |
| consumidores | `consumer-inventory.md`, `frontend-consumer.md` | T04/T05; Vitest 4; E2E |
| alcance de empresa | `tenant-scope-proof.md` | LT-12/13/14; M-07/M-08 |
| `total` | `contract-decision.md` | LT-05/08/15; M-04 |
| orden | `ordering-proof.md` | LT-11; M-06 |
| contrato backend | `contract-decision.md`, `implementation.md` (T01, T02) | LT-01…15, SQL; M-01…M-09 |
| frontend / API client | `frontend-consumer.md` (T04) | `organization.test.ts` 9/9; typecheck; lint; M-10/M-11 |
| QA / E2E | `consumer-inventory.md` (T05) | E2E globales; `qa/repro-almacenes-listado.py` |
| pruebas hostiles | `hostile-tests.md` | 29 en SQLite y PostgreSQL |
| mutaciones | `mutation-campaign.md` | 12/12 |
| SQLite / PostgreSQL completas | `sqlite-full.md`, `postgres-full.md` | 42/1609/1040 · 38/2625/28 |
| gates frontend | `frontend-gates.md` | 481/481, build |
| OpenAPI | `openapi-before.md`, `openapi-after.md` | 544/533/11; 2 operaciones documentadas |
| E2E | `global-e2e.md` | 3 corridas (1 clasificada + 2 limpias) |
| rendimiento | `performance-after.md` | 203 KB → 3,7 KB; 422 |
| convergencia | `convergence.md`, delta §13 | — |

FR-LT-001…030 → T01–T06 y LT-01…24 (delta §4, §8, §12). Cobertura: **100 %**.
