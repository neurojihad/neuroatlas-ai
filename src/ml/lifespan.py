import asyncio
import contextlib
from contextlib import asynccontextmanager
from functools import partial

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import FastAPI

from common.adapters.bus.in_mem import InMemEventBus
from common.adapters.bus.kafka import (
    KafkaEventBus,
    get_consumer,
    get_producer,
    run_consumer_loop,
)
from common.application.logging import logger
from common.core.entities.events import EventStream
from common.core.ports.bus import EventBus
from ml.adapters.messaging.prediction_handler import handle_prediction_event
from ml.adapters.predictor.baseline import BaselineOutcomePredictor
from ml.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle for the ML service.

    Loads the predictor into app state. When Kafka is enabled, consumes
    prediction-requested events and publishes prediction-completed responses.
    """
    await logger.ainfo("Service starting.", service_name="ml", model_version=settings.model_version)
    predictor = BaselineOutcomePredictor(model_version=settings.model_version)
    app.state.predictor = predictor

    consumer_task: asyncio.Task[None] | None = None
    producer: AIOKafkaProducer | None = None
    consumer: AIOKafkaConsumer | None = None
    in_mem_bus: InMemEventBus | None = None
    event_bus: EventBus

    handler = partial(
        handle_prediction_event,
        predictor=predictor,
        settings=settings,
    )

    if settings.kafka_enabled:
        producer = get_producer(settings)
        consumer = get_consumer(
            settings,
            EventStream.PredictionRequests,
            settings.kafka_consumer_group,
        )
        await producer.start()
        await consumer.start()
        publish_bus = KafkaEventBus(producer=producer)
        consume_bus = KafkaEventBus(consumer=consumer)
        event_bus = publish_bus
        handler = partial(handler, event_bus=publish_bus)
        consumer_task = asyncio.create_task(
            run_consumer_loop(consume_bus, handler),
            name="prediction-requests-consumer",
        )
    else:
        in_mem_bus = InMemEventBus.instance()
        event_bus = in_mem_bus
        await in_mem_bus.start()
        handler = partial(handler, event_bus=in_mem_bus)
        in_mem_bus.subscribe(EventStream.PredictionRequests, handler)

    app.state.event_bus = event_bus

    yield

    if consumer_task is not None:
        consumer_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await consumer_task
    if consumer is not None:
        await consumer.stop()
    if producer is not None:
        await producer.stop()
    if in_mem_bus is not None:
        await in_mem_bus.stop()
    await logger.ainfo("Service stopped.", service_name="ml")
