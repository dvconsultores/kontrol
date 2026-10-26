"""Pruebas rojas del contrato MFA para login de alta y desafío."""

from __future__ import annotations

import base64
import os
import re
import uuid
from datetime import timedelta

import pytest
from mfa_apoyo import codigo_totp
from mfa_mundo import (
    alta_por_desafio,
    crear_usuario,
    entrar_con_totp,
    login,
    mundo_mfa,
    sesiones_de,
)
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import decode_token
from app.modules.identity_access.models import MfaFactor, MfaRecoveryCode, User
from app.modules.identity_access.models import Session as AuthSession

# La fixture `reloj_mfa` vive en el helper compartido (mismo patrón que tests.conftest_multicompany).
pytest_plugins = ("mfa_apoyo",)


@pytest.fixture(scope="module")
def mundo():
    with mundo_mfa() as m:
        yield m


def assert_no_cookie(r, mensaje: str) -> None:
    assert "kontrol_refresh" not in r.cookies, mensaje


def _usuario_unico(prefijo: str) -> str:
    return f"u_{prefijo}_{uuid.uuid4().hex[:10]}"


def test_mfa_b01_privilegiado_sin_factor_enrollment_required(mundo):
    """MFA-B01: privilegiado sin factor recibe MFA_ENROLLMENT_REQUIRED sin sesión ni cookie."""
    usuario = _usuario_unico("b01")
    crear_usuario(mundo, usuario, admin=True)
    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "MFA_ENROLLMENT_REQUIRED", r.text
    assert isinstance(data.get("challenge_token"), str) and data["challenge_token"], r.text
    assert data.get("expires_in") == 300, r.text
    assert "access_token" not in data, r.text
    assert_no_cookie(r, "respuesta de enrollment no debe incluir cookie")


def test_mfa_b02_sensible_enrollment_required(mundo):
    """MFA-B02: rol sensible sin factor recibe MFA_ENROLLMENT_REQUIRED."""
    usuario = _usuario_unico("b02")
    crear_usuario(mundo, usuario, rol="R_ALMACEN")
    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "MFA_ENROLLMENT_REQUIRED", r.text


def test_mfa_b03_estandar_authenticated(mundo):
    """MFA-B03: usuario estándar se autentica con contraseña y cookie."""
    usuario = _usuario_unico("b03")
    crear_usuario(mundo, usuario, rol="R_CONSULTA")
    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "AUTHENTICATED", r.text
    assert data.get("access_token"), r.text
    assert "kontrol_refresh" in r.cookies, r.text
    me = mundo.client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    assert me.status_code == 200, me.text


def test_mfa_b15_privilegiado_sin_sesion_tras_login(mundo, reloj_mfa):
    """MFA-B15: el desafío de enrollment no crea ninguna sesión de usuario."""
    usuario = _usuario_unico("b15")
    user_id = crear_usuario(mundo, usuario, admin=True)
    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "MFA_ENROLLMENT_REQUIRED", r.text
    assert sesiones_de(mundo, user_id) == []


def test_mfa_b16_contrasena_erronea_sin_desafio(mundo):
    """MFA-B16: contraseña incorrecta devuelve AUTH_INVALID_CREDENTIALS sin desafío."""
    usuario = _usuario_unico("b16")
    crear_usuario(mundo, usuario, admin=True)
    r = login(mundo.client, usuario, contrasena="ContrasenaMala!1")
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "AUTH_INVALID_CREDENTIALS", r.text
    assert "challenge_token" not in r.json(), r.text


def test_mfa_a01_alta_por_desafio(mundo, reloj_mfa):
    """MFA-A01: enrollment devuelve otpauth_uri, manual_key, qr_svg_data_uri y expires_in."""
    usuario = _usuario_unico("a01")
    crear_usuario(mundo, usuario, admin=True)
    r = login(mundo.client, usuario)
    challenge_token = r.json()["challenge_token"]

    r = mundo.client.post(
        "/api/v1/auth/mfa/enrollment", json={"challenge_token": challenge_token}
    )
    assert r.status_code == 200, r.text
    assert "no-store" in r.headers.get("cache-control", "").lower(), r.text
    data = r.json()
    for key in ("otpauth_uri", "manual_key", "qr_svg_data_uri", "expires_in"):
        assert key in data, (key, r.text)
    assert data["expires_in"] == 600, r.text
    assert data["otpauth_uri"].startswith("otpauth://totp/KONTROL:"), r.text
    secret = data["otpauth_uri"].split("secret=", 1)[1].split("&", 1)[0]
    assert secret == data["manual_key"].replace(" ", ""), r.text
    assert data["qr_svg_data_uri"].startswith("data:image/svg+xml"), r.text


