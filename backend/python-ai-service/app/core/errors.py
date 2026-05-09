from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.envelopes import error


class JarvisError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 500, details: dict | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ProviderUnavailableError(JarvisError):
    def __init__(self, provider_id: str, reason: str = "API key not configured"):
        super().__init__(
            code="provider_unavailable",
            message=f"Provider '{provider_id}' is unavailable: {reason}",
            status_code=503,
            details={"providerId": provider_id, "reason": reason},
        )


class ServiceUnavailableError(JarvisError):
    def __init__(self, service: str):
        super().__init__(
            code="service_unavailable",
            message=f"Service '{service}' is not available",
            status_code=503,
            details={"service": service},
        )


class NotFoundError(JarvisError):
    def __init__(self, resource: str):
        super().__init__(
            code="not_found",
            message=f"Resource '{resource}' not found",
            status_code=404,
        )


class ValidationError(JarvisError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            code="validation_error",
            message=message,
            status_code=422,
            details=details,
        )


async def jarvis_error_handler(request: Request, exc: JarvisError) -> JSONResponse:
    correlation_id = request.headers.get("x-correlation-id")
    return JSONResponse(
        status_code=exc.status_code,
        content=error(exc.code, exc.message, exc.details, correlation_id),
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = request.headers.get("x-correlation-id")
    return JSONResponse(
        status_code=500,
        content=error("internal_error", "An internal error occurred", None, correlation_id),
    )
