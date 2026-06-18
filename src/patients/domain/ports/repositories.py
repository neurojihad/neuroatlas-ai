import abc

from patients.domain.entities import Assessment, Patient


class PatientsRepository(abc.ABC):
    """Persistence interface for patient records."""

    @abc.abstractmethod
    async def create(self, patient: Patient) -> None:
        """Persist a new patient."""
        raise NotImplementedError

    @abc.abstractmethod
    async def find_by_id(self, patient_id: str) -> Patient | None:
        """Return a patient by surrogate id, or None."""
        raise NotImplementedError

    @abc.abstractmethod
    async def list_all(self, limit: int, offset: int) -> list[Patient]:
        """Return a page of patients."""
        raise NotImplementedError


class AssessmentsRepository(abc.ABC):
    """Persistence interface for clinical assessments."""

    @abc.abstractmethod
    async def create(self, assessment: Assessment) -> None:
        """Persist a new assessment."""
        raise NotImplementedError

    @abc.abstractmethod
    async def list_for_patient(self, patient_id: str) -> list[Assessment]:
        """Return all assessments for a patient, most recent first."""
        raise NotImplementedError
