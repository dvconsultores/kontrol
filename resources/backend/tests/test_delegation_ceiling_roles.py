"""Pruebas DCR para techo de delegación al crear roles y publicar delegabilidad en listado."""
from uuid import uuid4

import pytest
from mfa_mundo import API, alta_por_desafio, crear_usuario, eventos, mundo_mfa
from sqlalchemy import func, select

from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Permission, Role, RolePermission
from app.modules.organization.models import Company

pytest_plugins = ("mfa_apoyo",)


@pytest.fixture(scope="module")
def mundo():
    with mundo_mfa() as m:
        yield m


@pytest.fixture(scope="module")
def roles(mundo):
    db = mundo.factory()
    try:
        gestor = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code="R_DCR_GESTOR",
            name="R_DCR_GESTOR",
            company_id=None,
            permissions=[
                "roles:view",
                "roles:edit",
                "roles:create",
                "users:view",
                "inventario:view",
            ],
            actor=mundo.admin_id,
        )
        sub = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code="R_DCR_SUB",
            name="R_DCR_SUB",
            company_id=None,
            permissions=["inventario:view"],
            actor=mundo.admin_id,
        )
        return {"R_DCR_GESTOR": gestor["id"], "R_DCR_SUB": sub["id"]}
    finally:
        db.close()


def _nombre():
    return f"rol_{uuid4().hex[:10]}"


def _actor(mundo, reloj, rol=None, admin=False):
    nombre = f"user_{uuid4().hex[:10]}"
    user_id = crear_usuario(mundo, nombre, rol=rol, admin=admin)
    auth = alta_por_desafio(mundo.client, reloj, nombre)
    return user_id, auth.cabeceras


def _crear(mundo, cab, code, permisos, **extra):
    payload = {"code": code, "name": code, "permissions": permisos}
    payload.update(extra)
    return mundo.client.post(f"{API}/roles", json=payload, headers=cab)


def _existe_rol(mundo, code):
    db = mundo.factory()
    try:
        stmt = select(func.count()).select_from(Role).where(Role.code == code)
        return db.execute(stmt).scalar_one() > 0
    finally:
        db.close()


def _negaciones(mundo, actor_id):
    return [e for e in eventos(mundo, "AUTHORITY_DELEGATION_DENIED") if e.user_id == actor_id]


def _empresa_b(mundo):
    db = mundo.factory()
    try:
        stmt = select(Company.id).where(Company.tenant_id == mundo.tenant_b_id).limit(1)
        return db.execute(stmt).scalar_one()
    finally:
        db.close()


def test_dcr_C01_gestor_no_puede_crear_rol_con_permiso_fuera_de_su_techo(mundo, roles, reloj_mfa):
    """DCR-C01: gestor no puede crear rol con users:mfa_reset."""
    code = _nombre()
    actor_id, cab = _actor(mundo, reloj_mfa, rol="R_DCR_GESTOR")
    antes = len(_negaciones(mundo, actor_id))

    r = _crear(mundo, cab, code, ["users:mfa_reset"])

    assert r.status_code == 403, r.text
    assert r.json()["code"] == "AUTHORITY_CEILING_EXCEEDED", r.text
    assert not _existe_rol(mundo, code), r.text
    negs = _negaciones(mundo, actor_id)
    assert len(negs) == antes + 1, r.text
    assert negs[-1].reason == "AUTHORITY_CEILING_EXCEEDED", r.text
    assert negs[-1].evidence["role_code"] == code, r.text
    assert negs[-1].evidence["capabilities_excedidas"] == ["users:mfa_reset"], r.text


def test_dcr_C02_gestor_no_puede_crear_rol_sombra_con_permisos_de_admin(mundo, roles, reloj_mfa):
    """DCR-C02: gestor no puede crear rol con los permisos de ADMIN."""
    db = mundo.factory()
    try:
        admin_perms = next(
            r["permissions"] for r in identity_service.list_roles(db) if r["code"] == "ADMIN"
        )
    finally:
        db.close()

    code = _nombre()
    _, cab = _actor(mundo, reloj_mfa, rol="R_DCR_GESTOR")
    r = _crear(mundo, cab, code, admin_perms)

    assert r.status_code == 403, r.text
    assert r.json()["code"] == "AUTHORITY_CEILING_EXCEEDED", r.text
    assert not _existe_rol(mundo, code), r.text


def test_dcr_C03_gestor_puede_crear_rol_dentro_de_su_techo(mundo, roles, reloj_mfa):
    """DCR-C03: gestor crea rol con inventario:view."""
    code = _nombre()
    _, cab = _actor(mundo, reloj_mfa, rol="R_DCR_GESTOR")
    r = _crear(mundo, cab, code, ["inventario:view"])

    assert r.status_code == 201, r.text
    assert "id" in r.json(), r.text
    assert _existe_rol(mundo, code), r.text


def test_dcr_C04_gestor_puede_crear_rol_con_company_id_de_su_tenant(mundo, roles, reloj_mfa):
    """DCR-C04: gestor crea rol con company_id del tenant propio."""
    code = _nombre()
    _, cab = _actor(mundo, reloj_mfa, rol="R_DCR_GESTOR")
    r = _crear(mundo, cab, code, ["inventario:view"], company_id=mundo.company_id)

    assert r.status_code == 201, r.text
    assert "id" in r.json(), r.text
    assert _existe_rol(mundo, code), r.text


