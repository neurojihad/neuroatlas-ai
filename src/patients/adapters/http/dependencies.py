from fastapi import Request

from patients.domain.ports.uow import PatientsUnitOfWork


async def unit_of_work(request: Request) -> PatientsUnitOfWork:
    """Provide a unit of work built by the configured factory."""
    return request.app.state.uow_factory()
