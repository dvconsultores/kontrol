"""SAC · Verifica caso por caso el contrato puro ``app.core.sync_auth_contract``.

Cubre los vectores V1..V14 con claves Ed25519 sintéticas generadas en la propia prueba.
"""

from __future__ import annotations

import hashlib

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core import sync_auth_contract as sa


def _envelope() -> dict:
    return sa.build_envelope(
        installation_id="KTL-XX-SINTETICA",
        challenge_id="11111111-1111-1111-1111-111111111111",
        nonce="ab" * 32,
        method="post",
        target="/v1/license/sync",
        body_sha256="0" * 64,
    )


def test_sac_01_build_envelope_normaliza_method_y_claves() -> None:
    envelope = _envelope()
    assert envelope["method"] == "POST"
    assert envelope["protocol_version"] == 1
    assert set(envelope.keys()) == set(sa.ENVELOPE_FIELDS)


@pytest.mark.parametrize(
    "overrides",
    [
        {"target": "/v1/license/sync?x=1"},
        {"target": "v1/license/sync"},
        {"target": "/v1/license/sync#f"},
        {"body_sha256": "0" * 63},
        {"body_sha256": "A" * 64},
        {"body_sha256": "zz" * 32},
        {"installation_id": ""},
        {"installation_id": "con espacio"},
        {"nonce": ""},
        {"challenge_id": "x" * 65},
    ],
    ids=[
        "target_query",
        "target_sin_barra",
        "target_fragmento",
        "body_sha256_corto",
        "body_sha256_mayusculas",
        "body_sha256_no_hex",
        "installation_id_vacio",
        "installation_id_espacio",
        "nonce_vacio",
        "challenge_id_largo",
    ],
)
def test_sac_02_build_envelope_rechaza_campos_invalidos(overrides: dict) -> None:
    kwargs = {
        "installation_id": "KTL-XX-SINTETICA",
        "challenge_id": "11111111-1111-1111-1111-111111111111",
        "nonce": "ab" * 32,
        "method": "post",
        "target": "/v1/license/sync",
        "body_sha256": "0" * 64,
    }
    kwargs.update(overrides)
    with pytest.raises(sa.SyncAuthContractError) as exc:
        sa.build_envelope(**kwargs)
    assert exc.value.code == "SYNC_ENVELOPE_INVALID"


def test_sac_03_build_envelope_rechaza_protocol_version_2() -> None:
    with pytest.raises(sa.SyncAuthContractError) as exc:
        sa.build_envelope(
            installation_id="KTL-XX-SINTETICA",
            challenge_id="11111111-1111-1111-1111-111111111111",
            nonce="ab" * 32,
            method="post",
            target="/v1/license/sync",
            body_sha256="0" * 64,
            protocol_version=2,
        )
    assert exc.value.code == "SYNC_PROTOCOL_UNSUPPORTED"


def test_sac_04_envelope_bytes_es_canonico_y_estable() -> None:
    envelope = _envelope()
    expected = (
        b'{"body_sha256":"'
        + b"0" * 64
        + b'","challenge_id":"11111111-1111-1111-1111-111111111111","installation_id":"KTL-XX-SINTETICA"'
        + b',"method":"POST","nonce":"'
        + b"ab" * 32
        + b'","protocol_version":1,"target":"/v1/license/sync"}'
    )
    assert sa.envelope_bytes(envelope) == expected
    assert sa.envelope_bytes(envelope) == sa.envelope_bytes(envelope)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda env: env.pop("nonce"),
        lambda env: env.__setitem__("extra", 1),
    ],
    ids=["falta_nonce", "clave_extra"],
)
def test_sac_05_envelope_bytes_rechaza_sobre_malformado(mutate) -> None:
    envelope = _envelope()
    mutate(envelope)
    with pytest.raises(sa.SyncAuthContractError) as exc:
        sa.envelope_bytes(envelope)
    assert exc.value.code == "SYNC_ENVELOPE_INVALID"


def test_sac_06_firma_y_verificacion_ok() -> None:
    private_key = Ed25519PrivateKey.generate()
    envelope = _envelope()
    signature = sa.sign_envelope(envelope, private_key)
    assert len(signature) == 128
    int(signature, 16)
    public_pem = sa.public_key_pem_from_private(private_key)
    assert sa.verify_envelope(envelope, signature, public_pem) is True


