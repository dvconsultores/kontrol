#!/usr/bin/env bash
# KONTROL - activa una licencia de PRUEBA autofirmada con la clave privada de
# la propia instalación (solo válida mientras KONTROL_LICENSE_PUBLIC_KEY_PEM
# esté vacío). En producción, el propietario de KONTROL firma con su clave
# privada central y el archivo lo importa el administrador local, con sesión y
# `license:create`, por POST /api/v1/license/activate.
# Uso (desde cualquier directorio del servidor):
#   bash scripts/activate-test-license.sh
# Re-ejecutar con bash aunque se invoque con sh (sh/dash no soporta bashisms).
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="${KONTROL_COMPOSE:-compose.yaml}"
COMPOSE_FILE="$REPO/$COMPOSE"

if ! docker compose -f "$COMPOSE_FILE" ps --services 2>/dev/null | grep -q '^backend$'; then
  echo "✗ El servicio backend no está activo. Ejecute primero bash scripts/setup.sh" >&2
  exit 1
fi

docker compose -f "$COMPOSE_FILE" exec -T backend python - <<'PY'
import json
import os
from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives import serialization

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.modules.licensing import service as ls

db = get_session_factory()()
# Crea la identidad de instalación si no existe (igual que el asistente de setup).
inst = ls.get_or_create_installation(db)

now = datetime.now(UTC)
payload = {
    "license_id": f"KTL-LIC-TEST-{now:%Y%m%d%H%M%S}",
    "installation_id": inst.installation_uuid,
    "customer_id": "cliente-prueba",
    "contract_id": "contrato-prueba",
    "period_start": (now - timedelta(days=1)).isoformat(),
    "period_end": (now + timedelta(days=365)).isoformat(),
    "critical_warning_start": (now + timedelta(days=335)).isoformat(),
    "read_only_start": (now + timedelta(days=345)).isoformat(),
    "entitlements": {"users": 10, "modules": ["*"]},
    "minimum_version": "1.0.0",
    "kid": "kontrol-lic-2026-01",
}

canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")

key_path = os.path.join(get_settings().installation_volume_path, "installation_private_key.pem")
with open(key_path, "rb") as fh:
    priv = serialization.load_pem_private_key(fh.read(), password=None)
signature_hex = priv.sign(canonical).hex()

state = ls.import_license(db, payload=payload, signature_hex=signature_hex, source="TEST")
print(f"✓ Licencia de prueba ACTIVADA: {state.license_id} | modo: {state.mode}")
print(f"  período: {state.period_start} -> {state.period_end}")
db.close()
PY
