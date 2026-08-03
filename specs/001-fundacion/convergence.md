# CONVERGENCIA — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.1 |
| Ruta | `specs/001-fundacion/convergence.md` |

## 1. Propósito

Registrar brechas restantes y nuevas tareas tras la implementación. `/speckit.converge` se ejecuta al cierre de la iniciativa.

## 2. Estado de implementación (2026-08-04)

| Área | Estado | Evidencia |
|---|---|---|
| Backend core (config, db, seguridad, errores, health, request ID) | ✔ Implementado | `resources/backend/app/core/*` |
| Modelos + migración Alembic `0001_fundacion` + seeds | ✔ Implementado | `resources/backend/alembic/versions/0001_fundacion.py`, `scripts/seed.py` |
| Módulos: licensing, identity_access, organization, audit, system, fiscal (prep.) | ✔ Implementado | `resources/backend/app/modules/*` |
| Tests backend | ✔ 25/25 · ruff · mypy | `resources/backend/tests/*` |
| Frontend: design system, App Shell, router, guards, páginas | ✔ Implementado | `resources/frontend/src/*` |
| Tests frontend | ✔ 14/14 · typecheck · eslint · build | `resources/frontend/src/**/*.test.tsx` |
| Infraestructura: compose, Dockerfiles, nginx, CLI, scripts | ✔ Implementado | `compose.yaml`, `compose.dev.yaml`, `Dockerfile.*`, `kontrol.py`, `scripts/*` |
| CI/CD | ✔ Especificado (requiere push) | `.github/workflows/ci.yml` |

## 3. Brechas y tareas pendientes

| ID | Brecha | Acción | Responsable | Estado |
|---|---|---|---|---|
| CVG-01 | Versionado final con revisión de CVE y lockfiles en CI | T-049: revisar CVE, fijar versiones en CI | Arquitecto/DevSecOps | Pendiente |
| CVG-02 | Revisión legal/contable de la matriz normativa | T-048: revisión firmada antes de producción | Legal/Contador | Pendiente |
| CVG-03 | Definición formal de entitlement/plan de licencia | Diferir a `010-licenciamiento-central` | Producto | Pendiente |
| CVG-04 | Política de retención documental por dominio | Diferir a Spec de documentos | Operación | Pendiente |
| CVG-05 | Pruebas E2E completas con backend real (Playwright) | Ejecutar con `compose.dev` | QA | Pendiente |
| CVG-06 | Contrato SMTP/notificaciones | Diferir envío real de correo | Backend | Pendiente |
| CVG-07 | Integración con organismos (SICA/SIGESAI/SENIAT) | Fuera de alcance; base outbox lista | Arquitecto | Pendiente |
| CVG-08 | Docker build y smoke E2E en CI | Validar en pipeline con Docker disponible | DevSecOps | Pendiente |
| CVG-09 | MFA completo | Preparado (campo `mfa_enabled`); flujos en Spec posterior | Backend | Pendiente |

## 4. Reglas de convergencia

- No cerrar la iniciativa sin `/speckit.converge`.
- Todo trabajo residual se registra como tarea nueva con trazabilidad.
- Una Spec no se declara terminada sin evidencia de pruebas.

## 5. Estado

| Elemento | Estado |
|---|---|
| Implementación fundacional | ✔ (core completo y validado) |
| Brechas registradas | ✔ |
| Tareas de convergencia | ✔ |
| Convergencia final | Pendiente — autorización y commit |
