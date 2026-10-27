import uuid

import pytest
from mfa_mundo import API, alta_por_desafio, crear_usuario, eventos, mundo_mfa
from sqlalchemy import select

from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import UserRole, UserScope
from app.modules.organization.models import Company

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


def _quitar(mundo, user_id, role_id):
    db = mundo.factory()
    try:
        for row in db.execute(
            select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        ).scalars():
            db.delete(row)
        db.commit()
    finally:
        db.close()


def _alcance(mundo, user_id, company_id):
    db = mundo.factory()
    try:
        db.add(UserScope(user_id=user_id, company_id=company_id))
        db.commit()
    finally:
        db.close()


def _actor(mundo, reloj, asignaciones):
    nombre = _nombre()
    user_id = crear_usuario(mundo, nombre)
    for role_id, company_id in asignaciones:
        _dar(mundo, user_id, role_id, company_id)
    auth = alta_por_desafio(mundo.client, reloj, nombre)
    return user_id, auth.cabeceras


def _h(cab, empresa):
    return {**cab, "X-Kontrol-Company": empresa}


def _negaciones(mundo, actor_id):
    return [e for e in eventos(mundo, "COMPANY_SCOPE_DENIED") if e.user_id == actor_id]


def _todo_el_tenant(mundo, reloj):
    nombre = _nombre()
    user_id = crear_usuario(mundo, nombre, admin=True, funcional=True)
    auth = alta_por_desafio(mundo.client, reloj, nombre)
    return user_id, auth.cabeceras


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
            rif="J-11111111-1",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        db.add(d2)
        db.commit()
        d2_id = d2.id

        rol = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code="R_CSA",
            name="Rol CSA",
            company_id=None,
            permissions=[
                "maestros:view",
                "maestros:create",
                "maestros:deactivate",
                "ventas:view",
                "tesoreria:view",
                "reportes:export",
            ],
            actor=mundo.admin_id,
        )["id"]

        roles = {r["code"]: r["id"] for r in identity_service.list_roles(db)}
        return {
            "d1": mundo.company_id,
            "d2": d2_id,
            "rol": rol,
            "fc": roles["FUNCIONAL_COMPLETO"],
            "admin_rol": roles["ADMIN"],
        }
    finally:
        db.close()


def test_csa_01_permiso_de_d1_no_vale_en_d2(mundo, reloj_mfa, escenario):
    """CSA-01: un permiso asignado en D1 solo autoriza en D1."""
    actor_id, cab = _actor(mundo, reloj_mfa, [(escenario["rol"], escenario["d1"])])
    r = mundo.client.get(
        f"{API}/maestros/unidades",
        headers=_h(cab, escenario["d1"]),
    )
    assert r.status_code == 200, r.text
    r = mundo.client.get(
        f"{API}/maestros/unidades",
        headers=_h(cab, escenario["d2"]),
    )
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "COMPANY_SCOPE_FORBIDDEN", r.text
    negaciones = _negaciones(mundo, actor_id)
    assert len(negaciones) == 1, negaciones
    assert negaciones[0].reason == "COMPANY_SCOPE_FORBIDDEN"
    assert negaciones[0].evidence == {"capability": "maestros:view", "company_id": escenario["d2"]}


def test_csa_02_creacion_solo_en_empresa_con_autoridad(mundo, reloj_mfa, escenario):
    """CSA-02: una creación rechazada por alcance no afecta a la base."""
    actor_id, cab = _actor(mundo, reloj_mfa, [(escenario["rol"], escenario["d1"])])
    code = f"U{_nombre().upper()}"
    r = mundo.client.post(
        f"{API}/maestros/unidades",
        headers=_h(cab, escenario["d1"]),
        json={"code": code, "name": code, "symbol": "u"},
    )
    assert r.status_code == 200, r.text

    code2 = f"V{_nombre().upper()}"
    r = mundo.client.post(
        f"{API}/maestros/unidades",
        headers=_h(cab, escenario["d2"]),
        json={"code": code2, "name": code2, "symbol": "v"},
    )
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "COMPANY_SCOPE_FORBIDDEN", r.text

    _, cab_admin = _todo_el_tenant(mundo, reloj_mfa)
    r = mundo.client.get(
        f"{API}/maestros/unidades",
        headers=_h(cab_admin, escenario["d2"]),
    )
    assert r.status_code == 200, r.text
    assert code2 not in [item["code"] for item in r.json()["items"]]


def test_csa_03_desactivacion_rechazada_no_cambia_estado(mundo, reloj_mfa, escenario):
    """CSA-03: una desactivación sin autoridad en D2 deja la unidad activa."""
    _, cab_admin = _todo_el_tenant(mundo, reloj_mfa)
    code = f"W{_nombre().upper()}"
    r = mundo.client.post(
        f"{API}/maestros/unidades",
        headers=_h(cab_admin, escenario["d2"]),
        json={"code": code, "name": code, "symbol": "w"},
    )
    assert r.status_code == 200, r.text
    unidad_id = r.json()["id"]

    actor_id, cab = _actor(mundo, reloj_mfa, [(escenario["rol"], escenario["d1"])])
    r = mundo.client.post(
        f"{API}/maestros/unidades/{unidad_id}/deactivate",
        headers=_h(cab, escenario["d2"]),
    )
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "COMPANY_SCOPE_FORBIDDEN", r.text

    r = mundo.client.get(
        f"{API}/maestros/unidades",
        headers=_h(cab_admin, escenario["d2"]),
    )
    assert r.status_code == 200, r.text
    unidad = next(item for item in r.json()["items"] if item["id"] == unidad_id)
    assert unidad["status"] == "ACTIVE", r.text


