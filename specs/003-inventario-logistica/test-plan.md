# PLAN DE PRUEBAS — 003-INVENTARIO-LOGISTICA

| Campo | Valor |
|---|---|
| Iniciativa | 003-inventario-logistica |
| Versión | 1.0 |
| Ruta | `specs/003-inventario-logistica/test-plan.md` |

## 1. Estrategia

- **Unitarias**: reglas de dominio puras (balanceo, unicidad, FEFO, valoración, máquinas de estado) en pytest.
- **Integración**: API + PostgreSQL (SQLite solo para tests unitarios; PostgreSQL para concurrencia/multiempresa), migración `0003`, aislamiento multiempresa.
- **Concurrencia**: reservas y salidas simultáneas con hilos/transacciones paralelas; verificación de no sobreadjudicación (T-003-022).
- **E2E/UI**: Playwright (rutas de inventario), axe para accesibilidad, responsive.
- **Contract**: API de integración v1 (T-003-015) validada contra 004/005 simulados.

## 2. Casos de prueba

| ID | Tipo | Objetivo | Criterio de éxito |
|---|---|---|---|
| TP-003-001 | Unit | Balanceo de movimientos | `quantity != 0`; entradas/salidas suman cero por documento |
| TP-003-002 | Unit | Inmutabilidad y reverso | Un movimiento no se edita/borra; el reverso referencia al original y queda auditado |
| TP-003-003 | Unit | Unicidad de lote | Lote duplicado rechazado según política; vencimiento coherente |
| TP-003-004 | Unit | Unicidad de serial/IMEI | Serial duplicado rechazado según política; historial completo |
| TP-003-005 | Unit | FEFO | La salida consume el lote con vencimiento más próximo; vencidos bloqueados |
| TP-003-006 | Unit | Valoración promedio | Costo promedio = suma(costo)/suma(cantidad) por producto/almacén |
| TP-003-007 | Unit | Valoración FIFO | La salida consume las capas más antiguas; `quantity_remaining ≥ 0` |
| TP-003-008 | Integración | Reserva ≤ disponible | Una reserva que excede el disponible se rechaza (o política aprobada) |
| TP-003-009 | Integración | Reconstrucción de balance | El balance se regenera desde movimientos y coincide con el esperado |
| TP-003-010 | Integración | Máquina de estados transferencia | Transiciones válidas/inválidas de DRAFT→…→CLOSED |
| TP-003-011 | Integración | Conteo → diferencias → ajuste | El ajuste requiere revisión y aprobación; genera movimiento, no edita saldo |
| TP-003-012 | Integración | Segregación de ajuste | Quien crea no aprueba; roles de revisión/a probación exigidos |
| TP-003-013 | Concurrencia | Reservas simultáneas | N reservas concurrentes no exceden el disponible (sin sobreadjudicación) |
| TP-003-014 | Concurrencia | Salidas simultáneas | Dos salidas concurrentes sobre el mismo lote no sobreadjudican |
| TP-003-015 | Multiempresa | Aislamiento negativo | La empresa A no ve ni afecta movimientos/balances de la empresa B |
| TP-003-016 | Contract | API v1 para 004/005 | `receive/reserve/release/pick/ship` cumplen el contrato y la idempotencia |
| TP-003-017 | Rendimiento | Índices y paginación | Consultas de existencias/kardex dentro del SLO con datos grandes |
| TP-003-018 | E2E | Existencias y kardex | Filtros, paginación, `allowed_actions`, sin scroll horizontal |
| TP-003-019 | E2E | Transferencia y conteo | Flujo completo hasta recepción/aprobación |
| TP-003-020 | E2E | Ajuste con aprobación | Motivo, evidencia, costo y aprobación; sin edición de saldo |
| TP-003-021 | Accesibilidad | axe + responsive | WCAG 2.2 AA en rutas de inventario |

## 3. Ambiente

- Backend: pytest + PostgreSQL 18 (integración), SQLite in-memory (unitarias), Alembic head `0003_inventario`.
- Frontend: Vitest (componentes), Playwright (E2E), axe (accesibilidad).
- CI: jobs de backend/frontend/migraciones/seguridad heredados de 001 (con `KONTROL_SECRET_KEY`).

## 4. Evidencia

- Resultados de pytest, vitest, Playwright, axe y tiempos de concurrencia en `evidence/`.
- Contract tests en `contracts/`.
