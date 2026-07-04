import pytest

from common.adapters.auth.base import extract_realm_roles
from common.adapters.auth.keycloak import NullAuthAdapter


def test_extract_realm_roles_empty_when_missing():
    assert extract_realm_roles({}) == []


@pytest.mark.asyncio
async def test_null_auth_adapter_accepts_bearer_prefix():
    adapter = NullAuthAdapter()
    user = await adapter.get_user("Bearer any-token")
    assert user.email == "dev@local"
