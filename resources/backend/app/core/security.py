"""Seguridad: Argon2id, tokens JWT, cookies y utilidades.

Decisión ADR-004: refresh token en cookie HttpOnly/Secure/SameSite y
access token de corta duración en memoria. Contraseñas con Argon2id.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError as Argon2VerificationError

from app.core.config import get_settings

_hasher = PasswordHasher()

_COMMON_PASSWORDS = {
    "password",
    "kontrol",
    "123456",
    "12345678",
    "admin",
    "password123",
    "qwerty",
    "abc123",
    "letmein",
    "contraseña",
}


# --------------------------------------------------------------------------- #
# Contraseñas (Argon2id)
# --------------------------------------------------------------------------- #
def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, plain)
    except Argon2VerificationError:
        return False


def validate_password_policy(plain: str, min_length: int | None = None) -> list[str]:
    """Retorna lista de incumplimientos de la política de contraseñas."""
    settings = get_settings()
    min_len = min_length or settings.password_min_length
    errors: list[str] = []
    if len(plain) < min_len:
        errors.append(f"La contraseña debe tener al menos {min_len} caracteres")
    if not any(c.islower() for c in plain):
        errors.append("Debe incluir al menos una letra minúscula")
    if not any(c.isupper() for c in plain):
        errors.append("Debe incluir al menos una letra mayúscula")
    if not any(c.isdigit() for c in plain):
        errors.append("Debe incluir al menos un número")
    lowered = plain.lower()
    if lowered in _COMMON_PASSWORDS or "password" in lowered:
        errors.append("La contraseña es demasiado común")
    return errors


# --------------------------------------------------------------------------- #
# Tokens JWT
# --------------------------------------------------------------------------- #
def _now() -> datetime:
    return datetime.now(UTC)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "iat": _now(),
        "exp": _now() + timedelta(minutes=settings.access_token_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, session_id: str, jti: str) -> str:
    settings = get_settings()
    payload = {
        "sub": subject,
        "type": "refresh",
        "sid": session_id,
        "jti": jti,
        "iat": _now(),
        "exp": _now() + timedelta(days=settings.refresh_token_days),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    settings = get_settings()
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Tipo de token inválido")
    return payload


def generate_secret_token(length: int = 32) -> str:
    """Token aleatorio para recuperación de contraseña (se almacena su hash)."""
    return secrets.token_urlsafe(length)


def sha256_hex(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Cookies
# --------------------------------------------------------------------------- #
def cookie_params(max_age_seconds: int | None = None) -> dict[str, Any]:
    settings = get_settings()
    params: dict[str, Any] = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": "/",
    }
    if max_age_seconds is not None:
        params["max_age"] = max_age_seconds
    return params
