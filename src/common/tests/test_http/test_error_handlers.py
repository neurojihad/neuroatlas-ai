from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from common.application.error_handlers import register_exception_handlers
from common.core.exceptions import DatabaseException

_INTERNAL_DETAILS = "psycopg: connection refused"


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def _boom() -> dict[str, str]:
        raise DatabaseException("db down", _INTERNAL_DETAILS)

    return app


async def test_database_exception_maps_to_500_without_leaking_details():
    app = _build_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["message"] == "Internal server error."
    assert body["details"] is None
    assert set(body) <= {"message", "details", "field_name"}
    assert _INTERNAL_DETAILS not in response.text
    assert "db down" not in response.text
