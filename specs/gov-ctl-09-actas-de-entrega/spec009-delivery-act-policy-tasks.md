# Tareas · CTL-09-DELIVERY-ACT-POLICY

**Autorización de implement:** el encargo «P2 — CTL-09 · Actas de entrega paramétricas y normativa versionada» (2026-11-18).

- **Tope de DeepSeek:** 16 llamadas (OD-AE-05).
- **Comunes a todas las tareas:** `RETRY_MAX: 2`; con DeepSeek, el modelo `deepseek-v4-pro`; con Claude, `MODEL=n-a`.

| Tarea | EXECUTOR | SEC_SENS | EGRESS_SAFE | FILES | TEST | DONE_WHEN | FR |
|---|---|---|---|---|---|---|---|
| T01 Fuente N34 custodiada, delta, plan y tareas | CLAUDE | NO | n-a | `specs/…/spec009-*`, `requerimientos/gobierno/normativa-n34/` | revisión | Compuerta PASS | FR-AE-02 |
| T02 Migración 0127 y modelos | CLAUDE (migración) | SÍ | n-a | `alembic/versions/0127_*.py`, `models.py` | upgrade, downgrade y upgrade en PG | Una cabeza | FR-AE-01, 11 |
| T03 Autoridad `service_actas_regla.py` | CLAUDE (semántica normativa) | NO | SÍ | archivo nuevo | T07 | Contrato del plan | FR-AE-02 a 10 |
| T04 Integración en `service_actas`, API `/regla`, esquemas y auditoría | CLAUDE (núcleo del P0) | NO | SÍ | `service_actas.py`, `api_actas.py`, `schemas_actas.py`, `audit_catalog_entries.py` | `test_gov_ctl09_actas` | 8/8 existentes en verde | FR-AE-04 a 11 |
| T05 Permisos, MFA, setup y constantes | CLAUDE (permisos) | SÍ | n-a | `setup/api.py`, `mfa_policy.py`, pruebas de recuento | recuentos | Verde | FR-AE-12 |
| T06 Políticas: servicio, esquemas y API | DEEPSEEK | NO | SÍ | 3 archivos nuevos y `main.py` | T07 | Rutas del plan | FR-AE-01, 03, 12 |
| T07 PG de políticas, regla y procesos (P0 incluido) | DEEPSEEK | NO | SÍ | `tests/test_gov_ctl09_politica*.py` | sí misma | Verde | FR-AE-01 a 12 |
| T08 Frontend de políticas y Vitest | DEEPSEEK | NO | SÍ | `actas/Politica*.tsx`, sus pruebas, `router.tsx`, `Sidebar.tsx` y `pantallas.ts` | Vitest | Verde | FR-AE-13 |
| T09 Nueva acta y ficha: regla, anexos condicionales, declaración, plazos y responsabilidad, y Vitest | DEEPSEEK | NO | SÍ | `NuevaActaEntregaPage.tsx`, `ActaEntregaPage.tsx`, sus pruebas y `api.ts` | Vitest | Verde; A17 condicional | FR-AE-05, 13 |
| T10 E2E (principal, P0, A17 positivo, versión y ORG-04) con Axe y humo UAT | DEEPSEEK | NO | SÍ | `e2e/gobierno-actas-politica.spec.ts`, `e2e/uat-humo-gobierno.spec.ts` | E2E real | 5 escenarios | FR-AE-14 |
| T11 Mutaciones M1–M10, auditoría de hardcode, N34_VALIDATION, tarjeta UAT, roadmap y cierre | CLAUDE | NO | n-a | `evidence/delivery-act-policy/*` | mutaciones | Las 10 muertas | FR-AE-14 |

**Trazabilidad:** 14 de 14 requisitos con tarea y prueba (100 %). Las reclasificaciones se declaran en `evidence/delivery-act-policy/ATTEMPT_LOG.md`.
