import abc

from common.core.entities.user import AuthTokenData, UserInfo


class AuthAdapter(abc.ABC):
    """Port for validating OIDC access tokens and extracting caller identity."""

    @abc.abstractmethod
    async def get_user(self, token: str) -> UserInfo:
        """Return authenticated user info from a bearer token."""

    async def get_claims(self, token: str) -> AuthTokenData:
        """Return decoded token context; default implementation wraps ``get_user``."""
        user_info = await self.get_user(token)
        return AuthTokenData(user_info=user_info)
