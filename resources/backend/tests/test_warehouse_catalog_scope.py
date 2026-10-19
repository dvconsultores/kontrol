"""Deuda WAREHOUSE-CATALOG-TYPE-CROSS-COMPANY: ubicaciones y zonas solo aceptan tipos de
catálogo de la empresa activa del contexto (ADR-D0-014); ajeno, de otro tenant o inexistente
se responde igual, como inexistente, con 404.

Las pruebas pasan en SQLite y PostgreSQL, sin skip, sin mocks.
"""
from __future__ import annotations

import ast
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.company_context import COMPANY_HEADER
from app.core.database import Base, get_db, init_models
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import UserRole, UserScope
from app.modules.organization.models import (
    Company,
    Installation,
    LocationType,
    Tenant,
    WarehouseLocation,
    WarehouseZone,
    ZoneType,
)
from app.modules.setup.api import SetupRequest, _bootstrap_roles, initialize
from tests.conftest import make_engine

PASSWORD = "Kontrol2026Segura!"

EMPRESA_A = EMPRESA_B = EMPRESA_C = None
LT_A = LT_B = LT_C = None
ZT_A = ZT_B = ZT_C = None
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
    global CLIENT, FACTORY, EMPRESA_A, EMPRESA_B, EMPRESA_C, LT_A, LT_B, LT_C, ZT_A, ZT_B, ZT_C

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

    lta = LocationType(company_id=str(ca.id), code="LT-A", name="Estante A",
                       status="ACTIVE", is_storable=True)
    ltb = LocationType(company_id=str(cb.id), code="LT-B", name="Estante B",
                       status="ACTIVE", is_storable=True)
    ltc = LocationType(company_id=str(cc.id), code="LT-C", name="Estante C",
                       status="ACTIVE", is_storable=True)
    zta = ZoneType(company_id=str(ca.id), code="ZT-A", name="Zona A", status="ACTIVE")
    ztb = ZoneType(company_id=str(cb.id), code="ZT-B", name="Zona B", status="ACTIVE")
    ztc = ZoneType(company_id=str(cc.id), code="ZT-C", name="Zona C", status="ACTIVE")
    db.add_all([lta, ltb, ltc, zta, ztb, ztc])
    db.flush()

    _crear_usuario(db, str(t1.id), "ua", [str(ca.id)])
    _crear_usuario(db, str(t1.id), "uab", [str(ca.id), str(cb.id)])

    sinrol = identity_service.create_user(
        db, tenant_id=str(t1.id), username="sinrol", email="sinrol@demo.test",
        password=PASSWORD, created_by=None)
    db.add(UserScope(user_id=str(sinrol.id), company_id=str(ca.id)))

    db.commit()

    EMPRESA_A, EMPRESA_B, EMPRESA_C = str(ca.id), str(cb.id), str(cc.id)
    LT_A, LT_B, LT_C = str(lta.id), str(ltb.id), str(ltc.id)
    ZT_A, ZT_B, ZT_C = str(zta.id), str(ztb.id), str(ztc.id)
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
    r = CLIENT.post("/api/v1/auth/login", json={
        "tenant_code": "T1", "username": usuario, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _como(usuario: str, empresa: str, tenant: str = "T1") -> dict:
    token = _login(usuario)
    return {
        "Authorization": f"Bearer {token}",
        COMPANY_HEADER: empresa,
    }


def _almacen(usuario: str, empresa: str, code: str, **extra) -> dict:
    headers = _como(usuario, empresa)
    payload = {"company_id": empresa, "code": code, "name": f"Almacén {code}", **extra}
    r = CLIENT.post("/api/v1/organization/warehouses", headers=headers, json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def _ubicacion_tipo(fila_id: str) -> str | None:
    db = FACTORY()
    try:
        loc = db.get(WarehouseLocation, fila_id)
        return str(loc.location_type_id) if loc and loc.location_type_id else None
    finally:
        db.close()


def _zona_tipo(fila_id: str) -> str | None:
    db = FACTORY()
    try:
        zona = db.get(WarehouseZone, fila_id)
        return str(zona.zone_type_id) if zona and zona.zone_type_id else None
    finally:
        db.close()


def _cuenta(modelo, **filtros) -> int:
    db = FACTORY()
    try:
        return db.query(modelo).filter_by(**filtros).count()
    finally:
        db.close()


def test_c01_ubicacion_en_a_con_lt_a_ok():
    wh = _almacen("ua", EMPRESA_A, "C01")
    r = CLIENT.post("/api/v1/organization/locations", headers=_como("ua", EMPRESA_A), json={
        "warehouse_id": wh["id"], "code": "L-C01", "location_type_id": LT_A})
    assert r.status_code == 200, r.text
    assert _ubicacion_tipo(r.json()["id"]) == LT_A


def test_c02_ubicacion_en_a_con_lt_b_otra_empresa_404():
    wh = _almacen("ua", EMPRESA_A, "C02")
    r = CLIENT.post("/api/v1/organization/locations", headers=_como("ua", EMPRESA_A), json={
        "warehouse_id": wh["id"], "code": "L-C02", "location_type_id": LT_B})
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "LOCATION_TYPE_NOT_FOUND"
    assert r.json()["message"] == "Tipo de ubicación no encontrado"
    assert _cuenta(WarehouseLocation, warehouse_id=wh["id"], code="L-C02") == 0


def test_c03_ubicacion_en_a_con_lt_c_otro_tenant_404():
    wh = _almacen("ua", EMPRESA_A, "C03")
    r = CLIENT.post("/api/v1/organization/locations", headers=_como("ua", EMPRESA_A), json={
        "warehouse_id": wh["id"], "code": "L-C03", "location_type_id": LT_C})
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "LOCATION_TYPE_NOT_FOUND"
    assert _cuenta(WarehouseLocation, warehouse_id=wh["id"], code="L-C03") == 0


def test_c04_ubicacion_con_tipo_inexistente_mismo_contrato_que_c02():
    wh = _almacen("ua", EMPRESA_A, "C04")
    inexistente = str(uuid.uuid4())
    r = CLIENT.post("/api/v1/organization/locations", headers=_como("ua", EMPRESA_A), json={
        "warehouse_id": wh["id"], "code": "L-C04", "location_type_id": inexistente})
    assert r.status_code == 404, r.text

    referencia = CLIENT.post("/api/v1/organization/locations", headers=_como("ua", EMPRESA_A), json={
        "warehouse_id": wh["id"], "code": "L-C04-REF", "location_type_id": LT_B})
    assert referencia.status_code == 404, referencia.text
    assert r.json()["code"] == referencia.json()["code"]
    assert r.json()["message"] == referencia.json()["message"]
    assert _cuenta(WarehouseLocation, warehouse_id=wh["id"], code="L-C04") == 0


def test_c05_bulk_en_a_con_lt_a_ok():
    wh = _almacen("ua", EMPRESA_A, "C05")
    r = CLIENT.post("/api/v1/organization/locations/bulk", headers=_como("ua", EMPRESA_A), json={
        "warehouse_id": wh["id"], "pattern": "C05-{n}", "count": 2,
        "preview": False, "location_type_id": LT_A})
    assert r.status_code == 200, r.text
    assert _cuenta(WarehouseLocation, warehouse_id=wh["id"]) == 2
    db = FACTORY()
    try:
        locs = db.query(WarehouseLocation).filter_by(warehouse_id=wh["id"]).all()
        assert {_ubicacion_tipo(str(loc.id)) for loc in locs} == {LT_A}
    finally:
        db.close()


def test_c06_bulk_en_a_con_lt_b_404():
    wh = _almacen("ua", EMPRESA_A, "C06")
    r = CLIENT.post("/api/v1/organization/locations/bulk", headers=_como("ua", EMPRESA_A), json={
        "warehouse_id": wh["id"], "pattern": "C06-{n}", "count": 2,
        "preview": False, "location_type_id": LT_B})
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "LOCATION_TYPE_NOT_FOUND"
    assert _cuenta(WarehouseLocation, warehouse_id=wh["id"]) == 0


def test_c06b_bulk_preview_en_a_con_lt_b_404():
    wh = _almacen("ua", EMPRESA_A, "C06B")
    r = CLIENT.post("/api/v1/organization/locations/bulk", headers=_como("ua", EMPRESA_A), json={
        "warehouse_id": wh["id"], "pattern": "C06B-{n}", "count": 2,
        "preview": True, "location_type_id": LT_B})
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "LOCATION_TYPE_NOT_FOUND"
    assert _cuenta(WarehouseLocation, warehouse_id=wh["id"]) == 0


def test_c07_patch_ubicacion_tipo_propio_y_null_desliga():
    wh = _almacen("ua", EMPRESA_A, "C07")
    r = CLIENT.post("/api/v1/organization/locations", headers=_como("ua", EMPRESA_A), json={
        "warehouse_id": wh["id"], "code": "L-C07", "location_type_id": LT_A})
    assert r.status_code == 200, r.text
    lid = r.json()["id"]

    r = CLIENT.patch(f"/api/v1/organization/locations/{lid}", headers=_como("ua", EMPRESA_A),
                     json={"location_type_id": LT_A})
    assert r.status_code == 200, r.text
    assert _ubicacion_tipo(lid) == LT_A

    r = CLIENT.patch(f"/api/v1/organization/locations/{lid}", headers=_como("ua", EMPRESA_A),
                     json={"location_type_id": None})
    assert r.status_code == 200, r.text
    assert _ubicacion_tipo(lid) is None

    r = CLIENT.patch(f"/api/v1/organization/locations/{lid}", headers=_como("ua", EMPRESA_A),
                     json={"location_type_id": LT_A})
    assert r.status_code == 200, r.text
    assert _ubicacion_tipo(lid) == LT_A


def test_c08_patch_ubicacion_con_lt_b_404_y_no_cambia():
    wh = _almacen("ua", EMPRESA_A, "C08")
    r = CLIENT.post("/api/v1/organization/locations", headers=_como("ua", EMPRESA_A), json={
        "warehouse_id": wh["id"], "code": "L-C08", "location_type_id": LT_A})
    assert r.status_code == 200, r.text
    lid = r.json()["id"]
    version = r.json()["version"]

    r = CLIENT.patch(f"/api/v1/organization/locations/{lid}", headers=_como("ua", EMPRESA_A),
                     json={"location_type_id": LT_B})
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "LOCATION_TYPE_NOT_FOUND"
    assert _ubicacion_tipo(lid) == LT_A

    r = CLIENT.get(f"/api/v1/organization/locations/{lid}", headers=_como("ua", EMPRESA_A))
    assert r.status_code == 200, r.text
    assert r.json()["version"] == version


def test_c09_zona_en_a_con_zt_a_ok():
    wh = _almacen("ua", EMPRESA_A, "C09", structure_levels={"zone": True})
    r = CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones",
                    headers=_como("ua", EMPRESA_A), json={
                        "code": "Z-C09", "name": "Zona", "zone_type_id": ZT_A})
    assert r.status_code == 200, r.text
    assert _zona_tipo(r.json()["id"]) == ZT_A


def test_c10_zona_en_a_con_zt_b_otra_empresa_404():
    wh = _almacen("ua", EMPRESA_A, "C10", structure_levels={"zone": True})
    r = CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones",
                    headers=_como("ua", EMPRESA_A), json={
                        "code": "Z-C10", "name": "Zona", "zone_type_id": ZT_B})
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "ZONE_TYPE_NOT_FOUND"
    assert r.json()["message"] == "Tipo de zona no encontrado"
    assert _cuenta(WarehouseZone, warehouse_id=wh["id"], code="Z-C10") == 0


def test_c11_zona_en_a_con_zt_c_otro_tenant_404():
    wh = _almacen("ua", EMPRESA_A, "C11", structure_levels={"zone": True})
    r = CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones",
                    headers=_como("ua", EMPRESA_A), json={
                        "code": "Z-C11", "name": "Zona", "zone_type_id": ZT_C})
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "ZONE_TYPE_NOT_FOUND"
    assert _cuenta(WarehouseZone, warehouse_id=wh["id"], code="Z-C11") == 0


