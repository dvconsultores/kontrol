"""Pruebas del motor de licencias (FR-001-050/052/053/055/056).

Cubren: verificación de firma Ed25519, cálculo de modo según calendario,
protección contra retroceso de reloj y bloqueo de escritura.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core import license as license_engine
from app.core.errors import LicenseBlockedError


def _make_keypair():
    private_key = Ed25519PrivateKey.generate()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    return private_key, public_pem


def _sign(private_key, payload: dict) -> str:
    import json

    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return private_key.sign(canonical).hex()


def _payload(period_start=None, period_end=None):
    base = datetime(2026, 4, 1, tzinfo=UTC)
    return {
        "issuer": "KONTROL Licensing Authority",
        "license_id": "LIC-000142",
        "installation_id": "KTL-VE-7D2A-8F91",
        "customer_id": "CUS-000087",
        "contract_id": "CON-000087",
        "company_tax_id": "J-12345678-9",
        "period_start": (period_start or base).isoformat(),
        "period_end": (period_end or base.replace(year=2027, month=3, day=31, hour=23, minute=59, second=59)).isoformat(),
        "critical_warning_start": datetime(2027, 4, 21, tzinfo=UTC).isoformat(),
        "read_only_start": datetime(2027, 5, 1, tzinfo=UTC).isoformat(),
        "entitlements": {"companies": 1, "users": 25, "modules": ["masters"]},
        "minimum_version": "1.0.0",
        "kid": "kontrol-lic-2026-01",
    }


class TestSignatureVerification:
    def test_valid_signature(self) -> None:
        private_key, public_pem = _make_keypair()
        payload = _payload()
        sig = _sign(private_key, payload)
        assert license_engine.verify_license_signature(payload, sig, public_pem) is True

    def test_tampered_payload_rejected(self) -> None:
        private_key, public_pem = _make_keypair()
        payload = _payload()
        sig = _sign(private_key, payload)
        payload["entitlements"] = {"companies": 999}
        assert license_engine.verify_license_signature(payload, sig, public_pem) is False

    def test_wrong_key_rejected(self) -> None:
        _, public_pem_a = _make_keypair()
        private_key_b, _ = _make_keypair()
        payload = _payload()
        sig = _sign(private_key_b, payload)
        assert license_engine.verify_license_signature(payload, sig, public_pem_a) is False


class TestModeComputation:
    def test_full_access_during_paid_period(self) -> None:
        data = license_engine.parse_license_payload(_payload())
        now = datetime(2026, 6, 1, tzinfo=UTC)
        assert license_engine.compute_mode(data, now) == license_engine.FULL_ACCESS

    def test_renewal_notice_after_period(self) -> None:
        data = license_engine.parse_license_payload(_payload())
        now = datetime(2027, 4, 10, tzinfo=UTC)
        assert license_engine.compute_mode(data, now) == license_engine.RENEWAL_NOTICE

    def test_critical_notice(self) -> None:
        data = license_engine.parse_license_payload(_payload())
        now = datetime(2027, 4, 25, tzinfo=UTC)
        assert license_engine.compute_mode(data, now) == license_engine.CRITICAL_RENEWAL_NOTICE

    def test_read_only_after_may_first(self) -> None:
        data = license_engine.parse_license_payload(_payload())
        now = datetime(2027, 5, 5, tzinfo=UTC)
        assert license_engine.compute_mode(data, now) == license_engine.READ_ONLY

    def test_clock_rollback_uses_last_reliable(self) -> None:
        data = license_engine.parse_license_payload(_payload())
        last_reliable = datetime(2027, 5, 5, tzinfo=UTC)
        now = datetime(2027, 1, 1, tzinfo=UTC)  # reloj retrocedido
        assert license_engine.compute_mode(data, now, last_reliable_date=last_reliable) == license_engine.READ_ONLY


class TestWriteBlocking:
    def test_write_blocked_in_read_only(self) -> None:
        with pytest.raises(LicenseBlockedError) as exc:
            license_engine.ensure_write_allowed(license_engine.READ_ONLY)
        assert exc.value.code == "LICENSE_READ_ONLY"
        assert exc.value.status_code == 423

    def test_write_allowed_in_full_access(self) -> None:
        license_engine.ensure_write_allowed(license_engine.FULL_ACCESS)  # no raise

    def test_mode_blocks_write(self) -> None:
        assert license_engine.mode_blocks_write(license_engine.READ_ONLY) is True
        assert license_engine.mode_blocks_write(license_engine.FULL_ACCESS) is False
