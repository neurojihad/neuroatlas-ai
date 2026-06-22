from prometheus_client import make_asgi_app

from common.application import app_factory
from housekeeper.adapters.http.handlers import router_v1
from housekeeper.lifespan import lifespan
from housekeeper.settings import settings

app = app_factory.create(
    settings=settings,
    lifespan=lifespan,
    routers=[router_v1],
    cors_origins=settings.origins,
    title="housekeeper",
)

# Observability lives in the app layer, never the domain (see backend_conventions).
app.mount("/metrics", make_asgi_app())
