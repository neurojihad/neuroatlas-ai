from patients.domain.entities import Assessment, Patient
from patients.domain.ports.repositories import AssessmentsRepository, PatientsRepository
from patients.domain.ports.uow import PatientsUnitOfWork

# Process-wide stores so the in-memory adapter survives across requests.
_PATIENTS: dict[str, Patient] = {}
_ASSESSMENTS: dict[str, Assessment] = {}


class InMemPatientsRepository(PatientsRepository):
    """In-memory patients repository for local dev and tests."""

    async def create(self, patient: Patient) -> None:
        """Persist a new patient."""
        _PATIENTS[patient.id] = patient

    async def find_by_id(self, patient_id: str) -> Patient | None:
        """Return a patient by id, or None."""
        return _PATIENTS.get(patient_id)

    async def list_all(self, limit: int, offset: int) -> list[Patient]:
        """Return a page of patients ordered by creation time."""
        ordered = sorted(_PATIENTS.values(), key=lambda p: p.created_at, reverse=True)
        return ordered[offset : offset + limit]


class InMemAssessmentsRepository(AssessmentsRepository):
    """In-memory assessments repository for local dev and tests."""

    async def create(self, assessment: Assessment) -> None:
        """Persist a new assessment."""
        _ASSESSMENTS[assessment.id] = assessment

    async def list_for_patient(self, patient_id: str) -> list[Assessment]:
        """Return all assessments for a patient, most recent first."""
        items = [a for a in _ASSESSMENTS.values() if a.patient_id == patient_id]
        return sorted(items, key=lambda a: a.recorded_at, reverse=True)


class InMemPatientsUnitOfWork(PatientsUnitOfWork):
    """In-memory unit of work. Commit/rollback are no-ops over shared dicts."""

    def __init__(self) -> None:
        self.patients = InMemPatientsRepository()
        self.assessments = InMemAssessmentsRepository()

    def copy(self) -> "InMemPatientsUnitOfWork":
        """Return a new unit of work over the same backing store."""
        return InMemPatientsUnitOfWork()

    async def commit(self) -> None:
        """No-op: the in-memory store mutates eagerly."""

    async def rollback(self) -> None:
        """No-op: the in-memory store has no transaction to undo."""


def reset_store() -> None:
    """Clear the in-memory store (used by tests)."""
    _PATIENTS.clear()
    _ASSESSMENTS.clear()