def test_csa_04_picking_y_tesoreria_respetan_empresa(mundo, reloj_mfa, escenario):
    """CSA-04: rutas de ventas y tesorería aplican el alcance por empresa."""
    _, cab = _actor(mundo, reloj_mfa, [(escenario["rol"], escenario["d1"])])
    for path in ("/sales/picking/cola", "/treasury/fx-policies"):
        r = mundo.client.get(f"{API}{path}", headers=_h(cab, escenario["d2"]))
        assert r.status_code == 403, r.text
        assert r.json()["code"] == "COMPANY_SCOPE_FORBIDDEN", r.text
        r = mundo.client.get(f"{API}{path}", headers=_h(cab, escenario["d1"]))
        assert r.status_code == 200, r.text


def test_csa_05_reporting_pasa_autoridad_antes_de_recurso(mundo, reloj_mfa, escenario):
    """CSA-05: con autoridad responde 404 REPORT_NOT_FOUND; sin ella, alcance."""
    _, cab = _actor(mundo, reloj_mfa, [(escenario["rol"], escenario["d1"])])
    body = {"report_key": "no-existe", "format": "CSV"}
    r = mundo.client.post(f"{API}/reporting/exports", headers=_h(cab, escenario["d1"]), json=body)
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "REPORT_NOT_FOUND", r.text
    r = mundo.client.post(f"{API}/reporting/exports", headers=_h(cab, escenario["d2"]), json=body)
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "COMPANY_SCOPE_FORBIDDEN", r.text


def test_csa_06_funcional_completo_en_d1_solo_vale_en_d1(mundo, reloj_mfa, escenario):
    """CSA-06: FUNCIONAL_COMPLETO asignado en D1 no vale en D2."""
    nombre = _nombre()
    user_id = crear_usuario(mundo, nombre)
    _dar(mundo, user_id, escenario["fc"], escenario["d1"])
    cab = alta_por_desafio(mundo.client, reloj_mfa, nombre).cabeceras

    r = mundo.client.get(f"{API}/maestros/unidades", headers=_h(cab, escenario["d1"]))
    assert r.status_code == 200, r.text
    r = mundo.client.get(f"{API}/maestros/unidades", headers=_h(cab, escenario["d2"]))
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "COMPANY_SCOPE_FORBIDDEN", r.text


def test_csa_07_admin_no_trae_permisos_de_negocio(mundo, reloj_mfa, escenario):
    """CSA-07: ADMIN no autoriza rutas de negocio."""
    nombre = _nombre()
    crear_usuario(mundo, nombre, admin=True)
    cab = alta_por_desafio(mundo.client, reloj_mfa, nombre).cabeceras

    r = mundo.client.get(f"{API}/maestros/unidades", headers=_h(cab, escenario["d1"]))
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "PERMISSION_DENIED", r.text



def test_csa_08_rol_nulo_vale_en_todas_las_empresas(mundo, reloj_mfa, escenario):
    """CSA-08: company_id nulo autoriza en todo el tenant accesible."""
    _, cab = _actor(mundo, reloj_mfa, [(escenario["rol"], None)])
    for empresa in (escenario["d1"], escenario["d2"]):
        r = mundo.client.get(f"{API}/maestros/unidades", headers=_h(cab, empresa))
        assert r.status_code == 200, r.text


def test_csa_09_revocacion_efectiva_sin_volver_a_entrar(mundo, reloj_mfa, escenario):
    """CSA-09: la autoridad se relee en cada petición con el mismo token."""
    actor_id, cab = _actor(mundo, reloj_mfa, [(escenario["rol"], None)])
    r = mundo.client.get(f"{API}/maestros/unidades", headers=_h(cab, escenario["d2"]))
    assert r.status_code == 200, r.text

    _quitar(mundo, actor_id, escenario["rol"])
    _dar(mundo, actor_id, escenario["rol"], escenario["d1"])
    r = mundo.client.get(f"{API}/maestros/unidades", headers=_h(cab, escenario["d2"]))
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "COMPANY_SCOPE_FORBIDDEN", r.text


def test_csa_10_acceso_manda_antes_que_capacidad(mundo, reloj_mfa, escenario):
    """CSA-10: sin acceso a la empresa responde COMPANY_NOT_FOUND."""
    actor_id, cab = _actor(mundo, reloj_mfa, [(escenario["rol"], None)])
    _alcance(mundo, actor_id, escenario["d1"])
    r = mundo.client.get(f"{API}/maestros/unidades", headers=_h(cab, escenario["d2"]))
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "COMPANY_NOT_FOUND", r.text


def test_csa_11_empresa_de_otro_tenant_no_encontrada(mundo, reloj_mfa, escenario):
    """CSA-11: empresa de otro tenant responde COMPANY_NOT_FOUND."""
    _, cab = _actor(mundo, reloj_mfa, [(escenario["rol"], escenario["d1"])])
    db = mundo.factory()
    try:
        otra = db.execute(
            select(Company.id).where(Company.tenant_id == mundo.tenant_b_id)
        ).scalar_one()
    finally:
        db.close()
    r = mundo.client.get(f"{API}/maestros/unidades", headers=_h(cab, otra))
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "COMPANY_NOT_FOUND", r.text


def test_csa_12_admin_de_arranque_con_asignaciones_nulas(mundo, escenario):
    """CSA-12: el admin inicial tiene ADMIN y FUNCIONAL_COMPLETO nulos."""
    db = mundo.factory()
    try:
        filas = db.execute(
            select(UserRole).where(UserRole.user_id == mundo.admin_id)
        ).scalars().all()
        claves = {(ur.role_id, ur.company_id) for ur in filas}
        assert (escenario["admin_rol"], None) in claves
        assert (escenario["fc"], None) in claves
    finally:
        db.close()
