"""Spec 003 · techo de delegación al asignar y quitar roles (DC).

Fija por la API el techo por capacidad exacta, la autoescalada, los roles
protegidos, la división de ADMIN (OD-DEL-10/12), la cadena evaluada en el
momento de la acción y el aislamiento de tenant.
"""
from uuid import uuid4

import pytest
from mfa_mundo import API, alta_por_desafio, crear_usuario, eventos, mundo_mfa
from sqlalchemy import func, select

from app.modules.identity_access import authority
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Permission, Role, RolePermission, UserRole
from app.modules.organization.models import Company

pytest_plugins = ("mfa_apoyo",)

TECNICAS = {
    "dashboard:view",
    "organization:view",
    "organization:create",
    "organization:edit",
    "organization:deactivate",
    "organization:activate",
    "organization:delete",
    "organization:manage_structure",
    "users:view",
    "users:create",
    "users:edit",
    "users:deactivate",
    "users:activate",
    "users:mfa_reset",
    "roles:view",
    "roles:create",
    "roles:edit",
    "audit:view",
    "license:view",
    "license:create",
    "license:edit",
    "license:approve",
    "notificaciones:configure",
    "tareas:configure",
    "documentos:manage_types",
}


@pytest.fixture(scope="module")
def mundo():
    with mundo_mfa() as m:
        yield m


@pytest.fixture(scope="module")
def roles(mundo):
    creados = {}
    definiciones = {
        "R_DEL_GESTOR": ["roles:view", "roles:edit", "roles:create", "users:view", "inventario:view"],
        "R_DEL_SUB": ["inventario:view"],
        "R_DEL_COMPRAS": ["compras:view"],
        "R_DEL_TECNICO": sorted(TECNICAS),
        "R_DEL_INACTIVO": ["inventario:view"],
    }
    db = mundo.factory()
    try:
        for code, permisos in definiciones.items():
            rol = identity_service.create_role(
                db,
                tenant_id=mundo.tenant_id,
                code=code,
                name=code,
                company_id=None,
                permissions=permisos,
                actor=mundo.admin_id,
            )
            creados[code] = rol["id"]
        rol_inactivo = db.execute(select(Role).where(Role.id == creados["R_DEL_INACTIVO"])).scalar_one()
        rol_inactivo.status = "INACTIVE"
        db.commit()
    finally:
        db.close()
    return creados


def _nombre():
    return uuid4().hex[:10]


def _id_rol(mundo, code):
    db = mundo.factory()
    try:
        roles_lista = identity_service.list_roles(db)
    finally:
        db.close()
    for rol in roles_lista:
        if rol["code"] == code:
            return rol["id"]
    raise AssertionError(f"Rol {code} no encontrado")


def _actor(mundo, reloj, rol=None, admin=False):
    usuario = _nombre()
    user_id = crear_usuario(mundo, usuario, rol=rol, admin=admin)
    sesion = alta_por_desafio(mundo.client, reloj, usuario)
    return user_id, sesion.cabeceras


def _destino(mundo, tenant="DEMO"):
    usuario = _nombre()
    return crear_usuario(mundo, usuario, tenant=tenant)


def _dar(mundo, user_id, role_id):
    db = mundo.factory()
    try:
        db.add(UserRole(user_id=user_id, role_id=role_id, company_id=None))
        db.commit()
    finally:
        db.close()


def _filas(mundo, user_id, role_id):
    db = mundo.factory()
    try:
        return db.execute(
            select(func.count()).select_from(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
            )
        ).scalar_one()
    finally:
        db.close()


def _asignar(mundo, cab, user_id, role_id, **extra):
    cuerpo = {"role_id": role_id, **extra}
    return mundo.client.post(
        f"{API}/users/{user_id}/roles",
        json=cuerpo,
        headers=cab,
    )


def _negaciones(mundo, actor_id):
    return [e for e in eventos(mundo, "AUTHORITY_DELEGATION_DENIED") if e.user_id == actor_id]


