"""HTTP tests for admin_ui guard proxy handlers."""

import pytest
from httpx import ASGITransport, AsyncClient

from admin_ui.auth.session import split_jwt
from admin_ui.main import app
from admin_ui.settings import settings
from admin_ui.tests.fakes import (
    DEFAULT_ACCESS_TOKEN,
    ExpiringAuthManager,
    FakeAuthManager,
    FakeHttpClient,
    FakeOidcClient,
    expired_access_token,
)
from common.core.entities.user import UserInfo

_FAKE_ACCESS = DEFAULT_ACCESS_TOKEN
_PAYLOAD_PART, _SIGNATURE_PART = split_jwt(_FAKE_ACCESS)


@pytest.fixture
def auth_cookies() -> dict[str, str]:
    return {
        settings.access_token_alias: _PAYLOAD_PART,
        settings.signature_token_alias: _SIGNATURE_PART,
    }


@pytest.mark.asyncio
async def test_guard_proxy_forwards_bearer_and_user_headers(auth_cookies: dict[str, str]):
    http_client = FakeHttpClient()

    async with app.router.lifespan_context(app):
        app.state.http_client = http_client
        app.state.auth_manager = FakeAuthManager()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/guard/api/v1/patients",
                cookies=auth_cookies,
                headers={"Correlation-Id": "crr_test123"},
            )

    assert response.status_code == 200
    assert http_client.last_request is not None
    assert http_client.last_request["url"] == "http://localhost:8001/api/v1/patients"
    headers = http_client.last_request["headers"]
    assert headers["Authorization"] == f"Bearer {_FAKE_ACCESS}"
    assert headers["X-User-Id"] == "usr_dev_local"
    assert headers["Correlation-Id"] == "crr_test123"


@pytest.mark.asyncio
async def test_guard_proxy_returns_401_without_session():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/guard/api/v1/patients")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_guard_proxy_returns_404_for_unknown_route(auth_cookies: dict[str, str]):
    async with app.router.lifespan_context(app):
        app.state.auth_manager = FakeAuthManager()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/guard/api/v1/unknown", cookies=auth_cookies)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_guard_proxy_refreshes_expired_session():
    expired_token = expired_access_token()
    payload_part, signature_part = split_jwt(expired_token)
    expired_cookies = {
        settings.access_token_alias: payload_part,
        settings.signature_token_alias: signature_part,
        settings.refresh_token_alias: "old-refresh",
    }
    refreshed_user = UserInfo(user_id="usr_refreshed", email="user@test.com", roles=["clinician"])
    oidc = FakeOidcClient(tokens={"access_token": _FAKE_ACCESS, "refresh_token": "new-refresh"})
    http_client = FakeHttpClient()

    async with app.router.lifespan_context(app):
        app.state.auth_manager = ExpiringAuthManager(user=refreshed_user)
        app.state.oidc_client = oidc
        app.state.http_client = http_client
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/guard/api/v1/patients", cookies=expired_cookies)

    assert response.status_code == 200
    assert oidc.refresh_calls == ["old-refresh"]
    assert settings.access_token_alias in response.cookies
    assert http_client.last_request is not None
    assert http_client.last_request["headers"]["X-User-Id"] == "usr_refreshed"


@pytest.mark.asyncio
async def test_guard_proxy_does_not_refresh_invalid_token(auth_cookies: dict[str, str]):
    oidc = FakeOidcClient()
    http_client = FakeHttpClient()

    async with app.router.lifespan_context(app):
        app.state.auth_manager = ExpiringAuthManager(
            user=UserInfo(user_id="usr_x", email="x@test.com", roles=["clinician"]),
        )
        app.state.oidc_client = oidc
        app.state.http_client = http_client
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/guard/api/v1/patients",
                cookies={**auth_cookies, settings.refresh_token_alias: "old-refresh"},
            )

    assert response.status_code == 401
    assert oidc.refresh_calls == []


@pytest.mark.asyncio
async def test_guard_proxy_ml_path_rewrite(auth_cookies: dict[str, str]):
    http_client = FakeHttpClient()

    async with app.router.lifespan_context(app):
        app.state.http_client = http_client
        app.state.auth_manager = FakeAuthManager()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/guard/api/v1/ml/predict", cookies=auth_cookies, json={})

    assert response.status_code == 200
    assert http_client.last_request is not None
    assert http_client.last_request["url"] == "http://localhost:8002/api/v1/predict"
