"""HTTP tests for admin_ui static SPA serving and window._env_ injection."""

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from admin_ui.adapters.http.frontend import (
    _ENV_SCRIPT_PATTERN,
    build_runtime_env,
    mount_static_files,
    render_index,
)
from admin_ui.main import app
from admin_ui.settings import AdminUiSettings

_INDEX_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <script>window._env_ = {};</script>
    <title>NeuroAtlas Admin</title>
  </head>
  <body><div id="root"></div></body>
</html>
"""


@pytest.fixture
def built_frontend(tmp_path: Path) -> Path:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "main.js").write_text("console.log('ok');", encoding="utf-8")
    (tmp_path / "index.html").write_text(_INDEX_TEMPLATE, encoding="utf-8")
    return tmp_path


@pytest.fixture
def frontend_settings(built_frontend: Path) -> AdminUiSettings:
    return AdminUiSettings(frontend_dir=str(built_frontend))


@pytest.mark.asyncio
async def test_serve_index_injects_runtime_env(frontend_settings: AdminUiSettings):
    html = render_index(frontend_settings)
    expected_env = json.dumps(build_runtime_env(frontend_settings))
    assert f"window._env_ = {expected_env}" in html
    assert _ENV_SCRIPT_PATTERN.search(html) is None


@pytest.mark.asyncio
async def test_serve_index_injects_runtime_env_from_cra_build(tmp_path: Path):
    cra_index = (
        '<!doctype html><html lang="en"><head>'
        "<script>window._env_={}</script>"
        '<script defer="defer" src="/static/js/main.js"></script>'
        "</head><body><div id=\"root\"></div></body></html>"
    )
    (tmp_path / "index.html").write_text(cra_index, encoding="utf-8")
    settings = AdminUiSettings(frontend_dir=str(tmp_path))
    html = render_index(settings)
    expected_env = json.dumps(build_runtime_env(settings))
    assert f"window._env_ = {expected_env}" in html


@pytest.mark.asyncio
async def test_root_returns_index_with_env(built_frontend: Path, frontend_settings: AdminUiSettings):
    expected_env = json.dumps(build_runtime_env(frontend_settings))
    async with app.router.lifespan_context(app):
        app.state.settings = frontend_settings
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as client:
            response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert f"window._env_ = {expected_env}" in response.text


@pytest.mark.asyncio
async def test_client_route_returns_index_on_refresh(built_frontend: Path, frontend_settings: AdminUiSettings):
    expected_env = json.dumps(build_runtime_env(frontend_settings))
    async with app.router.lifespan_context(app):
        app.state.settings = frontend_settings
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as client:
            response = await client.get("/dashboard")
    assert response.status_code == 200
    assert f"window._env_ = {expected_env}" in response.text


@pytest.mark.asyncio
async def test_static_assets_are_served_through_main_app(built_frontend: Path, frontend_settings: AdminUiSettings):
    (built_frontend / "static" / "js").mkdir(parents=True, exist_ok=True)
    (built_frontend / "static" / "js" / "main.js").write_text("console.log('bundle');", encoding="utf-8")
    async with app.router.lifespan_context(app):
        app.state.settings = frontend_settings
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as client:
            response = await client.get("/static/js/main.js")
    assert response.status_code == 200
    assert response.text == "console.log('bundle');"


@pytest.mark.asyncio
async def test_static_assets_are_served(built_frontend: Path, frontend_settings: AdminUiSettings):
    test_app = FastAPI()
    mount_static_files(test_app, frontend_settings)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.get("/static/main.js")
    assert response.status_code == 200
    assert response.text == "console.log('ok');"


@pytest.mark.asyncio
async def test_api_routes_are_not_handled_by_spa(built_frontend: Path):
    async with app.router.lifespan_context(app):
        app.state.settings = AdminUiSettings(frontend_dir=str(built_frontend))
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as client:
            auth_response = await client.get("/api/v1/auth")
            health_response = await client.get("/health")
    assert auth_response.status_code == 200
    assert health_response.status_code == 200
    assert health_response.json()["service"] == "admin_ui"
