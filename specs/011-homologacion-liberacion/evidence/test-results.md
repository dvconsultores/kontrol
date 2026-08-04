# Resultados de pruebas — 011-HOMOLOGACION-LIBERACION

| Campo | Valor |
|---|---|
| Fecha | 2026-08-04 |
| Rama | `feature/001-fundacion` (HEAD `7091451`) |
| Método | Auditoría profunda 001-011 (gates re-ejecutados) |

## Gates

| Gate | Comando | Resultado |
|---|---|---|
| Backend pytest (spec) | `.venv/bin/python -m pytest tests/test_homologation.py -q` | ✔ 17/17 |
| Backend pytest (suite) | `.venv/bin/python -m pytest -q` | ✔ 190/190 |
| Backend ruff | `.venv/bin/ruff check .` | ✔ limpio |
| Backend mypy | `.venv/bin/mypy .` | ✔ 96 archivos, 0 issues |
| Alembic | `alembic heads` | ✔ head `0011_homologacion` |
| OpenAPI | `app.openapi()['paths']` | ✔ 213 rutas (homologation 8) |
| Frontend tsc / eslint | `npx tsc -b` / `npx eslint . --max-warnings 0` | ✔ limpios |
| Frontend vitest / build | `npx vitest run` / `npx vite build` | ✔ 16/16 · build OK |

## Cobertura (011)

Acto de homologación fiscal (DRAFT→SUBMITTED→APPROVED/REJECTED) con acto
formal, evidencia SHA-256 y segregación; regla de "homologado" derivada;
liberación de versión (DRAFT→CANDIDATE→RELEASED/BLOCKED) con gates,
homologación aprobada y licencia válida; timeline append-only.

## Pendientes de negocio (no bloquean)

- Integración CI/CD de gates, plantilla oficial del acto formal, firma/estampa
  de eventos y vínculo de la versión liberada en "Acerca de" (CVG-011-01..04).
