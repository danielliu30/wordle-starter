"""
Global Error Handlers

Standardized error responses for all API endpoints.
Provides consistent error format with error codes, messages, and request IDs.
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime
import structlog

logger = structlog.get_logger()


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions with standardized format"""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error("HTTP exception", request_id=request_id, status_code=exc.status_code, detail=exc.detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {"code": "HTTP_ERROR", "message": exc.detail or "An error occurred", "details": None},
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with field details"""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning("Validation error", request_id=request_id, errors=exc.errors())
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {"code": "VALIDATION_ERROR", "message": "Invalid request data", "details": exc.errors()},
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error("Unhandled exception", request_id=request_id, error=str(exc), exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred", "details": None},
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
