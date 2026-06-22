from typing import cast

from fastapi import Request

from housekeeper.adapters.database.pg_monitor import PgDatabaseMonitor
from housekeeper.domain.ports.monitoring import DatabaseMonitor


async def database_monitor(request: Request) -> DatabaseMonitor:
    """Provide a Postgres-backed database monitor from app state."""

    sessionmaker = request.app.state.sessionmaker
    return cast(DatabaseMonitor, PgDatabaseMonitor(sessionmaker))