def test_dc_a01_gestor_delega_sub_dentro_del_techo(mundo, reloj_mfa, roles):
    """DC-A01: gestor asigna R_DEL_SUB a un destino."""
    actor_id, cab = _actor(mundo, reloj_mfa, rol="R_DEL_GESTOR")
    destino_id = _destino(mundo)
    rol_id = roles["R_DEL_SUB"]
    negaciones_antes = _negaciones(mundo, actor_id)

    r = _asignar(mundo, cab, destino_id, rol_id)

    assert r.status_code == 200, r.text
    assert _filas(mundo, destino_id, rol_id) == 1, r.text
    recientes = [e for e in eventos(mundo, "ROLE_ASSIGNED") if e.after and e.after.get("user_id") == destino_id]
    assert recientes, "No hay evento ROLE_ASSIGNED para el destino"
    assert "company_id" in recientes[-1].after, recientes[-1].after
    assert len(_negaciones(mundo, actor_id)) == len(negaciones_antes), "No debe haber negaciones"


def test_dc_a02_gestor_no_delega_r_gestor_mfa(mundo, reloj_mfa, roles):
    """DC-A02: gestor asigna R_GESTOR_MFA a un destino."""
    actor_id, cab = _actor(mundo, reloj_mfa, rol="R_DEL_GESTOR")
    destino_id = _destino(mundo)
    rol_id = _id_rol(mundo, "R_GESTOR_MFA")
    negaciones_antes = _negaciones(mundo, actor_id)

    r = _asignar(mundo, cab, destino_id, rol_id)

    assert r.status_code == 403, r.text
    assert r.json()["code"] == "AUTHORITY_CEILING_EXCEEDED", r.text
    assert _filas(mundo, destino_id, rol_id) == 0, r.text
    nuevas = _negaciones(mundo, actor_id)[len(negaciones_antes):]
    assert len(nuevas) == 1, r.text
    negacion = nuevas[0]
    assert negacion.reason == "AUTHORITY_CEILING_EXCEEDED", negacion.reason
    assert negacion.evidence["role_code"] == "R_GESTOR_MFA", negacion.evidence
    assert negacion.evidence["capabilities_excedidas"] == ["users:mfa_reset"], negacion.evidence


def test_dc_a03_gestor_no_delega_r_almacen(mundo, reloj_mfa, roles):
    """DC-A03: gestor asigna R_ALMACEN y excede por inventario:transition."""
    actor_id, cab = _actor(mundo, reloj_mfa, rol="R_DEL_GESTOR")
    destino_id = _destino(mundo)
    rol_id = _id_rol(mundo, "R_ALMACEN")
    negaciones_antes = _negaciones(mundo, actor_id)

    r = _asignar(mundo, cab, destino_id, rol_id)

    assert r.status_code == 403, r.text
    assert r.json()["code"] == "AUTHORITY_CEILING_EXCEEDED", r.text
    assert _filas(mundo, destino_id, rol_id) == 0, r.text
    nuevas = _negaciones(mundo, actor_id)[len(negaciones_antes):]
    assert len(nuevas) == 1, r.text
    assert nuevas[0].evidence["capabilities_excedidas"] == ["inventario:transition"], nuevas[0].evidence


def test_dc_s01_gestor_se_autoasigna_admin(mundo, reloj_mfa, roles):
    """DC-S01: gestor se asigna ADMIN a sí mismo."""
    actor_id, cab = _actor(mundo, reloj_mfa, rol="R_DEL_GESTOR")
    rol_id = _id_rol(mundo, "ADMIN")
    negaciones_antes = _negaciones(mundo, actor_id)

    r = _asignar(mundo, cab, actor_id, rol_id)

    assert r.status_code == 403, r.text
    assert r.json()["code"] == "SELF_ESCALATION_FORBIDDEN", r.text
    assert _filas(mundo, actor_id, rol_id) == 0, r.text
    nuevas = _negaciones(mundo, actor_id)[len(negaciones_antes):]
    assert len(nuevas) == 1, r.text
    assert nuevas[0].reason == "SELF_ESCALATION_FORBIDDEN", nuevas[0].reason


def test_dc_s02_gestor_se_autoasigna_r_gestor_mfa(mundo, reloj_mfa, roles):
    """DC-S02: gestor se asigna R_GESTOR_MFA a sí mismo."""
    actor_id, cab = _actor(mundo, reloj_mfa, rol="R_DEL_GESTOR")
    rol_id = _id_rol(mundo, "R_GESTOR_MFA")
    negaciones_antes = _negaciones(mundo, actor_id)

    r = _asignar(mundo, cab, actor_id, rol_id)

    assert r.status_code == 403, r.text
    assert r.json()["code"] == "SELF_ESCALATION_FORBIDDEN", r.text
    assert _filas(mundo, actor_id, rol_id) == 0, r.text
    nuevas = _negaciones(mundo, actor_id)[len(negaciones_antes):]
    assert len(nuevas) == 1, r.text
    assert nuevas[0].reason == "SELF_ESCALATION_FORBIDDEN", nuevas[0].reason


