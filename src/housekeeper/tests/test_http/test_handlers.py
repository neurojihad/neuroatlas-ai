from fastapi.testclient import TestClient

from housekeeper.adapters.database.fake import FakeDatabaseMonitor
from housekeeper.adapters.http import dependencies
from housekeeper.domain.entities import LongRunningQuery
from housekeeper.main import app


def _client() -> TestClient:
    """Build a TestClient with the monitor dependency overridden by a fake.

    The client is created without entering its lifespan context, so no real
    database engine is constructed; handlers use the overridden fake monitor.
    """

    monitor = FakeDatabaseMonitor(
        queries=[LongRunningQuery(pid=7, duration_seconds=9.0, state="active", query="SELECT pg_sleep(10)")]
    )
    app.dependency_overrides[dependencies.database_monitor] = lambda: monitor
    return TestClient(app)


def test_health_endpoint():
    client = _client()
    resp = client.get("/api/v1/db/health")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["data"]["database"] == "neuroatlas"


def test_long_running_queries_endpoint():
    client = _client()
    resp = client.get("/api/v1/db/long-running-queries", params={"threshold_seconds": 5})
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["data"][0]["pid"] == 7


def test_maintenance_endpoint():
    client = _client()
    resp = client.post("/api/v1/db/maintenance")
    app.dependency_overrides.clear()
    assert resp.json()["data"]["status"] == "ok"
