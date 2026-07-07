from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from admin_ui.adapters.http.frontend import mount_static_files
from admin_ui.auth.keycloak import KeycloakOidcClient
from admin_ui.auth.session import PkceStore
from admin_ui.settings import settings
from common.adapters.auth.keycloak import build_auth_adapter
from common.application.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle for the admin_ui BFF service."""
    await logger.ainfo("Service starting.", service_name="admin_ui")
    app.state.settings = settings
    mount_static_files(app, settings)
    app.state.http_client = httpx.AsyncClient(timeout=settings.default_http_timeout_sec)
    app.state.auth_manager = build_auth_adapter(settings)
    app.state.pkce_store = PkceStore()
    app.state.oidc_client = KeycloakOidcClient(settings, app.state.http_client)
    yield
    await app.state.http_client.aclose()
    await logger.ainfo("Service stopped.", service_name="admin_ui")
