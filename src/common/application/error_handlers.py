from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from common.application.logging import logger
from common.core.exceptions import AuthException, ContextValidationError, DatabaseException, DomainError


def register_exception_handlers(app: FastAPI) -> None:
    """Translate domain errors into the uniform error envelope."""

    @app.exception_handler(DomainError)
    async def _domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        body: dict[str, str | None] = {"message": exc.message, "details": exc.details}
        if isinstance(exc, ContextValidationError):
            body["field_name"] = exc.field_name
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(AuthException)
    async def _auth_error_handler(_: Request, exc: AuthException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": exc.message, "details": exc.details},
        )

    @app.exception_handler(DatabaseException)
    async def _database_error_handler(request: Request, exc: DatabaseException) -> JSONResponse:
        await logger.aerror(
            "Database adapter failure.",
            method=request.method,
            path=request.url.path,
            details=exc.details,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": "Internal server error.", "details": None},
        )
