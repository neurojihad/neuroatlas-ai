import pytest
from httpx import ASGITransport, AsyncClient

from patients.main import app


@pytest.mark.asyncio
async def test_register_patient_with_null_auth():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/patients",
                json={"date_of_birth_year": 2018, "sex": "F"},
            )
    assert response.status_code == 201
    assert response.json()["data"].startswith("pat_")


@pytest.mark.asyncio
async def test_list_patients_with_null_auth():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/patients")
    assert response.status_code == 200
    assert "data" in response.json()
