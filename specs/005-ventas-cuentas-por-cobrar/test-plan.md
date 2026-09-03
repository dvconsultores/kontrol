# PLAN DE PRUEBAS — 005-VENTAS-CUENTAS-POR-COBRAR

| Campo | Valor |
|---|---|
| Iniciativa | 005-ventas-cuentas-por-cobrar |
| Versión | 1.0 |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/test-plan.md` |

## 1. Estrategia

- **Unitarias**: máquinas de estado (OV/factura de venta), análisis de crédito, cálculo de saldo CxC, aplicaciones que no exceden saldo, aging, snapshot.
- **Integración**: API + PostgreSQL; reserva/picking/despacho → 003; factura → CxC (reutiliza 004); retención sufrida; contrato cobros/aplicaciones para 006; aislamiento multiempresa.
- **Concurrencia**: cobros/aplicaciones simultáneos sin sobrededucción (T-005-020).
- **E2E/UI**: Playwright (rutas de ventas), axe, responsive.

## 2. Casos de prueba

| ID | Tipo | Objetivo | Criterio de éxito |
|---|---|---|---|
| TP-005-001 | Unit | Máquina de estados OV | Transiciones válidas/inválidas DRAFT→…→CLOSED |
| TP-005-002 | Unit | Análisis de crédito | Límite/bloqueo/margen separados; excepción aprobada |
| TP-005-003 | Unit | Cotización sin reserva | Cotizar no reserva inventario |
| TP-005-004 | Integración | Reserva al aprobar | Disponible baja, físico sin cambio (via 003) |
| TP-005-005 | Integración | Picking y salida | Salida a tránsito/entregado-no-facturado con costo (via 003) |
| TP-005-006 | Integración | Bloqueo de despacho | Falta documento/venció/no coincide → bloqueado |
| TP-005-007 | Unit | Máquina de estados factura | DRAFT→…→EMITTED→PAID; CREDITED/VOIDED vinculado |
| TP-005-008 | Unit | Snapshot fiscal | Base VES y tasa snapshot por línea |
| TP-005-009 | Unit | Saldo de CxC | `balance = original − applied`; saldo calculado |
| TP-005-010 | Unit | Idempotencia de cobro | Reintento no duplica el cobro |
| TP-005-011 | Unit/Integración | Aplicación atómica | Ninguna aplicación excede saldo de origen ni destino |
| TP-005-012 | Concurrencia | Cobros simultáneos | N cobros concurrentes no sobrededucen |
| TP-005-013 | Unit | Aging | Buckets 0-30/31-60/61-90/>90 correctos |
| TP-005-014 | Unit | Retención sufrida | Registrada y aplicada por regla versionada |
| TP-005-015 | Contract | Contrato 006 | Cobros/aplicaciones cumplen el contrato y la idempotencia |
| TP-005-016 | Multiempresa | Aislamiento negativo | Empresa A no ve/afecta CxC de B |
| TP-005-017 | E2E | Orden de venta y despacho | Flujo completo hasta salida |
| TP-005-018 | E2E | Factura y CxC | Factura emite open item RECEIVABLE |
| TP-005-019 | E2E | Cobro multimoneda | Múltiples medios/monedas aplicados |
| TP-005-020 | Accesibilidad | axe + responsive | WCAG 2.2 AA en rutas de ventas |

## 3. Ambiente

- Backend: pytest + PostgreSQL 18 (integración), SQLite in-memory (unitarias), Alembic head `0005_ventas`.
- Frontend: Vitest (componentes), Playwright (E2E), axe (accesibilidad).
- CI: jobs heredados de 001 (con `KONTROL_SECRET_KEY`).

## 4. Evidencia

- Resultados de pytest, vitest, Playwright, axe y concurrencia en `evidence/`.
- Contract tests en `contracts/`.

---

# PLAN DE PRUEBAS — SPEC 030 · CRÉDITO / APROBACIÓN / RESERVA

| Nivel | Suite | Casos | Motor |
|---|---|---:|---|
| Estructural | `test_spec030_architecture.py` | 11 | lectura de código y del ORM (falla en construcción) |
| Funcional multiempresa | `test_spec030_reservation.py` | 26 | PostgreSQL 18.6, dos tenants y tres empresas |
| Concurrencia | `test_spec030_concurrency.py` | 2 | PostgreSQL 18.6, dos conexiones reales con barrera |
| Integridad hostil | `test_spec030_postgres_hostile.py` | 10 | PostgreSQL 18.6, verificando SQLSTATE |
| Migración de datos | `test_spec030_migration_0043.py` | 7 | PostgreSQL 18.6, base sembrada en `0042` |
| Extremo a extremo | `e2e/sales-orders.spec.ts` | 4 × 3 navegadores | frontend + API + backend + PostgreSQL reales |

## Qué prueba cada bloque

- **Estructural**: que el disparador siga siendo la confirmación y no sea configurable; que solo
  `confirmar_pedido` reserve; que la máquina no recupere `CREDIT_PENDING`, `APPROVED` ni `RESERVED`;
  que el índice parcial, la unicidad del saldo y los `CHECK` estén en el ORM; que la migración
  declare lo mismo; que la disponibilidad se lea bajo bloqueo y en orden determinista; que no
  aparezca un planificador local; que el despacho consuma y no libere; que `ventas:submit` exista y
  sea distinto de `ventas:approve`.
- **Funcional**: contado, crédito, rechazo, reversión, cancelación, expiración, insuficiencia,
  multilínea, sobreventa autorizada, cantidad base con presentación, listado por lotes, aislamiento
  entre empresas y tenants, auditoría y compatibilidad de la ruta genérica.
- **Concurrencia**: el caso obligatorio (disponible 10, dos pedidos de 8) y su variante con
  `allow_negative`.
- **Hostil**: las cuatro claves foráneas, la segunda reserva activa de la misma línea, el reservado
  negativo por actualización directa, la resta por debajo de cero, la cantidad no positiva, la
  coherencia línea↔pedido y la clave única del saldo.
- **Migración**: reconstrucción con línea, caso ambiguo sin línea inventada, manual, huérfana,
  renombrado de estados con evidencia, nombres de índices y checks, e idempotencia de columnas.

## Criterio de aceptación

Cero fallos. Los saltos admitidos son los ocho de `test_documents_storage.py` (S3 sin servicio real,
dependencia externa P1 declarada en `active-blockers.md`), más los que declara la propia suite
multiempresa cuando no hay PostgreSQL.
