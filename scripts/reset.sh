#!/usr/bin/env bash
# KONTROL - borra contenedores, redes, volúmenes e imágenes de KONTROL para
# empezar de cero.
#
# ⚠️ DESTRUYE DATOS: volúmenes de storage, license-state y backups se eliminan
#    (la identidad de instalación se regenerará al siguiente arranque).
#    La base de datos es EXTERNA y NO se toca.
#    Solo se eliminan recursos de KONTROL (no afecta NPM ni otros proyectos).
#
# Uso:
#   bash scripts/reset.sh        # pide confirmación
#   bash scripts/reset.sh -y     # sin confirmación (para automatizar)
# Re-ejecutar con bash aunque se invoque con sh (sh/dash no soporta bashisms).
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
COMPOSE="${KONTROL_COMPOSE:-compose.yaml}"

FORCE=0
if [[ "${1:-}" == "-y" || "${1:-}" == "--yes" ]]; then
  FORCE=1
fi

echo "=== KONTROL - Reset completo ==="
echo "Se eliminarán: contenedores, red, volúmenes (storage/license-state/backups)"
echo "e imágenes de KONTROL. La base de datos EXTERNA no se toca."

if [[ "$FORCE" -eq 0 ]]; then
  read -r -p "¿Continuar? (sí/N) " CONFIRM
  case "$CONFIRM" in
    s|S|si|sí|y|Y|yes|YES) ;;
    *) echo "Cancelado."; exit 0 ;;
  esac
fi

# 1) Detener y eliminar contenedores, red y huérfanos del proyecto
echo "1/4 Deteniendo y eliminando contenedores/redes..."
docker compose -f "$COMPOSE" down --remove-orphans 2>/dev/null || true

# 2) Eliminar volúmenes del proyecto y los nominales (por si cambió el compose)
echo "2/4 Eliminando volúmenes..."
docker compose -f "$COMPOSE" down -v 2>/dev/null || true
docker volume rm -f kontrol-storage kontrol-license-state kontrol-backups 2>/dev/null || true
docker volume ls -q --filter "name=kontrol" | xargs -r docker volume rm -f 2>/dev/null || true

# 3) Eliminar imágenes de KONTROL y watchtower
echo "3/4 Eliminando imágenes..."
REG="${KONTROL_IMAGE_REGISTRY:-dvconsultores}"
TAG="${KONTROL_IMAGE_TAG:-latest}"
for IMG in kontrol-backend kontrol-frontend kontrol-nginx; do
  docker rmi -f "$REG/$IMG:$TAG" 2>/dev/null || true
done
docker rmi -f containrrr/watchtower 2>/dev/null || true
docker image prune -f >/dev/null 2>&1 || true

# 4) Verificación
echo "4/4 Verificación..."
echo "  Contenedores restantes:  $(docker ps -a --filter "name=kontrol" -q | wc -l)"
echo "  Volúmenes restantes:     $(docker volume ls -q --filter "name=kontrol" | wc -l)"
echo "  Imágenes restantes:      $(docker images --format '{{.Repository}}' | grep -c 'dvconsultores/kontrol' || true)"

echo ""
echo "✓ Reset completado. Para empezar de cero:"
echo "  bash scripts/setup.sh"
echo ""
echo "Notas:"
echo "  - El archivo .env se conserva (contiene los secretos). Elimínelo a mano"
echo "    si desea regenerarlo desde .env.example."
echo "  - La base de datos externa NO se tocó. Si además desea recrearla, hágalo"
echo "    en su PostgreSQL (drop/create) y ajuste KONTROL_DB_URL si cambió."
