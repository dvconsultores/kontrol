# Tasks PROC-08

Todas las tareas: `RETRY_MAX: 2`, `EGRESS_SAFE: sí` (solo datos sintéticos) y `MODEL: deepseek-v4-pro`, salvo T6 y T7 (`n-a`).

| Tarea | Qué | Ejecutor | Sensible a seguridad | Ficheros | Prueba | Hecha cuando |
|---|---|---|---|---|---|---|
| T1 | Modelos, migración 0093, permisos, catálogo de auditoría, clases de evento, SoD y guardas derivadas | DEEPSEEK | sí (permisos) | `models.py`, `alembic/versions/0093_gov_proc08_decision.py`, `setup/api.py`, `mfa_policy.py`, `audit_catalog_entries.py`, `service_sod.py`, `service_expedientes.py` (etiquetas y claves de auditoría), pruebas de recuento | guardas, `alembic heads` | 1 cabeza; recuentos medidos; migración en PostgreSQL |
| T2 | Recomendación: estado, emisión, sustitución, firmantes, opciones, rechazos, instantánea e informe PDF, más la siguiente acción de PROC-07 | DEEPSEEK | sí (identidad) | `service_decision.py`, `schemas_decision.py`, `api_decision.py`, `main.py`, `service_evaluacion.py`, `service_expedientes.py`, `tests/test_gov_proc08_recomendacion.py` | la prueba nueva + PROC-07 | Pruebas verdes en PostgreSQL |
| T3 | Decisión: acto DOC-02, autoridad, resultados ADJUDICADA, DESIERTA, TERMINADA y NULIDAD, opciones según art. 110, separación de la Comisión, notificaciones por oferente | DEEPSEEK | sí (autoridad) | `service_decision_resolver.py`, `api_decision.py`, `schemas_decision.py`, `tests/test_gov_proc08_decision.py` | la prueba nueva | Pruebas verdes en PostgreSQL, con las negativas materiales |
| T4 | Sección «Recomendación y decisión» | DEEPSEEK | no | `ExpedienteDecision.tsx`, `ExpedientePage.tsx` | tsc, eslint, build | Compila |
| T5 | E2E principal de adjudicación (Chromium), con Axe y 390/320 | DEEPSEEK | no | `e2e/gobierno-decision.spec.ts` | E2E canónica | 1/1 |
| T6 | Cierre: Alembic, regresiones, OpenAPI, fixtures, publicación, UAT, tarjeta y matrices | CLAUDE | — | — | — | `HEAD == origin`; pila UAT en el commit |
| T7 | Converge | CLAUDE | — | — | — | Sin huecos |

## Estado al cierre (2026-11-10)

T1–T7 completadas. Producto publicado en `570a033`; evidencia en `evidence/CIERRE.md` y tarjeta de prueba en
`evidence/OWNER_UAT_CARD.md`. Estado: OWNER_UAT_READY (OWNER_ACCEPTED pendiente de la dueña).
