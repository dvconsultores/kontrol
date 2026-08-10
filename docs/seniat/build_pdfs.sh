#!/usr/bin/env bash
# KONTROL — Genera los PDF del expediente SENIAT a partir de los HTML.
# Requiere google-chrome (o chromium) en el PATH.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

CHROME="${CHROME:-google-chrome}"
if ! command -v "$CHROME" >/dev/null 2>&1; then
  for c in google-chrome-stable chromium chromium-browser; do
    if command -v "$c" >/dev/null 2>&1; then CHROME="$c"; break; fi
  done
fi

FILES=(
  "00-portada.html:00-portada.pdf"
  "01-solicitud-de-homologacion.html:01-solicitud-de-homologacion.pdf"
  "02-identificacion-del-contribuyente.html:02-identificacion-del-contribuyente.pdf"
  "03-ficha-tecnica-del-sistema.html:03-ficha-tecnica-del-sistema.pdf"
  "04-monitoreo-y-auditoria.html:04-monitoreo-y-auditoria.pdf"
  "05-conexion-con-plataformas.html:05-conexion-con-plataformas.pdf"
  "06-manual-tecnico-para-usuarios.html:06-manual-tecnico-para-usuarios.pdf"
  "07-manual-tecnico-fabricante-hardware.html:07-manual-tecnico-fabricante-hardware.pdf"
)

for entry in "${FILES[@]}"; do
  src="${entry%%:*}"; out="${entry##*:}"
  echo "▶ ${src} → ${out}"
  "$CHROME" --headless --disable-gpu --no-sandbox \
    --no-pdf-header-footer \
    --user-data-dir="${TMPDIR:-/tmp}/kontrol-chrome-$$" \
    --print-to-pdf="$DIR/$out" \
    "file://$DIR/$src" 2>/dev/null || { echo "✗ falló ${src}"; exit 1; }
done

echo "✓ PDF generados en $DIR"
