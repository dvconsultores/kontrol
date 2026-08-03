# ESTRUCTURA DEL REPOSITORIO — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Responsable | Arquitecto de software |
| Ruta | `specs/001-fundacion/repository-structure.md` |

## Estructura objetivo (consolidada)

```text
kontrol/
├── kontrol.py                  # CLI: install, preflight, backup, restore, update, diagnose
├── compose.yaml                # Producción
├── compose.dev.yaml            # Desarrollo
├── .env.example
├── .gitignore
├── .dockerignore
├── resources/
│   ├── frontend/
│   │   ├── src/app/            # providers, router, shell
│   │   ├── src/modules/        # módulos por dominio
│   │   ├── src/components/     # componentes compartidos
│   │   ├── src/design-system/  # tokens y primitivas
│   │   ├── src/api/            # cliente OpenAPI generado
│   │   ├── src/lib/            # utilidades controladas
│   │   └── src/tests/
│   └── backend/
│       ├── app/
│       │   ├── core/           # config, seguridad, db, licencia
│       │   ├── modules/        # dominios
│       │   ├── shared/         # errores, auditoría, reportes
│       │   └── main.py
│       ├── alembic/
│       └── tests/
├── specs/                      # Specs por iniciativa (Spec Kit)
├── requerimientos/             # Documentos fuente (no renombrar)
├── docs/
│   ├── governance/
│   ├── evidence/
│   └── ...
├── scripts/                    # install, backup, restore, diagnose, update
├── storage/                    # documentos persistentes
├── backups/
└── databases/                  # volumen PostgreSQL local (dev)
```

## Reglas

- Backend: `modules/<dominio>` con modelos, servicios, repositorios, endpoints, eventos y pruebas.
- Frontend: cada módulo tiene `routes`, `pages`, `components`, `queries`, `mutations`, `schemas`, `types`, `permissions`, `tests`.
- Los componentes compartidos no importan módulos de negocio; los módulos sí pueden importar design system y shared.
- Sin `utils.ts` genérico sin responsabilidad clara.
- Rutas diferidas por módulo con error boundary.
- Textos visibles centralizados.

## Estado

| Elemento | Estado |
|---|---|
| Estructura del repositorio | ✔ |
| Aprobación | Pendiente |
