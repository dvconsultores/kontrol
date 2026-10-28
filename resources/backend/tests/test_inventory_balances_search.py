"""
C05-T05: búsqueda por producto en GET /api/v1/inventory/balances.
"""
import uuid
from types import SimpleNamespace

import pytest
from mfa_mundo import API, alta_por_desafio, crear_usuario, login, mundo_mfa

from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import UserRole
from app.modules.inventory.models import InventoryBalance
from app.modules.master_data.models import CatalogItem
from app.modules.organization.models import Company, Warehouse

pytest_plugins = ("mfa_apoyo",)


@pytest.fixture(scope="module")
def mundo():
    with mundo_mfa() as m:
        yield m


def _dar(mundo, user_id, role_id, company_id):
    db = mundo.factory()
    try:
        db.add(UserRole(user_id=user_id, role_id=role_id, company_id=company_id))
        db.commit()
    finally:
        db.close()


def _entrar(mundo, reloj, nombre):
    r = login(mundo.client, nombre)
    assert r.status_code == 200, r.text
    if r.json().get("status") == "AUTHENTICATED":
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return alta_por_desafio(mundo.client, reloj, nombre).cabeceras


@pytest.fixture(scope="module")
def escenario(mundo):
    s = uuid.uuid4().hex[:8]
    db = mundo.factory()
    try:
        # empresa principal: dos almacenes, dos artículos, tres saldos
        w1 = Warehouse(company_id=mundo.company_id, code=f"EXS-W1-{s}", name="W1", status="ACTIVE")
        w2 = Warehouse(company_id=mundo.company_id, code=f"EXS-W2-{s}", name="W2", status="ACTIVE")
        item_a = CatalogItem(company_id=mundo.company_id, code=f"EXS-A-{s}", name=f"Tornillo galvanizado {s}",
                             item_type="PRODUCT", status="ACTIVE")
        item_b = CatalogItem(company_id=mundo.company_id, code=f"EXS-B-{s}", name=f"Tuerca hexagonal {s}",
                             item_type="PRODUCT", status="ACTIVE")
        db.add_all([w1, w2, item_a, item_b])
        db.flush()

        balance_a_w1 = InventoryBalance(company_id=mundo.company_id, warehouse_id=str(w1.id), product_id=str(item_a.id),
                                        state="DISPONIBLE", qty_on_hand=10.0, qty_reserved=0.0, qty_available=10.0)
        balance_a_w2 = InventoryBalance(company_id=mundo.company_id, warehouse_id=str(w2.id), product_id=str(item_a.id),
                                        state="DISPONIBLE", qty_on_hand=10.0, qty_reserved=0.0, qty_available=10.0)
        balance_b_w1 = InventoryBalance(company_id=mundo.company_id, warehouse_id=str(w1.id), product_id=str(item_b.id),
                                        state="DISPONIBLE", qty_on_hand=10.0, qty_reserved=0.0, qty_available=10.0)

        # empresa D2 con su artículo C y su saldo
        company_d2 = Company(tenant_id=mundo.tenant_id, code=f"EXS-D2-{s}", legal_name=f"D2 {s}",
                             rif="J-55555555-5", legal_type="JURIDICA", functional_currency="VED",
                             status="ACTIVE")
        db.add(company_d2)
        db.flush()

        w_d2 = Warehouse(company_id=company_d2.id, code=f"EXS-WD2-{s}", name="WD2", status="ACTIVE")
        item_c = CatalogItem(company_id=company_d2.id, code=f"EXS-C-{s}", name=f"Tornillo galvanizado {s}",
                             item_type="PRODUCT", status="ACTIVE")
        db.add_all([w_d2, item_c])
        db.flush()

        balance_c_d2 = InventoryBalance(company_id=company_d2.id, warehouse_id=str(w_d2.id), product_id=str(item_c.id),
                                        state="DISPONIBLE", qty_on_hand=10.0, qty_reserved=0.0, qty_available=10.0)

        # saldo corrupto en la empresa principal apuntando al artículo de D2
        balance_corrupto = InventoryBalance(company_id=mundo.company_id, warehouse_id=str(w1.id), product_id=str(item_c.id),
                                            state="DISPONIBLE", qty_on_hand=10.0, qty_reserved=0.0, qty_available=10.0)

        db.add_all([balance_a_w1, balance_a_w2, balance_b_w1, balance_c_d2, balance_corrupto])
        db.flush()

        role = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"EXS-ROLE-{s}",
            name=f"Existencias {s}",
            company_id=None,
            permissions=["inventario:view"],
            actor=mundo.admin_id,
        )
        db.commit()

        return SimpleNamespace(
            s=s,
            w1_id=str(w1.id),
            a_id=str(item_a.id),
            b_id=str(item_b.id),
            c_id=str(item_c.id),
            d2_balance_id=str(balance_c_d2.id),
            corrupto_id=str(balance_corrupto.id),
            role_id=role["id"],
        )
    finally:
        db.close()


