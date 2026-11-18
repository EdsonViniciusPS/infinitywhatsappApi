"""Custom application exceptions and FastAPI exception handlers."""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "app_error",
        details: Any = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details
        super().__init__(message)


class UnauthorizedError(AppError):
    """Raised when authentication credentials are missing or invalid."""

    def __init__(self, message: str = "Credenciais inválidas ou ausentes.") -> None:
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, "unauthorized")


class ForbiddenError(AppError):
    """Raised when a tenant tries to access a resource it does not own."""

    def __init__(self, message: str = "Acesso negado a este recurso.") -> None:
        super().__init__(message, status.HTTP_403_FORBIDDEN, "forbidden")


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str = "Recurso não encontrado.") -> None:
        super().__init__(message, status.HTTP_404_NOT_FOUND, "not_found")


class EvolutionAPIError(AppError):
    """Raised when the upstream Evolution API returns an error or is unreachable."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_502_BAD_GATEWAY,
        details: Any = None,
    ) -> None:
        super().__init__(message, status_code, "evolution_api_error", details)


class GeminiAPIError(AppError):
    """Raised when the Google Gemini API returns an error or is misconfigured."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_502_BAD_GATEWAY,
        details: Any = None,
    ) -> None:
        super().__init__(message, status_code, "gemini_api_error", details)


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        payload: dict[str, Any] = {
            "error": {
                "code": exc.code,
                "message": exc.message,
            }
        }
        if exc.details is not None:
            payload["error"]["details"] = exc.details
        return JSONResponse(status_code=exc.status_code, content=payload)
