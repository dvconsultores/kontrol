# Resultados de pruebas — 009-REPORTES-AUDITORIA

| Campo | Valor |
|---|---|
| Fecha | 2026-08-04 |
| Rama | `feature/001-fundacion` (HEAD `7091451`) |
| Método | Auditoría profunda 001-011 (gates re-ejecutados) |

## Gates

| Gate | Comando | Resultado |
|---|---|---|
| Backend pytest (spec) | `.venv/bin/python -m pytest tests/test_reporting.py -q` | ✔ 13/13 |
| Backend pytest (suite) | `.venv/bin/python -m pytest -q` | ✔ 190/190 |
| Backend ruff | `.venv/bin/ruff check .` | ✔ limpio |
| Backend mypy | `.venv/bin/mypy .` | ✔ 96 archivos, 0 issues |
| Alembic | `alembic heads` | ✔ head `0011_homologacion` |
| OpenAPI | `app.openapi()['paths']` | ✔ 213 rutas (reporting 7) |
| Frontend tsc / eslint | `npx tsc -b` / `npx eslint . --max-warnings 0` | ✔ limpios |
| Frontend vitest / build | `npx vitest run` / `npx vite build` | ✔ 16/16 · build OK |

## Cobertura (009)

Dashboard con indicadores y vencimientos por módulo, reportes
ejecutivos/operativos/financieros/fiscales/regulatorios (solo lectura sobre
003-008), exportación auditada (CSV/PDF), jobs y timeline de auditoría
(reutiliza `AuditEvent` de 001).

## Pendientes de negocio (no bloquean)

- Plantillas PDF y marca, política de retención de exportaciones, jobs con
  cola externa y listado de jobs en UI (CVG-009-01/02/03/05).
- Contabilidad formal fuera del roadmap actual (CVG-009-04).
