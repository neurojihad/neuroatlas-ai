from common.application import app_factory
from ml.adapters.http.handlers import router_v1
from ml.lifespan import lifespan
from ml.settings import settings

app = app_factory.create(
    settings=settings,
    lifespan=lifespan,
    routers=[router_v1],
    cors_origins=settings.origins,
    title="ml",
)
