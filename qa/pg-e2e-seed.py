"""Siembra la base de QA sobre PostgreSQL para la suite E2E (Spec 045).

Crea instalación, tenant, empresa, usuario admin y una licencia firmada válida.
No usa datos productivos ni credenciales reales.

Uso:
    KONTROL_DB_URL=postgresql+psycopg2://... PYTHONPATH=resources/backend \
        resources/backend/.venv/bin/python qa/pg-e2e-seed.py
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta

os.environ.setdefault("KONTROL_SECRET_KEY", "qa-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")
os.environ.setdefault("KONTROL_COOKIE_SECURE", "false")
for _k, _v in (("KONTROL_INSTALLATION_VOLUME_PATH", "/tmp/k-lic"),
               ("KONTROL_STORAGE_PATH", "/tmp/k-st"),
               ("KONTROL_BACKUP_PATH", "/tmp/k-bk")):
    os.environ.setdefault(_k, _v)

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.core.database import get_session_factory  # noqa: E402
from app.modules.licensing import service as licensing_service  # noqa: E402
from app.modules.licensing.models import LicenseState  # noqa: E402
from app.modules.organization.models import Installation  # noqa: E402
from app.modules.setup.api import SetupRequest, initialize  # noqa: E402


def _licencia_vigente(db) -> bool:
    """¿Hay ya una licencia que sirva?

    Esta siembra corre ahora antes de cada ejecución de la suite. Importar otra
    vez una licencia equivalente dejaría el estado igual —se actualiza por
    instalación— pero añadiría un artefacto y un evento de auditoría por
    ejecución: una historia de importaciones que nunca ocurrieron, sobre una
    base de QA que dura semanas. Se importa cuando hace falta, no siempre.
    Desde GOV-0-01 una licencia sin el módulo `gobierno` no sirve:
    se reimporta.
    """
    estado = db.execute(select(LicenseState).limit(1)).scalars().first()
    return (estado is not None
            and estado.mode in {"FULL_ACCESS", "GRACE"}
            and estado.period_end > datetime.now(UTC)
            and "gobierno" in ((estado.entitlements or {}).get("modules") or []))


ADMIN_PASSWORD = os.environ.get("KONTROL_E2E_PASSWORD", "Kontrol2026Segura!")

db = get_session_factory()()
try:
    try:
        initialize(db, SetupRequest(
            tenant_code="DEMO", tenant_name="Empresa Demo QA", company_code="D1",
            company_legal_name="Demo C.A.", company_rif="J-12345678-9",
            admin_username="admin", admin_password=ADMIN_PASSWORD))
        db.commit()
        print("setup: creado")
    except Exception as exc:  # ya inicializada
        db.rollback()
        print(f"setup: {str(exc)[:60]}")

    if _licencia_vigente(db):
        print("licencia: ya vigente, no se reimporta")
        raise SystemExit(0)

    # Firmante sintético. En una corrida de `qa/e2e-run.py` es el de la corrida, cuya pública ya
    # es el ancla del backend y de este proceso; fuera de una corrida (siembra manual de QA) se
    # genera uno efímero y se declara su pública como ancla de ESTE proceso, explícitamente.
    # Nunca la clave de la instalación, y nunca en producción.
    if os.environ.get("KONTROL_ENVIRONMENT", "local") not in ("local", "dev", "qa"):
        raise SystemExit("pg-e2e-seed.py: la licencia sintética solo se siembra en entornos de QA")
    ruta_firmante = os.environ.get("KONTROL_E2E_LICENSE_SIGNING_KEY")
    if ruta_firmante:
        with open(ruta_firmante, "rb") as fh:
            key = serialization.load_pem_private_key(fh.read(), password=None)
    else:
        key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    inst = db.execute(select(Installation).limit(1)).scalars().first()
    now = datetime.now(UTC)
    payload = {
        "issuer": "KONTROL-QA", "license_id": "LIC-E2E",
        "installation_id": inst.installation_uuid, "customer_id": "C1", "contract_id": "C1",
        "company_tax_id": "J-12345678-9",
        "period_start": (now - timedelta(days=30)).isoformat(),
        "period_end": (now + timedelta(days=300)).isoformat(),
        "read_only_start": (now + timedelta(days=330)).isoformat(),
        "critical_warning_start": (now + timedelta(days=320)).isoformat(),
        "plan": "MULTI_COMPANY", "minimum_version": "1.0.0", "kid": "kontrol-lic-2026-01",
        "entitlements": {"modules": ["gobierno"]},  # GOV-0-01: la instalación de QA habilita la línea de Gobierno
    }
    signature = key.sign(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hex()
    os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = pub
    get_settings.cache_clear()
    licensing_service.import_license(db, payload=payload, signature_hex=signature, source="MANUAL")
    db.commit()
    print("licencia: importada")
finally:
    db.close()
