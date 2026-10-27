import uuid

import pytest
from mfa_mundo import API, alta_por_desafio, crear_usuario, login, mundo_mfa
from sqlalchemy import select

from app.modules.identity_access import authority
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Role, User, UserRole, UserScope
from app.modules.organization.models import Company, Warehouse

pytest_plugins = ("mfa_apoyo",)


def _nombre():
    return uuid.uuid4().hex[:10]


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


def _actor(mundo, reloj, asignaciones):
    nombre = _nombre()
    user_id = crear_usuario(mundo, nombre)
    for role_id, company_id in asignaciones:
        _dar(mundo, user_id, role_id, company_id)
    return user_id, _entrar(mundo, reloj, nombre)


def _h(cab, empresa):
    return {**cab, "X-Kontrol-Company": empresa}


@pytest.fixture(scope="module")
def mundo():
    with mundo_mfa() as m:
        yield m


@pytest.fixture(scope="module")
def escenario(mundo):
    db = mundo.factory()
    try:
        d2 = Company(
            tenant_id=mundo.tenant_id,
            code="D2",
            legal_name="Demo Dos CA",
            rif="J-33333333-3",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        db.add(d2)
        db.commit()

        roles = {}
        definiciones = {
            "R_CSD_TAR": ["tareas:view"],
            "R_CSD_DOC": ["documentos:view"],
            "R_CSD_OV": ["organization:view"],
            "R_CSD_OE": ["organization:edit"],
            "R_CSD_MV": ["maestros:view"],
            "R_CSD_ME": ["maestros:edit", "maestros:deactivate"],
        }
        for code, permissions in definiciones.items():
            roles[code] = identity_service.create_role(
                db,
                tenant_id=mundo.tenant_id,
                code=code,
                name=code,
                company_id=None,
                permissions=permissions,
                actor=mundo.admin_id,
            )["id"]

        wh_d1 = Warehouse(
            company_id=mundo.company_id,
            code=f"CSD_D1_{_nombre()}",
            name="CSD Almacen D1",
        )
        wh_d2 = Warehouse(
            company_id=d2.id,
            code=f"CSD_D2_{_nombre()}",
            name="CSD Almacen D2",
        )
        db.add(wh_d1)
        db.add(wh_d2)
        db.commit()
    finally:
        db.close()

    return {
        "d1": mundo.company_id,
        "d2": d2.id,
        "roles": roles,
        "wh_d1": wh_d1.id,
        "wh_d2": wh_d2.id,
    }


def test_csd_01_tasks_scope_permission_denied_en_otra_empresa(mundo, reloj_mfa, escenario):
    """CSD-01: tareas:view solo en D1 no autoriza tasks en D2."""
    _, cab = _actor(mundo, reloj_mfa, [(escenario["roles"]["R_CSD_TAR"], escenario["d1"])])

    r_d1 = mundo.client.get(f"{API}/tasks?scope=all", headers=_h(cab, escenario["d1"]))
    assert r_d1.status_code == 200, r_d1.text

    r_d2 = mundo.client.get(f"{API}/tasks?scope=all", headers=_h(cab, escenario["d2"]))
    assert r_d2.status_code == 403, r_d2.text
    assert r_d2.json()["code"] == "PERMISSION_DENIED", r_d2.text


def test_csd_02_documentos_por_recurso_res_denied_en_otra_empresa(mundo, reloj_mfa, escenario):
    """CSD-02: organization:view solo en D1 no permite documentos por recurso en D2."""
    asignaciones = [
        (escenario["roles"]["R_CSD_DOC"], None),
        (escenario["roles"]["R_CSD_OV"], escenario["d1"]),
    ]
    _, cab = _actor(mundo, reloj_mfa, asignaciones)

    r_d1 = mundo.client.get(
        f"{API}/documentos/por-recurso/Warehouse/{escenario['wh_d1']}",
        headers=_h(cab, escenario["d1"]),
    )
    assert r_d1.status_code == 200, r_d1.text

    r_d2 = mundo.client.get(
        f"{API}/documentos/por-recurso/Warehouse/{escenario['wh_d2']}",
        headers=_h(cab, escenario["d2"]),
    )
    assert r_d2.status_code == 403, r_d2.text
    assert r_d2.json()["code"] == "RESOURCE_ACCESS_DENIED", r_d2.text


def test_csd_03_unidades_allowed_actions_no_edit_en_otra_empresa(mundo, reloj_mfa, escenario):
    """CSD-03: maestros:edit/deactivate solo en D1 no aparecen en allowed_actions de D2."""
    admin_nombre = _nombre()
    crear_usuario(mundo, admin_nombre, admin=True, funcional=True)
    admin_auth = _entrar(mundo, reloj_mfa, admin_nombre)

    def crear_unidad(empresa, prefijo):
        payload = {
            "code": f"{prefijo}_{_nombre()}",
            "name": f"Unidad {prefijo}",
            "symbol": f"{prefijo[:4]}",
        }
        r = mundo.client.post(
            f"{API}/maestros/unidades",
            json=payload,
            headers=_h(admin_auth, empresa),
        )
        assert r.status_code == 200, r.text
        return r.json()["id"]

    unidad_d1 = crear_unidad(escenario["d1"], "CSDD1")
    unidad_d2 = crear_unidad(escenario["d2"], "CSDD2")

    asignaciones = [
        (escenario["roles"]["R_CSD_MV"], None),
        (escenario["roles"]["R_CSD_ME"], escenario["d1"]),
    ]
    _, cab = _actor(mundo, reloj_mfa, asignaciones)

    r_d1 = mundo.client.get(f"{API}/maestros/unidades/{unidad_d1}", headers=_h(cab, escenario["d1"]))
    assert r_d1.status_code == 200, r_d1.text
    allowed_d1 = r_d1.json()["allowed_actions"]
    assert "edit" in allowed_d1, allowed_d1

    r_d2 = mundo.client.get(f"{API}/maestros/unidades/{unidad_d2}", headers=_h(cab, escenario["d2"]))
    assert r_d2.status_code == 200, r_d2.text
    allowed_d2 = r_d2.json()["allowed_actions"]
    assert "edit" not in allowed_d2, allowed_d2
    assert "deactivate" not in allowed_d2, allowed_d2


def test_csd_04_warehouses_allowed_actions_no_edit_en_otra_empresa(mundo, reloj_mfa, escenario):
    """CSD-04: organization:edit solo en D1 no aparece en allowed_actions de almacén D2."""
    asignaciones = [
        (escenario["roles"]["R_CSD_OV"], None),
        (escenario["roles"]["R_CSD_OE"], escenario["d1"]),
    ]
    _, cab = _actor(mundo, reloj_mfa, asignaciones)

    r_d1 = mundo.client.get(
        f"{API}/organization/warehouses/{escenario['wh_d1']}",
        headers=_h(cab, escenario["d1"]),
    )
    assert r_d1.status_code == 200, r_d1.text
    allowed_d1 = r_d1.json()["allowed_actions"]
    assert "edit" in allowed_d1, allowed_d1

    r_d2 = mundo.client.get(
        f"{API}/organization/warehouses/{escenario['wh_d2']}",
        headers=_h(cab, escenario["d2"]),
    )
    assert r_d2.status_code == 200, r_d2.text
    allowed_d2 = r_d2.json()["allowed_actions"]
    assert "edit" not in allowed_d2, allowed_d2


def test_csd_05_sin_acceso_a_la_empresa_no_hay_capacidades(mundo, escenario):
    """CSD-05: sin acceso a la empresa no hay capacidades aunque el rol tenga company_id nulo."""
    user_id = crear_usuario(mundo, _nombre())
    _dar(mundo, user_id, escenario["roles"]["R_CSD_TAR"], None)
    db = mundo.factory()
    try:
        db.add(UserScope(user_id=user_id, company_id=escenario["d1"]))
        db.commit()
        user = db.get(User, user_id)
        assert "tareas:view" in authority.capabilities_in_company(db, user, escenario["d1"])
        assert authority.capabilities_in_company(db, user, escenario["d2"]) == set()
    finally:
        db.close()


def test_csd_06_usuario_inactivo_no_tiene_capacidades(mundo, escenario):
    """CSD-06: un usuario inactivo no tiene capacidades."""
    user_id = crear_usuario(mundo, _nombre())
    _dar(mundo, user_id, escenario["roles"]["R_CSD_TAR"], None)
    db = mundo.factory()
    try:
        user = db.get(User, user_id)
        assert "tareas:view" in authority.capabilities_in_company(db, user, escenario["d1"])
        user.status = "INACTIVE"
        db.commit()
        db.refresh(user)
        assert authority.capabilities_in_company(db, user, escenario["d1"]) == set()
    finally:
        db.close()


def test_csd_07_asignacion_a_empresa_sin_acceso_no_cuenta(mundo, escenario):
    """CSD-07: una asignación de rol explícita a una empresa a la que el usuario no accede no cuenta."""
    user_id = crear_usuario(mundo, _nombre())
    _dar(mundo, user_id, escenario["roles"]["R_CSD_TAR"], escenario["d2"])
    db = mundo.factory()
    try:
        db.add(UserScope(user_id=user_id, company_id=escenario["d1"]))
        db.commit()
        user = db.get(User, user_id)
        assert authority.companies_with_capability(db, user, "tareas:view") == set()
        assert authority.has_capability_in_company(db, user, "tareas:view", escenario["d2"]) is False
    finally:
        db.close()


def test_csd_08_empresa_de_otro_tenant_sin_capacidades(mundo, escenario):
    """CSD-08: una empresa de otro tenant nunca aporta capacidades, aunque el rol tenga company_id nulo y sin user_scopes."""
    user_id = crear_usuario(mundo, _nombre())
    _dar(mundo, user_id, escenario["roles"]["R_CSD_TAR"], None)
    db = mundo.factory()
    try:
        ajena = (
            db.execute(select(Company.id).where(Company.tenant_id == mundo.tenant_b_id))
            .scalars()
            .first()
        )
        assert ajena is not None
        user = db.get(User, user_id)
        assert "tareas:view" in authority.capabilities_in_company(db, user, escenario["d1"])
        assert authority.capabilities_in_company(db, user, ajena) == set()
    finally:
        db.close()


def test_csd_09_rol_inactivo_no_aporta_capacidades(mundo, escenario):
    """CSD-09: un rol con status distinto de "ACTIVE" no aporta capacidades."""
    db = mundo.factory()
    try:
        rol_id = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"R_CSD_INA_{_nombre()}",
            name="R_CSD_INA",
            company_id=None,
            permissions=["tareas:view"],
            actor=mundo.admin_id,
        )["id"]
        db.commit()
        user_id = crear_usuario(mundo, _nombre())
        _dar(mundo, user_id, rol_id, None)
        user = db.get(User, user_id)
        assert "tareas:view" in authority.capabilities_in_company(db, user, escenario["d1"])
        rol = db.get(Role, rol_id)
        rol.status = "INACTIVE"
        db.commit()
        assert "tareas:view" not in authority.capabilities_in_company(db, user, escenario["d1"])
    finally:
        db.close()
