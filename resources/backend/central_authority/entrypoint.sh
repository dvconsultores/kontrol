#!/bin/sh
# Autoridad Central de Licencias: migra SU base y arranca la API de health. Sin clave de firma en prod no arranca.
set -eu
echo "[central] Aplicando migraciones de la autoridad (alembic -c central_authority/alembic.ini upgrade head)..."
alembic -c central_authority/alembic.ini upgrade head
echo "[central] Iniciando API..."
exec "$@"
