from contextlib import asynccontextmanager

from fastapi import FastAPI

from common.adapters.auth.keycloak import build_auth_adapter
from common.adapters.database.user_repository import PostgresUserRepository
from common.application.logging import logger
from common.core.entities.user import UserInfo
from common.database.engine import build_engine, build_sessionmaker
from patients.adapters.database.in_mem import InMemPatientsUnitOfWork
from patients.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle for the patients service."""
    await logger.ainfo("Service starting.", service_name="patients")
    app.state.settings = settings
    app.state.auth_manager = build_auth_adapter(settings)
    app.state.uow_factory = InMemPatientsUnitOfWork

    if settings.auth_enabled and settings.user_upsert_enabled:
        engine = build_engine(settings.postgres_uri)
        session_factory = build_sessionmaker(engine)
        app.state._user_engine = engine

        async def upsert_user(user: UserInfo) -> None:
            async with session_factory() as session:
                repo = PostgresUserRepository(session)
                await repo.upsert_from_user_info(user)

        app.state.upsert_user = upsert_user
    else:
        app.state.upsert_user = None

    yield

    user_engine = getattr(app.state, "_user_engine", None)
    if user_engine is not None:
        await user_engine.dispose()
    await logger.ainfo("Service stopped.", service_name="patients")
