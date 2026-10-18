"""OBS-01: integridad de almacén traduciendo solo la violación única del código.

La dueña decidió que, en las cinco altas de la estructura física de almacén,
solo la violación única reconocida de la restricción del código se traduce al
409 de dominio de siempre. Cualquier otro `IntegrityError` se relanza para que
el manejador genérico devuelva el 500 `INTERNAL_ERROR` saneado.

Se ejecuta igual sobre SQLite y PostgreSQL según `KONTROL_TEST_DB_URL`.
"""

from __future__ import annotations

import ast
import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db, init_models
from app.core.integrity import es_violacion_unica, es_violacion_unica_de, restriccion_unica
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import UserScope
from app.modules.organization.models import (
    Company,
    Warehouse,
    WarehouseLocation,
    WarehouseZone,
)
from app.modules.organization.warehouse_api import (
    _UQ_ALMACEN,
    _UQ_UBICACION,
)
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine

PASSWORD = "Kontrol2026Segura!"
GENERICO = "Ocurrió un error interno. Intente nuevamente."

_CLIENT: TestClient
_FACTORY: sessionmaker
_EMPRESA: str
_TENANT_ID: str
_USUARIO_SIN_ROL: str


@pytest.fixture(scope="module", autouse=True)
def _app_client():
    global _CLIENT, _FACTORY, _EMPRESA, _TENANT_ID, _USUARIO_SIN_ROL
    engine = make_engine()
    # SQLite no activa claves foráneas por defecto: sin este PRAGMA una clave
    # foránea inexistente no produce un IntegrityError real y la prueba de 500
    # no ejercitaría el camino del manejador genérico.
    if "KONTROL_TEST_DB_URL" not in os.environ:
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
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
        admin_username="admin", admin_password=PASSWORD,
    ))
    db.close()

    db = factory()
    company = db.execute(select(Company)).scalars().first()
    _EMPRESA = str(company.id)
    _TENANT_ID = str(company.tenant_id)
    _USUARIO_SIN_ROL = str(identity_service.create_user(
        db, tenant_id=_TENANT_ID, username="sinrol", email="sinrol@o01.test",
        password=PASSWORD, created_by=None).id)
    db.add(UserScope(user_id=_USUARIO_SIN_ROL, company_id=_EMPRESA))
    db.commit()
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
    _CLIENT = TestClient(app, raise_server_exceptions=False)
    yield _CLIENT
    engine.dispose()


