"""Pruebas de autoridad de sesión y MFA para roles privilegiados/sensibles."""

from __future__ import annotations

import base64
import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from mfa_apoyo import codigo_totp
from mfa_mundo import (
    API,
    CONTRASENA,
    MundoMfa,
    alta_por_desafio,
    crear_usuario,
    entrar_con_totp,
    eventos,
    login,
    mundo_mfa,
    sesiones_de,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, decode_token
from app.modules.identity_access.models import MfaFactor, Role, User, UserRole
from app.modules.identity_access.models import Session as AuthSession

pytest_plugins = ("mfa_apoyo",)


@pytest.fixture(scope="module")
def mundo() -> Iterator[MundoMfa]:
    """Crea un mundo MFA para todo el módulo."""
    with mundo_mfa() as m:
        yield m


def _cabeceras(resp) -> dict[str, str]:
    """Devuelve cabeceras Bearer a partir de una respuesta de login."""
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _limpiar_cookies(mundo: MundoMfa) -> None:
    """Limpia las cookies del cliente."""
    mundo.client.cookies.clear()


def _user_id(mundo: MundoMfa, usuario: str) -> str:
    """Obtiene el id del usuario por nombre."""
    db: Session = mundo.factory()
    try:
        user = db.execute(
            select(User).where(
                User.username == usuario, User.tenant_id == mundo.tenant_id
            )
        ).scalars().first()
        assert user is not None
        return str(user.id)
    finally:
        db.close()


def _role_id(mundo: MundoMfa, codigo: str) -> str:
    """Obtiene el id de un rol por código."""
    db: Session = mundo.factory()
    try:
        role = db.execute(
            select(Role).where(Role.code == codigo, Role.company_id.is_(None))
        ).scalars().first()
        assert role is not None
        return str(role.id)
    finally:
        db.close()


def _factor_id(mundo: MundoMfa, usuario: str) -> str | None:
    """Obtiene el primer factor del usuario."""
    db: Session = mundo.factory()
    try:
        user_id = _user_id(mundo, usuario)
        factor = db.execute(
            select(MfaFactor).where(MfaFactor.user_id == user_id)
        ).scalars().first()
        return str(factor.id) if factor else None
    finally:
        db.close()


def _factor_status(mundo: MundoMfa, factor_id: str) -> str | None:
    """Obtiene el estado de un factor."""
    db: Session = mundo.factory()
    try:
        factor = db.execute(
            select(MfaFactor).where(MfaFactor.id == factor_id)
        ).scalars().first()
        return factor.status if factor else None
    finally:
        db.close()


def _factor_key_id(mundo: MundoMfa, factor_id: str) -> str | None:
    """Obtiene el id de clave de un factor."""
    db: Session = mundo.factory()
    try:
        factor = db.execute(
            select(MfaFactor).where(MfaFactor.id == factor_id)
        ).scalars().first()
        return factor.key_id if factor else None
    finally:
        db.close()


def _mfa_enabled(mundo: MundoMfa, user_id: str) -> bool:
    """Devuelve si el MFA está habilitado para el usuario."""
    db: Session = mundo.factory()
    try:
        user = db.execute(select(User).where(User.id == user_id)).scalars().first()
        return bool(user.mfa_enabled) if user else False
    finally:
        db.close()


def _factor_activo_de(mundo: MundoMfa, user_id: str) -> bool:
    """Devuelve si existe un factor activo del usuario."""
    db: Session = mundo.factory()
    try:
        factor = db.execute(
            select(MfaFactor).where(
                MfaFactor.user_id == user_id, MfaFactor.status == "ACTIVE"
            )
        ).scalars().first()
        return factor is not None
    finally:
        db.close()


def _validar_invariante(mundo: MundoMfa) -> None:
    """Valida el invariante de fuente única para todos los usuarios del tenant."""
    db: Session = mundo.factory()
    try:
        users = db.execute(
            select(User).where(User.tenant_id == mundo.tenant_id)
        ).scalars().all()
        for user in users:
            assert _mfa_enabled(mundo, str(user.id)) == _factor_activo_de(
                mundo, str(user.id)
            )
    finally:
        db.close()


def test_mfa_h01_revocacion_inmediata(mundo: MundoMfa):
    """MFA-H01: revocación inmediata de sesión."""
    usuario = f"u_{uuid.uuid4().hex[:10]}"
    crear_usuario(mundo, usuario, rol="R_CONSULTA")

    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    a = _cabeceras(r)
    _limpiar_cookies(mundo)

    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    b = _cabeceras(r)
    _limpiar_cookies(mundo)

    token_a = a["Authorization"].split(" ", 1)[1]
    sid_a = decode_token(token_a)["sid"]
    db = mundo.factory()
    try:
        sesion_a = db.execute(
            select(AuthSession).where(AuthSession.family_id == sid_a)
        ).scalars().first()
        assert sesion_a is not None
        id_a = sesion_a.id
    finally:
        db.close()

    r = mundo.client.delete(f"{API}/auth/sessions/{id_a}", headers=b)
    assert r.status_code == 200, r.text

    r = mundo.client.get(f"{API}/auth/me", headers=a)
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "SESSION_REVOKED", r.text

    r = mundo.client.get(f"{API}/auth/me", headers=b)
    assert r.status_code == 200, r.text


def test_mfa_h01b_logout_revoca_familia(mundo: MundoMfa):
    """MFA-H01b: logout revoca la familia de sesión."""
    usuario = f"u_{uuid.uuid4().hex[:10]}"
    crear_usuario(mundo, usuario, rol="R_CONSULTA")

    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    cookie = r.cookies.get("kontrol_refresh")
    assert cookie is not None
    _limpiar_cookies(mundo)

    r = mundo.client.post(f"{API}/auth/logout", cookies={"kontrol_refresh": cookie})
    assert r.status_code == 200, r.text

    r = mundo.client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "SESSION_REVOKED", r.text


def test_mfa_h02_token_sin_sid(mundo: MundoMfa):
    """MFA-H02: token sin sid."""
    usuario = f"u_{uuid.uuid4().hex[:10]}"
    user_id = crear_usuario(mundo, usuario, rol="R_CONSULTA")
    token = create_access_token(user_id, extra={"tenant_id": mundo.tenant_id})

    r = mundo.client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "AUTH_INVALID_TOKEN", r.text


def test_mfa_h02b_rotacion_conserva_familia(mundo: MundoMfa):
    """MFA-H02b: la rotación conserva la familia de sesión."""
    usuario = f"u_{uuid.uuid4().hex[:10]}"
    crear_usuario(mundo, usuario, rol="R_CONSULTA")

    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    viejo = r.json()["access_token"]
    cookie_vieja = r.cookies.get("kontrol_refresh")
    assert cookie_vieja is not None
    _limpiar_cookies(mundo)

    token_viejo_sid = decode_token(viejo)["sid"]
    db = mundo.factory()
    try:
        familia_vieja = db.execute(
            select(AuthSession).where(AuthSession.family_id == token_viejo_sid)
        ).scalars().all()
        assert familia_vieja
        inicial = familia_vieja[0]
        for row in familia_vieja:
            if row.revoked_at is None:
                inicial = row
                break
    finally:
        db.close()

    r = mundo.client.post(
        f"{API}/auth/refresh", cookies={"kontrol_refresh": cookie_vieja}
    )
    assert r.status_code == 200, r.text
    nuevo = r.json()["access_token"]
    cookie_nueva = r.cookies.get("kontrol_refresh")
    assert cookie_nueva is not None
    _limpiar_cookies(mundo)

    for token in (viejo, nuevo):
        r = mundo.client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text

    token_nuevo_sid = decode_token(nuevo)["sid"]
    db = mundo.factory()
    try:
        rotacion = db.execute(
            select(AuthSession)
            .where(AuthSession.family_id == token_nuevo_sid)
            .order_by(AuthSession.created_at)
        ).scalars().all()
        assert rotacion
        nueva_fila = [row for row in rotacion if row.revoked_at is None][0]
    finally:
        db.close()

    assert nueva_fila.family_id == inicial.family_id
    assert nueva_fila.auth_method == inicial.auth_method
    assert nueva_fila.mfa_verified_at == inicial.mfa_verified_at
    assert nueva_fila.reauth_at == inicial.reauth_at

    r = mundo.client.post(
        f"{API}/auth/logout", cookies={"kontrol_refresh": cookie_nueva}
    )
    assert r.status_code == 200, r.text
    _limpiar_cookies(mundo)

    for token in (viejo, nuevo):
        r = mundo.client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401, r.text
        assert r.json().get("code") == "SESSION_REVOKED", r.text


def test_mfa_h03_elevacion_con_revocacion(mundo: MundoMfa, reloj_mfa):
    """MFA-H03: elevación de política con revocación de sesión."""
    usuario = f"u_{uuid.uuid4().hex[:10]}"
    user_id = crear_usuario(mundo, usuario, rol="R_CONSULTA")

    admin_user = f"u_{uuid.uuid4().hex[:10]}"
    crear_usuario(mundo, admin_user, admin=True)
    admin_headers = alta_por_desafio(mundo.client, reloj_mfa, admin_user).cabeceras

    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    _limpiar_cookies(mundo)

    role_id = _role_id(mundo, "R_ALMACEN")
    r = mundo.client.post(
        f"{API}/users/{user_id}/roles",
        json={"role_id": role_id},
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "SESSION_REVOKED", r.text

    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    assert r.json().get("status") == "MFA_ENROLLMENT_REQUIRED", r.text


def test_mfa_h03b_elevacion_sin_revocacion(mundo: MundoMfa):
    """MFA-H03b: elevación directa en BD sin revocación inmediata."""
    usuario = f"u_{uuid.uuid4().hex[:10]}"
    user_id = crear_usuario(mundo, usuario, rol="R_CONSULTA")

    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    cookie = r.cookies.get("kontrol_refresh")
    assert cookie is not None
    _limpiar_cookies(mundo)

    db: Session = mundo.factory()
    try:
        role = db.execute(
            select(Role).where(Role.code == "R_ALMACEN", Role.company_id.is_(None))
        ).scalars().first()
        assert role is not None
        db.add(UserRole(user_id=user_id, role_id=str(role.id), company_id=None))
        db.commit()
    finally:
        db.close()

    r = mundo.client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "MFA_REQUIRED", r.text

    r = mundo.client.post(
        f"{API}/auth/refresh", cookies={"kontrol_refresh": cookie}
    )
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "MFA_REQUIRED", r.text

    rows = sesiones_de(mundo, user_id)
    assert rows
    assert all(row.revoked_at is not None for row in rows)


def test_mfa_h06_degradacion(mundo: MundoMfa, reloj_mfa):
    """MFA-H06: degradación de política revoca sesiones."""
    usuario = f"u_{uuid.uuid4().hex[:10]}"
    user_id = crear_usuario(mundo, usuario, rol="R_ALMACEN")
    alta = alta_por_desafio(mundo.client, reloj_mfa, usuario)
    token = alta.respuesta["access_token"]
    _limpiar_cookies(mundo)

    admin_user = f"u_{uuid.uuid4().hex[:10]}"
    crear_usuario(mundo, admin_user, admin=True)
    admin_headers = alta_por_desafio(mundo.client, reloj_mfa, admin_user).cabeceras

    role_id = _role_id(mundo, "R_ALMACEN")
    r = mundo.client.delete(
        f"{API}/users/{user_id}/roles/{role_id}", headers=admin_headers
    )
    assert r.status_code == 200, r.text

    r = mundo.client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "SESSION_REVOKED", r.text


def test_mfa_h04_cambio_propio_de_contrasena(mundo: MundoMfa):
    """MFA-H04: cambio propio de contraseña revoca otras sesiones."""
    usuario = f"u_{uuid.uuid4().hex[:10]}"
    crear_usuario(mundo, usuario, rol="R_CONSULTA")

    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    a = _cabeceras(r)
    cookie_a = r.cookies.get("kontrol_refresh")
    assert cookie_a is not None
    _limpiar_cookies(mundo)

    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    b = _cabeceras(r)
    cookie_b = r.cookies.get("kontrol_refresh")
    assert cookie_b is not None
    _limpiar_cookies(mundo)

    r = mundo.client.post(
        f"{API}/auth/change-password",
        json={"current_password": CONTRASENA, "new_password": "Kontrol2027Nueva!"},
        headers=a,
        cookies={"kontrol_refresh": cookie_a},
    )
    assert r.status_code == 200, r.text
    _limpiar_cookies(mundo)

    r = mundo.client.get(f"{API}/auth/me", headers=a)
    assert r.status_code == 200, r.text

    r = mundo.client.get(f"{API}/auth/me", headers=b)
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "SESSION_REVOKED", r.text


def test_mfa_h05_restablecimiento_por_token(mundo: MundoMfa, reloj_mfa):
    """MFA-H05: restablecimiento por token revoca todas las sesiones."""
    usuario = f"u_{uuid.uuid4().hex[:10]}"
    crear_usuario(mundo, usuario, rol="R_GESTOR_MFA")
    alta = alta_por_desafio(mundo.client, reloj_mfa, usuario)
    factor_id = _factor_id(mundo, usuario)
    assert factor_id is not None

    a = entrar_con_totp(mundo.client, reloj_mfa, usuario, alta.clave_manual)
    _limpiar_cookies(mundo)
    b = entrar_con_totp(mundo.client, reloj_mfa, usuario, alta.clave_manual)
    _limpiar_cookies(mundo)

    r = mundo.client.post(
        f"{API}/auth/password-reset/request",
        json={"tenant_code": "DEMO", "username": usuario},
    )
    assert r.status_code == 200, r.text
    reset_token = r.json()["reset_token"]

    r = mundo.client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "Kontrol2027Nueva!"},
    )
    assert r.status_code == 200, r.text

    for headers in (a, b):
        r = mundo.client.get(f"{API}/auth/me", headers=headers)
        assert r.status_code == 401, r.text
        assert r.json().get("code") == "SESSION_REVOKED", r.text

    assert _factor_status(mundo, factor_id) == "ACTIVE"


