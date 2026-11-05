"""
Global Error Handlers

Standardized error responses for all API endpoints.
Provides consistent error format with error codes, messages, and request IDs.
"""
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime, timezone
import structlog

logger = structlog.get_logger()


def _error_body(request: Request, code: str, message: str, details=None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": getattr(request.state, "request_id", "unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    }


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle FastAPI HTTP exceptions with standardized format"""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error("HTTP exception", request_id=request_id, status_code=exc.status_code, detail=exc.detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(request, "HTTP_ERROR", exc.detail or "An error occurred"),
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with field details"""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning("Validation error", request_id=request_id, errors=exc.errors())
    
    return JSONResponse(
        status_code=422,
        content=_error_body(
            request, "VALIDATION_ERROR", "Invalid request data", jsonable_encoder(exc.errors())
        ),
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error("Unhandled exception", request_id=request_id, error=str(exc), exc_info=True)
    
    # Starlette sends this 500 from outside RequestIDMiddleware, so set the header here.
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body(request, "INTERNAL_ERROR", "An unexpected error occurred"),
        headers={"X-Request-ID": request_id},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
