import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Base settings shared by every NeuroAtlas service.

    Service-specific settings subclass this and add their own fields.
    """

    service_name: str = "neuroatlas"
    environment: str = os.getenv("ENVIRONMENT", "local")
    default_http_timeout_sec: float = float(os.getenv("DEFAULT_HTTP_TIMEOUT_SEC", "10"))