def test_mfa_h07_sesion_caducada(mundo: MundoMfa):
    """MFA-H07: sesión caducada."""
    usuario = f"u_{uuid.uuid4().hex[:10]}"
    user_id = crear_usuario(mundo, usuario, rol="R_CONSULTA")

    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]

    db: Session = mundo.factory()
    try:
        rows = db.execute(
            select(AuthSession).where(AuthSession.user_id == user_id)
        ).scalars().all()
        assert rows
        pasado = datetime.now(UTC) - timedelta(days=1)
        for row in rows:
            row.expires_at = pasado
        db.commit()
    finally:
        db.close()

    r = mundo.client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "SESSION_REVOKED", r.text


def test_mfa_i05_invariante_fuente_unica(mundo: MundoMfa, reloj_mfa):
    """MFA-I05: invariante de fuente única mfa_enabled."""
    privilegiado = f"u_{uuid.uuid4().hex[:10]}"
    p_id = crear_usuario(mundo, privilegiado, rol="R_GESTOR_MFA")
    estandar = f"u_{uuid.uuid4().hex[:10]}"
    e_id = crear_usuario(mundo, estandar, rol="R_CONSULTA")

    assert _mfa_enabled(mundo, p_id) is False
    assert _mfa_enabled(mundo, e_id) is False

    alta_p = alta_por_desafio(mundo.client, reloj_mfa, privilegiado)
    assert _mfa_enabled(mundo, p_id) is True
    assert _factor_activo_de(mundo, p_id) is True
    _validar_invariante(mundo)

    # Reemplazo por API
    r = mundo.client.post(
        f"{API}/auth/mfa/enrollment", json={}, headers=alta_p.cabeceras
    )
    assert r.status_code == 200, r.text
    nueva_clave = r.json()["manual_key"]
    reloj_mfa.siguiente_paso()
    codigo = codigo_totp(nueva_clave, reloj_mfa.ahora())
    r = mundo.client.post(
        f"{API}/auth/mfa/enrollment/confirm",
        json={"code": codigo},
        headers=alta_p.cabeceras,
    )
    assert r.status_code == 200, r.text
    _validar_invariante(mundo)

    # Reset administrativo por API
    admin_user = f"u_{uuid.uuid4().hex[:10]}"
    crear_usuario(mundo, admin_user, admin=True)
    admin_headers = alta_por_desafio(mundo.client, reloj_mfa, admin_user).cabeceras
    r = mundo.client.post(
        f"{API}/users/{p_id}/mfa/reset", headers=admin_headers
    )
    assert r.status_code == 204, r.text
    _validar_invariante(mundo)

    alta_por_desafio(mundo.client, reloj_mfa, privilegiado)
    assert _factor_activo_de(mundo, p_id) is True
    assert _mfa_enabled(mundo, p_id) is True
    _validar_invariante(mundo)

    r = login(mundo.client, estandar)
    assert r.status_code == 200, r.text
    cabeceras_e = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = mundo.client.post(f"{API}/auth/mfa/enrollment", json={}, headers=cabeceras_e)
    assert r.status_code == 200, r.text
    clave_e = r.json()["manual_key"]
    reloj_mfa.siguiente_paso()
    r = mundo.client.post(
        f"{API}/auth/mfa/enrollment/confirm",
        json={"code": codigo_totp(clave_e, reloj_mfa.ahora())},
        headers=cabeceras_e,
    )
    assert r.status_code == 200, r.text
    assert _factor_activo_de(mundo, e_id) is True
    assert _mfa_enabled(mundo, e_id) is True
    _validar_invariante(mundo)

    # Desactivación del estándar por API
    r = mundo.client.delete(f"{API}/auth/mfa", headers=cabeceras_e)
    assert r.status_code == 204, r.text
    assert _factor_activo_de(mundo, e_id) is False
    assert _mfa_enabled(mundo, e_id) is False
    _validar_invariante(mundo)


