"""RVR · Verifica caso por caso la función pura `evaluate_current_artifact` de reverificación.

Cubre los vectores V1..V13 con claves Ed25519 sintéticas generadas en la propia prueba.
"""

from __future__ import annotations

from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core import license_reverification as rv
from app.core.license_contract import payload_hash, sign_license_payload

_CENTINELA = object()


def _pub(clave: Ed25519PrivateKey) -> str:
    return clave.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


def _payload(**extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "issuer": "QA",
        "license_id": "LIC-X",
        "installation_id": "KTL-XX-INST",
        "customer_id": "C",
        "contract_id": "K",
        "company_tax_id": "J-0",
        "period_start": "2030-04-01T00:00:00-04:00",
        "period_end": "2031-03-31T23:59:59-04:00",
        "critical_warning_start": "2031-04-21T00:00:00-04:00",
        "read_only_start": "2031-05-01T00:00:00-04:00",
        "entitlements": {"companies": 3},
        "minimum_version": "1.0.0",
        "kid": "kid-a",
    }
    base.update(extra)
    return base


def _caso(clave: Ed25519PrivateKey, payload: Any, **kw: Any) -> rv.Reverification:
    signature_hex = kw.pop("signature_hex", _CENTINELA)
    if signature_hex is _CENTINELA:
        signature_hex = sign_license_payload(payload, clave)
    stored_hash = kw.pop("stored_hash", _CENTINELA)
    if stored_hash is _CENTINELA:
        stored_hash = payload_hash(payload)
    installation_uuid = kw.pop("installation_uuid", "KTL-XX-INST")
    state_license_id = kw.pop("state_license_id", "LIC-X")
    trust_set = kw.pop("trust_set", {"kid-a": _pub(clave)})
    assert not kw
    return rv.evaluate_current_artifact(
        payload=payload,
        signature_hex=signature_hex,
        stored_hash=stored_hash,
        installation_uuid=installation_uuid,
        state_license_id=state_license_id,
        trust_set=trust_set,
    )


def test_rvr_01_caso_base_valido() -> None:
    a = Ed25519PrivateKey.generate()
    r = _caso(a, _payload())
    assert r.status == rv.VALID
    assert r.reason == "ok"
    assert r.license_id == "LIC-X"
    assert r.kid == "kid-a"
    assert r.grants_authority is True


@pytest.mark.parametrize(
    "payload",
    [None, "texto"],
    ids=["payload-none", "payload-texto"],
)
def test_rvr_02_artifact_unreadable_payload(payload: object) -> None:
    a = Ed25519PrivateKey.generate()
    r = _caso(a, payload, signature_hex="00", stored_hash="0" * 64)
    assert r.status == rv.MALFORMED_ARTIFACT
    assert r.reason == "artifact_unreadable"
    assert r.license_id == "LIC-X"
    assert r.kid is None
    assert r.grants_authority is False


def test_rvr_02_artifact_unreadable_signature_none() -> None:
    a = Ed25519PrivateKey.generate()
    r = _caso(a, _payload(), signature_hex=None)
    assert r.status == rv.MALFORMED_ARTIFACT
    assert r.reason == "artifact_unreadable"
    assert r.license_id == "LIC-X"
    assert r.kid is None
    assert r.grants_authority is False


def test_rvr_03_stored_hash_distinto() -> None:
    a = Ed25519PrivateKey.generate()
    r = _caso(a, _payload(), stored_hash="0" * 64)
    assert r.status == rv.ARTIFACT_STATE_MISMATCH
    assert r.reason == "payload_hash"


def test_rvr_03_payload_alterado_tras_firmar() -> None:
    a = Ed25519PrivateKey.generate()
    original = _payload()
    firma = sign_license_payload(original, a)
    huella = payload_hash(original)
    alterado = _payload(entitlements={"companies": 999})
    r = _caso(a, alterado, signature_hex=firma, stored_hash=huella)
    assert r.status == rv.ARTIFACT_STATE_MISMATCH
    assert r.reason == "payload_hash"
    assert r.license_id == "LIC-X"
    assert r.kid == "kid-a"
    assert r.grants_authority is False


def test_rvr_04_license_id_distinto_del_estado() -> None:
    a = Ed25519PrivateKey.generate()
    r = _caso(a, _payload(), state_license_id="LIC-OTRA")
    assert r.status == rv.ARTIFACT_STATE_MISMATCH
    assert r.reason == "license_id"


