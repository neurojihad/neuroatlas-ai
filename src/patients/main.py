from common.application import app_factory
from patients.adapters.http.handlers import router_v1
from patients.lifespan import lifespan
from patients.settings import settings

app = app_factory.create(
    settings=settings,
    lifespan=lifespan,
    routers=[router_v1],
    cors_origins=settings.origins,
    title="patients",
)
