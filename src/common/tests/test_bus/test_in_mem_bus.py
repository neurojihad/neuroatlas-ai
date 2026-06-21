import pytest

from common.adapters.bus.in_mem import InMemEventBus
from common.core.entities.events import Event, EventKind, EventStream


@pytest.fixture(autouse=True)
def _reset_bus():
    InMemEventBus.reset()
    yield
    InMemEventBus.reset()


@pytest.mark.asyncio
async def test_in_mem_bus_dispatches_to_subscribed_handler():
    received: list[str] = []

    async def handler(event: Event) -> None:
        received.append(event.event_id)

    bus = InMemEventBus.instance()
    bus.subscribe(EventStream.PredictionRequests, handler)

    event = Event(
        kind=EventKind.PredictionRequested,
        source="gateway",
        aggregate_id="req-1",
        stream=EventStream.PredictionRequests,
    )
    await bus.send_to_bus(EventStream.PredictionRequests, [event])

    assert received == [event.event_id]


@pytest.mark.asyncio
async def test_in_mem_bus_does_not_dispatch_to_other_streams():
    received: list[str] = []

    async def handler(event: Event) -> None:
        received.append(event.event_id)

    bus = InMemEventBus.instance()
    bus.subscribe(EventStream.PredictionEvents, handler)

    event = Event(
        kind=EventKind.PredictionRequested,
        source="gateway",
        aggregate_id="req-1",
        stream=EventStream.PredictionRequests,
    )
    await bus.send_to_bus(EventStream.PredictionRequests, [event])

    assert received == []
