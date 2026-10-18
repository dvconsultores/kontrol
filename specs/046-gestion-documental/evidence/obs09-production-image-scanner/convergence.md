# `/speckit.converge` · OBS-09 · PRODUCTION-IMAGE-WITHOUT-SCANNER
| Gate | Resultado |
|---|---|
| Causa raíz | PROVEN: composición de producción sin analizador frente a un producto que lo exige por defecto (falso seguro) |
| Adaptador clamd (INSTREAM, sin rutas, sin almacén, falso seguro, sin alternativa) | hecho y probado: O09 29/29, CLAMD-QA 15/15, demonio real 12/12 |
| Composición | `compose.yaml` + `Dockerfile.clamd` + `deploy/clamd/clamd.conf`: contrato **verificado estáticamente** (puerto interno, sin almacén, firmas en el servicio, healthcheck PING, límites ≥ 50 MiB) |
| Construcción de imagen y `compose up` reales | **NO ejecutados**: sin runtime de contenedores en el equipo de QA (`COMPOSE_RUNTIME_UNAVAILABLE`); pasos en `docs/evidence/docker-validation-checklist.md` |
| Mutaciones | 16/16 |
| Regresiones dirigidas | SQLite 278/0/54 · PostgreSQL 342/0/9 |
| SQLite ×2 | 1783/0/1046 · 1783/0/1046 (623 s · 704 s) |
| PostgreSQL | 2803/0/26 (1434 s) |
| E2E | 284/0/0 (clamscan; LIMPIA) |
| OpenAPI | 544/533/11, sin cambio |
| OBS-06 / OBS-12 | preservadas (O06 20/20, O12 20/20 en las dirigidas; telemetría intacta) |
| Residuos | bases 0 · `t_` 0 · efímeros 0 · contenedores/redes/imágenes/volúmenes de OBS-09: ninguno creado · puertos libres · ClamAV rastreado 0 |
| BLOCKER · MATERIAL OQ · UNKNOWN · trazabilidad | **1 (entorno)** · 0 · 0 · 100 % |
**Veredicto: `OBS-09 — IMPLEMENTATION IN PROGRESS — BLOCKED BY ENVIRONMENT`** (caso F): todo lo demostrable sin runtime
está convergido; el cierre `CLOSED / CONVERGED` exige la evidencia de composición (`compose-runtime-evidence.md`) desde un
equipo con Docker. Tareas 8 · CLAUDE 7 · DeepSeek 1 (T08-DOC, 1 llamada, $0.000176, 0 rechazos, 0 reintentos) · código y
pruebas escritos por Claude antes de la regla mandatoria del 2026-10-18 (opción A).
