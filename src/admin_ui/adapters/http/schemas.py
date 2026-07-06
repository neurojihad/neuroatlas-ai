"""Pydantic schemas for admin_ui HTTP auth endpoints."""

from pydantic import BaseModel, Field


class AuthUrlSchema(BaseModel):
    """Keycloak authorize URL for browser SSO redirect."""

    auth_url: str


class UserInfoSchema(BaseModel):
    """Authenticated caller exposed to the embedded React app."""

    user_id: str
    email: str
    roles: list[str] = Field(default_factory=list)


class LogoutSchema(BaseModel):
    """Optional Keycloak end-session URL for frontend redirect."""

    logout_url: str | None = None