def test_c12_zona_con_tipo_inexistente_mismo_contrato_que_c10():
    wh = _almacen("ua", EMPRESA_A, "C12", structure_levels={"zone": True})
    inexistente = str(uuid.uuid4())
    r = CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones",
                    headers=_como("ua", EMPRESA_A), json={
                        "code": "Z-C12", "name": "Zona", "zone_type_id": inexistente})
    assert r.status_code == 404, r.text

    referencia = CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones",
                             headers=_como("ua", EMPRESA_A), json={
                                 "code": "Z-C12-REF", "name": "Zona", "zone_type_id": ZT_B})
    assert referencia.status_code == 404, referencia.text
    assert r.json()["code"] == referencia.json()["code"]
    assert r.json()["message"] == referencia.json()["message"]
    assert _cuenta(WarehouseZone, warehouse_id=wh["id"], code="Z-C12") == 0


def test_c13_patch_zona_a_zt_a_ok():
    wh = _almacen("ua", EMPRESA_A, "C13", structure_levels={"zone": True})
    r = CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones",
                    headers=_como("ua", EMPRESA_A), json={
                        "code": "Z-C13", "name": "Zona"})
    assert r.status_code == 200, r.text
    zid = r.json()["id"]

    r = CLIENT.patch(f"/api/v1/organization/zones/{zid}", headers=_como("ua", EMPRESA_A),
                     json={"zone_type_id": ZT_A})
    assert r.status_code == 200, r.text
    assert _zona_tipo(zid) == ZT_A