def _login(usuario: str = "admin") -> dict:
    r = _CLIENT.post("/api/v1/auth/login", json={
        "tenant_code": "DEMO", "username": usuario, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _cid() -> str:
    return _CLIENT.get("/api/v1/organization/companies", headers=_login()).json()["items"][0]["id"]


def _almacen(code: str, levels: dict | None = None, **extra) -> dict:
    r = _CLIENT.post("/api/v1/organization/warehouses", headers=_login(), json={
        "company_id": _cid(), "code": code, "name": f"Almacén {code}",
        "structure_levels": levels or {}, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def _cuenta(modelo, **filtros) -> int:
    db = _FACTORY()
    try:
        return db.query(modelo).filter_by(**filtros).count()
    finally:
        db.close()


def _sin_fuga(r) -> None:
    texto = r.text.lower()
    for trozo in ("constraint", "foreign", "unique", "integrity", "sqlite",
                  "psycopg", "insert", "sql", "fk_", "uq_", "traceback",
                  "warehouses", "branch_id", "location_type_id", "zone_type_id"):
        assert trozo not in texto, r.text


def test_o01_01_almacen_codigo_repetido_es_409():
    _almacen("O01-001")
    r = _CLIENT.post("/api/v1/organization/warehouses", headers=_login(), json={
        "company_id": _cid(), "code": "O01-001", "name": "Duplicado"})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "WAREHOUSE_CODE_DUPLICATE"
    assert r.json()["message"] == "Ya existe un almacén con ese código en la empresa"
    _sin_fuga(r)
    db = _FACTORY()
    rows = db.execute(select(Warehouse).where(
        Warehouse.company_id == _cid(), Warehouse.code == "O01-001")).scalars().all()
    assert len(rows) == 1
    assert rows[0].name == "Almacén O01-001"
    db.close()


def test_o01_02_ubicacion_codigo_repetido_es_409():
    wh = _almacen("O01-002")
    body = {"warehouse_id": wh["id"], "code": "L-001"}
    r = _CLIENT.post("/api/v1/organization/locations", headers=_login(), json=body)
    assert r.status_code == 200, r.text
    r = _CLIENT.post("/api/v1/organization/locations", headers=_login(), json=body)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "LOCATION_CODE_DUPLICATE"
    assert r.json()["message"] == "Ya existe una ubicación con ese código en el almacén"
    _sin_fuga(r)
    db = _FACTORY()
    rows = db.execute(select(WarehouseLocation).where(
        WarehouseLocation.warehouse_id == wh["id"],
        WarehouseLocation.code == "L-001")).scalars().all()
    assert len(rows) == 1
    db.close()


def test_o01_03_zona_codigo_repetido_es_409():
    wh = _almacen("O01-003", {"zone": True})
    r = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones",
                     headers=_login(), json={"code": "Z-1", "name": "Zona"})
    assert r.status_code == 200, r.text
    r = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones",
                     headers=_login(), json={"code": "Z-1", "name": "Zona"})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "ZONE_CODE_DUPLICATE"
    assert r.json()["message"] == "Ya existe un nodo con ese código en el almacén"
    _sin_fuga(r)


def test_o01_04_tipos_catalogo_repetidos_es_409():
    body = {"company_id": _cid(), "code": "ZT-1", "name": "Zona"}
    r = _CLIENT.post("/api/v1/organization/zone-types", headers=_login(), json=body)
    assert r.status_code == 200, r.text
    r = _CLIENT.post("/api/v1/organization/zone-types", headers=_login(), json=body)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "ZONE_TYPE_CODE_DUPLICATE"
    assert r.json()["message"] == "Ya existe un tipo con ese código en la empresa"
    _sin_fuga(r)
    body = {"company_id": _cid(), "code": "LT-1", "name": "Ubicación"}
    r = _CLIENT.post("/api/v1/organization/location-types", headers=_login(), json=body)
    assert r.status_code == 200, r.text
    r = _CLIENT.post("/api/v1/organization/location-types", headers=_login(), json=body)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "LOCATION_TYPE_CODE_DUPLICATE"
    assert r.json()["message"] == "Ya existe un tipo con ese código en la empresa"
    _sin_fuga(r)


def test_o01_05_bulk_repite_codigo_sin_marcador_es_409():
    wh = _almacen("O01-005")
    body = {"warehouse_id": wh["id"], "pattern": "O01-BULK",
            "count": 2, "preview": False}
    r = _CLIENT.post("/api/v1/organization/locations/bulk", headers=_login(), json=body)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "LOCATION_CODE_DUPLICATE"
    assert r.json()["message"] == "Otra operación creó uno de los códigos"
    _sin_fuga(r)
    assert _cuenta(WarehouseLocation, warehouse_id=wh["id"], code="O01-BULK") == 0


def test_o01_06_almacen_branch_inexistente_es_500():
    r = _CLIENT.post("/api/v1/organization/warehouses", headers=_login(), json={
        "company_id": _cid(), "code": "O01-006", "name": "FK rota",
        "branch_id": str(uuid.uuid4())})
    assert r.status_code == 500, r.text
    assert r.json()["code"] == "INTERNAL_ERROR"
    assert r.json()["message"] == GENERICO
    _sin_fuga(r)
    assert _cuenta(Warehouse, code="O01-006") == 0


def test_o01_07_ubicacion_tipo_inexistente_es_500():
    wh = _almacen("O01-007")
    r = _CLIENT.post("/api/v1/organization/locations", headers=_login(), json={
        "warehouse_id": wh["id"], "code": "L-500",
        "location_type_id": str(uuid.uuid4())})
    assert r.status_code == 500, r.text
    assert r.json()["code"] == "INTERNAL_ERROR"
    assert r.json()["message"] == GENERICO
    _sin_fuga(r)
    assert _cuenta(WarehouseLocation, warehouse_id=wh["id"], code="L-500") == 0


def test_o01_08_zona_tipo_inexistente_es_500():
    wh = _almacen("O01-008", {"zone": True})
    r = _CLIENT.post(f"/api/v1/organization/warehouses/{wh['id']}/zones",
                     headers=_login(), json={
                         "code": "Z-500", "name": "Zona",
                         "zone_type_id": str(uuid.uuid4())})
    assert r.status_code == 500, r.text
    assert r.json()["code"] == "INTERNAL_ERROR"
    assert r.json()["message"] == GENERICO
    _sin_fuga(r)
    assert _cuenta(WarehouseZone, warehouse_id=wh["id"], code="Z-500") == 0


def test_o01_09_despues_de_409_y_500_alta_prospera():
    wh = _almacen("O01-009")
    cuerpos = [
        {"warehouse_id": wh["id"], "code": "L-OK"},
        {"warehouse_id": wh["id"], "code": "L-OK"},
        {"warehouse_id": wh["id"], "code": "L-FK",
         "location_type_id": str(uuid.uuid4())},
        {"warehouse_id": wh["id"], "code": "L-OK-2"},
    ]
    r = _CLIENT.post("/api/v1/organization/locations", headers=_login(), json=cuerpos[0])
    assert r.status_code == 200, r.text
    r = _CLIENT.post("/api/v1/organization/locations", headers=_login(), json=cuerpos[1])
    assert r.status_code == 409, r.text
    r = _CLIENT.post("/api/v1/organization/locations", headers=_login(), json=cuerpos[2])
    assert r.status_code == 500, r.text
    r = _CLIENT.post("/api/v1/organization/locations", headers=_login(), json=cuerpos[3])
    assert r.status_code == 200, r.text
    assert _cuenta(WarehouseLocation, warehouse_id=wh["id"], code="L-OK") == 1
    assert _cuenta(WarehouseLocation, warehouse_id=wh["id"], code="L-FK") == 0


def test_o01_10_clasificador_errores_reales_del_motor():
    wh_creado = _almacen("O01-010")
    unica = None
    foranea = None
    not_null = None
    primaria = None
    es_pg = bool(os.environ.get("KONTROL_TEST_DB_URL"))
    for tentativa in ("unica", "foranea", "not_null", "primaria"):
        db = _FACTORY()
        try:
            if tentativa == "unica":
                db.add(Warehouse(
                    company_id=_EMPRESA, branch_id=None, code="O01-010",
                    name="Duplicado", status="ACTIVE"))
            elif tentativa == "foranea":
                db.add(Warehouse(
                    company_id=_EMPRESA, branch_id=str(uuid.uuid4()),
                    code="FK-002", name="FK", status="ACTIVE"))
            elif tentativa == "not_null":
                db.add(Warehouse(
                    company_id=_EMPRESA, branch_id=None, code="NN-002",
                    name=None, status="ACTIVE"))
            else:
                db.add(Warehouse(
                    id=wh_creado["id"], company_id=_EMPRESA, branch_id=None,
                    code="PK-002", name="PK", status="ACTIVE"))
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            if tentativa == "unica":
                unica = exc
            elif tentativa == "foranea":
                foranea = exc
            elif tentativa == "not_null":
                not_null = exc
            else:
                primaria = exc
        finally:
            db.close()
    assert unica is not None and foranea is not None and not_null is not None and primaria is not None
    assert es_violacion_unica_de(unica, _UQ_ALMACEN) is True
    assert es_violacion_unica_de(unica, _UQ_UBICACION) is False
    assert es_violacion_unica_de(foranea, _UQ_ALMACEN) is False
    assert es_violacion_unica_de(not_null, _UQ_ALMACEN) is False
    assert es_violacion_unica_de(primaria, _UQ_ALMACEN) is False
    assert es_violacion_unica(unica, "uq_warehouses_company_code") is es_pg


def test_o01_11_restriccion_unica_forma_y_errores():
    r = restriccion_unica(Warehouse.__table__, "uq_warehouses_company_code")
    assert r.name == "uq_warehouses_company_code"
    assert [c.name for c in r.columns] == ["company_id", "code"]
    with pytest.raises(LookupError):
        restriccion_unica(Warehouse.__table__, "no_existe")
    with pytest.raises(TypeError):
        restriccion_unica(select(Warehouse).subquery(), "uq_warehouses_company_code")


def test_o01_12_precedencia_http():
    _almacen("O01-012")
    r = _CLIENT.post("/api/v1/organization/warehouses", json={
        "company_id": _cid(), "code": "O01-012", "name": "Otra"})
    assert r.status_code == 401, r.text
    r = _CLIENT.post("/api/v1/organization/locations", headers=_login(), json={
        "warehouse_id": str(uuid.uuid4()), "code": "O01-012"})
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "WAREHOUSE_NOT_FOUND"


def test_o01_13_sin_rol_no_ve_409_ni_500():
    _almacen("O01-013")
    r = _CLIENT.post("/api/v1/organization/warehouses", headers=_login("sinrol"), json={
        "company_id": _cid(), "code": "O01-013", "name": "Sin rol"})
    assert r.status_code == 403, r.text


def test_o01_14_contrato_estatico_warehouse_api():
    ruta = Path(__file__).resolve().parents[1] / "app" / "modules" / "organization" / "warehouse_api.py"
    arbol = ast.parse(ruta.read_text())
    assert not any(isinstance(n, ast.FunctionDef) and n.name == "_integrity" for n in arbol.body)
    count = 0
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.ExceptHandler):
            continue
        if isinstance(nodo.type, ast.Name) and nodo.type.id == "IntegrityError":
            count += 1
            sentencias = nodo.body
            assert isinstance(sentencias[0], ast.Expr) and isinstance(sentencias[0].value, ast.Call) and getattr(sentencias[0].value.func, "attr", None) == "rollback"
            assert isinstance(sentencias[1], ast.If)
            assert isinstance(sentencias[1].test, ast.UnaryOp) and isinstance(sentencias[1].test.op, ast.Not)
            assert isinstance(sentencias[1].test.operand, ast.Call) and isinstance(sentencias[1].test.operand.func, ast.Name) and sentencias[1].test.operand.func.id == "es_violacion_unica_de"
            assert len(sentencias[1].body) == 1 and isinstance(sentencias[1].body[0], ast.Raise) and sentencias[1].body[0].exc is None
            assert isinstance(sentencias[-1], ast.Raise)
            assert isinstance(sentencias[-1].exc, ast.Call) and isinstance(sentencias[-1].exc.func, ast.Name) and sentencias[-1].exc.func.id == "ConflictError"
    assert count == 5
    for nodo in ast.walk(arbol):
        assert not (isinstance(nodo, ast.ExceptHandler) and (
            nodo.type is None
            or (isinstance(nodo.type, ast.Name) and nodo.type.id in ("Exception", "BaseException"))
        ))
