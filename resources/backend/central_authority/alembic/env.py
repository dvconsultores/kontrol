"""Entorno Alembic de la Autoridad Central: su propia base y su propia tabla de versión."""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import create_engine, pool

from alembic import context

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from central_authority.config import get_settings  # noqa: E402
from central_authority.models import Base  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
# Misma raíz que el cliente: la URL no pasa por `configparser` («%» es interpolación allí); va directa a
# SQLAlchemy, como en `central_authority/database.py` (MIGRACIONES-URL-CON-PORCENTAJE).
settings = get_settings()
VERSION_TABLE = "cla_alembic_version"


def run_migrations_offline() -> None:
    context.configure(url=settings.db_url, target_metadata=target_metadata,
                      literal_binds=True, version_table=VERSION_TABLE)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(settings.db_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, version_table=VERSION_TABLE)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
