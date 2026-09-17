"""Bootstrap local de QA: prepara una BD SQLite de archivo y la inicializa.

Uso (una vez):  PYTHONPATH=resources/backend .venv/bin/python qa/local-backend-bootstrap.py
Luego arrancar:  KONTROL_DB_URL=<misma URL> KONTROL_COOKIE_SECURE=false \
                 PYTHONPATH=resources/backend .venv/bin/python -m uvicorn app.main:app \
                 --host 127.0.0.1 --port 8000

`KONTROL_COOKIE_SECURE=false` **no es opcional** cuando la pila local sirve por
`http://`: WebKit se niega a guardar una cookie `Secure` desde un origen
inseguro —Chromium y Firefox hacen una excepción con localhost, Safari no—, así
que sin esa variable la cookie de refresco no se guarda, la sesión no se
restaura y **toda** navegación devuelve 401 en WebKit. En producción, servida
por HTTPS tras Nginx, la variable va en `true` y así queda en `compose.yaml`.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime, timedelta

DB_FILE = os.environ.get("KONTROL_QA_DB_FILE", os.path.join(tempfile.gettempdir(), "kontrol-qa-n6.db"))
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

os.environ.setdefault("KONTROL_SECRET_KEY", "qa-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")
os.environ.setdefault("KONTROL_COOKIE_SECURE", "false")
os.environ["KONTROL_DB_URL"] = f"sqlite+pysqlite:///{DB_FILE}"
_tmp = tempfile.gettempdir()
os.environ["KONTROL_INSTALLATION_VOLUME_PATH"] = os.path.join(_tmp, "kontrol-qa-license")
os.environ["KONTROL_STORAGE_PATH"] = os.path.join(_tmp, "kontrol-qa-storage")
os.environ["KONTROL_BACKUP_PATH"] = os.path.join(_tmp, "kontrol-qa-backups")

from app.core.config import get_settings  # noqa: E402
get_settings.cache_clear()

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, init_models  # noqa: E402
from app.modules.licensing import service as licensing_service  # noqa: E402
from app.modules.organization.models import Installation  # noqa: E402
from app.modules.setup.api import SetupRequest, initialize  # noqa: E402

init_models()
engine = create_engine(f"sqlite+pysqlite:///{DB_FILE}", future=True, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
import app.core.database as dm
dm._engine = engine  # type: ignore[attr-defined]
dm._SessionLocal = factory  # type: ignore[attr-defined]

db = factory()
initialize(db, SetupRequest(
    tenant_code="DEMO", tenant_name="Empresa Demo QA", company_code="D1",
    company_legal_name="GLOBAL DV ASESORES, C.A.", company_rif="J-50662172-0",
    admin_username="admin", admin_password="Kontrol2026Segura!",
))

# Licencia FULL_ACCESS
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
key = Ed25519PrivateKey.generate()
pub = key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode("utf-8")
inst = db.execute(select(Installation).limit(1)).scalars().first()
now = datetime.now(UTC)
payload = {
    "issuer": "K", "license_id": "LIC-QA-LOCAL", "installation_id": inst.installation_uuid,
    "customer_id": "C1", "contract_id": "C1", "company_tax_id": "J-50662172-0",
    "period_start": (now - timedelta(days=30)).isoformat(),
    "period_end": (now + timedelta(days=120)).isoformat(),
    "critical_warning_start": (now + timedelta(days=180)).isoformat(),
    "read_only_start": (now + timedelta(days=200)).isoformat(),
    "entitlements": {"companies": 5, "users": 25, "modules": ["*"]},
    "minimum_version": "1.0.0", "kid": "kontrol-lic-2026-01",
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

# ---------------------------------------------------------------------------
# Mundo multiempresa de N6 (ARCH-MC-001 §7)
#
# La definición no vive aquí: vive en `qa/n6_world.py`, compartida con la
# siembra sobre la base del E2E (`qa/n6-e2e-seed.py`). Tenerla dos veces era
# tenerla mal —los mismos `(tenant, code)` se describían distinto en cada
# guion y cuál quedaba dependía de cuál corriera último—.
#
#   T1 (DEMO) ─ Empresa A (D1) ─ Sucursal A1 ─ Almacén ALM-A
#             └ Empresa B (D2) ─ Sucursal B1 ─ Almacén ALM-B
#   T2 (DEMO2) ─ Empresa C (E1) ─ Sucursal C1
#
# Usuarios: ua (solo A) · ub (solo B) · uab (A+B) · uc (T2).
# ---------------------------------------------------------------------------
import n6_world  # noqa: E402  (mismo directorio que este guion)

from app.modules.organization.models import Branch, Warehouse  # noqa: E402

db = factory()
ids = n6_world.sembrar(db)

# Sucursales y almacenes existen solo en esta pila autónoma, que sirve además
# para recorrer la interfaz a mano. Las 25 pruebas de N6 no los ejercitan, así
# que la siembra compartida no los escribe: añadir estructura que nadie mira a
# una base compartida solo puede estorbar a las suites que sí cuentan almacenes.
from sqlalchemy import select as _select  # noqa: E402

for _empresa, _code in ((ids["empresa_a"], "A1"), (ids["empresa_b"], "B1"),
                        (ids["empresa_c"], "C1")):
    if not db.execute(_select(Branch).where(Branch.company_id == _empresa,
                                            Branch.code == _code)).scalars().first():
        db.add(Branch(company_id=_empresa, code=_code, name=f"Sucursal {_code}", status="ACTIVE"))
for _empresa, _code in ((ids["empresa_a"], "ALM-A"), (ids["empresa_b"], "ALM-B")):
    if not db.execute(_select(Warehouse).where(Warehouse.company_id == _empresa,
                                               Warehouse.code == _code)).scalars().first():
        db.add(Warehouse(company_id=_empresa, code=_code, name=f"Almacen {_code}", status="ACTIVE"))
db.commit()

# Los identificadores quedan escritos para que las pruebas no los codifiquen a
# mano: sembrar de nuevo genera otros, y una prueba con ids fijos empezaría a
# pasar por el motivo equivocado.
IDS_FILE = os.environ.get("KONTROL_QA_IDS_FILE", os.path.join(tempfile.gettempdir(), "kontrol-n6-ids.json"))
with open(IDS_FILE, "w", encoding="utf-8") as fh:
    json.dump(ids, fh)
print(f"  ids en {IDS_FILE}")
for _clave in ("empresa_a", "empresa_b", "empresa_c"):
    print(f"  {_clave} = {ids[_clave]}")
db.close()

print(f"OK backend N6 listo. DB={DB_FILE}")
