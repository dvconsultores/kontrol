# CRITERIOS DE ACEPTACIÓN — 010-LICENCIAMIENTO-CENTRAL

| Campo | Valor |
|---|---|
| Iniciativa | 010-licenciamiento-central |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/010-licenciamiento-central/acceptance-criteria.md` |

> Convención: `AC-010-XXX`. Cada AC vincula un FR (ver traceability-matrix.md).

## Configuración y sincronización

| ID | Criterio | FR |
|---|---|---|
| AC-010-001 | El administrador puede configurar URL del servidor central, clave pública y política de sincronización (manual + programada) y persistirla. | FR-010-001 |
| AC-010-002 | Al sincronizar, se registra una ejecución en `license_sync_runs` (SUCCESS/FAILED) y un evento en `LicenseEvent`. | FR-010-002, FR-010-004 |
| AC-010-003 | Con red: la licencia se verifica contra el central (contrato v1). Sin red: se tolera con `last_reliable_date` dentro de `grace_days`. | FR-010-003 |

## Entitlements

| ID | Criterio | FR |
|---|---|---|
| AC-010-010 | La matriz de entitlements (002-009) se sincroniza y se guarda un snapshot versionado. | FR-010-010, FR-010-012 |
| AC-010-011 | Un módulo sin entitlement queda bloqueado en backend (denegación por defecto). | FR-010-011 |

## Renovación

| ID | Criterio | FR |
|---|---|---|
| AC-010-020 | El administrador solicita renovación adjuntando comprobante; el proveedor puede VERIFICAR y emitir ISSUED o REJECTED. | FR-010-020, FR-010-021 |

## Modos y auditoría

| ID | Criterio | FR |
|---|---|---|
| AC-010-030 | Las transiciones FULL_ACCESS → RENEWAL_NOTICE → CRITICAL_RENEWAL_NOTICE → READ_ONLY → SECURITY_SUSPENSION son correctas y registradas. | FR-010-030 |
| AC-010-031 | En READ_ONLY/SECURITY_SUSPENSION las escrituras de negocio quedan bloqueadas (ensure_write_allowed). | FR-010-031 |
| AC-010-032 | El historial de eventos de licencia es consultable (activación, sincronización, renovación, modo). | FR-010-032 |
| AC-010-100 | Sincronización idempotente y aislada por tenant; montos con decimal exacto. | FR-010-100 |
| AC-010-101 | Frontend: configuración central, sincronización, entitlements, renovación y eventos operativos. | FR-010-101 |
