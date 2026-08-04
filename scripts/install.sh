#!/usr/bin/env bash
# KONTROL - instalación inicial (DOC-07 §6.2).
# Re-ejecutar con bash aunque se invoque con sh (sh/dash no soporta bashisms).
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

if [[ ! -f .env ]]; then
  echo "✗ Falta .env. Copie desde .env.example y complete los secretos."
  exit 1
fi

echo "1/4 Preflight"
python3 kontrol.py preflight

echo "2/4 Descargar imágenes y levantar pila (migraciones automáticas al arrancar)"
docker compose -f compose.yaml pull
docker compose -f compose.yaml up -d

echo "3/4 Esperar health"
sleep 10
docker compose -f compose.yaml ps

echo "4/4 Inicialización"
echo "  - Abra la UI y el asistente creará la empresa inicial y el administrador."
echo "  - Para activar licencia, importe el archivo firmado del propietario de KONTROL."
echo "✓ Instalación lista."
