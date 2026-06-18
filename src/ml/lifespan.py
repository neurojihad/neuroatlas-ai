from contextlib import asynccontextmanager

from fastapi import FastAPI

from common.application.logging import logger
from ml.adapters.predictor.baseline import BaselineOutcomePredictor
from ml.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle for the ML service.

    Loads the predictor into app state. The scaffold ships a transparent
    rule-based baseline; swap it for a trained XGBoost model loaded from the
    model registry without touching the domain or HTTP layers.
    """
    await logger.ainfo("Service starting.", service_name="ml", model_version=settings.model_version)
    app.state.predictor = BaselineOutcomePredictor(model_version=settings.model_version)
    yield
    await logger.ainfo("Service stopped.", service_name="ml")
