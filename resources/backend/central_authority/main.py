"""API mínima de la Autoridad Central: health. Sin sync (bloqueado: `CENTRAL-SYNC-AUTHORITY-UNDEFINED`),
sin API de administración pública (las operaciones del propietario van por la CLI)."""

from __future__ import annotations

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from central_authority import __version__
from central_authority.config import SERVICE_NAME, get_settings
from central_authority.database import get_db


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

    return app


app = create_app()
