"""Estructura física de almacén (Spec 008).

Cubre lo que la Spec declara no negociable: que un almacén simple funcione sin
tramos, que uno complejo mantenga la cadena, que el orden físico sea
determinista, que el histórico no se destruya y que `structure_levels` no sea
un campo editable una vez el almacén opera.

Sobre PostgreSQL cuando `KONTROL_TEST_DB_URL` lo indica (P21).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db, init_models
from app.modules.organization import structure as st
from app.modules.organization.models import Warehouse, WarehouseLocation
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine

_CLIENT: TestClient
_FACTORY: sessionmaker


@pytest.fixture(scope="module", autouse=True)
def _app_client():
    global _CLIENT, _FACTORY
    engine = make_engine()
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
    _FACTORY = factory
    _CLIENT = TestClient(app)
    yield _CLIENT


def _headers() -> dict:
    r = _CLIENT.post("/api/v1/auth/login", json={
        "tenant_code": "DEMO", "username": "admin", "password": "Kontrol2026Segura!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _company_id() -> str:
    return _CLIENT.get("/api/v1/organization/companies", headers=_headers()).json()["items"][0]["id"]


def _new_warehouse(code: str, levels: dict | None = None, **extra) -> dict:
    h = _headers()
    body = {"company_id": _company_id(), "code": code, "name": f"Almacén {code}",
            "structure_levels": levels or {}, **extra}
    r = _CLIENT.post("/api/v1/organization/warehouses", headers=h, json=body)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------- AC-008-01
def test_almacen_simple_no_exige_tramos():
    """Un almacén de una habitación crea ubicaciones directas."""
    h = _headers()
    wh = _new_warehouse("SIMPLE-1")
    assert wh["declared_levels"] == []
    assert wh["structure_regime"] == "INITIAL"

    for index in range(1, 6):
        r = _CLIENT.post("/api/v1/organization/locations", headers=h,
                         json={"warehouse_id": wh["id"], "code": f"S-{index:02d}"})
        assert r.status_code == 200, r.text
        assert r.json()["zone"] is None and r.json()["level"] is None

    listed = _CLIENT.get(f"/api/v1/organization/locations?warehouse_id={wh['id']}", headers=h).json()
    assert listed["total"] == 5

    # La estructura no ofrece tramos que el almacén no declara.
    tree = _CLIENT.get(f"/api/v1/organization/warehouses/{wh['id']}/structure", headers=h).json()
    assert tree["zones"] == [] and tree["aisles"] == []
    assert not any(action.startswith("add_zone") for action in tree["allowed_actions"])


# ---------------------------------------------------------------- AC-008-02
def test_almacen_complejo_cadena_completa():
    h = _headers()
    wh = _new_warehouse("CPLX-1", {"zone": True, "aisle": True, "rack": True, "level": True})
    zone = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones", headers=h,
                        json={"code": "ZA", "name": "Alta rotación", "sequence": 1}).json()
    aisle = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/aisles", headers=h,
                         json={"code": "P03", "name": "Pasillo 3", "sequence": 3,
                               "parent_id": zone["id"]}).json()
    rack = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/racks", headers=h,
                        json={"code": "R1", "name": "Rack 1", "sequence": 1,
                              "parent_id": aisle["id"]}).json()
    level = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/levels", headers=h,
                         json={"code": "N2", "name": "Nivel 2", "sequence": 2,
                               "parent_id": rack["id"]}).json()
    loc = _CLIENT.post("/api/v1/organization/locations", headers=h, json={
        "warehouse_id": wh["id"], "code": "A-0345", "name": "Posición 5",
        "zone_id": zone["id"], "aisle_id": aisle["id"], "rack_id": rack["id"],
        "level_id": level["id"]})
    assert loc.status_code == 200, loc.text
    data = loc.json()
    assert data["zone"]["code"] == "ZA" and data["level"]["code"] == "N2"
    assert data["display_path"] == "CPLX-1 / Alta rotación / Pasillo 3 / Rack 1 / Nivel 2 / A-0345"


# ------------------------------------------------------ AC-008-03 / AC-008-04
def test_cadena_incoherente_y_entre_almacenes_rechazadas():
    h = _headers()
    wh = _new_warehouse("CPLX-2", {"zone": True, "aisle": True, "rack": True})
    z1 = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones", headers=h,
                      json={"code": "Z1", "name": "Zona 1"}).json()
    a1 = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/aisles", headers=h,
                      json={"code": "A1", "name": "Pasillo 1", "parent_id": z1["id"]}).json()
    a2 = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/aisles", headers=h,
                      json={"code": "A2", "name": "Pasillo 2", "parent_id": z1["id"]}).json()
    rack = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/racks", headers=h,
                        json={"code": "R1", "name": "Rack 1", "parent_id": a1["id"]}).json()

    # El rack existe y pertenece al almacén, pero cuelga de otro pasillo.
    bad = _CLIENT.post("/api/v1/organization/locations", headers=h, json={
        "warehouse_id": wh["id"], "code": "BAD-1", "zone_id": z1["id"],
        "aisle_id": a2["id"], "rack_id": rack["id"]})
    assert bad.status_code == 422, bad.text
    assert bad.json()["code"] == "HIERARCHY_INCOHERENT"

    # Tramo de otro almacén.
    other = _new_warehouse("CPLX-3", {"zone": True})
    foreign = _CLIENT.post(f"/api/v1/organization/warehouses/{other['id']}/zones", headers=h,
                           json={"code": "ZX", "name": "Zona X"}).json()
    cross = _CLIENT.post("/api/v1/organization/locations", headers=h, json={
        "warehouse_id": wh["id"], "code": "BAD-2", "zone_id": foreign["id"]})
    assert cross.status_code == 422
    assert cross.json()["code"] == "HIERARCHY_CROSS_WAREHOUSE"


def test_tramo_no_declarado_se_rechaza():
    h = _headers()
    wh = _new_warehouse("SIMPLE-2")
    r = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones", headers=h,
                     json={"code": "Z", "name": "Zona"})
    assert r.status_code == 422
    assert r.json()["code"] == "STRUCTURE_LEVEL_DISABLED"


# ---------------------------------------------------------------- AC-008-06
def test_codigo_unico_por_almacen():
    h = _headers()
    wh = _new_warehouse("DUP-1")
    first = _CLIENT.post("/api/v1/organization/locations", headers=h,
                         json={"warehouse_id": wh["id"], "code": "X-01"})
    assert first.status_code == 200
    second = _CLIENT.post("/api/v1/organization/locations", headers=h,
                          json={"warehouse_id": wh["id"], "code": "X-01"})
    assert second.status_code == 409
    assert second.json()["code"] == "LOCATION_CODE_DUPLICATE"

    # El mismo código en otro almacén sí es válido: la unicidad es por almacén.
    other = _new_warehouse("DUP-2")
    ok = _CLIENT.post("/api/v1/organization/locations", headers=h,
                      json={"warehouse_id": other["id"], "code": "X-01"})
    assert ok.status_code == 200


# ---------------------------------------------------------------- AC-008-07
def test_etiqueta_derivada_no_persistida():
    h = _headers()
    wh = _new_warehouse("LBL-1", {"zone": True})
    zone = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones", headers=h,
                        json={"code": "Z", "name": "Alta rotación"}).json()
    loc = _CLIENT.post("/api/v1/organization/locations", headers=h,
                       json={"warehouse_id": wh["id"], "code": "L-1",
                             "zone_id": zone["id"]}).json()
    assert "Alta rotación" in loc["display_path"]

    _CLIENT.patch(f"/api/v1/organization/zones/{zone['id']}", headers=h, json={"name": "Zona A"})
    again = _CLIENT.get(f"/api/v1/organization/locations/{loc['id']}", headers=h).json()
    assert "Zona A" in again["display_path"]
    assert "Alta rotación" not in again["display_path"]

    # La etiqueta no es una columna del modelo.
    assert "display_path" not in {c.name for c in WarehouseLocation.__table__.columns}


# ---------------------------------------------------------------- AC-008-08
def test_orden_fisico_determinista_y_estable():
    h = _headers()
    wh = _new_warehouse("ORD-1", {"zone": True, "aisle": True})
    z2 = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones", headers=h,
                      json={"code": "Z2", "name": "Zona 2", "sequence": 2}).json()
    z1 = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones", headers=h,
                      json={"code": "Z1", "name": "Zona 1", "sequence": 1}).json()
    for code, zone_id, seq in (("C", z2["id"], 1), ("B", z1["id"], 2),
                               ("A", z1["id"], 1), ("SINZONA", None, 0)):
        body = {"warehouse_id": wh["id"], "code": code, "sequence": seq}
        if zone_id:
            body["zone_id"] = zone_id
        assert _CLIENT.post("/api/v1/organization/locations", headers=h, json=body).status_code == 200

    first = _CLIENT.get(f"/api/v1/organization/locations/ordered?warehouse_id={wh['id']}",
                        headers=h).json()
    codes = [item["code"] for item in first["items"]]
    # NULLS FIRST: la ubicación sin zona encabeza; luego zona 1 y dentro de
    # ella por secuencia; luego zona 2.
    assert codes == ["SINZONA", "A", "B", "C"], codes

    second = _CLIENT.get(f"/api/v1/organization/locations/ordered?warehouse_id={wh['id']}",
                         headers=h).json()
    assert [item["code"] for item in second["items"]] == codes
    assert first["items"][0]["physical_order"] == [None, None, None, None, 0]


# ------------------------------------------------------ AC-008-09 / AC-008-10
def test_estados_sin_full_y_mercancia_independiente():
    assert "FULL" not in st.VALID_STATUSES
    columns = {c.name for c in WarehouseLocation.__table__.columns}
    assert "occupancy" not in columns and "is_full" not in columns

    h = _headers()
    wh = _new_warehouse("EST-1")
    loc = _CLIENT.post("/api/v1/organization/locations", headers=h,
                       json={"warehouse_id": wh["id"], "code": "E-1"}).json()
    blocked = _CLIENT.post(f"/api/v1/organization/locations/{loc['id']}/block", headers=h)
    assert blocked.status_code == 200 and blocked.json()["status"] == "BLOCKED"

    # El estado de la ubicación no toca ningún estado de mercancía: no existe
    # tal columna en la ubicación.
    detail = _CLIENT.get(f"/api/v1/organization/locations/{loc['id']}", headers=h).json()
    assert detail["status"] == "BLOCKED"
    assert "goods_state" not in detail and "stock_state" not in detail


# ============================================================================
# CONTROL 2 — mutabilidad estructural (AC-008-31..40)
# ============================================================================

# ---------------------------------------------------------------- AC-008-31
def test_caso_a_structure_levels_editable_sin_datos():
    h = _headers()
    wh = _new_warehouse("MUT-A", {"zone": True})
    r = _CLIENT.patch(f"/api/v1/organization/warehouses/{wh['id']}/structure-levels",
                      headers=h, json={"structure_levels": {"zone": True, "aisle": True}})
    assert r.status_code == 200, r.text
    assert r.json()["declared_levels"] == ["zone", "aisle"]
    assert r.json()["structure_regime"] == "INITIAL"


# ------------------------------------------------------ AC-008-32 / AC-008-33
def test_caso_b_y_c_tramo_utilizado_no_se_elimina_ni_reordena():
    h = _headers()
    wh = _new_warehouse("MUT-B", {"zone": True, "aisle": True, "rack": True})
    zone = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones", headers=h,
                        json={"code": "Z", "name": "Zona"}).json()
    aisle = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/aisles", headers=h,
                         json={"code": "P", "name": "Pasillo", "parent_id": zone["id"]}).json()
    _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/racks", headers=h,
                 json={"code": "R", "name": "Rack", "parent_id": aisle["id"]})

    # El almacén es ya operativo y no vuelve atrás.
    detail = _CLIENT.get(f"/api/v1/organization/warehouses/{wh['id']}", headers=h).json()
    assert detail["structure_regime"] == "OPERATIONAL"
    assert "manage_structure" not in detail["allowed_actions"]

    blocked = _CLIENT.patch(f"/api/v1/organization/warehouses/{wh['id']}/structure-levels",
                            headers=h,
                            json={"structure_levels": {"zone": True, "aisle": True, "rack": False}})
    assert blocked.status_code == 409, blocked.text
    body = blocked.json()
    assert body["code"] == "STRUCTURE_LEVEL_IN_USE"
    assert body["details"]["dependencies"]["node_count"] == 1
    assert body["details"]["allowed_actions"] == ["deactivate"]
    assert body["details"]["reason"]

    # Reordenar/colapsar es retirar un tramo utilizado: mismo bloqueo.
    reorder = _CLIENT.patch(f"/api/v1/organization/warehouses/{wh['id']}/structure-levels",
                            headers=h,
                            json={"structure_levels": {"zone": False, "aisle": True, "rack": True}})
    assert reorder.status_code == 409
    assert reorder.json()["code"] == "STRUCTURE_LEVEL_IN_USE"

    # La jerarquía existente no cambió.
    after = _CLIENT.get(f"/api/v1/organization/warehouses/{wh['id']}", headers=h).json()
    assert after["declared_levels"] == ["zone", "aisle", "rack"]


def test_tramo_declarado_sin_nodos_si_puede_retirarse():
    """La granularidad es el tramo, no el almacén: lo que nunca se usó se
    retira aunque el almacén ya opere."""
    h = _headers()
    wh = _new_warehouse("MUT-B2", {"zone": True, "aisle": True, "rack": True})
    _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones", headers=h,
                 json={"code": "Z", "name": "Zona"})
    r = _CLIENT.patch(f"/api/v1/organization/warehouses/{wh['id']}/structure-levels", headers=h,
                      json={"structure_levels": {"zone": True, "aisle": True, "rack": False}})
    assert r.status_code == 200, r.text
    assert r.json()["declared_levels"] == ["zone", "aisle"]


def test_anadir_profundidad_con_ubicaciones_se_bloquea():
    h = _headers()
    wh = _new_warehouse("MUT-D", {"zone": True})
    zone = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones", headers=h,
                        json={"code": "Z", "name": "Zona"}).json()
    _CLIENT.post("/api/v1/organization/locations", headers=h,
                 json={"warehouse_id": wh["id"], "code": "L1", "zone_id": zone["id"]})
    r = _CLIENT.patch(f"/api/v1/organization/warehouses/{wh['id']}/structure-levels", headers=h,
                      json={"structure_levels": {"zone": True, "aisle": True}})
    assert r.status_code == 409
    assert r.json()["code"] == "STRUCTURE_DEPTH_CHANGE_FORBIDDEN"


# ---------------------------------------------------------------- AC-008-34
def test_caso_d_desactivar_y_reactivar_nodo_sin_dependencias():
    h = _headers()
    wh = _new_warehouse("MUT-E", {"zone": True})
    zone = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones", headers=h,
                        json={"code": "Z", "name": "Zona"}).json()
    off = _CLIENT.post(f"/api/v1/organization/zones/{zone['id']}/deactivate", headers=h)
    assert off.status_code == 200 and off.json()["status"] == "INACTIVE"
    on = _CLIENT.post(f"/api/v1/organization/zones/{zone['id']}/activate", headers=h)
    assert on.status_code == 200 and on.json()["status"] == "ACTIVE"


# ------------------------------------------------------ AC-008-13 / AC-008-40
def test_desactivacion_en_cascada_silenciosa_no_existe():
    h = _headers()
    wh = _new_warehouse("MUT-F", {"zone": True, "aisle": True})
    zone = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones", headers=h,
                        json={"code": "Z", "name": "Zona"}).json()
    aisle = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/aisles", headers=h,
                         json={"code": "P", "name": "Pasillo", "parent_id": zone["id"]}).json()
    blocked = _CLIENT.post(f"/api/v1/organization/zones/{zone['id']}/deactivate", headers=h)
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "NODE_HAS_ACTIVE_CHILDREN"
    assert blocked.json()["details"]["dependencies"]["aisle"] == 1

    # Nada se desactivó en cascada.
    assert _CLIENT.get(f"/api/v1/organization/aisles/{aisle['id']}",
                       headers=h).json()["status"] == "ACTIVE"
    assert _CLIENT.get(f"/api/v1/organization/zones/{zone['id']}",
                       headers=h).json()["status"] == "ACTIVE"


# ---------------------------------------------------------------- AC-008-35
def test_caso_e_borrado_con_descendientes_bloqueado():
    h = _headers()
    wh = _new_warehouse("MUT-G", {"zone": True, "aisle": True})
    zone = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones", headers=h,
                        json={"code": "Z", "name": "Zona"}).json()
    _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/aisles", headers=h,
                 json={"code": "P", "name": "Pasillo", "parent_id": zone["id"]})
    r = _CLIENT.delete(f"/api/v1/organization/zones/{zone['id']}", headers=h)
    assert r.status_code == 409
    assert r.json()["code"] == "NODE_HAS_HISTORY"
    assert r.json()["details"]["allowed_actions"] == ["deactivate"]
    assert _CLIENT.get(f"/api/v1/organization/zones/{zone['id']}", headers=h).status_code == 200


def test_borrado_de_nodo_limpio_permitido():
    h = _headers()
    wh = _new_warehouse("MUT-H", {"zone": True})
    zone = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones", headers=h,
                        json={"code": "Z", "name": "Zona"}).json()
    assert _CLIENT.delete(f"/api/v1/organization/zones/{zone['id']}", headers=h).status_code == 200
    assert _CLIENT.get(f"/api/v1/organization/zones/{zone['id']}", headers=h).status_code == 404


# ---------------------------------------------------------------- AC-008-15
def test_borrar_almacen_no_destruye_ubicaciones():
    """Sin `cascade` destructivo: la relación ORM no puede sobreescribir la
    conservación histórica (R-008-8)."""
    h = _headers()
    wh = _new_warehouse("CASC-1")
    loc = _CLIENT.post("/api/v1/organization/locations", headers=h,
                       json={"warehouse_id": wh["id"], "code": "L-1"}).json()
    blocked = _CLIENT.delete(f"/api/v1/organization/warehouses/{wh['id']}", headers=h)
    assert blocked.status_code == 409
    assert blocked.json()["details"]["dependencies"]["locations"] == 1
    # Ninguna ubicación se borró.
    assert _CLIENT.get(f"/api/v1/organization/locations/{loc['id']}", headers=h).status_code == 200

    # Un almacén vacío sí se borra.
    empty = _new_warehouse("CASC-2")
    assert _CLIENT.delete(f"/api/v1/organization/warehouses/{empty['id']}",
                          headers=h).status_code == 200


def test_sin_cascade_delete_orphan_en_el_modelo():
    assert Warehouse.locations.property.cascade.delete_orphan is False
    assert Warehouse.locations.property.cascade.delete is False


# ---------------------------------------------------------------- AC-008-37
def test_caso_g_almacen_simple_extremo_a_extremo():
    h = _headers()
    wh = _new_warehouse("E2E-S")
    loc = _CLIENT.post("/api/v1/organization/locations", headers=h,
                       json={"warehouse_id": wh["id"], "code": "U-1", "name": "Única"}).json()
    assert _CLIENT.get(f"/api/v1/organization/locations/{loc['id']}", headers=h).status_code == 200
    assert _CLIENT.get(f"/api/v1/organization/locations?warehouse_id={wh['id']}&q=U-1",
                       headers=h).json()["total"] == 1
    assert _CLIENT.post(f"/api/v1/organization/locations/{loc['id']}/deactivate",
                        headers=h).json()["status"] == "INACTIVE"
    assert _CLIENT.post(f"/api/v1/organization/locations/{loc['id']}/activate",
                        headers=h).json()["status"] == "ACTIVE"
    ordered = _CLIENT.get(f"/api/v1/organization/locations/ordered?warehouse_id={wh['id']}",
                          headers=h).json()
    assert ordered["total"] == 1


# ============================================================================
# Multiempresa, permisos y concurrencia
# ============================================================================

def _second_tenant() -> dict:
    """Segundo tenant con su propia empresa, almacén y administrador.

    Se construye desde los modelos porque `initialize` solo corre una vez por
    instalación.
    """
    from app.modules.identity_access import service as identity_service
    from app.modules.identity_access.models import UserRole
    from app.modules.organization.models import Company, Installation, Tenant
    from app.modules.setup.api import _bootstrap_roles

    db = _FACTORY()
    try:
        if db.execute(select(Tenant).where(Tenant.code == "OTRA")).scalars().first() is None:
            inst = db.execute(select(Installation).limit(1)).scalars().first()
            tenant = Tenant(installation_id=str(inst.id), code="OTRA", name="Otra Empresa",
                            plan="MONO_COMPANY", status="ACTIVE")
            db.add(tenant)
            db.flush()
            db.add(Company(tenant_id=str(tenant.id), code="O1", legal_name="Otra C.A.",
                           rif="J-98765432-1", legal_type="CA", functional_currency="VED",
                           status="ACTIVE"))
            user = identity_service.create_user(db, tenant_id=str(tenant.id), username="admin2",
                                                email="admin2@otra.com",
                                                password="Kontrol2026Segura!", created_by=None)
            role = _bootstrap_roles(db, str(tenant.id), str(user.id))
            db.add(UserRole(user_id=str(user.id), role_id=str(role.id), company_id=None))
            db.commit()
    finally:
        db.close()
    r = _CLIENT.post("/api/v1/auth/login", json={
        "tenant_code": "OTRA", "username": "admin2", "password": "Kontrol2026Segura!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------- AC-008-05
def test_aislamiento_multiempresa_en_backend():
    h_a = _headers()
    wh_a = _new_warehouse("ISO-A", {"zone": True})
    zone_a = _CLIENT.post(f"/api/v1/organization/warehouses/{wh_a['id']}/zones", headers=h_a,
                          json={"code": "Z", "name": "Zona"}).json()
    loc_a = _CLIENT.post("/api/v1/organization/locations", headers=h_a,
                         json={"warehouse_id": wh_a["id"], "code": "IA-1"}).json()

    h_b = _second_tenant()
    # No los ve.
    listed = _CLIENT.get("/api/v1/organization/warehouses", headers=h_b).json()
    assert all(w["code"] != "ISO-A" for w in listed["items"])
    assert _CLIENT.get("/api/v1/organization/locations", headers=h_b).json()["total"] == 0

    # No los consulta ni los modifica: se responde como inexistente para no
    # confirmar que existen (enumeración).
    assert _CLIENT.get(f"/api/v1/organization/warehouses/{wh_a['id']}", headers=h_b).status_code == 404
    assert _CLIENT.get(f"/api/v1/organization/locations/{loc_a['id']}", headers=h_b).status_code == 404
    assert _CLIENT.get(f"/api/v1/organization/zones/{zone_a['id']}", headers=h_b).status_code == 404
    assert _CLIENT.patch(f"/api/v1/organization/locations/{loc_a['id']}", headers=h_b,
                         json={"name": "intruso"}).status_code == 404
    assert _CLIENT.post(f"/api/v1/organization/warehouses/{wh_a['id']}/deactivate",
                        headers=h_b).status_code == 404
    assert _CLIENT.delete(f"/api/v1/organization/locations/{loc_a['id']}",
                          headers=h_b).status_code == 404
    # Tampoco puede crear hijos bajo el almacén ajeno.
    assert _CLIENT.post(f"/api/v1/organization/warehouses/{wh_a['id']}/zones", headers=h_b,
                        json={"code": "X", "name": "X"}).status_code == 404
    assert _CLIENT.post("/api/v1/organization/locations", headers=h_b,
                        json={"warehouse_id": wh_a["id"], "code": "X"}).status_code == 404

    # Nada cambió.
    assert _CLIENT.get(f"/api/v1/organization/locations/{loc_a['id']}",
                       headers=h_a).json()["name"] is None


def test_referencia_a_tramo_de_otra_empresa_rechazada():
    h_a = _headers()
    wh_a = _new_warehouse("ISO-C", {"zone": True})
    zone_a = _CLIENT.post(f"/api/v1/organization/warehouses/{wh_a['id']}/zones", headers=h_a,
                          json={"code": "ZC", "name": "Zona C"}).json()
    h_b = _second_tenant()
    company_b = _CLIENT.get("/api/v1/organization/companies", headers=h_b).json()["items"][0]["id"]
    wh_b = _CLIENT.post("/api/v1/organization/warehouses", headers=h_b, json={
        "company_id": company_b, "code": "ISO-D", "name": "Almacén B",
        "structure_levels": {"zone": True}}).json()
    r = _CLIENT.post("/api/v1/organization/locations", headers=h_b, json={
        "warehouse_id": wh_b["id"], "code": "ID-1", "zone_id": zone_a["id"]})
    assert r.status_code == 422
    assert r.json()["code"] == "HIERARCHY_CROSS_WAREHOUSE"


# ---------------------------------------------------------------- AC-008-21
def test_allowed_actions_lo_calcula_el_backend():
    h = _headers()
    wh = _new_warehouse("ACT-1")
    loc = _CLIENT.post("/api/v1/organization/locations", headers=h,
                       json={"warehouse_id": wh["id"], "code": "AC-1"}).json()
    assert set(loc["allowed_actions"]) >= {"edit", "deactivate", "block"}
    assert "delete" in loc["allowed_actions"] and loc["can_delete"] is True

    # Sin permisos, la lista queda vacía: describe lo que ESTE usuario puede.
    db = _FACTORY()
    try:
        obj = db.get(WarehouseLocation, loc["id"])
        assert st.location_allowed_actions(db, obj, permissions=set()) == []
    finally:
        db.close()


def test_if_match_concurrencia_optimista():
    h = _headers()
    wh = _new_warehouse("VER-1")
    loc = _CLIENT.post("/api/v1/organization/locations", headers=h,
                       json={"warehouse_id": wh["id"], "code": "V-1"}).json()
    version = loc["version"]
    ok = _CLIENT.patch(f"/api/v1/organization/locations/{loc['id']}", headers={
        **h, "If-Match": str(version)}, json={"name": "Primero"})
    assert ok.status_code == 200 and ok.json()["version"] == version + 1

    stale = _CLIENT.patch(f"/api/v1/organization/locations/{loc['id']}", headers={
        **h, "If-Match": str(version)}, json={"name": "Segundo"})
    assert stale.status_code == 409
    assert stale.json()["code"] == "VERSION_CONFLICT"
    assert _CLIENT.get(f"/api/v1/organization/locations/{loc['id']}",
                       headers=h).json()["name"] == "Primero"


def test_concurrencia_de_codigo_resuelta_por_constraint():
    """Dos creaciones simultáneas del mismo código: una prospera.

    La garantía es la restricción de base de datos, no una comprobación previa
    en el servicio, que dos transacciones simultáneas pueden pasar a la vez.
    """
    import threading

    h = _headers()
    wh = _new_warehouse("CONC-1")
    results: list[int] = []
    barrier = threading.Barrier(2)

    def attempt() -> None:
        barrier.wait()
        r = _CLIENT.post("/api/v1/organization/locations", headers=h,
                         json={"warehouse_id": wh["id"], "code": "RACE-1"})
        results.append(r.status_code)

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(results) == [200, 409], results
    assert _CLIENT.get(f"/api/v1/organization/locations?warehouse_id={wh['id']}&q=RACE-1",
                       headers=h).json()["total"] == 1


# ---------------------------------------------------------------- AC-008-19
def test_estructura_no_carga_ubicaciones_por_defecto():
    h = _headers()
    wh = _new_warehouse("DEPTH-1", {"zone": True})
    zone = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones", headers=h,
                        json={"code": "Z", "name": "Zona"}).json()
    for index in range(12):
        _CLIENT.post("/api/v1/organization/locations", headers=h,
                     json={"warehouse_id": wh["id"], "code": f"D-{index:02d}",
                           "zone_id": zone["id"]})

    default = _CLIENT.get(f"/api/v1/organization/warehouses/{wh['id']}/structure",
                          headers=h).json()
    assert "locations" not in default
    assert len(default["zones"]) == 1

    paged = _CLIENT.get(
        f"/api/v1/organization/warehouses/{wh['id']}/structure?depth=locations&limit=5",
        headers=h).json()
    assert paged["locations"]["total"] == 12
    assert len(paged["locations"]["items"]) == 5

    bad = _CLIENT.get(f"/api/v1/organization/warehouses/{wh['id']}/structure?depth=galaxia",
                      headers=h)
    assert bad.status_code == 422
    assert bad.json()["code"] == "STRUCTURE_DEPTH_INVALID"


# ---------------------------------------------------------------- AC-008-23
def test_creacion_masiva_con_vista_previa_obligatoria():
    h = _headers()
    wh = _new_warehouse("BULK-1")
    _CLIENT.post("/api/v1/organization/locations", headers=h,
                 json={"warehouse_id": wh["id"], "code": "B-0003"})

    preview = _CLIENT.post("/api/v1/organization/locations/bulk", headers=h, json={
        "warehouse_id": wh["id"], "pattern": "B-{seq}", "count": 5, "preview": True}).json()
    assert preview["preview"] is True
    assert preview["total_planned"] == 4 and preview["already_exists"] == ["B-0003"]
    # La vista previa no escribió nada.
    assert _CLIENT.get(f"/api/v1/organization/locations?warehouse_id={wh['id']}",
                       headers=h).json()["total"] == 1

    created = _CLIENT.post("/api/v1/organization/locations/bulk", headers=h, json={
        "warehouse_id": wh["id"], "pattern": "B-{seq}", "count": 5, "preview": False}).json()
    assert created["total"] == 4 and created["skipped"] == ["B-0003"]
    assert _CLIENT.get(f"/api/v1/organization/locations?warehouse_id={wh['id']}",
                       headers=h).json()["total"] == 5


def test_codigo_generado_desde_el_patron_del_almacen():
    """El patrón es dato del almacén, no una convención codificada (P8)."""
    h = _headers()
    wh = _new_warehouse("GEN-1", code_pattern="{warehouse}/{seq}")
    loc = _CLIENT.post("/api/v1/organization/locations", headers=h,
                       json={"warehouse_id": wh["id"]}).json()
    assert loc["code"] == "GEN-1/0001"
    second = _CLIENT.post("/api/v1/organization/locations", headers=h,
                          json={"warehouse_id": wh["id"]}).json()
    assert second["code"] == "GEN-1/0002"


def test_politica_de_codigo_manual_exige_codigo():
    h = _headers()
    wh = _new_warehouse("MAN-1", code_policy="MANUAL")
    r = _CLIENT.post("/api/v1/organization/locations", headers=h,
                     json={"warehouse_id": wh["id"]})
    assert r.status_code == 422
    assert r.json()["code"] == "LOCATION_CODE_REQUIRED"


# ============================================================================
# Histórico: borrado protegido y reubicación (AC-008-11, 14, 35, 36)
# ============================================================================

def _seed_movement(warehouse_id: str, location_id: str, company_id: str) -> None:
    """Un movimiento real sobre la ubicación. Es lo que la convierte en
    ubicación con historial."""
    from datetime import UTC, datetime

    from app.modules.inventory.models import InventoryMovement, MovementType
    from app.modules.master_data.models import CatalogItem

    db = _FACTORY()
    try:
        mtype = db.execute(select(MovementType).limit(1)).scalars().first()
        if mtype is None:
            mtype = MovementType(code="ENT", name="Entrada", direction="IN",
                                 affects_balance=True, status="ACTIVE")
            db.add(mtype)
            db.flush()
        item = db.execute(select(CatalogItem).limit(1)).scalars().first()
        if item is None:
            item = CatalogItem(company_id=company_id, code="P-001", name="Producto",
                               item_type="PRODUCT", status="ACTIVE")
            db.add(item)
            db.flush()
        db.add(InventoryMovement(
            company_id=company_id, warehouse_id=warehouse_id, location_id=location_id,
            product_id=str(item.id), movement_type_id=str(mtype.id), quantity=10.0,
            currency="VED", occurred_at=datetime.now(UTC),
            # Entrada: procedencia de estado exigida desde la Spec 023.
            target_state="DISPONIBLE"))
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------- AC-008-11
def test_ubicacion_con_movimientos_no_se_borra():
    h = _headers()
    wh = _new_warehouse("HIST-1")
    loc = _CLIENT.post("/api/v1/organization/locations", headers=h,
                       json={"warehouse_id": wh["id"], "code": "H-1"}).json()
    assert loc["can_delete"] is True

    _seed_movement(wh["id"], loc["id"], wh["company_id"])

    detail = _CLIENT.get(f"/api/v1/organization/locations/{loc['id']}", headers=h).json()
    assert detail["can_delete"] is False
    assert "delete" not in detail["allowed_actions"]
    assert "deactivate" in detail["allowed_actions"]
    assert detail["delete_blocked_by"]["movements"] == 1

    blocked = _CLIENT.delete(f"/api/v1/organization/locations/{loc['id']}", headers=h)
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "LOCATION_HAS_HISTORY"
    assert blocked.json()["details"]["allowed_actions"] == ["deactivate"]
    # Sigue existiendo.
    assert _CLIENT.get(f"/api/v1/organization/locations/{loc['id']}", headers=h).status_code == 200


# ---------------------------------------------------------------- AC-008-12
def test_desactivacion_reversible_y_auditada():
    h = _headers()
    wh = _new_warehouse("HIST-2")
    loc = _CLIENT.post("/api/v1/organization/locations", headers=h,
                       json={"warehouse_id": wh["id"], "code": "H-2"}).json()
    _seed_movement(wh["id"], loc["id"], wh["company_id"])

    assert _CLIENT.post(f"/api/v1/organization/locations/{loc['id']}/deactivate",
                        headers=h).json()["status"] == "INACTIVE"
    assert _CLIENT.post(f"/api/v1/organization/locations/{loc['id']}/activate",
                        headers=h).json()["status"] == "ACTIVE"

    from app.modules.audit.models import AuditEvent

    db = _FACTORY()
    try:
        actions = {e.action for e in db.execute(
            select(AuditEvent).where(AuditEvent.entity_id == loc["id"])).scalars().all()}
    finally:
        db.close()
    assert {"DEACTIVATE", "ACTIVATE", "DELETE_BLOCKED"} & actions == {"DEACTIVATE", "ACTIVATE"}


# ------------------------------------------------------ AC-008-14 / AC-008-36
def test_caso_f_reubicacion_con_historial_bloqueada():
    h = _headers()
    wh = _new_warehouse("REL-1", {"zone": True})
    z1 = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones", headers=h,
                      json={"code": "Z1", "name": "Zona 1"}).json()
    z2 = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones", headers=h,
                      json={"code": "Z2", "name": "Zona 2"}).json()
    loc = _CLIENT.post("/api/v1/organization/locations", headers=h,
                       json={"warehouse_id": wh["id"], "code": "R-1",
                             "zone_id": z1["id"]}).json()

    # Sin historial: la reubicación se permite y se audita.
    moved = _CLIENT.patch(f"/api/v1/organization/locations/{loc['id']}", headers=h,
                          json={"zone_id": z2["id"]})
    assert moved.status_code == 200, moved.text
    assert moved.json()["zone"]["code"] == "Z2"

    _seed_movement(wh["id"], loc["id"], wh["company_id"])

    # Con historial: rechazada. Mover mercancía es un movimiento, no una edición.
    blocked = _CLIENT.patch(f"/api/v1/organization/locations/{loc['id']}", headers=h,
                            json={"zone_id": z1["id"]})
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "LOCATION_HAS_HISTORY"
    assert _CLIENT.get(f"/api/v1/organization/locations/{loc['id']}",
                       headers=h).json()["zone"]["code"] == "Z2"

    # La metadata sí sigue siendo editable: no es un cambio estructural.
    ok = _CLIENT.patch(f"/api/v1/organization/locations/{loc['id']}", headers=h,
                       json={"name": "Renombrada"})
    assert ok.status_code == 200 and ok.json()["name"] == "Renombrada"


# ---------------------------------------------------------------- AC-008-35
def test_historico_heredado_impide_borrar_el_nodo_padre():
    """Una zona sin stock propio cuya ubicación tiene movimientos tampoco se
    borra: el histórico se hereda hacia arriba."""
    h = _headers()
    wh = _new_warehouse("INH-1", {"zone": True})
    zone = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones", headers=h,
                        json={"code": "Z", "name": "Zona"}).json()
    loc = _CLIENT.post("/api/v1/organization/locations", headers=h,
                       json={"warehouse_id": wh["id"], "code": "I-1",
                             "zone_id": zone["id"]}).json()
    _seed_movement(wh["id"], loc["id"], wh["company_id"])

    db = _FACTORY()
    try:
        inherited = st.node_inherited_history(db, "zone", zone["id"])
    finally:
        db.close()
    assert inherited and inherited["movements"] == 1

    r = _CLIENT.delete(f"/api/v1/organization/zones/{zone['id']}", headers=h)
    assert r.status_code == 409
    assert r.json()["code"] == "NODE_HAS_HISTORY"


# ---------------------------------------------------------------- AC-008-16
def test_las_dos_referencias_son_fk_reales():
    """PostgreSQL rechaza una ubicación inexistente en saldo y en conteo."""
    from app.core.database import Base as _Base

    for table in ("inventory_balances", "stock_count_lines"):
        fks = {list(fk.columns)[0].name: list(fk.elements)[0].target_fullname
               for fk in _Base.metadata.tables[table].foreign_key_constraints}
        assert fks.get("location_id") == "warehouse_locations.id", table


@pytest.mark.skipif("postgresql" not in __import__("os").environ.get("KONTROL_TEST_DB_URL", ""),
                    reason="La integridad referencial solo la impone PostgreSQL")
def test_fk_rechaza_ubicacion_inexistente_en_postgresql():
    from sqlalchemy.exc import IntegrityError

    from app.modules.inventory.models import InventoryBalance

    h = _headers()
    wh = _new_warehouse("FK-1")
    db = _FACTORY()
    try:
        db.add(InventoryBalance(
            company_id=wh["company_id"], warehouse_id=wh["id"],
            location_id="00000000-0000-0000-0000-000000000000",
            product_id="00000000-0000-0000-0000-000000000000",
            state="DISPONIBLE", qty_on_hand=0.0, qty_reserved=0.0, qty_available=0.0))
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()
    del h
