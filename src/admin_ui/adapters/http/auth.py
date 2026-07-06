"""OIDC auth route handlers for the admin_ui BFF."""

from fastapi import APIRouter, Query, Request, Response, status
from fastapi.responses import RedirectResponse

from admin_ui.adapters.http import dependencies
from admin_ui.adapters.http.schemas import AuthUrlSchema, LogoutSchema, UserInfoSchema
from admin_ui.auth.keycloak import KeycloakOidcClient
from admin_ui.auth.session import PkceStore, build_authorize_url, sanitize_redirect_path
from admin_ui.settings import AdminUiSettings
from common.core.exceptions import Unauthorized
from common.http.schemas import ResponseSchema

router_v1 = APIRouter(prefix="/api/v1", tags=["auth"])


@router_v1.get("/auth", response_model=ResponseSchema[AuthUrlSchema])
async def start_auth(
    request: Request,
    redirect_after_login: str = Query(default="/", alias="redirect"),
) -> ResponseSchema[AuthUrlSchema]:
    """Return the Keycloak authorize URL with PKCE state for browser SSO."""

    settings: AdminUiSettings = request.app.state.settings
    pkce_store: PkceStore = request.app.state.pkce_store
    safe_redirect = sanitize_redirect_path(redirect_after_login)
    challenge = pkce_store.create(redirect_after_login=safe_redirect)
    redirect_uri = dependencies.redirect_uri_for_request(request)

    auth_url = build_authorize_url(
        keycloak_base=settings.keycloak_url,
        realm=settings.keycloak_realm,
        client_id=settings.keycloak_client_id,
        redirect_uri=redirect_uri,
        state=challenge.state,
        code_challenge=challenge.code_challenge,
    )

    return ResponseSchema[AuthUrlSchema](data=AuthUrlSchema(auth_url=auth_url))


@router_v1.get("/token")
async def token_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
) -> RedirectResponse:
    """Exchange the OIDC authorization code and establish a cookie session."""

    settings: AdminUiSettings = request.app.state.settings
    pkce_store: PkceStore = request.app.state.pkce_store
    oidc: KeycloakOidcClient = request.app.state.oidc_client

    stored = pkce_store.pop(state)
    if stored is None:
        raise Unauthorized("Invalid or expired OAuth state.")
    code_verifier, redirect_after_login = stored

    redirect_uri = dependencies.redirect_uri_for_request(request)
    tokens = await oidc.exchange_code(
        code=code,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier,
    )

    access_token = str(tokens["access_token"])
    refresh_token = tokens.get("refresh_token")
    refresh_str = str(refresh_token) if refresh_token else None

    response = RedirectResponse(
        url=sanitize_redirect_path(redirect_after_login),
        status_code=status.HTTP_302_FOUND,
    )

    dependencies.set_auth_cookies(
        response,
        settings=settings,
        access_token=access_token,
        refresh_token=refresh_str,
    )

    return response


@router_v1.post("/token/refresh", status_code=status.HTTP_200_OK, response_model=ResponseSchema[None])
async def refresh_token(
    request: Request,
    response: Response,
) -> ResponseSchema[None]:
    """Refresh the session using the httponly refresh token cookie."""

    settings: AdminUiSettings = request.app.state.settings
    oidc: KeycloakOidcClient = request.app.state.oidc_client
    refresh_token_value = request.cookies.get(settings.refresh_token_alias)

    if not refresh_token_value:
        raise Unauthorized("Missing refresh token.")

    tokens = await oidc.refresh(refresh_token_value)
    access_token = str(tokens["access_token"])
    new_refresh = tokens.get("refresh_token")
    refresh_str = str(new_refresh) if new_refresh else refresh_token_value

    dependencies.set_auth_cookies(
        response,
        settings=settings,
        access_token=access_token,
        refresh_token=refresh_str,
    )

    return ResponseSchema[None](data=None)


@router_v1.post("/logout", response_model=ResponseSchema[LogoutSchema])
async def logout(request: Request, response: Response) -> ResponseSchema[LogoutSchema]:
    """Clear session cookies and return optional Keycloak logout URL."""

    settings: AdminUiSettings = request.app.state.settings
    oidc: KeycloakOidcClient = request.app.state.oidc_client
    dependencies.clear_auth_cookies(response, settings)

    return ResponseSchema[LogoutSchema](data=LogoutSchema(logout_url=oidc.logout_url))


@router_v1.get("/auth/me", response_model=ResponseSchema[UserInfoSchema])
async def auth_me(request: Request, response: Response) -> ResponseSchema[UserInfoSchema]:
    """Return the current authenticated user from the session JWT."""

    settings: AdminUiSettings = request.app.state.settings
    _access_token, user, refreshed_tokens = await dependencies.resolve_session_with_refresh(request)
    if refreshed_tokens is not None:
        dependencies.set_auth_cookies(
            response,
            settings=settings,
            access_token=refreshed_tokens["access_token"],
            refresh_token=refreshed_tokens["refresh_token"],
        )

    return ResponseSchema[UserInfoSchema](
        data=UserInfoSchema(user_id=user.user_id, email=user.email, roles=user.roles),
    )
