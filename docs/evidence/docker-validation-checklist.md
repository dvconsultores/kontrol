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

## Analizador antimalware como servicio (Spec 046 · OBS-09, opción B) — ejecutar en el servidor con Docker

```bash
# 1. Construir la imagen del analizador (clamav/clamav:1.4.3 + deploy/clamd/clamd.conf) y la del backend
docker build -f Dockerfile.clamd -t "${KONTROL_IMAGE_REGISTRY:-dvconsultores}/kontrol-clamd:${KONTROL_IMAGE_TAG:-latest}" .
docker build -f Dockerfile.backend -t "${KONTROL_IMAGE_REGISTRY:-dvconsultores}/kontrol-backend:${KONTROL_IMAGE_TAG:-latest}" .
docker image inspect "${KONTROL_IMAGE_REGISTRY:-dvconsultores}/kontrol-backend:${KONTROL_IMAGE_TAG:-latest}" --format '{{.Size}}'

# 2. El backend NO lleva analizador ni firmas; clamd sí
docker run --rm --entrypoint sh "${KONTROL_IMAGE_REGISTRY:-dvconsultores}/kontrol-backend:${KONTROL_IMAGE_TAG:-latest}" -c 'command -v clamscan || echo "sin clamscan"; ls /var/lib/clamav 2>/dev/null || echo "sin firmas"'
docker compose up -d clamd && docker compose ps clamd            # esperar healthy (start_period 300 s: carga de firmas)
docker compose exec clamd sh -c 'printf "zVERSION\0" | nc -w 5 127.0.0.1 3310'   # ClamAV 1.4.3/<daily>/<fecha>

# 3. Puerto interno y sin almacén documental
docker inspect kontrol-clamd --format '{{json .NetworkSettings.Ports}} {{json .Mounts}}'   # sin puertos publicados; solo /var/lib/clamav

# 4. Contrato funcional desde el backend (tras `docker compose up -d`)
#    subida limpia → 201 · EICAR → 422 FILE_INFECTED · `docker compose stop clamd` → 422 SCAN_FAILED (falso seguro) · `start clamd` → vuelve 201
```

Registrar: `CLAMD_VERSION`, `SIGNATURE_DATABASE_VERSION/DATE`, `BASE_BACKEND_IMAGE_SIZE`, `BUILD_TIME`, `CLAMD_HEALTHY_AFTER_S`,
y los cuatro resultados del punto 4, en `specs/046-gestion-documental/evidence/obs09-production-image-scanner/compose-runtime-evidence.md`.

Automatizado: `resources/backend/.venv/bin/python qa/compose_qa.py` (o `python3 qa/compose_qa.py`) desde la raíz, en un equipo con Docker, ejecuta esta lista completa, limpia sus recursos y emite el bloque `OBS09_EXTERNAL_DOCKER_EVIDENCE` que audita Claude.