def test_mfa_a02_sin_confirmar_pending_y_no_activo(mundo, reloj_mfa):
    """MFA-A02: alta sin confirmar deja factor PENDING y mfa_enabled en False."""
    usuario = _usuario_unico("a02")
    user_id = crear_usuario(mundo, usuario, admin=True)
    r = login(mundo.client, usuario)
    challenge_token = r.json()["challenge_token"]
    r = mundo.client.post(
        "/api/v1/auth/mfa/enrollment", json={"challenge_token": challenge_token}
    )
    assert r.status_code == 200, r.text

    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "MFA_ENROLLMENT_REQUIRED", r.text

    db = mundo.factory()
    try:
        factor = (
            db.execute(select(MfaFactor).where(MfaFactor.user_id == user_id))
            .scalars()
            .first()
        )
        assert factor is not None
        assert factor.status == "PENDING", r.text
        user = db.execute(select(User).where(User.id == user_id)).scalars().first()
        assert user.mfa_enabled is False, r.text
    finally:
        db.close()


def test_mfa_a03_confirm_codigo_erroneo_y_correcto(mundo, reloj_mfa):
    """MFA-A03: confirm con código erróneo falla y el correcto activa 10 recovery codes."""
    usuario = _usuario_unico("a03")
    user_id = crear_usuario(mundo, usuario, admin=True)
    r = login(mundo.client, usuario)
    challenge_token = r.json()["challenge_token"]
    r = mundo.client.post(
        "/api/v1/auth/mfa/enrollment", json={"challenge_token": challenge_token}
    )
    manual_key = r.json()["manual_key"]

    r = mundo.client.post(
        "/api/v1/auth/mfa/enrollment/confirm",
        json={"challenge_token": challenge_token, "code": "000000"},
    )
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "MFA_INVALID_CODE", r.text

    reloj_mfa.siguiente_paso()
    code = codigo_totp(manual_key, reloj_mfa.ahora())
    r = mundo.client.post(
        "/api/v1/auth/mfa/enrollment/confirm",
        json={"challenge_token": challenge_token, "code": code},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "AUTHENTICATED", r.text
    assert data.get("access_token"), r.text
    assert "kontrol_refresh" in r.cookies, r.text
    codes = data["recovery_codes"]
    assert len(codes) == 10, r.text
    patron = re.compile(r"^[A-Z2-7]{4}-[A-Z2-7]{4}-[A-Z2-7]{4}-[A-Z2-7]{4}$")
    assert len(set(codes)) == 10, r.text
    assert all(patron.match(c) for c in codes), r.text

    db = mundo.factory()
    try:
        factor = (
            db.execute(select(MfaFactor).where(MfaFactor.user_id == user_id))
            .scalars()
            .first()
        )
        assert factor.status == "ACTIVE", r.text
        user = db.execute(select(User).where(User.id == user_id)).scalars().first()
        assert user.mfa_enabled is True, r.text
    finally:
        db.close()


def test_mfa_a04_login_con_factor_mfa_required(mundo, reloj_mfa):
    """MFA-A04: login con factor activo devuelve MFA_REQUIRED con los dos métodos."""
    usuario = _usuario_unico("a04")
    crear_usuario(mundo, usuario, admin=True)
    alta_por_desafio(mundo.client, reloj_mfa, usuario)

    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "MFA_REQUIRED", r.text
    assert data["methods"] == ["TOTP", "RECOVERY_CODE"], r.text


def test_mfa_a05_reiniciar_alta_sustituye_pendiente(mundo, reloj_mfa):
    """MFA-A05: reiniciar el alta cambia la clave y solo vale el último código."""
    usuario = _usuario_unico("a05")
    crear_usuario(mundo, usuario, admin=True)
    r = login(mundo.client, usuario)
    challenge_token = r.json()["challenge_token"]

    r = mundo.client.post(
        "/api/v1/auth/mfa/enrollment", json={"challenge_token": challenge_token}
    )
    primera = r.json()["manual_key"]
    r = mundo.client.post(
        "/api/v1/auth/mfa/enrollment", json={"challenge_token": challenge_token}
    )
    segunda = r.json()["manual_key"]
    assert primera != segunda, r.text

    reloj_mfa.siguiente_paso()
    code_primera = codigo_totp(primera, reloj_mfa.ahora())
    r = mundo.client.post(
        "/api/v1/auth/mfa/enrollment/confirm",
        json={"challenge_token": challenge_token, "code": code_primera},
    )
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "MFA_INVALID_CODE", r.text

    code_segunda = codigo_totp(segunda, reloj_mfa.ahora())
    r = mundo.client.post(
        "/api/v1/auth/mfa/enrollment/confirm",
        json={"challenge_token": challenge_token, "code": code_segunda},
    )
    assert r.status_code == 200, r.text


def obtener_desafio(mundo, usuario):
    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "MFA_REQUIRED", r.text
    return r.json()["challenge_token"]


def test_mfa_a06_proposito_desafio_enroll_vs_login(mundo, reloj_mfa):
    """MFA-A06: desafío de enrollment no vale en verify y el de login no vale en enrollment."""
    usuario = _usuario_unico("a06")
    crear_usuario(mundo, usuario, admin=True)
    r = login(mundo.client, usuario)
    enroll_token = r.json()["challenge_token"]
    r = mundo.client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge_token": enroll_token, "code": "000000"},
    )
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "MFA_CHALLENGE_INVALID", r.text

    alta_por_desafio(mundo.client, reloj_mfa, usuario)
    login_token = obtener_desafio(mundo, usuario)
    r = mundo.client.post(
        "/api/v1/auth/mfa/enrollment", json={"challenge_token": login_token}
    )
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "MFA_CHALLENGE_INVALID", r.text


