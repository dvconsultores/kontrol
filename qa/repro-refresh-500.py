"""Reproduce el bug de refresh (500 timezone) — QA no destructivo."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime, timedelta

os.environ.setdefault("KONTROL_SECRET_KEY", "qa-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")
os.environ.setdefault("KONTROL_COOKIE_SECURE", "false")
os.environ["KONTROL_DB_URL"] = "sqlite+pysqlite:///:memory:"
_tmp = tempfile.gettempdir()
os.environ["KONTROL_INSTALLATION_VOLUME_PATH"] = os.path.join(_tmp, "k-lic")
os.environ["KONTROL_STORAGE_PATH"] = os.path.join(_tmp, "k-sto")
os.environ["KONTROL_BACKUP_PATH"] = os.path.join(_tmp, "k-bak")

from app.core.config import get_settings  # noqa: E402
get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, get_db, init_models  # noqa: E402
from app.modules.licensing import service as licensing_service  # noqa: E402
from app.modules.organization.models import Installation  # noqa: E402
from app.modules.setup.api import SetupRequest, initialize  # noqa: E402

engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
init_models()
Base.metadata.create_all(engine)
f = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
import app.core.database as dm  # noqa: E402
dm._engine = engine  # type: ignore[attr-defined]
dm._SessionLocal = f  # type: ignore[attr-defined]

db = f()
initialize(db, SetupRequest(
    tenant_code="DEMO", tenant_name="Empresa Demo QA", company_code="D1",
    company_legal_name="GLOBAL DV ASESORES, C.A.", company_rif="J-50662172-0",
    admin_username="admin", admin_password="Kontrol2026Segura!",
))

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

key = Ed25519PrivateKey.generate()
pub = key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode("utf-8")
inst = db.execute(select(Installation).limit(1)).scalars().first()
now = datetime.now(UTC)
payload = {
    "issuer": "K", "license_id": "LIC", "installation_id": inst.installation_uuid,
    "customer_id": "C", "contract_id": "C", "company_tax_id": "J-50662172-0",
    "period_start": (now - timedelta(days=30)).isoformat(),
    "period_end": (now + timedelta(days=120)).isoformat(),
    "critical_warning_start": (now + timedelta(days=180)).isoformat(),
    "read_only_start": (now + timedelta(days=200)).isoformat(),
    "entitlements": {"companies": 1, "users": 25, "modules": ["*"]},
    "minimum_version": "1.0.0", "kid": "k",
}
sig = key.sign(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hex()
os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = pub
get_settings.cache_clear()
try:
    licensing_service.import_license(db, payload=payload, signature_hex=sig, source="MANUAL")
finally:
    os.environ.pop("KONTROL_LICENSE_PUBLIC_KEY_PEM", None)
    get_settings.cache_clear()
db.close()

from app.main import create_app  # noqa: E402
app = create_app()


def _gdb():
    d = f()
    try:
        yield d
    finally:
        d.close()


app.dependency_overrides[get_db] = _gdb
c = TestClient(app)
r = c.post("/api/v1/auth/login", json={"tenant_code": "DEMO", "username": "admin", "password": "Kontrol2026Segura!"})
print("login:", r.status_code)
refresh_cookie = r.cookies.get("kontrol_refresh")
print("refresh cookie presente:", bool(refresh_cookie))
r2 = c.post("/api/v1/auth/refresh", cookies={"kontrol_refresh": refresh_cookie} if refresh_cookie else {})
print("refresh:", r2.status_code, r2.text[:300])
