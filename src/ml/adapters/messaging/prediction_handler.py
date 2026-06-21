from dataclasses import asdict

from common.application.logging import logger
from common.application.settings import Settings
from common.core.entities.events import Event, EventKind, EventStream
from common.core.ports.bus import EventBus
from ml.domain import queries
from ml.domain.entities import OutcomeTarget, PatientFeatures
from ml.domain.ports.predictor import OutcomePredictor


async def handle_prediction_event(
    event: Event,
    *,
    predictor: OutcomePredictor,
    event_bus: EventBus,
    settings: Settings,
) -> None:
    """Consume PredictionRequested events and publish PredictionCompleted."""
    if event.kind != EventKind.PredictionRequested:
        return

    payload = event.payload
    target = OutcomeTarget(payload["target"])
    features = PatientFeatures(**payload["features"])
    request_id = payload.get("request_id")

    result = queries.predict_outcome(target=target, features=features, predictor=predictor)

    completed = Event(
        kind=EventKind.PredictionCompleted,
        source=settings.service_name,
        aggregate_id=event.aggregate_id,
        stream=EventStream.PredictionEvents,
        payload={
            "request_id": request_id,
            "target": result.target.value,
            "probability": result.probability,
            "label": result.label,
            "model_version": result.model_version,
            "baseline": result.baseline,
            "attributions": [asdict(a) for a in result.attributions],
        },
        meta=dict(event.meta),
    )
    await event_bus.send_to_bus(EventStream.PredictionEvents, [completed])
    await logger.ainfo(
        "Prediction completed.",
        request_id=request_id,
        aggregate_id=event.aggregate_id,
        target=result.target.value,
    )
