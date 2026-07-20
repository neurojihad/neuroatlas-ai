from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends

from common.adapters.http.schemas import ResponseSchema
from ml.adapters.http import dependencies
from ml.adapters.http.schemas import PredictionSchema, PredictPayload
from ml.domain import queries
from ml.domain.entities import PatientFeatures
from ml.domain.ports.predictor import OutcomePredictor

router_v1 = APIRouter(prefix="/api/v1", tags=["ml"])


@router_v1.post("/predict", response_model=ResponseSchema[PredictionSchema])
async def predict(
    payload: PredictPayload,
    predictor: Annotated[OutcomePredictor, Depends(dependencies.predictor)],
) -> ResponseSchema[PredictionSchema]:
    """Predict a rehabilitation outcome with feature attributions.

    Every prediction returns SHAP-style attributions and the model baseline so
    the result is explainable, never a black box.
    """
    features = PatientFeatures(**payload.features.model_dump())
    result = queries.predict_outcome(target=payload.target, features=features, predictor=predictor)
    return ResponseSchema[PredictionSchema](data=PredictionSchema(**asdict(result)))
