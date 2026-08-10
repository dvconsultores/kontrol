# Spec 012 — Tareas de Auditoría (ejecutadas) y de Remediación (pendientes de autorización)

## Auditoría (ejecutada, sin cambios de código)
- T-A1 Inventario de menú/router/páginas/API (scripts `tools/audit_frontend.py`, `tools/audit_backend.py`).
- T-A2 Auditoría BD estática (`tools/audit_db.py`).
- T-A3 Reproducciones E2E locales (empresa→sucursal→almacén; crear sucursal/almacén = 200).
- T-A4 Consolidación de hallazgos y matrices.

## Remediación (IMPLEMENTADA — Olas 1, 2, 3 y puertas; autorizada)
- [x] T-01 Página+ruta **Usuarios** (`/seguridad/usuarios`) + consumo `GET/POST /users`.
- [x] T-02 Página+ruta **Roles/Permisos** (`/seguridad/roles`) + endpoints backend `GET /roles`, `POST/DELETE /users/{id}/roles`.
- [x] T-03 **Establecimientos** (menú+ruta+página sobre `/organization/establishments`).
- [x] T-04 **Ubicaciones** (`/organization/locations`).
- [x] Fix pre-existente: `POST /users` sin commit (persistencia).
- [x] T-05 **Dinero Float→Numeric**: 58 columnas → `Numeric(18,2)`/`Numeric(14,6)` + migración `0012_numeric_money` + coerción `float()` en la aritmética de servicios. pytest 193 ✓.
- [x] T-06 **Migraciones PostgreSQL**: cadena 0001→0012 compila offline (145 CREATE TABLE, 61 ALTER COLUMN); ORM usa `DateTime(timezone=True)`. Pendiente `alembic upgrade` en PostgreSQL real (drift).
- [x] T-07 **Clasificación de 117 endpoints huérfanos** → `orphan-endpoints-classification.md` (sistema/resueltos/backend-only/GAP).
- [x] T-08..T-09 Puertas permanentes: `src/tests/audit-completeness.test.ts` (G1-G4).
- [x] T-10 **E2E de procesos**: `tests/test_process_flows.py` (org chain, seguridad, enforcement READ_ONLY 423).
- [x] T-11 **Crawler de rutas**: `e2e/route-crawl.spec.ts` (recorre menú sin 404/errores/H1).
- [x] **GAP UI (T-07)**: páginas **Perfiles fiscales** (`/maestros/perfiles`) y **Sesiones** (`/seguridad/sesiones`).
- [x] **Permisos de negocio (hallazgo crítico)**: el seed solo otorgaba 7 recursos al rol ADMIN (faltaban maestros/compras/ventas/inventario/tesoreria/fiscal/regulatorio/reportes → 403 en operaciones). Corregido: catálogo completo en `_bootstrap_roles` (aditivo) + migración de datos `0013_seed_business_permissions` (instalaciones existentes).

## Remediación PENDIENTE (T-12..T-16 — requieren ambiente autorizado)
- [ ] T-12 Navegadores reales + responsive + accesibilidad (axe).
- [ ] T-13 Seguridad destructiva (OWASP) en ambiente controlado.
- [ ] T-14 Backup→restore probado en PostgreSQL real.
- [ ] T-15 Rendimiento con dataset representativo.
- [ ] T-16 Auditoría fiscal normativa + inmutabilidad en PostgreSQL real.
- [ ] T-06 complemento: `alembic upgrade`/`check` en PostgreSQL real (drift).
- [ ] Construir UI de los GAP de T-07 (acciones de ventas/compras, perfiles fiscales, sesiones) — nuevas tareas.
