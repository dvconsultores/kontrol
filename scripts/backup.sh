#!/usr/bin/env bash
# KONTROL - crea una copia de seguridad verificable.
# Uso: ./scripts/backup.sh [opciones para `python -m app.ops.backup create`]
# Re-ejecutar con bash aunque se invoque con sh (sh/dash no soporta bashisms).
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi
set -euo pipefail

# Cargar .env local (secretos de la instalación; no versionado).
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$REPO/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO/.env"
  set +a
fi

cd "$REPO/resources/backend"
exec "${KONTROL_PYTHON:-python3}" -m app.ops.backup create --dest "${KONTROL_BACKUP_DIR:-$REPO/backups}" "$@"
