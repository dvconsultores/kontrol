"""Idempotencia (ADR-013): Idempotency-Key en operaciones críticas.

Almacena el resultado de una operación por clave para que un reintento
no duplique efectos (FR-001-063, EDGE-19).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.modules.system.models import IdempotencyRecord


def new_idempotency_key() -> str:
    return uuid.uuid4().hex


def _hash_response(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, default=str, sort_keys=True).encode()).hexdigest()


def get_or_record(
    db: Session,
    *,
    key: str,
    method: str,
    path: str,
    user_id: str | None,
    company_id: str | None,
    executor: Callable[[], tuple[int, dict[str, Any]]],
) -> tuple[int, dict[str, Any]]:
    """Ejecuta `executor` una sola vez por `key`.

    Devuelve (status, payload) del resultado original en reintentos.
    """
    existing = db.query(IdempotencyRecord).filter(IdempotencyRecord.key == key).first()
    if existing:
        return existing.response_status, existing.response_payload

    status, payload = executor()

    record = IdempotencyRecord(
        key=key,
        method=method,
        path=path,
        user_id=user_id,
        company_id=company_id,
        response_status=status,
        response_hash=_hash_response(payload),
        response_payload=payload,
    )
    db.add(record)
    try:
        db.commit()
    except ConflictError:
        db.rollback()
        raise
    return status, payload


def require_idempotency_key(request: Request) -> str:
    key = request.headers.get("Idempotency-Key")
    if not key:
        raise ConflictError(code="IDEMPOTENCY_KEY_REQUIRED", message="Se requiere Idempotency-Key para esta operación")
    return key
