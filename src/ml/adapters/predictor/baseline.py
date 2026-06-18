import math
from dataclasses import asdict

from ml.domain.entities import (
    FeatureAttribution,
    OutcomeTarget,
    PatientFeatures,
    PredictionResult,
)
from ml.domain.ports.predictor import OutcomePredictor

# Transparent linear weights standing in for a trained model. These are NOT
# clinically validated — they exist so the pipeline (input -> probability ->
# attributions) is exercisable end to end. Replace with a loaded model.
_INTERCEPT = 0.0
_WEIGHTS: dict[str, float] = {
    "age_years": -0.05,  # older children improve a bit less on this target
    "gmfcs": -0.45,  # higher (worse) GMFCS -> lower improvement probability
    "macs": -0.25,
    "ashworth_mean": -0.30,
    "rom_mean": 0.010,
    "therapy_hours_per_week": 0.12,
}
# Reference (mean) feature values used as the SHAP-style baseline.
_REFERENCE: dict[str, float] = {
    "age_years": 7.0,
    "gmfcs": 3.0,
    "macs": 3.0,
    "ashworth_mean": 2.0,
    "rom_mean": 90.0,
    "therapy_hours_per_week": 3.0,
}


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class BaselineOutcomePredictor(OutcomePredictor):
    """Transparent logistic baseline with exact additive attributions.

    Because the model is linear in logit space, each feature's contribution is
    `weight * (value - reference)`, which is the exact SHAP value for a linear
    model. This keeps the explanation contract identical to the future
    XGBoost + SHAP implementation.
    """

    def __init__(self, model_version: str) -> None:
        self.model_version = model_version

    def predict(self, target: OutcomeTarget, features: PatientFeatures) -> PredictionResult:
        """Compute probability and per-feature attributions."""
        values = asdict(features)

        baseline_logit = _INTERCEPT + sum(_WEIGHTS[f] * _REFERENCE[f] for f in _WEIGHTS)
        logit = _INTERCEPT + sum(_WEIGHTS[f] * values[f] for f in _WEIGHTS)

        attributions = [
            FeatureAttribution(
                feature=f,
                value=float(values[f]),
                contribution=_WEIGHTS[f] * (float(values[f]) - _REFERENCE[f]),
            )
            for f in _WEIGHTS
        ]
        attributions.sort(key=lambda a: abs(a.contribution), reverse=True)

        probability = _sigmoid(logit)
        return PredictionResult(
            target=target,
            probability=round(probability, 4),
            label=probability >= 0.5,
            model_version=self.model_version,
            attributions=attributions,
            baseline=round(_sigmoid(baseline_logit), 4),
        )
