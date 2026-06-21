import datetime

from common.core.entities.events import Event, EventKind, EventStream


def test_event_as_dict_serializes_datetime():
    created_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    event = Event(
        kind=EventKind.PredictionRequested,
        source="gateway",
        aggregate_id="req-1",
        stream=EventStream.PredictionRequests,
        created_at=created_at,
        payload={"target": "gmfcs_improvement"},
    )
    data = event.as_dict()
    assert data["kind"] == EventKind.PredictionRequested
    assert data["stream"] == EventStream.PredictionRequests
    assert data["created_at"] == created_at.isoformat()


def test_event_stream_values_match_architecture_topics():
    assert EventStream.PredictionRequests == "prediction-requested"
    assert EventStream.PredictionEvents == "prediction-completed"
    assert len(EventStream.all_streams()) == 8
