# CONVERGENCIA — 003-INVENTARIO-LOGISTICA

| Campo | Valor |
|---|---|
| Iniciativa | 003-inventario-logistica |
| Versión | 1.0 |
| Ruta | `specs/003-inventario-logistica/convergence.md` |

## 1. Propósito

Registrar brechas y nuevas tareas tras la implementación. `/speckit.converge` se ejecuta al cierre.

## 2. Brechas identificadas

| ID | Brecha | Acción | Responsable | Estado |
|---|---|---|---|---|
| CVG-003-01 | Política de costeo por defecto por empresa | Decisión de negocio (CL-003-11) | Costos | Pendiente |
| CVG-003-02 | Política de vencidos (bloqueo anticipado, destino) | Decisión (CL-003-12) | Almacén | Pendiente |
| CVG-003-03 | Política de ubicaciones/picking | Decisión (CL-003-14) | Logística | Pendiente |
| CVG-003-04 | Reservas: expiración por job/programado | Automatizar `expire_reservations` | Backend | Pendiente (job) |
| CVG-003-05 | Picking y despacho completos (PickList/shipment) | Dependen de Spec 005 (ventas) | Arquitecto | Pendiente (005) |
| CVG-003-06 | Recepción de compra completa | Depende de Spec 004 (compras) | Arquitecto | Pendiente (004) |

## 3. Implementado (003)

| Elemento | Estado |
|---|---|
| Modelos (15 tablas nuevas) + migración `0003_inventario` | ✔ |
| Maestros de custodia reutilizados de 001 (`organization`: warehouses/locations) | ✔ (CL-003-02) |
| Motor de movimientos balanceados e inmutables + reverso vinculado | ✔ |
| Tipos de movimiento versionados + seeds idempotentes | ✔ |
| Lotes, seriales/IMEI (unicidad), FEFO y transiciones de estado | ✔ |
| Reservas (reserva/liberación/expiración; disponible = físico − reservas) | ✔ |
| Balance reconstruible (`recompute`) + existencias + kardex | ✔ |
| Transferencias con máquina de estados y diferencias | ✔ |
| Conteos y ajustes con segregación (crea/revisa/aprueba) | ✔ |
| Costos por capas (promedio/FIFO versionado) + valoración | ✔ |
| API `/inventory/*` (25 endpoints) + integración v1 (`receive`/`ship`) | ✔ |
| Frontend: existencias, kardex, transferencias, conteos, ajustes | ✔ |

## 4. Validación local

| Compuerta | Resultado |
|---|---|
| Backend pytest | ✔ 57/57 (incluye 20 de inventario) |
| Backend ruff | ✔ limpio (incluye migración) |
| Backend mypy | ✔ 54 archivos, 0 issues |
| Alembic | ✔ head `0003_inventario` (upgrade/downgrade) |
| OpenAPI | ✔ 25 endpoints `/inventory/*` (64 rutas totales) |
| Frontend tsc | ✔ limpio |
| Frontend eslint | ✔ limpio |
| Frontend vitest | ✔ 16/16 |
| Frontend build | ✔ build de producción OK |

## 5. Estado

| Elemento | Estado |
|---|---|
| Fase documental | ✔ |
| Implementación | ✔ (sujeta a 001 certificada + 002 implementado + autorización expresa) |
| Certificación (Docker/CI/legal, integración 004/005) | Pendiente — depende de 001 certificada y de Specs 004/005 |
