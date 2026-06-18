from dataclasses import dataclass, field
from enum import StrEnum


class OutcomeTarget(StrEnum):
    """Supported prediction targets."""

    GMFCS_IMPROVEMENT = "gmfcs_improvement"  # probability of improving >=1 GMFCS level
    GOAL_ATTAINMENT = "goal_attainment"  # probability of reaching rehab goal


@dataclass
class PatientFeatures:
    """Model input features derived from clinical assessments.

    Kept deliberately small for the scaffold; extend as the feature schema is
    finalized against a real dataset.
    """

    age_years: float
    gmfcs: int
    macs: int
    ashworth_mean: float
    rom_mean: float
    therapy_hours_per_week: float = 0.0


@dataclass
class FeatureAttribution:
    """A single feature's contribution to the prediction (SHAP-style)."""

    feature: str
    value: float
    contribution: float  # signed contribution toward the predicted probability


@dataclass
class PredictionResult:
    """Model output paired with its explanation, for clinician trust."""

    target: OutcomeTarget
    probability: float
    label: bool
    model_version: str
    attributions: list[FeatureAttribution] = field(default_factory=list)
    baseline: float = 0.0  # expected value (model's average output)
