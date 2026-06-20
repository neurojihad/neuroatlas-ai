from housekeeper.domain.entities import (
    DatabaseHealth,
    LongRunningQuery,
    MaintenanceResult,
)
from housekeeper.domain.ports.monitoring import DatabaseMonitor


async def get_database_health(monitor: DatabaseMonitor) -> DatabaseHealth:
    """Return a snapshot of database health."""

    return await monitor.health()


async def list_long_running_queries(
    min_duration_seconds: float,
    monitor: DatabaseMonitor,
) -> list[LongRunningQuery]:
    """Return queries running longer than the given threshold."""

    return await monitor.list_long_running_queries(min_duration_seconds)


async def run_maintenance(monitor: DatabaseMonitor) -> MaintenanceResult:
    """Trigger a safe maintenance operation."""

    return await monitor.run_maintenance()
