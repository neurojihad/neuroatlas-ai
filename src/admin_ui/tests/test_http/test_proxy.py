"""Tests for guard path → upstream URL resolution."""

import pytest

from admin_ui.adapters.http.proxy import backend_path, resolve_upstream_url
from admin_ui.settings import AdminUiSettings
from common.core.exceptions import NotFound


@pytest.fixture
def settings() -> AdminUiSettings:
    return AdminUiSettings(
        patients_route="localhost:8001",
        ml_route="localhost:8002",
        housekeeper_route="localhost:8003",
    )


def test_backend_path_patients_strips_guard_prefix():
    assert backend_path("/guard/api/v1/patients", "/guard/api/v1/patients/pat_abc") == "/api/v1/patients/pat_abc"


def test_backend_path_ml_rewrites_to_api_v1():
    assert backend_path("/guard/api/v1/ml", "/guard/api/v1/ml/predict") == "/api/v1/predict"


def test_backend_path_housekeeper_rewrites_to_api_v1():
    assert backend_path("/guard/api/v1/housekeeper", "/guard/api/v1/housekeeper/db/health") == "/api/v1/db/health"


def test_resolve_upstream_url_patients(settings: AdminUiSettings):
    url = resolve_upstream_url(settings, "/guard/api/v1/patients", "limit=10")
    assert url == "http://localhost:8001/api/v1/patients?limit=10"


def test_resolve_upstream_url_ml(settings: AdminUiSettings):
    url = resolve_upstream_url(settings, "/guard/api/v1/ml/predict", "")
    assert url == "http://localhost:8002/api/v1/predict"


def test_resolve_upstream_url_unknown_path(settings: AdminUiSettings):
    with pytest.raises(NotFound):
        resolve_upstream_url(settings, "/guard/api/v1/unknown", "")
