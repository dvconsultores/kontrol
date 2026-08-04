# PLAN — 003-INVENTARIO-LOGISTICA

| Campo | Valor |
|---|---|
| Iniciativa | 003-inventario-logistica |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Arquitecto de software / Arquitecto de datos |
| Ruta | `specs/003-inventario-logistica/plan.md` |

## 1. Validación contra la Constitución

| Principio | Cumplimiento |
|---|---|
| P1 Spec antes que código | ✔ Este plan no implementa |
| P2 Autorización expresa | ✔ Se detiene en `/speckit.analyze` |
| P3 Trazabilidad | ✔ `traceability-matrix.md` |
| P5 Datos históricos protegidos | ✔ movimientos inmutables; reverso vinculado; saldos calculados |
| P6 Seguridad en backend | ✔ permisos/alcance/estados validados en backend |
| P7 Frontend uniforme | ✔ patrones WF y componentes compartidos |
| P8 No hardcodear reglas | ✔ tipos de movimiento, métodos de costeo, FEFO y estados versionados |
| P9 Instalación independiente | ✔ hereda 001 |
| P11 Accesibilidad/responsive | ✔ hereda 001 |
| P13 Integridad transaccional | ✔ bloqueo de fila, idempotencia, versión/ETag |
| P15 Datos del cliente protegidos | ✔ hereda 001 |
| P17 No retrabajo visual | ✔ componentes compartidos |
| P18 Política de modales | ✔ formularios/pantallas completas (ADR-015) |

**Resultado: compatible con la Constitución.**

## 2. Arquitectura

Módulo de backend `inventory` (extiende la fundación de 001 y maestros de 002):

| Submódulo | Responsabilidad en 003 |
|---|---|
| `inventory/warehouses` | Warehouse + Location (custodia; maestros con estados) |
| `inventory/movements` | Motor de movimientos balanceados e inmutables + tipos versionados + reversos |
| `inventory/lots` | InventoryLot, ProductSerial (unicidad, vencimiento, FEFO, estados) |
| `inventory/reservations` | Reservation (reserva/liberación/expiración; disponible = físico − reservas) |
| `inventory/transfers` | Transfer + líneas + máquina de estados + diferencias |
| `inventory/counts` | StockCount (plan, congelamiento, líneas, diferencias, aprobación) |
| `inventory/adjustments` | Ajustes con motivo/evidencia/costo/aprobación → movimientos |
| `inventory/costing` | CostLayer (capas, valoración promedio/FIFO, landed cost) |
| `inventory/balances` | InventoryBalance (cache reconstruible) + kardex |

Frontend: módulo `inventario/` (`existencias`, `kardex`, `transferencias`, `conteos`, `ajustes`, `almacenes`), reutilizando `design-system` y componentes de 001/002 (DataTable, AsyncCombobox, formularios completos).

## 3. Estructura de archivos esperada

```text
resources/backend/app/modules/inventory/
├── warehouses/   (models, service, api, tests)
├── movements/    (models, service, api, tests)
├── lots/         (models, service, api, tests)
├── reservations/ (models, service, api, tests)
├── transfers/    (models, service, api, tests)
├── counts/       (models, service, api, tests)
├── adjustments/  (models, service, api, tests)
├── costing/      (models, service, api, tests)
└── balances/     (models, service, api, tests)
resources/backend/alembic/versions/0003_inventario.py
resources/frontend/src/modules/inventario/
├── existencias/  kardex/  transferencias/  conteos/  ajustes/  almacenes/
specs/003-inventario-logistica/... (este paquete)
```

## 4. Datos y migraciones

- Modelo en `data-model.md`; migración Alembic `0003_inventario` (upgrade/downgrade) sobre head `0002_maestros`.
- Seeds idempotentes: tipos de movimiento base (ENTRADA_RECEPCION, SALIDA_DESPACHO, TRANSFERENCIA_SALIDA, TRANSFERENCIA_ENTRADA, AJUSTE_POSITIVO, AJUSTE_NEGATIVO, CONTEO, DEVOLUCION_CLIENTE, DEVOLUCION_PROVEEDOR, REVERSO) y estados de lote/serial — versionados, editables por la empresa.
- Constraints: unique serial/IMEI según política; unique lote según política; movimiento balanceado (`quantity != 0`); reservas ≤ disponible; multiempresa en cada agregado; versión/ETag en entidades editables.

## 5. Contratos

- OpenAPI con endpoints REST de inventario (`/inventory/*`): existencias, kardex, movimientos, lotes, seriales, reservas, transferencias, conteos, ajustes, capas de costo.
- `allowed_actions` calculadas en backend.
- API de integración v1 para 004/005: `receive`, `reserve`, `release`, `pick`, `ship` (servicios invocables sin duplicar lógica de saldos).
- Contrato de errores heredado de 001; idempotencia en POST críticos; transiciones por endpoints explícitos (`/submit`, `/approve`, `/cancel`, `/confirm`, `/reverse`).

## 6. Pruebas

Plan en `test-plan.md`: unitarias (balanceo, unicidad lote/serial, FEFO, valoración promedio/FIFO, máquina de estados), integración (API/PostgreSQL, aislamiento multiempresa, concurrencia de reservas con bloqueo), E2E (existencias, kardex, transferencia, conteo→ajuste, ajuste con aprobación), accesibilidad/responsive.

## 7. Fases de implementación (para `/speckit.implement`)

1. Modelos + migración `0003_inventario` + seeds (tipos de movimiento, estados).
2. Maestros de custodia: `warehouses` (Warehouse + Location).
3. Motor de movimientos: servicio transaccional balanceado + reversos + tipos versionados.
4. Lotes y seriales: unicidad, vencimiento, FEFO, estados.
5. Reservas: reserva/liberación/expiración con bloqueo y disponible.
6. Transferencias: máquina de estados + diferencias.
7. Conteos y ajustes: plan, congelamiento, diferencias, aprobación, movimientos.
8. Costos: capas + valoración promedio/FIFO + costo de salida.
9. Balances y kardex: cache reconstruible + consultas paginadas.
10. API de integración v1 para 004/005.
11. Frontend: existencias, kardex, transferencias, conteos, ajustes, almacenes.
12. Tests (unit/integración/E2E), concurrencia y CI.
13. Documentación y evidencia.

## 8. Entregables de esta fase documental

Este plan forma parte de la fase documental de `003-inventario-logistica`; **no autoriza implementación**. La implementación requiere `/speckit.analyze` consistente, **001 certificada**, **002 implementado** y autorización expresa.

## 9. Estado de aprobación

| Elemento | Estado |
|---|---|
| Arquitectura | ✔ |
| Datos | ✔ (data-model.md) |
| Pruebas | ✔ (test-plan.md) |
| Aprobación | Pendiente |