def test_dc_s03_gestor_se_autoasigna_r_del_sub(mundo, reloj_mfa, roles):
    """DC-S03: gestor se asigna R_DEL_SUB y ya posee esa capacidad."""
    actor_id, cab = _actor(mundo, reloj_mfa, rol="R_DEL_GESTOR")
    rol_id = roles["R_DEL_SUB"]
    negaciones_antes = _negaciones(mundo, actor_id)

    r = _asignar(mundo, cab, actor_id, rol_id)

    assert r.status_code == 200, r.text
    assert _filas(mundo, actor_id, rol_id) == 1, r.text
    assert len(_negaciones(mundo, actor_id)) == len(negaciones_antes), "No debe haber negaciones"


def test_dc_p01_tecnico_sin_rol_admin_no_delega_admin(mundo, reloj_mfa, roles):
    """DC-P01: actor con R_DEL_TECNICO asigna ADMIN a un destino."""
    actor_id, cab = _actor(mundo, reloj_mfa, rol="R_DEL_TECNICO")
    destino_id = _destino(mundo)
    rol_id = _id_rol(mundo, "ADMIN")
    negaciones_antes = _negaciones(mundo, actor_id)

    r = _asignar(mundo, cab, destino_id, rol_id)

    assert r.status_code == 403, r.text
    assert r.json()["code"] == "AUTHORITY_CEILING_EXCEEDED", r.text
    assert _filas(mundo, destino_id, rol_id) == 0, r.text
    nuevas = _negaciones(mundo, actor_id)[len(negaciones_antes):]
    assert len(nuevas) == 1, r.text
    assert nuevas[0].evidence["capabilities_excedidas"] == [], nuevas[0].evidence


def test_dc_p02_admin_delega_admin(mundo, reloj_mfa, roles):
    """DC-P02: actor admin=True asigna ADMIN a un destino."""
    actor_id, cab = _actor(mundo, reloj_mfa, admin=True)
    destino_id = _destino(mundo)
    rol_id = _id_rol(mundo, "ADMIN")
    negaciones_antes = _negaciones(mundo, actor_id)

    r = _asignar(mundo, cab, destino_id, rol_id)

    assert r.status_code == 200, r.text
    assert _filas(mundo, destino_id, rol_id) == 1, r.text
    assert len(_negaciones(mundo, actor_id)) == len(negaciones_antes), "No debe haber negaciones"


def test_dc_p03_admin_no_delega_funcional_completo(mundo, reloj_mfa, roles):
    """DC-P03: actor admin=True asigna FUNCIONAL_COMPLETO a un destino."""
    actor_id, cab = _actor(mundo, reloj_mfa, admin=True)
    destino_id = _destino(mundo)
    rol_id = _id_rol(mundo, "FUNCIONAL_COMPLETO")
    negaciones_antes = _negaciones(mundo, actor_id)

    r = _asignar(mundo, cab, destino_id, rol_id)

    assert r.status_code == 403, r.text
    assert r.json()["code"] == "AUTHORITY_CEILING_EXCEEDED", r.text
    assert _filas(mundo, destino_id, rol_id) == 0, r.text
    nuevas = _negaciones(mundo, actor_id)[len(negaciones_antes):]
    assert len(nuevas) == 1, r.text
    excedidas = nuevas[0].evidence["capabilities_excedidas"]
    assert excedidas and excedidas == sorted(excedidas), excedidas
    assert not set(excedidas) & TECNICAS, excedidas


