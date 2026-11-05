#!/usr/bin/env bash
# Gobierno regression script (preflight OBS-CERT-GOV-01).
#
# Runs the Gobierno end-to-end regression against an ephemeral stack started by
# `qa/e2e-run.py --orden`. The runner invokes this script from the repository
# root and exports KONTROL_E2E_DB_URL with the database URL of the run.
#
# Usage:
#   python qa/e2e-run.py --con-analizador --orden qa/e2e-gobierno-regresion.sh
#
# Steps:
#   1) Playwright: all e2e/gobierno-*.spec.ts (chromium, firefox, webkit) -> rc_e2e
#   2) Playwright: e2e/uat-humo-gobierno.spec.ts (humo-uat)             -> rc_humo
#   3) Backend scope_scan                                               -> rc_scan
#   4) Backend gobierno_integridad.py                                   -> rc_int
#   5) Exit 0 only if rc_e2e, rc_scan and rc_int are all 0; otherwise 1.

set -u

RAIZ=$(pwd)

# --- 1) Gobierno e2e specs (chromium, firefox, webkit) ----------------------
cd "$RAIZ/resources/frontend" || {
  printf 'base_tras_e2e: rc_e2e=1 rc_scan=1 rc_integridad=1\n'
  exit 1
}

gobierno_specs=()
for f in e2e/gobierno-*.spec.ts; do
  [ -e "$f" ] || continue
  gobierno_specs+=("$f")
done

if [ "${#gobierno_specs[@]}" -eq 0 ]; then
  printf 'e2e-gobierno-regresion: no se encontraron e2e/gobierno-*.spec.ts\n' >&2
  rc_e2e=1
else
  node node_modules/@playwright/test/cli.js test "${gobierno_specs[@]}" \
    --project=chromium --project=firefox --project=webkit --retries=0
  rc_e2e=$?
fi

# --- 2) Humo UAT de Gobierno -----------------------------------------------
node node_modules/@playwright/test/cli.js test e2e/uat-humo-gobierno.spec.ts \
  --project=humo-uat --retries=0
rc_humo=$?

if [ "$rc_e2e" -eq 0 ]; then
  rc_e2e=$rc_humo
fi

# --- 3) scope_scan ----------------------------------------------------------
cd "$RAIZ/resources/backend" || {
  printf 'base_tras_e2e: rc_e2e=%s rc_scan=1 rc_integridad=1\n' "$rc_e2e"
  exit 1
}

KONTROL_SCAN_DB_URL="$KONTROL_E2E_DB_URL" .venv/bin/python -m app.ops.scope_scan
rc_scan=$?

# --- 4) gobierno_integridad.py ---------------------------------------------
KONTROL_SCAN_DB_URL="$KONTROL_E2E_DB_URL" .venv/bin/python "$RAIZ/qa/gobierno_integridad.py"
rc_int=$?

# --- 5) Resultado ----------------------------------------------------------
printf 'base_tras_e2e: rc_e2e=%s rc_scan=%s rc_integridad=%s\n' "$rc_e2e" "$rc_scan" "$rc_int"

if [ "$rc_e2e" -eq 0 ] && [ "$rc_scan" -eq 0 ] && [ "$rc_int" -eq 0 ]; then
  exit 0
fi
exit 1
