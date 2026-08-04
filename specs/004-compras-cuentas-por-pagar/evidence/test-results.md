# EVIDENCIA DE PRUEBAS — 004-COMPRAS-CUENTAS-POR-PAGAR

| Campo | Valor |
|---|---|
| Iniciativa | 004-compras-cuentas-por-pagar |
| Fecha | 2026-08-04 |
| Ruta | `specs/004-compras-cuentas-por-pagar/evidence/test-results.md` |

## Backend (pytest)

```
$ python -m pytest -q
74 passed
```

17 nuevas pruebas de compras (`tests/test_purchasing.py`):
- `TestOrdenDeCompra`: máquina de estados completa (DRAFT→…→CLOSED) y transición inválida rechazada.
- `TestRecepcionIntegra003`: aceptar recepción registra el movimiento y saldo **vía 003**; lotes; la orden pasa a PARTIALLY_RECEIVED; requiere orden aprobada.
- `TestFacturaProveedor`: duplicidad rechazada, flujo hasta POSTED + creación de OpenItem, conciliación triple con variación (EXCEPTION), reverso bloqueado con saldo pendiente.
- `TestCxP`: pago aprobado → aplicación reduce saldo; la aplicación no excede saldo de destino ni de origen; pago completo cierra el open item y marca la factura PAID; nota de crédito reduce saldo; anticipo se imputa; aging por buckets.
- `TestRetencion`: estados de retención y aplicación que reduce saldo (EMITIDA).
- `TestMultiempresa`: aislamiento negativo.

## Compuertas

| Herramienta | Resultado |
|---|---|
| ruff | All checks passed (app, scripts, tests, migración) |
| mypy | Success: no issues found in 60 source files |
| alembic heads | `0004_compras (head)` |
| OpenAPI | 32 endpoints `/purchasing/*`; total 96 rutas |

## Frontend

- tsc: sin errores.
- eslint --max-warnings 0: limpio.
- vitest: 16/16.
- vite build: OK (461 kB JS / 136 kB gzip).

## Notas

- La recepción invoca el motor de 003 (`ENTRADA_RECEPCION` + lotes/seriales + capas de costo); 004 no duplica saldos.
- La retención es estructural (referencia a reglas versionadas); el cálculo fiscal completo es de 007.
- La conciliación bancaria de pagos es de 006 (contrato `Payment`/`Application`).
