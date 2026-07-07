"""Helpers for live-stack admin_ui E2E smoke tests (NLS-68)."""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx
import jwt

from admin_ui.auth.session import split_jwt


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
    postgres_dsn: str
    access_token_cookie: str
    signature_token_cookie: str
    auth_enabled: bool

    @classmethod
    def from_env(cls) -> SmokeConfig:
        postgres_uri = os.getenv(
            "POSTGRES_URI",
            "postgresql+asyncpg://neuroatlas:password@localhost:5432/neuroatlas",
        )
        return cls(
            admin_ui_url=os.getenv("SMOKE_ADMIN_UI_URL", "http://localhost:8000").rstrip("/"),
            patients_url=os.getenv("SMOKE_PATIENTS_URL", "http://localhost:8001").rstrip("/"),
            keycloak_url=os.getenv("KEYCLOAK_URL", "http://localhost:8080").rstrip("/"),
            keycloak_realm=os.getenv("KEYCLOAK_REALM", "neuroatlas"),
            keycloak_client_id=os.getenv("SMOKE_KEYCLOAK_CLIENT_ID", "neuroatlas-api"),
            keycloak_client_secret=os.getenv("KEYCLOAK_CLIENT_SECRET", "dev-neuroatlas-api-secret"),
            username=os.getenv("SMOKE_USERNAME", ""),
            password=os.getenv("SMOKE_PASSWORD", ""),
            postgres_dsn=postgres_uri.replace("postgresql+asyncpg://", "postgresql://", 1),
            access_token_cookie=os.getenv("NEUROATLAS_ACCESS_TOKEN", "NEUROATLAS_ACCESS_TOKEN"),
            signature_token_cookie=os.getenv("NEUROATLAS_TOKEN_SIGN", "NEUROATLAS_TOKEN_SIGN"),
            auth_enabled=os.getenv("AUTH_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
        )


def keycloak_sub_from_token(access_token: str) -> str:
    claims = jwt.decode(access_token, options={"verify_signature": False})
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("Access token missing sub claim.")
    return subject


async def wait_for_health(client: httpx.AsyncClient, url: str, *, label: str) -> None:
    response = await client.get(f"{url}/health")
    if response.status_code != 200:
        raise RuntimeError(f"{label} health check failed: {response.status_code} {response.text}")


async def obtain_keycloak_access_token(client: httpx.AsyncClient, config: SmokeConfig) -> str:
    token_url = (
        f"{config.keycloak_url}/realms/{config.keycloak_realm}/protocol/openid-connect/token"
    )
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
    payload_part, signature_part = split_jwt(access_token)
    return {
        config.access_token_cookie: payload_part,
        config.signature_token_cookie: signature_part,
    }


async def fetch_user_row(config: SmokeConfig, keycloak_sub: str) -> dict[str, str] | None:
    import asyncpg

    conn = await asyncpg.connect(config.postgres_dsn)
    try:
        row = await conn.fetchrow(
            "SELECT id, keycloak_sub, email FROM users WHERE keycloak_sub = $1",
            keycloak_sub,
        )
    finally:
        await conn.close()
    if row is None:
        return None
    return {"id": row["id"], "keycloak_sub": row["keycloak_sub"], "email": row["email"]}
