import datetime

from pydantic import BaseModel

from patients.domain.entities import AssessmentType


class RegisterPatientPayload(BaseModel):
    """Request body for registering a patient."""

    date_of_birth_year: int
    sex: str | None = None
    diagnosis_code: str | None = None


class PatientSchema(BaseModel):
    """Patient response model."""

    id: str
    date_of_birth_year: int
    sex: str | None = None
    diagnosis_code: str | None = None
    created_at: datetime.datetime


class RecordAssessmentPayload(BaseModel):
    """Request body for recording an assessment."""

    type: AssessmentType
    value: float | str
    body_site: str | None = None
    meta: dict = {}


class AssessmentSchema(BaseModel):
    """Assessment response model."""

    id: str
    patient_id: str
    type: AssessmentType
    value: float | str
    recorded_at: datetime.datetime
    body_site: str | None = None
    meta: dict = {}
