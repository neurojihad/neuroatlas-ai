from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from housekeeper.domain.entities import (
    DatabaseHealth,
    LongRunningQuery,
    MaintenanceResult,
)
from housekeeper.domain.ports.monitoring import DatabaseMonitor

_LONG_RUNNING_SQL = text(
    """
    SELECT
        pid,
        EXTRACT(EPOCH FROM (now() - query_start)) AS duration_seconds,
        state,
        query,
        application_name,
        wait_event_type
    FROM pg_stat_activity
    WHERE state IS NOT NULL
      AND state <> 'idle'
      AND query_start IS NOT NULL
      AND now() - query_start >= make_interval(secs => :min_duration)
    ORDER BY duration_seconds DESC
    """
)

_HEALTH_SQL = text(
    """
    SELECT
        current_database() AS database,
        numbackends AS active_connections,
        current_setting('max_connections')::int AS max_connections,
        pg_database_size(current_database()) AS size_bytes,
        pg_size_pretty(pg_database_size(current_database())) AS size_pretty
    FROM pg_stat_database
    WHERE datname = current_database()
    """
)

# Static, parameter-free maintenance statement. No user input is interpolated.
_MAINTENANCE_SQL = text("ANALYZE")


class PgDatabaseMonitor(DatabaseMonitor):
    """Postgres-backed database monitor using an async SQLAlchemy session."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the session factory; a session is opened per operation."""

        self._session_factory = session_factory

    async def list_long_running_queries(self, min_duration_seconds: float) -> list[LongRunningQuery]:
        """Return queries running longer than ``min_duration_seconds``."""

        async with self._session_factory() as session:
            result = await session.execute(_LONG_RUNNING_SQL, {"min_duration": min_duration_seconds})
            rows = result.mappings().all()
        return [
            LongRunningQuery(
                pid=row["pid"],
                duration_seconds=float(row["duration_seconds"]),
                state=row["state"],
                query=row["query"],
                application_name=row["application_name"],
                wait_event_type=row["wait_event_type"],
            )
            for row in rows
        ]

    async def health(self) -> DatabaseHealth:
        """Return a snapshot of current database health metrics."""

        async with self._session_factory() as session:
            result = await session.execute(_HEALTH_SQL)
            row = result.mappings().one()
        return DatabaseHealth(
            database=row["database"],
            active_connections=row["active_connections"],
            max_connections=row["max_connections"],
            size_bytes=row["size_bytes"],
            size_pretty=row["size_pretty"],
        )

    async def run_maintenance(self) -> MaintenanceResult:
        """Run ANALYZE to refresh planner statistics."""

        async with self._session_factory() as session:
            await session.execute(_MAINTENANCE_SQL)
            await session.commit()
        return MaintenanceResult(operation="ANALYZE", status="ok")
