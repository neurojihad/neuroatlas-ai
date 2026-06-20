from pydantic import BaseModel


class DatabaseHealthSchema(BaseModel):
    """Database health response model."""

    database: str
    active_connections: int
    max_connections: int
    size_bytes: int
    size_pretty: str


class LongRunningQuerySchema(BaseModel):
    """Long-running query response model."""

    pid: int
    duration_seconds: float
    state: str
    query: str
    application_name: str | None = None
    wait_event_type: str | None = None


class MaintenanceResultSchema(BaseModel):
    """Maintenance operation response model."""

    operation: str
    status: str
    detail: str | None = None
