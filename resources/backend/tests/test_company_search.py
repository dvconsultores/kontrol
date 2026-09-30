"""EMP-Q · La búsqueda general de Empresas busca de verdad (FR-001-065, FR-002-042 por analogía).

`GET /api/v1/organization/companies?q=…` llegaba desde la pantalla y el servidor
lo ignoraba: la misma lista con 200 para cualquier término. Los campos quedaron
decididos en `spec001-dead-search-analysis.md §6`: `code`, `legal_name`,
`trade_name`, `rif`, con la semántica del precedente vivo de terceros —contiene,
sin distinguir mayúsculas— y siempre dentro del tenant.

Dos tenants con la **misma** empresa `ALFA-OBJETIVO` en cada uno: lo único que
puede separarlas es el tenant. SQLite por defecto; PostgreSQL con
`KONTROL_TEST_DB_URL`.
"""
from __future__ import annotations

import uuid

import pytest
from conftest import make_engine
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db, init_models
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import UserRole, UserScope
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.setup.api import SetupRequest, _bootstrap_roles, initialize

PASSWORD = "Kontrol2026Segura!"
_FACTORY: sessionmaker | None = None
_CLIENT: TestClient | None = None
W: dict[str, str] = {}

#: Marcadores únicos por campo, con mayúsculas mezcladas a propósito.
MARCA = {
    "code": "CMP-Q-CODE-UNICO",
    "legal_name": "Comercial Horizonte Legal Q",
    "trade_name": "Marca Comercial Q Fantasia",
    "rif": "J-77712345-Q",
}


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
    # Una empresa por campo, cada una con un solo marcador; el resto es ruido único.
    for campo, valor in MARCA.items():
        W[f"por_{campo}"] = _empresa(db, str(t_a.id), **{campo: valor})
    # Nombre comercial nulo: la búsqueda por razón social debe encontrarla sin 500.
    W["sin_trade"] = _empresa(db, str(t_a.id), legal_name="Sin Nombre Comercial Q CA", trade_name=None)
    # La misma empresa en los dos tenants.
    W["alfa_a"] = _empresa(db, str(t_a.id), code="ALFA-OBJETIVO", legal_name="Alfa Objetivo CA", rif="J-10101010-1")
    W["alfa_b"] = _empresa(db, str(t_b.id), code="ALFA-OBJETIVO", legal_name="Alfa Objetivo CA", rif="J-10101010-1")
    W["e1"] = _empresa(db, str(t_b.id), code="E1", legal_name="Tercera Empresa CA")

    # Usuarios: `admin` (sin alcance declarado: todas las del tenant), `admin2` en B,
    # `solo_d1` limitado a D1.
    u_b = identity_service.create_user(db, tenant_id=str(t_b.id), username="admin2",
                                       email="admin2@q.test", password=PASSWORD, created_by=None)
    rol_b = _bootstrap_roles(db, str(t_b.id), str(u_b.id))
    db.add(UserRole(user_id=str(u_b.id), role_id=str(rol_b.id), company_id=None))
    u_d1 = identity_service.create_user(db, tenant_id=str(t_a.id), username="solo_d1",
                                        email="solo_d1@q.test", password=PASSWORD, created_by=None)
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
    r = _CLIENT.post("/api/v1/auth/login", json={"tenant_code": tenant, "username": user, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _buscar(h: dict, q: str | None = None, **params) -> list[dict]:
    if q is not None:
        params["q"] = q
    r = _CLIENT.get("/api/v1/organization/companies", headers=h, params=params)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list), "el listado de empresas es un array plano (EMPRESAS-SIN-SOBRE sigue abierta)"
    return body


def _ids(filas: list[dict]) -> list[str]:
    return [f["id"] for f in filas]


# --------------------------------------------------------------------------- #
# EMP-Q-01 / 02 · sin q nada cambia; un término inexistente devuelve vacío
# --------------------------------------------------------------------------- #
def test_emp_q_01_sin_q_y_con_q_vacia_el_listado_es_el_de_siempre():
    h = _login("DEMO", "admin")
    base = _buscar(h)
    assert len(base) == 7 and base[0]["id"] == W["d1"], "todas las del tenant, por fecha de alta"
    assert _ids(_buscar(h, "")) == _ids(base)
    assert _ids(_buscar(h, q=None)) == _ids(base)


def test_emp_q_02_un_termino_inexistente_devuelve_una_lista_vacia_con_200():
    assert _buscar(_login("DEMO", "admin"), "ZZZ-NO-EXISTE-EMPRESA-Q") == []


# --------------------------------------------------------------------------- #
# EMP-Q-03..06 · cada uno de los cuatro campos, y solo esos
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("campo", list(MARCA))
def test_emp_q_03_a_06_cada_campo_decidido_encuentra_solo_su_empresa(campo: str):
    filas = _buscar(_login("DEMO", "admin"), MARCA[campo])
    assert _ids(filas) == [W[f"por_{campo}"]], f"buscar por {campo} debe dar exactamente esa empresa"


def test_emp_q_campos_no_decididos_no_se_buscan():
    """`status`, `functional_currency`, `id`: fuera, como en terceros."""
    h = _login("DEMO", "admin")
    assert _buscar(h, "ACTIVE") == []
    assert _buscar(h, "VED") == []
    assert _buscar(h, W["d1"]) == []


# --------------------------------------------------------------------------- #
# EMP-Q-07 / 08 · semántica del precedente: contiene, sin distinguir mayúsculas
# --------------------------------------------------------------------------- #
def test_emp_q_07_no_distingue_mayusculas():
    h = _login("DEMO", "admin")
    assert _ids(_buscar(h, "horizonte")) == [W["por_legal_name"]]
    assert _ids(_buscar(h, "HORIZONTE")) == [W["por_legal_name"]]
    assert _ids(_buscar(h, "cmp-q-code")) == [W["por_code"]]


def test_emp_q_08_encuentra_un_fragmento_interior():
    h = _login("DEMO", "admin")
    assert _ids(_buscar(h, "Horizonte Legal")) == [W["por_legal_name"]]
    assert _ids(_buscar(h, "7771234")) == [W["por_rif"]]
    assert _ids(_buscar(h, "Marca Comercial")) == [W["por_trade_name"]]


# --------------------------------------------------------------------------- #
# EMP-Q-09 · nombre comercial nulo
# --------------------------------------------------------------------------- #
def test_emp_q_09_un_nombre_comercial_nulo_ni_rompe_ni_se_busca_como_texto():
    h = _login("DEMO", "admin")
    assert _ids(_buscar(h, "Sin Nombre Comercial")) == [W["sin_trade"]]
    assert _buscar(h, "None") == []


# --------------------------------------------------------------------------- #
# EMP-Q-10 / 11 · aislamiento: tenant AND búsqueda; alcance AND búsqueda
# --------------------------------------------------------------------------- #
def test_emp_q_10_la_misma_empresa_en_dos_tenants_solo_aparece_en_el_suyo():
    assert _ids(_buscar(_login("DEMO", "admin"), "ALFA-OBJETIVO")) == [W["alfa_a"]]
    assert _ids(_buscar(_login("DEMO2", "admin2"), "ALFA-OBJETIVO")) == [W["alfa_b"]]
    assert _ids(_buscar(_login("DEMO2", "admin2"), "alfa objetivo")) == [W["alfa_b"]]
    # Ni el término ni la consulta amplían el tenant.
    forzado = _buscar(_login("DEMO", "admin"), "ALFA-OBJETIVO", tenant_id=W["tenant_b"])
    assert _ids(forzado) == [W["alfa_a"]]


def test_emp_q_11_la_busqueda_actua_dentro_del_alcance_del_usuario_no_lo_sustituye():
    """`solo_d1` opera en D1: buscar una empresa del tenant fuera de su alcance da vacío."""
    h = _login("DEMO", "solo_d1")
    assert _ids(_buscar(h)) == [W["d1"]]
    assert _buscar(h, MARCA["code"]) == []
    assert _ids(_buscar(h, "Demo")) == [W["d1"]]


# --------------------------------------------------------------------------- #
# EMP-Q-12 / 13 / 14 · el conjunto completo, en el orden de siempre
# --------------------------------------------------------------------------- #
def test_emp_q_12_13_el_resultado_es_el_conjunto_filtrado_entero():
    """Este listado no pagina (`EMPRESAS-SIN-SOBRE`): lo que se devuelve es
    exactamente el conjunto que coincide, sin recorte previo ni posterior."""
    db = _FACTORY()
    try:
        lote = [_empresa(db, W["tenant_a"], legal_name=f"Lote Q {i:02d} CA") for i in range(15)]
        db.commit()
    finally:
        db.close()
    filas = _buscar(_login("DEMO", "admin"), "Lote Q")
    assert len(filas) == 15 and sorted(_ids(filas)) == sorted(lote)
    assert len(_buscar(_login("DEMO", "admin"), "Lote Q 0")) == 10


def test_emp_q_14_la_busqueda_conserva_el_orden_por_fecha_de_alta():
    h = _login("DEMO", "admin")
    orden_base = [f["id"] for f in _buscar(h) if f["legal_name"].startswith("Lote Q")]
    assert [f["id"] for f in _buscar(h, "Lote Q")] == orden_base


# --------------------------------------------------------------------------- #
# EMP-Q-15 / 16 · contrato publicado y frontera con los parámetros no declarados
# --------------------------------------------------------------------------- #
def test_emp_q_15_openapi_declara_q_opcional_y_ninguna_autoridad_nueva():
    op = _CLIENT.app.openapi()["paths"]["/api/v1/organization/companies"]["get"]
    params = {p["name"]: p for p in op.get("parameters", [])}
    assert set(params) == {"q"}
    assert params["q"]["in"] == "query" and params["q"].get("required", False) is False
    assert params["q"]["schema"].get("type") == "string"
    assert "tenant_id" not in params and "company_id" not in params


def test_emp_q_16_un_parametro_desconocido_se_sigue_ignorando_como_antes():
    """`API-QUERY-SILENCIOSA` sigue abierta: declarar `q` no convierte al endpoint en estricto."""
    h = _login("DEMO", "admin")
    base = _ids(_buscar(h))
    r = _CLIENT.get("/api/v1/organization/companies", headers=h, params={"__kontrol_unknown_query_probe__": "1"})
    assert r.status_code == 200 and _ids(r.json()) == base
    r = _CLIENT.get("/api/v1/organization/companies", headers=h,
                    params={"q": "ALFA-OBJETIVO", "__kontrol_unknown_query_probe__": "1"})
    assert r.status_code == 200 and _ids(r.json()) == [W["alfa_a"]]


# --------------------------------------------------------------------------- #
# EMP-Q-17 · la identidad de `Company.code` no cambia
# --------------------------------------------------------------------------- #
def test_emp_q_17_dos_empresas_con_el_mismo_codigo_siguen_conviviendo_y_ambas_se_encuentran():
    """`SEED-EMPRESA-CODIGO-NO-UNICO` sigue `MATERIAL_DECISION_REQUIRED`: buscar por
    código no lo convierte en identidad."""
    db = _FACTORY()
    try:
        dup = _empresa(db, W["tenant_a"], code="ALFA-OBJETIVO", legal_name="Alfa Duplicada CA")
        db.commit()
        unicos = {tuple(u["column_names"]) for u in inspect(db.get_bind()).get_unique_constraints("companies")}
        indices = {tuple(i["column_names"]) for i in inspect(db.get_bind()).get_indexes("companies") if i.get("unique")}
    finally:
        db.close()
    assert ("tenant_id", "code") not in unicos | indices
    assert sorted(_ids(_buscar(_login("DEMO", "admin"), "ALFA-OBJETIVO"))) == sorted([W["alfa_a"], dup])
