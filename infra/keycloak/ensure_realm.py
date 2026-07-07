#!/usr/bin/env python3
"""Idempotent Keycloak bootstrap: ensure neuroatlas realm clients/roles from import JSON.

Fixes stale ``keycloak_data`` volumes where ``--import-realm`` ran before ``neuroatlas-ui``
existed (Keycloak only auto-imports on first empty database).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

REALM_NAME = "neuroatlas"
IMPORT_PATH = Path(__file__).resolve().parent / "import" / "neuroatlas-realm.json"
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080").rstrip("/")
ADMIN_USER = os.getenv("KEYCLOAK_ADMIN", "admin")
ADMIN_PASS = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")


def load_realm() -> dict[str, Any]:
    return json.loads(IMPORT_PATH.read_text(encoding="utf-8"))


def wait_for_keycloak(client: httpx.Client) -> None:
    for attempt in range(60):
        try:
            response = client.get(f"{KEYCLOAK_URL}/realms/master")
            if response.status_code == 200:
                return
        except httpx.RequestError:
            pass
        if attempt == 0:
            print(f"Waiting for Keycloak at {KEYCLOAK_URL}...")
        time.sleep(2)
    raise RuntimeError(f"Keycloak not reachable at {KEYCLOAK_URL}")


def admin_token(client: httpx.Client) -> str:
    response = client.post(
        f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": ADMIN_USER,
            "password": ADMIN_PASS,
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"Keycloak admin login failed: {response.status_code} {response.text}")
    token = response.json().get("access_token")
    if not isinstance(token, str):
        raise RuntimeError("Keycloak admin login response missing access_token.")
    return token


def ensure_realm(client: httpx.Client, headers: dict[str, str], realm_doc: dict[str, Any]) -> None:
    response = client.get(f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}", headers=headers)
    if response.status_code == 404:
        payload = {key: value for key, value in realm_doc.items() if key not in ("clients", "roles")}
        create = client.post(f"{KEYCLOAK_URL}/admin/realms", headers=headers, json=payload)
        if create.status_code not in (201, 409):
            raise RuntimeError(f"Could not create realm {REALM_NAME}: {create.status_code} {create.text}")
        print(f"Created realm {REALM_NAME}")
    elif response.status_code != 200:
        raise RuntimeError(f"Could not read realm {REALM_NAME}: {response.status_code} {response.text}")


def ensure_roles(client: httpx.Client, headers: dict[str, str], roles: list[dict[str, Any]]) -> None:
    existing_resp = client.get(f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/roles", headers=headers)
    existing_resp.raise_for_status()
    existing = {role["name"] for role in existing_resp.json()}
    for role in roles:
        if role["name"] in existing:
            continue
        create = client.post(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/roles",
            headers=headers,
            json=role,
        )
        if create.status_code not in (201, 409):
            raise RuntimeError(f"Could not create role {role['name']}: {create.status_code} {create.text}")
        print(f"Created role {role['name']}")


def find_client(client: httpx.Client, headers: dict[str, str], client_id: str) -> bool:
    response = client.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/clients",
        headers=headers,
        params={"clientId": client_id},
    )
    response.raise_for_status()
    return bool(response.json())


def ensure_clients(client: httpx.Client, headers: dict[str, str], clients: list[dict[str, Any]]) -> None:
    for client_def in clients:
        client_id = client_def["clientId"]
        if find_client(client, headers, client_id):
            print(f"Client exists: {client_id}")
            continue
        create = client.post(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/clients",
            headers=headers,
            json=client_def,
        )
        if create.status_code not in (201, 409):
            raise RuntimeError(f"Could not create client {client_id}: {create.status_code} {create.text}")
        print(f"Created client: {client_id}")


def main() -> int:
    realm_doc = load_realm()
    with httpx.Client(timeout=30.0) as client:
        wait_for_keycloak(client)
        headers = {"Authorization": f"Bearer {admin_token(client)}"}
        ensure_realm(client, headers, realm_doc)
        ensure_roles(client, headers, realm_doc["roles"]["realm"])
        ensure_clients(client, headers, realm_doc["clients"])
    print("Keycloak realm ensure complete.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Keycloak realm ensure failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
