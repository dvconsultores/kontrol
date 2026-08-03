"""Dependencias FastAPI: usuario actual, permisos y licencia (P6/P8)."""

from __future__ import annotations

import jwt as pyjwt
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core import license as license_engine
from app.core import security
from app.core.database import get_db
from app.core.errors import PermissionDeniedError
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Resuelve el usuario desde el access token (en memoria / header).

    ADR-004: el access token es de corta duración y NO se guarda en
    localStorage; el refresh va en cookie HttpOnly.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise PermissionDeniedError(code="AUTH_REQUIRED", message="Debe iniciar sesión", status_code=401)
    token = auth_header.removeprefix("Bearer ").strip()
    try:
        payload = security.decode_token(token, expected_type="access")
    except pyjwt.PyJWTError:
        raise PermissionDeniedError(code="AUTH_INVALID_TOKEN", message="Sesión inválida o expirada", status_code=401) from None

    user = db.get(User, payload.get("sub"))
    if not user or user.status != "ACTIVE":
        raise PermissionDeniedError(code="AUTH_USER_INACTIVE", message="El usuario no está activo", status_code=403)
    return user


def current_user_permissions(user: User = Depends(get_current_user)) -> list[str]:
    # Se resuelven bajo demanda con la sesión; ver require_permission.
    return []


def require_permission(resource: str, action: str):
    """Dependencia: requiere permiso resource:action (deny by default)."""

    def checker(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        permissions = identity_service.get_user_permissions(db, user)
        if not identity_service.user_has_permission(user, permissions, resource, action):
            raise PermissionDeniedError()
        return user

    return checker


def get_license_mode(db: Session = Depends(get_db)) -> str:
    """Modo actual de licencia (FR-001-052)."""
    from app.modules.licensing import service as licensing_service

    return licensing_service.current_mode(db)


def require_write_allowed(mode: str = Depends(get_license_mode)) -> None:
    """Bloquea escrituras en READ_ONLY / SECURITY_SUSPENSION (FR-001-053)."""
    license_engine.ensure_write_allowed(mode)
