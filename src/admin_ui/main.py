"""Entry point for the admin UI BFF service."""

from admin_ui.adapters.http.auth import router_v1 as auth_router
from admin_ui.adapters.http.frontend import router_frontend
from admin_ui.adapters.http.proxy_handlers import router_guard
from admin_ui.lifespan import lifespan
from admin_ui.settings import settings
from common.application import app_factory

app = app_factory.create(
    settings=settings,
    lifespan=lifespan,
    routers=[auth_router, router_guard, router_frontend],
    cors_origins=settings.origins,
    title="admin_ui",
)
