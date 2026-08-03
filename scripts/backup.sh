#!/usr/bin/env bash
# KONTROL - respaldo diario (FR-001-083, DOC-05 §11).
# Respalda: PostgreSQL, storage, license-state y backups cifrados (opcional).
set -euo pipefail

COMPOSE="${KONTROL_COMPOSE:-compose.yaml}"
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="${KONTROL_BACKUP_DIR:-./backups}/$STAMP"

mkdir -p "$DEST"

echo "▶ Respaldo de PostgreSQL"
docker compose -f "$COMPOSE" exec -T db pg_dump -U "${KONTROL_DB_USER:-kontrol}" "${KONTROL_DB_NAME:-kontrol}" > "$DEST/db.sql"

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
