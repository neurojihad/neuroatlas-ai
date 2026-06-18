import abc

from common.core.ports.uow import UnitOfWork
from patients.domain.ports.repositories import AssessmentsRepository, PatientsRepository


class PatientsUnitOfWork(UnitOfWork):
    """Transactional boundary exposing the patient-domain repositories.

    The concrete type comes from `adapters/database`; the domain depends only
    on this interface.
    """

    patients: PatientsRepository
    assessments: AssessmentsRepository

    @abc.abstractmethod
    def copy(self) -> "PatientsUnitOfWork":
        """Return a fresh unit of work sharing the same backing store."""
        raise NotImplementedError
