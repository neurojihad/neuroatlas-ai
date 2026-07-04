"""Validate Keycloak realm import includes neuroatlas-ui browser client (NLS-ADMIN-02)."""

import json
from typing import Any, cast

import pytest

from common.tests.paths import repo_root

REALM_PATH = repo_root() / "infra" / "keycloak" / "import" / "neuroatlas-realm.json"


@pytest.fixture(scope="module")
def realm() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(REALM_PATH.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def ui_client(realm: dict[str, Any]) -> dict[str, Any]:
    clients = {client["clientId"]: client for client in realm["clients"]}
    assert "neuroatlas-ui" in clients, "neuroatlas-ui client missing from realm import"
    return cast(dict[str, Any], clients["neuroatlas-ui"])


def test_realm_has_neuroatlas_roles(realm: dict[str, Any]) -> None:
    role_names = {role["name"] for role in realm["roles"]["realm"]}
    assert {"admin", "clinician", "researcher"}.issubset(role_names)


def test_neuroatlas_ui_is_public_pkce_client(ui_client: dict[str, Any]) -> None:
    assert ui_client["publicClient"] is True
    assert ui_client["standardFlowEnabled"] is True
    assert ui_client["directAccessGrantsEnabled"] is False
    assert ui_client["implicitFlowEnabled"] is False
    assert ui_client["attributes"]["pkce.code.challenge.method"] == "S256"


def test_neuroatlas_ui_redirect_uris(ui_client: dict[str, Any]) -> None:
    redirect_uris = set(ui_client["redirectUris"])
    assert "http://localhost:8000/api/v1/token" in redirect_uris
    assert "http://127.0.0.1:8000/api/v1/token" in redirect_uris
    assert "http://localhost:3000/*" in redirect_uris


def test_neuroatlas_ui_web_origins(ui_client: dict[str, Any]) -> None:
    web_origins = set(ui_client["webOrigins"])
    assert {"http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:3000"}.issubset(web_origins)


def test_neuroatlas_ui_audience_mapper(ui_client: dict[str, Any]) -> None:
    mappers = ui_client.get("protocolMappers", [])
    audience_mappers = [
        mapper
        for mapper in mappers
        if mapper.get("protocolMapper") == "oidc-audience-mapper"
        and mapper.get("config", {}).get("included.client.audience") == "neuroatlas-api"
    ]
    assert audience_mappers, "neuroatlas-ui must map aud to neuroatlas-api for backend validation"
