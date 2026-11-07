"""Pruebas de gestión del factor MFA, reautenticación y reset administrativo."""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from mfa_apoyo import codigo_totp
from mfa_mundo import (
    API,
    CONTRASENA,
    AltaMfa,
    alta_por_desafio,
    crear_usuario,
    entrar_con_totp,
    login,
    mundo_mfa,
)
from sqlalchemy import select

from app.core.dependencies import require_recent_reauth
from app.core.route_contexts import contextos_de_api
from app.modules.identity_access.mfa_policy import REAUTH_PROTECTED_OPERATIONS
from app.modules.identity_access.models import MfaRecoveryCode, User

pytest_plugins = ("mfa_apoyo",)

RUTAS_PROTEGIDAS = {
    ("POST", "/api/v1/license/activate"),
    ("POST", "/api/v1/license/import"),
    ("PUT", "/api/v1/licensing/central-config"),
    ("POST", "/api/v1/licensing/sync"),
    ("POST", "/api/v1/licensing/renewal-requests"),
    ("POST", "/api/v1/licensing/renewal-requests/{request_id}/transition"),
    ("POST", "/api/v1/licensing/mode-transition"),
    ("POST", "/api/v1/users"),
    ("POST", "/api/v1/users/{user_id}/roles"),
    ("DELETE", "/api/v1/users/{user_id}/roles/{role_id}"),
    ("POST", "/api/v1/roles"),
    ("POST", "/api/v1/organization/warehouses/{warehouse_id}/deactivate"),
    ("DELETE", "/api/v1/organization/warehouses/{warehouse_id}"),
    ("POST", "/api/v1/organization/zones/{node_id}/deactivate"),
    ("DELETE", "/api/v1/organization/zones/{node_id}"),
    ("POST", "/api/v1/organization/aisles/{node_id}/deactivate"),
    ("DELETE", "/api/v1/organization/aisles/{node_id}"),
    ("POST", "/api/v1/organization/racks/{node_id}/deactivate"),
    ("DELETE", "/api/v1/organization/racks/{node_id}"),
    ("POST", "/api/v1/organization/levels/{node_id}/deactivate"),
    ("DELETE", "/api/v1/organization/levels/{node_id}"),
    ("POST", "/api/v1/organization/locations/{location_id}/deactivate"),
    ("DELETE", "/api/v1/organization/locations/{location_id}"),
    ("POST", "/api/v1/approvals/policies"),
    ("PATCH", "/api/v1/approvals/policies/{policy_id}"),
    ("POST", "/api/v1/approvals/policies/{policy_id}/activate"),
    ("POST", "/api/v1/approvals/policies/{policy_id}/close"),
    ("POST", "/api/v1/approvals/policies/{policy_id}/rules"),
    ("POST", "/api/v1/approvals/policies/{policy_id}/rules/{rule_id}/levels"),
    ("POST", "/api/v1/auth/mfa/recovery-codes"),
    ("DELETE", "/api/v1/auth/mfa"),
    ("POST", "/api/v1/users/{user_id}/mfa/reset"),
}

PERMISOS_SENSIBLES = {
    "users:create",
    "roles:create",
    "roles:edit",
    "organization:delete",
    "organization:deactivate",
    "license:create",
    "license:edit",
    "license:approve",
    "aprobaciones:configure",
    "users:mfa_reset",
}


@pytest.fixture(scope="module")
def mundo():
    """Crea un mundo MFA para todo el módulo."""
    with mundo_mfa() as m:
        yield m


def _usuario(mundo) -> str:
    """Devuelve un nombre de usuario único."""
    return f"u_{uuid.uuid4().hex[:10]}"


def _cabeceras_bearer(token: str) -> dict[str, str]:
    """Devuelve las cabeceras de autorización Bearer."""
    return {"Authorization": f"Bearer {token}"}


def _token_de(cabeceras: dict[str, str]) -> str:
    """Extrae el token Bearer de unas cabeceras."""
    return cabeceras["Authorization"].split(" ", 1)[1]


