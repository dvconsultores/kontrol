#!/usr/bin/env bash
# Deja la base del E2E con el mundo completo que las suites esperan.
#
# Único punto de entrada de la siembra, y el orden importa: la 047 y N6
# necesitan el tenant y la primera empresa que crea la siembra de la 045, así
# que no son conmutables. Antes ese orden vivía repartido entre tres docstrings
# y la memoria de quien levantaba la pila; ahora está escrito una vez.
#
# Las cuatro siembras son idempotentes y no borran nada: esto puede ejecutarse
# antes de cada suite, que es justo lo que hace `e2e/global-setup.ts`.
# La última (`qa/mfa-e2e-identidades.py`) clona los usuarios de N6 para los
# workers de la corrida MFA.
#
# Uso:  bash qa/e2e-seed.sh postgresql+psycopg2://postgres@localhost:55432/ke2e
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export KONTROL_DB_URL="${1:-${KONTROL_DB_URL:-}}"
[ -n "$KONTROL_DB_URL" ] || { echo "qa/e2e-seed.sh: falta la URL de la base" >&2; exit 2; }

PY="${KONTROL_E2E_PYTHON:-$RAIZ/resources/backend/.venv/bin/python}"
[ -x "$PY" ] || { echo "qa/e2e-seed.sh: no hay intérprete ejecutable en $PY" >&2; exit 2; }

export PYTHONPATH="$RAIZ/resources/backend"
cd "$RAIZ"
for guion in qa/pg-e2e-seed.py qa/spec047-e2e-seed.py qa/n6-e2e-seed.py qa/mfa-e2e-identidades.py; do
  echo "· $guion"
  "$PY" "$guion"
done
