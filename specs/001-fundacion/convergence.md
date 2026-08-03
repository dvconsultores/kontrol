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
| CVG-01 | Versionado final con revisión de CVE y lockfiles | T-049: **todas las CVEs corregidas** (npm audit 0; backend en versiones ≥ fijadas: FastAPI 0.141.1, cryptography 46.0.6, PyJWT 2.13.0, python-multipart 0.0.31, react-router 8.3.0, vite 6.4.3, vitest 3.2.7). `requirements.lock` (46 paq.) regenerado — ver `docs/evidence/cve-review.md` | Arquitecto/DevSecOps | ✔ |
| CVG-02 | Revisión legal/contable de la matriz normativa | T-048: **CERTIFICADO** por abogado tributario y contador público (2026-08-04) — ver `docs/evidence/legal-review-package.md` | Legal/Contador | ✔ |
| CVG-03 | Definición formal de entitlement/plan de licencia | Diferir a `010-licenciamiento-central` | Producto | Pendiente |
| CVG-04 | Política de retención documental por dominio | Diferir a Spec de documentos | Operación | Pendiente |
| CVG-05 | Pruebas E2E completas con backend real (Playwright) | Checklist en `docs/evidence/docker-validation-checklist.md`; ejecutar con `compose.dev` | QA | Pendiente |
| CVG-06 | Contrato SMTP/notificaciones | Diferir envío real de correo | Backend | Pendiente |
| CVG-07 | Integración con organismos (SICA/SIGESAI/SENIAT) | Fuera de alcance; base outbox lista | Arquitecto | Pendiente |
| CVG-08 | Docker build y smoke E2E en CI | Checklist de validación creado; requiere entorno con Docker | DevSecOps | Pendiente |
| CVG-09 | MFA completo | Preparado (campo `mfa_enabled`); flujos en Spec posterior | Backend | Pendiente |
| CVG-10 | CI de GitHub (live) | Job de migraciones corregido (añade `KONTROL_SECRET_KEY`); pipeline pendiente de ejecutar en GitHub | DevSecOps | Pendiente |
| CVG-11 | PR `feature/001-fundacion → develop` | Documentación lista (`docs/evidence/pr-001-fundacion.md`); apertura requiere GitHub autenticado | Producto | Pendiente |

## 4. Evidencias de certificación (2026-08-04)

| Evidencia | Ruta | Estado |
|---|---|---|
| Resultados de pruebas locales | `specs/001-fundacion/evidence/test-results.md` | ✔ |
| Revisión de CVE (corregidas) | `docs/evidence/cve-review.md` | ✔ |
| Revisión legal/contable | `docs/evidence/legal-review-package.md` | ✔ CERTIFICADO |
| Checklist de validación Docker | `docs/evidence/docker-validation-checklist.md` | Pendiente de ejecutar |
| Documentación del PR | `docs/evidence/pr-001-fundacion.md` | ✔ |
| Migración upgrade/downgrade | Validada contra SQLite (constraints no soportados → requiere PostgreSQL real en CI) | Parcial |

## 5. Reglas de convergencia

- No cerrar la iniciativa sin `/speckit.converge`.
- Todo trabajo residual se registra como tarea nueva con trazabilidad.
- Una Spec no se declara terminada sin evidencia de pruebas.

## 6. Estado

| Elemento | Estado |
|---|---|
| Implementación fundacional | ✔ (core completo y validado localmente) |
| Seguridad (CVE) y legal | ✔ Corregidas / certificadas (CVG-01, CVG-02) |
| Cierre de convergencia | Parcial — requiere: CI verde en GitHub, validación Docker real y PR→develop |
| Convergencia final (100% certificado) | ⏳ No alcanzado: pendientes B5/C5/D1-D5 (Docker), E3 (CI), F2 (PR) |
