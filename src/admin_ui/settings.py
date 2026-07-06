import os
from dataclasses import dataclass, field

from common.application.settings import Settings


@dataclass
class AdminUiSettings(Settings):
    """Settings for the admin UI BFF (browser entry + OIDC session + guard proxy)."""

    service_name: str = "admin_ui"
    static_path: str = "frontend/static"

    keycloak_url: str = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
    keycloak_realm: str = os.getenv("KEYCLOAK_REALM", "neuroatlas")
    keycloak_client_id: str = os.getenv("KEYCLOAK_UI_CLIENT_ID", "neuroatlas-ui")
    keycloak_client_secret: str = os.getenv("KEYCLOAK_UI_CLIENT_SECRET", "")

    access_token_alias: str = os.getenv("NEUROATLAS_ACCESS_TOKEN", "NEUROATLAS_ACCESS_TOKEN")
    refresh_token_alias: str = os.getenv("NEUROATLAS_REFRESH_TOKEN", "NEUROATLAS_REFRESH_TOKEN")
    signature_token_alias: str = os.getenv("NEUROATLAS_TOKEN_SIGN", "NEUROATLAS_TOKEN_SIGN")

    patients_route: str = os.getenv("PATIENTS_ROUTE", "localhost:8001")
    ml_route: str = os.getenv("ML_ROUTE", "localhost:8002")
    housekeeper_route: str = os.getenv("HOUSEKEEPER_ROUTE", "localhost:8003")

    origins: list[str] = field(
        default_factory=lambda: [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    service_map: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.service_map:
            self.service_map = {
                "/guard/api/v1/patients": self.patients_route,
                "/guard/api/v1/ml": self.ml_route,
                "/guard/api/v1/housekeeper": self.housekeeper_route,
            }


settings = AdminUiSettings()
