from collections import defaultdict
from collections.abc import AsyncIterator, Awaitable, Callable

from common.application.logging import logger
from common.core.entities.events import Event, EventKind
from common.core.ports.bus import EventBus

EventHandler = Callable[[Event], Awaitable[None]]


class InMemEventBus(EventBus):
    """In-process bus for tests and local runs without Kafka."""

    _instance: "InMemEventBus | None" = None

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    @classmethod
    def instance(cls) -> "InMemEventBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def subscribe(self, stream: str, handler: EventHandler) -> None:
        self._handlers[stream].append(handler)

    async def send_to_bus(self, stream: str, events: list[Event]) -> None:
        handlers = list(self._handlers.get(stream, []))
        for event in events:
            for handler in handlers:
                try:
                    await handler(event)
                except Exception:
                    await logger.aexception(
                        "In-memory event handler failed.",
                        stream=stream,
                        event_id=event.event_id,
                        kind=str(event.kind),
                    )

    async def get_messages(self) -> AsyncIterator[Event]:
        if False:
            yield Event(kind=EventKind.PredictionRequested, source="", aggregate_id="")

    async def commit(self, event: Event) -> None:
        return None

    async def move_ptr_to_commited(self) -> None:
        return None

    async def start(self) -> None:
        await logger.ainfo("In-memory event bus started.")

    async def stop(self) -> None:
        await logger.ainfo("In-memory event bus stopped.")
