# Tareas · CNT-02

Cada tarea tiene `RETRY_MAX: 2`. Tope del ciclo: 8 llamadas a DeepSeek con `deepseek-v4-pro`; el objetivo es de 3 a 5. `OWNER_EXCEPTION_INHERITED=0`.

| Tarea | Qué hace | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|
| T001 | Reconciliación, arqueología, fuentes, delta de CNT-01, Spec, plan, gate y tareas | CLAUDE | n-a | — | — | `specs/gov-cnt-02-adendas-variaciones/*`, `specs/gov-cnt-01-contrato-orden/cnt01-moneda-cobertura-delta.md` | — | Gate PASS |
| T002 | Base y endurecimiento: modelos y guardas, migración 0117, catálogo de auditoría (+5), SoD (+2), cabezas, y H01–H09 en `service_contratos.py` con sus ayudantes públicos | DEEPSEEK (Claude fija el DDL y las reglas) | deepseek-v4-pro | SÍ: migración, monedas y autoridad, con diseño fijado por Claude | SÍ | `models.py`, `alembic/versions/0117_gov_cnt02_modificaciones.py`, `audit_catalog_entries.py`, `service_sod.py`, `service_contratos.py`, tests de recuento y de cabeza, `test_gov_cnt01_contratos.py` (vector G) | Alembic up/down/up en PG; CNT-01 13/13 | Ruff limpio; mypy sin errores nuevos; 1 cabeza |
| T003 | Servicio, esquemas y API de CNT-02, más `main.py` | DEEPSEEK | deepseek-v4-pro | SÍ: autoridad, cobertura y límite, con reglas fijadas por Claude | SÍ | `service_contratos_modificaciones.py`, `schemas_contratos_modificaciones.py`, `api_contratos_modificaciones.py`, `main.py` | Sonda de humo en PG | Ruff y mypy sin errores nuevos |
| T004 | Pruebas PG de CNT-02 (C02-01..20) y del delta H01–H09 | DEEPSEEK | deepseek-v4-pro | no | SÍ | `tests/test_gov_cnt02_modificaciones.py`, `tests/test_gov_cnt01_moneda_cobertura.py` | PG dirigido | Todo verde; las mutaciones mueren |
| T005 | Frontend: API, dos pantallas, rutas, enlace y conversión en ContratoPage, y Vitest | DEEPSEEK | deepseek-v4-pro | no | SÍ | `modules/gobierno/contratos/*`, `router.tsx`, `pantallas.ts` | Vitest, typecheck y lint | Todo verde |
| T006 | E2E: recorrido del sponsor y delta de CNT-01, con 1280/390/320 y Axe | DEEPSEEK | deepseek-v4-pro | no | SÍ | `e2e/gobierno-contratos-modificaciones.spec.ts` | E2E dirigida | Verde con 0 reintentos |
| T007 | Auditoría, mutaciones, QA final (PG completa una vez sobre el árbol final), matrices, evidencia, UAT y publicación | CLAUDE | n-a | — | — | evidencia y matrices | — | `CIERRE.md` |
