"""TSET · Verifica caso por caso las funciones puras del conjunto de confianza del cliente.

Cubre los vectores T1..T16 con claves Ed25519 sintéticas generadas en la propia prueba,
tanto para ``app.core.trust_anchor`` como para ``central_authority.config``.
"""

from __future__ import annotations

import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core import trust_anchor as ta
from central_authority.config import Settings, SigningKeyError, active_signing_pem, load_signing_key_set


def _pub(clave: Ed25519PrivateKey) -> str:
    return clave.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


def _priv(clave: Ed25519PrivateKey) -> str:
    return clave.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def _ajustes(**kw: object) -> Settings:
    return Settings(
        _env_file=None,
        environment="qa",
        db_url="sqlite+pysqlite:///:memory:",
        **kw,
    )


def test_tset_01_par_de_una_clave() -> None:
    a = Ed25519PrivateKey.generate()
    resultado = ta.load_trust_set(trust_keys=None, legacy_pem=_pub(a), legacy_kid="kid-a")
    assert resultado == {"kid-a": _pub(a).strip() + "\n"}


def test_tset_02_conjunto_desde_json_y_dict() -> None:
    a = Ed25519PrivateKey.generate()
    b = Ed25519PrivateKey.generate()
    mapa = {"kid-a": _pub(a), "kid-b": _pub(b)}
    desde_json = ta.load_trust_set(trust_keys=json.dumps(mapa), legacy_pem=None, legacy_kid=None)
    assert set(desde_json.keys()) == {"kid-a", "kid-b"}
    desde_dict = ta.load_trust_set(trust_keys=mapa, legacy_pem=None, legacy_kid=None)
    assert desde_dict == desde_json


def test_tset_03_union_json_y_legacy() -> None:
    a = Ed25519PrivateKey.generate()
    b = Ed25519PrivateKey.generate()
    resultado = ta.load_trust_set(
        trust_keys=json.dumps({"kid-b": _pub(b)}),
        legacy_pem=_pub(a),
        legacy_kid="kid-a",
    )
    assert set(resultado.keys()) == {"kid-a", "kid-b"}


def test_tset_04_entrada_repetida_identica() -> None:
    a = Ed25519PrivateKey.generate()
    resultado = ta.load_trust_set(
        trust_keys=json.dumps({"kid-a": _pub(a)}),
        legacy_pem=_pub(a),
        legacy_kid="kid-a",
    )
    assert set(resultado.keys()) == {"kid-a"}


def test_tset_05_kid_duplicado_con_pem_distinta() -> None:
    a = Ed25519PrivateKey.generate()
    b = Ed25519PrivateKey.generate()
    with pytest.raises(ta.TrustAnchorError) as exc:
        ta.load_trust_set(
            trust_keys=json.dumps({"kid-a": _pub(a)}),
            legacy_pem=_pub(b),
            legacy_kid="kid-a",
        )
    assert exc.value.reason == "duplicate_kid"


def test_tset_06_clave_duplicada() -> None:
    a = Ed25519PrivateKey.generate()
    with pytest.raises(ta.TrustAnchorError) as exc:
        ta.load_trust_set(
            trust_keys=json.dumps({"kid-a": _pub(a), "kid-alias": _pub(a)}),
            legacy_pem=None,
            legacy_kid=None,
        )
    assert exc.value.reason == "duplicate_key"


@pytest.mark.parametrize(
    ("trust_keys", "legacy_pem", "legacy_kid"),
    [
        pytest.param(None, None, "kid-a", id="sin-fuentes"),
        pytest.param("", None, "kid-a", id="trust-keys-vacio"),
        pytest.param("   ", None, "kid-a", id="trust-keys-espacios"),
    ],
)
def test_tset_07_conjunto_vacio(trust_keys: object, legacy_pem: object, legacy_kid: object) -> None:
    with pytest.raises(ta.TrustAnchorError) as exc:
        ta.load_trust_set(trust_keys=trust_keys, legacy_pem=legacy_pem, legacy_kid=legacy_kid)
    assert exc.value.reason == "missing"


@pytest.mark.parametrize("legacy_kid", [None, ""], ids=["kid-none", "kid-vacio"])
def test_tset_08_kid_ausente(legacy_kid: object) -> None:
    a = Ed25519PrivateKey.generate()
    with pytest.raises(ta.TrustAnchorError) as exc:
        ta.load_trust_set(trust_keys=None, legacy_pem=_pub(a), legacy_kid=legacy_kid)
    assert exc.value.reason == "kid_missing"


