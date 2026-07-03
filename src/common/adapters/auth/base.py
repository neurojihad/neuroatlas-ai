from abc import abstractmethod
from typing import Any

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from common.application.logging import logger
from common.application.settings import Settings
from common.core.exceptions import AuthException


def strip_bearer_prefix(token: str) -> str:
    """Remove a ``Bearer `` prefix when present."""
    prefix = "bearer "
    if token.lower().startswith(prefix):
        return token[len(prefix) :].strip()
    return token.strip()


def extract_realm_roles(claims: dict[str, Any]) -> list[str]:
    """Map Keycloak ``realm_access.roles`` to application role names."""
    realm_access = claims.get("realm_access")
    if not isinstance(realm_access, dict):
        return []
    roles = realm_access.get("roles")
    if not isinstance(roles, list):
        return []
    ignored = frozenset({"offline_access", "uma_authorization"})
    return [role for role in roles if isinstance(role, str) and role not in ignored]


class BaseAuthManager:
    """Shared JWT verification via JWKS."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._jwks_client: PyJWKClient | None = None

    @property
    @abstractmethod
    def jwks_url(self) -> str:
        """JWKS endpoint for the configured identity provider."""

    def _get_jwks_client(self) -> PyJWKClient:
        if self._jwks_client is None:
            self._jwks_client = PyJWKClient(self.jwks_url)
        return self._jwks_client

    async def verify_jwt_token(self, token: str) -> dict[str, Any]:
        """Validate a JWT and return its claims."""
        token = strip_bearer_prefix(token)
        try:
            signing_key = self._get_jwks_client().get_signing_key_from_jwt(token)
            decode_kwargs: dict[str, Any] = {
                "algorithms": ["RS256"],
                "issuer": self._settings.oidc_issuer,
            }
            if self._settings.oidc_audience:
                decode_kwargs["audience"] = self._settings.oidc_audience
            else:
                decode_kwargs["options"] = {"verify_aud": False}
            claims: dict[str, Any] = jwt.decode(token, signing_key.key, **decode_kwargs)
            return claims
        except PyJWTError as exc:
            await logger.aerror("JWT validation failed.", exc_info=exc)
            raise AuthException("Invalid or expired access token.", str(exc)) from exc
