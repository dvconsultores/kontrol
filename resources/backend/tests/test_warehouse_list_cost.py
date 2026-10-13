"""WHL · El listado de almacenes dice lo mismo que el detalle, y no cuesta más por fila.

`GET /organization/warehouses` preguntaba a la base una docena de veces por cada almacén
para saber si se puede borrar, en qué régimen está y qué acciones ofrece. Las pantallas que
llenan un desplegable con el listado entero pagaban eso por cada almacén de la empresa
(FR-054-E2EFLK-002..005).

Dos cosas se comprueban aquí. Que el listado, que ahora cuenta las dependencias de toda la
página de una vez, responde por cada almacén exactamente lo que responde su detalle, que
sigue preguntando por separado: el detalle es el oráculo. Y que el número de sentencias de
una página no depende de cuántos almacenes trae.

Sobre PostgreSQL cuando `KONTROL_TEST_DB_URL` lo indica (P21).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db, init_models
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Permission, Role, RolePermission, UserRole, UserScope
from app.modules.inventory.models import InventoryMovement, MovementType
from app.modules.master_data.models import CatalogItem
from app.modules.organization import structure as st
from app.modules.organization.models import (
    Company,
    Installation,
    Tenant,
    Warehouse,
    WarehouseLocation,
)
from app.modules.setup.api import SetupRequest, _bootstrap_roles, initialize
from tests.conftest import make_engine

PASSWORD = "Kontrol2026Segura!"
API = "/api/v1/organization"
TABLAS_DE_DEPENDENCIAS = (
    "warehouse_zones", "warehouse_aisles", "warehouse_racks", "warehouse_levels",
    "warehouse_locations", "inventory_movements",
)
LOTE = 40

_CLIENT: TestClient
_FACTORY: sessionmaker
_ENGINE: Engine
_EMPRESA: str
_MUNDO: dict[str, str]


def _login(tenant: str, username: str) -> dict[str, str]:
    r = _CLIENT.post("/api/v1/auth/login", json={
        "tenant_code": tenant, "username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _admin() -> dict[str, str]:
    return _login("DEMO", "admin")


def _crear(codigo: str, tramos: dict[str, bool] | None = None) -> str:
    r = _CLIENT.post(f"{API}/warehouses", headers=_admin(), json={
        "company_id": _EMPRESA, "code": codigo, "name": f"Almacén {codigo}",
        "structure_levels": tramos or {}})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _nodo(almacen: str, tramo: str, codigo: str, padre: str | None = None) -> str:
    r = _CLIENT.post(f"{API}/warehouses/{almacen}/{tramo}s", headers=_admin(),
                     json={"code": codigo, "name": codigo, "parent_id": padre})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _ubicacion(almacen: str, codigo: str, **padres: str) -> str:
    r = _CLIENT.post(f"{API}/locations", headers=_admin(),
                     json={"warehouse_id": almacen, "code": codigo, **padres})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _movimiento(db: Session, almacen: str, ubicacion: str | None = None) -> None:
    tipo = db.execute(select(MovementType).limit(1)).scalars().first()
    if tipo is None:
        tipo = MovementType(code="ENT", name="Entrada", direction="IN",
                            affects_balance=True, status="ACTIVE")
        db.add(tipo)
        db.flush()
    producto = db.execute(select(CatalogItem).limit(1)).scalars().first()
    if producto is None:
        producto = CatalogItem(company_id=_EMPRESA, code="P-WHL", name="Producto",
                               item_type="PRODUCT", status="ACTIVE")
        db.add(producto)
        db.flush()
    db.add(InventoryMovement(
        company_id=_EMPRESA, warehouse_id=almacen, location_id=ubicacion,
        product_id=str(producto.id), movement_type_id=str(tipo.id), quantity=10.0,
        currency="VED", occurred_at=datetime.now(UTC), target_state="DISPONIBLE"))


def _usuario(db: Session, tenant_id: str, username: str, permisos: set[str]) -> None:
    """Usuario de la empresa con un rol que solo lleva `permisos`."""
    usuario = identity_service.create_user(
        db, tenant_id=tenant_id, username=username, email=f"{username}@demo.test",
        password=PASSWORD, must_change_password=False, created_by=None)
    rol = Role(code=f"WHL-{username}".upper(), name=f"WHL {username}", protected=False, status="ACTIVE")
    db.add(rol)
    db.flush()
    concedidos = set()
    for p in db.query(Permission).all():
        if f"{p.resource}:{p.action}" in permisos:
            db.add(RolePermission(role_id=str(rol.id), permission_id=str(p.id)))
            concedidos.add(f"{p.resource}:{p.action}")
    assert concedidos == permisos, "el catálogo de permisos no trae alguno de los pedidos"
    db.add(UserRole(user_id=str(usuario.id), role_id=str(rol.id), company_id=None))
    db.add(UserScope(user_id=str(usuario.id), company_id=_EMPRESA))


def _otro_tenant(db: Session) -> None:
    """Otra empresa, de otro tenant, con un almacén que tiene de todo."""
    instalacion = db.execute(select(Installation).limit(1)).scalars().one()
    tenant = Tenant(installation_id=str(instalacion.id), code="OTRA", name="Otra Empresa",
                    plan="MONO_COMPANY", status="ACTIVE")
    db.add(tenant)
    db.flush()
    db.add(Company(tenant_id=str(tenant.id), code="O1", legal_name="Otra C.A.",
                   rif="J-98765432-1", legal_type="CA", functional_currency="VED", status="ACTIVE"))
    usuario = identity_service.create_user(db, tenant_id=str(tenant.id), username="admin2",
                                           email="admin2@otra.com", password=PASSWORD, created_by=None)
    rol = _bootstrap_roles(db, str(tenant.id), str(usuario.id))
    db.add(UserRole(user_id=str(usuario.id), role_id=str(rol.id), company_id=None))


def _poblar() -> dict[str, str]:
    """Un almacén por cada estado que cambia lo que el listado dice de él.

    Los que llevan `-HEREDADO` tienen filas escritas sin pasar por la API: el régimen
    guardado sigue en `INITIAL` aunque ya haya estructura, que es como quedan los datos
    anteriores a que el régimen se promoviera al crear el primer nodo.
    """
    mundo = {
        "VACIO": _crear("WHL-VACIO"),
        "TRAMOS": _crear("WHL-TRAMOS", {"zone": True, "rack": True}),
        "INACTIVO": _crear("WHL-INACTIVO"),
        "UBICACION": _crear("WHL-UBICACION"),
        "ZONA": _crear("WHL-ZONA", {"zone": True}),
        "COMPLETO": _crear("WHL-COMPLETO", {"zone": True, "aisle": True, "rack": True, "level": True}),
        "MOVIMIENTOS": _crear("WHL-MOVIMIENTOS"),
        "OPERATIVO-GUARDADO": _crear("WHL-OPERATIVO-GUARDADO", {"zone": True}),
        "UBICACION-HEREDADO": _crear("WHL-UBICACION-HEREDADO"),
        **{f"{tramo.upper()}-HEREDADO": _crear(f"WHL-{tramo.upper()}-HEREDADO") for tramo in st.LEVEL_MODEL},
    }
    r = _CLIENT.post(f"{API}/warehouses/{mundo['INACTIVO']}/deactivate", headers=_admin())
    assert r.status_code == 200, r.text
    _ubicacion(mundo["UBICACION"], "U-1")
    _ubicacion(mundo["UBICACION"], "U-2")
    _nodo(mundo["ZONA"], "zone", "Z-1")
    completo = mundo["COMPLETO"]
    zona = _nodo(completo, "zone", "Z-1")
    pasillo = _nodo(completo, "aisle", "P-1", zona)
    rack = _nodo(completo, "rack", "R-1", pasillo)
    nivel = _nodo(completo, "level", "N-1", rack)
    _nodo(completo, "level", "N-2", rack)
    en_completo = _ubicacion(completo, "C-1", zone_id=zona, aisle_id=pasillo, rack_id=rack, level_id=nivel)
    for i in range(LOTE):
        _crear(f"LOTE-{i:03d}")

    with _FACTORY() as db:
        _movimiento(db, completo, en_completo)
        _movimiento(db, mundo["MOVIMIENTOS"])
        _movimiento(db, mundo["MOVIMIENTOS"])
        db.get(Warehouse, mundo["OPERATIVO-GUARDADO"]).structure_regime = st.REGIME_OPERATIONAL
        db.add(WarehouseLocation(company_id=_EMPRESA, warehouse_id=mundo["UBICACION-HEREDADO"], code="H-1"))
        for tramo, modelo in st.LEVEL_MODEL.items():
            db.add(modelo(company_id=_EMPRESA, warehouse_id=mundo[f"{tramo.upper()}-HEREDADO"],
                          code="H-1", name="Heredado"))
        _usuario(db, db.get(Company, _EMPRESA).tenant_id, "visor", {"organization:view"})
        _usuario(db, db.get(Company, _EMPRESA).tenant_id, "editor",
                 {"organization:view", "organization:edit", "organization:delete"})
        _otro_tenant(db)
        db.commit()

    ajeno = _login("OTRA", "admin2")
    empresa_ajena = _CLIENT.get(f"{API}/companies", headers=ajeno).json()["items"][0]["id"]
    r = _CLIENT.post(f"{API}/warehouses", headers=ajeno, json={
        "company_id": empresa_ajena, "code": "WHL-AJENO", "name": "Almacén ajeno", "structure_levels": {}})
    assert r.status_code == 200, r.text
    mundo["AJENO"] = r.json()["id"]
    r = _CLIENT.post(f"{API}/locations", headers=ajeno, json={"warehouse_id": mundo["AJENO"], "code": "A-1"})
    assert r.status_code == 200, r.text
    return mundo


@pytest.fixture(scope="module", autouse=True)
def _app_client():
    global _CLIENT, _FACTORY, _ENGINE, _EMPRESA, _MUNDO
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    import app.core.database as dm

    dm._engine = engine  # type: ignore[attr-defined]
    dm._SessionLocal = factory  # type: ignore[attr-defined]

    with factory() as db:
        initialize(db, SetupRequest(
            tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1",
            company_legal_name="Demo C.A.", company_rif="J-12345678-9",
            admin_username="admin", admin_password=PASSWORD,
        ))

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
    _ENGINE = engine
    _CLIENT = TestClient(app)
    _EMPRESA = _CLIENT.get(f"{API}/companies", headers=_admin()).json()["items"][0]["id"]
    _MUNDO = _poblar()
    yield _CLIENT


@contextmanager
def sentencias() -> Iterator[list[tuple[str, list[Any]]]]:
    """Las sentencias que llegan a la base mientras dura el bloque, con sus parámetros."""
    vistas: list[tuple[str, list[Any]]] = []

    def anotar(conn, cursor, statement, parameters, context, executemany):
        valores = parameters.values() if isinstance(parameters, dict) else parameters
        vistas.append((statement, list(valores or [])))

    event.listen(_ENGINE, "before_cursor_execute", anotar)
    try:
        yield vistas
    finally:
        event.remove(_ENGINE, "before_cursor_execute", anotar)


def _listar(cabeceras: dict[str, str], consulta: str) -> dict[str, Any]:
    r = _CLIENT.get(f"{API}/warehouses?{consulta}", headers=cabeceras)
    assert r.status_code == 200, r.text
    return r.json()


def _detalle(cabeceras: dict[str, str], almacen: str) -> dict[str, Any]:
    r = _CLIENT.get(f"{API}/warehouses/{almacen}", headers=cabeceras)
    assert r.status_code == 200, r.text
    return r.json()


def _de(tabla: str, vistas: list[tuple[str, list[Any]]]) -> list[list[Any]]:
    return [parametros for sentencia, parametros in vistas if f"FROM {tabla}" in sentencia]


# ---------------------------------------------------------------- WHL-01
def test_whl_01_cada_item_del_listado_es_igual_al_detalle_del_almacen():
    h = _admin()
    listado = {item["id"]: item for item in _listar(h, "q=WHL-&limit=100")["items"]}
    propios = {clave: almacen for clave, almacen in _MUNDO.items() if clave != "AJENO"}
    assert set(listado) == set(propios.values())
    for clave, almacen in propios.items():
        assert listado[almacen] == _detalle(h, almacen), clave


def test_whl_01_el_mundo_cubre_los_estados_que_cambian_la_respuesta():
    """La paridad no vale nada sobre almacenes iguales: aquí se fija, a mano, lo que el
    listado tiene que decir de cada estado."""
    items = {item["code"]: item for item in _listar(_admin(), "q=WHL-&limit=100")["items"]}

    def resumen(codigo: str) -> tuple[bool, dict[str, int] | None, str, list[str]]:
        item = items[f"WHL-{codigo}"]
        return item["can_delete"], item["delete_blocked_by"], item["structure_regime"], item["allowed_actions"]

    assert resumen("VACIO") == (True, None, "INITIAL",
                                ["edit", "deactivate", "manage_structure", "add_location", "delete"])
    assert resumen("TRAMOS") == (True, None, "INITIAL", [
        "edit", "deactivate", "manage_structure", "add_zone", "add_rack", "add_location", "delete"])
    assert resumen("INACTIVO") == (True, None, "INITIAL",
                                   ["edit", "activate", "manage_structure", "add_location", "delete"])
    assert resumen("UBICACION") == (False, {"locations": 2}, "OPERATIONAL", ["edit", "deactivate", "add_location"])
    assert resumen("ZONA") == (False, {"zone": 1}, "OPERATIONAL",
                               ["edit", "deactivate", "add_zone", "add_location"])
    assert resumen("COMPLETO") == (
        False, {"zone": 1, "aisle": 1, "rack": 1, "level": 2, "locations": 1, "movements": 1}, "OPERATIONAL",
        ["edit", "deactivate", "add_zone", "add_aisle", "add_rack", "add_level", "add_location"])
    assert resumen("MOVIMIENTOS") == (False, {"movements": 2}, "INITIAL",
                                      ["edit", "deactivate", "manage_structure", "add_location"])
    assert resumen("OPERATIVO-GUARDADO") == (True, None, "OPERATIONAL",
                                             ["edit", "deactivate", "add_zone", "add_location", "delete"])
    assert resumen("UBICACION-HEREDADO") == (False, {"locations": 1}, "OPERATIONAL",
                                             ["edit", "deactivate", "add_location"])
    for tramo in st.LEVEL_MODEL:
        assert resumen(f"{tramo.upper()}-HEREDADO") == (
            False, {tramo: 1}, "OPERATIONAL", ["edit", "deactivate", "add_location"]), tramo


def test_whl_01_la_paridad_se_mantiene_pagina_a_pagina():
    """Una página corta trae almacenes con dependencias junto a otros que no las tienen."""
    h = _admin()
    vistos: list[str] = []
    for offset in range(0, len(_MUNDO) - 1, 3):
        pagina = _listar(h, f"q=WHL-&limit=3&offset={offset}")["items"]
        assert 1 <= len(pagina) <= 3
        for item in pagina:
            assert item == _detalle(h, item["id"]), item["code"]
            vistos.append(item["id"])
    assert sorted(vistos) == sorted(a for clave, a in _MUNDO.items() if clave != "AJENO")


# ---------------------------------------------------------------- WHL-02
@pytest.mark.parametrize("username, esperadas_en_vacio, esperadas_con_ubicacion", [
    ("visor", [], []),
    ("editor", ["edit", "delete"], ["edit"]),
])
def test_whl_02_las_acciones_se_recortan_a_los_permisos_de_quien_pregunta(
        username, esperadas_en_vacio, esperadas_con_ubicacion):
    h = _login("DEMO", username)
    listado = {item["id"]: item for item in _listar(h, "q=WHL-&limit=100")["items"]}
    assert listado[_MUNDO["VACIO"]]["allowed_actions"] == esperadas_en_vacio
    assert listado[_MUNDO["UBICACION"]]["allowed_actions"] == esperadas_con_ubicacion
    for clave, almacen in _MUNDO.items():
        if clave != "AJENO":
            assert listado[almacen] == _detalle(h, almacen), clave
    # Lo demás no depende de quién pregunta.
    del_admin = {item["id"]: item for item in _listar(_admin(), "q=WHL-&limit=100")["items"]}
    for almacen, item in listado.items():
        for campo in ("can_delete", "delete_blocked_by", "structure_regime"):
            assert item[campo] == del_admin[almacen][campo]


# ---------------------------------------------------------------- WHL-03
def test_whl_03_una_pagina_de_cuarenta_cuesta_las_mismas_sentencias_que_una_de_tres():
    h = _admin()
    with sentencias() as de_tres:
        assert len(_listar(h, "q=LOTE-&limit=3")["items"]) == 3
    with sentencias() as de_cuarenta:
        assert len(_listar(h, f"q=LOTE-&limit={LOTE}")["items"]) == LOTE
    assert len(de_cuarenta) == len(de_tres)


def test_whl_03_tampoco_cuesta_mas_cuando_los_almacenes_tienen_dependencias():
    h = _admin()
    with sentencias() as de_uno:
        assert len(_listar(h, "q=WHL-COMPLETO&limit=5")["items"]) == 1
    with sentencias() as de_todos:
        assert len(_listar(h, "q=WHL-&limit=100")["items"]) == len(_MUNDO) - 1
    assert len(de_todos) == len(de_uno)


# ---------------------------------------------------------------- WHL-04
def test_whl_04_cada_tabla_de_dependencias_se_consulta_una_vez_por_pagina():
    with sentencias() as vistas:
        pagina = _listar(_admin(), "q=WHL-&limit=100")["items"]
    assert len(pagina) > 10
    for tabla in TABLAS_DE_DEPENDENCIAS:
        assert len(_de(tabla, vistas)) == 1, tabla


# ---------------------------------------------------------------- WHL-05
def test_whl_05_el_listado_no_trae_almacenes_de_otra_empresa():
    propios = _listar(_admin(), "limit=100")
    assert _MUNDO["AJENO"] not in {item["id"] for item in propios["items"]}
    assert propios["total"] == len(_MUNDO) - 1 + LOTE == len(propios["items"])

    ajenos = _listar(_login("OTRA", "admin2"), "limit=100")
    assert [item["id"] for item in ajenos["items"]] == [_MUNDO["AJENO"]]
    assert ajenos["items"][0]["delete_blocked_by"] == {"locations": 1}


def test_whl_05_las_cuentas_solo_preguntan_por_los_almacenes_de_la_pagina():
    with sentencias() as vistas:
        pagina = _listar(_admin(), "q=WHL-&limit=4&offset=2")["items"]
    de_la_pagina = {item["id"] for item in pagina}
    assert len(de_la_pagina) == 4
    for tabla in TABLAS_DE_DEPENDENCIAS:
        (parametros,) = _de(tabla, vistas)
        assert set(parametros) == de_la_pagina, tabla


# ---------------------------------------------------------------- WHL-06
@pytest.mark.parametrize("consulta, total", [("q=NO-EXISTE-NINGUNO", 0), (f"q=LOTE-&offset={LOTE}", LOTE)])
def test_whl_06_una_pagina_vacia_no_pregunta_por_dependencias(consulta, total):
    with sentencias() as vistas:
        cuerpo = _listar(_admin(), consulta)
    assert cuerpo["items"] == [] and cuerpo["total"] == total
    for tabla in TABLAS_DE_DEPENDENCIAS:
        assert _de(tabla, vistas) == [], tabla


# ---------------------------------------------------------------- WHL-07
def test_whl_07_total_limite_desplazamiento_y_orden_no_cambian():
    cuerpo = _listar(_admin(), "q=LOTE-&limit=4&offset=2")
    assert (cuerpo["total"], cuerpo["limit"], cuerpo["offset"]) == (LOTE, 4, 2)
    assert [item["code"] for item in cuerpo["items"]] == ["LOTE-002", "LOTE-003", "LOTE-004", "LOTE-005"]

    por_defecto = _listar(_admin(), "q=LOTE-")
    assert (por_defecto["total"], por_defecto["limit"], por_defecto["offset"]) == (LOTE, 50, 0)
    assert [item["code"] for item in por_defecto["items"]] == [f"LOTE-{i:03d}" for i in range(LOTE)]


def test_whl_07_los_filtros_del_listado_siguen_filtrando():
    inactivos = _listar(_admin(), "status=INACTIVE&limit=100")
    assert [item["code"] for item in inactivos["items"]] == ["WHL-INACTIVO"]
    assert inactivos["total"] == 1
    assert inactivos["items"][0] == _detalle(_admin(), _MUNDO["INACTIVO"])
