"""Serve built React SPA assets with runtime ``window._env_`` injection."""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from starlette.staticfiles import StaticFiles

from admin_ui.settings import AdminUiSettings

_ENV_SCRIPT_PATTERN = re.compile(
    r"<script>\s*window\._env_\s*=\s*\{\s*\}\s*;?\s*</script>",
    re.IGNORECASE,
)
_RESERVED_PATH_PREFIXES = (
    "/api/",
    "/guard/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
)
_ADMIN_UI_ROOT = Path(__file__).resolve().parents[2]

router_frontend = APIRouter(tags=["frontend"])


def resolve_frontend_dir(settings: AdminUiSettings) -> Path:
    """Return the directory that contains the built ``index.html``."""

    path = Path(settings.frontend_dir)
    if path.is_absolute():
        return path
    return _ADMIN_UI_ROOT / path


def resolve_static_dir(settings: AdminUiSettings) -> Path:
    return resolve_frontend_dir(settings) / "static"


def build_runtime_env(settings: AdminUiSettings) -> dict[str, object]:
    """Runtime config exposed to the embedded React SPA."""

    return {
        "AUTH_ENABLED": settings.auth_enabled,
    }


def render_index(settings: AdminUiSettings) -> str:
    frontend_dir = resolve_frontend_dir(settings)
    index_path = frontend_dir / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=503, detail="Frontend assets not built")

    template = index_path.read_text(encoding="utf-8")
    env_script = f"<script>window._env_ = {json.dumps(build_runtime_env(settings))};</script>"
    if not _ENV_SCRIPT_PATTERN.search(template):
        raise HTTPException(status_code=500, detail="index.html missing window._env_ placeholder")
    return _ENV_SCRIPT_PATTERN.sub(env_script, template, count=1)


def _is_reserved_path(path: str) -> bool:
    for prefix in _RESERVED_PATH_PREFIXES:
        normalized = prefix.rstrip("/")
        if path == normalized or path.startswith(prefix):
            return True
    return False


def mount_static_files(app, settings: AdminUiSettings) -> None:
    """Mount CRA ``/static`` assets when the build output is present."""

    static_dir = resolve_static_dir(settings)
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@router_frontend.get("/", include_in_schema=False)
async def serve_index(request: Request) -> HTMLResponse:
    settings: AdminUiSettings = request.app.state.settings
    return HTMLResponse(render_index(settings))


@router_frontend.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str, request: Request) -> Response:
    path = f"/{full_path}"
    if _is_reserved_path(path):
        raise HTTPException(status_code=404)

    settings: AdminUiSettings = request.app.state.settings
    frontend_dir = resolve_frontend_dir(settings)
    file_path = (frontend_dir / full_path).resolve()
    frontend_root = frontend_dir.resolve()
    if not str(file_path).startswith(str(frontend_root)):
        raise HTTPException(status_code=404)
    if file_path.is_file():
        return FileResponse(file_path)

    return HTMLResponse(render_index(settings))
