import os
from dataclasses import dataclass

from common.application.settings import Settings


@dataclass
class PatientsSettings(Settings):
    """Settings for the Patients (clinical data) service."""

    service_name: str = "patients"
    postgres_uri: str = os.getenv(
        "POSTGRES_URI",
        "postgresql+asyncpg://neuroatlas:password@localhost:5432/neuroatlas",
    )
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]


settings = PatientsSettings()
