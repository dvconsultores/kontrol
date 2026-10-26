"""Middleware: request ID y licencia (FR-001-053/081, ADR-010/013).

- RequestID: asigna request_id a cada request para logs y auditoría.
- License: bloquea métodos de escritura de negocio en READ_ONLY antes
  de abrir transacción y antes de reservar correlativos.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core import license as license_engine
from app.core.logging import new_request_id

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Endpoints siempre permitidos en solo consulta (seguridad y renovación).
# DOC-07 §9.1: seguridad y carga de comprobante siguen disponibles.
# /api/v1/setup/: el asistente inicial debe poder ejecutarse aunque aún no
# exista Installation (sin instalación no hay licencia que bloquear).
LICENSE_EXEMPT_PREFIXES = (
    "/api/v1/license/",
    "/api/v1/licensing/sync",  # renovar por sync autenticado en READ_ONLY es legítimo (FR-010-412)
    "/api/v1/setup/",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
    "/api/v1/auth/change-password",
    "/api/v1/auth/password-reset/",
    # Segundo factor (Spec 002): sin él no se completa el login ni la reautenticación que exige la licencia.
    "/api/v1/auth/mfa/verify",
    "/api/v1/auth/mfa/enrollment",  # cubre también /confirm
    "/api/v1/auth/reauth",
    "/api/v1/health/",
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Any:
        request.state.request_id = new_request_id()
        request.state.start_time = __import__("time").time()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response


class LicenseMiddleware(BaseHTTPMiddleware):
    """Bloqueo de escritura según modo de licencia."""

    def __init__(self, app: Any, *, get_mode: Any) -> None:
        super().__init__(app)
        self._get_mode = get_mode

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        path = request.url.path
        if request.method in WRITE_METHODS and not path.startswith(LICENSE_EXEMPT_PREFIXES):
            mode = await run_in_threadpool(self._get_mode)
            if mode in {license_engine.READ_ONLY, license_engine.SECURITY_SUSPENSION}:
                return JSONResponse(
                    status_code=423,
                    content={
                        "code": "LICENSE_READ_ONLY" if mode == license_engine.READ_ONLY else "LICENSE_SECURITY_SUSPENSION",
                        "message": ("La licencia anual de KONTROL no ha sido renovada. " "La instalación se encuentra en modo solo consulta." if mode == license_engine.READ_ONLY else "La licencia no es válida. Contacte al soporte de KONTROL."),
                        "field_errors": {},
                        "request_id": getattr(request.state, "request_id", None),
                        "details": {"license_url": "/mi-licencia"},
                    },
                )
        return await call_next(request)