@pytest.mark.parametrize(
    "field",
    list(sa.ENVELOPE_FIELDS),
    ids=list(sa.ENVELOPE_FIELDS),
)
def test_sac_07_cualquier_campo_alterado_invalida_firma(field: str) -> None:
    private_key = Ed25519PrivateKey.generate()
    public_pem = sa.public_key_pem_from_private(private_key)
    original = _envelope()
    signature = sa.sign_envelope(original, private_key)
    if field == "protocol_version":
        with pytest.raises(sa.SyncAuthContractError) as exc:
            sa.build_envelope(
                installation_id=original["installation_id"],
                challenge_id=original["challenge_id"],
                nonce=original["nonce"],
                method=original["method"],
                target=original["target"],
                body_sha256=original["body_sha256"],
                protocol_version=2,
            )
        assert exc.value.code == "SYNC_PROTOCOL_UNSUPPORTED"
        return
    replacements = {
        "method": "GET",
        "target": "/v1/license/other",
        "body_sha256": "1" * 64,
        "installation_id": "KTL-XX-OTRA",
        "challenge_id": "22222222-2222-2222-2222-222222222222",
        "nonce": "cd" * 32,
    }
    altered = dict(original)
    altered[field] = replacements[field]
    assert sa.verify_envelope(altered, signature, public_pem) is False


def test_sac_08_verificacion_falla_sin_lanzar() -> None:
    private_key = Ed25519PrivateKey.generate()
    other_key = Ed25519PrivateKey.generate()
    envelope = _envelope()
    signature = sa.sign_envelope(envelope, private_key)
    public_pem = sa.public_key_pem_from_private(private_key)
    other_pem = sa.public_key_pem_from_private(other_key)
    assert sa.verify_envelope(envelope, signature, other_pem) is False
    assert sa.verify_envelope(envelope, "00" * 64, public_pem) is False
    assert sa.verify_envelope(envelope, "no-es-hex", public_pem) is False


def test_sac_09_parse_protocol_version_acepta_uno_y_rechaza_resto() -> None:
    assert sa.parse_protocol_version(1) == 1
    assert sa.parse_protocol_version("1") == 1
    for value in (2, "2", "x", True, None, 1.5):
        with pytest.raises(sa.SyncAuthContractError) as exc:
            sa.parse_protocol_version(value)
        assert exc.value.code == "SYNC_PROTOCOL_UNSUPPORTED"


def test_sac_10_new_nonce_y_nonce_digest() -> None:
    nonce = sa.new_nonce()
    assert len(nonce) == 64
    assert nonce == nonce.lower()
    int(nonce, 16)
    assert sa.new_nonce() != nonce
    assert sa.nonce_digest("abc") == hashlib.sha256(b"abc").hexdigest()


def test_sac_11_body_sha256_de_vacio() -> None:
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert sa.body_sha256(b"") == expected


def test_sac_12_canonical_body() -> None:
    assert sa.canonical_body({"b": 1, "a": "ñ"}) == '{"a":"ñ","b":1}'.encode()


def test_sac_13_public_key_fingerprint() -> None:
    private_key = Ed25519PrivateKey.generate()
    other_key = Ed25519PrivateKey.generate()
    public_pem = sa.public_key_pem_from_private(private_key)
    other_pem = sa.public_key_pem_from_private(other_key)
    fingerprint = sa.public_key_fingerprint(public_pem)
    assert len(fingerprint) == 64
    assert fingerprint == fingerprint.lower()
    int(fingerprint, 16)
    assert sa.public_key_fingerprint(public_pem) == fingerprint
    assert sa.public_key_fingerprint(other_pem) != fingerprint
    with pytest.raises(ValueError):
        sa.public_key_fingerprint("no es pem")


def test_sac_14_constantes_del_contrato() -> None:
    assert sa.SYNC_METHOD == "POST"
    assert sa.SYNC_TARGET == "/v1/license/sync"
    assert sa.CHALLENGE_TARGET == "/v1/license/sync/challenge"
    assert sa.PROTOCOL_VERSION == 1
