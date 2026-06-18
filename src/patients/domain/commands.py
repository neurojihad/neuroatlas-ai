import datetime
from dataclasses import dataclass, field

from ulid import ULID

from common.application.logging import logger
from common.core.commands import Command, CommandResult
from common.core.exceptions import ContextValidationError
from patients.domain.entities import Assessment, AssessmentType, Patient
from patients.domain.ports.uow import PatientsUnitOfWork

# Valid ranges per ordinal assessment scale.
_SCALE_RANGES: dict[AssessmentType, tuple[float, float]] = {
    AssessmentType.GMFCS: (1, 5),
    AssessmentType.MACS: (1, 5),
    AssessmentType.ASHWORTH: (0, 4),
}


class RegisterPatient(Command):
    """Create a new de-identified patient record."""

    @dataclass(frozen=True)
    class Context(Command.Context):
        """Input for patient registration."""

        date_of_birth_year: int
        sex: str | None = None
        diagnosis_code: str | None = None

        def validate_context(self) -> None:
            """Validate the registration payload."""
            current_year = datetime.datetime.now(datetime.UTC).year
            if not (current_year - 25 <= self.date_of_birth_year <= current_year):
                raise ContextValidationError(
                    "Birth year is out of the supported pediatric range.",
                    field_name="date_of_birth_year",
                )

    def __init__(self, uow: PatientsUnitOfWork, ctx: "RegisterPatient.Context") -> None:
        super().__init__(uow, ctx)
        self.ctx: RegisterPatient.Context

    async def execute(self) -> CommandResult[str]:
        """Persist the patient and return its surrogate id."""
        patient = Patient(
            id=f"pat_{str(ULID()).lower()}",
            date_of_birth_year=self.ctx.date_of_birth_year,
            sex=self.ctx.sex,
            diagnosis_code=self.ctx.diagnosis_code,
        )
        async with self.uow:
            await self.uow.patients.create(patient)
        await logger.ainfo("Patient registered.", patient_id=patient.id)
        return CommandResult(data=patient.id)


class RecordAssessment(Command):
    """Record a single clinical assessment for a patient."""

    @dataclass(frozen=True)
    class Context(Command.Context):
        """Input for recording an assessment."""

        patient_id: str
        type: AssessmentType
        value: float | str
        body_site: str | None = None
        meta: dict = field(default_factory=dict)

        def validate_context(self) -> None:
            """Validate the assessment payload against scale ranges."""
            if not self.patient_id.startswith("pat_"):
                raise ContextValidationError("Invalid patient id.", field_name="patient_id")

            if self.type in _SCALE_RANGES:
                low, high = _SCALE_RANGES[self.type]
                if not isinstance(self.value, (int, float)) or not (low <= float(self.value) <= high):
                    raise ContextValidationError(
                        f"{self.type.value.upper()} must be a number in [{low}, {high}].",
                        field_name="value",
                    )
            elif self.type is AssessmentType.CLINICAL_NOTE and not str(self.value).strip():
                raise ContextValidationError("Clinical note cannot be empty.", field_name="value")

    def __init__(self, uow: PatientsUnitOfWork, ctx: "RecordAssessment.Context") -> None:
        super().__init__(uow, ctx)
        self.ctx: RecordAssessment.Context

    async def execute(self) -> CommandResult[str]:
        """Persist the assessment and return its id."""
        assessment = Assessment(
            id=f"asm_{str(ULID()).lower()}",
            patient_id=self.ctx.patient_id,
            type=self.ctx.type,
            value=self.ctx.value,
            recorded_at=datetime.datetime.now(datetime.UTC),
            body_site=self.ctx.body_site,
            meta=self.ctx.meta,
        )
        async with self.uow:
            if not await self.uow.patients.find_by_id(self.ctx.patient_id):
                raise ContextValidationError("Unknown patient.", field_name="patient_id")
            await self.uow.assessments.create(assessment)
        await logger.ainfo("Assessment recorded.", assessment_id=assessment.id, type=assessment.type)
        return CommandResult(data=assessment.id)
