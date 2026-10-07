"""Contrato PURO de autenticación de la instalación ante la Autoridad Central (Spec 004 ·
`CENTRAL-SYNC-AUTHORITY-UNDEFINED`): desafío-respuesta con la identidad Ed25519 de la instalación.

Lo comparten el cliente (que firma) y la autoridad (que verifica), igual que `license_contract`:
sin SQLAlchemy, sin settings, sin red. Tres autoridades que no se mezclan: la clave privada de la
INSTALACIÓN prueba «esta petición viene de la instalación X» (este módulo); la clave del PROPIETARIO
firma licencias (`license_contract`); TLS protege el canal. El sobre canónico que se firma liga la
versión del protocolo, la identidad, el desafío, el nonce, el método, el destino canónico y el
SHA-256 de los bytes EXACTOS del cuerpo: cambiar cualquiera invalida la firma. No lleva reloj del
cliente: la vida del desafío la controla la autoridad.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.license_contract import load_public_key

#: Única versión admitida en la Fase 1. Una versión distinta se rechaza: no hay degradación silenciosa.
PROTOCOL_VERSION = 1
SYNC_METHOD = "POST"
SYNC_TARGET = "/v1/license/sync"
CHALLENGE_TARGET = "/v1/license/sync/challenge"
#: Cabeceras del transporte de la prueba (el cuerpo de negocio no se contamina).
HEADER_INSTALLATION = "X-Kontrol-Installation"
HEADER_CHALLENGE = "X-Kontrol-Challenge"
HEADER_NONCE = "X-Kontrol-Nonce"
HEADER_PROTOCOL = "X-Kontrol-Sync-Protocol"
HEADER_SIGNATURE = "X-Kontrol-Signature"
#: Orden fijo de los campos del sobre; la serialización canónica los exige todos y ninguno más.
ENVELOPE_FIELDS = ("protocol_version", "installation_id", "challenge_id", "nonce", "method", "target", "body_sha256")
#: 256 bits de aleatoriedad criptográfica, en hexadecimal minúsculo.
NONCE_BYTES = 32


class SyncAuthContractError(Exception):
    """El sobre o uno de sus campos no cumple el contrato."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def new_nonce() -> str:
    return secrets.token_hex(NONCE_BYTES)


def nonce_digest(nonce: str) -> str:
    """Lo que la autoridad guarda: el SHA-256 del nonce, nunca el nonce."""
    return hashlib.sha256(nonce.encode("utf-8")).hexdigest()


def body_sha256(body: bytes) -> str:
    """SHA-256 en hexadecimal minúsculo de los bytes exactos del cuerpo (los que viajan)."""
    return hashlib.sha256(body).hexdigest()


def canonical_body(payload: dict[str, Any]) -> bytes:
    """Los bytes del cuerpo: se serializa UNA vez, se hashea, se firma el sobre y se envían ESTOS bytes."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def parse_protocol_version(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int | str):
        raise SyncAuthContractError("SYNC_PROTOCOL_UNSUPPORTED", "Versión del protocolo de sincronización no admitida.")
    try:
        version = int(value)
    except ValueError:
        raise SyncAuthContractError("SYNC_PROTOCOL_UNSUPPORTED", "Versión del protocolo de sincronización no admitida.") from None
    if version != PROTOCOL_VERSION:
        raise SyncAuthContractError("SYNC_PROTOCOL_UNSUPPORTED", "Versión del protocolo de sincronización no admitida.")
    return version


def _texto(valor: Any, campo: str, maximo: int) -> str:
    if not isinstance(valor, str) or not valor.strip() or len(valor) > maximo or any(c.isspace() for c in valor):
        raise SyncAuthContractError("SYNC_ENVELOPE_INVALID", f"El campo {campo} del sobre no es válido.")
    return valor


def build_envelope(*, installation_id: str, challenge_id: str, nonce: str, method: str, target: str,
                   body_sha256: str, protocol_version: int = PROTOCOL_VERSION) -> dict[str, Any]:
    """El sobre canónico. Método en mayúsculas; destino: ruta normalizada sin consulta (`?`) ni fragmento."""
    if not isinstance(method, str) or not method.strip():
        raise SyncAuthContractError("SYNC_ENVELOPE_INVALID", "El método del sobre no es válido.")
    if not isinstance(target, str) or not target.startswith("/") or "?" in target or "#" in target or any(c.isspace() for c in target):
        raise SyncAuthContractError("SYNC_ENVELOPE_INVALID", "El destino del sobre no es válido.")
    if not isinstance(body_sha256, str) or len(body_sha256) != 64 or body_sha256 != body_sha256.lower() or any(
            c not in "0123456789abcdef" for c in body_sha256):
        raise SyncAuthContractError("SYNC_ENVELOPE_INVALID", "El resumen del cuerpo debe ser SHA-256 en hexadecimal minúsculo.")
    return {
        "protocol_version": parse_protocol_version(protocol_version),
        "installation_id": _texto(installation_id, "installation_id", 64),
        "challenge_id": _texto(challenge_id, "challenge_id", 64),
        "nonce": _texto(nonce, "nonce", 128),
        "method": method.strip().upper(),
        "target": target,
        "body_sha256": body_sha256,
    }


def envelope_bytes(envelope: dict[str, Any]) -> bytes:
    """Serialización canónica y determinista del sobre: JSON UTF-8, claves ordenadas, sin espacios.
    Exige exactamente los siete campos del contrato."""
    if set(envelope) != set(ENVELOPE_FIELDS):
        raise SyncAuthContractError("SYNC_ENVELOPE_INVALID", "El sobre no tiene exactamente los campos del contrato.")
    normalizado = build_envelope(**envelope)
    return json.dumps(normalizado, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sign_envelope(envelope: dict[str, Any], private_key: Ed25519PrivateKey) -> str:
    """Firma con la clave privada de la INSTALACIÓN (nunca la del propietario)."""
    return private_key.sign(envelope_bytes(envelope)).hex()


def verify_envelope(envelope: dict[str, Any], signature_hex: str, public_key_pem: str) -> bool:
    """Verifica con la clave pública PREVIAMENTE vinculada en el registro; nunca con una que traiga la petición."""
    try:
        load_public_key(public_key_pem).verify(bytes.fromhex(signature_hex), envelope_bytes(envelope))
        return True
    except (InvalidSignature, ValueError, TypeError, SyncAuthContractError):
        return False


def public_key_fingerprint(public_key_pem: str) -> str:
    """Huella determinista de la clave pública: SHA-256 de sus bytes DER (SubjectPublicKeyInfo). Identifica; no autentica."""
    der = load_public_key(public_key_pem).public_bytes(encoding=serialization.Encoding.DER,
                                                       format=serialization.PublicFormat.SubjectPublicKeyInfo)
    return hashlib.sha256(der).hexdigest()


def public_key_pem_from_private(private_key: Ed25519PrivateKey) -> str:
    """La clave pública de la instalación, derivada localmente; la privada no sale de aquí."""
    return private_key.public_key().public_bytes(encoding=serialization.Encoding.PEM,
                                                 format=serialization.PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
