from dataclasses import dataclass, field


@dataclass(frozen=True)
class UserInfo:
    """Authenticated caller identity (no PHI — patient ids stay in request paths)."""

    user_id: str
    email: str
    roles: list[str] = field(default_factory=list)
    tenant_id: str | None = None


@dataclass(frozen=True)
class AuthTokenData:
    """Decoded access token context."""

    user_info: UserInfo
    client_id: str | None = None
