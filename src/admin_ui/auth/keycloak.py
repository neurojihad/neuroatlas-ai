"""Keycloak OIDC token exchange and refresh for the admin_ui BFF."""

from __future__ import annotations

from typing import Any

import httpx

from admin_ui.settings import AdminUiSettings
from common.core.exceptions import AuthException


class KeycloakOidcClient:
    """Exchange authorization codes and refresh tokens with Keycloak."""

    def __init__(self, settings: AdminUiSettings, http_client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http = http_client
        self._token_url = (
            f"{settings.keycloak_url.rstrip('/')}/realms/{settings.keycloak_realm}/protocol/openid-connect/token"
        )
        self._logout_url = (
            f"{settings.keycloak_url.rstrip('/')}/realms/{settings.keycloak_realm}/protocol/openid-connect/logout"
        )

    @property
    def logout_url(self) -> str:
        return self._logout_url

    async def exchange_code(
        self,
        *,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> dict[str, Any]:
        data = {
            "grant_type": "authorization_code",
            "client_id": self._settings.keycloak_client_id,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }
        if self._settings.keycloak_client_secret:
            data["client_secret"] = self._settings.keycloak_client_secret
        return await self._post_token(data)

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        data = {
            "grant_type": "refresh_token",
            "client_id": self._settings.keycloak_client_id,
            "refresh_token": refresh_token,
        }
        if self._settings.keycloak_client_secret:
            data["client_secret"] = self._settings.keycloak_client_secret
        return await self._post_token(data)

    async def _post_token(self, data: dict[str, str]) -> dict[str, Any]:
        try:
            response = await self._http.post(
                self._token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except httpx.HTTPError as exc:
            raise AuthException("Keycloak token request failed.", str(exc)) from exc
        if response.status_code != 200:
            raise AuthException(
                "Keycloak token request rejected.",
                response.text,
            )
        body: dict[str, Any] = response.json()
        if "access_token" not in body:
            raise AuthException("Keycloak response missing access_token.")
        return body
