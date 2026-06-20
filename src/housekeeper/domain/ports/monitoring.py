import abc

from housekeeper.domain.entities import (
    DatabaseHealth,
    LongRunningQuery,
    MaintenanceResult,
)


class DatabaseMonitor(abc.ABC):
    """Interface for observing and maintaining the database.

    Implementations live in ``adapters/database`` (a Postgres adapter backed by
    an async session now, a fake for tests). The domain depends only on this
    port.
    """

    @abc.abstractmethod
    async def list_long_running_queries(self, min_duration_seconds: float) -> list[LongRunningQuery]:
        """Return queries running longer than ``min_duration_seconds``."""

        raise NotImplementedError

    @abc.abstractmethod
    async def health(self) -> DatabaseHealth:
        """Return a snapshot of current database health metrics."""

        raise NotImplementedError

    @abc.abstractmethod
    async def run_maintenance(self) -> MaintenanceResult:
        """Run a safe maintenance operation and return its result."""

        raise NotImplementedError
