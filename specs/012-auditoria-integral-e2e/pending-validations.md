# Spec 012 — Validaciones Pendientes (T-12..T-16)

Estado actualizado (2026-08-10): parte quedó **resuelta con código/entregables**;
el resto requiere infraestructura/ambiente autorizado.

## T-12 · Navegadores reales + responsive + accesibilidad — PARCIAL (spec axe listo)
- Añadido `e2e/accessibility.spec.ts` (axe-core / WCAG 2.2 AA): login + 12 páginas autenticadas
  (sin violaciones serias/críticas). Dependencia `@axe-core/playwright` instalada.
- **Pendiente ejecutar**: levantar el stack (`compose.dev`) con credenciales E2E
  (`KONTROL_E2E_USER`/`KONTROL_E2E_PASSWORD`) y correr
  `npm run test:e2e -- --project=chromium e2e/accessibility.spec.ts`.
- Pendiente manual: dispositivos reales (BrowserStack/Sauce/LambdaTest), viewports 320–1920, zoom 110–200%.

## T-13 · Seguridad — RESUELTO (hallazgos corregidos + suite)
- **Fix crítico**: fugas de tenant en organización (companies/branches/establishments/warehouses/locations
  no filtraban por tenant) → ahora scoped por `Company.tenant_id`; escrituras validan pertenencia (404).
- **Fix**: `create_cashbox` (tesorería) guardaba el almacén sin validar pertenencia → ahora `warehouse_in_tenant_scope`.
- Suite `tests/test_security_integration.py` (8 tests): 401, RBAC 403, aislamiento de tenants, IDOR 404,
  escritura cruzada, inyección SQLi/XSS. Detalle en `security-validation.md`.
- Pendiente manual (ambiente controlado): CSRF/headers, uploads, secretos en logs, suite contra PG real.

## T-14 · Backup → Restore probado — PARCIAL (scripts validados)
- Sintaxis bash validada (`bash -n`) en los 8 scripts (`scripts/*.sh`).
- **Pendiente ejecutar** en PostgreSQL real: `backup.sh` → destruir entorno temporal → reconstruir →
  `restore.sh` → verificar DB, storage, licencia, installation id, auditoría.

## T-15 · Rendimiento — GUÍA LISTA (`performance-checklist.md`)
- Checklist backend (P50/P95/P99, N+1, índices, EXPLAIN, carga) y frontend (bundle, LCP/INP).
- **Pendiente ejecutar** con dataset representativo y stack levantado.

## T-16 · Auditoría fiscal normativa — GUÍA LISTA (`fiscal-audit-checklist.md`)
- Checklist IVA/ISLR/IGTF, numeración, notas, libros, inmutabilidad, homologación.
- **Pendiente ejecutar** con equipo fiscal + documentos oficiales + PostgreSQL real.

## Verificación timezone/drift en PostgreSQL real (T-06 complemento) — PARCIAL
- **Resuelto**: `tests/test_migrations_offline.py` (3 tests):
  - Cadena de esquema 0001→0012 compila offline en dialecto PostgreSQL (145 CREATE TABLE, 63 ALTER).
  - Migración de datos `0013_seed_business_permissions` es idempotente (2 ejecuciones no duplican)
    y no falla sin rol ADMIN.
- **Pendiente** en instancia PostgreSQL real: `alembic upgrade head` y `alembic check` (drift modelo↔BD),
  verificación de `DateTime(timezone=True)` (naive vs aware).

