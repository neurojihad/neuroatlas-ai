"""Plain test doubles for admin_ui HTTP tests (no unittest.mock)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
import jwt

from common.core.entities.user import UserInfo
from common.core.exceptions import AuthException
from common.core.ports.auth import AuthAdapter

DEFAULT_ACCESS_TOKEN = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.fake-signature"


def expired_access_token() -> str:
    """JWT with exp in the past (for refresh-path tests)."""
    return jwt.encode({"sub": "test", "exp": 1}, "secret", algorithm="HS256")


@dataclass
class FakeOidcClient:
    """Records OIDC token exchange/refresh calls and returns configured token payloads."""

    tokens: dict[str, Any] = field(
        default_factory=lambda: {
            "access_token": DEFAULT_ACCESS_TOKEN,
            "refresh_token": "refresh-token-value",
        }
    )
    exchange_calls: list[dict[str, str]] = field(default_factory=list)
    refresh_calls: list[str] = field(default_factory=list)

    async def exchange_code(self, *, code: str, redirect_uri: str, code_verifier: str) -> dict[str, Any]:
        self.exchange_calls.append(
            {"code": code, "redirect_uri": redirect_uri, "code_verifier": code_verifier},
        )
        return self.tokens

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        self.refresh_calls.append(refresh_token)
        return self.tokens

    @property
    def logout_url(self) -> str:
        return "http://localhost:8080/realms/neuroatlas/protocol/openid-connect/logout"


@dataclass
class FakeHttpClient:
    """Captures the last proxied upstream request and returns a fixed httpx response."""

    response: httpx.Response = field(
        default_factory=lambda: httpx.Response(
            status_code=200,
            content=b'{"data":[]}',
            headers={"content-type": "application/json"},
        )
    )
    last_request: dict[str, Any] | None = None

    async def request(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        content: bytes | None = None,
    ) -> httpx.Response:
        self.last_request = {
            "method": method,
            "url": url,
            "headers": headers or {},
            "content": content,
        }
        return self.response

    async def aclose(self) -> None:
        return None


@dataclass
class FakeAuthManager(AuthAdapter):
    """Returns a fixed user for every bearer token."""

    user: UserInfo = field(
        default_factory=lambda: UserInfo(
            user_id="usr_dev_local",
            email="dev@local",
            roles=["clinician", "admin"],
        ),
    )

    async def get_user(self, token: str) -> UserInfo:
        return self.user


@dataclass
class ExpiringAuthManager(AuthAdapter):
    """Fails once with AuthException, then returns the configured user."""

    user: UserInfo
    calls: int = 0

    async def get_user(self, token: str) -> UserInfo:
        self.calls += 1
        if self.calls == 1:
            raise AuthException("expired")
        return self.user