def test_dc_t01_catalogo_y_admin_inicial(mundo):
    """DC-T01: ADMIN tiene exactamente TECNICAS; FUNCIONAL_COMPLETO cubre el resto."""
    db = mundo.factory()
    try:
        roles_lista = identity_service.list_roles(db)
        por_codigo = {r["code"]: r for r in roles_lista}
        admin = por_codigo["ADMIN"]
        funcional = por_codigo["FUNCIONAL_COMPLETO"]

        assert set(admin["permissions"]) == TECNICAS, admin["permissions"]
        assert funcional["protected"] is True, funcional
        permisos_funcional = set(funcional["permissions"])
        assert permisos_funcional.isdisjoint(TECNICAS), permisos_funcional & TECNICAS

        catalogo = {
            f"{p.resource}:{p.action}"
            for p in db.execute(select(Permission)).scalars()
        }
        assert len(catalogo) == 106, len(catalogo)
        assert permisos_funcional | TECNICAS == catalogo, catalogo - (permisos_funcional | TECNICAS)

        admin_id = mundo.admin_id
        filas_admin = db.execute(
            select(UserRole).where(UserRole.user_id == admin_id)
        ).scalars().all()
        codigos_admin = {
            db.execute(select(Role.code).where(Role.id == ur.role_id)).scalar_one()
            for ur in filas_admin
        }
        assert "ADMIN" in codigos_admin, codigos_admin
        assert "FUNCIONAL_COMPLETO" in codigos_admin, codigos_admin
        for ur in filas_admin:
            if db.execute(select(Role.code).where(Role.id == ur.role_id)).scalar_one() in {"ADMIN", "FUNCIONAL_COMPLETO"}:
                assert ur.company_id is None, ur.company_id
    finally:
        db.close()


def test_dc_t02_admin_no_delega_roles_funcionales(mundo, reloj_mfa, roles):
    """DC-T02: actor admin=True no puede asignar R_ALMACEN ni R_DEL_SUB."""
    actor_id, cab = _actor(mundo, reloj_mfa, admin=True)
    destino_id = _destino(mundo)
    negaciones_antes = _negaciones(mundo, actor_id)

    for rol_id in (_id_rol(mundo, "R_ALMACEN"), roles["R_DEL_SUB"]):
        r = _asignar(mundo, cab, destino_id, rol_id)
        assert r.status_code == 403, r.text
        assert r.json()["code"] == "AUTHORITY_CEILING_EXCEEDED", r.text
        assert _filas(mundo, destino_id, rol_id) == 0, r.text

    nuevas = _negaciones(mundo, actor_id)[len(negaciones_antes):]
    assert len(nuevas) == 2, nuevas


def test_dc_h01_cadena_de_autoridad(mundo, reloj_mfa, roles):
    """DC-H01: al perder una capacidad, el actor ya no puede delegarla."""
    actor_id, cab = _actor(mundo, reloj_mfa, rol="R_DEL_GESTOR")
    _dar(mundo, actor_id, roles["R_DEL_COMPRAS"])
    destino_y = _destino(mundo)
    destino_z = _destino(mundo)
    rol_compras = roles["R_DEL_COMPRAS"]
    negaciones_antes = _negaciones(mundo, actor_id)

    r = _asignar(mundo, cab, destino_y, rol_compras)
    assert r.status_code == 200, r.text
    assert _filas(mundo, destino_y, rol_compras) == 1, r.text

    db = mundo.factory()
    try:
        identity_service.remove_role_from_user(
            db,
            tenant_id=mundo.tenant_id,
            user_id=actor_id,
            role_id=rol_compras,
            actor=mundo.admin_id,
        )
    finally:
        db.close()

    r = _asignar(mundo, cab, destino_z, rol_compras)
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "AUTHORITY_CEILING_EXCEEDED", r.text
    assert _filas(mundo, destino_y, rol_compras) == 1, "Lo ya delegado se conserva"
    nuevas = _negaciones(mundo, actor_id)[len(negaciones_antes):]
    assert len(nuevas) == 1, nuevas


def test_dc_x01_rol_de_otro_tenant_no_se_puede_asignar(mundo, reloj_mfa, roles):
    """DC-X01: gestor asigna R_DEL_SUB a un destino del tenant B."""
    actor_id, cab = _actor(mundo, reloj_mfa, rol="R_DEL_GESTOR")
    destino_id = _destino(mundo, tenant="DEMO2")
    rol_id = roles["R_DEL_SUB"]

    r = _asignar(mundo, cab, destino_id, rol_id)

    assert r.status_code == 404, r.text


def test_dc_x02_rol_de_empresa_del_tenant_b_no_encontrado(mundo, reloj_mfa, roles):
    """DC-X02: rol con company_id del tenant B no existe para el actor del tenant A."""
    actor_id, cab = _actor(mundo, reloj_mfa, rol="R_DEL_GESTOR")
    destino_id = _destino(mundo)
    db = mundo.factory()
    try:
        company_b = db.execute(
            select(Company).where(Company.tenant_id == mundo.tenant_b_id)
        ).scalar_one()
        rol = Role(
            code=f"R_OTRO_TENANT_{_nombre()}",
            name="Rol otro tenant",
            company_id=company_b.id,
            protected=False,
            status="ACTIVE",
        )
        db.add(rol)
        db.flush()
        permiso = db.execute(
            select(Permission).where(Permission.resource == "inventario", Permission.action == "view")
        ).scalar_one()
        db.add(RolePermission(role_id=rol.id, permission_id=permiso.id))
        db.commit()
        rol_id = rol.id
    finally:
        db.close()

    r = _asignar(mundo, cab, destino_id, rol_id)

    assert r.status_code == 404, r.text
    assert r.json()["code"] == "ROLE_NOT_FOUND", r.text
    assert _filas(mundo, destino_id, rol_id) == 0, r.text


