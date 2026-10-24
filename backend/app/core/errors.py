from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("parksmart.errors")


class AppException(Exception):
    """Base application exception."""
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, error_type: str = "bad_request"):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(message)


class DatabaseConnectionError(AppException):
    """Raised when database is unavailable and operation requires database connectivity."""
    def __init__(self, message: str = "Database service unavailable. Please check MongoDB connectivity."):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_type="database_unavailable"
        )


class EntityNotFoundError(AppException):
    """Raised when requested resource does not exist."""
    def __init__(self, entity_name: str, entity_id: str):
        super().__init__(
            message=f"{entity_name} with id '{entity_id}' not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            error_type="not_found"
        )


class DuplicateEntityError(AppException):
    """Raised when an entity with the specified ID or unique field already exists."""
    def __init__(self, entity_name: str, entity_id: str):
        super().__init__(
            message=f"{entity_name} with id '{entity_id}' already exists.",
            status_code=status.HTTP_409_CONFLICT,
            error_type="duplicate_entity"
        )


class IntegrationUnavailableError(AppException):
    """Raised when an external integration module (ML or Recommendation engine) is unavailable or not yet configured."""
    def __init__(self, service_name: str, detail: str = "Integration module is not yet configured or unavailable."):
        super().__init__(
            message=f"{service_name} integration unavailable: {detail}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_type="integration_unavailable"
        )


class BadRequestError(AppException):
    """Raised when request parameters are syntactically valid but violate business rules."""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type="bad_request"
        )


def register_error_handlers(app: FastAPI) -> None:
    """Register custom exception handlers for uniform error structures."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": exc.error_type,
                    "message": exc.message,
                    "status_code": exc.status_code
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        formatted_errors = []
        for error in exc.errors():
            loc = " -> ".join([str(x) for x in error.get("loc", [])])
            formatted_errors.append({
                "location": loc,
                "message": error.get("msg", ""),
                "type": error.get("type", "")
            })

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "type": "validation_error",
                    "message": "Input validation failed. Please check the submitted fields.",
                    "details": formatted_errors,
                    "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY
                }
            }
        )