def test_c14_patch_zona_con_zt_b_404_y_no_cambia():
    wh = _almacen("ua", EMPRESA_A, "C14", structure_levels={"zone": True})
    r = CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones",
                    headers=_como("ua", EMPRESA_A), json={
                        "code": "Z-C14", "name": "Zona", "zone_type_id": ZT_A})
    assert r.status_code == 200, r.text
    zid = r.json()["id"]

    r = CLIENT.patch(f"/api/v1/organization/zones/{zid}", headers=_como("ua", EMPRESA_A),
                     json={"zone_type_id": ZT_B})
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "ZONE_TYPE_NOT_FOUND"
    assert _zona_tipo(zid) == ZT_A


def test_c15_null_ubicacion_sin_tipo_y_patch_zona_null_desliga():
    wh = _almacen("ua", EMPRESA_A, "C15", structure_levels={"zone": True})
    r = CLIENT.post("/api/v1/organization/locations", headers=_como("ua", EMPRESA_A), json={
        "warehouse_id": wh["id"], "code": "L-C15", "location_type_id": None})
    assert r.status_code == 200, r.text
    assert _ubicacion_tipo(r.json()["id"]) is None

    r = CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones",
                    headers=_como("ua", EMPRESA_A), json={
                        "code": "Z-C15", "name": "Zona", "zone_type_id": ZT_A})
    assert r.status_code == 200, r.text
    zid = r.json()["id"]

    r = CLIENT.patch(f"/api/v1/organization/zones/{zid}", headers=_como("ua", EMPRESA_A),
                     json={"zone_type_id": None})
    assert r.status_code == 200, r.text
    assert _zona_tipo(zid) is None


