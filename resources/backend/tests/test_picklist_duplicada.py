"""PL · Un pedido no tiene dos planes de picking vivos (PICKLIST-DUPLICADA-500; Spec 031 post-D0-15: «un solo plan
activo por pedido», índice parcial `uq_pick_lists_active_order` sobre `(order_id) WHERE status IN ('DRAFT','CONFIRMED')`).

`POST /sales/pick-lists` sobre un pedido con un plan `DRAFT` o `CONFIRMED` responde 409 `PICKLIST_DUPLICATE` con el
plan vigente en `details`; no persiste plan ni líneas; no toca el pedido ni el plan existente; sesión, permiso y alcance
de empresa se resuelven antes (401/403/404, nunca 409 para un pedido ajeno); bajo concurrencia en PostgreSQL entra
exactamente uno y el resto recibe el mismo 409 (el índice sigue siendo el respaldo final, traducido solo cuando es
**esa** violación); un plan terminal (CLOSED/CANCELLED/INVALIDATED) libera el pedido. SQLite o PostgreSQL.
"""
from __future__ import annotations

import os
import threading
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.company_context import COMPANY_HEADER
from app.core.database import Base, get_db, init_models
from app.core.errors import ConflictError
from app.modules.audit.models import AuditEvent
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.sales import service as sales_service
from app.modules.sales.models import PickList, PickListLine, SalesOrder
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine
from tests.test_system_access import PASSWORD, _usuario

PG = os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql")
API = "/api/v1"
_CLIENT: TestClient
_FACTORY: sessionmaker
_D1: str
_C2: str


@pytest.fixture(scope="module", autouse=True)
def _mundo() -> Iterator[None]:
    """DEMO/D1 (admin; `operador` sin `ventas:create`) y un segundo tenant T2/C2 con `adminc`."""
    global _CLIENT, _FACTORY, _D1, _C2
    import app.core.database as dm

    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    dm._engine, dm._SessionLocal = engine, factory  # type: ignore[attr-defined]
    with factory() as db:
        initialize(db, SetupRequest(tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1", company_legal_name="Demo C.A.",
                                    company_rif="J-12345678-9", admin_username="admin", admin_password=PASSWORD))
        tenant = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().one()
        empresa = db.execute(select(Company).where(Company.tenant_id == tenant.id)).scalars().one()
        _D1 = str(empresa.id)
        _usuario(db, str(tenant.id), _D1, "operador", sin={"ventas:create"})
        inst = db.execute(select(Installation)).scalars().first()
        t2 = Tenant(installation_id=str(inst.id), code="T2", name="Tenant Dos")
        db.add(t2)
        db.flush()
        c2 = Company(tenant_id=str(t2.id), code="C2", legal_name="Otra C.A.", rif="J-99999999-9")
        db.add(c2)
        db.flush()
        _C2 = str(c2.id)
        _usuario(db, str(t2.id), _C2, "adminc", sin=set())
        db.commit()
    from app.main import create_app

    app = create_app()

    def _db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _db
    # Como el servidor real: un error no controlado es un 500, no una excepción en la prueba.
    _CLIENT, _FACTORY = TestClient(app, raise_server_exceptions=False), factory
    yield


def _sesion(usuario: str = "admin", tenant: str = "DEMO", empresa: str | None = None) -> dict[str, str]:
    r = _CLIENT.post(f"{API}/auth/login", json={"tenant_code": tenant, "username": usuario, "password": PASSWORD})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}", COMPANY_HEADER: empresa or _D1}
    return h


def _crear(ruta: str, cuerpo: dict, h: dict[str, str]) -> str:
    r = _CLIENT.post(f"{API}{ruta}", json=cuerpo, headers=h)
    assert r.status_code in (200, 201), f"{ruta}: {r.status_code} {r.text}"
    return r.json()["id"]


_N = 0


def _marca() -> str:
    global _N
    _N += 1
    return f"{_N:03d}"


def _pedido_liberado(h: dict[str, str], empresa: str) -> tuple[str, str]:
    """Un pedido en la cola de preparación (RELEASED) y el almacén de su empresa, por la API."""
    m = _marca()
    almacen = _crear("/organization/warehouses", {"company_id": empresa, "branch_id": None, "code": f"ALM-{m}", "name": f"Almacén {m}"}, h)
    cliente = _crear("/maestros/terceros", {"code": f"CLI-{m}", "name": f"Cliente {m}", "roles": ["CLIENTE"]}, h)
    producto = _crear("/maestros/catalogos/items", {"code": f"PRD-{m}", "name": f"Producto {m}", "item_type": "PRODUCT"}, h)
    pedido = _crear("/sales/orders", {"code": f"OV-{m}", "customer_id": cliente, "warehouse_id": almacen, "currency": "VED"}, h)
    r = _CLIENT.post(f"{API}/sales/orders/{pedido}/lines", json={"product_id": producto, "quantity": 1, "unit_price": 10, "needs_inventory": False}, headers=h)
    assert r.status_code == 200, r.text
    r = _CLIENT.post(f"{API}/sales/orders/{pedido}/submit", json={}, headers=h)
    assert r.status_code == 200, r.text
    assert _CLIENT.get(f"{API}/sales/orders/{pedido}", headers=h).json()["status"] == "RELEASED"
    return pedido, almacen


