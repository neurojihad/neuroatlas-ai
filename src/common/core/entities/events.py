import datetime
import enum
from dataclasses import asdict, dataclass, field
from typing import Any

from ulid import ULID


class EventStream(enum.StrEnum):
    """Kafka topic names (event streams). Values match docs/ARCHITECTURE.md."""

    ArticleImportRequests = "article-import-requested"
    ArticleImportEvents = "article-imported"
    EmbeddingsRequests = "embeddings-requested"
    EmbeddingsEvents = "embeddings-generated"
    SearchRequests = "search-requested"
    SearchEvents = "search-completed"
    PredictionRequests = "prediction-requested"
    PredictionEvents = "prediction-completed"

    @classmethod
    def all_streams(cls) -> list["EventStream"]:
        return list(cls)


class EventKind(enum.StrEnum):
    """Logical event types carried inside Event.kind."""

    ArticleImportRequested = "ArticleImportRequested"
    ArticleImported = "ArticleImported"
    EmbeddingsRequested = "EmbeddingsRequested"
    EmbeddingsGenerated = "EmbeddingsGenerated"
    SearchRequested = "SearchRequested"
    SearchCompleted = "SearchCompleted"
    PredictionRequested = "PredictionRequested"
    PredictionCompleted = "PredictionCompleted"


@dataclass
class Event:
    """Domain event published to and consumed from the bus."""

    kind: EventKind
    source: str
    aggregate_id: str
    stream: EventStream | str | None = None
    event_id: str = field(default_factory=lambda: str(ULID()), kw_only=True)
    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC), kw_only=True)
    payload: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key, value in data.items():
            if isinstance(value, datetime.datetime):
                data[key] = value.isoformat()
        return data
