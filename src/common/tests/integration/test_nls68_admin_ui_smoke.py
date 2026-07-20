"""NLS-68 / NLS-ADMIN-08: E2E smoke — admin_ui session → patients API + JIT user row."""

from __future__ import annotations

import httpx
import pytest

from common.utils.identifiers import prefixed_id
from common.tests.integration.smoke_helpers import (
    SmokeConfig,
    fetch_user_row,
    keycloak_sub_from_token,
    obtain_keycloak_access_token,
    session_cookies_from_token,
    wait_for_health,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_ui_guard_lists_patients_with_session_cookies(
    smoke_enabled: None,
    smoke_credentials: SmokeConfig,
) -> None:
    """Verify the admin_ui session flow proxies to patients and JIT-provisions a user.

    Authenticates against Keycloak, exchanges the token for admin_ui session cookies,
    then asserts ``/api/v1/auth/me`` and the guarded patients listing both succeed and
    that a matching ``users`` row was just-in-time created.

    Args:
        smoke_enabled: Fixture gating the test on ``SMOKE_INTEGRATION``.
        smoke_credentials: Live-stack endpoints and credentials for the run.
    """

    config = smoke_credentials

    async with httpx.AsyncClient(timeout=30.0) as client:
        await wait_for_health(client, config.admin_ui_url, label="admin_ui")
        await wait_for_health(client, config.patients_url, label="patients")

        access_token = await obtain_keycloak_access_token(client, config)
        cookies = session_cookies_from_token(config, access_token)

        me_response = await client.get(f"{config.admin_ui_url}/api/v1/auth/me", cookies=cookies)
        assert me_response.status_code == 200, me_response.text
        me_body = me_response.json()["data"]
        assert me_body["email"]

        patients_response = await client.get(
            f"{config.admin_ui_url}/guard/api/v1/patients",
            cookies=cookies,
        )
        assert patients_response.status_code == 200, patients_response.text
        patients_body = patients_response.json()
        assert "data" in patients_body

        keycloak_sub = keycloak_sub_from_token(access_token)
        user_row = await fetch_user_row(config, keycloak_sub)
        assert user_row is not None, "Expected JIT upsert to create a users row."
        assert user_row["id"] == prefixed_id("user", keycloak_sub)
        assert user_row["keycloak_sub"] == keycloak_sub
