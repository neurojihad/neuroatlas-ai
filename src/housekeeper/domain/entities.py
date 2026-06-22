from dataclasses import dataclass


@dataclass
class LongRunningQuery:
    """A query currently running longer than a configured threshold."""

    pid: int
    duration_seconds: float
    state: str
    query: str
    application_name: str | None = None
    wait_event_type: str | None = None


@dataclass
class DatabaseHealth:
    """A point-in-time snapshot of database health metrics."""

    database: str
    active_connections: int
    max_connections: int
    size_bytes: int
    size_pretty: str


@dataclass
class MaintenanceResult:
    """Outcome of a maintenance operation."""

    operation: str
    status: str
    detail: str | None = None
