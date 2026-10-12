"""Dependencias FastAPI: usuario actual, permisos y licencia (P6/P8)."""

import jwt as pyjwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import license as license_engine
from app.core import security
from app.core.database import get_db
from app.core.errors import PermissionDeniedError
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import User

#: Nombre del esquema de seguridad en el OpenAPI (`components.securitySchemes`): estable y técnico.
BEARER_SCHEME_NAME = "BearerAccessToken"


class BearerAccessToken(HTTPBearer):
    """El único analizador de la credencial, y a la vez el esquema OpenAPI que la describe
    (`OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD`; FR-001-020/021).

    Es un `HTTPBearer` de FastAPI porque eso es lo que la autenticación de KONTROL **es**: un JWT de
    acceso en `Authorization: Bearer …`. Al declararlo como dependencia, FastAPI publica
    `securitySchemes.BearerAccessToken` (`http`/`bearer`/`JWT`) y añade `security` a cada operación
    cuyo árbol de dependencias llegue hasta aquí —es decir, a toda ruta protegida por
    `get_current_user` o `require_permission`—, derivado de la misma primitiva que protege en
    tiempo de ejecución: no hay una segunda lista de rutas que pueda divergir.

    `__call__` conserva la semántica EXACTA que tenía la lectura manual de la cabecera —prefijo
    literal `Bearer ` (sensible a mayúsculas), token con espacios recortados, `Bearer ` vacío
    devuelve credencial vacía (→ `AUTH_INVALID_TOKEN`), otro esquema o ausencia → `None` (→
    `AUTH_REQUIRED`)— y nunca lanza por sí mismo: los códigos y estados los sigue decidiendo
    `get_current_user`. El `HTTPBearer` de serie aceptaría `bearer` en minúsculas y convertiría
    `Bearer ` vacío en «no autenticado»; eso cambiaría el contrato, y OpenAPI debe describir el
    runtime, no modificarlo.
    """

    def __init__(self) -> None:
        super().__init__(
            scheme_name=BEARER_SCHEME_NAME,
            bearerFormat="JWT",
            description="Access token JWT de corta duración emitido por `POST /auth/login` o `POST /auth/refresh`; "
            "se envía como `Authorization: Bearer <token>`. El refresh viaja en cookie HttpOnly y solo lo consume `/auth/refresh`.",
            auto_error=False,
        )

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:  # type: ignore[override]
        return read_bearer_credentials(request)


def read_bearer_credentials(request: Request) -> HTTPAuthorizationCredentials | None:
    """La lectura de la cabecera, una sola vez para la dependencia y para quien la llame directamente."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=auth_header.removeprefix("Bearer ").strip())


bearer_access_token = BearerAccessToken()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_access_token), db: Session = Depends(get_db)
) -> User:
    """Resuelve el usuario desde el access token (en memoria / header).

    ADR-004: el access token es de corta duración y NO se guarda en
    localStorage; el refresh va en cookie HttpOnly.
    """
    if credentials is None:
        raise PermissionDeniedError(code="AUTH_REQUIRED", message="Debe iniciar sesión", status_code=401)
    token = credentials.credentials
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
