"""Entry point for the admin UI BFF service."""

from admin_ui.lifespan import lifespan
from admin_ui.settings import settings
from common.application import app_factory

app = app_factory.create(
    settings=settings,
    lifespan=lifespan,
    routers=[],
    cors_origins=settings.origins,
    title="admin_ui",
)
