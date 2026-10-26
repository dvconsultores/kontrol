"""MFA · TOTP RFC 6238 (Spec 002/003 · OQ-GAB-2)."""

from __future__ import annotations

import ast
import base64
import sys
import urllib.parse
from datetime import UTC, datetime

from mfa_apoyo import codigo_totp

from app.modules.identity_access import totp


def test_mfa_t01_vectores_rfc6238_sha1():
    """MFA-T01: vectores oficiales RFC 6238 con SHA-1 y código de 6 dígitos."""
    raw = b"12345678901234567890"
    b32 = totp.encode_secret(raw)
    vectores = [
        (59, "287082"),
        (1111111109, "081804"),
        (1111111111, "050471"),
        (1234567890, "005924"),
        (2000000000, "279037"),
        (20000000000, "353130"),
    ]
    for t, esperado in vectores:
        assert totp.code_at(raw, t // 30) == esperado
        assert codigo_totp(b32, datetime.fromtimestamp(t, UTC)) == esperado


def test_mfa_t02_parametros():
    """MFA-T02: constantes del contrato."""
    assert totp.PERIOD == 30
    assert totp.DIGITS == 6
    assert totp.ALGORITHM == "SHA1"
    assert totp.SKEW_STEPS == 1


def test_mfa_t03_generate_secret():
    """MFA-T03: generate_secret produce 20 bytes y dos llamadas difieren."""
    primero = totp.generate_secret()
    segundo = totp.generate_secret()
    assert len(primero) == 20
    assert len(segundo) == 20
    assert primero != segundo


def test_mfa_t04_codificacion_y_clave_manual():
    """MFA-T04: Base32 mayúscula sin relleno y clave manual en grupos de 4."""
    raw = totp.generate_secret()
    codificada = totp.encode_secret(raw)

    assert codificada == codificada.upper()
    assert "=" not in codificada

    relleno = "=" * (-len(codificada) % 8)
    assert base64.b32decode(codificada + relleno) == raw

    manual = totp.format_manual_key(codificada)
    grupos = manual.split(" ")
    assert all(len(grupo) == 4 for grupo in grupos[:-1])
    assert len(grupos[-1]) <= 4
    assert manual.replace(" ", "") == codificada


def test_mfa_t05_time_step_bordes():
    """MFA-T05: time_step en bordes de período de 30 s."""
    borde_cero = datetime(1970, 1, 1, 0, 0, 29, tzinfo=UTC)
    borde_uno_inicio = datetime(1970, 1, 1, 0, 0, 30, tzinfo=UTC)
    borde_uno_fin = datetime(1970, 1, 1, 0, 0, 59, tzinfo=UTC)
    borde_dos = datetime(1970, 1, 1, 0, 1, 0, tzinfo=UTC)

    assert totp.time_step(borde_cero) == 0
    assert totp.time_step(borde_uno_inicio) == 1
    assert totp.time_step(borde_uno_fin) == 1
    assert totp.time_step(borde_dos) == 2


def test_mfa_t06_ventana_acepta_paso_anterior_actual_y_siguiente():
    """MFA-T06: match_step acepta s-1, s y s+1 y devuelve el paso correcto."""
    raw = totp.generate_secret()
    instante = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    paso_actual = totp.time_step(instante)

    for desplazamiento in (-1, 0, 1):
        codigo = totp.code_at(raw, paso_actual + desplazamiento)
        resultado = totp.match_step(raw, codigo, instante)
        assert resultado == paso_actual + desplazamiento


def test_mfa_t07_ventana_rechaza_fuera():
    """MFA-T07: match_step rechaza s-2 y s+2 cuando no coinciden con la ventana."""
    raw = b"12345678901234567890"
    instante = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    paso_actual = totp.time_step(instante)

    codigo_s_menos_2 = totp.code_at(raw, paso_actual - 2)
    codigo_s_mas_2 = totp.code_at(raw, paso_actual + 2)

    codigos_ventana = {
        totp.code_at(raw, paso_actual + desplazamiento)
        for desplazamiento in (-1, 0, 1)
    }
    assert codigo_s_menos_2 not in codigos_ventana
    assert codigo_s_mas_2 not in codigos_ventana

    assert totp.match_step(raw, codigo_s_menos_2, instante) is None
    assert totp.match_step(raw, codigo_s_mas_2, instante) is None


def test_mfa_t08_formatos_rechazados():
    """MFA-T08: solo se aceptan exactamente 6 dígitos ASCII; se ignoran espacios."""
    raw = b"12345678901234567890"
    instante = datetime.fromtimestamp(59, UTC)

    for codigo_invalido in ("", "12345", "1234567", "12a456", "１２３４５６"):
        assert totp.match_step(raw, codigo_invalido, instante) is None

    codigo_con_espacio = "287 082"
    codigo_sin_espacio = "287082"
    assert totp.match_step(raw, codigo_con_espacio, instante) == totp.match_step(
        raw, codigo_sin_espacio, instante
    )


def test_mfa_t09_provisioning_uri():
    """MFA-T09: URI otpauth con prefijo, cuenta codificada y parámetros exactos."""
    raw = totp.generate_secret()
    cuenta = "usuario@kontrol.com con espacio"
    uri = totp.provisioning_uri(raw, account=cuenta)
    params = urllib.parse.parse_qs(urllib.parse.urlsplit(uri).query)

    prefijo = "otpauth://totp/KONTROL:"
    assert uri.startswith(prefijo)
    assert urllib.parse.quote(cuenta) in uri.removeprefix(prefijo)

    assert params["secret"] == [totp.encode_secret(raw)]
    assert params["issuer"] == ["KONTROL"]
    assert params["algorithm"] == ["SHA1"]
    assert params["digits"] == ["6"]
    assert params["period"] == ["30"]


def test_mfa_t10_solo_stdlib():
    """MFA-T10: los imports de nivel superior del módulo TOTP son de stdlib."""
    ruta = totp.__file__
    with open(ruta, encoding="utf-8") as fichero:
        arbol = ast.parse(fichero.read(), filename=ruta)

    for nodo in arbol.body:
        if isinstance(nodo, ast.Import):
            nombres = [alias.name.split(".")[0] for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.module == "__future__":
                continue
            nombres = [nodo.module.split(".")[0]] if nodo.module else []
        else:
            continue

        for nombre in nombres:
            assert nombre in sys.stdlib_module_names
