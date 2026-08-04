# RESEARCH — 003-INVENTARIO-LOGISTICA

| Campo | Valor |
|---|---|
| Iniciativa | 003-inventario-logistica |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Arquitecto técnico / Arquitecto de datos |
| Ruta | `specs/003-inventario-logistica/research.md` |

## 1. Motor de movimientos (fuente de verdad)

- `InventoryMovement` es la **única fuente** de saldos (DOC-03 §5). `InventoryBalance` es una cache reconstruible.
- Invariantes: `quantity != 0`; cada documento de origen genera movimientos que suman cero por agregado (balanceo); no UPDATE/DELETE físico (Constitución P5).
- Reversos: un movimiento reverso **referencia** al original (`reversed_by_id`) y queda auditado; nunca se elimina el original.
- Idempotencia: `Idempotency-Key` en POST críticos (DOC-03 §14) para reintentos de recepción/salida/reserva.

## 2. Concurrencia y consistencia (sin sobreadjudicación)

- Reservas y salidas se ejecutan en **transacciones atómicas** con `SELECT ... FOR UPDATE` sobre las filas de balance/lote afectadas (DOC-03 §12).
- Alternativa para alto volumen: `pg_advisory_xact_lock` por clave `(company_id, product_id, warehouse_id)`.
- `available = on_hand − reserved`; la reserva falla (o queda pendiente) si `reserved + delta > on_hand`, salvo política aprobada de sobreadjudicación.
- Versión/ETag (DOC-03 §14) evita sobrescritura silenciosa en entidades editables (planes de conteo, transferencias).

## 3. FEFO y vencimientos

- Política FEFO: al salir, se prioriza el lote con `expiry_date` más próximo (o el más antiguo si no hay vencimiento) según el perfil de trazabilidad del producto (DOC-02 §5).
- Bloqueo de vencidos: un lote con `expiry_date < today` no es elegible para salida (salvo política de excepción aprobada).
- El perfil de inventario (002) determina si el producto usa lote, serial o lote+vencimiento; 003 consume esos perfiles, no los redefine.

## 4. Valoración por capas

- `CostLayer` registra `quantity_in`, `quantity_remaining`, `unit_cost`, moneda, tasa fiscal y `landed_cost` (DOC-03 §5).
- **Promedio ponderado**: costo unitario = suma(costo remanente)/suma(cantidad remanente) por producto/almacén.
- **FIFO**: la salida consume las capas más antiguas en orden.
- El método proviene de un `CostingProfile` **versionado** (P8); el default es promedio ponderado (SU-003-01). Las capas históricas nunca se reescriben.
- Decimal exacto: cantidades y costos con precisión controlada (DOC-01 §3).

## 5. Cache de balance reconstruible

- `InventoryBalance` se actualiza de forma **incremental** dentro de la misma transacción del movimiento (consistencia fuerte) y, para reconstrucción, se regenera desde movimientos bajo demanda o por job/outbox (SU-003-05).
- Índices: `(company_id, product_id, warehouse_id, location_id, lot_id, serial_id, state)` y `(company_id, product_id, expiry_date)` para FEFO.

## 6. Integración con 004/005 (API v1)

- 003 expone servicios de dominio: `receive`, `reserve`, `release`, `pick`, `ship`, `adjust`, `transfer`.
- 004 (compras) llama `receive` en la recepción; 005 (ventas) llama `reserve` al aprobar la orden y `ship` en la salida.
- Los documentos de origen se referencian (`document_ref`) pero 003 no emite documentos fiscales (CL-003-01).
- Contrato de errores y versionado heredados de 001 (DOC-03 §14).

## 7. Estados y máquinas de estado

- Lote/serial: DISPONIBLE → RESERVADO → TRANSITO → CUARENTENA → VENCIDO/RECHAZADO/DESECHO (transiciones autorizadas).
- Transferencia: DRAFT → SUBMITTED → APPROVED → PICKING → IN_TRANSIT → PARTIALLY_RECEIVED/RECEIVED → CLOSED (DOC-03 §13).
- Conteo: plan → congelamiento/lectura → conteo → diferencias → aprobación → ajuste (DOC-02 §8).
- Ajuste: segregación crea (Almacén) → revisa (Costos/auditor) → aprueba (Aprobador) (DOC-02 §12).

## 8. Seguridad

- `allowed_actions` calculadas en backend por estado y permiso (P6); el frontend solo muestra.
- Aislamiento multiempresa: `company_id` en cada agregado; pruebas negativas obligatorias.
- Auditoría integral en movimientos, lotes, seriales, reservas, conteos y ajustes (DOC-01 §3).

## 9. Referencias técnicas (stack 001/002)

- PostgreSQL 18: transacciones, `FOR UPDATE`, advisory locks, índices parciales, restricciones CHECK para `quantity != 0` y unicidad.
- SQLAlchemy 2.0 + Alembic (head `0002_maestros` → `0003_inventario`).
- FastAPI (backend) + React 19 / react-router 8 / TanStack Query (frontend) — estándar DOC-08.
- Los patrones de concurrencia se validarán con pruebas simultáneas (T-003-022).
