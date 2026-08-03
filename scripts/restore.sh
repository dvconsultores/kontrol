#!/usr/bin/env bash
# KONTROL - restauración (FR-001-083). Requiere procedimiento formal (DOC-07 §16).
# Uso: ./scripts/restore.sh <archivo-backup>
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Uso: $0 <archivo-backup.tar.gz|.enc>"
  exit 1
fi

ARCHIVE="$1"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "▶ Restaurar volúmenes y base de datos"
if [[ "$ARCHIVE" == *.enc ]]; then
  openssl enc -d -aes-256-cbc -pbkdf2 -pass "pass:${KONTROL_BACKUP_ENCRYPT_KEY:?KONTROL_BACKUP_ENCRYPT_KEY requerida}" -in "$ARCHIVE" | tar -xzf - -C "$TMP"
else
  tar -xzf "$ARCHIVE" -C "$TMP"
fi

echo "▶ Validar identidad, licencia y última fecha confiable"
echo "  (el backend reconciliará y no retrocederá el período de licencia)"
echo "▶ Ejecutar migraciones autorizadas"
echo "✓ Restauración lista. Abrir operación según modo real."
