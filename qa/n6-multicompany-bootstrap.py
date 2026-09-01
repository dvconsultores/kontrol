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
# Dos empresas del mismo tenant, que es el único escenario donde el defecto que
# esta fase corrige se puede manifestar, más un segundo tenant para comprobar
# que la frontera de arriba tampoco se cruza.
#
#   T1 (DEMO) ─ Empresa A ─ Sucursal A1 ─ Almacén A1
#             └ Empresa B ─ Sucursal B1 ─ Almacén B1
#   T2 (DEMO2) ─ Empresa C
#
# Usuarios: ua (solo A) · ub (solo B) · uab (A+B) · uc (T2).
# ---------------------------------------------------------------------------
from app.modules.identity_access import service as identity_service  # noqa: E402
from app.modules.identity_access.models import UserRole, UserScope  # noqa: E402
from app.modules.organization.models import Branch, Company, Tenant, Warehouse  # noqa: E402
from app.modules.setup.api import _bootstrap_roles  # noqa: E402

PASS = "Kontrol2026Segura!"
db = factory()

t1 = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().one()
ca = db.execute(select(Company).where(Company.tenant_id == str(t1.id))).scalars().first()

cb = Company(tenant_id=str(t1.id), code="D2",
             legal_name="INVERSIONES SEGUNDA EMPRESA COMPAÑIA ANONIMA",
             rif="J-40771283-5", legal_type="JURIDICA",
             functional_currency="VED", status="ACTIVE")
db.add(cb)
db.flush()

t2 = Tenant(installation_id=str(inst.id), code="DEMO2", name="Otro Cliente",
            plan="MONO_COMPANY", status="ACTIVE")
db.add(t2)
db.flush()
cc = Company(tenant_id=str(t2.id), code="E1", legal_name="TERCERA EMPRESA CA",
             rif="J-30303030-3", legal_type="JURIDICA",
             functional_currency="VED", status="ACTIVE")
db.add(cc)
db.flush()

for empresa, code in ((ca, "A1"), (cb, "B1"), (cc, "C1")):
    db.add(Branch(company_id=str(empresa.id), code=code, name=f"Sucursal {code}", status="ACTIVE"))
db.flush()

for empresa, code in ((ca, "ALM-A"), (cb, "ALM-B")):
    db.add(Warehouse(company_id=str(empresa.id), code=code, name=f"Almacen {code}",
                     status="ACTIVE"))
db.flush()


def _usuario(tenant_id, username, empresas):
    u = identity_service.create_user(db, tenant_id=tenant_id, username=username,
                                     email=f"{username}@qa.test", password=PASS, created_by=None)
    rol = _bootstrap_roles(db, tenant_id, str(u.id))
    db.add(UserRole(user_id=str(u.id), role_id=str(rol.id), company_id=None))
    for c in empresas:
        db.add(UserScope(user_id=str(u.id), company_id=c))
    db.flush()


# Un tercero identificable en cada empresa. Es lo que permite comprobar que la
# lista de una no aparece bajo la otra: sin datos distintos, dos listas vacías
# tampoco se contaminan y el aislamiento quedaría "demostrado" por no haber nada.
from app.modules.master_data.models import Party  # noqa: E402

for empresa, marca in ((ca, "SOLO-DE-A"), (cb, "SOLO-DE-B")):
    db.add(Party(company_id=str(empresa.id), code=marca, name=f"Tercero {marca}",
                 legal_name=f"Tercero {marca}", person_type="JURIDICA",
                 roles=["CLIENTE"], status="ACTIVE"))
db.flush()

_usuario(str(t1.id), "ua", [str(ca.id)])
_usuario(str(t1.id), "ub", [str(cb.id)])
_usuario(str(t1.id), "uab", [str(ca.id), str(cb.id)])
_usuario(str(t2.id), "uc", [str(cc.id)])
db.commit()
# Los identificadores quedan escritos para que las pruebas no los codifiquen a
# mano: sembrar de nuevo genera otros, y una prueba con ids fijos empezaría a
# pasar por el motivo equivocado.
IDS_FILE = os.environ.get("KONTROL_QA_IDS_FILE", os.path.join(tempfile.gettempdir(), "kontrol-n6-ids.json"))
with open(IDS_FILE, "w", encoding="utf-8") as fh:
    json.dump({"empresa_a": str(ca.id), "empresa_b": str(cb.id), "empresa_c": str(cc.id),
               "tenant_1": str(t1.id), "tenant_2": str(t2.id)}, fh)
print(f"  ids en {IDS_FILE}")
print(f"  empresa A = {ca.id}  ({ca.legal_name})")
print(f"  empresa B = {cb.id}  ({cb.legal_name})")
print(f"  empresa C = {cc.id}  (tenant DEMO2)")
db.close()

print(f"OK backend N6 listo. DB={DB_FILE}")
