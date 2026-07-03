"""Container liveness probe used by Docker Compose healthchecks."""

import sys

import httpx

_HEALTH_URL = "http://127.0.0.1:8000/health"


def main() -> None:
    """Exit 0 when the service health endpoint responds with HTTP 200."""

    try:
        response = httpx.get(_HEALTH_URL, timeout=2.0)
        if response.status_code != 200:
            sys.exit(1)
    except httpx.HTTPError:
        sys.exit(1)


if __name__ == "__main__":
    main()
