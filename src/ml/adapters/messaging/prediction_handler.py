from dataclasses import asdict

from common.application.logging import logger
from common.application.settings import Settings
from common.core.entities.events import Event, EventKind, EventStream
from common.core.exceptions import ContextValidationError
from common.core.ports.bus import EventBus
from ml.domain import queries
from ml.domain.entities import OutcomeTarget, PatientFeatures
from ml.domain.ports.predictor import OutcomePredictor

_REQUIRED_FEATURE_KEYS = ("age_years", "gmfcs", "macs", "ashworth_mean", "rom_mean")


def _parse_prediction_payload(payload: object) -> tuple[OutcomeTarget, PatientFeatures, str | None]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict.")
    if "target" not in payload:
        raise ValueError("payload is missing 'target'.")
    if "features" not in payload:
        raise ValueError("payload is missing 'features'.")
    features_raw = payload["features"]
    if not isinstance(features_raw, dict):
        raise ValueError("'features' must be a dict.")
    missing = [key for key in _REQUIRED_FEATURE_KEYS if key not in features_raw]
    if missing:
        raise ValueError(f"features missing keys: {', '.join(missing)}.")
    request_id = payload.get("request_id")
    if request_id is not None and not isinstance(request_id, str):
        raise ValueError("'request_id' must be a string.")
    try:
        target = OutcomeTarget(payload["target"])
    except ValueError as exc:
        raise ValueError(f"invalid target: {payload['target']!r}.") from exc
    return target, PatientFeatures(**features_raw), request_id


async def handle_prediction_event(
    event: Event,
    *,
    predictor: OutcomePredictor,
    event_bus: EventBus,
    settings: Settings,
) -> None:
    """Consume PredictionRequested events and publish PredictionCompleted."""
    if event.kind != EventKind.PredictionRequested:
        await logger.awarning(
            "Ignoring unexpected event kind on prediction stream.",
            kind=str(event.kind),
            event_id=event.event_id,
        )
        return

    try:
        target, features, request_id = _parse_prediction_payload(event.payload)
    except ValueError as exc:
        await logger.awarning(
            "Invalid prediction request payload.",
            event_id=event.event_id,
            aggregate_id=event.aggregate_id,
            error=str(exc),
        )
        return

    try:
        result = queries.predict_outcome(target=target, features=features, predictor=predictor)
    except ContextValidationError as exc:
        await logger.awarning(
            "Prediction input rejected.",
            event_id=event.event_id,
            aggregate_id=event.aggregate_id,
            message=exc.message,
            field_name=exc.field_name,
        )
        return

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
