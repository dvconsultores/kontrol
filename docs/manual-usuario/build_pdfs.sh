#!/usr/bin/env bash
# KONTROL — Genera el PDF del Manual de Usuario a partir del HTML.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

CHROME="${CHROME:-google-chrome}"
if ! command -v "$CHROME" >/dev/null 2>&1; then
  for c in google-chrome-stable chromium chromium-browser; do
    if command -v "$c" >/dev/null 2>&1; then CHROME="$c"; break; fi
  done
fi

"$CHROME" --headless --disable-gpu --no-sandbox \
  --no-pdf-header-footer \
  --user-data-dir="${TMPDIR:-/tmp}/kontrol-chrome-manual-$$" \
  --print-to-pdf="$DIR/manual-de-usuario.pdf" \
  "file://$DIR/manual-de-usuario.html" 2>/dev/null || { echo "✗ falló la conversión"; exit 1; }

echo "✓ PDF generado: $DIR/manual-de-usuario.pdf"
