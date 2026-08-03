# Checklist de validación Docker — 001-fundacion

| Campo | Valor |
|---|---|
| Fecha | 2026-08-04 |
| Estado | PENDIENTE — requiere entorno con Docker (no disponible en el sandbox de validación) |
| Ruta | `docs/evidence/docker-validation-checklist.md` |

## Comandos exactos (ejecutar en el servidor con Docker)

```bash
cd /home/maria/Proyectos/kontrol

# 1. Configuración válida
docker compose -f compose.yaml config --quiet && echo "config OK"

# 2. Build de imágenes (multi-stage, no root)
docker compose -f compose.yaml build

# 3. Preparar .env (sin secretos reales)
cp .env.example .env   # complete los valores

# 4. Levantar la pila
docker compose -f compose.yaml up -d

# 5. Health checks
docker compose -f compose.yaml ps
curl -fsS http://localhost:8080/healthz.json
curl -fsS http://localhost:8000/api/v1/health/live
curl -fsS http://localhost:8000/api/v1/health/ready

# 6. Migraciones (upgrade + downgrade) contra PostgreSQL real
docker compose -f compose.yaml exec backend alembic upgrade head
docker compose -f compose.yaml exec backend alembic downgrade base
docker compose -f compose.yaml exec backend alembic upgrade head

# 7. Persistencia de identidad (recrear contenedor sin perder installation_id)
docker compose -f compose.yaml stop backend && docker compose -f compose.yaml start backend

# 8. Diagnóstico
./scripts/diagnose.sh

# 9. Smoke E2E (frontend + backend vivos)
cd resources/frontend && npm run test:e2e

# 10. Limpieza
docker compose -f compose.yaml down
```

## Criterios de aceptación

| # | Criterio |
|---|---|
| 1 | `docker compose config` no reporta errores |
| 2 | Las 3 imágenes construyen (frontend, backend, nginx) |
| 3 | Todos los health checks responden OK |
| 4 | `alembic upgrade head` aplica la migración `0001` contra PostgreSQL 18 |
| 5 | `alembic downgrade base` revierte sin errores |
| 6 | Recrear el contenedor backend no cambia `installation_uuid` |
| 7 | El diagnóstico no expone secretos |
| 8 | El smoke E2E de Playwright pasa (login visible y accesible) |

## Registro de resultados

| Criterio | Resultado | Fecha | Responsable |
|---|---|---|---|
| (completar al ejecutar) | | | |
