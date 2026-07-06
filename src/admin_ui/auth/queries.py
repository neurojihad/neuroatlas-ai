"""Read-side auth helpers for the admin_ui BFF."""

from common.core.entities.user import UserInfo
from common.core.ports.auth import AuthAdapter


async def get_user_from_access_token(auth_manager: AuthAdapter, access_token: str) -> UserInfo:
    """Validate an access JWT and return caller identity."""
    return await auth_manager.get_user(access_token)
