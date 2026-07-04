from typing import Any

from common.adapters.auth.base import (
    BaseAuthManager,
    extract_realm_roles,
    strip_bearer_prefix,
)
from common.application.settings import Settings
from common.core.entities.user import AuthTokenData, UserInfo
from common.core.exceptions import AuthException
from common.core.ports.auth import AuthAdapter
from common.utils.identifiers import prefixed_id


def _client_id(claims: dict[str, Any]) -> str | None:
    azp = claims.get("azp")
    if isinstance(azp, str):
        return azp
    aud = claims.get("aud")
    if isinstance(aud, str):
        return aud
    return None


class KeycloakAuthAdapter(BaseAuthManager, AuthAdapter):
    """Validate Keycloak OIDC access tokens via JWKS."""

    @property
    def jwks_url(self) -> str:
        return str(self._settings.oidc_jwks_url)

    async def get_claims(self, token: str) -> AuthTokenData:
        claims = await self.verify_jwt_token(token)
        return AuthTokenData(user_info=self._user_info_from_claims(claims), client_id=_client_id(claims))

    async def get_user(self, token: str) -> UserInfo:
        claims = await self.verify_jwt_token(token)
        return self._user_info_from_claims(claims)

    @staticmethod
    def _user_info_from_claims(claims: dict[str, Any]) -> UserInfo:
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise AuthException("Invalid user identifier in token.")
        email = claims.get("email")
        if not isinstance(email, str) or not email:
            email = claims.get("preferred_username", "")
        if not isinstance(email, str):
            email = ""
        return UserInfo(
            user_id=prefixed_id("user", subject),
            email=email,
            roles=extract_realm_roles(claims),
        )


class NullAuthAdapter(AuthAdapter):
    """Development adapter used when ``AUTH_ENABLED=false``."""

    async def get_user(self, token: str) -> UserInfo:
        _ = strip_bearer_prefix(token)
        return UserInfo(
            user_id="usr_dev_local",
            email="dev@local",
            roles=["clinician", "admin"],
        )


def build_auth_adapter(settings: Settings) -> AuthAdapter:
    """Return the configured auth adapter for the current environment."""
    if settings.auth_enabled:
        return KeycloakAuthAdapter(settings)
    return NullAuthAdapter()
