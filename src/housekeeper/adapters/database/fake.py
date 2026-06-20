from housekeeper.domain.entities import (
    DatabaseHealth,
    LongRunningQuery,
    MaintenanceResult,
)
from housekeeper.domain.ports.monitoring import DatabaseMonitor


class FakeDatabaseMonitor(DatabaseMonitor):
    """In-memory database monitor for tests; needs no real Postgres."""

    def __init__(
        self,
        *,
        queries: list[LongRunningQuery] | None = None,
        health: DatabaseHealth | None = None,
    ) -> None:
        """Seed canned long-running queries and a health snapshot."""

        self._queries = queries or []
        self._health = health or DatabaseHealth(
            database="neuroatlas",
            active_connections=3,
            max_connections=100,
            size_bytes=10_485_760,
            size_pretty="10 MB",
        )
        self.maintenance_calls = 0

    async def list_long_running_queries(self, min_duration_seconds: float) -> list[LongRunningQuery]:
        """Return seeded queries at or above the threshold."""

        return [q for q in self._queries if q.duration_seconds >= min_duration_seconds]

    async def health(self) -> DatabaseHealth:
        """Return the seeded health snapshot."""

        return self._health

    async def run_maintenance(self) -> MaintenanceResult:
        """Record the call and return a successful result."""

        self.maintenance_calls += 1
        return MaintenanceResult(operation="ANALYZE", status="ok")
