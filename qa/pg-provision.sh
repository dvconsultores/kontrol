#!/usr/bin/env bash
# Aprovisiona una instancia PostgreSQL real de QA (Spec 045 · CVG-045-01/02).
#
# Usa los binarios de PostgreSQL empaquetados en `pgserver` (dependencia SOLO de
# QA, no de producción: no está en requirements.txt). Cuando KONTROL_PGBIN está
# definido, los binarios se toman de esa ruta (la certificación canónica lo fija
# a la instalación de qa/postgres_qa.json); solo en el desarrollo no canónico se
# usa pgserver dentro de resources/backend/.venv. En un entorno con Docker, el
# equivalente es `compose.dev` con el servicio de PostgreSQL.
#
# Uso:  bash qa/pg-provision.sh [start|stop|status|reset]
set -euo pipefail

BACKEND="$(cd "$(dirname "${BASH_SOURCE[0]}")/../resources/backend" && pwd)"
PGBIN="${KONTROL_PGBIN:-$BACKEND/.venv/lib/python3.11/site-packages/pgserver/pginstall/bin}"
PGDATA="${KONTROL_PGDATA:-/tmp/kontrol-pgdata-045}"
PGPORT="${KONTROL_PGPORT:-55432}"
LOG="${KONTROL_PGLOG:-/tmp/kontrol-pg.log}"

[ -x "$PGBIN/pg_ctl" ] || { echo "PostgreSQL de QA no disponible en $PGBIN (pgserver no instalado o KONTROL_PGBIN inválido)"; exit 1; }

# `btree_gist` no viene en el paquete `pgserver`: su instalación trae `plpgsql` y
# `vector` y nada más. El esquema lo necesita —hay un `CREATE EXTENSION IF NOT
# EXISTS btree_gist` en las migraciones— así que sin él **toda** la suite falla
# en el fixture, no en una prueba concreta. Se compila una vez con PGXS contra
# esa misma instalación; requiere gcc y make.
ext_btree_gist() {
  local dir="$($PGBIN/pg_config --sharedir)/extension"
  [ -f "$dir/btree_gist.control" ] && return 0
  if [ "${KONTROL_PG_SIN_COMPILAR:-0}" = "1" ]; then echo "btree_gist no está instalado en $PGBIN y KONTROL_PG_SIN_COMPILAR=1 prohíbe compilarlo" >&2; return 1; fi
  local ver="$($PGBIN/pg_config --version | awk '{print $2}')"
  local tmp="${KONTROL_PGSRC:-/tmp/kontrol-pgsrc}"
  echo "compilando btree_gist para PostgreSQL $ver…"
  mkdir -p "$tmp"
  [ -d "$tmp/postgresql-$ver" ] || {
    curl -sSL "https://ftp.postgresql.org/pub/source/v$ver/postgresql-$ver.tar.bz2" \
      | tar xjf - -C "$tmp" "postgresql-$ver/contrib/btree_gist"
  }
  make -C "$tmp/postgresql-$ver/contrib/btree_gist" USE_PGXS=1 PG_CONFIG="$PGBIN/pg_config" install >/dev/null
}

init() {
  [ -f "$PGDATA/PG_VERSION" ] && return 0
  mkdir -p "$PGDATA"
  # Timezone UTC y encoding UTF8: parámetros fijados por ADR-D0-001.
  "$PGBIN/initdb" -D "$PGDATA" -U postgres -E UTF8 --locale=C >/dev/null
}

start() {
  ext_btree_gist
  init
  # Un DROP SCHEMA del esquema completo toma unos 6300 bloqueos y hay pruebas que sueltan dos a la vez.
  "$PGBIN/pg_ctl" -D "$PGDATA" -o "-p $PGPORT -c listen_addresses=localhost -c timezone=UTC -c max_locks_per_transaction=256" -l "$LOG" start
  sleep 2
  "$PGBIN/psql" -h localhost -p "$PGPORT" -U postgres -d postgres -q \
    -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='kontrol_migrator') THEN CREATE ROLE kontrol_migrator LOGIN PASSWORD 'qa'; END IF; END \$\$;" \
    -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='kontrol_app') THEN CREATE ROLE kontrol_app LOGIN PASSWORD 'qa'; END IF; END \$\$;"
  "$PGBIN/psql" -h localhost -p "$PGPORT" -U postgres -d postgres -tAc "SELECT version();"
}

mkdb() {
  "$PGBIN/psql" -h localhost -p "$PGPORT" -U postgres -d postgres -q \
    -c "DROP DATABASE IF EXISTS $1;" \
    -c "CREATE DATABASE $1 OWNER kontrol_migrator ENCODING 'UTF8';" \
    -c "ALTER DATABASE $1 SET timezone TO 'UTC';"
}

case "${1:-start}" in
  start)  start ;;
  stop)   "$PGBIN/pg_ctl" -D "$PGDATA" stop ;;
  status) "$PGBIN/pg_ctl" -D "$PGDATA" status ;;
  reset)  "$PGBIN/pg_ctl" -D "$PGDATA" stop || true; rm -rf "$PGDATA"; start ;;
  mkdb)   mkdb "$2" ;;
  *) echo "uso: $0 [start|stop|status|reset|mkdb <nombre>]"; exit 1 ;;
esac
