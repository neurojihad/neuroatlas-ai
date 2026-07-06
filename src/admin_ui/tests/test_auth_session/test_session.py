"""Tests for PKCE store and split-JWT cookie helpers."""

import pytest

from admin_ui.auth.session import (
    PkceStore,
    build_authorize_url,
    is_access_token_expired,
    join_jwt,
    sanitize_redirect_path,
    split_jwt,
)
from admin_ui.tests.fakes import DEFAULT_ACCESS_TOKEN, expired_access_token


def test_split_and_join_jwt_roundtrip():
    token = "header.payload.signature"
    payload_part, signature = split_jwt(token)
    assert payload_part == "header.payload"
    assert signature == "signature"
    assert join_jwt(payload_part, signature) == token


def test_split_jwt_rejects_invalid_format():
    with pytest.raises(ValueError, match="Invalid JWT"):
        split_jwt("not-a-jwt")


def test_pkce_store_create_and_pop():
    store = PkceStore(ttl_sec=600)
    challenge = store.create(redirect_after_login="/patients")
    assert challenge.state
    assert challenge.code_challenge
    assert challenge.code_verifier
    stored = store.pop(challenge.state)
    assert stored == (challenge.code_verifier, "/patients")
    assert store.pop(challenge.state) is None


def test_build_authorize_url_includes_pkce_params():
    url = build_authorize_url(
        keycloak_base="http://localhost:8080",
        realm="neuroatlas",
        client_id="neuroatlas-ui",
        redirect_uri="http://localhost:8000/api/v1/token",
        state="test-state",
        code_challenge="test-challenge",
    )
    assert "client_id=neuroatlas-ui" in url
    assert "code_challenge=test-challenge" in url
    assert "code_challenge_method=S256" in url
    assert "state=test-state" in url


def test_sanitize_redirect_path_allows_relative_paths():
    assert sanitize_redirect_path("/patients") == "/patients"
    assert sanitize_redirect_path("/") == "/"


@pytest.mark.parametrize(
    "unsafe",
    ["https://evil.com", "//evil.com/path", "http://evil.com", "javascript:alert(1)"],
)
def test_sanitize_redirect_path_blocks_open_redirects(unsafe: str):
    assert sanitize_redirect_path(unsafe) == "/"


def test_is_access_token_expired_detects_exp_claim():
    assert is_access_token_expired(expired_access_token()) is True
    assert is_access_token_expired(DEFAULT_ACCESS_TOKEN) is False
