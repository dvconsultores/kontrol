"""Firma una licencia SINTÉTICA para la instalación de una corrida E2E.

Uso (la URL de la base viaja en el entorno, nunca en la línea de órdenes):
    KONTROL_DB_URL=postgresql+psycopg2://... KONTROL_E2E_LICENSE_SIGNING_KEY=<estado>/license/qa_license_signing_key.pem \\
    PYTHONPATH=resources/backend python qa/licencia_firmada.py <license_id> [--otra-instalacion] [--firma-invalida]

Imprime en la salida estándar el JSON `{"payload": {...}, "signature_hex": "..."}` que espera
`POST /api/v1/license/activate`. Firma con el **firmante sintético de la corrida** —el par que
`qa/e2e-run.py` genera y cuya clave pública declara como `KONTROL_LICENSE_PUBLIC_KEY_PEM` del
backend de esa corrida (FR-010-154)—. Nunca con la clave de la instalación: esa identifica a la
instalación y no es ancla de confianza. Solo en entornos de QA.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

os.environ.setdefault("KONTROL_SECRET_KEY", "qa-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.database import get_session_factory, init_models  # noqa: E402
from app.modules.organization.models import Installation  # noqa: E402


def payload_sintetico(license_id: str, installation_id: str) -> dict[str, object]:
    """Una licencia como la de la siembra E2E (`qa/pg-e2e-seed.py`): vigente, mismo `kid`."""
    ahora = datetime.now(UTC)
    return {
        "issuer": "KONTROL-QA", "license_id": license_id, "installation_id": installation_id,
        "customer_id": "C1", "contract_id": "C1", "company_tax_id": "J-12345678-9",
        "period_start": (ahora - timedelta(days=30)).isoformat(),
        "period_end": (ahora + timedelta(days=300)).isoformat(),
        "critical_warning_start": (ahora + timedelta(days=320)).isoformat(),
        "read_only_start": (ahora + timedelta(days=330)).isoformat(),
        "plan": "MULTI_COMPANY", "minimum_version": "1.0.0", "kid": "kontrol-lic-2026-01",
    }


def firmar(payload: dict[str, object], clave: Ed25519PrivateKey) -> str:
    canonico = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return clave.sign(canonico).hex()


def main(argv: list[str]) -> int:
    if not argv or argv[0].startswith("--"):
        print("uso: licencia_firmada.py <license_id> [--otra-instalacion] [--firma-invalida]", file=sys.stderr)
        return 2
    if os.environ.get("KONTROL_ENVIRONMENT", "local") not in ("local", "dev", "qa"):
        raise RuntimeError("este guion solo firma licencias de prueba en entornos de QA")
    ruta_firmante = os.environ.get("KONTROL_E2E_LICENSE_SIGNING_KEY")
    if not ruta_firmante:
        raise RuntimeError("KONTROL_E2E_LICENSE_SIGNING_KEY es obligatoria: el firmante sintético lo genera la corrida")
    clave = serialization.load_pem_private_key(Path(ruta_firmante).read_bytes(), password=None)
    if not isinstance(clave, Ed25519PrivateKey):
        raise RuntimeError("el firmante sintético no es Ed25519")

    init_models()
    db = get_session_factory()()
    try:
        instalacion = db.execute(select(Installation).order_by(Installation.created_at).limit(1)).scalars().first()
    finally:
        db.close()
    if instalacion is None:
        raise RuntimeError("la base no tiene instalación")

    destino = "KTL-QA-OTRA-INSTALACION" if "--otra-instalacion" in argv else instalacion.installation_uuid
    payload = payload_sintetico(argv[0], destino)
    firma = "00" * 64 if "--firma-invalida" in argv else firmar(payload, clave)
    print(json.dumps({"payload": payload, "signature_hex": firma}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
