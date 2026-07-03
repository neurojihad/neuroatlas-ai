"""Centralized Alembic environment for NeuroAtlas, owned by the Housekeeper service.

ALL database migrations for EVERY service are created and applied here:

    make makemigration m="add patients tables"   # autogenerate a revision
    make migrate                                  # alembic upgrade head

``target_metadata`` is ``common.database.base.Base.metadata``. To make a
service's tables visible to autogenerate, import its ORM model module under the
"future model imports" marker below. In Phase 1 no service has ORM models yet,
so the metadata is intentionally empty.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

# --- Future model imports ---------------------------------------------------
import common.adapters.database.models.user  # noqa: F401
from common.database.base import Base
from common.database.engine import build_engine
from housekeeper.settings import settings

# Import each service's ORM model module here so autogenerate sees its tables,
# e.g. `import patients.adapters.database.models  # noqa: F401`.
# ---------------------------------------------------------------------------

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _run_migrations(connection: Connection) -> None:
    """Configure the migration context against a live connection and run it."""

    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode, emitting SQL to the script output."""

    context.configure(
        url=settings.postgres_uri,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode against the async engine."""

    engine = build_engine(settings.postgres_uri)
    async with engine.connect() as connection:
        await connection.run_sync(_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
