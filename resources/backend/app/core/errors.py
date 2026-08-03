"""Contrato uniforme de errores de la API (FR-001-063, NFR-001-001).

Formato: {code, message, field_errors, request_id, details}. Nunca se
retornan excepciones SQL, stack traces, rutas internas ni secretos.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class KontrolError(Exception):
    """Error funcional controlado con código y mensaje amigable."""

    status_code = 400

    def __init__(
        self,
        code: str,
        message: str,
        *,
        field_errors: dict[str, list[str]] | None = None,
        details: Any = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field_errors = field_errors or {}
        self.details = details
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(KontrolError):
    status_code = 404

    def __init__(self, code: str = "NOT_FOUND", message: str = "Recurso no encontrado"):
        super().__init__(code=code, message=message, status_code=404)


class PermissionDeniedError(KontrolError):
    status_code = 403

    def __init__(
        self,
        code: str = "PERMISSION_DENIED",
        message: str = "No tiene permiso para esta acción",
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(code=code, message=message, status_code=status_code or 403)


class ScopeDeniedError(KontrolError):
    status_code = 403

    def __init__(self, message: str = "Fuera de su alcance organizacional"):
        super().__init__(code="SCOPE_DENIED", message=message, status_code=403)


class ConflictError(KontrolError):
    status_code = 409

    def __init__(self, code: str = "CONFLICT", message: str = "Conflicto al procesar la operación"):
        super().__init__(code=code, message=message, status_code=409)


class LicenseBlockedError(KontrolError):
    """Bloqueo por licencia (HTTP 423)."""

    status_code = 423

    def __init__(self, *, code: str = "LICENSE_READ_ONLY", message: str = "Operación bloqueada por la licencia", details: Any = None):
        super().__init__(code=code, message=message, status_code=423, details=details)


def error_payload(
    *,
    code: str,
    message: str,
    request_id: str,
    field_errors: dict[str, list[str]] | None = None,
    details: Any = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "field_errors": field_errors or {},
        "request_id": request_id,
        "details": details,
    }


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(KontrolError)
    async def _kontrol_error_handler(request: Request, exc: KontrolError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(
                code=exc.code,
                message=exc.message,
                request_id=_request_id(request),
                field_errors=exc.field_errors,
                details=exc.details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        field_errors: dict[str, list[str]] = {}
        for err in exc.errors():
            loc = [str(x) for x in err.get("loc", []) if x != "body"]
            key = ".".join(loc) or "_"
            field_errors.setdefault(key, []).append(err.get("msg", "Valor inválido"))
        return JSONResponse(
            status_code=422,
            content=error_payload(
                code="VALIDATION_ERROR",
                message="Revise la información enviada",
                request_id=_request_id(request),
                field_errors=field_errors,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            401: "AUTH_INVALID_CREDENTIALS",
            403: "PERMISSION_DENIED",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            429: "RATE_LIMITED",
        }.get(exc.status_code, f"HTTP_{exc.status_code}")
        message = str(exc.detail) if isinstance(exc.detail, str) else "Error de la solicitud"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(code=code, message=message, request_id=_request_id(request)),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        import logging

        logging.getLogger("kontrol").exception("Error no controlado", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=error_payload(
                code="INTERNAL_ERROR",
                message="Ocurrió un error interno. Intente nuevamente.",
                request_id=_request_id(request),
            ),
        )
