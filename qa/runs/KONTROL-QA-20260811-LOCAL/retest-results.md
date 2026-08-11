# RE-TEST FUNCIONAL — RUN `KONTROL-QA-20260811-LOCAL` (backend local corregido)

Fecha: 2026-08-11 · Backend: local (uvicorn, SQLite) · Harness: TestClient de la app real + E2E in-process
Herramienta: `qa/functional-e2e-inprocess.py`

## Resultado general
**19/20 PASS** (procesos de negocio operativos). 1 hallazgo pendiente (cobertura de auditoría).

## Bugs reales detectados y CORREGIDOS
### KQA-100 (CRITICAL) — Decimal+float (regresión de la migración Numeric)
- `recompute_invoice_total` (purchasing/sales) mezclaba `Decimal` (fila refrescada de la BD) con `float` (línea nueva en memoria) → `TypeError` al sumar totales.
- `open_item_balance`, `_source_available`, `_reduce_source`, `apply_source`, `apply_credit_note` restaban/sumaban `Decimal` con `float` (p.ej. `Payment.amount` Numeric − `Payment.applied` Float).
- Rompía: factura proveedor POSTED, pago, cobro, notas de crédito, CxC/CxP.
- **Fix**: coerción `float()` en la aritmética (preserva semántica previa). Commit `17c8112`.

### KQA-101 (HIGH) — Recepción no completaba en instalación fresca
- `accept_receipt` requería el tipo de movimiento `ENTRADA_RECEPCION`, que no existía en una instalación nueva → `404 MOVEMENT_TYPE_NOT_FOUND` → el inventario nunca se actualizaba y rompía reserva/despacho en cascada.
- **Fix**: auto-configuración idempotente de tipos de movimiento base (`ENTRADA_RECEPCION`, `SALIDA_DESPACHO`, `TRANSFERENCIA_*`, `CONTEO`, `AJUSTE_*`, `REVERSO`). Commit `17c8112`.

## Hallazgo pendiente (no bloquea flujos)
### KQA-102 (HIGH) — Cobertura de auditoría
- Solo `identity_access` registra eventos de auditoría (login/usuarios/roles). Los módulos de negocio (empresa, sucursales, almacenes, clientes, proveedores, productos, compras, ventas, facturas, cobros, pagos, notas) NO registran eventos → en todo el E2E solo hubo 2 eventos.
- Requerimiento QA (sección 66) pide auditar esas operaciones. Recomendado: instrumentar `record_audit` en los servicios de negocio (actor, entidad, before/after). No implementado en esta pasada para evitar cambios amplios apresurados.

## Matriz de flujos (E2E in-process)
| # | Flujo | Resultado |
|---|---|---|
| 1 | Login | PASS |
| 2 | Empresa GLOBAL DV | PASS |
| 3 | Sucursales VAL-QA / CCS-QA | PASS |
| 4 | Almacenes ALM-VAL-QA / ALM-CCS-QA | PASS |
| 5 | Proveedores ALFA/BETA + Clientes ORION/NOVA | PASS |
| 6 | Productos QA + servicio | PASS |
| 7 | Orden de compra OC-QA-0001 (aprobada) | PASS |
| 8 | Recepción RC-QA-0001 (confirm+quality+accept) | PASS |
| 9 | Factura proveedor FAC-QA-ALFA-0001 (POSTED) | PASS |
| 10 | Conciliación triple-match | PASS |
| 11 | Pago y aplicación CxP (saldo 0) | PASS |
| 12 | Inventario MONITOR=10 / TECLADO=20 | PASS |
| 13 | Cotización COT-QA-0001 | PASS |
| 14 | Orden de venta OV-QA-0001 (RESERVED) | PASS |
| 15 | Despacho PK/DESP-QA-0001 (validate) | PASS |
| 16 | Factura de venta (EMITTED + CxC) | PASS |
| 17 | Cobro y aplicación CxC (saldo 0) | PASS |
| 18 | Devolución de venta DEV-QA-0001 | PASS |
| 19 | Nota de crédito NC-QA-0001 (post) | PASS |
| 20 | Transferencia TR-QA-0001 Valencia→Caracas | PASS |
| 21 | Auditoría registra eventos | FAIL (KQA-102) |

## Estado producción (kontrol.globaldv.net)
- La instancia pública seguía con la API en **502** (ver RUN `KONTROL-QA-20260810-234937`). El código local está sano (health 200, E2E 19/20, pytest 207).
- La causa del 502 en producción es de despliegue/infraestructura (contenedor backend caído / nginx upstream / migración contra PG) — requiere acceso al servidor para: revisar logs del contenedor, `docker compose up -d --force-recreate backend`, verificar `alembic upgrade head` en PG, y el enrutado de `/health/*` en nginx (KQA-002).

## Validación
- pytest 207/207 (incluye 3 tests de regresión en `tests/test_qa_fixes.py`) · ruff · mypy.
