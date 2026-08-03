# Definition of Done — 001-FUNDACION

| Campo | Valor |
|---|---|
| Fecha | 2026-08-04 |
| Rama | `feature/001-fundacion` |
| Commits | `342882a`, `19225f0` |
| Ruta | `docs/governance/dod-001-fundacion.md` |

La iniciativa **001-fundacion** se declara **100% certificada** solo cuando TODOS los criterios siguientes están en ✔. Ninguno se omite sin ADR de excepción.

## A. Especificación y gobernanza

| # | Criterio | Estado |
|---|---|---|
| A1 | Constitución creada y aplicada | ✔ |
| A2 | Spec 001 completa y `/speckit.analyze` sin bloqueos | ✔ |
| A3 | Inventario documental, autoridad y conflictos | ✔ |
| A4 | ADR-001..015 propuestos | ✔ |
| A5 | Matriz de trazabilidad completa | ✔ |

## B. Backend (validado localmente)

| # | Criterio | Estado |
|---|---|---|
| B1 | pytest 25/25 | ✔ |
| B2 | ruff (lint + format) | ✔ |
| B3 | mypy 0 issues | ✔ |
| B4 | App importa y rutas registradas | ✔ |
| B5 | Migración Alembic `0001` (upgrade/downgrade contra **PostgreSQL real**) | ⏳ CI/Docker |

## C. Frontend (validado localmente)

| # | Criterio | Estado |
|---|---|---|
| C1 | vitest 14/14 | ✔ |
| C2 | typecheck 0 errores | ✔ |
| C3 | eslint 0 problemas | ✔ |
| C4 | Build de producción OK | ✔ |
| C5 | E2E Playwright (smoke) ejecutado | ⏳ requiere backend+frontend vivos |

## D. Infraestructura

| # | Criterio | Estado |
|---|---|---|
| D1 | compose config válido | ⏳ requiere Docker |
| D2 | Build de las 3 imágenes | ⏳ requiere Docker |
| D3 | Health checks OK en runtime | ⏳ requiere Docker |
| D4 | Persistencia de identidad (recrear contenedor) | ⏳ requiere Docker |
| D5 | Backup/restore/diagnóstico verificados | ⏳ requiere Docker |

## E. Seguridad y operación

| # | Criterio | Estado |
|---|---|---|
| E1 | Sin secretos en el repositorio | ✔ (escaneo + gitignore) |
| E2 | Revisión de CVE (T-049) | Parcial — `python-multipart` corregido; `starlette`/`react-router` pendientes de decisión (`cve-review.md`) |
| E3 | CI de GitHub en verde | ⏳ pendiente de ejecutar/revisar |
| E4 | Revisión legal/contable (T-048) | ⏳ pendiente (`legal-review-package.md`) |
| E5 | SBOM / escaneo Docker / gitleaks | ⏳ CI |

## F. Entrega

| # | Criterio | Estado |
|---|---|---|
| F1 | Rama en remoto (`origin/feature/001-fundacion`) | ✔ (`19225f0`) |
| F2 | PR → `develop` abierto y revisado | ⏳ pendiente (documentado) |
| F3 | `/speckit.converge` cerrado con evidencias | Parcial (CVG-01..11) |

## Resultado

- **Certificado al 2026-08-04:** fases A (gobernanza), B1–B4, C1–C4, E1, F1.
- **Pendientes para 100%:** B5, C5, D1–D5 (requieren Docker), E2 decisión de CVE, E3 CI verde, E4 revisión legal, F2 PR → develop, F3 convergencia completa.

> La fundación está **lista para desarrollo local**; su **certificación formal** se completa al cubrir B5/C5/D1-D5 (entorno Docker), E2/E3 (CI y CVE) y E4 (legal) antes de producción.