def test_dcr_C05_gestor_no_puede_crear_rol_con_permiso_parcialmente_fuera_de_su_techo(mundo, roles, reloj_mfa):
    """DCR-C05: gestor no crea rol con inventario:view e inventario:approve."""
    code = _nombre()
    actor_id, cab = _actor(mundo, reloj_mfa, rol="R_DCR_GESTOR")
    antes = len(_negaciones(mundo, actor_id))

    r = _crear(mundo, cab, code, ["inventario:view", "inventario:approve"])

    assert r.status_code == 403, r.text
    assert r.json()["code"] == "AUTHORITY_CEILING_EXCEEDED", r.text
    assert not _existe_rol(mundo, code), r.text
    negs = _negaciones(mundo, actor_id)
    assert len(negs) == antes + 1, r.text
    assert negs[-1].evidence["capabilities_excedidas"] == ["inventario:approve"], r.text


def test_dcr_C06_admin_solo_tecnico_no_puede_crear_rol_con_compras_approve(mundo, roles, reloj_mfa):
    """DCR-C06: usuario solo ADMIN no crea rol con compras:approve."""
    code = _nombre()
    _, cab = _actor(mundo, reloj_mfa, admin=True)
    r = _crear(mundo, cab, code, ["compras:approve"])

    assert r.status_code == 403, r.text
    assert r.json()["code"] == "AUTHORITY_CEILING_EXCEEDED", r.text
    assert not _existe_rol(mundo, code), r.text


def test_dcr_C07_gestor_no_puede_crear_rol_con_company_id_de_otro_tenant(mundo, roles, reloj_mfa):
    """DCR-C07: gestor no crea rol con company_id del tenant B."""
    code = _nombre()
    _, cab = _actor(mundo, reloj_mfa, rol="R_DCR_GESTOR")
    r = _crear(mundo, cab, code, ["inventario:view"], company_id=_empresa_b(mundo))

    assert r.status_code == 404, r.text
    assert r.json()["code"] == "COMPANY_NOT_FOUND", r.text
    assert not _existe_rol(mundo, code), r.text


def test_dcr_G01_gestor_ve_delegabilidad_en_listado(mundo, roles, reloj_mfa):
    """DCR-G01: gestor ve delegable True para R_DCR_SUB y False para ADMIN y R_GESTOR_MFA."""
    _, cab = _actor(mundo, reloj_mfa, rol="R_DCR_GESTOR")
    r = mundo.client.get(f"{API}/roles", headers=cab)

    assert r.status_code == 200, r.text
    items = {item["code"]: item for item in r.json()["items"]}

    assert items["R_DCR_SUB"]["delegable"] is True, r.text
    assert items["R_DCR_SUB"]["motivo"] is None, r.text
    assert items["ADMIN"]["delegable"] is False, r.text
    assert items["ADMIN"]["motivo"] == "AUTHORITY_CEILING_EXCEEDED", r.text
    assert items["R_GESTOR_MFA"]["delegable"] is False, r.text
    assert items["R_GESTOR_MFA"]["motivo"] == "AUTHORITY_CEILING_EXCEEDED", r.text

    for code, item in items.items():
        assert "delegable" in item, f"{code}: {r.text}"
        assert "motivo" in item, f"{code}: {r.text}"


def test_dcr_G02_admin_ve_su_propio_rol_delegable_y_funcional_completo_no(mundo, roles, reloj_mfa):
    """DCR-G02: ADMIN ve ADMIN delegable True y FUNCIONAL_COMPLETO delegable False."""
    _, cab = _actor(mundo, reloj_mfa, admin=True)
    r = mundo.client.get(f"{API}/roles", headers=cab)

    assert r.status_code == 200, r.text
    items = {item["code"]: item for item in r.json()["items"]}

    assert items["ADMIN"]["delegable"] is True, r.text
    assert items["ADMIN"]["motivo"] is None, r.text
    assert items["FUNCIONAL_COMPLETO"]["delegable"] is False, r.text
    assert items["FUNCIONAL_COMPLETO"]["motivo"] == "AUTHORITY_CEILING_EXCEEDED", r.text


def test_dcr_G03_rol_de_empresa_del_tenant_b_no_aparece_en_listado_del_gestor(mundo, roles, reloj_mfa):
    """DCR-G03: rol con company_id del tenant B no aparece en listado del tenant A."""
    db = mundo.factory()
    try:
        perm = db.execute(
            select(Permission).where(Permission.resource == "inventario", Permission.action == "view")
        ).scalar_one()
        rol_b = Role(
            code=_nombre(),
            name="rol_tenant_b",
            company_id=_empresa_b(mundo),
            protected=False,
            status="ACTIVE",
        )
        db.add(rol_b)
        db.flush()
        db.add(RolePermission(role_id=rol_b.id, permission_id=perm.id))
        db.commit()
        code_b = rol_b.code
    finally:
        db.close()

    _, cab = _actor(mundo, reloj_mfa, rol="R_DCR_GESTOR")
    r = mundo.client.get(f"{API}/roles", headers=cab)

    assert r.status_code == 200, r.text
    codes = {item["code"] for item in r.json()["items"]}
    assert code_b not in codes, r.text
