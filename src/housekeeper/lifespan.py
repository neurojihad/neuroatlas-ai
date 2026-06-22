from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from common.application.logging import logger
from common.database.engine import build_engine, build_sessionmaker
from housekeeper.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifecycle for the Housekeeper service.

    Builds the async engine and session factory from settings and stores the
    session factory on ``app.state``. The engine connects lazily, so startup
    never requires a live database (tests run offline). The engine is disposed
    on shutdown.
    """

    await logger.ainfo("Service starting.", service_name=settings.service_name)
    engine = build_engine(settings.postgres_uri)
    app.state.sessionmaker = build_sessionmaker(engine)
    try:
        yield
    finally:
        await engine.dispose()
        await logger.ainfo("Service stopped.", service_name=settings.service_name)
