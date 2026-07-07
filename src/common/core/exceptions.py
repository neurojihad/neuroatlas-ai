class DomainError(Exception):
    """Base class for all domain errors."""

    status_code: int = 400

    def __init__(self, message: str, details: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFound(DomainError):
    """Requested entity does not exist."""

    status_code = 404


class ContextValidationError(DomainError):
    """A command context failed validation."""

    status_code = 422

    def __init__(self, message: str, field_name: str | None = None) -> None:
        super().__init__(message)
        self.field_name = field_name


class InvalidOperation(DomainError):
    """Operation is not allowed in the current state."""

    status_code = 409


class Unauthorized(DomainError):
    """Missing or invalid credentials."""

    status_code = 401


class Forbidden(DomainError):
    """Authenticated caller lacks permission for the requested action."""

    status_code = 403


class BusException(Exception):
    """Raised when the event bus adapter fails."""

    def __init__(self, message: str, details: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class AuthException(Exception):
    """Raised when the auth adapter fails to validate a token."""

    status_code = 401

    def __init__(self, message: str, details: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