def _plan(h: dict[str, str], pedido: str, almacen: str, lines: list[dict] | None = None):
    return _CLIENT.post(f"{API}/sales/pick-lists", json={"code": f"PL-{_marca()}", "order_id": pedido, "warehouse_id": almacen, "lines": lines}, headers=h)


def _planes_de(pedido: str) -> list[PickList]:
    with _FACTORY() as db:
        return list(db.execute(select(PickList).where(PickList.order_id == pedido)).scalars().all())


def _pedido(pedido: str) -> tuple[str, object]:
    with _FACTORY() as db:
        o = db.get(SalesOrder, pedido)
        return o.status, o.updated_at


def _auditorias() -> int:
    with _FACTORY() as db:
        return db.execute(select(func.count()).select_from(AuditEvent)).scalar_one()


# ----------------------------------------------------------------------------- PL-01/02/03/04/05/06/07/16/17
def test_pl_01_02_03_el_segundo_plan_vivo_es_un_409_de_dominio_y_no_deja_rastro():
    h = _sesion()
    pedido, almacen = _pedido_liberado(h, _D1)
    primero = _plan(h, pedido, almacen)
    assert primero.status_code == 200, primero.text  # contrato vigente del alta: 200
    plan_id = primero.json()["id"]
    estado_pedido, actualizado = _pedido(pedido)
    [vigente] = _planes_de(pedido)
    huella = (vigente.code, vigente.status, vigente.updated_at, vigente.status_reason)
    auditorias = _auditorias()

    segundo = _plan(h, pedido, almacen, lines=[{"product_id": "x", "quantity": 1}])
    assert segundo.status_code == 409, segundo.text
    cuerpo = segundo.json()
    assert cuerpo["code"] == "PICKLIST_DUPLICATE"
    assert "plan" in cuerpo["message"].lower()
    assert cuerpo["details"] == {"order_id": pedido, "picklist_id": plan_id, "status": "DRAFT"}

    # PL-04/05: ni plan ni líneas; PL-06: el pedido no se tocó; PL-07: el plan vigente tampoco; PL-16/17: sin auditoría falsa.
    planes = _planes_de(pedido)
    assert [p.id for p in planes] == [plan_id]
    with _FACTORY() as db:
        assert db.execute(select(func.count()).select_from(PickListLine).where(PickListLine.picklist_id == plan_id)).scalar_one() == 0
    assert _pedido(pedido) == (estado_pedido, actualizado) == ("RELEASED", actualizado)
    [vigente] = planes
    assert (vigente.code, vigente.status, vigente.updated_at, vigente.status_reason) == huella
    assert _auditorias() == auditorias


# ----------------------------------------------------------------------------- PL-08/09
def test_pl_08_sin_sesion_401_antes_que_409():
    h = _sesion()
    pedido, almacen = _pedido_liberado(h, _D1)
    assert _plan(h, pedido, almacen).status_code == 200
    r = _CLIENT.post(f"{API}/sales/pick-lists", json={"code": "PL-ANON", "order_id": pedido, "warehouse_id": almacen}, headers={COMPANY_HEADER: _D1})
    assert r.status_code == 401, r.text
    assert len(_planes_de(pedido)) == 1


def test_pl_09_sin_permiso_403_antes_que_409():
    h = _sesion()
    pedido, almacen = _pedido_liberado(h, _D1)
    assert _plan(h, pedido, almacen).status_code == 200
    r = _plan(_sesion("operador"), pedido, almacen)
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "PERMISSION_DENIED"
    assert len(_planes_de(pedido)) == 1


# ----------------------------------------------------------------------------- PL-10
def test_pl_10_un_pedido_ajeno_con_plan_vivo_sigue_siendo_404_no_409():
    hc = _sesion("adminc", "T2", _C2)
    pedido_ajeno, almacen_ajeno = _pedido_liberado(hc, _C2)
    assert _plan(hc, pedido_ajeno, almacen_ajeno).status_code == 200
    h = _sesion()
    _, almacen = _pedido_liberado(h, _D1)
    r = _plan(h, pedido_ajeno, almacen)
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "SALES_ORDER_NOT_FOUND"
    assert "PICKLIST" not in r.text
    assert len(_planes_de(pedido_ajeno)) == 1


