import pytest

from common.core.exceptions import ContextValidationError
from ml.adapters.predictor.baseline import BaselineOutcomePredictor
from ml.domain import queries
from ml.domain.entities import OutcomeTarget, PatientFeatures


def _predictor() -> BaselineOutcomePredictor:
    return BaselineOutcomePredictor(model_version="test-0.0.0")


def _features(**overrides) -> PatientFeatures:
    base = dict(age_years=6, gmfcs=2, macs=2, ashworth_mean=1.0, rom_mean=110, therapy_hours_per_week=5)
    base.update(overrides)
    return PatientFeatures(**base)


def test_prediction_returns_probability_and_attributions():
    result = queries.predict_outcome(OutcomeTarget.GMFCS_IMPROVEMENT, _features(), _predictor())
    assert 0.0 <= result.probability <= 1.0
    assert result.attributions
    assert result.model_version == "test-0.0.0"


def test_lower_gmfcs_predicts_higher_improvement():
    mild = queries.predict_outcome(OutcomeTarget.GMFCS_IMPROVEMENT, _features(gmfcs=1), _predictor())
    severe = queries.predict_outcome(OutcomeTarget.GMFCS_IMPROVEMENT, _features(gmfcs=5), _predictor())
    assert mild.probability > severe.probability


def test_attributions_are_sorted_by_magnitude():
    result = queries.predict_outcome(OutcomeTarget.GMFCS_IMPROVEMENT, _features(), _predictor())
    magnitudes = [abs(a.contribution) for a in result.attributions]
    assert magnitudes == sorted(magnitudes, reverse=True)


def test_invalid_gmfcs_is_rejected():
    with pytest.raises(ContextValidationError):
        queries.predict_outcome(OutcomeTarget.GMFCS_IMPROVEMENT, _features(gmfcs=7), _predictor())
