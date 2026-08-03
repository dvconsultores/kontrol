#!/usr/bin/env bash
# KONTROL - actualización controlada (DOC-08 §19): preflight, backup, pull, migrate, health, rollback.
set -euo pipefail

COMPOSE="${KONTROL_COMPOSE:-compose.yaml}"

echo "1/6 Preflight"
./scripts/diagnose.sh >/dev/null || true

echo "2/6 Backup previo"
"$(dirname "$0")/backup.sh"

echo "3/6 Pull y rebuild de imágenes"
docker compose -f "$COMPOSE" pull
docker compose -f "$COMPOSE" build --pull

echo "4/6 Migraciones (respaldadas y reversibles)"
docker compose -f "$COMPOSE" exec -T backend alembic upgrade head

echo "5/6 Health checks"
docker compose -f "$COMPOSE" up -d
sleep 5
docker compose -f "$COMPOSE" ps

echo "6/6 Actualización completada. Si algo falla, ejecute el rollback con el backup previo."
