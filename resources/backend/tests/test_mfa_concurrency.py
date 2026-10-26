"""MFA-B07 y MFA-C03 · la antirrepetición TOTP y el consumo de recuperación
tienen exactamente un ganador en escritura.

Dos peticiones simultáneas con el mismo código solo pueden producir una sesión:
una recibe 200 y la otra 401. Se usa el patrón de hilos del repo
(`motor_para_hilos`) para medir el producto y no el arnés.
"""

from __future__ import annotations

import threading
import uuid

import pytest
from fastapi.testclient import TestClient
from mfa_apoyo import codigo_totp
from mfa_mundo import alta_por_desafio, crear_usuario, login, mundo_mfa
from sqlalchemy import select

from app.core.security import sha256_hex
from app.modules.identity_access.models import (
    MfaRecoveryCode,
)
from app.modules.identity_access.models import (
    Session as AuthSession,
)
from tests.conftest import motor_para_hilos

pytest_plugins = ("mfa_apoyo",)

PLAZO = 15

MUNDO = None
CLIENT: TestClient
FACTORY = None


def _en_hilos(*trabajos) -> list[str]:
    """Ejecuta cada trabajo en su hilo y devuelve las excepciones que los mataron."""
    errores: list[str] = []
    barrera = threading.Barrier(len(trabajos), timeout=PLAZO)

    def envoltura(trabajo):
        try:
            barrera.wait(timeout=PLAZO)
            trabajo()
        except Exception as exc:  # noqa: BLE001
            errores.append(f"{type(exc).__name__}: {exc}"[:200])
            raise

    hilos = [threading.Thread(target=envoltura, args=(t,)) for t in trabajos]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(PLAZO * 2)
    assert not any(h.is_alive() for h in hilos), "un hilo no terminó"
    return errores


@pytest.fixture(scope="module", autouse=True)
def mundo():
    """Mundo MFA sobre motor de hilos para las pruebas de concurrencia."""
    global MUNDO, CLIENT, FACTORY
    with motor_para_hilos("mfa-concurrencia") as engine:
        with mundo_mfa(engine=engine) as m:
            MUNDO = m
            CLIENT = m.client
            FACTORY = m.factory
            yield m


def _desafio_para(usuario: str) -> str:
    r = login(CLIENT, usuario)
    assert r.status_code == 200, r.text
    assert r.json().get("status") == "MFA_REQUIRED", r.text
    token = r.json()["challenge_token"]
    assert isinstance(token, str) and token
    return token


def test_mfa_b07_mismo_totp_en_paralelo_un_solo_exito(mundo, reloj_mfa):
    """MFA-B07: el mismo TOTP en paralelo produce un único 200 y una sesión."""
    usuario = f"u_{uuid.uuid4().hex[:10]}"
    user_id = crear_usuario(MUNDO, usuario, admin=True)
    alta = alta_por_desafio(CLIENT, reloj_mfa, usuario)
    reloj_mfa.siguiente_paso()
    codigo = codigo_totp(alta.clave_manual, reloj_mfa.ahora())

    desafio_1 = _desafio_para(usuario)
    desafio_2 = _desafio_para(usuario)

    db = FACTORY()
    try:
        antes = db.execute(
            select(AuthSession).where(AuthSession.user_id == user_id)
        ).scalars().all()
        antes_count = len(antes)
    finally:
        db.close()

    respuestas: list = []
    cerrojo = threading.Lock()

    def verificar(desafio):
        r = CLIENT.post(
            "/api/v1/auth/mfa/verify",
            json={"challenge_token": desafio, "code": codigo},
        )
        with cerrojo:
            respuestas.append(r)

    errores = _en_hilos(
        lambda: verificar(desafio_1),
        lambda: verificar(desafio_2),
    )
    assert errores == [], errores
    estados = sorted(r.status_code for r in respuestas)
    assert estados == [200, 401], [(r.status_code, r.text) for r in respuestas]
    perdedora = next(r for r in respuestas if r.status_code == 401)
    assert perdedora.json()["code"] == "MFA_CODE_ALREADY_USED", perdedora.text

    db = FACTORY()
    try:
        despues = db.execute(
            select(AuthSession).where(AuthSession.user_id == user_id)
        ).scalars().all()
        despues_count = len(despues)
    finally:
        db.close()
    assert despues_count == antes_count + 1, (antes_count, despues_count)


def test_mfa_c03_mismo_codigo_de_recuperacion_en_paralelo_un_solo_exito(
    mundo, reloj_mfa
):
    """MFA-C03: el mismo recovery_code en paralelo produce un único 200 y una sesión."""
    usuario = f"u_{uuid.uuid4().hex[:10]}"
    user_id = crear_usuario(MUNDO, usuario, admin=True)
    alta = alta_por_desafio(CLIENT, reloj_mfa, usuario)
    recovery_code = alta.codigos[0]
    normalizado = recovery_code.replace("-", "").upper()
    hash_esperado = sha256_hex(normalizado)

    desafio_1 = _desafio_para(usuario)
    desafio_2 = _desafio_para(usuario)

    db = FACTORY()
    try:
        antes = db.execute(
            select(AuthSession).where(AuthSession.user_id == user_id)
        ).scalars().all()
        antes_count = len(antes)
    finally:
        db.close()

    respuestas: list = []
    cerrojo = threading.Lock()

    def verificar(desafio):
        r = CLIENT.post(
            "/api/v1/auth/mfa/verify",
            json={"challenge_token": desafio, "recovery_code": recovery_code},
        )
        with cerrojo:
            respuestas.append(r)

    errores = _en_hilos(
        lambda: verificar(desafio_1),
        lambda: verificar(desafio_2),
    )
    assert errores == [], errores
    estados = sorted(r.status_code for r in respuestas)
    assert estados == [200, 401], [(r.status_code, r.text) for r in respuestas]
    perdedora = next(r for r in respuestas if r.status_code == 401)
    assert perdedora.json()["code"] == "MFA_INVALID_CODE", perdedora.text

    db = FACTORY()
    try:
        fila = db.execute(
            select(MfaRecoveryCode).where(
                MfaRecoveryCode.code_hash == hash_esperado
            )
        ).scalars().one_or_none()
        assert fila is not None, "no se encontró la fila del código"
        assert fila.used_at is not None

        despues = db.execute(
            select(AuthSession).where(AuthSession.user_id == user_id)
        ).scalars().all()
        despues_count = len(despues)
    finally:
        db.close()
    assert despues_count == antes_count + 1, (antes_count, despues_count)
