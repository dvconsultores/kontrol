# Tasks CTL-03

Todas: `RETRY_MAX: 2`, `EGRESS_SAFE: sí`, `MODEL: deepseek-v4-pro` salvo T6 y T7 (`n-a`). `SECURITY_SENSITIVE: sí` en T1 y T2
(lectura de autoridad), no en T3 y T4.

| Tarea | Qué | Ejecutor | Ficheros | Prueba | Hecha cuando |
|---|---|---|---|---|---|
| T1 | Proyección de solo lectura (servicio, esquemas, API, registro) | DEEPSEEK | `service_separacion.py`, `schemas_separacion.py`, `api_separacion.py`, `main.py` | importa; ruff; mypy sin nuevos | GET devuelve el contrato |
| T2 | Pruebas PostgreSQL hostiles e invariantes | DEEPSEEK | `tests/test_gov_ctl03_separacion.py` | pytest PG | verdes; mutaciones mueren |
| T3 | Pantalla, ruta, menú, API cliente y Vitest | DEEPSEEK | `SeparacionPage.tsx`, `api.ts`, `router.tsx`, `Sidebar.tsx`, prueba | tsc, eslint, build, vitest | según `SCREEN_CONTRACT.md` |
| T4 | E2E canónica | DEEPSEEK | `e2e/gobierno-separacion.spec.ts` | E2E Chromium | 1/1 con Axe y 390/320 |
| T5 | Reserva por causa raíz nueva | DEEPSEEK | según defecto | — | — |
| T6 | Cierre: regresión dirigida, mutaciones (≤3), OpenAPI, fixtures, publicación, UAT, tarjeta, matrices | CLAUDE | — | — | `HEAD == origin` |
| T7 | Converge | CLAUDE | — | — | sin huecos |
