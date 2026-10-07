"""Motor y sesiones de la base PROPIA de la autoridad."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from central_authority.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().db_url, future=True, pool_pre_ping=True)


def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), class_=Session, expire_on_commit=False)


def get_db() -> Generator[Session]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
