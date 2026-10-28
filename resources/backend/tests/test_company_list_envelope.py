"""LIST · El listado de empresas responde el sobre del contrato (EMPRESAS-SIN-SOBRE).

`GET /api/v1/organization/companies` devolvía un array plano sin `total` ni
`page`, contra el contrato de listados de `api-contracts.md` («listados con
`q`, `page`, `page_size`») que los otros dieciséis listados ya cumplen con
`{items, total, page, page_size}`. Aquí se fija ese sobre: `total` cuenta el
mismo conjunto que `items` —tenant, alcance del usuario y `q`— antes de cortar
la página; la página empieza en 1, `page_size` es 20 por defecto y 100 como
máximo; fuera de rango responde 422; más allá del final, 200 con `items` vacío.

Dos tenants, un usuario limitado a una empresa y lotes suficientes para pasar
de una página. SQLite por defecto; PostgreSQL con `KONTROL_TEST_DB_URL`.
"""
from __future__ import annotations

import uuid

import pytest
from conftest import make_engine
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db, init_models
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import UserRole, UserScope
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.setup.api import SetupRequest, _bootstrap_roles, initialize

PASSWORD = "Kontrol2026Segura!"
SOBRE = {"items", "total", "page", "page_size"}
_FACTORY: sessionmaker | None = None
_CLIENT: TestClient | None = None
W: dict[str, str] = {}


def _empresa(db: Session, tenant_id: str, **campos) -> str:
    base = dict(code=f"C-{uuid.uuid4().hex[:6]}", legal_name=f"Empresa {uuid.uuid4().hex[:6]} CA",
                trade_name=None, rif=f"J-{uuid.uuid4().hex[:8]}", legal_type="JURIDICA",
                functional_currency="VED", status="ACTIVE")
    base.update(campos)
    c = Company(tenant_id=tenant_id, **base)
    db.add(c)
    db.flush()
    return str(c.id)


@pytest.fixture(scope="module", autouse=True)
def _mundo():
    global _FACTORY, _CLIENT
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    import app.core.database as dm

    dm._engine = engine  # type: ignore[attr-defined]
    dm._SessionLocal = factory  # type: ignore[attr-defined]

    db = factory()
    initialize(db, SetupRequest(
        tenant_code="DEMO", tenant_name="Tenant A", company_code="D1",
        company_legal_name="Demo C.A.", company_rif="J-12345678-9",
        admin_username="admin", admin_password=PASSWORD))
    t_a = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().one()
    d1 = db.execute(select(Company).where(Company.tenant_id == str(t_a.id))).scalars().one()
    inst = db.execute(select(Installation).limit(1)).scalars().first()
    t_b = Tenant(installation_id=str(inst.id), code="DEMO2", name="Tenant B", plan="MONO_COMPANY", status="ACTIVE")
    db.add(t_b)
    db.flush()
    W.update(tenant_a=str(t_a.id), tenant_b=str(t_b.id), d1=str(d1.id))
    # 25 empresas del tenant A con marcador común (pasan de la página por defecto)
    # y 3 más con otro marcador; la misma ALFA en los dos tenants.
    W["lote"] = ",".join(_empresa(db, str(t_a.id), legal_name=f"Lote Sobre {i:02d} CA") for i in range(25))
    W["otras"] = ",".join(_empresa(db, str(t_a.id), legal_name=f"Otra Sobre {i} CA") for i in range(3))
    W["alfa_a"] = _empresa(db, str(t_a.id), code="ALFA-OBJETIVO", legal_name="Alfa Objetivo CA")
    W["alfa_b"] = _empresa(db, str(t_b.id), code="ALFA-OBJETIVO", legal_name="Alfa Objetivo CA")
    for i in range(30):
        _empresa(db, str(t_b.id), legal_name=f"Lote Sobre B {i:02d} CA")

    u_b = identity_service.create_user(db, tenant_id=str(t_b.id), username="admin2",
                                       email="admin2@sobre.test", password=PASSWORD, created_by=None)
    rol_b = _bootstrap_roles(db, str(t_b.id), str(u_b.id))
    db.add(UserRole(user_id=str(u_b.id), role_id=str(rol_b.id), company_id=None))
    u_d1 = identity_service.create_user(db, tenant_id=str(t_a.id), username="solo_d1",
                                        email="solo_d1@sobre.test", password=PASSWORD, created_by=None)
    rol_a = _bootstrap_roles(db, str(t_a.id), str(u_d1.id))
    db.add(UserRole(user_id=str(u_d1.id), role_id=str(rol_a.id), company_id=None))
    db.add(UserScope(user_id=str(u_d1.id), company_id=str(d1.id)))
    db.commit()
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
    _FACTORY, _CLIENT = factory, TestClient(app)
    yield


