"""API de la Autoridad Central: health y el sync AUTENTICADO (desafío-respuesta con la identidad
Ed25519 de la instalación; Spec 004 · `CENTRAL-SYNC-AUTHORITY-UNDEFINED`). Sin API de administración
pública (las operaciones del propietario van por la CLI). Sin `/docs`."""

from __future__ import annotations

import json
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import sync_auth_contract as sync_auth
from central_authority import __version__, service
from central_authority.config import SERVICE_NAME, get_settings
from central_authority.database import get_db


def _error(exc: service.SyncAuthError) -> JSONResponse:
    cabeceras = {"Retry-After": str(exc.retry_after_seconds)} if isinstance(exc, service.SyncRateLimited) else None
    return JSONResponse({"code": exc.code, "message": str(exc)}, status_code=exc.status_code, headers=cabeceras)


def create_app() -> FastAPI:
    get_settings()  # en `prod`, sin clave de firma la configuración no carga y el servicio no arranca
    app = FastAPI(title="KONTROL Central Licensing Authority", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME}

    @app.get("/health/ready")
    def ready(db: Session = Depends(get_db)) -> dict[str, str]:
        try:
            db.execute(text("SELECT 1"))
        except Exception:
            return {"status": "degraded", "service": SERVICE_NAME, "database": "unreachable"}
        return {"status": "ok", "service": SERVICE_NAME, "database": "ok"}

    @app.post(sync_auth.CHALLENGE_TARGET)
    async def challenge(request: Request, db: Session = Depends(get_db)) -> Any:
        """Pre-autenticación por necesidad: devuelve solo lo que hace falta para construir la prueba."""
        try:
            cuerpo = json.loads(await request.body() or b"{}")
        except ValueError:
            cuerpo = None
        try:
            return service.create_sync_challenge(db, settings=get_settings(),
                                                 installation_uuid=cuerpo.get("installation_id") if isinstance(cuerpo, dict) else None)
        except service.SyncAuthError as exc:
            return _error(exc)

    @app.post(sync_auth.SYNC_TARGET)
    async def sync(request: Request, db: Session = Depends(get_db)) -> Any:
        """Autentica con los bytes EXACTOS recibidos, consume el desafío y devuelve el artefacto del libro."""
        body = await request.body()
        try:
            instalacion = service.authenticate_sync(db, headers=request.headers, method=request.method, path=request.url.path,
                                                    query=request.url.query, body=body)
            try:
                datos = json.loads(body)
            except ValueError:
                datos = None
            return service.sync_response(db, installation=instalacion, body=datos,
                                         challenge_id=request.headers.get(sync_auth.HEADER_CHALLENGE, ""))
        except service.SyncAuthError as exc:
            return _error(exc)

    return app


app = create_app()