def test_c16_patch_ubicacion_solo_name_no_toca_tipo():
    wh = _almacen("ua", EMPRESA_A, "C16")
    r = CLIENT.post("/api/v1/organization/locations", headers=_como("ua", EMPRESA_A), json={
        "warehouse_id": wh["id"], "code": "L-C16", "location_type_id": LT_A})
    assert r.status_code == 200, r.text
    lid = r.json()["id"]

    r = CLIENT.patch(f"/api/v1/organization/locations/{lid}", headers=_como("ua", EMPRESA_A),
                     json={"name": "x"})
    assert r.status_code == 200, r.text
    assert _ubicacion_tipo(lid) == LT_A


def test_c17_sin_auth_con_lt_b_401():
    wh = _almacen("ua", EMPRESA_A, "C17")
    r = CLIENT.post("/api/v1/organization/locations", json={
        "warehouse_id": wh["id"], "code": "L-C17", "location_type_id": LT_B})
    assert r.status_code == 401, r.text


def test_c18_sin_rol_en_a_con_lt_b_403():
    wh = _almacen("ua", EMPRESA_A, "C18")
    r = CLIENT.post("/api/v1/organization/locations", headers=_como("sinrol", EMPRESA_A),
                    json={
                        "warehouse_id": wh["id"], "code": "L-C18", "location_type_id": LT_B})
    assert r.status_code == 403, r.text


