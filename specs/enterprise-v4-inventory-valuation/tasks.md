# Tasks · V4

Columnas: EXECUTOR · MODEL · SECURITY_SENSITIVE · EGRESS_SAFE · RETRY_MAX · FILES · TEST · DONE_WHEN · STATUS.

| ID | Tarea | EXECUTOR | MODEL | SEC | EGRESS | RETRY | FILES | TEST | DONE_WHEN | STATUS |
|---|---|---|---|---|---|---|---|---|---|---|
| T001 | Reproducir los defectos en rojo sobre PostgreSQL | CLAUDE | n-a | no | n-a | 2 | `tests/test_v4_inventory_valuation.py` | la propia suite | 16 rojos documentados | COMPLETE |
| T002 | Migración 0130: consumos, enlace capa→movimiento, permiso `inventario:recompute` | CLAUDE | n-a | sí (permisos, migración) | n-a | 2 | `alembic/versions/0130_*`, `models.py`, `setup/api.py` | upgrade/downgrade/upgrade en PG | cabeza única, permiso otorgado | COMPLETE |
| T003 | Registro de consumo y restauración (autoridad de valor) | CLAUDE | n-a | sí (costeo) | n-a | 2 | `inventory/service.py` | FIFO, landed, parcial | valor conservado | COMPLETE |
| T004 | Transferencia: envío con bloqueo, mercancía ubicada, recepción acumulativa, reversión | CLAUDE | n-a | sí (concurrencia, costeo) | n-a | 2 | `inventory/service.py`, `inventory/api.py` | transferencias, concurrencia, reversión | 0 sobretransferencia; B→A exacto | COMPLETE |
| T005 | Reverso simétrico de movimientos | CLAUDE | n-a | sí (costeo) | n-a | 2 | `inventory/service.py` | reversión entrada/salida/estado/doble | compensación exacta | COMPLETE |
| T006 | Ajuste `apply` y conteo `start`, valorados | CLAUDE | n-a | sí (costeo) | n-a | 2 | `inventory/service.py` | ajustes y conteos | ledger y valor coherentes | COMPLETE |
| T007 | Recálculo con permiso, auditoría y reservas pendientes | CLAUDE | n-a | sí (permisos) | n-a | 2 | `inventory/api.py`, `inventory/service.py` | permiso 403, auditoría | 403 sin permiso | COMPLETE |
| T008 | Catálogo de auditoría de las acciones nuevas | CLAUDE | n-a | no | n-a | 2 | `shared/audit_catalog_entries.py` | pruebas de auditoría | eventos catalogados | COMPLETE |
| T009 | Nombres en listados (API) | CLAUDE | n-a | no | n-a | 2 | `inventory/api.py` | E2E | sin UUID principal | COMPLETE |
| T010 | UI Conteos, Ajustes, Movimientos | DEEPSEEK | deepseek-v4-flash | no | sí | 2 | 3 páginas + `api/types.ts` | typecheck, lint, Vitest | nombres, `start`, esperado opcional | COMPLETE (AUDIT_PASS, intento 1) |
| T011 | UI Transferencias: valor, recepción por línea, reversión | DEEPSEEK → CLAUDE | deepseek-v4-pro | no | sí | 2 | `TransferenciasPage.tsx`, `api/types.ts` | E2E-V4-01 | recorrido completo | COMPLETE (3 AUDIT_REJECT; tope agotado; implementada por Claude) |
| T012 | E2E de transferencia y reversión con Axe | CLAUDE | n-a | no | n-a | 2 | `e2e/v4-transferencias.spec.ts` | Playwright PG | pasa | COMPLETE |
| T013 | E2E de landed cost → transferencia | CLAUDE | n-a | no | n-a | 2 | `e2e/importaciones.spec.ts` (paso 17) | Playwright PG | destino conserva landed | PARTIAL: verificado en corrida diagnóstica; la E2E canónica de importaciones falla antes por un BASELINE ajeno (impresión del PDF) |
| T014 | Mutaciones | CLAUDE | n-a | no | n-a | 2 | — | 16 mutantes | todos mueren | COMPLETE |
| T015 | Regresión PG dirigida y completa | CLAUDE | n-a | no | n-a | 2 | — | pytest PG | 0 fallos nuevos | ver CIERRE |
| T016 | Rebaseline Enterprise y evidencia | CLAUDE | n-a | no | n-a | 2 | docs | revisión | filas afectadas actualizadas | ver CIERRE |
