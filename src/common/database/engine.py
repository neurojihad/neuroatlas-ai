from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    """Create an async SQLAlchemy engine for the given database URL.

    Args:
        database_url: Async-driver URL, e.g. ``postgresql+asyncpg://...``.
        echo: When True, SQLAlchemy logs every emitted statement.

    Returns:
        A configured async engine. The engine connects lazily, so building it
        never requires a live database.
    """
    return create_async_engine(database_url, echo=echo, pool_pre_ping=True)


def build_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an ``async_sessionmaker`` bound to the given engine.

    Args:
        engine: The async engine the sessions are bound to.

    Returns:
        A session factory that yields ``AsyncSession`` instances.
    """
    return async_sessionmaker(bind=engine, expire_on_commit=False)
