# MATRIZ DE DEPENDENCIAS — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Responsable | Arquitecto / DevSecOps |
| Ruta | `specs/001-fundacion/dependency-matrix.md` |

## Stack propuesto (línea base DOC-08, sujeto a validación en `research.md`)

| Capa | Tecnología | Línea propuesta | Lockfile | Imagen | Estado |
|---|---|---|---|---|---|
| Frontend | React | 19.x | package-lock | — | Propuesta |
| Frontend | TypeScript | estricto (6.x estable compatible) | package-lock | — | Propuesta |
| Build | Vite | 8.x (validar disponibilidad, CL-12) | package-lock | — | Pendiente validación |
| Estilos | Tailwind CSS | 4.x | package-lock | — | Propuesta |
| Rutas | React Router | 8.x | package-lock | — | Propuesta |
| Estado | TanStack Query | 5.x | package-lock | — | Propuesta |
| Formularios | React Hook Form | 7.x | package-lock | — | Propuesta |
| Validación | Zod | 4.x | package-lock | — | Propuesta |
| Tablas | TanStack Table | 8.x | package-lock | — | Propuesta |
| Iconos | Lucide React | línea estable | package-lock | — | Propuesta |
| Fechas | date-fns + Intl | línea estable | package-lock | — | Propuesta |
| Backend | Python | 3.13.x (validar, CL-13) | requirements.lock/uv.lock | `python:3.13-slim` | Pendiente validación |
| API | FastAPI | línea estable | lock | — | Propuesta |
| DTO | Pydantic | 2.x | lock | — | Propuesta |
| ORM | SQLAlchemy | 2.x | lock | — | Propuesta |
| Migraciones | Alembic | 1.x | lock | — | Propuesta |
| Base de datos | PostgreSQL | 18.x (validar, CL-11) | — | `postgres:18` (digest) | Pendiente validación |
| PDF | ReportLab | 4.x | lock | — | Propuesta |
| Plantillas | Jinja2 | 3.x | lock | — | Propuesta |
| Proxy | Nginx | línea estable | — | `nginx:stable-alpine` (digest) | Propuesta |
| Unit frontend | Vitest | 4.x | package-lock | — | Propuesta |
| E2E | Playwright | línea estable | package-lock | — | Propuesta |
| Unit backend | Pytest | 8.x | lock | — | Propuesta |
| Lint/type | ESLint + oxlint + Prettier / Ruff + mypy | líneas compatibles | lock | — | Propuesta |
| Contratos | OpenAPI 3.1 + cliente generado | — | — | — | Propuesta |

## Componentes opcionales (NO en 001, requieren ADR)

| Componente | Decisión | ADR |
|---|---|---|
| Redis | Aplazado | ADR-009 |
| Celery | Aplazado | ADR-009 |
| MinIO/S3 | Aplazado | ADR-008 |
| OpenTelemetry | Aplazado | ADR-010 |
| Prometheus/Grafana | Aplazado | ADR-010 |
| Sentry | Aplazado | ADR-010 |
| pgaudit | Evaluar como complemento | ADR-012 |

## Reglas de versionado

- No `latest` en producción (Constitución P16, ADR-014).
- Versiones fijas en lockfiles e imágenes (digest cuando sea razonable).
- Fecha de actualización y CVE documentados.
- Actualizaciones mayores mediante Spec independiente.

## Estado

| Elemento | Estado |
|---|---|
| Matriz de dependencias | ✔ (línea base) |
| Versiones resueltas en la implementación (T-049 parcial, 2026-08-04) | React 19.2.8 · Vite 5.4.21 (Vite 8 de DOC-08 no existe; se usó la estable disponible) · Tailwind 4.3.3 · React Router 7.18.2 · TanStack Query 5.101.4 · TanStack Table 8.x · TypeScript 5.7 · Vitest 2.x · date-fns 4.x · Lucide 0.469.x |
| Versiones backend (resueltas, lockfile) | FastAPI 0.115.6 · Pydantic 2.10.4 · SQLAlchemy 2.0.36 · Alembic 1.14.0 · Argon2-cffi 23.1.0 · PyJWT 2.10.1 · pytest 8.3.4 |
| Versionado final con evidencia | Parcial — T-049 pendiente de revisión de CVE y lockfiles de CI |