def test_c19_almacen_de_b_patch_por_ua_en_a_404():
    wh_b = _almacen("uab", EMPRESA_B, "C19", structure_levels={"zone": True})

    r = CLIENT.post("/api/v1/organization/locations", headers=_como("ua", EMPRESA_A), json={
        "warehouse_id": wh_b["id"], "code": "L-C19-AJENA", "location_type_id": LT_A})
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "WAREHOUSE_NOT_FOUND"

    r = CLIENT.post(f"/api/v1/organization/warehouses/{wh_b['id']}/zones",
                    headers=_como("ua", EMPRESA_A), json={
                        "code": "Z-C19-AJENA", "name": "Zona", "zone_type_id": ZT_A})
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "WAREHOUSE_NOT_FOUND"

    r = CLIENT.post("/api/v1/organization/locations", headers=_como("uab", EMPRESA_B), json={
        "warehouse_id": wh_b["id"], "code": "L-C19", "location_type_id": LT_B})
    assert r.status_code == 200, r.text
    lid = r.json()["id"]

    r = CLIENT.patch(f"/api/v1/organization/locations/{lid}", headers=_como("ua", EMPRESA_A),
                     json={"location_type_id": LT_A})
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "LOCATION_NOT_FOUND"

    r = CLIENT.post(f"/api/v1/organization/warehouses/{wh_b['id']}/zones",
                    headers=_como("uab", EMPRESA_B), json={
                        "code": "Z-C19", "name": "Zona", "zone_type_id": ZT_B})
    assert r.status_code == 200, r.text
    zid = r.json()["id"]

    r = CLIENT.patch(f"/api/v1/organization/zones/{zid}", headers=_como("ua", EMPRESA_A),
                     json={"zone_type_id": ZT_A})
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "ZONE_NOT_FOUND"


def test_c20_patch_ubicacion_version_conflict_antes_que_tipo():
    wh = _almacen("ua", EMPRESA_A, "C20")
    r = CLIENT.post("/api/v1/organization/locations", headers=_como("ua", EMPRESA_A), json={
        "warehouse_id": wh["id"], "code": "L-C20", "location_type_id": LT_A})
    assert r.status_code == 200, r.text
    lid = r.json()["id"]

    headers = _como("ua", EMPRESA_A)
    headers["If-Match"] = "999"
    r = CLIENT.patch(f"/api/v1/organization/locations/{lid}", headers=headers,
                     json={"location_type_id": LT_B})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "VERSION_CONFLICT"
    assert _ubicacion_tipo(lid) == LT_A


