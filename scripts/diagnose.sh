#!/usr/bin/env bash
# KONTROL - diagnóstico de instalación (FR-001-084). Salida sanitizada, sin secretos.
set -euo pipefail

COMPOSE="${KONTROL_COMPOSE:-compose.yaml}"

echo "=== KONTROL - Diagnóstico ==="
docker compose -f "$COMPOSE" version --short 2>/dev/null || echo "docker compose no disponible"

echo ""
echo "--- Servicios ---"
docker compose -f "$COMPOSE" ps --format "table {{.Name}}\t{{.Status}}"

echo ""
echo "--- Health backend ---"
docker compose -f "$COMPOSE" exec -T backend python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready').read().decode())" 2>/dev/null \
  || echo "backend no accesible"

echo ""
echo "--- Diagnóstico del sistema (endpoint sanitizado) ---"
# Requiere token; en operación se ejecuta mediante la API con sesión autorizada.

echo "✓ Diagnóstico completado (sin secretos)"
