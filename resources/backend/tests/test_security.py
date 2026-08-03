"""Pruebas de seguridad: Argon2id, política de contraseñas y tokens."""

from __future__ import annotations

import jwt
import pytest

from app.core import security


class TestPasswordHashing:
    def test_hash_and_verify(self) -> None:
        hashed = security.hash_password("SuperSecreto123")
        assert hashed != "SuperSecreto123"
        assert security.verify_password("SuperSecreto123", hashed) is True

    def test_wrong_password_fails(self) -> None:
        hashed = security.hash_password("SuperSecreto123")
        assert security.verify_password("OtraClave999", hashed) is False


class TestPasswordPolicy:
    def test_weak_password_returns_errors(self) -> None:
        errors = security.validate_password_policy("abc")
        assert len(errors) >= 1

    def test_strong_password_passes(self) -> None:
        errors = security.validate_password_policy("Kontrol2026Segura!")
        assert errors == []

    def test_common_password_rejected(self) -> None:
        errors = security.validate_password_policy("Password123")
        assert any("común" in e for e in errors)


class TestTokens:
    def test_access_token_roundtrip(self) -> None:
        token = security.create_access_token("user-1", extra={"tenant_id": "t1"})
        payload = security.decode_token(token, expected_type="access")
        assert payload["sub"] == "user-1"
        assert payload["tenant_id"] == "t1"

    def test_refresh_token_not_usable_as_access(self) -> None:
        refresh = security.create_refresh_token("user-1", session_id="s1", jti="j1")
        with pytest.raises(jwt.InvalidTokenError):
            security.decode_token(refresh, expected_type="access")

    def test_sha256_deterministic(self) -> None:
        assert security.sha256_hex("hola") == security.sha256_hex("hola")
        assert security.sha256_hex("hola") != security.sha256_hex("adios")
