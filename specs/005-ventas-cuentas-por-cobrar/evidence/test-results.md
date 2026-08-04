# EVIDENCIA DE PRUEBAS — 005-VENTAS-CUENTAS-POR-COBRAR

| Campo | Valor |
|---|---|
| Iniciativa | 005-ventas-cuentas-por-cobrar |
| Fecha | 2026-08-04 |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/evidence/test-results.md` |

## Backend (pytest)

```
$ python -m pytest -q
85 passed
```

11 nuevas pruebas de ventas (`tests/test_sales.py`):
- `TestOrdenDeVenta`: máquina de estados (DRAFT→…→RESERVED) y **reserva vía 003** (disponible baja, físico sin cambio); transición inválida rechazada.
- `TestDespacho`: validación documental → confirmación de salida (movimiento OUT vía 003 + liberación de reservas); el despacho exige validación previa.
- `TestFacturaVenta`: emisión → open item **RECEIVABLE**; anulación bloqueada con cobro aplicado.
- `TestCxC`: cobro aprobado → aplicación reduce saldo; pago completo cierra el open item y marca la factura PAID; nota de crédito reduce saldo; aging por buckets (RECEIVABLE).
- `TestMultiempresa`: aislamiento negativo.

## Compuertas

| Herramienta | Resultado |
|---|---|
| ruff | All checks passed (app, scripts, tests, migración) |
| mypy | Success: no issues found in 66 source files |
| alembic heads | `0005_ventas (head)` |
| OpenAPI | 27 endpoints `/sales/*`; total 123 rutas |

## Frontend

- tsc: sin errores.
- eslint --max-warnings 0: limpio.
- vitest: 16/16.
- vite build: OK (469 kB JS / 137 kB gzip).

## Notas

- La reserva/picking/despacho invocan el motor de 003; el despacho libera las reservas cumplidas.
- La CxC reutiliza el motor de aplicaciones de 004 (open items RECEIVABLE, cobros IN, aplicaciones atómicas, anticipos, retenciones sufridas, aging).
- La factura de venta es comercial (snapshot fiscal); la emisión fiscal formal es de 007. La conciliación bancaria de cobros es de 006.
