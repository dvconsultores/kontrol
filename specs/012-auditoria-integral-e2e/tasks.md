# Spec 012 — Tareas de Auditoría (ejecutadas) y de Remediación (pendientes de autorización)

## Auditoría (ejecutada, sin cambios de código)
- T-A1 Inventario de menú/router/páginas/API (scripts `tools/audit_frontend.py`, `tools/audit_backend.py`).
- T-A2 Auditoría BD estática (`tools/audit_db.py`).
- T-A3 Reproducciones E2E locales (empresa→sucursal→almacén; crear sucursal/almacén = 200).
- T-A4 Consolidación de hallazgos y matrices.

## Remediación (IMPLEMENTADA — Ola 1 + puertas, autorizada)
- [x] T-01 Página+ruta **Usuarios** (`/seguridad/usuarios`) + consumo `GET/POST /users`.
- [x] T-02 Página+ruta **Roles/Permisos** (`/seguridad/roles`) + endpoints backend `GET /roles`, `POST/DELETE /users/{id}/roles`.
- [x] T-03 **Establecimientos** (menú+ruta+página sobre `/organization/establishments`).
- [x] T-04 **Ubicaciones** (`/organization/locations`).
- [x] Fix pre-existente: `POST /users` sin commit (persistencia).
- [x] T-08..T-09 Puertas permanentes: `src/tests/audit-completeness.test.ts` (G1-G4).

## Remediación PENDIENTE (olas siguientes)
- [ ] T-05 Migrar 58 columnas dinero `Float`→`Numeric`.
- [ ] T-06 Verificar timezone/drift en PostgreSQL real.
- [ ] T-07 Clasificar 117 endpoints huérfanos (futuro vs brecha) y construir UI de los obligatorios.
- [ ] T-10 E2E de procesos críticos (Playwright).
- [ ] T-11 Crawler de rutas (no destructivo).
- [ ] T-12..T-16 Validaciones pendientes (browsers, accesibilidad, seguridad, backup/restore, rendimiento, fiscal).