def test_mfa_a08_secreto_cifrado(mundo, reloj_mfa):
    """MFA-A08: secret_ciphertext no contiene la clave manual en claro ni decodificada."""
    usuario = _usuario_unico("a08")
    user_id = crear_usuario(mundo, usuario, admin=True)
    alta = alta_por_desafio(mundo.client, reloj_mfa, usuario)

    db = mundo.factory()
    try:
        factor = (
            db.execute(select(MfaFactor).where(MfaFactor.user_id == user_id))
            .scalars()
            .first()
        )
        ring = os.environ.get("KONTROL_MFA_KEYS", "")
        kid = ring.split(":")[0] if ring else ""
        assert factor.key_id == kid, "key_id debe coincidir con el kid del anillo"
        padded = alta.clave_manual.replace(" ", "").upper()
        b32 = base64.b32decode(padded + "=" * (-len(padded) % 8))
        assert b32 not in factor.secret_ciphertext, "el secreto decodificado no debe estar en claro"
        assert alta.clave_manual.encode("utf-8") not in factor.secret_ciphertext, (
            "la clave manual no debe estar en claro"
        )
    finally:
        db.close()


def test_mfa_a09_recuperacion_solo_hash(mundo, reloj_mfa):
    """MFA-A09: los códigos de recuperación se guardan solo como hash SHA-like de 64 hex."""
    usuario = _usuario_unico("a09")
    user_id = crear_usuario(mundo, usuario, admin=True)
    alta = alta_por_desafio(mundo.client, reloj_mfa, usuario)

    db = mundo.factory()
    try:
        rows = (
            db.execute(
                select(MfaRecoveryCode).where(MfaRecoveryCode.user_id == user_id)
            )
            .scalars()
            .all()
        )
        assert len(rows) == 10, "debe haber 10 códigos de recuperación"
        for row in rows:
            assert re.fullmatch(r"[0-9a-f]{64}", row.code_hash), (
                "code_hash debe ser 64 hex"
            )
            cleartext = [c.replace("-", "").lower() for c in alta.codigos]
            for code in cleartext:
                assert code not in row.code_hash.lower(), (
                    "ningún código debe figurar en claro"
                )
    finally:
        db.close()


