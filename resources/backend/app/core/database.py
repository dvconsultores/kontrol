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
        _engine = create_engine(
            get_settings().db_url,
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
    """Importa todos los modelos para registrar metadata (usado por Alembic autogenerate)."""
    from app.modules import (  # noqa: F401
        audit,
        identity_access,
        inventory,
        licensing,
        master_data,
        organization,
        purchasing,
        system,
    )


# Re-export para conveniencia de módulos
__all__ = ["Base", "get_db", "get_engine", "get_session_factory", "init_models", "Session"]
