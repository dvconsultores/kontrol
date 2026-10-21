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
| Versiones finales resueltas (2026-08-04, T-049 con CVE corregidas) | **Frontend:** React 19.2.8 · Vite **6.4.3** · Tailwind 4.3.3 · **react-router 8.3.0** (reemplaza react-router-dom 7.18.2 por CVE) · TanStack Query 5.101.4 · TanStack Table 8.x · TypeScript 5.7 · **Vitest 3.2.7** · date-fns 4.x · Lucide 0.469.x |
| Versiones backend finales (resueltas, lockfile) | **FastAPI 0.141.1** · starlette **1.3.1** · Pydantic 2.10.4 · SQLAlchemy 2.0.36 · Alembic 1.14.0 · **cryptography 46.0.6** · **PyJWT 2.13.0** · **python-multipart 0.0.31** · Argon2-cffi 23.1.0 · **pytest 9.0.3** |
| Lockfiles | `requirements.lock` (46 paq.) + `package-lock.json` regenerados |
| CVE | **0 en npm audit**; backend en versiones ≥ fijadas por pip-audit — ver `docs/evidence/cve-review.md` |


## Actualización 2026-10-20 — conjunto de despliegue reproducible (Spec 052, OD-CERT-05)

La fila «Versiones backend finales» de arriba registra la resolución del 2026-08-04.
- Desde el 2026-10-20 la autoridad de versiones del backend es `resources/backend/requirements.lock`.
  - Lo genera el comando canónico declarado en su cabecera:
    `uv pip compile requirements.txt --python-version 3.13 --python-platform x86_64-unknown-linux-gnu --exclude-newer 2026-10-20T00:00:00Z --upgrade -o requirements.lock`.
  - Tiene 49 paquetes, directos y transitivos.
  - La imagen lo instala con `--no-deps` y `pip check`.
- Diferencia material con la fila histórica: **starlette 1.9.0**. Cumple el suelo de `cve-review.md` (≥ 1.3.1) y la
  compatibilidad de FastAPI 0.141.1 (`>=0.46.0`), y es la versión certificada.
- El lock histórico (46 paquetes, `pip freeze` sobre Python 3.11) queda sustituido.
- La auditoría del 2026-10-20 encuentra avisos nuevos en los pines directos `PyJWT 2.13.0` y `cryptography 46.0.6`
  (deuda BACKEND-DIRECT-DEPENDENCIES-KNOWN-VULNERABILITIES).
- Evidencia: `evidence/production-dependencies-reproducible/` y
  `spec052-production-dependencies-reproducible-delta.md`.

## Actualización 2026-10-20 — pisos de seguridad de PyJWT y cryptography (Spec 001, OD-SEC-02)

PyJWT pasa de 2.13.0 a **2.15.0** y cryptography de 46.0.6 a **50.0.2**. Son pines directos de `requirements.txt`, y el
lock se regenera con el mismo corte; ningún otro paquete cambia.
- **Motivo:** 19 avisos públicos corregibles (14 de PyJWT, 5 de cryptography), de los que 3 aplican a KONTROL. Además,
  el OpenSSL 4.0.3 embebido en 50.0.2 corrige tres CVE de OpenSSL.
- cryptography 46 → 50 es un salto mayor: este es su ciclo de seguridad explícito (ADR-014), con compatibilidad
  verificada sobre los usos reales (Ed25519 y PEM).
- **Pisos de seguridad vigentes** (protegidos por `test_seguridad_dependencias.py`):
  - PyJWT ≥ 2.15.0;
  - cryptography ≥ 50.0.2.
- Registro: `docs/evidence/cve-review.md` §«Backend — revisión 2026-10-20».
- Evidencia: `evidence/backend-direct-dependency-security/` y `spec001-backend-direct-dependency-security-delta.md`.

## Actualización 2026-10-21 — base de despliegue fijada (Spec 052, OD-CERT-07/08)

**Base del backend:**
- `python:3.13.16-slim-trixie@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f`: patch tag,
  distro trixie y digest del **índice** OCI (manifiesto `linux/amd64` `8fb4cfa1…`).
- CPython 3.13.16, glibc 2.41, OpenSSL 3.5.7-1~deb13u3.
- `ca-certificates` fijado a `20250419+deb13u1` por DSA-6572-1.

**Fuente versionada:** `specs/001-fundacion/certified-deployment-base.json`, que leen las pruebas IBB.

**Línea base de compatibilidad del intérprete de despliegue:** **V5** (IMAGE_ROOTFS, CPython 3.13.16 de la imagen con
su glibc y su OpenSSL, y bundle de CA corregido). **V4** (CPython 3.13.15) queda como histórica.

Esto no es canonicalización: RELEASE_DEPLOYMENT_PARITY_CERTIFIED sigue en 0.