def test_mfa_b04_totp_authenticated_session(mundo, reloj_mfa):
    """MFA-B04: verify TOTP crea sesión PASSWORD_TOTP con sid igual a family_id."""
    usuario = _usuario_unico("b04")
    user_id = crear_usuario(mundo, usuario, admin=True)
    alta = alta_por_desafio(mundo.client, reloj_mfa, usuario)
    headers = entrar_con_totp(mundo.client, reloj_mfa, usuario, alta.clave_manual)
    access_token = headers["Authorization"].split(" ", 1)[1]
    sid = decode_token(access_token)["sid"]

    me = mundo.client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200, me.text

    db = mundo.factory()
    try:
        session = (
            db.execute(
                select(AuthSession).where(AuthSession.family_id == sid)
            )
            .scalars()
            .first()
        )
        assert session is not None, "debe existir la sesión del token devuelto"
        assert session.user_id == user_id, "la sesión debe pertenecer al usuario"
        assert session.auth_method == "PASSWORD_TOTP", "auth_method debe ser PASSWORD_TOTP"
        assert session.mfa_verified_at is not None, "mfa_verified_at no debe ser nulo"
        payload = decode_token(access_token)
        assert payload["sid"] == session.family_id, "sid del token debe coincidir con family_id"
    finally:
        db.close()


def test_mfa_b05_verify_codigo_erroneo(mundo, reloj_mfa):
    """MFA-B05: código TOTP erróneo devuelve MFA_INVALID_CODE y attempts_remaining=4."""
    usuario = _usuario_unico("b05")
    crear_usuario(mundo, usuario, admin=True)
    alta_por_desafio(mundo.client, reloj_mfa, usuario)
    token = obtener_desafio(mundo, usuario)

    r = mundo.client.post(
        "/api/v1/auth/mfa/verify", json={"challenge_token": token, "code": "999999"}
    )
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "MFA_INVALID_CODE", r.text
    assert r.json()["details"]["attempts_remaining"] == 4, r.text
    assert "999999" not in r.text, "el cuerpo no debe incluir el código enviado"


def test_mfa_b06_antirrepeticion(mundo, reloj_mfa):
    """MFA-B06: reutilizar el mismo paso TOTP devuelve MFA_CODE_ALREADY_USED."""
    usuario = _usuario_unico("b06")
    crear_usuario(mundo, usuario, admin=True)
    alta = alta_por_desafio(mundo.client, reloj_mfa, usuario)

    token = obtener_desafio(mundo, usuario)
    reloj_mfa.siguiente_paso()
    codigo = codigo_totp(alta.clave_manual, reloj_mfa.ahora())
    r = mundo.client.post(
        "/api/v1/auth/mfa/verify", json={"challenge_token": token, "code": codigo}
    )
    assert r.status_code == 200, r.text

    token = obtener_desafio(mundo, usuario)
    r = mundo.client.post(
        "/api/v1/auth/mfa/verify", json={"challenge_token": token, "code": codigo}
    )
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "MFA_CODE_ALREADY_USED", r.text


