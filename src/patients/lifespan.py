from contextlib import asynccontextmanager

from fastapi import FastAPI

from common.application.logging import logger
from patients.adapters.database.in_mem import InMemPatientsUnitOfWork


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle for the patients service.

    The scaffold uses an in-memory unit of work so the service runs without a
    database. Swap `InMemPatientsUnitOfWork` for the SQLAlchemy adapter when the
    Postgres schema and migrations land.
    """
    await logger.ainfo("Service starting.", service_name="patients")
    app.state.uow_factory = InMemPatientsUnitOfWork
    yield
    await logger.ainfo("Service stopped.", service_name="patients")
