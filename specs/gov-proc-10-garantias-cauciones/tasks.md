# Tasks PROC-10

Todas las tareas: `RETRY_MAX: 2`, `EGRESS_SAFE: sí` (solo datos sintéticos, sin secretos ni rutas privadas) y
`MODEL: deepseek-v4-pro`, salvo T5 y T6 (`n-a`).

| Tarea | Qué | Ejecutor | Sensible a seguridad | Ficheros | Prueba | Hecha cuando |
|---|---|---|---|---|---|---|
| T1 | Backend: reglas versionadas, 4 modelos y guardas PG, migración (hoy 0096, reposicionada en el bloque 2), permisos y MFA, catálogo de auditoría, clase GARANTIA, SoD, servicio, esquemas, API y guardas de recuento | DEEPSEEK | sí (permisos, MFA, aislamiento) | `garantias_reglas.py`, `models.py`, `alembic/versions/0096_gov_proc10_garantias.py`, `setup/api.py`, `mfa_policy.py`, `audit_catalog_entries.py`, `service_expedientes.py`, `service_sod.py`, `service_garantias.py`, `schemas_garantias.py`, `api_garantias.py`, `main.py`, 5 pruebas de guarda | guardas, `alembic heads`, ruff, mypy | 1 cabeza; recuentos verdes; migración en PostgreSQL |
| T2 | Pruebas PostgreSQL de PROC-10 e interfaz «Garantías y cauciones» | DEEPSEEK | no | `tests/test_gov_proc10_garantias.py`, `api.ts`, `ExpedienteGarantias.tsx`, `ExpedientePage.tsx` | pytest PG, tsc, eslint, build, vitest Gobierno | Backend gate §54 verde |
| T3 | E2E principal (mantenimiento, renovación, liberación con MFA, NO_EVALUABLE del adjudicatario), Axe y 390/320; defectos reales | DEEPSEEK | no | `e2e/gobierno-garantias.spec.ts` (+ defectos acotados) | E2E canónica | 1/1 |
| T4 | Reserva funcional | DEEPSEEK | — | según defecto | — | — |
| T5 | Cierre: Alembic limpio, regresión mínima, OpenAPI, fixtures, publicación, UAT, tarjeta, matrices | CLAUDE | — | — | — | `HEAD == origin`; pila UAT en el commit |
| T6 | Converge | CLAUDE | — | — | — | Sin huecos |

## Estado (2026-11-10)

T1, T2 y T3 hechas; T4 consumida en el bloque 2 (defecto de producto `regla.forma` del formulario de requisito) y en el
bloque 3 (apertura idempotente del historial en la E2E). T5 en curso: técnica cerrada (ver `evidence/CIERRE.md`); faltan push, UAT,
tarjeta y matrices. T6: convergido, sin huecos (FR-001..FR-015 con implementación y prueba medidas).