def test_mfa_b08_desafio_consumido_y_caducidad(mundo, reloj_mfa):
    """MFA-B08: desafío consumido y desafío caducado devuelven MFA_CHALLENGE_INVALID."""
    usuario = _usuario_unico("b08")
    crear_usuario(mundo, usuario, admin=True)
    alta = alta_por_desafio(mundo.client, reloj_mfa, usuario)

    token = obtener_desafio(mundo, usuario)
    reloj_mfa.siguiente_paso()
    codigo = codigo_totp(alta.clave_manual, reloj_mfa.ahora())
    r = mundo.client.post(
        "/api/v1/auth/mfa/verify", json={"challenge_token": token, "code": codigo}
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(
        "/api/v1/auth/mfa/verify", json={"challenge_token": token, "code": codigo}
    )
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "MFA_CHALLENGE_INVALID", r.text

    token = obtener_desafio(mundo, usuario)
    reloj_mfa.avanzar(301)
    r = mundo.client.post(
        "/api/v1/auth/mfa/verify", json={"challenge_token": token, "code": codigo}
    )
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "MFA_CHALLENGE_INVALID", r.text


def test_mfa_b09_challenge_no_es_credencial(mundo, reloj_mfa):
    """MFA-B09: challenge_token no sirve como Bearer para endpoints protegidos."""
    usuario = _usuario_unico("b09")
    crear_usuario(mundo, usuario, admin=True)
    challenge = login(mundo.client, usuario).json()["challenge_token"]

    headers = {"Authorization": f"Bearer {challenge}"}
    assert mundo.client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert mundo.client.get("/api/v1/users", headers=headers).status_code == 401


def test_mfa_b10_desfase_ventana(mundo, reloj_mfa):
    """MFA-B10: ventana ±1 acepta t-30 y t+30 para usuarios distintos y rechaza fuera."""
    usuario = _usuario_unico("b10a")
    crear_usuario(mundo, usuario, admin=True)
    clave = alta_por_desafio(mundo.client, reloj_mfa, usuario).clave_manual
    reloj_mfa.siguiente_paso()
    reloj_mfa.siguiente_paso()
    t = reloj_mfa.ahora()
    codigo_anterior = codigo_totp(clave, t - timedelta(seconds=30))
    token = obtener_desafio(mundo, usuario)
    r = mundo.client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge_token": token, "code": codigo_anterior},
    )
    assert r.status_code == 200, r.text

    usuario2 = _usuario_unico("b10b")
    crear_usuario(mundo, usuario2, admin=True)
    clave2 = alta_por_desafio(mundo.client, reloj_mfa, usuario2).clave_manual
    reloj_mfa.siguiente_paso()
    reloj_mfa.siguiente_paso()
    t2 = reloj_mfa.ahora()
    codigo_siguiente = codigo_totp(clave2, t2 + timedelta(seconds=30))
    token = obtener_desafio(mundo, usuario2)
    r = mundo.client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge_token": token, "code": codigo_siguiente},
    )
    assert r.status_code == 200, r.text

    usuario3 = _usuario_unico("b10c")
    crear_usuario(mundo, usuario3, admin=True)
    clave3 = alta_por_desafio(mundo.client, reloj_mfa, usuario3).clave_manual
    reloj_mfa.siguiente_paso()
    reloj_mfa.siguiente_paso()
    t3 = reloj_mfa.ahora()
    token = obtener_desafio(mundo, usuario3)
    r = mundo.client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge_token": token, "code": codigo_totp(clave3, t3 - timedelta(seconds=60))},
    )
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "MFA_INVALID_CODE", r.text

    token = obtener_desafio(mundo, usuario3)
    r = mundo.client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge_token": token, "code": codigo_totp(clave3, t3 + timedelta(seconds=60))},
    )
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "MFA_INVALID_CODE", r.text


def test_mfa_b11_agotar_desafio(mundo, reloj_mfa):
    """MFA-B11: cinco fallos agotan el desafío y el siguiente login bloquea la cuenta."""
    usuario = _usuario_unico("b11")
    crear_usuario(mundo, usuario, admin=True)
    alta = alta_por_desafio(mundo.client, reloj_mfa, usuario)

    token = obtener_desafio(mundo, usuario)
    for _ in range(5):
        r = mundo.client.post(
            "/api/v1/auth/mfa/verify",
            json={"challenge_token": token, "code": "000000"},
        )
        assert r.status_code == 401, r.text

    reloj_mfa.siguiente_paso()
    codigo = codigo_totp(alta.clave_manual, reloj_mfa.ahora())
    r = mundo.client.post(
        "/api/v1/auth/mfa/verify", json={"challenge_token": token, "code": codigo}
    )
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "MFA_CHALLENGE_INVALID", r.text

    r = login(mundo.client, usuario)
    assert r.status_code == 423, r.text
    assert r.json().get("code") == "AUTH_ACCOUNT_LOCKED", r.text


def test_mfa_b12_login_correcto_no_borra_fallos_otp(mundo, reloj_mfa):
    """MFA-B12: login correcto no reinicia el contador de fallos OTP."""
    usuario = _usuario_unico("b12")
    crear_usuario(mundo, usuario, admin=True)
    alta_por_desafio(mundo.client, reloj_mfa, usuario)

    token = obtener_desafio(mundo, usuario)
    for _ in range(3):
        r = mundo.client.post(
            "/api/v1/auth/mfa/verify",
            json={"challenge_token": token, "code": "000000"},
        )
        assert r.status_code == 401, r.text

    r = login(mundo.client, usuario)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "MFA_REQUIRED", r.text

    token = r.json()["challenge_token"]
    for _ in range(2):
        r = mundo.client.post(
            "/api/v1/auth/mfa/verify",
            json={"challenge_token": token, "code": "000000"},
        )
        assert r.status_code == 401, r.text

    r = login(mundo.client, usuario)
    assert r.status_code == 423, r.text
    assert r.json().get("code") == "AUTH_ACCOUNT_LOCKED", r.text


