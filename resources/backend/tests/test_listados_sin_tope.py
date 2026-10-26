"""LT · Los listados tienen tope y las listas de preparación se paginan (LISTADOS-SIN-TOPE; dueñas Spec 008 y Spec 031;
contrato de listados de la Spec 001: `{items, total, page, page_size}`, `page` ≥ 1, `page_size` 1..100, 422 fuera de rango).

`GET /organization/warehouses` aceptaba cualquier `limit` (100 000 traía la empresa entera; -1 era un 500 en PostgreSQL).
`GET /sales/pick-lists` devolvía la colección entera con un sobre que solo parecía paginado. Aquí, con 1 100 listas y
7 almacenes en D1 y otra empresa C2 al lado: tope, validación, sobre exacto, `total` dentro de la empresa y del filtro
antes de cortar, páginas sin solapes, orden determinista con desempate, aislamiento de empresa y los dos invariantes
estáticos que impiden volver a cortar en Python. SQLite o PostgreSQL.
"""
from __future__ import annotations

import inspect
import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy import event, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.company_context import COMPANY_HEADER
from app.core.database import Base, get_db, init_models
from app.modules.master_data.models import Party
from app.modules.organization.models import Company, Installation, Tenant, Warehouse
from app.modules.sales import api as sales_api
from app.modules.sales.models import PickList, SalesOrder
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine
from tests.test_system_access import PASSWORD, _usuario

PG = os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql")
API = "/api/v1"
LISTAS = 1100
ALMACENES = 7
_CLIENT: TestClient
_FACTORY: sessionmaker
_D1: str
_C2: str
_ESPERADO: list[str]  # ids de las listas de D1 en el orden del contrato: created_at desc, id asc
_SQL: list[str] = []


