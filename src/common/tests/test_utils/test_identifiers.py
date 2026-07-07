import pytest

from common.adapters.auth.base import extract_realm_roles
from common.adapters.auth.keycloak import NullAuthAdapter, build_auth_adapter
from common.application.settings import Settings
from common.utils.identifiers import PrefixesEnum, generate_id_for, prefixed_id


def test_prefixed_id_uses_type_prefix():
    assert prefixed_id("user", "abc-123") == "usr_abc-123"


def test_generate_id_for_includes_prefix():
    patient_id = generate_id_for("patient")
    assert patient_id.startswith("pat_")


def test_prefixes_enum_with_delimiter():
    assert PrefixesEnum.user.with_delimiter == "usr_"


def test_extract_realm_roles_filters_keycloak_defaults():
    claims = {
        "realm_access": {
            "roles": ["clinician", "offline_access", "uma_authorization", "admin"],
        }
    }
    assert extract_realm_roles(claims) == ["clinician", "admin"]


@pytest.mark.asyncio
async def test_null_auth_adapter_returns_dev_user():
    adapter = NullAuthAdapter()
    user = await adapter.get_user("ignored")
    assert user.user_id == "usr_dev_local"
    assert "clinician" in user.roles


def test_build_auth_adapter_uses_null_when_disabled():
    settings = Settings(auth_enabled=False)
    adapter = build_auth_adapter(settings)
    assert isinstance(adapter, NullAuthAdapter)
