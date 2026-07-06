"""FastAPI dependencies for admin_ui cookie-based OIDC session."""

from typing import Annotated

from fastapi import Depends, Request

from admin_ui.auth.keycloak import KeycloakOidcClient
from admin_ui.auth.queries import get_user_from_access_token
from admin_ui.auth.session import join_jwt, split_jwt
from admin_ui.settings import AdminUiSettings
from common.core.entities.user import UserInfo
from common.core.exceptions import AuthException, Unauthorized
from common.core.ports.auth import AuthAdapter


def _cookie_secure(settings: AdminUiSettings) -> bool:
    return settings.environment != "local"


def set_auth_cookies(
    response,
    *,
    settings: AdminUiSettings,
    access_token: str,
    refresh_token: str | None,
) -> None:
    """Set split JWT access cookies and httponly refresh cookie on a response."""
    payload_part, signature_part = split_jwt(access_token)
    secure = _cookie_secure(settings)
    common = {"path": "/", "samesite": "lax", "secure": secure}
    response.set_cookie(
        key=settings.access_token_alias,
        value=payload_part,
        httponly=False,
        **common,
    )
    response.set_cookie(
        key=settings.signature_token_alias,
        value=signature_part,
        httponly=True,
        **common,
    )
    if refresh_token:
        response.set_cookie(
            key=settings.refresh_token_alias,
            value=refresh_token,
            httponly=True,
            **common,
        )


def clear_auth_cookies(response, settings: AdminUiSettings) -> None:
    """Remove all session cookies."""
    for name in (
        settings.access_token_alias,
        settings.signature_token_alias,
        settings.refresh_token_alias,
    ):
        response.delete_cookie(key=name, path="/")


def redirect_uri_for_request(request: Request) -> str:
    """Build the OIDC redirect URI matching Keycloak client registration."""
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/v1/token"


async def get_session_access_token(request: Request) -> str:
    """Reconstruct the access JWT from split session cookies."""
    settings: AdminUiSettings = request.app.state.settings
    payload = request.cookies.get(settings.access_token_alias)
    signature = request.cookies.get(settings.signature_token_alias)
    if not payload or not signature:
        raise Unauthorized("Missing session cookies.")
    try:
        return join_jwt(payload, signature)
    except ValueError as exc:
        raise Unauthorized("Invalid session cookies.") from exc


async def get_session_user(
    request: Request,
    token: Annotated[str, Depends(get_session_access_token)],
) -> UserInfo:
    """Validate session access token and return caller identity."""
    auth_manager: AuthAdapter = request.app.state.auth_manager
    return await get_user_from_access_token(auth_manager, token)


SessionUser = Annotated[UserInfo, Depends(get_session_user)]


async def resolve_session_with_refresh(
    request: Request,
) -> tuple[str, UserInfo, dict[str, str] | None]:
    """Return access token, user, and optional refreshed token payload for cookie updates."""
    settings: AdminUiSettings = request.app.state.settings
    auth_manager: AuthAdapter = request.app.state.auth_manager
    oidc: KeycloakOidcClient = request.app.state.oidc_client

    access_token = await get_session_access_token(request)
    try:
        user = await get_user_from_access_token(auth_manager, access_token)
        return access_token, user, None
    except AuthException:
        refresh_token_value = request.cookies.get(settings.refresh_token_alias)
        if not refresh_token_value:
            raise Unauthorized("Session expired.") from None

        tokens = await oidc.refresh(refresh_token_value)
        access_token = str(tokens["access_token"])
        new_refresh = tokens.get("refresh_token")
        refresh_str = str(new_refresh) if new_refresh else refresh_token_value
        user = await get_user_from_access_token(auth_manager, access_token)
        return access_token, user, {"access_token": access_token, "refresh_token": refresh_str}
