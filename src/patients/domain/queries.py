from common.core.exceptions import NotFound
from patients.domain.entities import Assessment, Patient
from patients.domain.ports.uow import PatientsUnitOfWork


async def get_patient(patient_id: str, uow: PatientsUnitOfWork) -> Patient:
    """Return a patient by id or raise NotFound."""
    async with uow:
        patient = await uow.patients.find_by_id(patient_id)
        if not patient:
            raise NotFound(f"Patient {patient_id} not found.")
        return patient


async def list_patients(limit: int, offset: int, uow: PatientsUnitOfWork) -> list[Patient]:
    """Return a page of patients."""
    async with uow:
        return await uow.patients.list_all(limit=limit, offset=offset)


async def list_patient_assessments(patient_id: str, uow: PatientsUnitOfWork) -> list[Assessment]:
    """Return all assessments for a patient (validates the patient exists)."""
    async with uow:
        if not await uow.patients.find_by_id(patient_id):
            raise NotFound(f"Patient {patient_id} not found.")
        return await uow.assessments.list_for_patient(patient_id)
