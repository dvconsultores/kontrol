# Resultados de pruebas — 007-NUCLEO-FISCAL

| Campo | Valor |
|---|---|
| Fecha | 2026-08-04 |
| Rama | `feature/001-fundacion` (HEAD `7091451`) |
| Método | Auditoría profunda 001-011 (gates re-ejecutados) |

## Gates

| Gate | Comando | Resultado |
|---|---|---|
| Backend pytest (spec) | `.venv/bin/python -m pytest tests/test_fiscal.py -q` | ✔ 21/21 |
| Backend pytest (suite) | `.venv/bin/python -m pytest -q` | ✔ 190/190 |
| Backend ruff | `.venv/bin/ruff check .` | ✔ limpio |
| Backend mypy | `.venv/bin/mypy .` | ✔ 96 archivos, 0 issues |
| Alembic | `alembic heads` | ✔ head `0011_homologacion` |
| OpenAPI | `app.openapi()['paths']` | ✔ 213 rutas (fiscal 23) |
| Frontend tsc / eslint | `npx tsc -b` / `npx eslint . --max-warnings 0` | ✔ limpios |
| Frontend vitest / build | `npx vitest run` / `npx vite build` | ✔ 16/16 · build OK |

## Cobertura (007)

Reglas fiscales versionadas, numeración y números de control, emisión de
documentos fiscales, notas de crédito/débito, retenciones (reutiliza 004),
libros reconstruibles y períodos fiscales.

## Pendientes de negocio (no bloquean)

- Formatos de libros/PDF, alícuotas exactas del ejercicio, retenciones
  unificadas y contingencia de facturación en UI (CVG-007-01/02/05/06).
- Acto formal de homologación de la versión fiscal → cubierto por 011.
