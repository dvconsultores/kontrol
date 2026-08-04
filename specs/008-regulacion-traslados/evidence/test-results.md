# Resultados de pruebas — 008-REGULACION-TRASLADOS

| Campo | Valor |
|---|---|
| Fecha | 2026-08-04 |
| Rama | `feature/001-fundacion` (HEAD `7091451`) |
| Método | Auditoría profunda 001-011 (gates re-ejecutados) |

## Gates

| Gate | Comando | Resultado |
|---|---|---|
| Backend pytest (spec) | `.venv/bin/python -m pytest tests/test_regulatory.py -q` | ✔ 15/15 |
| Backend pytest (suite) | `.venv/bin/python -m pytest -q` | ✔ 190/190 |
| Backend ruff | `.venv/bin/ruff check .` | ✔ limpio |
| Backend mypy | `.venv/bin/mypy .` | ✔ 96 archivos, 0 issues |
| Alembic | `alembic heads` | ✔ head `0011_homologacion` |
| OpenAPI | `app.openapi()['paths']` | ✔ 213 rutas (regulatory 15) |
| Frontend tsc / eslint | `npx tsc -b` / `npx eslint . --max-warnings 0` | ✔ limpios |
| Frontend vitest / build | `npx vitest run` / `npx vite build` | ✔ 16/16 · build OK |

## Cobertura (008)

Organismos y permisos, vehículos y conductores, permisos/guías
(SICA/SIGESAI/SACS), evaluación y bloqueo del despacho por línea, y
contingencias regulatorias; consume `Shipment`/`ShipmentLine` de 005.

## Pendientes de negocio (no bloquean)

- Matrices oficiales por organismo, contingencias con regla oficial en UI y
  guía fiscal SENIAT con 007 (CVG-008-01/03/04).
