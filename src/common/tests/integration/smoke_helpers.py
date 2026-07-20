"""Helpers for live-stack admin_ui E2E smoke tests (NLS-68)."""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx
import jwt
from sqlalchemy import select

from admin_ui.auth.session import split_jwt
from common.adapters.database.models.user import UserORM
from common.database.engine import build_engine, build_sessionmaker


@dataclass(frozen=True)
class SmokeConfig:
    """Runtime endpoints and credentials for smoke tests."""

    admin_ui_url: str
    patients_url: str
    keycloak_url: str
    keycloak_realm: str
    keycloak_client_id: str
    keycloak_client_secret: str
    username: str
    password: str
    postgres_uri: str
    access_token_cookie: str
    signature_token_cookie: str
    auth_enabled: bool

    @classmethod
    def from_env(cls) -> SmokeConfig:
        """Build a config from environment variables with local-stack defaults.

        Returns:
            A ``SmokeConfig`` populated from ``SMOKE_*``/``KEYCLOAK_*``/``POSTGRES_URI``
            environment variables, falling back to local development defaults.
        """

        return cls(
            admin_ui_url=os.getenv("SMOKE_ADMIN_UI_URL", "http://localhost:8000").rstrip("/"),
            patients_url=os.getenv("SMOKE_PATIENTS_URL", "http://localhost:8001").rstrip("/"),
            keycloak_url=os.getenv("KEYCLOAK_URL", "http://localhost:8080").rstrip("/"),
            keycloak_realm=os.getenv("KEYCLOAK_REALM", "neuroatlas"),
            keycloak_client_id=os.getenv("SMOKE_KEYCLOAK_CLIENT_ID", "neuroatlas-api"),
            keycloak_client_secret=os.getenv("KEYCLOAK_CLIENT_SECRET", "dev-neuroatlas-api-secret"),
            username=os.getenv("SMOKE_USERNAME", ""),
            password=os.getenv("SMOKE_PASSWORD", ""),
            postgres_uri=os.getenv(
                "POSTGRES_URI",
                "postgresql+asyncpg://neuroatlas:password@localhost:5432/neuroatlas",
            ),
            access_token_cookie=os.getenv("NEUROATLAS_ACCESS_TOKEN", "NEUROATLAS_ACCESS_TOKEN"),
            signature_token_cookie=os.getenv("NEUROATLAS_TOKEN_SIGN", "NEUROATLAS_TOKEN_SIGN"),
            auth_enabled=os.getenv("AUTH_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
        )


def keycloak_sub_from_token(access_token: str) -> str:
    """Extract the ``sub`` claim from a Keycloak access token.

    The token signature is not verified; only the payload is decoded.

    Args:
        access_token: Encoded JWT access token issued by Keycloak.

    Returns:
        The subject (``sub``) claim identifying the authenticated user.

    Raises:
        ValueError: If the token has no non-empty string ``sub`` claim.
    """

    claims = jwt.decode(access_token, options={"verify_signature": False})
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("Access token missing sub claim.")
    return subject


async def wait_for_health(client: httpx.AsyncClient, url: str, *, label: str) -> None:
    """Assert that a service ``/health`` endpoint returns HTTP 200.

    Args:
        client: Async HTTP client used to issue the request.
        url: Base URL of the service to probe (without the ``/health`` suffix).
        label: Human-readable service name used in the failure message.

    Raises:
        RuntimeError: If the health endpoint responds with a non-200 status.
    """

    response = await client.get(f"{url}/health")
    if response.status_code != 200:
        raise RuntimeError(f"{label} health check failed: {response.status_code} {response.text}")


async def obtain_keycloak_access_token(client: httpx.AsyncClient, config: SmokeConfig) -> str:
    """Obtain a Keycloak access token via the resource owner password grant.

    Args:
        client: Async HTTP client used to call the Keycloak token endpoint.
        config: Smoke configuration providing the realm, client, and user credentials.

    Returns:
        The encoded access token string returned by Keycloak.

    Raises:
        RuntimeError: If the token request fails or the response omits ``access_token``.
    """

    token_url = f"{config.keycloak_url}/realms/{config.keycloak_realm}/protocol/openid-connect/token"
    response = await client.post(
        token_url,
        data={
            "grant_type": "password",
            "client_id": config.keycloak_client_id,
            "client_secret": config.keycloak_client_secret,
            "username": config.username,
            "password": config.password,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if response.status_code != 200:
        raise RuntimeError(f"Keycloak token request failed: {response.status_code} {response.text}")
    body = response.json()
    access_token = body.get("access_token")
    if not isinstance(access_token, str):
        raise RuntimeError("Keycloak response missing access_token.")
    return access_token


def session_cookies_from_token(config: SmokeConfig, access_token: str) -> dict[str, str]:
    """Split an access token into admin_ui session cookies.

    Args:
        config: Smoke configuration providing the cookie names to use.
        access_token: Encoded JWT access token to split into payload and signature.

    Returns:
        Mapping of cookie name to value for the access-token payload and signature parts.
    """

    payload_part, signature_part = split_jwt(access_token)
    return {
        config.access_token_cookie: payload_part,
        config.signature_token_cookie: signature_part,
    }


async def fetch_user_row(config: SmokeConfig, keycloak_sub: str) -> dict[str, str] | None:
    """Fetch the ``users`` row for a Keycloak subject via the project async engine.

    Uses the shared SQLAlchemy engine and ``UserORM`` model (the same building blocks
    the services wire in ``lifespan.py``) rather than a raw driver connection, so the
    smoke test reads the database through the project's own persistence layer.

    Args:
        config: Smoke configuration providing the Postgres connection URL.
        keycloak_sub: Keycloak subject identifier to look up.

    Returns:
        Mapping with ``id``, ``keycloak_sub``, and ``email`` for the matching user,
        or ``None`` if no row exists.
    """

    engine = build_engine(config.postgres_uri)
    try:
        session_factory = build_sessionmaker(engine)
        async with session_factory() as session:
            result = await session.execute(select(UserORM).where(UserORM.keycloak_sub == keycloak_sub))
            user = result.scalar_one_or_none()
    finally:
        await engine.dispose()
    if user is None:
        return None
    return {"id": user.id, "keycloak_sub": user.keycloak_sub, "email": user.email}
