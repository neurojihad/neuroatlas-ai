"""Guard reverse-proxy handlers forwarding session JWT to backend services."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Request
from starlette.responses import Response as StarletteResponse

from admin_ui.adapters.http import dependencies
from admin_ui.adapters.http.proxy import resolve_upstream_url
from admin_ui.settings import AdminUiSettings
from common.application.logging import logger
from common.adapters.http.schemas import ErrorSchema
from common.utils.identifiers import generate_id_for

router_guard = APIRouter(tags=["guard-proxy"])

_PROXY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
_FORWARD_REQUEST_HEADERS = frozenset(
    {
        "accept",
        "accept-encoding",
        "accept-language",
        "content-type",
        "if-match",
        "if-none-match",
        "if-modified-since",
        "if-unmodified-since",
    }
)
_CORRELATION_HEADERS = ("correlation-id", "x-correlation-id")


def _correlation_id(request: Request) -> Any:
    for header in _CORRELATION_HEADERS:
        value = request.headers.get(header)
        if value:
            return value
    return generate_id_for("correlation")


def _proxy_request_headers(request: Request, access_token: str, user_id: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-User-Id": user_id,
        "Correlation-Id": _correlation_id(request),
    }
    for name, value in request.headers.items():
        if name.lower() in _FORWARD_REQUEST_HEADERS:
            headers[name] = value
    return headers


def _proxy_response_headers(upstream: httpx.Response) -> dict[str, str]:
    allowed = ("content-type", "cache-control", "etag", "location")
    return {name: value for name, value in upstream.headers.items() if name.lower() in allowed}


@router_guard.api_route("/guard/{full_path:path}", methods=_PROXY_METHODS)
async def guard_proxy(request: Request, full_path: str) -> StarletteResponse:
    """Proxy authenticated browser requests to internal backend services."""
    settings: AdminUiSettings = request.app.state.settings
    http_client: httpx.AsyncClient = request.app.state.http_client
    guard_path = f"/guard/{full_path}"

    access_token, user, refreshed_tokens = await dependencies.resolve_session_with_refresh(request)
    upstream_url = resolve_upstream_url(settings, guard_path, request.url.query)
    body = await request.body()

    try:
        upstream = await http_client.request(
            method=request.method,
            url=upstream_url,
            headers=_proxy_request_headers(request, access_token, user.user_id),
            content=body if body else None,
        )
    except httpx.HTTPError as exc:
        await logger.aerror(
            "Guard proxy upstream request failed.",
            exc_info=exc,
            guard_path=guard_path,
            upstream_url=upstream_url,
            user_id=user.user_id,
        )
        return StarletteResponse(
            status_code=502,
            content=ErrorSchema(message="Upstream service unavailable.").model_dump_json(),
            media_type="application/json",
        )

    await logger.ainfo(
        "Guard proxy request completed.",
        guard_path=guard_path,
        upstream_url=upstream_url,
        status_code=upstream.status_code,
        user_id=user.user_id,
    )
    proxy_response = StarletteResponse(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=_proxy_response_headers(upstream),
    )
    if refreshed_tokens is not None:
        dependencies.set_auth_cookies(
            proxy_response,
            settings=settings,
            access_token=refreshed_tokens["access_token"],
            refresh_token=refreshed_tokens["refresh_token"],
        )
    return proxy_response
