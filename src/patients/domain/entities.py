import datetime
from dataclasses import dataclass, field
from enum import StrEnum


class AssessmentType(StrEnum):
    """Supported clinical assessment instruments."""

    GMFCS = "gmfcs"  # Gross Motor Function Classification System (I-V)
    MACS = "macs"  # Manual Ability Classification System (I-V)
    ASHWORTH = "ashworth"  # Modified Ashworth Scale (0-4) for spasticity
    ROM = "rom"  # Range of Motion (degrees)
    CLINICAL_NOTE = "clinical_note"  # Free-text note (PHI-scrubbed)


@dataclass
class Patient:
    """A de-identified pediatric patient record.

    Only surrogate identifiers are stored; no direct PII ever reaches this layer.
    """

    id: str
    date_of_birth_year: int  # year only, to avoid storing exact DOB
    sex: str | None = None
    diagnosis_code: str | None = None  # e.g. ICD-10 G80.x for cerebral palsy
    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))


@dataclass
class Assessment:
    """A single clinical assessment captured during an encounter."""

    id: str
    patient_id: str
    type: AssessmentType
    value: float | str  # numeric scale/score, or text for clinical notes
    recorded_at: datetime.datetime
    body_site: str | None = None  # for ROM / Ashworth (e.g. "left_knee")
    meta: dict = field(default_factory=dict)
