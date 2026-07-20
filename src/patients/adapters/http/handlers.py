from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from common.adapters.http.auth_dependencies import require_clinician
from common.application.logging import logger
from common.core.entities.user import UserInfo
from common.adapters.http.schemas import ListResponseSchema, ResponseSchema
from patients.adapters.http import dependencies
from patients.adapters.http.schemas import (
    AssessmentSchema,
    PatientSchema,
    RecordAssessmentPayload,
    RegisterPatientPayload,
)
from patients.domain import commands, queries
from patients.domain.ports.uow import PatientsUnitOfWork

router_v1 = APIRouter(prefix="/api/v1", tags=["patients"])


@router_v1.post(
    "/patients",
    response_model=ResponseSchema[str],
    status_code=status.HTTP_201_CREATED,
)
async def register_patient(
    payload: RegisterPatientPayload,
    uow: Annotated[PatientsUnitOfWork, Depends(dependencies.unit_of_work)],
    user: Annotated[UserInfo, Depends(require_clinician)],
) -> ResponseSchema[str]:
    """Register a new de-identified patient."""
    ctx = commands.RegisterPatient.Context(**payload.model_dump(), user_id=user.user_id)
    result = await commands.RegisterPatient(uow=uow, ctx=ctx).execute()
    return ResponseSchema[str](data=result.data)


@router_v1.get("/patients", response_model=ListResponseSchema[PatientSchema])
async def list_patients(
    uow: Annotated[PatientsUnitOfWork, Depends(dependencies.unit_of_work)],
    user: Annotated[UserInfo, Depends(require_clinician)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListResponseSchema[PatientSchema]:
    """List patients with offset pagination."""
    patients = await queries.list_patients(limit=limit, offset=offset, uow=uow)
    await logger.ainfo("Patients listed.", user_id=user.user_id, count=len(patients))
    return ListResponseSchema[PatientSchema](data=[PatientSchema(**asdict(p)) for p in patients])


@router_v1.get("/patients/{patient_id}", response_model=ResponseSchema[PatientSchema])
async def get_patient(
    uow: Annotated[PatientsUnitOfWork, Depends(dependencies.unit_of_work)],
    user: Annotated[UserInfo, Depends(require_clinician)],
    patient_id: str = Path(..., description="Surrogate patient id, e.g. pat_..."),
) -> ResponseSchema[PatientSchema]:
    """Fetch a single patient by id."""
    patient = await queries.get_patient(patient_id, uow=uow)
    await logger.ainfo("Patient fetched.", user_id=user.user_id, patient_id=patient_id)
    return ResponseSchema[PatientSchema](data=PatientSchema(**asdict(patient)))


@router_v1.post(
    "/patients/{patient_id}/assessments",
    response_model=ResponseSchema[str],
    status_code=status.HTTP_201_CREATED,
)
async def record_assessment(
    payload: RecordAssessmentPayload,
    uow: Annotated[PatientsUnitOfWork, Depends(dependencies.unit_of_work)],
    user: Annotated[UserInfo, Depends(require_clinician)],
    patient_id: str = Path(..., description="Surrogate patient id, e.g. pat_..."),
) -> ResponseSchema[str]:
    """Record a clinical assessment (GMFCS, MACS, Ashworth, ROM, note)."""
    ctx = commands.RecordAssessment.Context(
        patient_id=patient_id,
        user_id=user.user_id,
        **payload.model_dump(),
    )
    result = await commands.RecordAssessment(uow=uow, ctx=ctx).execute()
    return ResponseSchema[str](data=result.data)


@router_v1.get(
    "/patients/{patient_id}/assessments",
    response_model=ListResponseSchema[AssessmentSchema],
)
async def list_assessments(
    uow: Annotated[PatientsUnitOfWork, Depends(dependencies.unit_of_work)],
    user: Annotated[UserInfo, Depends(require_clinician)],
    patient_id: str = Path(..., description="Surrogate patient id, e.g. pat_..."),
) -> ListResponseSchema[AssessmentSchema]:
    """List all assessments recorded for a patient."""
    items = await queries.list_patient_assessments(patient_id, uow=uow)
    await logger.ainfo("Assessments listed.", user_id=user.user_id, patient_id=patient_id, count=len(items))
    return ListResponseSchema[AssessmentSchema](data=[AssessmentSchema(**asdict(a)) for a in items])