def test_mfa_b13_recovery_code(mundo, reloj_mfa):
    """MFA-B13: recovery_code crea sesión PASSWORD_RECOVERY y no se puede reutilizar."""
    usuario = _usuario_unico("b13")
    user_id = crear_usuario(mundo, usuario, admin=True)
    alta = alta_por_desafio(mundo.client, reloj_mfa, usuario)

    token = obtener_desafio(mundo, usuario)
    codigo = alta.codigos[0]
    compacto = codigo.replace("-", "").lower()
    r = mundo.client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge_token": token, "recovery_code": compacto},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "AUTHENTICATED", r.text
    assert r.json()["recovery_codes_remaining"] == 9, r.text
    assert "kontrol_refresh" in r.cookies, r.text
    access_token = r.json()["access_token"]
    sid = decode_token(access_token)["sid"]

    db = mundo.factory()
    try:
        session = (
            db.execute(select(AuthSession).where(AuthSession.family_id == sid))
            .scalars()
            .first()
        )
        assert session is not None, "debe existir la sesión del token devuelto"
        assert session.user_id == user_id, "la sesión debe pertenecer al usuario"
        assert session.auth_method == "PASSWORD_RECOVERY", "auth_method debe ser PASSWORD_RECOVERY"
    finally:
        db.close()

    token = obtener_desafio(mundo, usuario)
    r = mundo.client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge_token": token, "recovery_code": codigo},
    )
    assert r.status_code == 401, r.text
    assert r.json().get("code") == "MFA_INVALID_CODE", r.text


def test_mfa_b14_must_change_password_se_conserva(mundo, reloj_mfa):
    """MFA-B14: must_change_password se conserva tras completar el alta."""
    usuario = _usuario_unico("b14")
    crear_usuario(mundo, usuario, admin=True, must_change_password=True)
    r = login(mundo.client, usuario)
    challenge_token = r.json()["challenge_token"]

    r = mundo.client.post(
        "/api/v1/auth/mfa/enrollment", json={"challenge_token": challenge_token}
    )
    manual_key = r.json()["manual_key"]
    reloj_mfa.siguiente_paso()
    codigo = codigo_totp(manual_key, reloj_mfa.ahora())
    r = mundo.client.post(
        "/api/v1/auth/mfa/enrollment/confirm",
        json={"challenge_token": challenge_token, "code": codigo},
    )
    assert r.status_code == 200, r.text
    assert r.json()["must_change_password"] is True, r.text


def test_mfa_b18_validacion_cuerpo_verify(mundo, reloj_mfa):
    """MFA-B18: verificación del cuerpo de verify devuelve 422 para reglas de unicidad y extras."""
    usuario = _usuario_unico("b18")
    crear_usuario(mundo, usuario, admin=True)
    alta_por_desafio(mundo.client, reloj_mfa, usuario)
    token = obtener_desafio(mundo, usuario)

    assert (
        mundo.client.post(
            "/api/v1/auth/mfa/verify",
            json={"challenge_token": token, "code": "000000", "recovery_code": "XX"},
        ).status_code
        == 422
    )
    assert (
        mundo.client.post(
            "/api/v1/auth/mfa/verify", json={"challenge_token": token}
        ).status_code
        == 422
    )
    assert (
        mundo.client.post(
            "/api/v1/auth/mfa/verify",
            json={"challenge_token": token, "code": "000000", "extra": True},
        ).status_code
        == 422
    )


def test_mfa_b19_sin_clave(mundo, monkeypatch):
    """MFA-B19: sin KONTROL_MFA_KEYS, login mantiene enrollment y el alta devuelve 503."""
    usr = _usuario_unico("b19")
    crear_usuario(mundo, usr, admin=True)
    monkeypatch.delenv("KONTROL_MFA_KEYS", raising=False)
    get_settings.cache_clear()
    try:
        r = login(mundo.client, usr)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "MFA_ENROLLMENT_REQUIRED", r.text
        assert "access_token" not in r.json(), r.text
        assert_no_cookie(r, "login sin clave MFA no debe incluir cookie")

        r = mundo.client.post(
            "/api/v1/auth/mfa/enrollment",
            json={"challenge_token": r.json()["challenge_token"]},
        )
        assert r.status_code == 503, r.text
        assert r.json().get("code") == "MFA_UNAVAILABLE", r.text
    finally:
        get_settings.cache_clear()
