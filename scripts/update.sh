#!/usr/bin/env bash
# KONTROL - actualización controlada (DOC-08 §19): preflight, backup, pull, health, rollback.
# Las migraciones (iniciales y futuras) se aplican automáticamente al arrancar
# el backend (entrypoint: alembic upgrade head), por lo que no se ejecutan aquí.
# Re-ejecutar con bash aunque se invoque con sh (sh/dash no soporta bashisms).
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi
set -euo pipefail

COMPOSE="${KONTROL_COMPOSE:-compose.yaml}"

echo "1/5 Preflight"
./scripts/diagnose.sh >/dev/null || true

echo "2/5 Backup previo"
"$(dirname "$0")/backup.sh"

echo "3/5 Pull de imágenes"
docker compose -f "$COMPOSE" pull

echo "4/5 Recrear servicios (migraciones automáticas al arrancar)"
docker compose -f "$COMPOSE" up -d
sleep 5
docker compose -f "$COMPOSE" ps

echo "5/5 Actualización completada. Si algo falla, ejecute el rollback con el backup previo."
