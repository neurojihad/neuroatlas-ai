import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    """Base settings shared by every NeuroAtlas service.

    Service-specific settings subclass this and add their own fields.
    """

    service_name: str = "neuroatlas"
    environment: str = os.getenv("ENVIRONMENT", "local")
    default_http_timeout_sec: float = float(os.getenv("DEFAULT_HTTP_TIMEOUT_SEC", "10"))
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_client_id: str = os.getenv("KAFKA_CLIENT_ID", "neuroatlas")
    kafka_consumer_group: str = os.getenv("KAFKA_CONSUMER_GROUP", "neuroatlas")
    kafka_enabled: bool = _env_bool("KAFKA_ENABLED", False)
