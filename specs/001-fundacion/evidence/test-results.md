# Evidencia de pruebas — 001-fundacion (2026-08-04)

| Puerta | Resultado | Fecha |
|---|---|---|
| Backend pytest | 25/25 passed | 2026-08-04 |
| Backend ruff lint | All checks passed | 2026-08-04 |
| Backend ruff format | 39 files already formatted | 2026-08-04 |
| Backend mypy | Success: no issues (35 source files) | 2026-08-04 |
| Backend app import + rutas | OK (health, setup, license, auth, organization, audit) | 2026-08-04 |
| Alembic head | `0001_fundacion (head)` | 2026-08-04 |
| Frontend typecheck (tsc -b) | 0 errors | 2026-08-04 |
| Frontend eslint (max-warnings 0) | 0 problems | 2026-08-04 |
| Frontend vitest | 5 files / 14 tests passed | 2026-08-04 |
| Frontend build (vite) | built (JS 421.88 kB / gzip 128.93 kB) | 2026-08-04 |

## Notas

- Pruebas de integración con PostgreSQL real y E2E de Playwright: pendientes de
  entorno con Docker (CVG-08); cubiertas por `compose.dev.yaml` y el pipeline CI.
- La validación local usó Python 3.11; el objetivo de producción es Python 3.13
  (imagen Docker). Se relajó `requires-python` en `pyproject.toml` para
  desarrollo local (documentado en el propio archivo).
