#!/bin/sh
set -eu

# KONTROL - Entrypoint del backend.
# Aplica las migraciones de la base de datos EXTERNA (iniciales y futuras)
# contra KONTROL_DB_URL y luego ejecuta el comando del contenedor (uvicorn).
# Alembic es idempotente: solo aplica revisiones pendientes, por lo que es
# seguro en cada arranque y en cada actualización del cliente.

# KAUD-006 (P14): en producción no se permite la etiqueta "latest".
if [ "${KONTROL_ENVIRONMENT:-prod}" = "prod" ] && [ "${KONTROL_IMAGE_TAG:-latest}" = "latest" ]; then
    echo "[kontrol] ERROR: KONTROL_IMAGE_TAG=latest no está permitido en producción (P14)." >&2
    exit 1
fi

echo "[kontrol] Aplicando migraciones de base de datos (alembic upgrade head)..."
alembic upgrade head

echo "[kontrol] Iniciando API..."
exec "$@"
