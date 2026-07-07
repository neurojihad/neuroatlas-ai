"""Resolve guard paths to upstream backend URLs."""

from admin_ui.settings import AdminUiSettings
from common.core.exceptions import NotFound


def _normalize_host(host: str) -> str:
    if host.startswith("http://") or host.startswith("https://"):
        return host.rstrip("/")
    return f"http://{host.rstrip('/')}"


def backend_path(guard_prefix: str, full_path: str) -> str:
    """Map a guard path to the backend service path."""
    if guard_prefix.endswith("/patients"):
        return full_path.removeprefix("/guard")
    remainder = full_path[len(guard_prefix) :]
    return f"/api/v1{remainder}"


def resolve_upstream_url(settings: AdminUiSettings, path: str, query: str) -> str:
    """Return the full upstream URL for a guard request path."""
    for guard_prefix, host in sorted(settings.service_map.items(), key=lambda item: len(item[0]), reverse=True):
        if path == guard_prefix or path.startswith(f"{guard_prefix}/"):
            service_path = backend_path(guard_prefix, path)
            base = _normalize_host(host)
            url = f"{base}{service_path}"
            if query:
                url = f"{url}?{query}"
            return url
    raise NotFound(f"No upstream service configured for path: {path}")