# ----------------------------------------------------------------------------- PL-11/12
@pytest.mark.skipif(not PG, reason="la carrera se certifica sobre PostgreSQL (P21)")
@pytest.mark.parametrize("n", [2, 10])
def test_pl_11_12_bajo_concurrencia_entra_exactamente_uno_y_el_resto_es_409(n: int):
    h = _sesion()
    pedido, almacen = _pedido_liberado(h, _D1)
    estados: list[int] = []
    cuerpos: list[dict] = []
    barrera = threading.Barrier(n)

    def _intento(i: int) -> None:
        barrera.wait()
        r = _CLIENT.post(f"{API}/sales/pick-lists", json={"code": f"PL-C{i}", "order_id": pedido, "warehouse_id": almacen}, headers=h)
        estados.append(r.status_code)
        cuerpos.append(r.json())

    hilos = [threading.Thread(target=_intento, args=(i,)) for i in range(n)]
    for t in hilos:
        t.start()
    for t in hilos:
        t.join()
    assert sorted(estados) == [200] + [409] * (n - 1), estados
    assert {c["code"] for e, c in zip(estados, cuerpos, strict=True) if e == 409} == {"PICKLIST_DUPLICATE"}
    assert len(_planes_de(pedido)) == 1
    assert [p.status for p in _planes_de(pedido)] == ["DRAFT"]


# ----------------------------------------------------------------------------- PL-13
def test_pl_13_otra_violacion_de_integridad_no_se_disfraza_de_duplicado(monkeypatch):
    h = _sesion()
    pedido, almacen = _pedido_liberado(h, _D1)
    construir = PickList.__init__

    def _plan_invalido(self, **kw):
        kw["status"] = "BOGUS"  # incumple el CHECK `pick_list_status`, no la unicidad
        construir(self, **kw)

    monkeypatch.setattr(PickList, "__init__", _plan_invalido)
    with _FACTORY() as db, pytest.raises(IntegrityError):
        sales_service.create_picklist(db, company_id=_D1, code="PL-BOGUS", order_id=pedido, warehouse_id=almacen, actor="qa")
    assert _planes_de(pedido) == []


# ----------------------------------------------------------------------------- PL-14 (respaldo del índice y sesión viva)
@pytest.mark.skipif(not PG, reason="el índice parcial solo existe en PostgreSQL")
def test_pl_14_si_la_carrera_llega_al_indice_la_respuesta_es_el_mismo_409_y_la_sesion_sigue_viva(monkeypatch):
    h = _sesion()
    pedido, almacen = _pedido_liberado(h, _D1)
    assert _plan(h, pedido, almacen).status_code == 200
    otro, almacen_otro = _pedido_liberado(h, _D1)
    # Simula la carrera: la comprobación previa no ve el plan (otro lo está insertando) y la inserción
    # choca con el índice; la consulta que construye el conflicto ya lo ve.
    ver = sales_service._plan_activo
    llamadas: list[int] = []

    def _ciego_la_primera_vez(*a, **k):
        llamadas.append(1)
        return None if len(llamadas) == 1 else ver(*a, **k)

    monkeypatch.setattr(sales_service, "_plan_activo", _ciego_la_primera_vez)
    with _FACTORY() as db:
        with pytest.raises(ConflictError) as exc:
            sales_service.create_picklist(db, company_id=_D1, code="PL-CARRERA", order_id=pedido, warehouse_id=almacen, actor="qa")
        assert exc.value.code == "PICKLIST_DUPLICATE"
        assert exc.value.details["picklist_id"] == _planes_de(pedido)[0].id
        # La misma sesión sigue sirviendo: otro pedido se planifica y se confirma.
        plan = sales_service.create_picklist(db, company_id=_D1, code="PL-VIVA", order_id=otro, warehouse_id=almacen_otro, actor="qa")
        db.commit()
        assert plan.id
    assert len(_planes_de(pedido)) == 1 and len(_planes_de(otro)) == 1


# ----------------------------------------------------------------------------- PL-15
@pytest.mark.parametrize("terminal", ["CLOSED", "CANCELLED", "INVALIDATED"])
def test_pl_15_un_plan_terminal_libera_el_pedido(terminal: str):
    h = _sesion()
    pedido, almacen = _pedido_liberado(h, _D1)
    primero = _plan(h, pedido, almacen)
    assert primero.status_code == 200
    with _FACTORY() as db:
        db.get(PickList, primero.json()["id"]).status = terminal
        db.commit()
    assert _plan(h, pedido, almacen).status_code == 200
    assert len(_planes_de(pedido)) == 2


@pytest.mark.parametrize("vivo", ["DRAFT", "CONFIRMED"])
def test_pl_15b_un_plan_vivo_en_cualquiera_de_sus_dos_estados_bloquea(vivo: str):
    h = _sesion()
    pedido, almacen = _pedido_liberado(h, _D1)
    primero = _plan(h, pedido, almacen)
    with _FACTORY() as db:
        db.get(PickList, primero.json()["id"]).status = vivo
        db.commit()
    r = _plan(h, pedido, almacen)
    assert r.status_code == 409 and r.json()["details"]["status"] == vivo


# ----------------------------------------------------------------------------- PL-18
def test_pl_18_la_operacion_sigue_protegida_en_el_openapi():
    esquema = _CLIENT.app.openapi()
    assert esquema["paths"]["/api/v1/sales/pick-lists"]["post"]["security"] == [{"BearerAccessToken": []}]
