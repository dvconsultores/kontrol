"""Reproducción: Decimal+float en factura proveedor (POSTED / open-items)."""
import json
import os
import tempfile
from datetime import UTC, datetime, timedelta

os.environ.setdefault("KONTROL_SECRET_KEY", "x" * 40)
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")
os.environ.setdefault("KONTROL_COOKIE_SECURE", "false")
os.environ.setdefault("KONTROL_DB_URL", "sqlite+pysqlite:///:memory:")
_t = tempfile.gettempdir()
os.environ.setdefault("KONTROL_INSTALLATION_VOLUME_PATH", _t + "/l")
os.environ.setdefault("KONTROL_STORAGE_PATH", _t + "/s")
os.environ.setdefault("KONTROL_BACKUP_PATH", _t + "/b")

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

engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                       connect_args={"check_same_thread": False}, poolclass=StaticPool)
init_models()
Base.metadata.create_all(engine)
factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
import app.core.database as dm
dm._engine = engine  # type: ignore[attr-defined]
dm._SessionLocal = factory  # type: ignore[attr-defined]

db = factory()
initialize(db, SetupRequest(
    tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1",
    company_legal_name="Demo C.A.", company_rif="J-12345678-9",
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
    "issuer": "K", "license_id": "L", "installation_id": inst.installation_uuid,
    "customer_id": "C", "contract_id": "C", "company_tax_id": "J-12345678-9",
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


def _g():
    d = factory()
    yield d
    d.close()


app.dependency_overrides[get_db] = _g
client = TestClient(app, raise_server_exceptions=True)
r = client.post("/api/v1/auth/login", json={"tenant_code": "DEMO", "username": "admin", "password": "Kontrol2026Segura!"})
h = {"Authorization": f"Bearer {r.json()['access_token']}"}

sup = client.post("/api/v1/maestros/terceros", headers=h, json={"code": "P1", "name": "PROV A", "roles": ["PROVEEDOR"]}).json()
it = client.post("/api/v1/maestros/catalogos/items", headers=h, json={"code": "ART1", "name": "A", "item_type": "PRODUCT"}).json()
inv = client.post("/api/v1/purchasing/supplier-invoices", headers=h,
                  json={"supplier_id": sup["id"], "invoice_number": "F1", "control_number": None, "issue_date": None, "currency": "VED"}).json()
iid = inv["id"]
print("invoice created", iid)
for q, p in [(5, 40.0), (2, 10.5)]:
    rr = client.post(f"/api/v1/purchasing/supplier-invoices/{iid}/lines", headers=h,
                     json={"product_id": it["id"], "quantity": q, "unit_price": p, "tax_amount": 0})
    print("add line", rr.status_code, rr.text[:120])
for t in ("VALIDATED", "APPROVED", "POSTED"):
    rr = client.post(f"/api/v1/purchasing/supplier-invoices/{iid}/transition", headers=h, json={"target": t})
    print("transition", t, rr.status_code, rr.text[:200])
    if rr.status_code >= 400:
        import traceback
        break
print("=== GET open-items ===")
rr = client.get("/api/v1/purchasing/open-items", headers=h)
print("open-items", rr.status_code, rr.text[:300])