def _crear_privilegiado_con_factor(mundo, reloj, *, admin: bool = False, tenant: str = "DEMO"):
    """Crea un usuario privilegiado con factor MFA."""
    usuario = _usuario(mundo)
    rol = None if admin else "R_GESTOR_MFA"
    user_id = crear_usuario(
        mundo, usuario, rol=rol, admin=admin, tenant=tenant, must_change_password=False
    )
    alta = alta_por_desafio(mundo.client, reloj, usuario, tenant=tenant)
    return usuario, user_id, alta


def _enrollment_bearer(client, cabeceras: dict[str, str], *, body: dict | None = None):
    """Realiza una solicitud de enrollment Bearer."""
    return client.post(f"{API}/auth/mfa/enrollment", json=body or {}, headers=cabeceras)


def _confirmar_enrollment_bearer(client, cabeceras: dict[str, str], clave_manual: str, reloj):
    """Confirma un enrollment Bearer."""
    reloj.siguiente_paso()
    codigo = codigo_totp(clave_manual, reloj.ahora())
    return client.post(
        f"{API}/auth/mfa/enrollment/confirm", json={"code": codigo}, headers=cabeceras
    )


def _login_estandar(client, usuario: str) -> str:
    """Inicia sesión de un usuario estándar y devuelve el access token."""
    r = login(client, usuario)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _crear_estandar_con_factor(mundo, reloj):
    """Crea un usuario estándar con factor MFA voluntario."""
    usuario = _usuario(mundo)
    user_id = crear_usuario(mundo, usuario, rol="R_CONSULTA")
    token = _login_estandar(mundo.client, usuario)
    cabeceras = _cabeceras_bearer(token)
    r = _enrollment_bearer(mundo.client, cabeceras)
    assert r.status_code == 200, r.text
    clave = r.json()["manual_key"]
    r = _confirmar_enrollment_bearer(mundo.client, cabeceras, clave, reloj)
    assert r.status_code == 200, r.text
    return (
        usuario,
        user_id,
        AltaMfa(
            cabeceras=cabeceras,
            clave_manual=clave,
            codigos=r.json()["recovery_codes"],
            respuesta=r.json(),
        ),
    )


def test_mfa_d01_estado(mundo, reloj_mfa):
    """MFA-D01: estado del factor para privilegiado y estándar."""
    usuario, _, alta = _crear_privilegiado_con_factor(mundo, reloj_mfa)

    r = mundo.client.get(f"{API}/auth/mfa", headers=alta.cabeceras)
    assert r.status_code == 200, r.text
    datos = r.json()
    assert set(datos.keys()) == {
        "required",
        "policy_class",
        "enabled",
        "activated_at",
        "recovery_codes_remaining",
    }
    assert datos["required"] is True
    assert datos["policy_class"] == "PRIVILEGED"
    assert datos["enabled"] is True
    assert datos["activated_at"] is not None
    assert datos["recovery_codes_remaining"] == 10

    usuario_std = _usuario(mundo)
    crear_usuario(mundo, usuario_std, rol="R_CONSULTA")
    token_std = _login_estandar(mundo.client, usuario_std)

    r = mundo.client.get(f"{API}/auth/mfa", headers=_cabeceras_bearer(token_std))
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos == {
        "required": False,
        "policy_class": "STANDARD",
        "enabled": False,
        "activated_at": None,
        "recovery_codes_remaining": 0,
    }


def test_mfa_d01b_listado_de_usuarios_muestra_si_la_verificacion_esta_activa(mundo, reloj_mfa):
    """MFA-D01b: el listado de usuarios expone mfa_enabled (derivado) y nada del factor."""
    admin_usuario, admin_id, alta = _crear_privilegiado_con_factor(mundo, reloj_mfa, admin=True)
    std = _usuario(mundo)
    std_id = crear_usuario(mundo, std, rol="R_CONSULTA")
    r = mundo.client.get(f"{API}/users", headers=alta.cabeceras)
    assert r.status_code == 200, r.text
    por_id = {u["id"]: u for u in r.json()}
    assert por_id[str(admin_id)]["mfa_enabled"] is True
    assert por_id[str(std_id)]["mfa_enabled"] is False
    for u in r.json():
        assert not ({"manual_key", "secret", "recovery_codes", "activated_at"} & set(u))


