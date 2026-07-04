import pytest
from httpx import ASGITransport, AsyncClient

from admin_ui.main import app


@pytest.mark.asyncio
async def test_health_returns_ok():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "admin_ui"
