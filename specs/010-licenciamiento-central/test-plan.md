# PLAN DE PRUEBAS — 010-LICENCIAMIENTO-CENTRAL

| Campo | Valor |
|---|---|
| Iniciativa | 010-licenciamiento-central |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/010-licenciamiento-central/test-plan.md` |

> Convención: `TP-010-XXX`. Pruebas automatizadas con pytest (sqlite in-memory) y vitest (frontend). Cobertura objetivo: todas las rutas nuevas del módulo licensing.

## Backend

| ID | Escenario | Pasos clave | Resultado esperado | FR |
|---|---|---|---|---|
| TP-010-001 | Configurar servidor central | Crear `license_central_config` con URL/clave/política | Persistido y validado | FR-010-001 |
| TP-010-002 | Sincronizar licencia | Ejecutar sincronización contra fake server | `license_sync_runs` SUCCESS + evento | FR-010-002/004 |
| TP-010-003 | Offline con gracia | Sin red, dentro de `grace_days` y con `last_reliable_date` reciente | Licencia válida; evento de uso offline | FR-010-003 |
| TP-010-010 | Sincronizar entitlements | Sincronizar matriz 002-009 | Snapshot versionado creado | FR-010-010/012 |
| TP-010-011 | Bloqueo por módulo | Llamar a un módulo sin entitlement | 403 / bloqueo backend | FR-010-011 |
| TP-010-020 | Solicitar renovación | Crear `LicenseRenewalRequest` con comprobante | Estado REPORTED | FR-010-020 |
| TP-010-021 | Workflow renovación | VERIFY → ISSUED / REJECTED | Estado correcto + evento | FR-010-021 |
| TP-010-030 | Transiciones de modo | Avanzar modos hasta SECURITY_SUSPENSION | Transiciones correctas + eventos | FR-010-030 |
| TP-010-031 | Bloqueo de escrituras | Escritura de negocio en READ_ONLY/SECURITY_SUSPENSION | Bloqueada (ensure_write_allowed) | FR-010-031 |
| TP-010-032 | Histórico de eventos | Consultar `LicenseEvent` del tenant | Lista completa | FR-010-032 |
| TP-010-100 | Idempotencia y tenant | Doble sincronización; datos de otro tenant | Sin duplicados; aislamiento | FR-010-100 |
| TP-010-101 | Contrato v1 del cliente | Respuesta del fake server con formato v1 | Parseo correcto | FR-010-002 |

## Frontend

| ID | Escenario | Resultado esperado | FR |
|---|---|---|---|
| TP-010-101 | Página configuración central | Formulario y guardado OK | FR-010-101 |
| TP-010-101 | Página entitlements | Tabla de módulos con estado | FR-010-101 |
| TP-010-101 | Página renovación | Solicitud y detalle del workflow | FR-010-101 |
| TP-010-101 | Página eventos | Histórico con DataTable | FR-010-101 |

## Evidencia

- Backend: `pytest -q` (suite 001-009 + nueva licenciamiento).
- Lint/tipos: `ruff check .`, `mypy .`.
- Migración: `alembic upgrade head` (head `0010_licenciamiento`).
- Frontend: `tsc -b`, `eslint . --max-warnings 0`, `vitest run`, `vite build`.
