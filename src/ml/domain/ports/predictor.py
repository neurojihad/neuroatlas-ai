import abc

from ml.domain.entities import OutcomeTarget, PatientFeatures, PredictionResult


class OutcomePredictor(abc.ABC):
    """Interface for an outcome-prediction model.

    Implementations live in `adapters/predictor` (baseline heuristic now, a
    trained XGBoost + SHAP model later). The domain depends only on this port.
    """

    @abc.abstractmethod
    def predict(self, target: OutcomeTarget, features: PatientFeatures) -> PredictionResult:
        """Return a probability plus per-feature attributions for one patient."""
        raise NotImplementedError
