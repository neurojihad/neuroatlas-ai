import pytest

from common.adapters.bus.in_mem import InMemEventBus
from common.application.settings import Settings
from common.core.entities.events import Event, EventKind, EventStream
from ml.adapters.messaging.prediction_handler import handle_prediction_event
from ml.adapters.predictor.baseline import BaselineOutcomePredictor
from ml.domain.entities import OutcomeTarget


@pytest.fixture(autouse=True)
def _reset_bus():
    InMemEventBus.reset()
    yield
    InMemEventBus.reset()


@pytest.mark.asyncio
async def test_prediction_handler_publishes_completed_event():
    completed: list[dict] = []

    async def capture_completed(event: Event) -> None:
        completed.append(event.payload)

    bus = InMemEventBus.instance()
    bus.subscribe(EventStream.PredictionEvents, capture_completed)
    predictor = BaselineOutcomePredictor(model_version="test-0.0.0")
    settings = Settings(service_name="ml")

    request = Event(
        kind=EventKind.PredictionRequested,
        source="gateway",
        aggregate_id="req-1",
        stream=EventStream.PredictionRequests,
        payload={
            "request_id": "req-1",
            "target": OutcomeTarget.GMFCS_IMPROVEMENT.value,
            "features": {
                "age_years": 6,
                "gmfcs": 2,
                "macs": 2,
                "ashworth_mean": 1,
                "rom_mean": 110,
                "therapy_hours_per_week": 5,
            },
        },
    )

    await handle_prediction_event(
        request,
        predictor=predictor,
        event_bus=bus,
        settings=settings,
    )

    assert len(completed) == 1
    assert completed[0]["request_id"] == "req-1"
    assert completed[0]["target"] == OutcomeTarget.GMFCS_IMPROVEMENT.value
    assert 0.0 <= completed[0]["probability"] <= 1.0
    assert completed[0]["model_version"] == "test-0.0.0"
    assert completed[0]["attributions"]


@pytest.mark.asyncio
async def test_prediction_handler_skips_invalid_payload():
    completed: list[dict] = []

    async def capture_completed(event: Event) -> None:
        completed.append(event.payload)

    bus = InMemEventBus.instance()
    bus.subscribe(EventStream.PredictionEvents, capture_completed)
    predictor = BaselineOutcomePredictor(model_version="test-0.0.0")
    settings = Settings(service_name="ml")

    request = Event(
        kind=EventKind.PredictionRequested,
        source="gateway",
        aggregate_id="req-bad",
        stream=EventStream.PredictionRequests,
        payload={"target": OutcomeTarget.GMFCS_IMPROVEMENT.value},
    )

    await handle_prediction_event(
        request,
        predictor=predictor,
        event_bus=bus,
        settings=settings,
    )

    assert completed == []


@pytest.mark.asyncio
async def test_prediction_handler_ignores_unexpected_kind():
    completed: list[dict] = []

    async def capture_completed(event: Event) -> None:
        completed.append(event.payload)

    bus = InMemEventBus.instance()
    bus.subscribe(EventStream.PredictionEvents, capture_completed)
    predictor = BaselineOutcomePredictor(model_version="test-0.0.0")
    settings = Settings(service_name="ml")

    request = Event(
        kind=EventKind.PredictionCompleted,
        source="gateway",
        aggregate_id="req-1",
        stream=EventStream.PredictionRequests,
        payload={},
    )

    await handle_prediction_event(
        request,
        predictor=predictor,
        event_bus=bus,
        settings=settings,
    )

    assert completed == []