def _actor(mundo, reloj_mfa, role_id):
    nombre = f"exs{uuid.uuid4().hex[:12]}"
    user_id = crear_usuario(mundo, nombre)
    _dar(mundo, user_id, role_id, mundo.company_id)
    headers = _entrar(mundo, reloj_mfa, nombre)
    headers["X-Kontrol-Company"] = str(mundo.company_id)
    return headers


def _buscar(mundo, reloj_mfa, role_id, **params):
    headers = _actor(mundo, reloj_mfa, role_id)
    r = mundo.client.get(f"{API}/inventory/balances", headers=headers, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_e01_busca_por_nombre_sin_mayusculas(mundo, escenario, reloj_mfa):
    """E-01: búsqueda por nombre sin distinguir mayúsculas."""
    body = _buscar(mundo, reloj_mfa, escenario.role_id, q=f"TORNILLO GALVANIZADO {escenario.s}")
    assert body["total"] == 2, body
    assert all(item["product_id"] == escenario.a_id for item in body["items"]), body


def test_e02_busca_por_codigo(mundo, escenario, reloj_mfa):
    """E-02: búsqueda por código."""
    body = _buscar(mundo, reloj_mfa, escenario.role_id, q=f"exs-b-{escenario.s}")
    assert body["total"] == 1, body
    assert body["items"][0]["product_id"] == escenario.b_id, body


def test_e03_publica_identidad_del_producto(mundo, escenario, reloj_mfa):
    """E-03: publicación de identidad del producto, sin saldo corrupto."""
    body = _buscar(mundo, reloj_mfa, escenario.role_id, q=escenario.s)
    assert body["items"], body
    ids = {item["id"] for item in body["items"]}
    assert escenario.corrupto_id not in ids, body
    assert escenario.d2_balance_id not in ids, body
    for item in body["items"]:
        assert item["product_id"] in (escenario.a_id, escenario.b_id), body
        assert item["product_code"] in (f"EXS-A-{escenario.s}", f"EXS-B-{escenario.s}"), body
        assert item["product_name"] in (f"Tornillo galvanizado {escenario.s}", f"Tuerca hexagonal {escenario.s}"), body


def test_e04_sin_coincidencias(mundo, escenario, reloj_mfa):
    """E-04: sin coincidencias."""
    body = _buscar(mundo, reloj_mfa, escenario.role_id, q=f"NADA-{escenario.s}")
    assert body["total"] == 0, body
    assert body["items"] == [], body


def test_e05_compone_con_filtros(mundo, escenario, reloj_mfa):
    """E-05: composición con filtros."""
    body = _buscar(mundo, reloj_mfa, escenario.role_id, q=f"Tornillo galvanizado {escenario.s}",
                   warehouse_id=escenario.w1_id)
    assert body["total"] == 1, body
    assert body["items"][0]["product_id"] == escenario.a_id, body


def test_e06_compone_con_paginacion(mundo, escenario, reloj_mfa):
    """E-06: composición con paginación determinista."""
    q = f"Tornillo galvanizado {escenario.s}"
    page1 = _buscar(mundo, reloj_mfa, escenario.role_id, q=q, page_size=1, page=1)
    page2 = _buscar(mundo, reloj_mfa, escenario.role_id, q=q, page_size=1, page=2)
    assert page1["total"] == 2, page1
    assert page2["total"] == 2, page2
    assert len(page1["items"]) == 1, page1
    assert len(page2["items"]) == 1, page2
    assert page1["items"][0]["id"] != page2["items"][0]["id"], page1


def test_e07_vacio_no_filtra(mundo, escenario, reloj_mfa):
    """E-07: q vacío no filtra; el saldo corrupto aparece sin identidad de producto."""
    sin_q = _buscar(mundo, reloj_mfa, escenario.role_id, page_size=100)
    con_q = _buscar(mundo, reloj_mfa, escenario.role_id, q="", page_size=100)
    assert sin_q["total"] == con_q["total"], (sin_q, con_q)
    assert sin_q["total"] >= 4, sin_q
    sin_q_ids = {item["id"] for item in sin_q["items"]}
    assert escenario.d2_balance_id not in sin_q_ids, sin_q
    assert escenario.corrupto_id in sin_q_ids, sin_q
    corrupto = next(item for item in sin_q["items"] if item["id"] == escenario.corrupto_id)
    assert corrupto["product_name"] is None, corrupto
    assert corrupto["product_code"] is None, corrupto


def test_e08_otra_empresa_no_coincide(mundo, escenario, reloj_mfa):
    """E-08: saldos de otra empresa y corrupto no coinciden."""
    body = _buscar(mundo, reloj_mfa, escenario.role_id, q=f"Tornillo galvanizado {escenario.s}")
    assert body["total"] == 2, body
    ids = {item["id"] for item in body["items"]}
    assert escenario.corrupto_id not in ids, body
    assert escenario.d2_balance_id not in ids, body
    assert all(item["product_id"] == escenario.a_id for item in body["items"]), body
    assert all(item["product_id"] != escenario.c_id for item in body["items"]), body
