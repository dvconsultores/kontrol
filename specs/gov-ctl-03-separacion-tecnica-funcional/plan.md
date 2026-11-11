# Plan CTL-03

Base `d1d0a0a`; cabeza de Alembic `0096_gov_proc10_garantias`; **sin migración**. Módulo `government` (FastAPI, SQLAlchemy,
PostgreSQL) y frontend React + TanStack Query.

## Backend (proyección)
- `app/modules/government/service_separacion.py`: `separacion(db, ctx) -> dict` con `integridad`, `exigencia_identidad`,
  `administradores`, `denegaciones`. Reutiliza `authority.TECHNICAL_CAPABILITIES`, `SECURITY_ADMIN_CAPABILITIES`,
  `capabilities_in_company`, `role_capabilities`; `service_identidad.contexto_institucional` y `_politica_de`; `AuditEvent`;
  `GovernmentRoleCategory`.
- `schemas_separacion.py` (salida) y `api_separacion.py`: `GET /gobierno/control/separacion`, `gobierno_auditoria:view`,
  `get_company_context`, `require_module("gobierno")`. Registro en `main.py`.
- Consultas acotadas: cuentas del tenant con acceso al ente; roles por cuenta en una consulta; eventos ROLE_ASSIGNED por
  `entity_id` en una consulta; denegaciones con límite 50.

## Pruebas (PostgreSQL)
`tests/test_gov_ctl03_separacion.py`: invariantes de rutas y de la cabeza (PDD-CTL03-13), ADMIN puro (FR-001..003), guarda
institucional (FR-006), proyección y aislamiento (FR-007, FR-009), permisos. Regresión: `test_delegation_ceiling*`,
`test_gov_org06*`, `test_gov_org04*`, `test_gov_org03*`, `test_gov_org07*`, `test_gov_ctl01*`, `test_gov_ctl02*`, DOC-02.

## Frontend
`modules/gobierno/control/SeparacionPage.tsx`, función en `modules/gobierno/api.ts`, ruta en `app/router.tsx`, entrada en
`layout/Sidebar.tsx`, pantalla en `app/autoridad/pantallas.ts` si el patrón lo exige; Vitest de la página.

## E2E
`e2e/gobierno-separacion.spec.ts`: actores ADMIN puro, dual sin cargo, legítimo y Control Interno; Axe; 390/320.

## CONSTITUTION GATE
PASS (`DECISIONES.md`).
