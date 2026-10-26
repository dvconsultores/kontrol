"""Fixture canónico multiempresa (ARCH-MC-001, fase N5).

```
T1 ─ Company A ─ Branch A1 ─ Warehouse A1
   └ Company B ─ Branch B1 ─ Warehouse B1
T2 ─ Company C ─ Branch C1 ─ Warehouse C1
```

Usuarios: `UA` (solo A) · `UB` (solo B) · `UAB` (A+B) · `UC` (T2).

Existe porque probar el aislamiento con una sola empresa no prueba nada: si el
sistema solo conoce una, no puede confundirla con otra. La única forma de
demostrar que A y B no se mezclan es tener A y B.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy.orm import Session, sessionmaker

from app.core.company_context import COMPANY_HEADER
from app.core.database import Base, get_db, init_models
from app.modules.setup.api import SetupRequest, _bootstrap_roles, initialize
from tests.conftest import make_engine

PASSWORD = "Kontrol2026Segura!"
PG = os.environ.get("KONTROL_TEST_DB_URL", "")


@dataclass
class Mundo:
    """Todo lo que hace falta para preguntar «¿ve A lo de B?»."""

    client: TestClient
    factory: sessionmaker
    t1: str
    t2: str
    company_a: str
    company_b: str
    company_c: str
    branch_a: str
    branch_b: str
    branch_c: str
    warehouse_a: str
    warehouse_b: str
    warehouse_c: str

    # -- sesiones -----------------------------------------------------------
    def token(self, usuario: str, tenant: str = "T1") -> str:
        r = login_completo(self.client, "/api/v1/auth/login", json={
            "tenant_code": tenant, "username": usuario, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return r.json()["access_token"]

    def como(self, usuario: str, empresa: str | None = None,
             tenant: str = "T1") -> dict:
        """Cabeceras para operar como `usuario` en `empresa`."""
        h = {"Authorization": f"Bearer {self.token(usuario, tenant)}"}
        if empresa:
            h[COMPANY_HEADER] = empresa
        return h

    # -- atajos de petición -------------------------------------------------
    def post(self, ruta: str, usuario: str, empresa: str, cuerpo: dict,
             tenant: str = "T1"):
        return self.client.post(f"/api/v1{ruta}",
                                headers=self.como(usuario, empresa, tenant),
                                json=cuerpo)

    def get(self, ruta: str, usuario: str, empresa: str, tenant: str = "T1"):
        return self.client.get(f"/api/v1{ruta}",
                               headers=self.como(usuario, empresa, tenant))

    def put_json(self, ruta: str, usuario: str, empresa: str, cuerpo: dict,
                 tenant: str = "T1"):
        return self.client.put(f"/api/v1{ruta}",
                               headers=self.como(usuario, empresa, tenant),
                               json=cuerpo)

    def crear(self, ruta: str, usuario: str, empresa: str, cuerpo: dict) -> str:
        """Crea y devuelve el id, fallando con el cuerpo del error a la vista."""
        r = self.post(ruta, usuario, empresa, cuerpo)
        assert r.status_code in (200, 201), f"{ruta}: {r.status_code} {r.text}"
        return r.json()["id"]

    # -- la base, que es la que no puede mentir ------------------------------
    def dueño(self, tabla: str, fila: str, columna: str = "company_id") -> str | None:
        """Lee el propietario **desde PostgreSQL**, no desde la respuesta.

        Que la API filtre bien no dice nada si el dato persistido guarda el
        tenant: sería un filtro correcto sobre un dato indistinguible.
        """
        from sqlalchemy import text

        db = self.factory()
        try:
            return db.execute(
                text(f"SELECT {columna} FROM {tabla} WHERE id = :i"),
                {"i": fila}).scalar_one_or_none()
        finally:
            db.close()

    def filas(self, tabla: str, columna: str = "company_id") -> list[str]:
        from sqlalchemy import text

        db = self.factory()
        try:
            return [r[0] for r in db.execute(text(f"SELECT {columna} FROM {tabla}"))]
        finally:
            db.close()


def _crear_usuario(db: Session, tenant_id: str, username: str,
                   empresas: list[str] | None) -> str:
    """Usuario con alcance explícito. `empresas=None` significa todas."""
    from app.modules.identity_access import service as identity_service
    from app.modules.identity_access.models import UserRole, UserScope

    user = identity_service.create_user(
        db, tenant_id=tenant_id, username=username,
        email=f"{username}@demo.test", password=PASSWORD, created_by=None)
    rol = _bootstrap_roles(db, tenant_id, str(user.id))
    db.add(UserRole(user_id=str(user.id), role_id=str(rol.id), company_id=None))
    if empresas is not None:
        for c in empresas:
            db.add(UserScope(user_id=str(user.id), company_id=c))
    db.flush()
    return str(user.id)


@pytest.fixture(scope="module")
def mundo():
    """Levanta la aplicación con dos tenants y tres empresas."""
    if "postgresql" not in PG:
        pytest.skip("El aislamiento multiempresa se verifica sobre PostgreSQL (P21)")

    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    import app.core.database as dm

    dm._engine = engine        # type: ignore[attr-defined]
    dm._SessionLocal = factory  # type: ignore[attr-defined]

    db = factory()
    initialize(db, SetupRequest(
        tenant_code="T1", tenant_name="Tenant Uno", company_code="A",
        company_legal_name="Empresa A CA", company_rif="J-11111111-1",
        admin_username="admin", admin_password=PASSWORD))

    from app.modules.organization.models import Branch, Company, Installation, Tenant

    t1 = db.query(Tenant).filter(Tenant.code == "T1").one()
    ca = db.query(Company).filter(Company.tenant_id == str(t1.id)).one()

    cb = Company(tenant_id=str(t1.id), code="B", legal_name="Empresa B CA",
                 rif="J-22222222-2", legal_type="JURIDICA",
                 functional_currency="VED", status="ACTIVE")
    db.add(cb)
    db.flush()

    inst = db.query(Installation).first()
    t2 = Tenant(installation_id=str(inst.id), code="T2", name="Tenant Dos",
                plan="MONO_COMPANY", status="ACTIVE")
    db.add(t2)
    db.flush()
    cc = Company(tenant_id=str(t2.id), code="C", legal_name="Empresa C CA",
                 rif="J-33333333-3", legal_type="JURIDICA",
                 functional_currency="VED", status="ACTIVE")
    db.add(cc)
    db.flush()

    ba = Branch(company_id=str(ca.id), code="A1", name="Sucursal A", status="ACTIVE")
    bb = Branch(company_id=str(cb.id), code="B1", name="Sucursal B", status="ACTIVE")
    bc = Branch(company_id=str(cc.id), code="C1", name="Sucursal C", status="ACTIVE")
    db.add_all([ba, bb, bc])
    db.flush()

    _crear_usuario(db, str(t1.id), "ua", [str(ca.id)])
    _crear_usuario(db, str(t1.id), "ub", [str(cb.id)])
    _crear_usuario(db, str(t1.id), "uab", [str(ca.id), str(cb.id)])
    _crear_usuario(db, str(t2.id), "uc", [str(cc.id)])
    db.commit()

    _crear_usuario(db, str(t2.id), "adminc", None)
    db.commit()

    ids = dict(t1=str(t1.id), t2=str(t2.id), ca=str(ca.id), cb=str(cb.id),
               cc=str(cc.id), ba=str(ba.id), bb=str(bb.id), bc=str(bc.id))
    db.close()

    from app.main import create_app

    app = create_app()

    def _db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app)

    # Los almacenes se crean por la API, que es como los crearía un usuario.
    def _almacen(empresa: str, code: str, tenant: str = "T1",
                 usuario: str = "admin") -> str:
        h = {"Authorization": f"Bearer {login_completo(client, '/api/v1/auth/login', json={'tenant_code':tenant,'username':usuario,'password':PASSWORD}).json()['access_token']}",
             COMPANY_HEADER: empresa}
        r = client.post("/api/v1/organization/warehouses", headers=h, json={
            "company_id": empresa, "branch_id": None, "code": code,
            "name": f"Almacén {code}"})
        assert r.status_code == 200, r.text
        return r.json()["id"]

    wa = _almacen(ids["ca"], "ALM-A")
    wb = _almacen(ids["cb"], "ALM-B")
    wc = _almacen(ids["cc"], "ALM-C", tenant="T2", usuario="adminc")

    yield Mundo(client=client, factory=factory, t1=ids["t1"], t2=ids["t2"],
                company_a=ids["ca"], company_b=ids["cb"], company_c=ids["cc"],
                branch_a=ids["ba"], branch_b=ids["bb"], branch_c=ids["bc"],
                warehouse_a=wa, warehouse_b=wb, warehouse_c=wc)
