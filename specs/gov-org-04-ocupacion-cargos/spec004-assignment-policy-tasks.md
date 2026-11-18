# Tareas · ORG-04-AUTHORITY-ASSIGNMENT-POLICY

**Autorización de implement:** el encargo «P2 — ORG-04 · Delegaciones, suplencias, encargadurías y designaciones paramétricas» (2026-11-18). **Tope de DeepSeek:** 24 llamadas (OD-AP-04).

Todas las tareas comparten `RETRY_MAX: 2` y el modelo `deepseek-v4-pro` cuando el ejecutor es DeepSeek (MODEL=n-a cuando es Claude).

| Tarea | EXECUTOR | SEC_SENS | EGRESS_SAFE | FILES | TEST | DONE_WHEN | FR |
|---|---|---|---|---|---|---|---|
| T01 Migración 0126 (era 0125), modelos y disparador | CLAUDE (migración) | SÍ | n-a | `alembic/versions/0126_*.py`, `models.py` | upgrade, downgrade y upgrade en PG | Una cabeza; modelos alineados | FR-AP-01, 02, 06 |
| T02 Permiso, MFA, setup, catálogo de auditoría y ResourceKind | CLAUDE (permisos) | SÍ | n-a | `mfa_policy.py`, `setup/api.py`, `audit_catalog_entries.py`, `documents/resources.py` | `test_mfa_policy`, `test_n9_*` | Recuentos actualizados | FR-AP-10 |
| T03 Autoridad `service_asignacion_regla.py` | CLAUDE (reclasificada: pisos legales) | NO | SÍ | archivo nuevo | T06 | Contrato del plan | FR-AP-03, 04 |
| T04 Políticas: servicio, esquemas y API | DEEPSEEK | NO | SÍ | 3 archivos nuevos y `main.py` | T06 | Rutas del plan | FR-AP-01, 02, 09 |
| T05 Integración en `service_ocupacion`, esquemas, API y regla | CLAUDE (reclasificada: autoridad propia y emisor; brief > 55 KB) | NO | SÍ | `service_ocupacion.py`, `schemas_ocupacion.py`, `api_ocupacion.py`, `service_contratos_supervision.py` | T07 y PG de ORG-04 | P0 corregido en el backend | FR-AP-05 a 08, 12 |
| T06 PG de políticas y autoridad | DEEPSEEK | NO | SÍ | `tests/test_gov_org04_politica.py` | sí misma | Verde | FR-AP-01 a 04, 09, 10 |
| T07 PG de procesos y P0 | DEEPSEEK | NO | SÍ | `tests/test_gov_org04_politica_procesos.py` | sí misma | Escenarios A y B, congelación y legado | FR-AP-05 a 08, 12 |
| T08 Pruebas existentes (renombre y mensajes) | CLAUDE (reclasificada: 3 cambios mecánicos) | NO | SÍ | tests de ORG-04 afectados | PG dirigida | Verde | FR-AP-05 |
| T09 Frontend de políticas y Vitest | DEEPSEEK | NO | SÍ | 4 archivos nuevos, más `router.tsx`, `Sidebar.tsx` y `pantallas.ts` | Vitest | Verde | FR-AP-11 |
| T10 Formulario (T10a, DEEPSEEK) y ficha (T10b, CLAUDE reclasificada) de la asignación, y Vitest | DEEPSEEK/CLAUDE | NO | SÍ | `NuevaAsignacionPage*`, `AsignacionPage*`, `api.ts` | Vitest | Verde; la autorización es condicional | FR-AP-07, 08, 11 |
| T11 E2E de políticas de asignación | DEEPSEEK | NO | SÍ | `e2e/gobierno-ocupacion-politica.spec.ts` | E2E real | 5 escenarios y Axe | FR-AP-13 |
| T12 Mutaciones, auditoría de hardcode, tarjeta UAT y cierre | CLAUDE | NO | n-a | `evidence/assignment-policy/*` | mutaciones | Las 8 muertas | FR-AP-13 |

**Trazabilidad:** 13 de 13 requisitos con tarea y prueba (100 %).

Las reclasificaciones y el trabajo de Claude están declarados en `evidence/assignment-policy/ATTEMPT_LOG.md`.
