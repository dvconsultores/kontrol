# `/speckit.converge` · OBS-07 · CSYNC-AISLAMIENTO
| Gate | Resultado |
|---|---|
| Causa raíz | PROVEN: mundo de módulo compartido + precondiciones implícitas (10/13 fallaban solas, 11/13 en orden inverso) |
| Dueña | 004 (carpeta 010), apoyo 054 — confirmada |
| Alcance | solo pruebas (2 ficheros); producto, `conftest.py`, `qa/`, OBS-09: 0 |
| Dirigidas | 13/13 solas · directo · inverso (orden verificado) · SQLite y PostgreSQL |
| Mutaciones | 13/13 |
| SQLite ×2 · PostgreSQL · E2E · OpenAPI | 1800/0/1046 ×2 · 2820/0/26 · 284/0/0 · 544/533/11 |
| OBS-09 | IMPLEMENTATION IN PROGRESS / BLOCKED BY ENVIRONMENT, intacta |
| Prohibiciones | sleep/retry/skip/xfail/reorden/paralelismo/timeouts/aserciones debilitadas: 0 |
| BLOCKER · MATERIAL OQ · UNKNOWN · trazabilidad | 0 · 0 · 0 · 100 % |
**CLOSED / CONVERGED.**
