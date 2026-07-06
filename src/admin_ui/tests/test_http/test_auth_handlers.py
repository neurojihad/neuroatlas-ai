"""HTTP tests for admin_ui OIDC auth handlers."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from admin_ui.auth.session import PkceStore, split_jwt
from admin_ui.main import app
from admin_ui.settings import settings

_FAKE_ACCESS = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.fake-signature"
_PAYLOAD_PART, _SIGNATURE_PART = split_jwt(_FAKE_ACCESS)


@pytest.fixture
def auth_cookies() -> dict[str, str]:
    return {
        settings.access_token_alias: _PAYLOAD_PART,
        settings.signature_token_alias: _SIGNATURE_PART,
    }


@pytest.mark.asyncio
async def test_start_auth_returns_authorize_url():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/auth")
    assert response.status_code == 200
    body = response.json()
    auth_url = body["data"]["auth_url"]
    assert "protocol/openid-connect/auth" in auth_url
    assert "code_challenge=" in auth_url
    assert "code_challenge_method=S256" in auth_url
    assert "client_id=neuroatlas-ui" in auth_url


@pytest.mark.asyncio
async def test_auth_me_returns_401_without_cookies():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_returns_user_with_session_cookies(auth_cookies: dict[str, str]):
    with patch("admin_ui.settings.settings.auth_enabled", False):
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/auth/me", cookies=auth_cookies)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["user_id"] == "usr_dev_local"
    assert data["email"] == "dev@local"
    assert "clinician" in data["roles"]


@pytest.mark.asyncio
async def test_token_callback_exchanges_code_and_sets_cookies():
    async with app.router.lifespan_context(app):
        pkce = PkceStore()
        challenge = pkce.create(redirect_after_login="/patients")
        app.state.pkce_store = pkce
        mock_exchange = AsyncMock(
            return_value={
                "access_token": _FAKE_ACCESS,
                "refresh_token": "refresh-token-value",
            },
        )
        app.state.oidc_client.exchange_code = mock_exchange

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
            response = await client.get(
                "/api/v1/token",
                params={"code": "auth-code", "state": challenge.state},
            )

        assert response.status_code == 302
        assert response.headers["location"] == "/patients"
        assert settings.access_token_alias in response.cookies
        assert settings.signature_token_alias in response.cookies
        assert settings.refresh_token_alias in response.cookies
        mock_exchange.assert_awaited_once()


@pytest.mark.asyncio
async def test_token_callback_rejects_unknown_state():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/token",
                params={"code": "auth-code", "state": "unknown-state"},
            )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_updates_cookies():
    async with app.router.lifespan_context(app):
        mock_refresh = AsyncMock(
            return_value={
                "access_token": _FAKE_ACCESS,
                "refresh_token": "new-refresh",
            },
        )
        app.state.oidc_client.refresh = mock_refresh

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/token/refresh",
                cookies={settings.refresh_token_alias: "old-refresh"},
            )

        assert response.status_code == 200
        assert settings.access_token_alias in response.cookies
        mock_refresh.assert_awaited_once_with("old-refresh")


@pytest.mark.asyncio
async def test_logout_clears_cookies_and_returns_logout_url(auth_cookies: dict[str, str]):
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/logout", cookies=auth_cookies)

    assert response.status_code == 200
    body = response.json()["data"]
    assert "protocol/openid-connect/logout" in body["logout_url"]
