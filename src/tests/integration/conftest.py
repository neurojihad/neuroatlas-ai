"""Fixtures for live-stack integration smoke tests."""

from __future__ import annotations

import os

import pytest

from tests.integration.smoke_helpers import SmokeConfig


@pytest.fixture
def smoke_config() -> SmokeConfig:
    return SmokeConfig.from_env()


@pytest.fixture
def smoke_enabled() -> None:
    if os.getenv("SMOKE_INTEGRATION") != "1":
        pytest.skip("Set SMOKE_INTEGRATION=1 to run live smoke tests.")


@pytest.fixture
def smoke_credentials(smoke_config: SmokeConfig) -> SmokeConfig:
    if not smoke_config.username or not smoke_config.password:
        pytest.skip("Set SMOKE_USERNAME and SMOKE_PASSWORD for live smoke tests.")
    if not smoke_config.auth_enabled:
        pytest.skip("Set AUTH_ENABLED=true in infra/.env for live smoke tests.")
    return smoke_config
