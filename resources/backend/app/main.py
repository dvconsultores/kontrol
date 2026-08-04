"""Punto de entrada de la API de KONTROL.

Reúne: configuración, logging, middleware de request ID y licencia,
manejadores de errores uniformes y routers de los módulos fundacionales.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import LicenseMiddleware, RequestIDMiddleware
from app.modules.audit.api import router as audit_router
from app.modules.fiscal.api import router as fiscal_router
from app.modules.identity_access.api import router as auth_router
from app.modules.identity_access.api import users_router
from app.modules.inventory.api import router as inventory_router
from app.modules.licensing import service as licensing_service
from app.modules.licensing.api import router as license_router
from app.modules.master_data.api import router as master_data_router
from app.modules.organization.api import router as organization_router
from app.modules.purchasing.api import router as purchasing_router
from app.modules.regulatory.api import router as regulatory_router
from app.modules.sales.api import router as sales_router
from app.modules.setup.api import router as setup_router
from app.modules.system.api import router as system_router
from app.modules.treasury.api import router as treasury_router

configure_logging()
settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Plataforma Administrativa Empresarial para Venezuela — API fundacional",
        docs_url=None if settings.environment == "prod" else "/docs",
        redoc_url=None if settings.environment == "prod" else "/redoc",
    )

    # CORS restrictivo
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Middleware de licencia (bloquea escrituras en READ_ONLY)
    def _get_mode() -> str:
        db = get_session_factory()()
        try:
            return licensing_service.current_mode(db)
        finally:
            db.close()

    app.add_middleware(LicenseMiddleware, get_mode=_get_mode)
    app.add_middleware(RequestIDMiddleware)

    # Manejo de errores uniforme
    register_exception_handlers(app)

    # Routers
    prefix = settings.api_prefix
    app.include_router(system_router, prefix=prefix)
    app.include_router(setup_router, prefix=prefix)
    app.include_router(license_router, prefix=prefix)
    app.include_router(auth_router, prefix=prefix)
    app.include_router(users_router, prefix=prefix)
    app.include_router(organization_router, prefix=prefix)
    app.include_router(master_data_router, prefix=prefix)
    app.include_router(inventory_router, prefix=prefix)
    app.include_router(purchasing_router, prefix=prefix)
    app.include_router(sales_router, prefix=prefix)
    app.include_router(treasury_router, prefix=prefix)
    app.include_router(fiscal_router, prefix=prefix)
    app.include_router(regulatory_router, prefix=prefix)
    app.include_router(audit_router, prefix=prefix)

    @app.get("/")
    def root():
        return {"service": settings.app_name, "version": settings.app_version, "status": "ok"}

    return app


app = create_app()
