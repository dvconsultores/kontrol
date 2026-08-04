# Resultados de pruebas — 002-MAESTROS

| Campo | Valor |
|---|---|
| Fecha | 2026-08-04 |
| Rama | `feature/001-fundacion` (HEAD `7091451`) |
| Método | Auditoría profunda 001-011 (gates re-ejecutados) |

## Gates

| Gate | Comando | Resultado |
|---|---|---|
| Backend pytest (spec) | `.venv/bin/python -m pytest tests/test_maestros.py -q` | ✔ 12/12 |
| Backend pytest (suite) | `.venv/bin/python -m pytest -q` | ✔ 190/190 |
| Backend ruff | `.venv/bin/ruff check .` | ✔ limpio |
| Backend mypy | `.venv/bin/mypy .` | ✔ 96 archivos, 0 issues |
| Alembic | `alembic heads` | ✔ head `0011_homologacion` |
| OpenAPI | `app.openapi()['paths']` | ✔ 213 rutas (maestros 12) |
| Frontend tsc / eslint | `npx tsc -b` / `npx eslint . --max-warnings 0` | ✔ limpios |
| Frontend vitest / build | `npx vitest run` / `npx vite build` | ✔ 16/16 · build OK |

## Cobertura (002)

Maestros de terceros, productos, servicios, catálogos y atributos, con
aislamiento multiempresa y permisos.

## Pendientes de negocio (no bloquean)

- Catálogo semilla global y atributos obligatorios por rubro (CVG-002-01/02).
