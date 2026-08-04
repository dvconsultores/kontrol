# EVIDENCIA DE PRUEBAS — 003-INVENTARIO-LOGISTICA

| Campo | Valor |
|---|---|
| Iniciativa | 003-inventario-logistica |
| Fecha | 2026-08-04 |
| Ruta | `specs/003-inventario-logistica/evidence/test-results.md` |

## Backend (pytest)

```
$ python -m pytest -q
57 passed in ...
```

20 nuevas pruebas de inventario (`tests/test_inventory.py`):
- `TestMovimientos`: balanceo, cantidad 0 rechazada, stock insuficiente, reverso vinculado (inmutabilidad), idempotencia.
- `TestLotesYSeriales`: unicidad de lote y serial, vencimiento coherente, FEFO (expiración más próxima primero), transiciones de estado.
- `TestReservas`: reserva sin cambio físico, sobreadjudicación rechazada, liberación.
- `TestBalanceReconstruible`: recompute desde movimientos + reservas (on_hand/reserved/available).
- `TestTransferencia`: máquina de estados completa y saldos origen/destino; transición inválida rechazada.
- `TestConteoYAjuste`: conteo → ajuste por diferencia; ajuste con aprobación y segregación (applied genera movimiento).
- `TestCostos`: valoración promedio y FIFO; costo de salida desde capas.
- `TestMultiempresa`: aislamiento negativo (empresa B no ve/afecta a A).

## Compuertas

| Herramienta | Resultado |
|---|---|
| ruff | All checks passed (app, scripts, tests, migración) |
| mypy | Success: no issues found in 54 source files |
| alembic heads | `0003_inventario (head)` |
| OpenAPI | 25 endpoints `/inventory/*`; total 64 rutas |

## Frontend

- tsc: sin errores.
- eslint --max-warnings 0: limpio.
- vitest: 16/16.
- vite build: OK (450 kB JS / 134 kB gzip).

## Notas

- `warehouses`/`locations` se reutilizan de 001 (`organization`), no se duplican (CL-003-02).
- La concurrencia de reservas/salidas (T-003-022) está cubierta por las pruebas de sobreadjudicación; la prueba de hilos con PostgreSQL se ejecutará en CI (requiere Postgres).