def test_mfa_f01_reauth_ok_y_fallos(mundo, reloj_mfa):
    """MFA-F01: reautenticación con éxito y fallos."""
    usuario, _, alta = _crear_privilegiado_con_factor(mundo, reloj_mfa)
    cabeceras = alta.cabeceras

    reloj_mfa.siguiente_paso()
    codigo = codigo_totp(alta.clave_manual, reloj_mfa.ahora())
    r = mundo.client.post(
        f"{API}/auth/reauth",
        json={"password": CONTRASENA, "code": codigo},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    assert "reauth_valid_until" in r.json()

    r = mundo.client.post(
        f"{API}/auth/reauth",
        json={"password": "incorrecta", "code": codigo},
        headers=cabeceras,
    )
    assert r.status_code == 401, r.text
    assert r.json()["code"] == "REAUTH_FAILED"

    reloj_mfa.siguiente_paso()
    r = mundo.client.post(
        f"{API}/auth/reauth",
        json={"password": CONTRASENA, "code": "000000"},
        headers=cabeceras,
    )
    assert r.status_code == 401, r.text
    assert r.json()["code"] == "REAUTH_FAILED"

    r = mundo.client.post(
        f"{API}/auth/reauth",
        json={"password": CONTRASENA},
        headers=cabeceras,
    )
    assert r.status_code == 401, r.text
    assert r.json()["code"] == "REAUTH_FAILED"

    usuario_std = _usuario(mundo)
    crear_usuario(mundo, usuario_std, rol="R_CONSULTA")
    token_std = _login_estandar(mundo.client, usuario_std)

    r = mundo.client.post(
        f"{API}/auth/reauth",
        json={"password": CONTRASENA},
        headers=_cabeceras_bearer(token_std),
    )
    assert r.status_code == 200, r.text


def test_mfa_f02_frescura(mundo, reloj_mfa):
    """MFA-F02: frescura de la reautenticación."""
    _, _, alta = _crear_privilegiado_con_factor(mundo, reloj_mfa)
    cabeceras = alta.cabeceras

    r = mundo.client.post(f"{API}/auth/mfa/recovery-codes", headers=cabeceras)
    assert r.status_code == 200, r.text

    reloj_mfa.avanzar(301)
    r = mundo.client.post(f"{API}/auth/mfa/recovery-codes", headers=cabeceras)
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "REAUTH_REQUIRED"

    reloj_mfa.siguiente_paso()
    codigo = codigo_totp(alta.clave_manual, reloj_mfa.ahora())
    r = mundo.client.post(
        f"{API}/auth/reauth",
        json={"password": CONTRASENA, "code": codigo},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(f"{API}/auth/mfa/recovery-codes", headers=cabeceras)
    assert r.status_code == 200, r.text


def test_mfa_f03_registro(mundo, reloj_mfa):
    """MFA-F03: registro de rutas protegidas por reautenticación."""
    assert REAUTH_PROTECTED_OPERATIONS == frozenset(RUTAS_PROTEGIDAS)

    app: FastAPI = mundo.client.app
    rutas_dependencia = set()

    def _tiene(dep, predicado) -> bool:
        if predicado(dep):
            return True
        return any(_tiene(d, predicado) for d in getattr(dep, "dependencies", []))

    for contexto in contextos_de_api(app):
        if _tiene(contexto.dependant, lambda d: getattr(d, "call", None) is require_recent_reauth):
            for metodo in contexto.methods or set():
                rutas_dependencia.add((metodo, contexto.path))

    assert rutas_dependencia == set(RUTAS_PROTEGIDAS)

    def _tiene_permiso_sensible(dep) -> bool:
        call = getattr(dep, "call", None)
        return getattr(call, "kontrol_permission", None) in PERMISOS_SENSIBLES

    rutas_sensibles = set()
    for contexto in contextos_de_api(app):
        if _tiene(contexto.dependant, _tiene_permiso_sensible):
            for metodo in contexto.methods or set():
                rutas_sensibles.add((metodo, contexto.path))

    assert rutas_sensibles <= set(RUTAS_PROTEGIDAS)


def test_mfa_f04_aplicacion_real(mundo, reloj_mfa):
    """MFA-F04: aplicación real de la reautenticación."""
    _, _, alta = _crear_privilegiado_con_factor(mundo, reloj_mfa, admin=True)
    cabeceras = alta.cabeceras

    reloj_mfa.avanzar(301)

    body_usuario = {
        "username": _usuario(mundo),
        "email": None,
        "password": "OtraClave2026!",
        "must_change_password": True,
    }
    r = mundo.client.post(f"{API}/users", json=body_usuario, headers=cabeceras)
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "REAUTH_REQUIRED"

    body_rol = {
        "code": f"R_{uuid.uuid4().hex[:8]}",
        "name": "Temporal",
        "permissions": ["dashboard:view"],
    }
    r = mundo.client.post(f"{API}/roles", json=body_rol, headers=cabeceras)
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "REAUTH_REQUIRED"

    reloj_mfa.siguiente_paso()
    codigo = codigo_totp(alta.clave_manual, reloj_mfa.ahora())
    r = mundo.client.post(
        f"{API}/auth/reauth",
        json={"password": CONTRASENA, "code": codigo},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(f"{API}/users", json=body_usuario, headers=cabeceras)
    assert r.status_code in (200, 201), r.text

    r = mundo.client.post(f"{API}/roles", json=body_rol, headers=cabeceras)
    assert r.status_code in (200, 201), r.text


def test_mfa_c04_regenerar_invalida_lote_anterior(mundo, reloj_mfa):
    """MFA-C04: regenerar códigos invalida el lote anterior."""
    usuario, _, alta = _crear_privilegiado_con_factor(mundo, reloj_mfa)
    cabeceras = alta.cabeceras
    codigos_viejos = alta.codigos

    r = mundo.client.post(f"{API}/auth/mfa/recovery-codes", headers=cabeceras)
    assert r.status_code == 200, r.text
    cache_control = r.headers.get("cache-control", "")
    assert "no-store" in cache_control
    codigos_nuevos = r.json()["recovery_codes"]
    assert len(codigos_nuevos) == 10
    assert set(codigos_nuevos) != set(codigos_viejos)

    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    challenge = r.json()["challenge_token"]
    r = mundo.client.post(
        f"{API}/auth/mfa/verify",
        json={"challenge_token": challenge, "recovery_code": codigos_viejos[0]},
    )
    assert r.status_code == 401, r.text
    assert r.json()["code"] == "MFA_INVALID_CODE"

    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    challenge = r.json()["challenge_token"]
    r = mundo.client.post(
        f"{API}/auth/mfa/verify",
        json={"challenge_token": challenge, "recovery_code": codigos_nuevos[0]},
    )
    assert r.status_code == 200, r.text
    assert "access_token" in r.json()


def test_mfa_c05_regenerar_sin_factor(mundo, reloj_mfa):
    """MFA-C05: regenerar códigos sin factor."""
    usuario_std = _usuario(mundo)
    crear_usuario(mundo, usuario_std, rol="R_CONSULTA")
    token_std = _login_estandar(mundo.client, usuario_std)

    r = mundo.client.post(
        f"{API}/auth/mfa/recovery-codes", headers=_cabeceras_bearer(token_std)
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "MFA_NOT_CONFIGURED"


def test_mfa_d02_alta_voluntaria_estandar(mundo, reloj_mfa):
    """MFA-D02: alta voluntaria de un estándar por Bearer."""
    usuario_std = _usuario(mundo)
    crear_usuario(mundo, usuario_std, rol="R_CONSULTA")
    token_std = _login_estandar(mundo.client, usuario_std)
    cabeceras = _cabeceras_bearer(token_std)

    r = _enrollment_bearer(mundo.client, cabeceras)
    assert r.status_code == 200, r.text
    datos_alta = r.json()
    assert "manual_key" in datos_alta
    assert "otpauth_uri" in datos_alta
    assert "qr_svg_data_uri" in datos_alta
    assert "expires_in" in datos_alta

    r = _confirmar_enrollment_bearer(
        mundo.client, cabeceras, datos_alta["manual_key"], reloj_mfa
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["recovery_codes"]) == 10

    r = login(mundo.client, usuario_std)
    assert r.status_code == 200, r.text
    assert r.json().get("status") == "MFA_REQUIRED"


def test_mfa_d02b_reemplazo_privilegiado(mundo, reloj_mfa):
    """MFA-D02b: reemplazo de factor de un privilegiado."""
    usuario, _, alta = _crear_privilegiado_con_factor(mundo, reloj_mfa)
    cabeceras_a = alta.cabeceras

    cabeceras_b = entrar_con_totp(
        mundo.client, reloj_mfa, usuario, alta.clave_manual
    )

    r = _enrollment_bearer(mundo.client, cabeceras_a)
    assert r.status_code == 200, r.text
    clave_nueva = r.json()["manual_key"]

    r = _confirmar_enrollment_bearer(mundo.client, cabeceras_a, clave_nueva, reloj_mfa)
    assert r.status_code == 200, r.text

    r = mundo.client.get(f"{API}/auth/me", headers=cabeceras_b)
    assert r.status_code == 401, r.text
    assert r.json()["code"] == "SESSION_REVOKED"

    r = mundo.client.get(f"{API}/auth/me", headers=cabeceras_a)
    assert r.status_code == 200, r.text

    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    challenge = r.json()["challenge_token"]
    reloj_mfa.siguiente_paso()
    codigo_viejo = codigo_totp(alta.clave_manual, reloj_mfa.ahora())
    r = mundo.client.post(
        f"{API}/auth/mfa/verify",
        json={"challenge_token": challenge, "code": codigo_viejo},
    )
    assert r.status_code == 401, r.text
    assert r.json()["code"] == "MFA_INVALID_CODE"

    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    challenge = r.json()["challenge_token"]
    reloj_mfa.siguiente_paso()
    codigo_nuevo = codigo_totp(clave_nueva, reloj_mfa.ahora())
    r = mundo.client.post(
        f"{API}/auth/mfa/verify",
        json={"challenge_token": challenge, "code": codigo_nuevo},
    )
    assert r.status_code == 200, r.text
    assert "access_token" in r.json()


def test_mfa_d02c_enrollment_sin_reauth_reciente(mundo, reloj_mfa):
    """MFA-D02c: enrollment sin reautenticación reciente."""
    _, _, alta = _crear_privilegiado_con_factor(mundo, reloj_mfa)
    cabeceras = alta.cabeceras

    reloj_mfa.avanzar(301)
    r = _enrollment_bearer(mundo.client, cabeceras)
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "REAUTH_REQUIRED"


def test_mfa_d03_desactivar_privilegiado_y_estandar(mundo, reloj_mfa):
    """MFA-D03: desactivar factor de privilegiado y estándar."""
    _, _, alta = _crear_privilegiado_con_factor(mundo, reloj_mfa)
    r = mundo.client.delete(f"{API}/auth/mfa", headers=alta.cabeceras)
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "MFA_REQUIRED_BY_POLICY"

    usuario_std, user_id_std, alta_std = _crear_estandar_con_factor(mundo, reloj_mfa)
    cabeceras_b = entrar_con_totp(
        mundo.client, reloj_mfa, usuario_std, alta_std.clave_manual
    )

    r = mundo.client.delete(f"{API}/auth/mfa", headers=alta_std.cabeceras)
    assert r.status_code == 204, r.text

    r = mundo.client.get(f"{API}/auth/me", headers=cabeceras_b)
    assert r.status_code == 401, r.text

    r = mundo.client.get(f"{API}/auth/mfa", headers=alta_std.cabeceras)
    assert r.status_code == 200, r.text
    assert r.json()["enabled"] is False

    db = mundo.factory()
    try:
        user_db = db.execute(
            select(User).where(User.id == user_id_std)
        ).scalars().first()
        assert user_db is not None
        assert user_db.mfa_enabled is False
    finally:
        db.close()

    r = login(mundo.client, usuario_std)
    assert r.status_code == 200, r.text
    assert r.json().get("status") == "AUTHENTICATED"


def test_mfa_d04_reset_correcto(mundo, reloj_mfa):
    """MFA-D04: reset administrativo correcto."""
    _, _, actor_alta = _crear_privilegiado_con_factor(mundo, reloj_mfa, admin=True)
    objetivo_usuario = _usuario(mundo)
    objetivo_id = crear_usuario(
        mundo, objetivo_usuario, rol="R_GESTOR_MFA", must_change_password=False
    )
    objetivo_alta = alta_por_desafio(mundo.client, reloj_mfa, objetivo_usuario)

    r = mundo.client.post(
        f"{API}/users/{objetivo_id}/mfa/reset", headers=actor_alta.cabeceras
    )
    assert r.status_code == 204, r.text

    r = mundo.client.get(f"{API}/auth/me", headers=objetivo_alta.cabeceras)
    assert r.status_code == 401, r.text

    r = login(mundo.client, objetivo_usuario)
    assert r.status_code == 200, r.text
    assert r.json().get("status") == "MFA_ENROLLMENT_REQUIRED"

    db = mundo.factory()
    try:
        user_db = db.execute(
            select(User).where(User.id == objetivo_id)
        ).scalars().first()
        assert user_db is not None
        assert user_db.mfa_enabled is False
        codigos = db.execute(
            select(MfaRecoveryCode).where(MfaRecoveryCode.user_id == objetivo_id)
        ).scalars().all()
        assert len(codigos) == 0
    finally:
        db.close()


def test_mfa_d05_sin_permiso(mundo, reloj_mfa):
    """MFA-D05: reset sin permiso."""
    actor_usuario = _usuario(mundo)
    crear_usuario(mundo, actor_usuario, rol="R_ALMACEN")
    actor_alta = alta_por_desafio(mundo.client, reloj_mfa, actor_usuario)

    objetivo_usuario = _usuario(mundo)
    objetivo_id = crear_usuario(
        mundo, objetivo_usuario, rol="R_GESTOR_MFA", must_change_password=False
    )
    alta_por_desafio(mundo.client, reloj_mfa, objetivo_usuario)

    r = mundo.client.post(
        f"{API}/users/{objetivo_id}/mfa/reset", headers=actor_alta.cabeceras
    )
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "PERMISSION_DENIED"


def test_mfa_d06_otro_tenant_o_inexistente(mundo, reloj_mfa):
    """MFA-D06: reset de otro tenant o id inexistente."""
    actor_usuario = _usuario(mundo)
    crear_usuario(mundo, actor_usuario, rol="R_GESTOR_MFA")
    actor_alta = alta_por_desafio(mundo.client, reloj_mfa, actor_usuario)

    objetivo_otro_tenant = _usuario(mundo)
    objetivo_otro_id = crear_usuario(
        mundo, objetivo_otro_tenant, admin=True, tenant="DEMO2"
    )
    alta_por_desafio(
        mundo.client, reloj_mfa, objetivo_otro_tenant, tenant="DEMO2"
    )

    r = mundo.client.post(
        f"{API}/users/{objetivo_otro_id}/mfa/reset", headers=actor_alta.cabeceras
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "USER_NOT_FOUND"

    r = mundo.client.post(
        f"{API}/users/{uuid.uuid4()}/mfa/reset", headers=actor_alta.cabeceras
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "USER_NOT_FOUND"


def test_mfa_d07_a_si_mismo(mundo, reloj_mfa):
    """MFA-D07: reset a sí mismo."""
    usuario = _usuario(mundo)
    user_id = crear_usuario(mundo, usuario, rol="R_GESTOR_MFA")
    alta = alta_por_desafio(mundo.client, reloj_mfa, usuario)

    r = mundo.client.post(
        f"{API}/users/{user_id}/mfa/reset", headers=alta.cabeceras
    )
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "MFA_RESET_SELF_FORBIDDEN"


def test_mfa_d08_techo(mundo, reloj_mfa):
    """MFA-D08: techo de privilegios."""
    actor_usuario = _usuario(mundo)
    crear_usuario(mundo, actor_usuario, rol="R_GESTOR_MFA")
    actor_alta = alta_por_desafio(mundo.client, reloj_mfa, actor_usuario)

    admin_usuario = _usuario(mundo)
    admin_id = crear_usuario(mundo, admin_usuario, admin=True)
    alta_por_desafio(mundo.client, reloj_mfa, admin_usuario)
    r = mundo.client.post(
        f"{API}/users/{admin_id}/mfa/reset", headers=actor_alta.cabeceras
    )
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "MFA_RESET_CEILING"

    almacen_usuario = _usuario(mundo)
    almacen_id = crear_usuario(mundo, almacen_usuario, rol="R_ALMACEN")
    alta_por_desafio(mundo.client, reloj_mfa, almacen_usuario)
    r = mundo.client.post(
        f"{API}/users/{almacen_id}/mfa/reset", headers=actor_alta.cabeceras
    )
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "MFA_RESET_CEILING"

    mismo_usuario = _usuario(mundo)
    mismo_id = crear_usuario(mundo, mismo_usuario, rol="R_GESTOR_MFA")
    alta_por_desafio(mundo.client, reloj_mfa, mismo_usuario)
    r = mundo.client.post(
        f"{API}/users/{mismo_id}/mfa/reset", headers=actor_alta.cabeceras
    )
    assert r.status_code == 204, r.text


def test_mfa_d09_reset_sin_reauth_reciente(mundo, reloj_mfa):
    """MFA-D09: reset sin reautenticación reciente."""
    actor_usuario = _usuario(mundo)
    crear_usuario(mundo, actor_usuario, rol="R_GESTOR_MFA")
    actor_alta = alta_por_desafio(mundo.client, reloj_mfa, actor_usuario)

    objetivo_usuario = _usuario(mundo)
    objetivo_id = crear_usuario(mundo, objetivo_usuario, rol="R_GESTOR_MFA")
    alta_por_desafio(mundo.client, reloj_mfa, objetivo_usuario)

    reloj_mfa.avanzar(301)
    r = mundo.client.post(
        f"{API}/users/{objetivo_id}/mfa/reset", headers=actor_alta.cabeceras
    )
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "REAUTH_REQUIRED"

    db = mundo.factory()
    try:
        user_db = db.execute(
            select(User).where(User.id == objetivo_id)
        ).scalars().first()
        assert user_db is not None
        assert user_db.mfa_enabled is True
    finally:
        db.close()


def test_mfa_d10_objetivo_sin_factor(mundo, reloj_mfa):
    """MFA-D10: reset de objetivo sin factor."""
    actor_usuario = _usuario(mundo)
    crear_usuario(mundo, actor_usuario, rol="R_GESTOR_MFA")
    actor_alta = alta_por_desafio(mundo.client, reloj_mfa, actor_usuario)

    objetivo_usuario = _usuario(mundo)
    objetivo_id = crear_usuario(mundo, objetivo_usuario, rol="R_GESTOR_MFA")

    r = mundo.client.post(
        f"{API}/users/{objetivo_id}/mfa/reset", headers=actor_alta.cabeceras
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "MFA_NOT_CONFIGURED"
