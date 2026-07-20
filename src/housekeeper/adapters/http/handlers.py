from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from common.adapters.http.schemas import ListResponseSchema, ResponseSchema
from housekeeper.adapters.http import dependencies
from housekeeper.adapters.http.schemas import (
    DatabaseHealthSchema,
    LongRunningQuerySchema,
    MaintenanceResultSchema,
)
from housekeeper.domain import queries
from housekeeper.domain.ports.monitoring import DatabaseMonitor

router_v1 = APIRouter(prefix="/api/v1", tags=["housekeeper"])


@router_v1.get("/db/health", response_model=ResponseSchema[DatabaseHealthSchema])
async def database_health(
    monitor: Annotated[DatabaseMonitor, Depends(dependencies.database_monitor)],
) -> ResponseSchema[DatabaseHealthSchema]:
    """Return a snapshot of database health metrics."""

    health = await queries.get_database_health(monitor)
    return ResponseSchema[DatabaseHealthSchema](data=DatabaseHealthSchema(**asdict(health)))


@router_v1.get("/db/long-running-queries", response_model=ListResponseSchema[LongRunningQuerySchema])
async def long_running_queries(
    monitor: Annotated[DatabaseMonitor, Depends(dependencies.database_monitor)],
    threshold_seconds: float = Query(default=5.0, ge=0.0, description="Minimum query duration in seconds."),
) -> ListResponseSchema[LongRunningQuerySchema]:
    """List queries running longer than the given threshold."""

    items = await queries.list_long_running_queries(threshold_seconds, monitor)
    return ListResponseSchema[LongRunningQuerySchema](data=[LongRunningQuerySchema(**asdict(q)) for q in items])


@router_v1.post("/db/maintenance", response_model=ResponseSchema[MaintenanceResultSchema])
async def run_maintenance(
    monitor: Annotated[DatabaseMonitor, Depends(dependencies.database_monitor)],
) -> ResponseSchema[MaintenanceResultSchema]:
    """Run a safe maintenance operation (ANALYZE)."""

    result = await queries.run_maintenance(monitor)
    return ResponseSchema[MaintenanceResultSchema](data=MaintenanceResultSchema(**asdict(result)))
