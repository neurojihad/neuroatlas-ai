import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import orjson
import pytest
from aiokafka.structs import TopicPartition

from common.adapters.bus.kafka import KafkaEventBus, _dispatch_event, run_consumer_loop
from common.core.entities.events import Event, EventKind, EventStream
from common.core.exceptions import BusException
from common.core.ports.bus import EventBus


class _StubEventBus(EventBus):
    def __init__(self, events: list[Event]) -> None:
        self._events = events
        self.committed: list[str] = []

    async def send_to_bus(self, stream: str, events_batch: list[Event]) -> None:
        return None

    def get_messages(self) -> AsyncIterator[Event]:
        async def _once() -> AsyncIterator[Event]:
            for event in self._events:
                yield event

        return _once()

    async def commit(self, event: Event) -> None:
        self.committed.append(event.event_id)

    async def move_ptr_to_commited(self) -> None:
        return None


class _RecordingEventBus(EventBus):
    """Records commit calls for dispatch tests."""

    def __init__(self) -> None:
        self.committed: list[Event] = []

    async def send_to_bus(self, stream: str, events_batch: list[Event]) -> None:
        return None

    def get_messages(self) -> AsyncIterator[Event]:
        async def _once() -> AsyncIterator[Event]:
            for event in []:
                yield event

        return _once()

    async def commit(self, event: Event) -> None:
        self.committed.append(event)

    async def move_ptr_to_commited(self) -> None:
        return None


@dataclass
class _StubKafkaMessage:
    value: bytes
    offset: int


@dataclass
class _StubKafkaProducer:
    send_error: Exception | None = None
    send_calls: list[tuple[str, bytes]] = field(default_factory=list)
    send_keys: list[bytes] = field(default_factory=list)

    async def send_and_wait(self, topic: str, payload: bytes, *, key: bytes) -> None:
        if self.send_error is not None:
            raise self.send_error
        self.send_calls.append((topic, payload))
        self.send_keys.append(key)


@dataclass
class _StubKafkaConsumer:
    messages: dict[TopicPartition, list[_StubKafkaMessage]] = field(default_factory=dict)
    commit_calls: list[dict[TopicPartition, int]] = field(default_factory=list)

    async def seek_to_committed(self) -> None:
        return None

    async def getmany(
        self, timeout_ms: int = 100, max_records: int = 100
    ) -> dict[TopicPartition, list[_StubKafkaMessage]]:
        return self.messages

    async def commit(self, offsets: dict[TopicPartition, int]) -> None:
        self.commit_calls.append(offsets)


def _sample_event(**overrides: Any) -> Event:
    defaults: dict[str, Any] = {
        "kind": EventKind.PredictionRequested,
        "source": "gateway",
        "aggregate_id": "req-1",
        "stream": EventStream.PredictionRequests,
        "payload": {"target": "gmfcs_improvement", "features": {"age_years": 6}},
    }
    defaults.update(overrides)
    return Event(**defaults)


@pytest.mark.asyncio
async def test_send_to_bus_publishes_serialized_event():
    producer = _StubKafkaProducer()
    bus = KafkaEventBus(producer=producer)
    event = _sample_event()

    await bus.send_to_bus(EventStream.PredictionRequests, [event])

    assert len(producer.send_calls) == 1
    topic, payload = producer.send_calls[0]
    assert topic == EventStream.PredictionRequests
    assert producer.send_keys == [b"req-1"]
    decoded = orjson.loads(payload)
    assert decoded["kind"] == EventKind.PredictionRequested
    assert decoded["aggregate_id"] == "req-1"


@pytest.mark.asyncio
async def test_send_to_bus_requires_producer():
    bus = KafkaEventBus(producer=None)
    with pytest.raises(BusException, match="Producer is not configured"):
        await bus.send_to_bus(EventStream.PredictionRequests, [_sample_event()])


@pytest.mark.asyncio
async def test_send_to_bus_wraps_producer_errors():
    producer = _StubKafkaProducer(send_error=RuntimeError("broker down"))
    bus = KafkaEventBus(producer=producer)

    with pytest.raises(BusException, match="Failed to publish events"):
        await bus.send_to_bus(EventStream.PredictionRequests, [_sample_event()])


@pytest.mark.asyncio
async def test_get_messages_decodes_event_and_sets_offsets():
    consumer = _StubKafkaConsumer()
    bus = KafkaEventBus(consumer=consumer)
    partition = TopicPartition(EventStream.PredictionRequests, 0)
    raw_event = _sample_event().as_dict()
    consumer.messages = {partition: [_StubKafkaMessage(value=orjson.dumps(raw_event), offset=4)]}

    events = [event async for event in bus.get_messages()]

    assert len(events) == 1
    assert events[0].kind == EventKind.PredictionRequested
    assert events[0].meta["partition"] == partition
    assert events[0].meta["offset"] == 5


@pytest.mark.asyncio
async def test_get_messages_commits_poison_messages():
    consumer = _StubKafkaConsumer()
    bus = KafkaEventBus(consumer=consumer)
    partition = TopicPartition(EventStream.PredictionRequests, 0)
    consumer.messages = {partition: [_StubKafkaMessage(value=b"{not-json", offset=2)]}

    events = [event async for event in bus.get_messages()]

    assert events == []
    assert consumer.commit_calls == [{partition: 3}]


@pytest.mark.asyncio
async def test_commit_requires_partition_and_offset():
    bus = KafkaEventBus(consumer=_StubKafkaConsumer())
    with pytest.raises(BusException, match="Cannot commit event"):
        await bus.commit(_sample_event())


@pytest.mark.asyncio
async def test_dispatch_event_commits_after_handler_failure():
    event_bus = _RecordingEventBus()
    event = _sample_event()
    event.meta["partition"] = TopicPartition(EventStream.PredictionRequests, 0)
    event.meta["offset"] = 1

    async def failing_handler(_event: Event) -> None:
        raise RuntimeError("handler failed")

    await _dispatch_event(event_bus, failing_handler, event)

    assert event_bus.committed == [event]


@pytest.mark.asyncio
async def test_run_consumer_loop_survives_handler_failures():
    partition = TopicPartition(EventStream.PredictionRequests, 0)
    events = [
        _sample_event(event_id="evt-1", aggregate_id="req-1"),
        _sample_event(event_id="evt-2", aggregate_id="req-2"),
    ]
    for index, event in enumerate(events):
        event.meta["partition"] = partition
        event.meta["offset"] = index + 1

    bus = _StubEventBus(events)
    calls = {"count": 0}

    async def flaky_handler(_event: Event) -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("first event failed")

    task = asyncio.create_task(run_consumer_loop(bus, flaky_handler, poll_interval_sec=60))
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert calls["count"] == 2
    assert bus.committed == ["evt-1", "evt-2"]
