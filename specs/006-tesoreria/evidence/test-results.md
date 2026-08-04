# Resultados de pruebas — 006-TESORERIA

| Campo | Valor |
|---|---|
| Fecha | 2026-08-04 |
| Rama | `feature/001-fundacion` (HEAD `7091451`) |
| Método | Auditoría profunda 001-011 (gates re-ejecutados) |

## Gates

| Gate | Comando | Resultado |
|---|---|---|
| Backend pytest (spec) | `.venv/bin/python -m pytest tests/test_treasury.py -q` | ✔ 24/24 |
| Backend pytest (suite) | `.venv/bin/python -m pytest -q` | ✔ 190/190 |
| Backend ruff | `.venv/bin/ruff check .` | ✔ limpio |
| Backend mypy | `.venv/bin/mypy .` | ✔ 96 archivos, 0 issues |
| Alembic | `alembic heads` | ✔ head `0011_homologacion` |
| OpenAPI | `app.openapi()['paths']` | ✔ 213 rutas (treasury 27) |
| Frontend tsc / eslint | `npx tsc -b` / `npx eslint . --max-warnings 0` | ✔ limpios |
| Frontend vitest / build | `npx vitest run` / `npx vite build` | ✔ 16/16 · build OK |

## Cobertura (006)

Cajas (apertura/movimientos/arqueo/pre-cierre/cierre), bancos
(transacciones/ingresos-egresos/transferencias), conciliación asistida con
reglas y resolución manual auditada, e IGTF por regla y evento; integra pagos
004 y cobros 005.

## Pendientes de negocio (no bloquean)

- Reglas de match configurables por banco, política de cierres de caja,
  integración de ingresos 005 al estado de cuenta y flujo de anticipos en UI
  (CVG-006-02..05).
