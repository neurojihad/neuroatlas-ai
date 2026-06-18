from pydantic import BaseModel

from ml.domain.entities import OutcomeTarget


class FeaturesPayload(BaseModel):
    """Model input features for a single patient."""

    age_years: float
    gmfcs: int
    macs: int
    ashworth_mean: float
    rom_mean: float
    therapy_hours_per_week: float = 0.0


class PredictPayload(BaseModel):
    """Prediction request body."""

    target: OutcomeTarget
    features: FeaturesPayload


class AttributionSchema(BaseModel):
    """Per-feature contribution."""

    feature: str
    value: float
    contribution: float


class PredictionSchema(BaseModel):
    """Prediction response with explanation."""

    target: OutcomeTarget
    probability: float
    label: bool
    model_version: str
    baseline: float
    attributions: list[AttributionSchema]
