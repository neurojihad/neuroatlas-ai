"""Tests for PKCE store and split-JWT cookie helpers."""

import pytest

from admin_ui.auth.session import PkceStore, build_authorize_url, join_jwt, split_jwt


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
