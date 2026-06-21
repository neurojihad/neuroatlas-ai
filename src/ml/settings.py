import os
from dataclasses import dataclass

from common.application.settings import Settings


@dataclass
class MLSettings(Settings):
    """Settings for the ML (outcome prediction) service."""

    service_name: str = "ml"
    model_version: str = os.getenv("MODEL_VERSION", "baseline-0.1.0")
    kafka_client_id: str = os.getenv("KAFKA_CLIENT_ID", "ml")
    kafka_consumer_group: str = os.getenv("KAFKA_CONSUMER_GROUP", "ml")
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]


settings = MLSettings()
