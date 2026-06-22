import pytest

from common.adapters.bus.in_mem import InMemEventBus
from patients.adapters.database.in_mem import reset_store


@pytest.fixture(autouse=True)
def _clean_patients_store():
    """Reset the in-memory patients store before each test."""
    reset_store()
    yield
    reset_store()


@pytest.fixture(autouse=True)
def _reset_event_bus():
    """Reset the in-memory event bus before each test."""
    InMemEventBus.reset()
    yield
    InMemEventBus.reset()
