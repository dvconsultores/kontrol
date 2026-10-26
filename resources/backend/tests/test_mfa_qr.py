"""MFA · generación del QR del alta (Spec 002/003 · OQ-MFA-2)."""

from __future__ import annotations

import urllib.parse

import pytest

from app.modules.identity_access import mfa_qr, totp


def test_mfa_q01_svg_data_uri():
    """MFA-Q01: svg_data_uri devuelve una imagen SVG embebida en data URI."""
    uri = totp.provisioning_uri(totp.generate_secret(), account="u1")
    resultado = mfa_qr.svg_data_uri(uri)
    assert resultado.startswith("data:image/svg+xml")


@pytest.mark.parametrize(
    "uri_invalida",
    ["https://x", "<svg onload=alert(1)>", "javascript:alert(1)"],
)
def test_mfa_q02_rechaza_uri_no_otpauth(uri_invalida: str):
    """MFA-Q02: solo se aceptan URIs otpauth://totp/ generadas internamente."""
    with pytest.raises(ValueError):
        mfa_qr.svg_data_uri(uri_invalida)


def test_mfa_q03_salida_sin_marcado_activo():
    """MFA-Q03: la salida no contiene marcado activo tras decodificar la URI."""
    uri = totp.provisioning_uri(totp.generate_secret(), account="u1")
    resultado = mfa_qr.svg_data_uri(uri)
    decodificado = urllib.parse.unquote(resultado)
    assert "<script" not in decodificado
    assert "onload" not in decodificado
    assert "javascript:" not in decodificado


def test_mfa_q04_imports_de_terceros():
    """MFA-Q04: el módulo importa segno y ningún otro tercero."""
    import ast
    import sys

    ruta = mfa_qr.__file__
    with open(ruta, encoding="utf-8") as fichero:
        arbol = ast.parse(fichero.read(), filename=ruta)

    terceros = set()
    for nodo in arbol.body:
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                nombre = alias.name.split(".")[0]
                if nombre not in sys.stdlib_module_names:
                    terceros.add(nombre)
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.module and nodo.level == 0:
                nombre = nodo.module.split(".")[0]
                if nombre not in sys.stdlib_module_names:
                    terceros.add(nombre)

    assert terceros == {"segno"}