def test_c22_ubicacion_sin_code_con_lt_b_422_location_code_required():
    wh = _almacen("ua", EMPRESA_A, "C22", code_policy="MANUAL")
    r = CLIENT.post("/api/v1/organization/locations", headers=_como("ua", EMPRESA_A), json={
        "warehouse_id": wh["id"], "location_type_id": LT_B})
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "LOCATION_CODE_REQUIRED"
    assert _cuenta(WarehouseLocation, warehouse_id=wh["id"]) == 0


def test_c22b_bulk_pattern_invalido_con_lt_b_422():
    wh = _almacen("ua", EMPRESA_A, "C22B")
    r = CLIENT.post("/api/v1/organization/locations/bulk", headers=_como("ua", EMPRESA_A), json={
        "warehouse_id": wh["id"], "pattern": "{x}", "count": 1,
        "preview": False, "location_type_id": LT_B})
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "LOCATION_PATTERN_INVALID"
    assert _cuenta(WarehouseLocation, warehouse_id=wh["id"]) == 0


def test_c23_almacen_sin_tramos_zonas_con_zt_b_422():
    wh = _almacen("ua", EMPRESA_A, "C23")
    r = CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones",
                    headers=_como("ua", EMPRESA_A), json={
                        "code": "Z-C23", "name": "Zona", "zone_type_id": ZT_B})
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "STRUCTURE_LEVEL_DISABLED"
    assert _cuenta(WarehouseZone, warehouse_id=wh["id"]) == 0


def test_c24_uab_en_b_ubicacion_con_lt_b_ok():
    wh = _almacen("uab", EMPRESA_B, "C24")
    r = CLIENT.post("/api/v1/organization/locations", headers=_como("uab", EMPRESA_B), json={
        "warehouse_id": wh["id"], "code": "L-C24", "location_type_id": LT_B})
    assert r.status_code == 200, r.text
    assert _ubicacion_tipo(r.json()["id"]) == LT_B


def test_c25_uab_en_a_con_lt_b_404():
    wh = _almacen("uab", EMPRESA_A, "C25")
    r = CLIENT.post("/api/v1/organization/locations", headers=_como("uab", EMPRESA_A), json={
        "warehouse_id": wh["id"], "code": "L-C25", "location_type_id": LT_B})
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "LOCATION_TYPE_NOT_FOUND"
    assert _cuenta(WarehouseLocation, warehouse_id=wh["id"], code="L-C25") == 0


def test_c28_contrato_ast_de_warehouse_api():
    ruta = Path(__file__).resolve().parents[1] / "app" / "modules" / "organization" / "warehouse_api.py"
    arbol = ast.parse(ruta.read_text())

    funcion = next(
        nodo for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef)
        and nodo.name == "_exige_tipo_propio"
    )
    assert isinstance(funcion, ast.FunctionDef | ast.AsyncFunctionDef)
    codigo_funcion = ast.unparse(funcion)
    assert ".company_id" in codigo_funcion
    assert "ctx.company_id" in codigo_funcion

    llama_en = {}

    for nombre in ["create_location_full", "bulk_locations", "patch_location"]:
        funcion_obj = next(
            nodo for nodo in arbol.body
            if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef)
            and nodo.name == nombre
        )
        llama_en[nombre] = any(
            isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Name)
            and nodo.func.id == "_exige_tipo_propio"
            for nodo in ast.walk(funcion_obj)
        )
        if nombre == "patch_location":
            llama_en_patch_if = False
            for nodo in ast.walk(funcion_obj):
                if not isinstance(nodo, ast.If):
                    continue
                test = ast.unparse(nodo.test)
                if "location_type_id" not in test or "model_fields_set" not in test:
                    continue
                for hijo in ast.walk(nodo):
                    if (
                        isinstance(hijo, ast.Call)
                        and isinstance(hijo.func, ast.Name)
                        and hijo.func.id == "_exige_tipo_propio"
                    ):
                        llama_en_patch_if = True
            assert llama_en_patch_if

    assert llama_en["create_location_full"]
    assert llama_en["bulk_locations"]
    assert llama_en["patch_location"]

    for nombre in ["_create", "_patch"]:
        nodo_funcion = next(
            nodo for nodo in ast.walk(arbol)
            if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef)
            and nodo.name == nombre
            and nodo.col_offset > 0
        )
        hay_if_zone = False
        for nodo in ast.walk(nodo_funcion):
            if not isinstance(nodo, ast.If):
                continue
            if "zone" not in ast.unparse(nodo.test):
                continue
            hay_if_zone = hay_if_zone or any(
                isinstance(hijo, ast.Call)
                and isinstance(hijo.func, ast.Name)
                and hijo.func.id == "_exige_tipo_propio"
                for hijo in ast.walk(nodo)
            )
        assert hay_if_zone


