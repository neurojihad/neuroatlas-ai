"""PKCE state store and split-JWT cookie helpers for the admin_ui BFF session."""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import jwt
from jwt.exceptions import ExpiredSignatureError, PyJWTError

_PKCE_TTL_SEC = 600


@dataclass(frozen=True)
class PkceChallenge:
    """Generated PKCE pair and CSRF state for one authorize redirect."""

    state: str
    code_verifier: str
    code_challenge: str
    redirect_after_login: str


@dataclass
class _PkceEntry:
    code_verifier: str
    redirect_after_login: str
    created_at: float


class PkceStore:
    """In-memory PKCE verifier store keyed by OAuth state (Pioneer scope)."""

    def __init__(self, ttl_sec: int = _PKCE_TTL_SEC) -> None:
        self._ttl_sec = ttl_sec
        self._entries: dict[str, _PkceEntry] = {}

    def _purge_expired(self) -> None:
        cutoff = time.monotonic() - self._ttl_sec
        expired = [state for state, entry in self._entries.items() if entry.created_at < cutoff]
        for state in expired:
            del self._entries[state]

    def create(self, redirect_after_login: str = "/") -> PkceChallenge:
        self._purge_expired()
        code_verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        state = secrets.token_urlsafe(32)
        self._entries[state] = _PkceEntry(
            code_verifier=code_verifier,
            redirect_after_login=redirect_after_login,
            created_at=time.monotonic(),
        )
        return PkceChallenge(
            state=state,
            code_verifier=code_verifier,
            code_challenge=code_challenge,
            redirect_after_login=redirect_after_login,
        )

    def pop(self, state: str) -> tuple[str, str] | None:
        """Return (code_verifier, redirect_after_login) and remove the entry."""
        self._purge_expired()
        entry = self._entries.pop(state, None)
        if entry is None:
            return None
        return entry.code_verifier, entry.redirect_after_login


def split_jwt(token: str) -> tuple[str, str]:
    """Split a JWT into (header.payload, signature) for split-cookie storage."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format.")
    return f"{parts[0]}.{parts[1]}", parts[2]


def join_jwt(payload_part: str, signature_part: str) -> str:
    """Reconstruct a JWT from split-cookie parts."""
    if not payload_part or not signature_part:
        raise ValueError("Missing JWT cookie parts.")
    return f"{payload_part}.{signature_part}"


def build_authorize_url(
    *,
    keycloak_base: str,
    realm: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    scope: str = "openid profile email",
) -> str:
    """Build the Keycloak OIDC authorization URL with PKCE."""
    params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": scope,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    base = f"{keycloak_base.rstrip('/')}/realms/{realm}/protocol/openid-connect/auth"
    return f"{base}?{urlencode(params)}"


def sanitize_redirect_path(path: str) -> str:
    """Allow only same-origin relative paths (blocks open redirects)."""
    if not path.startswith("/") or path.startswith("//") or "://" in path:
        return "/"
    return path


def is_access_token_expired(token: str) -> bool:
    """Return True when the JWT exp claim is in the past (signature not verified)."""
    try:
        jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_iss": False,
                "verify_exp": True,
            },
        )
        return False
    except ExpiredSignatureError:
        return True
    except PyJWTError:
        return False
