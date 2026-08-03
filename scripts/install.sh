#!/usr/bin/env bash
# KONTROL - instalación inicial (DOC-07 §6.2).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

if [[ ! -f .env ]]; then
  echo "✗ Falta .env. Copie desde .env.example y complete los secretos."
  exit 1
fi

echo "1/4 Preflight"
python3 kontrol.py preflight

echo "2/4 Levantar pila"
docker compose -f compose.yaml up -d --build

echo "3/4 Esperar health"
sleep 10
docker compose -f compose.yaml ps

echo "4/4 Inicialización"
echo "  - Abra la UI y el asistente creará la empresa inicial y el administrador."
echo "  - Para activar licencia, importe el archivo firmado del propietario de KONTROL."
echo "✓ Instalación lista."
