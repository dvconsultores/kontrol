# CTL-07 · Tareas

| Tarea | Qué | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 | Reconciliación, recuento, selección, Spec, plan, gate y briefs | CLAUDE | n-a | no | n-a | 0 | specs/gov-ctl-07-alertas-atipicas/* | — | Gate PASS |
| T002 | Backend: modelo, migración 0109, servicio, esquemas, API, registro, capacidades, MFA, catálogo y recuentos | DEEPSEEK | deepseek-v4-pro | sí (diseño fijado por Claude) | sí | 2 | models.py, alembic/versions/0109_gov_ctl07_alertas.py, service_alertas.py, schemas_alertas.py, api_alertas.py, main.py, setup/api.py, mfa_policy.py, audit_catalog_entries.py, 5 pruebas de recuento o cabeza | T003 | ruff limpio; n10 sin diferencias nuevas; T003 en verde |
| T003 | Pruebas de backend en PostgreSQL (AC-01..09) | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | tests/test_gov_ctl07_alertas.py | la propia | Todas en verde y 2 mutaciones mueren |
| T004 | Pantalla, ruta, menú, requisito de pantalla y Vitest | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | control/AlertasAtipicasPage.tsx, .test.tsx, router.tsx, Sidebar.tsx, pantallas.ts | Vitest | typecheck, lint y Vitest en verde |
| T005 | E2E de 11 pasos con Axe a 1280, 390 y 320 | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | e2e/gobierno-alertas.spec.ts | E2E | En verde a las tres anchuras |
| T006 | Auditoría, QA final, matrices, tarjeta UAT, publicación y UAT | CLAUDE | n-a | — | — | — | evidencia, matrices y tarjeta | suite | Cierre |

Las seguridades (capacidades, MFA, autorrevisión, aislamiento) las **fija Claude en el contrato**. DeepSeek solo escribe el código mecánico que ya está especificado.
