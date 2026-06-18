from common.core.exceptions import ContextValidationError
from ml.domain.entities import OutcomeTarget, PatientFeatures, PredictionResult
from ml.domain.ports.predictor import OutcomePredictor


def _validate_features(features: PatientFeatures) -> None:
    """Guard against clinically impossible inputs."""
    if not (0 <= features.age_years <= 25):
        raise ContextValidationError("age_years out of pediatric range.", field_name="age_years")
    if features.gmfcs not in range(1, 6):
        raise ContextValidationError("gmfcs must be in [1, 5].", field_name="gmfcs")
    if features.macs not in range(1, 6):
        raise ContextValidationError("macs must be in [1, 5].", field_name="macs")
    if not (0 <= features.ashworth_mean <= 4):
        raise ContextValidationError("ashworth_mean must be in [0, 4].", field_name="ashworth_mean")


def predict_outcome(
    target: OutcomeTarget,
    features: PatientFeatures,
    predictor: OutcomePredictor,
) -> PredictionResult:
    """Validate input and delegate to the model.

    Read-side use case (no persistence): mirrors the paymentgate `queries`
    module but the "repository" here is the model port.
    """
    _validate_features(features)
    return predictor.predict(target=target, features=features)
