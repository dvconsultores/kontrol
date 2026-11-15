# Tareas · CNT-01

Cada tarea tiene `RETRY_MAX: 2`. Tope del ciclo: 8 llamadas a DeepSeek (objetivo, de 3 a 5) con `deepseek-v4-pro`.

| Tarea | Qué hace | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|
| T001 | Arqueología, Spec, plan, gate, tareas y fuentes | CLAUDE | n-a | — | — | `specs/gov-cnt-01-contrato-orden/*` | — | Gate PASS |
| T002 | Modelos, migración 0113 (reencadenada como 0115 en la integración), clasificador AAL generalizado, permisos, MFA, catálogo de auditoría, catálogo CTL-01 y recuentos | DEEPSEEK (Claude fija el DDL exacto) | deepseek-v4-pro | SÍ: migración y permisos, con diseño fijado por Claude | SÍ | `models.py`, `alembic/versions/0113_gov_cnt01_contratos.py`, `service_decision_limite.py`, `setup/api.py`, `mfa_policy.py`, `audit_catalog_entries.py`, `service_sod.py`, tests de recuento y de cabeza | Alembic upgrade, downgrade y upgrade en PG; AAL 12/12; recuentos | Ruff limpio; 1 cabeza (0113); AAL en verde |
| T003 | `service_contratos.py`, `schemas_contratos.py`, `api_contratos.py`, `main.py` y `contrato` en la decisión vigente | DEEPSEEK | deepseek-v4-pro | SÍ: autoridad y límite, con reglas fijadas por Claude | SÍ | Esos 5 ficheros, más `service_decision.py` | Sonda de humo en PG | Ruff y mypy sin errores nuevos |
| T004 | Pruebas backend: vectores A a I, inmutabilidad, cronología, CTL-01, permisos y aislamiento | DEEPSEEK | deepseek-v4-pro | no | SÍ | `tests/test_gov_cnt01_contratos.py` | PG dirigido | Todo verde; las mutaciones mueren |
| T005 | Frontend: API, `ContratosPage`, `ContratoPage`, menú, rutas, botón en la decisión y Vitest | DEEPSEEK | deepseek-v4-pro | no | SÍ | `modules/gobierno/contratos/*`, `Sidebar.tsx`, `router.tsx`, `ExpedienteDecision.tsx` | Vitest, typecheck y lint | Todo verde |
| T006 | E2E del recorrido y negativas, responsive y Axe | DEEPSEEK | deepseek-v4-pro | no | SÍ | `e2e/gobierno-contratos.spec.ts`, `e2e/helpers/gobierno.ts` | E2E dirigida | Verde con 0 reintentos |
| T007 | Auditoría, mutaciones, QA final, matrices, evidencia, UAT y publicación | CLAUDE | n-a | — | — | evidencia y matrices | — | `CIERRE.md` |
