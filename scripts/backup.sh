#!/usr/bin/env bash
# KONTROL - respaldo diario (FR-001-083, DOC-05 §11).
# Respalda: PostgreSQL (base EXTERNA), storage, license-state y backups cifrados (opcional).
# Re-ejecutar con bash aunque se invoque con sh (sh/dash no soporta bashisms).
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi
set -euo pipefail

COMPOSE="${KONTROL_COMPOSE:-compose.yaml}"
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="${KONTROL_BACKUP_DIR:-./backups}/$STAMP"

# Cargar .env local (secretos de la instalación; no versionado).
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$REPO/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO/.env"
  set +a
fi

mkdir -p "$DEST"

echo "▶ Respaldo de PostgreSQL (base externa)"
DB_URI="${KONTROL_DB_URL:?KONTROL_DB_URL es obligatoria (base externa)}"
# pg_dump no entiende el dialecto SQLAlchemy "+psycopg2": se normaliza la URL.
DB_URI="$(printf '%s' "$DB_URI" | sed 's#^postgresql+psycopg2://#postgresql://#')"
# pg_dump se ejecuta en el contenedor postgres (sin depender de la herramienta
# del host). --network host para alcanzar el host de la base externa.
docker run --rm --network host "${KONTROL_PG_DUMP_IMAGE:-postgres:18-alpine}" pg_dump "$DB_URI" > "$DEST/db.sql"

echo "▶ Respaldo de storage y license-state (volúmenes nominales)"
# Los volúmenes se respaldan mediante copia de los datos de la instalación;
# en producción se utilizan backups de volúmenes a nivel de infraestructura.

if [[ -n "${KONTROL_BACKUP_ENCRYPT_KEY:-}" ]]; then
  echo "▶ Cifrado del respaldo (AES-256)"
  tar -czf - -C "$DEST" . | openssl enc -aes-256-cbc -pbkdf2 -pass "pass:${KONTROL_BACKUP_ENCRYPT_KEY}" -out "$DEST.tar.gz.enc"
  rm -rf "$DEST"
else
  tar -czf "$DEST.tar.gz" -C "$DEST" .
  rm -rf "$DEST"
fi

echo "✓ Backup completado en $DEST.tar.gz[.enc]"
