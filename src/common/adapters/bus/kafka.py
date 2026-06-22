import asyncio
import datetime
from typing import AsyncIterator

import orjson
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from common.application.logging import logger
from common.application.settings import Settings
from common.core.entities.events import Event, EventKind, EventStream
from common.core.exceptions import BusException
from common.core.ports.bus import EventBus


def get_producer(settings: Settings) -> AIOKafkaProducer:
    return AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        client_id=settings.kafka_client_id,
    )


def get_consumer(
    settings: Settings,
    stream: EventStream,
    consumer_group_id: str,
) -> AIOKafkaConsumer:
    return AIOKafkaConsumer(
        stream,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=consumer_group_id,
        client_id=f"{settings.kafka_client_id}-consumer",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )


class KafkaEventBus(EventBus):
    """Kafka-backed event bus (paymentgate-style producer/consumer wiring)."""

    def __init__(
        self,
        producer: AIOKafkaProducer | None = None,
        consumer: AIOKafkaConsumer | None = None,
    ) -> None:
        self.producer = producer
        self.consumer = consumer

    async def send_to_bus(self, stream: str, events: list[Event]) -> None:
        if self.producer is None:
            raise BusException("Producer is not configured.")
        try:
            for event in events:
                await self.producer.send_and_wait(
                    stream,
                    orjson.dumps(event.as_dict()),
                    key=event.aggregate_id.encode(),
                )
                await logger.ainfo(
                    "Event published.",
                    stream=stream,
                    kind=event.kind,
                    event_id=event.event_id,
                )
        except Exception as exc:
            raise BusException("Failed to publish events.", str(exc)) from exc

    async def move_ptr_to_commited(self) -> None:
        if self.consumer is None:
            raise BusException("Consumer is not configured.")
        await self.consumer.seek_to_committed()

    async def get_messages(self) -> AsyncIterator[Event]:
        if self.consumer is None:
            raise BusException("Consumer is not configured.")
        try:
            await self.move_ptr_to_commited()
            batch = await self.consumer.getmany(timeout_ms=100, max_records=100)
            for partition, messages in batch.items():
                for message in messages:
                    try:
                        raw_event = orjson.loads(message.value.decode("utf-8"))
                        raw_event["created_at"] = datetime.datetime.fromisoformat(raw_event["created_at"])
                        raw_event["kind"] = EventKind(raw_event["kind"])
                        if raw_event.get("stream") is not None:
                            raw_event["stream"] = EventStream(raw_event["stream"])
                        event = Event(**raw_event)
                        event.meta["partition"] = partition
                        event.meta["offset"] = message.offset + 1
                        yield event
                    except Exception:
                        await logger.aexception("Failed to deserialize bus message.", message=message)
                        await self.consumer.commit({partition: message.offset + 1})
        except Exception as exc:
            raise BusException("Failed to consume events.", str(exc)) from exc

    async def commit(self, event: Event) -> None:
        if self.consumer is None:
            raise BusException("Consumer is not configured.")
        partition = event.meta.get("partition")
        offset = event.meta.get("offset")
        if partition is None or offset is None:
            raise BusException("Cannot commit event without partition/offset in meta.")
        await self.consumer.commit({partition: offset})


async def run_consumer_loop(
    event_bus: EventBus,
    handler,
    *,
    poll_interval_sec: float = 0.1,
) -> None:
    """Poll the bus and dispatch events until cancelled."""
    try:
        while True:
            async for event in event_bus.get_messages():
                await _dispatch_event(event_bus, handler, event)
            await asyncio.sleep(poll_interval_sec)
    except asyncio.CancelledError:
        raise


async def _dispatch_event(event_bus: EventBus, handler, event: Event) -> None:
    try:
        await handler(event)
    except Exception:
        await logger.aexception(
            "Event handler failed.",
            event_id=event.event_id,
            kind=str(event.kind),
            aggregate_id=event.aggregate_id,
        )
    try:
        await event_bus.commit(event)
    except Exception:
        await logger.aexception(
            "Failed to commit event offset.",
            event_id=event.event_id,
            kind=str(event.kind),
        )