def test_mfa_e01_rotura_cristal(mundo: MundoMfa, reloj_mfa, capsys):
    """MFA-E01: rotura de cristal por CLI."""
    usuario = f"u_{uuid.uuid4().hex[:10]}"
    user_id = crear_usuario(mundo, usuario, rol="R_GESTOR_MFA")
    alta = alta_por_desafio(mundo.client, reloj_mfa, usuario)
    token = alta.respuesta["access_token"]
    _limpiar_cookies(mundo)

    from app.modules.identity_access.mfa_breakglass import main as mfa_breakglass_main

    salida = mfa_breakglass_main(
        ["--tenant", "DEMO", "--username", usuario, "--confirm", usuario]
    )
    capturado = capsys.readouterr()
    assert salida == 0
    assert alta.clave_manual not in capturado.out
    for codigo in alta.codigos:
        assert codigo not in capturado.out

    assert _mfa_enabled(mundo, user_id) is False
    assert _factor_activo_de(mundo, user_id) is False

    r = mundo.client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401, r.text

    evs = eventos(mundo, "MFA_RESET_BREAKGLASS")
    assert any(e.source == "CLI" and e.entity_id == user_id for e in evs)


def test_mfa_e02_confirm_distinto(mundo: MundoMfa, reloj_mfa):
    """MFA-E02: confirm distinto al usuario."""
    usuario = f"u_{uuid.uuid4().hex[:10]}"
    user_id = crear_usuario(mundo, usuario, rol="R_GESTOR_MFA")
    alta_por_desafio(mundo.client, reloj_mfa, usuario)
    factor_id = _factor_id(mundo, usuario)
    assert factor_id is not None

    from app.modules.identity_access.mfa_breakglass import main as mfa_breakglass_main

    resultado = mfa_breakglass_main(
        ["--tenant", "DEMO", "--username", usuario, "--confirm", "otro"]
    )
    assert resultado == 2
    assert _factor_status(mundo, factor_id) == "ACTIVE"
    assert _mfa_enabled(mundo, user_id) is True


