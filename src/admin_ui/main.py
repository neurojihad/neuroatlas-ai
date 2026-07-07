"""Entry point for the admin UI BFF service."""

from admin_ui.adapters.http.auth import router_v1 as auth_router
from admin_ui.adapters.http.frontend import mount_static_files, router_frontend
from admin_ui.adapters.http.proxy_handlers import router_guard
from admin_ui.lifespan import lifespan
from admin_ui.settings import settings
from common.application import app_factory

app = app_factory.create(
    settings=settings,
    lifespan=lifespan,
    routers=[auth_router, router_guard],
    cors_origins=settings.origins,
    title="admin_ui",
)
mount_static_files(app, settings)
app.include_router(router_frontend)
