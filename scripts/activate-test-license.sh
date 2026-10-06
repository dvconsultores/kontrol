#!/usr/bin/env bash
# KONTROL - activa una licencia de PRUEBA firmada por un firmante sintético
# efímero, cuya clave pública se declara como ancla solo dentro de este proceso
# (nunca la clave de la instalación; se niega en prod). En producción, el
# propietario de KONTROL firma con su clave
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
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

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

# Firmante SINTÉTICO, solo de prueba: un par efímero cuya clave pública se declara aquí,
# explícitamente, como ancla de confianza de ESTE proceso. Nunca la clave de la instalación
# (identifica a la instalación; no es ancla) y nunca en producción.
if get_settings().environment == "prod":
    raise SystemExit("La licencia de PRUEBA no se activa en prod: configure KONTROL_LICENSE_PUBLIC_KEY_PEM con la clave del propietario e importe su licencia firmada.")
firmante = Ed25519PrivateKey.generate()
os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = firmante.public_key().public_bytes(
    encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
get_settings.cache_clear()
signature_hex = firmante.sign(canonical).hex()

state = ls.import_license(db, payload=payload, signature_hex=signature_hex, source="TEST")
print(f"✓ Licencia de prueba ACTIVADA: {state.license_id} | modo: {state.mode}")
print(f"  período: {state.period_start} -> {state.period_end}")
db.close()
PY