def test_mfa_e03_usuario_inexistente(mundo: MundoMfa):
    """MFA-E03: usuario inexistente en rotura de cristal."""
    from app.modules.identity_access.mfa_breakglass import main as mfa_breakglass_main

    resultado = mfa_breakglass_main(
        ["--tenant", "DEMO", "--username", "no_existe", "--confirm", "no_existe"]
    )
    assert resultado == 1


def test_mfa_e04_no_hay_ruta_http_breakglass(mundo: MundoMfa):
    """MFA-E04: no existe ruta HTTP de rotura de cristal."""
    rutas = " ".join(route.path for route in mundo.client.app.routes)
    assert "breakglass" not in rutas
    assert "break-glass" not in rutas


def test_mfa_k10_recifrado(mundo: MundoMfa, reloj_mfa, monkeypatch):
    """MFA-K10: recifrado de factores."""
    usuario = f"u_{uuid.uuid4().hex[:10]}"
    crear_usuario(mundo, usuario, rol="R_GESTOR_MFA")
    alta = alta_por_desafio(mundo.client, reloj_mfa, usuario)
    factor_id = _factor_id(mundo, usuario)
    assert factor_id is not None

    anillo_inicial = os.environ.get("KONTROL_MFA_KEYS", "")
    nueva_clave = base64.urlsafe_b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("KONTROL_MFA_KEYS", f"k2rot:{nueva_clave},{anillo_inicial}")
    get_settings.cache_clear()

    try:
        from app.modules.identity_access.mfa_rekey import main as mfa_rekey_main

        resultado = mfa_rekey_main([])
        assert resultado == 0
        assert _factor_key_id(mundo, factor_id) == "k2rot"

        r = login(mundo.client, usuario)
        assert r.status_code == 200, r.text
        assert r.json().get("status") == "MFA_REQUIRED", r.text
        challenge_token = r.json()["challenge_token"]
        reloj_mfa.siguiente_paso()
        codigo = codigo_totp(alta.clave_manual, reloj_mfa.ahora())
        r = mundo.client.post(
            f"{API}/auth/mfa/verify",
            json={"challenge_token": challenge_token, "code": codigo},
        )
        assert r.status_code == 200, r.text
    finally:
        monkeypatch.setenv("KONTROL_MFA_KEYS", anillo_inicial)
        get_settings.cache_clear()
