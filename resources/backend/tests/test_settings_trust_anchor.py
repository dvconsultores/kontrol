"""CFG · El ancla de confianza del propietario es obligatoria en `prod` y debe servir (FR-010-148..151).

Mismo contrato que `secret_key`: la configuración falla al cargar, antes de arrancar, con un
mensaje que dice qué variable falta y nunca lleva material de clave. Fuera de `prod` arranca
sin ancla y es la importación la que falla cerrada. Claves sintéticas generadas aquí.
"""

from __future__ import annotations

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from pydantic import ValidationError

from app.core.config import Settings
from app.core.trust_anchor import TrustAnchorError, load_trust_anchor

SECRETO = "x" * 40


def pem_ed25519() -> str:
    clave_privada = Ed25519PrivateKey.generate()
    return clave_privada.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")


def pem_rsa() -> str:
    clave_privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return clave_privada.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")


def _limpiar_entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KONTROL_LICENSE_PUBLIC_KEY_PEM", raising=False)
    monkeypatch.delenv("KONTROL_ENVIRONMENT", raising=False)


def test_cfg_01_en_prod_sin_ancla_la_configuracion_no_carga(monkeypatch: pytest.MonkeyPatch) -> None:
    _limpiar_entorno(monkeypatch)
    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=None, environment="prod", secret_key=SECRETO, license_public_key_pem=None)
    texto = str(excinfo.value)
    assert "KONTROL_LICENSE_PUBLIC_KEY_PEM es obligatoria en prod" in texto
    assert "ancla missing" in texto


def test_cfg_01b_en_prod_un_ancla_en_blanco_tampoco(monkeypatch: pytest.MonkeyPatch) -> None:
    _limpiar_entorno(monkeypatch)
    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=None, environment="prod", secret_key=SECRETO, license_public_key_pem="   ")
    texto = str(excinfo.value)
    assert "KONTROL_LICENSE_PUBLIC_KEY_PEM es obligatoria en prod" in texto
    assert "ancla missing" in texto


def test_cfg_02_en_prod_un_ancla_que_no_es_pem_no_carga(monkeypatch: pytest.MonkeyPatch) -> None:
    _limpiar_entorno(monkeypatch)
    with pytest.raises(ValidationError) as excinfo:
        Settings(
            _env_file=None,
            environment="prod",
            secret_key=SECRETO,
            license_public_key_pem="esto no es una clave",
        )
    texto = str(excinfo.value)
    assert "KONTROL_LICENSE_PUBLIC_KEY_PEM es obligatoria en prod" in texto
    assert "ancla invalid" in texto


def test_cfg_03_en_prod_una_clave_que_no_es_ed25519_no_carga(monkeypatch: pytest.MonkeyPatch) -> None:
    _limpiar_entorno(monkeypatch)
    with pytest.raises(ValidationError) as excinfo:
        Settings(
            _env_file=None,
            environment="prod",
            secret_key=SECRETO,
            license_public_key_pem=pem_rsa(),
        )
    texto = str(excinfo.value)
    assert "KONTROL_LICENSE_PUBLIC_KEY_PEM es obligatoria en prod" in texto
    assert "ancla invalid" in texto


def test_cfg_04_en_prod_con_el_ancla_del_propietario_carga(monkeypatch: pytest.MonkeyPatch) -> None:
    _limpiar_entorno(monkeypatch)
    pem = pem_ed25519()
    settings = Settings(
        _env_file=None,
        environment="prod",
        secret_key=SECRETO,
        license_public_key_pem=pem,
    )
    assert settings.environment == "prod"
    assert settings.license_public_key_pem == pem


@pytest.mark.parametrize("entorno", ["local", "dev", "qa", "uat", "staging"])
def test_cfg_05_fuera_de_prod_el_ancla_no_es_obligatoria_al_arrancar(
    monkeypatch: pytest.MonkeyPatch, entorno: str
) -> None:
    _limpiar_entorno(monkeypatch)
    settings = Settings(
        _env_file=None,
        environment=entorno,
        secret_key=SECRETO,
        license_public_key_pem=None,
    )
    assert settings.environment == entorno


def test_cfg_06_el_mensaje_de_error_no_lleva_material(monkeypatch: pytest.MonkeyPatch) -> None:
    _limpiar_entorno(monkeypatch)
    with pytest.raises(ValidationError) as excinfo:
        Settings(
            _env_file=None,
            environment="prod",
            secret_key=SECRETO,
            license_public_key_pem=pem_rsa(),
        )
    texto = str(excinfo.value)
    assert "BEGIN PUBLIC KEY" not in texto
    assert "MII" not in texto
    assert "/data" not in texto


def test_cfg_07_el_cargador_del_ancla_distingue_missing_de_invalid() -> None:
    for pem in (None, ""):
        with pytest.raises(TrustAnchorError) as excinfo:
            load_trust_anchor(pem)
        assert excinfo.value.reason == "missing"

    for pem in ("basura", pem_rsa()):
        with pytest.raises(TrustAnchorError) as excinfo:
            load_trust_anchor(pem)
        assert excinfo.value.reason == "invalid"

    clave = load_trust_anchor(pem_ed25519())
    assert isinstance(clave, Ed25519PublicKey)
    assert "BEGIN" not in str(TrustAnchorError("invalid"))


def test_cfg_08_el_error_de_arranque_no_reproduce_la_configuracion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pydantic incluye por defecto el valor de entrada en el error; aquí ese valor es toda la
    configuración, con `secret_key` dentro. El modelo lo oculta (`hide_input_in_errors`)."""
    _limpiar_entorno(monkeypatch)
    secreto = "s3cr3t0-que-no-debe-salir-en-el-registro-de-arranque"
    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=None, environment="prod", secret_key=secreto, license_public_key_pem=pem_ed25519()[:-10])
    texto = str(excinfo.value)
    assert "ancla invalid" in texto
    assert secreto not in texto and "input_value" not in texto and "BEGIN PUBLIC KEY" not in texto
