from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ResponseSchema(BaseModel, Generic[T]):
    """Single-object response envelope."""

    data: T


class ListResponseSchema(BaseModel, Generic[T]):
    """Collection response envelope."""

    data: list[T]


class PaginatedResponseSchema(BaseModel, Generic[T]):
    """Cursor-paginated response envelope."""

    data: list[T]
    next: str | None = None


class ErrorSchema(BaseModel):
    """Uniform error body returned for every handled exception."""

    message: str
    details: str | None = None
    field_name: str | None = None
