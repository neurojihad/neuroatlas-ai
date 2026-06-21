"""Container liveness probe used by Docker Compose healthchecks."""

import sys
import urllib.error
import urllib.request

_HEALTH_URL = "http://127.0.0.1:8000/health"


def main() -> None:
    """Exit 0 when the service health endpoint responds with HTTP 200."""

    try:
        with urllib.request.urlopen(_HEALTH_URL, timeout=2) as response:
            if response.status != 200:
                sys.exit(1)
    except (urllib.error.URLError, TimeoutError):
        sys.exit(1)


if __name__ == "__main__":
    main()