@pytest.mark.parametrize("kid", [None, ""], ids=["kid-eliminado", "kid-vacio"])
def test_rvr_05_kid_missing(kid: object) -> None:
    a = Ed25519PrivateKey.generate()
    payload = _payload()
    if kid is None:
        del payload["kid"]
    else:
        payload["kid"] = kid
    r = _caso(a, payload)
    assert r.status == rv.KID_MISSING
    assert r.reason == "kid_missing"
    assert r.grants_authority is False


def test_rvr_06_kid_desconocido() -> None:
    a = Ed25519PrivateKey.generate()
    r = _caso(a, _payload(kid="kid-z"))
    assert r.status == rv.KID_UNKNOWN
    assert r.reason == "unknown_kid"
    assert r.license_id == "LIC-X"
    assert r.kid == "kid-z"
    assert r.grants_authority is False


def test_rvr_07_firma_de_otra_clave_de_confianza() -> None:
    a = Ed25519PrivateKey.generate()
    b = Ed25519PrivateKey.generate()
    r = _caso(a, _payload(kid="kid-a"), signature_hex=sign_license_payload(_payload(kid="kid-a"), b),
              trust_set={"kid-a": _pub(a), "kid-b": _pub(b)})
    assert r.status == rv.SIGNATURE_INVALID
    assert r.reason == "owner_signature"
    assert r.license_id == "LIC-X"
    assert r.kid == "kid-a"
    assert r.grants_authority is False


@pytest.mark.parametrize(
    "signature_hex",
    ["00" * 64, "no-hex"],
    ids=["firma-ceros", "firma-no-hex"],
)
def test_rvr_08_firma_invalida(signature_hex: str) -> None:
    a = Ed25519PrivateKey.generate()
    r = _caso(a, _payload(), signature_hex=signature_hex)
    assert r.status == rv.SIGNATURE_INVALID
    assert r.reason == "owner_signature"
    assert r.grants_authority is False


def test_rvr_09_period_start_ausente() -> None:
    a = Ed25519PrivateKey.generate()
    payload = _payload()
    del payload["period_start"]
    r = _caso(a, payload)
    assert r.status == rv.MALFORMED_ARTIFACT
    assert r.grants_authority is False


def test_rvr_09_revision_cero() -> None:
    a = Ed25519PrivateKey.generate()
    r = _caso(a, _payload(revision=0))
    assert r.status == rv.MALFORMED_ARTIFACT
    assert r.reason == "LICENSE_INVALID_REVISION"
    assert r.grants_authority is False


def test_rvr_10_installation_mismatch() -> None:
    a = Ed25519PrivateKey.generate()
    r = _caso(a, _payload(), installation_uuid="KTL-XX-OTRA")
    assert r.status == rv.INSTALLATION_MISMATCH
    assert r.reason == "installation_id"
    assert r.license_id == "LIC-X"
    assert r.kid == "kid-a"
    assert r.grants_authority is False


def test_rvr_11_integridad_antes_que_kid() -> None:
    a = Ed25519PrivateKey.generate()
    r = _caso(a, _payload(kid="kid-z"), stored_hash="0" * 64)
    assert r.status == rv.ARTIFACT_STATE_MISMATCH
    assert r.reason == "payload_hash"


def test_rvr_11_kid_antes_que_identidad() -> None:
    a = Ed25519PrivateKey.generate()
    r = _caso(a, _payload(kid="kid-z"), installation_uuid="KTL-XX-OTRA")
    assert r.status == rv.KID_UNKNOWN
    assert r.reason == "unknown_kid"
    assert r.kid == "kid-z"


def test_rvr_12_conjuntos_y_autoridad() -> None:
    assert rv.FAILURES == frozenset(
        {
            rv.MALFORMED_ARTIFACT,
            rv.KID_MISSING,
            rv.KID_UNKNOWN,
            rv.SIGNATURE_INVALID,
            rv.INSTALLATION_MISMATCH,
            rv.ARTIFACT_STATE_MISMATCH,
            rv.TRUST_SET_INVALID,
        }
    )
    assert rv.VALID not in rv.FAILURES
    assert rv.NO_CURRENT_LICENSE not in rv.FAILURES
    assert rv.Reverification(rv.VALID, "ok").grants_authority is True
    assert rv.Reverification(rv.NO_CURRENT_LICENSE, "no_state").grants_authority is False


def test_rvr_13_determinismo_y_no_mutacion() -> None:
    a = Ed25519PrivateKey.generate()
    payload = _payload()
    copia = {**payload, "entitlements": dict(payload["entitlements"])}
    r1 = _caso(a, payload)
    r2 = _caso(a, payload)
    assert r1 == r2
    assert payload == copia
    assert r1.status == rv.VALID
