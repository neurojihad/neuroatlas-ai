import abc
from collections.abc import AsyncIterator

from common.core.entities.events import Event


class EventBus(abc.ABC):
    """Port for publishing and consuming domain events on Kafka streams."""

    @abc.abstractmethod
    async def send_to_bus(self, stream: str, events: list[Event]) -> None:
        """Publish events to the named stream (Kafka topic)."""

    @abc.abstractmethod
    def get_messages(self) -> AsyncIterator[Event]:
        """Poll the consumer assignment and yield decoded events."""

    @abc.abstractmethod
    async def commit(self, event: Event) -> None:
        """Acknowledge that an event was processed."""

    @abc.abstractmethod
    async def move_ptr_to_commited(self) -> None:
        """Seek the consumer to the last committed offset."""
