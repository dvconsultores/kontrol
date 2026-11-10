"""Base de datos (SQLAlchemy 2) y sesiones.

PostgreSQL es la única fuente de verdad transaccional (ADR-003).
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

# Convención de nombres para constraints (consistente y migrable).
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)  # type: ignore[arg-type]


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine():
    global _engine
    if _engine is None:
        url = get_settings().db_url
        # La sesión es UTC para que la serialización de los instantes no dependa
        # de la configuración del servidor (FR-001-251, ADR-020); la fecha de
        # negocio la deriva la aplicación en Caracas.
        if url.startswith("postgresql"):
            _engine = create_engine(
                url,
                connect_args={"options": "-c timezone=UTC"},
                pool_pre_ping=True,
                pool_recycle=1800,
                future=True,
            )
        else:
            _engine = create_engine(
                url,
                pool_pre_ping=True,
                pool_recycle=1800,
                future=True,
            )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            class_=Session,
            expire_on_commit=False,
            autoflush=False,
        )
    return _SessionLocal


def get_db() -> Generator[Session]:
    """Dependencia FastAPI que provee una sesión por request."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def init_models() -> None:
    """Importa todos los modelos para registrar metadata (usado por Alembic autogenerate y tests).

    Importa explícitamente cada submódulo `models` para garantizar que las
    tablas queden registradas en `Base.metadata` (los `__init__.py` de módulo
    no importan modelos).
    """
    import app.modules.approvals.models  # noqa: F401
    import app.modules.audit.models  # noqa: F401
    import app.modules.commercial.models  # noqa: F401
    import app.modules.documents.models  # noqa: F401
    import app.modules.fiscal.models  # noqa: F401
    import app.modules.government.models  # noqa: F401
    import app.modules.homologation.models  # noqa: F401
    import app.modules.identity_access.models  # noqa: F401
    import app.modules.imports.models  # noqa: F401
    import app.modules.inventory.models  # noqa: F401
    import app.modules.licensing.models  # noqa: F401
    import app.modules.master_data.models  # noqa: F401
    import app.modules.notifications.models  # noqa: F401
    import app.modules.organization.models  # noqa: F401
    import app.modules.purchasing.models  # noqa: F401
    import app.modules.regulatory.models  # noqa: F401
    import app.modules.reporting.models  # noqa: F401
    import app.modules.sales.models  # noqa: F401
    import app.modules.scheduler.models  # noqa: F401
    import app.modules.storage.models  # noqa: F401
    import app.modules.system.models  # noqa: F401
    import app.modules.treasury.models  # noqa: F401


# Re-export para conveniencia de módulos
__all__ = ["Base", "get_db", "get_engine", "get_session_factory", "init_models", "Session"]
