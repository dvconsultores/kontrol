"""Deuda WAREHOUSE-BRANCH-CROSS-COMPANY: la sucursal de un almacén debe pertenecer a la
empresa activa del contexto (ADR-D0-014), mismo precedente que establecimientos.

Las pruebas pasan en SQLite y PostgreSQL, sin skip, sin mocks.
"""
from __future__ import annotations

import ast
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy.orm import Session, sessionmaker

from app.core.company_context import COMPANY_HEADER
from app.core.database import Base, get_db, init_models
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import UserRole, UserScope
from app.modules.organization.models import Branch, Company, Installation, Tenant, Warehouse
from app.modules.setup.api import SetupRequest, _bootstrap_roles, initialize
from tests.conftest import make_engine

PASSWORD = "Kontrol2026Segura!"

EMPRESA_A = EMPRESA_B = EMPRESA_C = None
BRANCH_A = BRANCH_B = BRANCH_C = None
CLIENT = None
FACTORY = None


def _crear_usuario(db, tenant_id: str, username: str, empresas: list[str] | None) -> str:
    user = identity_service.create_user(
        db, tenant_id=tenant_id, username=username,
        email=f"{username}@demo.test", password=PASSWORD, created_by=None)

    rol = _bootstrap_roles(db, tenant_id, str(user.id))
    db.add(UserRole(user_id=str(user.id), role_id=str(rol.id), company_id=None))
    if empresas is not None:
        for empresa_id in empresas:
            db.add(UserScope(user_id=str(user.id), company_id=empresa_id))
    db.flush()
    return str(user.id)


@pytest.fixture(scope="module", autouse=True)
def _mundo():
    global CLIENT, FACTORY, EMPRESA_A, EMPRESA_B, EMPRESA_C, BRANCH_A, BRANCH_B, BRANCH_C

    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    import app.core.database as dm

    dm._engine = engine  # type: ignore[attr-defined]
    dm._SessionLocal = factory  # type: ignore[attr-defined]

    db = factory()
    initialize(db, SetupRequest(
        tenant_code="T1", tenant_name="Tenant Uno", company_code="A",
        company_legal_name="Empresa A CA", company_rif="J-11111111-1",
        admin_username="admin", admin_password=PASSWORD))

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
    _crear_usuario(db, str(t1.id), "uab", [str(ca.id), str(cb.id)])

    sinrol = identity_service.create_user(
        db, tenant_id=str(t1.id), username="sinrol", email="sinrol@demo.test",
        password=PASSWORD, created_by=None)
    db.add(UserScope(user_id=str(sinrol.id), company_id=str(ca.id)))

    db.commit()

    EMPRESA_A, EMPRESA_B, EMPRESA_C = str(ca.id), str(cb.id), str(cc.id)
    BRANCH_A, BRANCH_B, BRANCH_C = str(ba.id), str(bb.id), str(bc.id)
    db.close()

    from app.main import create_app

    app = create_app()

    def _override_get_db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _override_get_db
    FACTORY = factory
    CLIENT = TestClient(app, raise_server_exceptions=False)
    yield CLIENT
    engine.dispose()


