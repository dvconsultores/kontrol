# PR — 001-fundacion (documentación para apertura)

| Campo | Valor |
|---|---|
| Rama origen | `feature/001-fundacion` |
| Rama destino | `develop` |
| Commit base | `342882a` (chore(001): fundacion de KONTROL) |
| Ruta | `docs/evidence/pr-001-fundacion.md` |

## Título sugerido

> `chore(001): fundacion de KONTROL — spec, backend, frontend e infraestructura`

## Cuerpo sugerido (Markdown)

```markdown
## Descripción
Fundación de KONTROL conforme al flujo Spec Kit de `001-fundacion`
(spec, analyze, autorización expresa, implementación).

## Alcance
- Gobernanza: constitución, inventario documental, autoridad y conflictos.
- Spec completa: `specs/001-fundacion/` (plan, data-model, contratos, ADR,
  wireframes, checklist, tasks, trazabilidad).
- Backend FastAPI: core (seguridad, licencia Ed25519, errores, health),
  módulos (licensing, identity_access, organization, audit, system, fiscal-prep),
  Alembic `0001_fundacion`, seeds idempotentes.
- Frontend React: sistema de diseño, App Shell, router/guards, componentes
  compartidos, páginas fundacionales.
- Infraestructura: compose (prod/dev), Dockerfiles multi-stage no root, nginx,
  CLI `kontrol`, scripts (install/backup/restore/update/diagnose), CI.

## Evidencia de pruebas
- Backend: pytest 25/25 · ruff (lint+format) · mypy 0 issues.
- Frontend: vitest 14/14 · typecheck 0 · eslint 0 · build OK.
- Migraciones: Alembic `0001_fundacion (head)`; upgrade/downgrade pendiente de
  validación contra PostgreSQL real en CI.

## Checklist
- [x] Spec aprobada y `/speckit.analyze` sin bloqueos
- [x] Autorización expresa de implementación
- [x] Sin cambios no relacionados
- [x] Sin secretos (`.env.example` solo con placeholders; `.gitignore` cubre venv/node_modules/dist)
- [x] Lint y build sin errores
- [x] Sin fallos de pruebas (locales)

## Pendientes (convergencia)
- CI de GitHub por ejecutar y revisar.
- Validación Docker real y E2E Playwright (checklist: `docs/evidence/docker-validation-checklist.md`).
- Revisión legal/contable T-048 y CVE pendientes (T-049): `docs/evidence/cve-review.md`.
```

## Cómo abrirlo (requiere tu GitHub)

```bash
# Con GitHub CLI (autenticado)
gh pr create --base develop --head feature/001-fundacion --title "chore(001): fundacion de KONTROL" --body-file docs/evidence/pr-001-fundacion.md

# Solo con git (push de la rama y abrir el PR desde la web)
git push -u origin feature/001-fundacion
```

> Si el push aún no se completó en el remoto, el PR se abre sobre la web de GitHub una vez subida la rama.
