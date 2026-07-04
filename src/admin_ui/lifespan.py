from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from admin_ui.settings import settings
from common.application.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle for the admin_ui BFF service."""
    await logger.ainfo("Service starting.", service_name="admin_ui")
    app.state.settings = settings
    app.state.http_client = httpx.AsyncClient(timeout=settings.default_http_timeout_sec)
    yield
    await app.state.http_client.aclose()
    await logger.ainfo("Service stopped.", service_name="admin_ui")
