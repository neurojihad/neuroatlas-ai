from housekeeper.adapters.database.fake import FakeDatabaseMonitor
from housekeeper.domain import queries
from housekeeper.domain.entities import LongRunningQuery


def _monitor() -> FakeDatabaseMonitor:
    """Build a fake monitor seeded with two queries of differing durations."""

    return FakeDatabaseMonitor(
        queries=[
            LongRunningQuery(pid=1, duration_seconds=2.0, state="active", query="SELECT 1"),
            LongRunningQuery(pid=2, duration_seconds=12.0, state="active", query="SELECT pg_sleep(20)"),
        ]
    )


async def test_health_returns_snapshot():
    health = await queries.get_database_health(_monitor())
    assert health.database == "neuroatlas"
    assert health.max_connections >= health.active_connections


async def test_long_running_queries_filters_by_threshold():
    items = await queries.list_long_running_queries(5.0, _monitor())
    assert [q.pid for q in items] == [2]


async def test_run_maintenance_reports_ok():
    monitor = _monitor()
    result = await queries.run_maintenance(monitor)
    assert result.status == "ok"
    assert monitor.maintenance_calls == 1