def _login(usuario: str) -> str:
    r = login_completo(CLIENT, "/api/v1/auth/login", json={
        "tenant_code": "T1", "username": usuario, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _como(usuario: str, empresa: str, tenant: str = "T1") -> dict:
    token = _login(usuario)
    return {
        "Authorization": f"Bearer {token}",
        COMPANY_HEADER: empresa,
    }


def _alta(usuario: str, empresa: str, code: str, **extra):
    headers = _como(usuario, empresa)
    payload = {"company_id": empresa, "code": code, "name": f"Almacén {code}", **extra}
    return CLIENT.post("/api/v1/organization/warehouses", headers=headers, json=payload)


def _branch_de(warehouse_id: str) -> str | None:
    db = FACTORY()
    try:
        warehouse = db.get(Warehouse, warehouse_id)
        return str(warehouse.branch_id) if warehouse and warehouse.branch_id else None
    finally:
        db.close()


def _cuenta_codigo(code: str) -> int:
    db = FACTORY()
    try:
        return db.query(Warehouse).filter_by(code=code).count()
    finally:
        db.close()


def test_b01_ua_en_a_branch_a1_ok():
    r = _alta("ua", EMPRESA_A, "B-01", branch_id=BRANCH_A)
    assert r.status_code == 200, r.text
    assert _branch_de(r.json()["id"]) == BRANCH_A


def test_b02_ua_en_a_branch_b1_otra_empresa_404():
    r = _alta("ua", EMPRESA_A, "B-02", branch_id=BRANCH_B)
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "BRANCH_NOT_FOUND"
    assert r.json()["message"] == "Sucursal no encontrada"
    assert _cuenta_codigo("B-02") == 0


def test_b03_ua_en_a_branch_c1_otro_tenant_404():
    r = _alta("ua", EMPRESA_A, "B-03", branch_id=BRANCH_C)
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "BRANCH_NOT_FOUND"
    assert _cuenta_codigo("B-03") == 0


def test_b04_ua_en_a_branch_inexistente_mismo_contrato_que_b02():
    inexistente = str(uuid.uuid4())
    r = _alta("ua", EMPRESA_A, "B-04", branch_id=inexistente)
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "BRANCH_NOT_FOUND"
    assert r.json()["message"] == "Sucursal no encontrada"

    referencia = _alta("ua", EMPRESA_A, "B-04-REF", branch_id=BRANCH_B)
    assert referencia.status_code == 404, referencia.text
    assert r.json()["code"] == referencia.json()["code"]
    assert r.json()["message"] == referencia.json()["message"]


def test_b05_ua_en_a_sin_branch_id_ok():
    r = _alta("ua", EMPRESA_A, "B-05")
    assert r.status_code == 200, r.text
    assert _branch_de(r.json()["id"]) is None


def test_b06_patch_a_branch_a1_ok():
    r = _alta("ua", EMPRESA_A, "B-06", branch_id=None)
    assert r.status_code == 200, r.text
    wid = r.json()["id"]

    r = CLIENT.patch(
        f"/api/v1/organization/warehouses/{wid}",
        headers=_como("ua", EMPRESA_A),
        json={"branch_id": BRANCH_A},
    )
    assert r.status_code == 200, r.text
    assert _branch_de(wid) == BRANCH_A


def test_b07_patch_a_branch_b1_404_y_no_cambia():
    r = _alta("ua", EMPRESA_A, "B-07", branch_id=BRANCH_A)
    assert r.status_code == 200, r.text
    wid = r.json()["id"]
    version = r.json()["version"]

    r = CLIENT.patch(
        f"/api/v1/organization/warehouses/{wid}",
        headers=_como("ua", EMPRESA_A),
        json={"branch_id": BRANCH_B},
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "BRANCH_NOT_FOUND"
    assert _branch_de(wid) == BRANCH_A

    r = CLIENT.get(f"/api/v1/organization/warehouses/{wid}", headers=_como("ua", EMPRESA_A))
    assert r.status_code == 200, r.text
    assert r.json()["version"] == version


def test_b08_patch_a_branch_c1_404_y_no_cambia():
    r = _alta("ua", EMPRESA_A, "B-08", branch_id=BRANCH_A)
    assert r.status_code == 200, r.text
    wid = r.json()["id"]

    r = CLIENT.patch(
        f"/api/v1/organization/warehouses/{wid}",
        headers=_como("ua", EMPRESA_A),
        json={"branch_id": BRANCH_C},
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "BRANCH_NOT_FOUND"
    assert _branch_de(wid) == BRANCH_A


def test_b09_patch_branch_null_desliga():
    r = _alta("ua", EMPRESA_A, "B-09", branch_id=BRANCH_A)
    assert r.status_code == 200, r.text
    wid = r.json()["id"]

    r = CLIENT.patch(
        f"/api/v1/organization/warehouses/{wid}",
        headers=_como("ua", EMPRESA_A),
        json={"branch_id": None},
    )
    assert r.status_code == 200, r.text
    assert _branch_de(wid) is None


def test_b10_patch_sin_branch_id_no_toca_branch():
    r = _alta("ua", EMPRESA_A, "B-10", branch_id=BRANCH_A)
    assert r.status_code == 200, r.text
    wid = r.json()["id"]

    r = CLIENT.patch(
        f"/api/v1/organization/warehouses/{wid}",
        headers=_como("ua", EMPRESA_A),
        json={"name": "otro"},
    )
    assert r.status_code == 200, r.text
    assert _branch_de(wid) == BRANCH_A


def test_b11_uab_en_b_branch_b1_ok():
    r = _alta("uab", EMPRESA_B, "B-11", branch_id=BRANCH_B)
    assert r.status_code == 200, r.text
    assert _branch_de(r.json()["id"]) == BRANCH_B


def test_b12_uab_en_a_branch_b1_404():
    r = _alta("uab", EMPRESA_A, "B-12", branch_id=BRANCH_B)
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "BRANCH_NOT_FOUND"


def test_b13_sin_auth_401_y_sin_rol_403():
    r = CLIENT.post("/api/v1/organization/warehouses", json={
        "company_id": EMPRESA_A, "code": "B-13", "name": "Sin auth", "branch_id": BRANCH_B})
    assert r.status_code == 401, r.text

    r = _alta("sinrol", EMPRESA_A, "B-13", branch_id=BRANCH_B)
    assert r.status_code == 403, r.text


def test_b14_almacen_de_b_patch_por_ua_en_a_404_warehouse_not_found():
    r_alta_b = _alta("uab", EMPRESA_B, "B-14", branch_id=BRANCH_B)
    assert r_alta_b.status_code == 200, r_alta_b.text
    wid = r_alta_b.json()["id"]

    r = CLIENT.patch(
        f"/api/v1/organization/warehouses/{wid}",
        headers=_como("ua", EMPRESA_A),
        json={"branch_id": BRANCH_A},
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "WAREHOUSE_NOT_FOUND"


def test_b15_contrato_ast_de_warehouse_api():
    ruta = Path(__file__).resolve().parents[1] / "app" / "modules" / "organization" / "warehouse_api.py"
    arbol = ast.parse(ruta.read_text())

    funcion = next(
        nodo for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef)
        and nodo.name == "_exige_sucursal_propia"
    )
    assert isinstance(funcion, ast.FunctionDef | ast.AsyncFunctionDef)

    codigo_funcion = ast.unparse(funcion)
    assert ".company_id" in codigo_funcion
    assert "ctx.company_id" in codigo_funcion
    assert "BRANCH_NOT_FOUND" in codigo_funcion

    funcion_patch = next(
        nodo for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef)
        and nodo.name == "patch_warehouse"
    )

    llamada_en_patch = False
    for nodo in ast.walk(funcion_patch):
        if not isinstance(nodo, ast.If):
            continue
        test = ast.unparse(nodo.test)
        if "branch_id" not in test or "model_fields_set" not in test:
            continue
        for hijo in ast.walk(nodo):
            if (
                isinstance(hijo, ast.Call)
                and isinstance(hijo.func, ast.Name)
                and hijo.func.id == "_exige_sucursal_propia"
            ):
                llamada_en_patch = True

    assert llamada_en_patch

    funcion_create = next(
        nodo for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef)
        and nodo.name == "create_warehouse_full"
    )

    create_llama = any(
        isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Name)
        and nodo.func.id == "_exige_sucursal_propia"
        for nodo in ast.walk(funcion_create)
    )
    assert create_llama

    nodo_if_patch = next(
        nodo for nodo in funcion_patch.body
        if isinstance(nodo, ast.If) and "model_fields_set" in ast.unparse(nodo.test)
    )
    nodo_for_patch = next(
        nodo for nodo in funcion_patch.body
        if isinstance(nodo, ast.For) and "model_dump" in ast.unparse(nodo.iter)
    )
    assert funcion_patch.body.index(nodo_if_patch) < funcion_patch.body.index(nodo_for_patch)


def test_b16_empresa_del_cuerpo_se_comprueba_antes_que_la_sucursal():
    r = CLIENT.post(
        "/api/v1/organization/warehouses",
        headers=_como("ua", EMPRESA_A),
        json={"company_id": EMPRESA_B, "code": "B-16", "name": "x", "branch_id": BRANCH_B},
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "COMPANY_NOT_FOUND"
    assert _cuenta_codigo("B-16") == 0


def test_b17_codigo_obligatorio_se_comprueba_antes_que_la_sucursal():
    r = CLIENT.post(
        "/api/v1/organization/warehouses",
        headers=_como("ua", EMPRESA_A),
        json={"company_id": EMPRESA_A, "name": "x", "branch_id": BRANCH_B},
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "WAREHOUSE_CODE_REQUIRED"