def test_tset_09_entradas_invalidas() -> None:
    a = Ed25519PrivateKey.generate()
    rsa_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_pub_pem = rsa_priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    casos = [
        "no es json",
        json.dumps(["lista"]),
        json.dumps({"kid-a": "no es pem"}),
        json.dumps({"kid con espacio": _pub(a)}),
        json.dumps({"": _pub(a)}),
        json.dumps({"kid-a": rsa_pub_pem}),
        json.dumps({"kid-a": _priv(a)}),
    ]
    for entrada in casos:
        with pytest.raises(ta.TrustAnchorError) as exc:
            ta.load_trust_set(trust_keys=entrada, legacy_pem=None, legacy_kid=None)
        assert exc.value.reason == "invalid"


def test_tset_10_resolver_clave_propietaria() -> None:
    a = Ed25519PrivateKey.generate()
    conjunto = {"kid-a": _pub(a)}
    assert ta.resolve_trusted_owner_key("kid-a", conjunto) == _pub(a)
    with pytest.raises(ta.TrustAnchorError) as exc_unknown:
        ta.resolve_trusted_owner_key("kid-b", conjunto)
    assert exc_unknown.value.reason == "unknown_kid"
    for kid in (None, "", "   ", 5):
        with pytest.raises(ta.TrustAnchorError) as exc_missing:
            ta.resolve_trusted_owner_key(kid, conjunto)
        assert exc_missing.value.reason == "kid_missing"


def test_tset_11_par_de_la_autoridad() -> None:
    a = Ed25519PrivateKey.generate()
    ajustes = _ajustes(signing_private_key_pem=_priv(a), signing_kid="kid-a")
    assert load_signing_key_set(ajustes) == {"kid-a": _priv(a).strip() + "\n"}
    assert active_signing_pem(ajustes) == _priv(a).strip() + "\n"


def test_tset_12_conjunto_de_la_autoridad_y_kid_activo() -> None:
    a = Ed25519PrivateKey.generate()
    b = Ed25519PrivateKey.generate()
    ajustes = _ajustes(
        signing_keys=json.dumps({"kid-a": _priv(a), "kid-b": _priv(b)}),
        signing_kid="kid-b",
    )
    resultado = load_signing_key_set(ajustes)
    assert set(resultado.keys()) == {"kid-a", "kid-b"}
    assert active_signing_pem(ajustes) == _priv(b).strip() + "\n"


def test_tset_13_kid_activo_ausente() -> None:
    a = Ed25519PrivateKey.generate()
    ajustes = _ajustes(signing_keys=json.dumps({"kid-a": _priv(a)}), signing_kid="kid-b")
    with pytest.raises(SigningKeyError) as exc:
        load_signing_key_set(ajustes)
    assert exc.value.reason == "active_kid_missing"


def test_tset_14_duplicados_en_la_autoridad() -> None:
    a = Ed25519PrivateKey.generate()
    b = Ed25519PrivateKey.generate()
    with pytest.raises(SigningKeyError) as exc_kid:
        load_signing_key_set(
            _ajustes(
                signing_keys=json.dumps({"kid-a": _priv(a)}),
                signing_private_key_pem=_priv(b),
                signing_kid="kid-a",
            )
        )
    assert exc_kid.value.reason == "duplicate_kid"
    with pytest.raises(SigningKeyError) as exc_key:
        load_signing_key_set(
            _ajustes(
                signing_keys=json.dumps({"kid-a": _priv(a), "kid-x": _priv(a)}),
                signing_kid="kid-a",
            )
        )
    assert exc_key.value.reason == "duplicate_key"


def test_tset_15_entradas_invalidas_de_la_autoridad() -> None:
    a = Ed25519PrivateKey.generate()
    with pytest.raises(SigningKeyError) as exc_missing:
        load_signing_key_set(_ajustes(signing_kid="kid-a"))
    assert exc_missing.value.reason == "missing"
    with pytest.raises(SigningKeyError) as exc_invalid_json:
        load_signing_key_set(_ajustes(signing_keys="no es json", signing_kid="kid-a"))
    assert exc_invalid_json.value.reason == "invalid"
    with pytest.raises(SigningKeyError) as exc_invalid_pem:
        load_signing_key_set(
            _ajustes(signing_keys=json.dumps({"kid-a": _pub(a)}), signing_kid="kid-a")
        )
    assert exc_invalid_pem.value.reason == "invalid"


def test_tset_16_prod_valida_el_conjunto() -> None:
    a = Ed25519PrivateKey.generate()
    with pytest.raises(ValueError) as exc:
        Settings(
            _env_file=None,
            environment="prod",
            db_url="postgresql+psycopg2://u:p@h/db",
            signing_keys=json.dumps({"kid-a": _priv(a)}),
            signing_kid="kid-b",
        )
    mensaje = str(exc.value)
    assert "active_kid_missing" in mensaje
    assert "BEGIN" not in mensaje
    ok = Settings(
        _env_file=None,
        environment="prod",
        db_url="postgresql+psycopg2://u:p@h/db",
        signing_keys=json.dumps({"kid-a": _priv(a)}),
        signing_kid="kid-a",
    )
    assert ok.signing_kid == "kid-a"
