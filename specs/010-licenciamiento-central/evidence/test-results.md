# Resultados de pruebas — 010-LICENCIAMIENTO-CENTRAL

| Campo | Valor |
|---|---|
| Fecha | 2026-08-04 |
| Rama | `feature/001-fundacion` (HEAD `7091451`) |
| Método | Auditoría profunda 001-011 (gates re-ejecutados) |

## Gates

| Gate | Comando | Resultado |
|---|---|---|
| Backend pytest (spec) | `.venv/bin/python -m pytest tests/test_licensing_central.py -q` | ✔ 15/15 |
| Backend pytest (suite) | `.venv/bin/python -m pytest -q` | ✔ 190/190 |
| Backend ruff | `.venv/bin/ruff check .` | ✔ limpio |
| Backend mypy | `.venv/bin/mypy .` | ✔ 96 archivos, 0 issues |
| Alembic | `alembic heads` | ✔ head `0011_homologacion` |
| OpenAPI | `app.openapi()['paths']` | ✔ 213 rutas (licensing 10) |
| Frontend tsc / eslint | `npx tsc -b` / `npx eslint . --max-warnings 0` | ✔ limpios |
| Frontend vitest / build | `npx vitest run` / `npx vite build` | ✔ 16/16 · build OK |

## Cobertura (010)

Configuración del servidor central, sincronización (contrato v1) idempotente,
tolerancia offline con reloj confiable, entitlements por módulo 002-009 con
snapshots, renovación con comprobante (workflow) y refuerzo de modos.

## Pendientes de negocio (no bloquean)

- Servidor central real (externo), días de gracia por plan, scheduler y
  contrato v2 de revocación (CVG-010-01..04).
