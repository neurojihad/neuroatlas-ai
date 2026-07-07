from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from common.core.entities.user import UserInfo
from common.core.exceptions import Forbidden, Unauthorized
from common.core.ports.auth import AuthAdapter

UpsertUserFn = Callable[[UserInfo], Awaitable[None]]

_bearer = HTTPBearer(auto_error=False)


def _extract_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str | None:
    if credentials is None:
        return None
    return credentials.credentials


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(_extract_bearer_token)],
) -> UserInfo:
    """Validate the bearer token and optionally upsert a shadow user row."""
    settings = request.app.state.settings
    auth_manager: AuthAdapter = request.app.state.auth_manager
    if settings.auth_enabled:
        if not token:
            raise Unauthorized("Missing access token.")
        user = await auth_manager.get_user(token)
    else:
        user = await auth_manager.get_user("")
    upsert_user: UpsertUserFn | None = getattr(request.app.state, "upsert_user", None)
    if upsert_user is not None:
        await upsert_user(user)
    return user


def require_roles(*allowed_roles: str):
    """Factory for role-gated dependencies."""

    async def _dependency(user: Annotated[UserInfo, Depends(get_current_user)]) -> UserInfo:
        if not any(role in user.roles for role in allowed_roles):
            raise Forbidden(f"Requires one of: {', '.join(allowed_roles)}.")
        return user

    return _dependency


require_clinician = require_roles("clinician", "admin")