def _login(tenant: str, user: str) -> dict:
    r = login_completo(_CLIENT, "/api/v1/auth/login", json={"tenant_code": tenant, "username": user, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _get(h: dict, **params):
    return _CLIENT.get("/api/v1/organization/companies", headers=h, params=params)


def _sobre(h: dict, **params) -> dict:
    r = _get(h, **params)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, dict) and set(body) == SOBRE, f"no es el sobre del contrato: {body if not isinstance(body, dict) else set(body)}"
    return body


def _ids(body: dict) -> list[str]:
    return [i["id"] for i in body["items"]]


def _orden_contractual(ids: list[str]) -> list[str]:
    """Fecha de alta y, a igual fecha (una siembra en una transacción las deja
    iguales), el identificador: el desempate que hace determinista la página."""
    db = _FACTORY()
    try:
        filas = db.execute(select(Company.id, Company.created_at).where(Company.id.in_(ids))).all()
    finally:
        db.close()
    return [str(i) for i, _ in sorted(filas, key=lambda f: (f[1], str(f[0])))]


# --------------------------------------------------------------------------- #
# LIST-01 / 02 · forma y tipos
# --------------------------------------------------------------------------- #
def test_list_01_la_respuesta_es_el_sobre_del_contrato_y_no_un_array():
    body = _sobre(_login("DEMO", "admin"))
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int) and isinstance(body["page"], int) and isinstance(body["page_size"], int)


def test_list_02_los_items_son_empresas_completas():
    body = _sobre(_login("DEMO", "admin"))
    assert body["items"], "el tenant tiene empresas"
    assert set(body["items"][0]) == {"id", "code", "legal_name", "trade_name", "rif", "status",
                                     "functional_currency", "allowed_actions"}


# --------------------------------------------------------------------------- #
# LIST-03 / 04 · total y paginación por defecto
# --------------------------------------------------------------------------- #
def test_list_03_04_por_defecto_pagina_1_de_20_y_total_cuenta_todo_el_conjunto():
    body = _sobre(_login("DEMO", "admin"))
    assert (body["page"], body["page_size"]) == (1, 20)
    assert body["total"] == 30            # D1 + 25 lote + 3 otras + ALFA
    assert len(body["items"]) == 20


# --------------------------------------------------------------------------- #
# LIST-05 / 06 / 07 · segunda página, página vacía, orden estable
# --------------------------------------------------------------------------- #
def test_list_05_la_segunda_pagina_completa_el_conjunto_sin_duplicados_ni_ausencias():
    h = _login("DEMO", "admin")
    p1, p2 = _sobre(h, page=1, page_size=20), _sobre(h, page=2, page_size=20)
    assert p1["total"] == p2["total"] == 30
    assert len(p1["items"]) == 20 and len(p2["items"]) == 10
    todos = _ids(p1) + _ids(p2)
    assert len(todos) == len(set(todos)) == 30
    assert todos == _orden_contractual(todos), "fecha de alta y, a igual fecha, id"


