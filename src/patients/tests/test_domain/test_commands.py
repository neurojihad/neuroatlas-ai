import datetime

import pytest

from common.core.exceptions import ContextValidationError
from patients.adapters.database.in_mem import InMemPatientsUnitOfWork
from patients.domain import commands, queries
from patients.domain.entities import AssessmentType


def _uow() -> InMemPatientsUnitOfWork:
    return InMemPatientsUnitOfWork()


async def test_register_patient_returns_prefixed_id():
    ctx = commands.RegisterPatient.Context(date_of_birth_year=datetime.datetime.now(datetime.UTC).year - 5)
    result = await commands.RegisterPatient(uow=_uow(), ctx=ctx).execute()
    assert result.data.startswith("pat_")


async def test_register_patient_rejects_bad_birth_year():
    ctx = commands.RegisterPatient.Context(date_of_birth_year=1900)
    with pytest.raises(ContextValidationError):
        commands.RegisterPatient(uow=_uow(), ctx=ctx)


async def test_record_assessment_validates_gmfcs_range():
    patient_id = (
        await commands.RegisterPatient(
            uow=_uow(),
            ctx=commands.RegisterPatient.Context(date_of_birth_year=2020),
        ).execute()
    ).data

    ctx = commands.RecordAssessment.Context(patient_id=patient_id, type=AssessmentType.GMFCS, value=9)
    with pytest.raises(ContextValidationError):
        commands.RecordAssessment(uow=_uow(), ctx=ctx)


async def test_record_and_list_assessment_roundtrip():
    uow = _uow()
    patient_id = (
        await commands.RegisterPatient(
            uow=uow,
            ctx=commands.RegisterPatient.Context(date_of_birth_year=2019),
        ).execute()
    ).data

    ctx = commands.RecordAssessment.Context(patient_id=patient_id, type=AssessmentType.GMFCS, value=3)
    await commands.RecordAssessment(uow=uow, ctx=ctx).execute()

    items = await queries.list_patient_assessments(patient_id, uow=uow)
    assert len(items) == 1
    assert items[0].type is AssessmentType.GMFCS
    assert items[0].value == 3