def test_c29_orden_por_ast():
    ruta = Path(__file__).resolve().parents[1] / "app" / "modules" / "organization" / "warehouse_api.py"
    arbol = ast.parse(ruta.read_text())

    def _indice_llamada(nodos) -> int | None:
        for idx, nodo in enumerate(nodos):
            if (
                isinstance(nodo, ast.Expr)
                and isinstance(nodo.value, ast.Call)
                and isinstance(nodo.value.func, ast.Name)
                and nodo.value.func.id == "_exige_tipo_propio"
            ):
                return idx
        return None

    crear = next(
        nodo for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef)
        and nodo.name == "create_location_full"
    )
    llamada = _indice_llamada(crear.body)
    asignacion_location = next(
        idx for idx, nodo in enumerate(crear.body)
        if isinstance(nodo, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "location" for t in nodo.targets)
    )
    assert llamada is not None
    assert llamada < asignacion_location

    bulk = next(
        nodo for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef)
        and nodo.name == "bulk_locations"
    )
    llamada = _indice_llamada(bulk.body)
    if_preview = next(
        idx for idx, nodo in enumerate(bulk.body)
        if isinstance(nodo, ast.If) and "body.preview" in ast.unparse(nodo.test)
    )
    assert llamada is not None
    assert llamada < if_preview

    patch = next(
        nodo for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef)
        and nodo.name == "patch_location"
    )
    if_model_fields = next(
        idx for idx, nodo in enumerate(patch.body)
        if isinstance(nodo, ast.If) and "model_fields_set" in ast.unparse(nodo.test)
    )
    if_structural = next(
        idx for idx, nodo in enumerate(patch.body)
        if isinstance(nodo, ast.If) and "structural" in ast.unparse(nodo.test)
    )
    assert if_model_fields < if_structural

    crear_nodo = next(
        nodo for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef)
        and nodo.name == "_create"
        and nodo.col_offset > 0
    )
    crear_ifs = [idx for idx, nodo in enumerate(crear_nodo.body) if isinstance(nodo, ast.If)]
    indice_if_zone = next(
        idx for idx in crear_ifs
        if "zone" in ast.unparse(crear_nodo.body[idx].test)
        and any(
            isinstance(hijo, ast.Call)
            and isinstance(hijo.func, ast.Name)
            and hijo.func.id == "_exige_tipo_propio"
            for hijo in ast.walk(crear_nodo.body[idx])
        )
    )
    indice_node = next(
        idx for idx, nodo in enumerate(crear_nodo.body)
        if isinstance(nodo, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "node" for t in nodo.targets)
    )
    assert indice_if_zone < indice_node

    patch_nodo = next(
        nodo for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef)
        and nodo.name == "_patch"
        and nodo.col_offset > 0
    )
    if_zone_type = next(
        idx for idx, nodo in enumerate(patch_nodo.body)
        if isinstance(nodo, ast.If) and "zone_type_id" in ast.unparse(nodo.test)
    )
    for_data = next(
        idx for idx, nodo in enumerate(patch_nodo.body)
        if isinstance(nodo, ast.For) and "data.items()" in ast.unparse(nodo.iter)
    )
    assert if_zone_type < for_data