def test_list_06_una_pagina_mas_alla_del_final_responde_200_vacia_con_el_total():
    body = _sobre(_login("DEMO", "admin"), page=99)
    assert body["items"] == [] and body["total"] == 30 and body["page"] == 99


def test_list_07_el_orden_es_estable_entre_llamadas_y_tamanos():
    h = _login("DEMO", "admin")
    de_10 = _ids(_sobre(h, page=1, page_size=10)) + _ids(_sobre(h, page=2, page_size=10)) + _ids(_sobre(h, page=3, page_size=10))
    de_100 = _ids(_sobre(h, page=1, page_size=100))
    assert de_10 == de_100 and len(de_100) == 30


# --------------------------------------------------------------------------- #
# LIST-08 · parámetros fuera de contrato: 422, como el precedente de terceros
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("params", [{"page": 0}, {"page": -1}, {"page_size": 0}, {"page_size": 101}, {"page": "x"}])
def test_list_08_paginacion_invalida_responde_422(params):
    r = _get(_login("DEMO", "admin"), **params)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "VALIDATION_ERROR"


# --------------------------------------------------------------------------- #
# LIST-09 / 10 / 11 · q + paginación, q + alcance, q + tenant
# --------------------------------------------------------------------------- #
def test_list_09_q_se_aplica_antes_de_contar_y_de_paginar():
    h = _login("DEMO", "admin")
    p1 = _sobre(h, q="Lote Sobre", page=1, page_size=10)
    p2 = _sobre(h, q="Lote Sobre", page=2, page_size=10)
    p3 = _sobre(h, q="Lote Sobre", page=3, page_size=10)
    assert p1["total"] == p2["total"] == p3["total"] == 25
    assert [len(p["items"]) for p in (p1, p2, p3)] == [10, 10, 5]
    vistos = _ids(p1) + _ids(p2) + _ids(p3)
    assert sorted(vistos) == sorted(W["lote"].split(","))
    assert _sobre(h, q="Lote Sobre", page=4, page_size=10)["items"] == []


def test_list_10_el_total_es_el_del_alcance_del_usuario_no_el_del_tenant():
    h = _login("DEMO", "solo_d1")
    body = _sobre(h)
    assert body["total"] == 1 and _ids(body) == [W["d1"]]
    con_q = _sobre(h, q="Lote Sobre")
    assert con_q["total"] == 0 and con_q["items"] == []
    assert _sobre(h, q="Demo")["total"] == 1


def test_list_11_el_total_nunca_cuenta_empresas_de_otro_tenant():
    a = _sobre(_login("DEMO", "admin"), q="ALFA-OBJETIVO")
    b = _sobre(_login("DEMO2", "admin2"), q="ALFA-OBJETIVO")
    assert (a["total"], _ids(a)) == (1, [W["alfa_a"]])
    assert (b["total"], _ids(b)) == (1, [W["alfa_b"]])
    assert _sobre(_login("DEMO2", "admin2"))["total"] == 31   # ALFA + 30 lote B
    # ni la consulta amplía el conjunto: `tenant_id` no está declarado y se rechaza (FR-001-268)
    forzado = _get(_login("DEMO", "admin"), tenant_id=W["tenant_b"], page_size=100)
    assert forzado.status_code == 422, forzado.text
    assert forzado.json()["details"] == {"unknown_query_parameters": ["tenant_id"]}


# --------------------------------------------------------------------------- #
# LIST-12 · contrato publicado
# --------------------------------------------------------------------------- #
def test_list_12_openapi_declara_q_page_y_page_size_y_nada_mas():
    op = _CLIENT.app.openapi()["paths"]["/api/v1/organization/companies"]["get"]
    params = {p["name"]: p for p in op.get("parameters", [])}
    assert set(params) == {"q", "page", "page_size"}
    assert all(p.get("required", False) is False for p in params.values())
    assert params["page"]["schema"].get("minimum") == 1
    assert params["page_size"]["schema"].get("maximum") == 100 and params["page_size"]["schema"].get("default") == 20
