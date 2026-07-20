from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.application.settings import Settings
from common.application.error_handlers import register_exception_handlers


def create(
    *,
    settings: Settings,
    routers: list[APIRouter],
    title: str,
    lifespan: Callable[[FastAPI], AbstractAsyncContextManager] | None = None,
    cors_origins: list[str] | None = None,
) -> FastAPI:
    """Build a configured FastAPI app.

    Mirrors the paymentgate `common.application.create` factory so every service
    is wired the same way: shared CORS, error envelope, and a `/health` probe.
    """
    app = FastAPI(title=title, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    @app.get("/health", tags=["service"])
    async def health() -> dict[str, str]:
        """Liveness probe."""
        return {"status": "ok", "service": settings.service_name}

    for router in routers:
        app.include_router(router)

    return app
