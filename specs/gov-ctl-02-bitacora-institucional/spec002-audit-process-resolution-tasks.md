# Tareas · CTL-02-AUDIT-PROCESS-RESOLUTION

**Autorización de implement:** el encargo «P2 — CTL-02 · Bitácora institucional con resolución canónica de procesos» (2026-11-19).
**Tope de DeepSeek:** 8 llamadas.

Todas las tareas comparten `RETRY_MAX: 2`. Cuando ejecuta DeepSeek, el modelo es `deepseek-v4-pro`; cuando ejecuta Claude, MODEL=n-a.

| Tarea | EXECUTOR | SEC_SENS | EGRESS_SAFE | FILES | TEST | DONE_WHEN | FR |
|---|---|---|---|---|---|---|---|
| T01 Autoridad de procesos | CLAUDE (arquitectura de la autoridad, cambio transversal) | NO | n-a | `procesos.py` | T03 | Contrato del plan | FR-PR-01 a 05 |
| T02 Consumidores (CTL-02, CTL-04, CTL-07/REP-10, CTL-05), esquema de la bitácora y tipo del frontend | CLAUDE (cambio transversal) | NO | n-a | `service_auditoria.py`, `service_bitacora.py`, `schemas_bitacora.py`, `service_sod_eventos.py`, `service_reporte_control.py`, `service_rendicion.py`, `api_rendicion.py`, `api.ts` | T03 | Defecto corregido en el backend | FR-PR-01 a 08 |
| T03 PG, guardias y ajuste de GX02 | CLAUDE (evidencia del defecto y de las mutaciones) | NO | n-a | `tests/test_gov_ctl02_procesos.py`, `tests/test_gov_ctl04_auditoria.py` | sí misma | Los 20 puntos del §27 en verde | FR-PR-01 a 08 |
| T04 Frontend de la bitácora y Vitest | DEEPSEEK | NO | SÍ | `BitacoraPage.tsx`, `BitacoraEventoPage.tsx`, `BitacoraProcesoModulo.test.tsx` | Vitest, typecheck y lint | Verde | FR-PR-09 |
| T05 E2E de dos procesos, con actor, unidad y correlación, y filtro de CTL-04 | DEEPSEEK | NO | SÍ | `e2e/gobierno-bitacora-procesos.spec.ts` | E2E real | 1/1 con Axe | FR-PR-09 |
| T06 Mutaciones, hardcode, tarjeta UAT, roadmap y cierre | CLAUDE | NO | n-a | `evidence/audit-process-resolution/*` y `docs/roadmap/*` | mutaciones | M1–M9 muertas | FR-PR-05, 09 |

**Trazabilidad:** 9 de 9 requisitos con tarea y prueba (100 %).
