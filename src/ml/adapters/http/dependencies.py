from typing import cast

from fastapi import Request

from ml.domain.ports.predictor import OutcomePredictor


async def predictor(request: Request) -> OutcomePredictor:
    """Provide the loaded predictor from app state."""
    return cast(OutcomePredictor, request.app.state.predictor)
