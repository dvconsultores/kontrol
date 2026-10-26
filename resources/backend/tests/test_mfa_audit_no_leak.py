"""MFA-J01..J04 · la auditoría MFA registra solo cargas seguras y ningún secreto.

El contrato de auditoría exige una puerta única —`_audit_mfa`— con lista blanca de
claves de evidencia y valores primitivos. Estas pruebas recorren el flujo MFA
completo, inspeccionan cada fila `AuditEvent` y cada registro de log, y verifican
que nunca aparece material secreto: clave manual, URI otpauth, QR, códigos de
recuperación, challenge tokens, contraseñas ni códigos TOTP.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from dataclasses import dataclass

import pytest
from mfa_apoyo import codigo_totp
from mfa_mundo import (
    API,
    CONTRASENA,
    alta_por_desafio,
    crear_usuario,
    login,
    mundo_mfa,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditEvent
from app.modules.identity_access.models import User

pytest_plugins = ("mfa_apoyo",)

CLAVES_PERMITIDAS = {
    "method",
    "policy_class",
    "recovery_codes_remaining",
    "reason",
    "sessions_revoked",
    "target_user_id",
    "attempts_remaining",
}
RAZONES_VALIDAS = {"INVALID_CODE", "REPLAY", "EXHAUSTED", "LOCKED"}
ACCIONES_MINIMAS = {
    "MFA_ENROLLMENT_STARTED",
    "MFA_ENABLED",
    "MFA_CHALLENGE_SUCCEEDED",
    "MFA_CHALLENGE_FAILED",
    "MFA_RECOVERY_CODE_USED",
    "MFA_RECOVERY_CODES_REGENERATED",
    "MFA_RESET_BY_ADMIN",
    "MFA_REAUTH_SUCCEEDED",
    "MFA_REAUTH_FAILED",
    "SESSIONS_REVOKED_SECURITY_CHANGE",
}

CONTRASENA_MALA = "ContrasenaMala!9"


@dataclass
class SecretosRecorrido:
    secretos: list[str]
    codigos_totp: list[str]


class RecorridoMfa:
    """Ejecuta el recorrido MFA completo con usuarios únicos y guarda secretos."""

    def __init__(self, mundo) -> None:
        self.mundo = mundo

    def recorrer(self, reloj_mfa) -> SecretosRecorrido:
        mundo = self.mundo
        secretos: list[str] = [CONTRASENA, CONTRASENA_MALA]
        codigos_totp: list[str] = []

        usuario = f"u_{uuid.uuid4().hex[:10]}"
        objetivo = crear_usuario(mundo, usuario, admin=True)

        # 1. Alta manual: los tres formatos del material secreto y los códigos.
        r = login(mundo.client, usuario)
        assert r.status_code == 200, r.text
        assert r.json().get("status") == "MFA_ENROLLMENT_REQUIRED", r.text
        challenge_alta = r.json()["challenge_token"]
        assert isinstance(challenge_alta, str) and challenge_alta

        r = mundo.client.post(
            f"{API}/auth/mfa/enrollment", json={"challenge_token": challenge_alta}
        )
        assert r.status_code == 200, r.text
        enrollment = r.json()
        manual = enrollment.get("manual_key")
        assert manual, r.text
        secretos.extend(
            (
                str(manual),
                str(manual).replace(" ", ""),
                str(manual).replace(" ", "").lower(),
                enrollment.get("otpauth_uri"),
                enrollment.get("qr_svg_data_uri"),
                challenge_alta,
            )
        )

        reloj_mfa.siguiente_paso()
        codigo = codigo_totp(str(manual), reloj_mfa.ahora())
        codigos_totp.append(codigo)
        r = mundo.client.post(
            f"{API}/auth/mfa/enrollment/confirm",
            json={"challenge_token": challenge_alta, "code": codigo},
        )
        assert r.status_code == 200, r.text
        confirmacion = r.json()
        assert isinstance(confirmacion.get("access_token"), str), r.text
        recovery_codes = confirmacion.get("recovery_codes")
        assert isinstance(recovery_codes, list), r.text
        for value in recovery_codes:
            value = str(value)
            secretos.extend((value, value.replace("-", ""), value.lower()))
        cabeceras = {"Authorization": f"Bearer {confirmacion['access_token']}"}

        # 2. Código erróneo: 401.
        r = login(mundo.client, usuario)
        assert r.status_code == 200, r.text
        assert r.json().get("status") == "MFA_REQUIRED", r.text
        challenge = r.json()["challenge_token"]
        secretos.append(challenge)
        r = mundo.client.post(
            f"{API}/auth/mfa/verify",
            json={"challenge_token": challenge, "code": "000000"},
        )
        assert r.status_code == 401, r.text
        assert r.json().get("code") == "MFA_INVALID_CODE", r.text

        # 3. TOTP correcto.
        reloj_mfa.siguiente_paso()
        codigo_ok = codigo_totp(str(manual), reloj_mfa.ahora())
        codigos_totp.append(codigo_ok)
        r = mundo.client.post(
            f"{API}/auth/mfa/verify",
            json={"challenge_token": challenge, "code": codigo_ok},
        )
        assert r.status_code == 200, r.text

        # 4. Replay sin avanzar: MISMO código, MISMO desafío.
        r = login(mundo.client, usuario)
        assert r.status_code == 200, r.text
        assert r.json().get("status") == "MFA_REQUIRED", r.text
        challenge_replay = r.json()["challenge_token"]
        secretos.append(challenge_replay)
        r = mundo.client.post(
            f"{API}/auth/mfa/verify",
            json={"challenge_token": challenge_replay, "code": codigo_ok},
        )
        assert r.status_code == 401, r.text
        assert r.json().get("code") == "MFA_CODE_ALREADY_USED", r.text

        # 5. Código de recuperación.
        r = login(mundo.client, usuario)
        assert r.status_code == 200, r.text
        assert r.json().get("status") == "MFA_REQUIRED", r.text
        challenge_rec = r.json()["challenge_token"]
        secretos.append(challenge_rec)
        r = mundo.client.post(
            f"{API}/auth/mfa/verify",
            json={"challenge_token": challenge_rec, "recovery_code": recovery_codes[0]},
        )
        assert r.status_code == 200, r.text

        # 6. Regenerar códigos con las cabeceras del paso 1.
        r = mundo.client.post(
            f"{API}/auth/mfa/recovery-codes", headers=cabeceras
        )
        assert r.status_code == 200, r.text
        regenerados = r.json().get("recovery_codes")
        assert isinstance(regenerados, list), r.text
        for value in regenerados:
            value = str(value)
            secretos.extend((value, value.replace("-", ""), value.lower()))

        # 7. Reauth fallida y correcta con password explícito.
        r = mundo.client.post(
            f"{API}/auth/reauth",
            headers=cabeceras,
            json={"password": CONTRASENA_MALA, "code": "000000"},
        )
        assert r.status_code == 401, r.text
        assert r.json().get("code") == "REAUTH_FAILED", r.text

        reloj_mfa.siguiente_paso()
        codigo_reauth = codigo_totp(str(manual), reloj_mfa.ahora())
        codigos_totp.append(codigo_reauth)
        r = mundo.client.post(
            f"{API}/auth/reauth",
            headers=cabeceras,
            json={"password": CONTRASENA, "code": codigo_reauth},
        )
        assert r.status_code == 200, r.text

        # 8. Reset administrativo desde un actor distinto.
        actor = f"act_{uuid.uuid4().hex[:10]}"
        crear_usuario(mundo, actor, admin=True)
        alta_actor = alta_por_desafio(mundo.client, reloj_mfa, actor)
        secretos.append(alta_actor.clave_manual)
        secretos.extend(str(code) for code in alta_actor.codigos)
        r = mundo.client.post(
            f"{API}/users/{objetivo}/mfa/reset", headers=alta_actor.cabeceras
        )
        assert r.status_code == 204, r.text

        if os.environ.get("KONTROL_MFA_KEYS"):
            valor = os.environ["KONTROL_MFA_KEYS"]
            secretos.append(valor)
            if ":" in valor:
                secretos.append(valor.split(":", 1)[1])

        return SecretosRecorrido(secretos=secretos, codigos_totp=codigos_totp)


@pytest.fixture(scope="module")
def mundo():
    """Mundo de API MFA para todas las pruebas de este módulo."""
    with mundo_mfa() as m:
        yield m


def _texto_fila(fila: AuditEvent) -> str:
    columnas = {
        "action": fila.action,
        "entity_type": fila.entity_type,
        "entity_id": fila.entity_id,
        "user_id": fila.user_id,
        "session_id": fila.session_id,
        "request_id": fila.request_id,
        "reason": fila.reason,
        "before": fila.before,
        "after": fila.after,
        "evidence": fila.evidence,
        "ip": fila.ip,
        "source": fila.source,
    }
    return json.dumps(columnas, ensure_ascii=False, default=str)


def _comprobar_sin_secretos(
    texto: str, secreto: str, tipo: str, indice: int, codigos_totp: list[str]
) -> None:
    if secreto and secreto in texto:
        pytest.fail(f"secreto de tipo {tipo} presente en fila/registro {indice}")
    for codigo in codigos_totp:
        if re.search(rf"(?<![0-9]){re.escape(codigo)}(?![0-9])", texto):
            pytest.fail(f"código TOTP presente en fila/registro {indice}")


def test_mfa_j01_ningun_secreto_en_auditoria_ni_registros(mundo, reloj_mfa, caplog):
    """MFA-J01: ningún secreto ni código TOTP en auditoría ni logs."""
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        recorrido = RecorridoMfa(mundo)
        resultado = recorrido.recorrer(reloj_mfa)

    db: Session = mundo.factory()
    try:
        filas = list(db.execute(select(AuditEvent)).scalars().all())
    finally:
        db.close()

    for indice, fila in enumerate(filas):
        texto = _texto_fila(fila)
        for secreto in resultado.secretos:
            _comprobar_sin_secretos(
                texto, secreto, "secreto", indice, resultado.codigos_totp
            )

    for indice, record in enumerate(caplog.records):
        texto = record.getMessage() + " " + str(record.args)
        for secreto in resultado.secretos:
            _comprobar_sin_secretos(
                texto, secreto, "secreto", indice, resultado.codigos_totp
            )


def test_mfa_j02_carga_de_auditoria_en_lista_blanca(mundo, reloj_mfa):
    """MFA-J02: cargas de auditoría seguras y catálogo mínimo."""
    recorrido = RecorridoMfa(mundo)
    recorrido.recorrer(reloj_mfa)

    db: Session = mundo.factory()
    try:
        filas = list(db.execute(select(AuditEvent)).scalars().all())
    finally:
        db.close()

    seleccion = [
        fila
        for fila in filas
        if fila.action.startswith("MFA_")
        or fila.action == "SESSIONS_REVOKED_SECURITY_CHANGE"
    ]
    assert seleccion, "no hay eventos MFA"

    for fila in seleccion:
        assert fila.before is None, fila.action
        assert fila.after is None, fila.action
        evidencia = fila.evidence or {}
        assert isinstance(evidencia, dict), fila.action
        assert set(evidencia.keys()) <= CLAVES_PERMITIDAS, (
            fila.action,
            set(evidencia.keys()) - CLAVES_PERMITIDAS,
        )
        for valor in evidencia.values():
            assert isinstance(valor, str | int | bool | type(None)), (
                fila.action,
                type(valor),
            )
        assert fila.entity_type == "User", fila.action
        assert fila.entity_id is not None, fila.action

    acciones = {fila.action for fila in seleccion}
    assert ACCIONES_MINIMAS <= acciones, acciones

    fallos = [
        fila for fila in seleccion if fila.action == "MFA_CHALLENGE_FAILED"
    ]
    assert fallos, "no hay fallos MFA"
    razones = {fila.evidence.get("reason") for fila in fallos}
    assert "INVALID_CODE" in razones, razones
    assert "REPLAY" in razones, razones
    assert razones <= RAZONES_VALIDAS, razones


def test_mfa_j03_la_puerta_rechaza_claves_y_valores_no_permitidos(mundo):
    """MFA-J03: la puerta rechaza claves y valores no primitivos."""
    from app.modules.identity_access.mfa_service import _audit_mfa

    db: Session = mundo.factory()
    try:
        usuario = db.execute(
            select(User).where(User.username == "admin")
        ).scalars().one()
        antes = db.execute(select(func.count()).select_from(AuditEvent)).scalar_one()

        with pytest.raises(ValueError):
            _audit_mfa(db, "MFA_ENABLED", user=usuario, code="123456")
        with pytest.raises(ValueError):
            _audit_mfa(db, "MFA_ENABLED", user=usuario, reason={"x": 1})

        despues = db.execute(select(func.count()).select_from(AuditEvent)).scalar_one()
        assert despues == antes, "la puerta escribió una fila pese al rechazo"
        db.rollback()
    finally:
        db.close()


def test_mfa_j04_respuestas_sin_material_secreto(mundo, reloj_mfa):
    """MFA-J04: las respuestas de los endpoints de sesión no exponen secretos."""
    usuario = f"u_{uuid.uuid4().hex[:10]}"
    crear_usuario(mundo, usuario, admin=True)
    alta = alta_por_desafio(mundo.client, reloj_mfa, usuario)
    cabeceras = alta.cabeceras

    for ruta in (f"{API}/auth/mfa", f"{API}/auth/me", f"{API}/auth/sessions"):
        r = mundo.client.get(ruta, headers=cabeceras)
        assert r.status_code == 200, r.text
        texto = r.text.lower()
        for prohibido in ("secret", "ciphertext", "code_hash", "token_hash"):
            assert prohibido not in texto, ruta
        assert alta.clave_manual.replace(" ", "").lower() not in texto, ruta