@pytest.fixture(scope="module", autouse=True)
def _mundo() -> Iterator[None]:
    """DEMO/D1 con 1 100 listas (cinco grupos de diez comparten instante) y 7 almacenes; T2/C2 con 50 listas y 1 almacén."""
    global _CLIENT, _FACTORY, _D1, _C2, _ESPERADO
    import app.core.database as dm

    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    event.listen(engine, "before_cursor_execute", lambda conn, cur, stmt, *_: _SQL.append(stmt))
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    dm._engine, dm._SessionLocal = engine, factory  # type: ignore[attr-defined]
    base = datetime(2026, 1, 1, tzinfo=UTC)
    with factory() as db:
        initialize(db, SetupRequest(tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1", company_legal_name="Demo C.A.",
                                    company_rif="J-12345678-9", admin_username="admin", admin_password=PASSWORD))
        tenant = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().one()
        d1 = db.execute(select(Company).where(Company.tenant_id == tenant.id)).scalars().one()
        _D1 = str(d1.id)
        inst = db.execute(select(Installation)).scalars().first()
        t2 = Tenant(installation_id=str(inst.id), code="T2", name="Tenant Dos")
        db.add(t2)
        db.flush()
        c2 = Company(tenant_id=str(t2.id), code="C2", legal_name="Otra C.A.", rif="J-99999999-9")
        db.add(c2)
        db.flush()
        _C2 = str(c2.id)
        _usuario(db, str(t2.id), _C2, "adminc", sin=set())
        almacenes = [Warehouse(company_id=_D1, code=f"W{i}", name=f"Almacén {i}", status="ACTIVE") for i in range(ALMACENES)]
        ajeno = Warehouse(company_id=_C2, code="WX", name="Ajeno", status="ACTIVE")
        db.add_all([*almacenes, ajeno])
        cliente = Party(company_id=_D1, code="CLI-1", name="Cliente sintético")
        cliente2 = Party(company_id=_C2, code="CLI-2", name="Cliente ajeno")
        db.add_all([cliente, cliente2])
        db.flush()
        pedidos = [SalesOrder(company_id=_D1, code=f"SO-{i:05d}", customer_id=str(cliente.id)) for i in range(LISTAS)]
        pedidos2 = [SalesOrder(company_id=_C2, code=f"SO2-{i:05d}", customer_id=str(cliente2.id)) for i in range(50)]
        db.add_all([*pedidos, *pedidos2])
        db.flush()
        # Las cincuenta primeras comparten instante de diez en diez: ahí se ve el desempate.
        listas = [PickList(company_id=_D1, code=f"PK-{i:05d}", order_id=str(pedidos[i].id), warehouse_id=str(almacenes[i % ALMACENES].id),
                           status="DRAFT", created_at=base + timedelta(seconds=(i // 10 if i < 50 else i))) for i in range(LISTAS)]
        db.add_all(listas)
        db.add_all([PickList(company_id=_C2, code=f"PK2-{i:05d}", order_id=str(o.id), warehouse_id=str(ajeno.id), status="DRAFT")
                    for i, o in enumerate(pedidos2)])
        db.commit()
        _ESPERADO = [str(p.id) for p in sorted(listas, key=lambda p: (-p.created_at.timestamp(), str(p.id)))]
    from app.main import create_app

    app = create_app()

    def _db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _db
    _CLIENT, _FACTORY = TestClient(app, raise_server_exceptions=False), factory
    yield


def _sesion(usuario: str = "admin", tenant: str = "DEMO", empresa: str | None = None) -> dict[str, str]:
    r = login_completo(_CLIENT, f"{API}/auth/login", json={"tenant_code": tenant, "username": usuario, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}", COMPANY_HEADER: empresa or _D1}


def _almacenes(consulta: str, h: dict[str, str] | None = None):
    return _CLIENT.get(f"{API}/organization/warehouses?{consulta}", headers=h or _sesion())


def _listas(consulta: str = "", h: dict[str, str] | None = None):
    return _CLIENT.get(f"{API}/sales/pick-lists" + (f"?{consulta}" if consulta else ""), headers=h or _sesion())


# ---------------------------------------------------------------- LT-01..03 · almacenes: tope, validación, defecto y desplazamiento
def test_lt_01_el_maximo_del_contrato_se_acepta_y_el_defecto_sigue_siendo_50():
    r = _almacenes("limit=100")
    assert r.status_code == 200 and r.json()["limit"] == 100 and r.json()["total"] == ALMACENES and len(r.json()["items"]) == ALMACENES
    por_defecto = _almacenes("").json()
    assert (por_defecto["limit"], por_defecto["offset"], por_defecto["total"]) == (50, 0, ALMACENES)
    assert set(por_defecto) == {"total", "limit", "offset", "items"}


@pytest.mark.parametrize("consulta", ["limit=101", "limit=100000", "limit=0", "limit=-1", "limit=abc", "offset=-1", "offset=x"])
def test_lt_02_03_fuera_de_contrato_es_422_y_nunca_500(consulta):
    r = _almacenes(consulta)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "VALIDATION_ERROR"


def test_lt_03b_offset_mas_alla_del_final_es_una_pagina_vacia_con_el_mismo_total():
    cuerpo = _almacenes("offset=100000").json()
    assert cuerpo["items"] == [] and cuerpo["total"] == ALMACENES and cuerpo["offset"] == 100000
    paginas = [_almacenes(f"limit=3&offset={o}").json()["items"] for o in (0, 3, 6)]
    assert [len(p) for p in paginas] == [3, 3, 1]
    assert [w["code"] for p in paginas for w in p] == [f"W{i}" for i in range(ALMACENES)]


# ---------------------------------------------------------------- LT-04..10 · pick-lists: sobre, páginas, bordes
def test_lt_04_05_el_sobre_es_el_del_contrato_y_la_primera_pagina_trae_20_de_1100():
    cuerpo = _listas().json()
    assert set(cuerpo) == {"items", "total", "page", "page_size"}
    assert (cuerpo["total"], cuerpo["page"], cuerpo["page_size"], len(cuerpo["items"])) == (LISTAS, 1, 20, 20)
    assert set(cuerpo["items"][0]) == {"id", "code", "order_id", "warehouse_id", "status"}


def test_lt_06_07_las_paginas_no_se_solapan_y_la_ultima_es_parcial():
    vistos: list[str] = []
    for page in range(1, 13):
        cuerpo = _listas(f"page={page}&page_size=100").json()
        assert cuerpo["total"] == LISTAS and cuerpo["page"] == page and cuerpo["page_size"] == 100
        vistos += [p["id"] for p in cuerpo["items"]]
    assert len(vistos) == LISTAS and len(set(vistos)) == LISTAS
    assert len(_listas("page=11&page_size=100").json()["items"]) == 100
    assert _listas("page=12&page_size=100").json()["items"] == []
    assert len(_listas("page=55&page_size=20").json()["items"]) == 20 and len(_listas("page=56&page_size=20").json()["items"]) == 0
    assert len(_listas("page=12&page_size=99").json()["items"]) == LISTAS - 11 * 99


def test_lt_08_mas_alla_del_final_viene_vacia_con_el_mismo_total():
    cuerpo = _listas("page=999&page_size=100").json()
    assert cuerpo == {"items": [], "total": LISTAS, "page": 999, "page_size": 100}


def test_lt_09_el_maximo_se_acepta():
    assert len(_listas("page_size=100").json()["items"]) == 100


@pytest.mark.parametrize("consulta", ["page_size=101", "page_size=0", "page_size=-5", "page_size=abc", "page=0", "page=-1", "page=abc"])
def test_lt_10_fuera_de_rango_es_422(consulta):
    r = _listas(consulta)
    assert r.status_code == 422 and r.json()["code"] == "VALIDATION_ERROR", r.text


# ---------------------------------------------------------------- LT-11 · orden determinista con desempate
def test_lt_11_el_orden_es_el_del_contrato_mas_reciente_primero_e_id_como_desempate_y_se_repite():
    paginas = [[p["id"] for p in _listas(f"page={page}&page_size=100").json()["items"]] for page in range(1, 13)]
    assert [i for pagina in paginas for i in pagina] == _ESPERADO
    assert [p["id"] for p in _listas("page=1&page_size=100").json()["items"]] == paginas[0]
    # Las cincuenta de instante compartido quedan al final (son las más antiguas) y, dentro de cada grupo, por id.
    cola = [p["id"] for p in _listas("page=11&page_size=100").json()["items"]][-50:]
    assert cola == _ESPERADO[-50:]
    with _FACTORY() as db:
        empates = db.execute(select(PickList.created_at, PickList.id).where(PickList.id.in_(cola))).all()
    por_instante: dict[datetime, list[str]] = {}
    for instante, ident in empates:
        por_instante.setdefault(instante, []).append(ident)
    assert len(por_instante) == 5 and all(len(ids) == 10 for ids in por_instante.values())
    for ids in por_instante.values():
        assert [i for i in cola if i in ids] == sorted(ids)


# ---------------------------------------------------------------- LT-12..15 · empresa, empresa ajena y filtro
def test_lt_12_13_items_y_total_son_solo_de_la_empresa_en_la_que_se_opera():
    d1 = _listas("page_size=100").json()
    c2 = _listas("page_size=100", _sesion("adminc", "T2", _C2)).json()
    assert d1["total"] == LISTAS and c2["total"] == 50 and len(c2["items"]) == 50
    assert all(p["code"].startswith("PK-") for p in d1["items"]) and all(p["code"].startswith("PK2-") for p in c2["items"])
    assert _almacenes("limit=100", _sesion("adminc", "T2", _C2)).json()["total"] == 1


def test_lt_14_una_empresa_ajena_en_la_cabecera_no_revela_nada():
    for r in (_listas("page_size=100", _sesion(empresa=_C2)), _almacenes("limit=100", _sesion(empresa=_C2))):
        assert r.status_code == 404 and r.json()["code"] == "COMPANY_NOT_FOUND", r.text
        assert "items" not in r.text and "total" not in r.text


def test_lt_15_el_total_refleja_el_filtro_antes_de_cortar():
    with _FACTORY() as db:
        pedido = db.execute(select(PickList.order_id).where(PickList.company_id == _D1)).scalars().first()
    cuerpo = _listas(f"order_id={pedido}&page_size=5").json()
    assert cuerpo["total"] == 1 and len(cuerpo["items"]) == 1 and cuerpo["items"][0]["order_id"] == pedido
    assert _listas("order_id=no-existe").json() == {"items": [], "total": 0, "page": 1, "page_size": 20}


# ---------------------------------------------------------------- LT-23/24 · dataset grande y lo que viaja
def test_lt_23_24_con_mas_de_mil_listas_la_respuesta_es_una_pagina_y_el_cuerpo_es_pequeno():
    r = _listas()
    assert r.json()["total"] > 1000 and len(r.json()["items"]) == 20
    assert len(r.content) < 6_000  # la colección entera pesaba 203 550 bytes (evidencia); una página de 20, menos de 6 KB
    assert len(_listas("page_size=100").content) < 25_000


# ---------------------------------------------------------------- invariantes: el corte lo hace la base, no Python
def test_lt_sql_el_corte_viaja_en_la_sentencia_y_no_se_rebana_en_python():
    _SQL.clear()
    _listas("page=3&page_size=7")
    sentencias = [s for s in _SQL if "FROM pick_lists" in s and "count" not in s.lower()]
    assert sentencias and all("LIMIT" in s.upper() and "OFFSET" in s.upper() for s in sentencias), sentencias
    assert any("count" in s.lower() and "pick_lists" in s for s in _SQL)
    fuente = inspect.getsource(sales_api.list_pick_lists)
    assert ".offset(" in fuente and ".limit(" in fuente and "func.count()" in fuente
    assert "items[" not in fuente and "[:" not in fuente and "len(items)" not in fuente
