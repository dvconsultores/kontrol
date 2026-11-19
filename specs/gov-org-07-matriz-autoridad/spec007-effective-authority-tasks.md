# Tareas · ORG-07-EFFECTIVE-AUTHORITY-MATRIX

**Autorización de implement:** el encargo «P2 — ORG-07 · Matriz de autoridad efectiva con ORG-04» (2026-11-19).
**Tope de DeepSeek:** 8 llamadas.

Todas las tareas comparten `RETRY_MAX: 2`. Cuando ejecuta DeepSeek, el modelo es `deepseek-v4-pro`; cuando ejecuta Claude, MODEL=n-a.

| Tarea | EXECUTOR | SEC_SENS | EGRESS_SAFE | FILES | TEST | DONE_WHEN | FR |
|---|---|---|---|---|---|---|---|
| T01 ORG-04: `autoridad_efectiva_en` | CLAUDE (resolución canónica de autoridad) | NO | n-a | `service_ocupacion.py` | T03 | Contrato del plan | FR-EA-01 a 04 |
| T02 ORG-07: proyección, reserva de personas, CSV, esquemas y API | CLAUDE (control de acceso OD-EA-01) | SÍ | n-a | `service_autoridad.py`, `schemas_autoridad.py`, `api_autoridad.py` | T03 | P0 corregido en el backend | FR-EA-01 a 07 |
| T03 PG de la matriz efectiva y del P0 | CLAUDE (evidencia del defecto y de las mutaciones) | NO | n-a | `tests/test_gov_org07_efectiva.py` | sí misma | Los 20 puntos del §29 en verde (17 pruebas) | FR-EA-01 a 07 |
| T04 Frontend de la matriz y Vitest | DEEPSEEK | NO | SÍ | `MatrizAutoridadPage.tsx`, `MatrizAutoridadPage.test.tsx` y los tipos (contrato de Claude) | Vitest, typecheck y lint | Verde | FR-EA-08 |
| T05 E2E efectiva, histórica y CSV | DEEPSEEK | NO | SÍ | `e2e/gobierno-autoridad-efectiva.spec.ts` | E2E real | 3 escenarios y Axe | FR-EA-09 |
| T07 Defecto de ORG-04 destapado por la E2E (activar una delegación daba 500 con `autoflush=False`) | CLAUDE (depuración y causa raíz) | NO | n-a | `service_ocupacion.py` | `test_org07_ea17_*` y PG de ORG-04 | La E2E activa delegaciones contra la app real | D-EA-11 |
| T06 Mutaciones, hardcode, tarjeta UAT, roadmap y cierre | CLAUDE | NO | n-a | `evidence/effective-authority/*` y `docs/roadmap/*` | mutaciones | M1–M8 muertas | FR-EA-09 |

**Trazabilidad:** 9 de 9 requisitos con tarea y prueba (100 %).