def test_dc_v01_campo_extra_invalido(mundo, reloj_mfa, roles):
    """DC-V01: el cuerpo con protected=True se rechaza con 422."""
    actor_id, cab = _actor(mundo, reloj_mfa, rol="R_DEL_GESTOR")
    destino_id = _destino(mundo)
    rol_id = roles["R_DEL_SUB"]

    r = _asignar(mundo, cab, destino_id, rol_id, protected=True)

    assert r.status_code == 422, r.text
    assert _filas(mundo, destino_id, rol_id) == 0, r.text


def test_dc_i01_rol_inactivo_no_se_puede_asignar(mundo, reloj_mfa, roles):
    """DC-I01: gestor asigna R_DEL_INACTIVO y recibe 409."""
    actor_id, cab = _actor(mundo, reloj_mfa, rol="R_DEL_GESTOR")
    destino_id = _destino(mundo)
    rol_id = roles["R_DEL_INACTIVO"]

    r = _asignar(mundo, cab, destino_id, rol_id)

    assert r.status_code == 409, r.text
    assert r.json()["code"] == "ROLE_INACTIVE", r.text
    assert _filas(mundo, destino_id, rol_id) == 0, r.text


def test_dc_m01_quitar_rol_fuera_del_techo_se_deniega(mundo, reloj_mfa, roles):
    """DC-M01: gestor intenta quitar R_GESTOR_MFA y excede su techo."""
    actor_id, cab = _actor(mundo, reloj_mfa, rol="R_DEL_GESTOR")
    destino_id = _destino(mundo)
    rol_id = _id_rol(mundo, "R_GESTOR_MFA")
    _dar(mundo, destino_id, rol_id)
    negaciones_antes = _negaciones(mundo, actor_id)

    r = mundo.client.delete(
        f"{API}/users/{destino_id}/roles/{rol_id}",
        headers=cab,
    )

    assert r.status_code == 403, r.text
    assert r.json()["code"] == "AUTHORITY_CEILING_EXCEEDED", r.text
    assert _filas(mundo, destino_id, rol_id) == 1, r.text
    nuevas = _negaciones(mundo, actor_id)[len(negaciones_antes):]
    assert len(nuevas) == 1, nuevas
    assert nuevas[0].reason == "AUTHORITY_CEILING_EXCEEDED", nuevas[0].reason


def test_dc_m02_quitar_rol_dentro_del_techo(mundo, reloj_mfa, roles):
    """DC-M02: gestor quita R_DEL_SUB dentro de su techo."""
    actor_id, cab = _actor(mundo, reloj_mfa, rol="R_DEL_GESTOR")
    destino_id = _destino(mundo)
    rol_id = roles["R_DEL_SUB"]
    _dar(mundo, destino_id, rol_id)
    negaciones_antes = _negaciones(mundo, actor_id)

    r = mundo.client.delete(
        f"{API}/users/{destino_id}/roles/{rol_id}",
        headers=cab,
    )

    assert r.status_code == 200, r.text
    assert _filas(mundo, destino_id, rol_id) == 0, r.text
    assert len(_negaciones(mundo, actor_id)) == len(negaciones_antes), "No debe haber negaciones"


def test_dc_u01_usuario_inactivo_no_tiene_autoridad(mundo, roles):
    """DC-U01: un usuario INACTIVE no tiene capacidades ni alcance aunque conserve sus roles."""
    from app.modules.identity_access.models import User

    user_id = crear_usuario(mundo, _nombre(), rol="R_DEL_SUB")
    db = mundo.factory()
    try:
        user = db.get(User, user_id)
        assert "inventario:view" in authority.effective_capabilities(db, user)
        assert authority.effective_scope(db, user, "inventario:view")
        user.status = "INACTIVE"
        db.commit()
        assert authority.effective_capabilities(db, user) == set()
        assert authority.effective_scope(db, user, "inventario:view") == set()
    finally:
        db.close()
