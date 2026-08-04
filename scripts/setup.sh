#!/usr/bin/env bash
# KONTROL - instalación y activación en un solo paso.
# Preflight → pull → up -d → migraciones → licencia de prueba → estado.
#
# Uso:
#   bash scripts/setup.sh                          # todo (instala, migra, activa licencia de prueba)
#   KONTROL_TEST_LICENSE=0 bash scripts/setup.sh   # sin licencia de prueba (producción)
#
# En producción, la licencia la firma el propietario de KONTROL con su clave
# privada central y se importa por POST /api/v1/license/activate (UI o curl).
# Re-ejecutar con bash aunque se invoque con sh (sh/dash no soporta bashisms).
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
COMPOSE="${KONTROL_COMPOSE:-compose.yaml}"

echo "=== KONTROL - Setup completo ==="

# 1) .env
if [[ ! -f .env ]]; then
  echo "✗ Falta .env. Copie desde .env.example y complete los secretos."
  exit 1
fi

# 2) Preflight
echo "1/6 Preflight"
python3 kontrol.py preflight

# 3) Imágenes y pila
echo "2/6 Descargar imágenes"
docker compose -f "$COMPOSE" pull
echo "3/6 Levantar pila"
docker compose -f "$COMPOSE" up -d

# 4) Esperar a que el backend esté activo
echo "4/6 Esperando backend..."
for _ in $(seq 1 60); do
  if docker compose -f "$COMPOSE" top backend >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
if ! docker compose -f "$COMPOSE" top backend >/dev/null 2>&1; then
  echo "✗ El backend no está activo. Revise: docker compose -f $COMPOSE logs backend" >&2
  exit 1
fi

# 5) Migraciones (idempotente: iniciales y futuras; también en cada arranque)
echo "5/6 Migraciones (alembic upgrade head)"
docker compose -f "$COMPOSE" exec -T backend alembic upgrade head

# 6) Licencia
if [[ "${KONTROL_TEST_LICENSE:-1}" != "0" ]]; then
  echo "6/6 Activar licencia de PRUEBA (KONTROL_TEST_LICENSE=0 para omitir)"
  docker compose -f "$COMPOSE" exec -T backend python - <<'PY'
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
db.close()
PY
else
  echo "6/6 Licencia: omitida (KONTROL_TEST_LICENSE=0). Importe la licencia firmada del propietario (POST /api/v1/license/activate)."
fi

echo ""
echo "=== Estado ==="
docker compose -f "$COMPOSE" ps
echo ""
docker compose -f "$COMPOSE" exec -T backend python -c \
  "import urllib.request;print('Health:', urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live').read().decode())" 2>/dev/null \
  || echo "Health: no accesible"
echo ""
echo "✓ Listo. Abra la UI (NPM o puerto publicado) y ejecute el asistente de empresa/administrador."
