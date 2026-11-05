"""
Request ID Middleware

Generates or extracts a unique request ID for every API request.
Used for distributed tracing and debugging across microservices.
"""
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse, Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle request IDs for distributed tracing.
    
    Flow:
    1. Check for X-Request-ID header from client
    2. Generate UUID if not provided
    3. Add to request.state for use in endpoints/logging
    4. Return X-Request-ID in response headers
    
    This enables:
    - Request tracing across microservices
    - Debugging with request_id in logs
    - Client-side error reporting with request_id
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and manage request ID.
        
        Args:
            request: Incoming FastAPI request
            call_next: Next middleware/endpoint to call
        
        Returns:
            Response with X-Request-ID header
        """
        # Extract or generate request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Add to request state for use in endpoints and logging
        request.state.request_id = request_id

        # Process request
        response: Response = await call_next(request)

        # Add to response headers
        response.headers["X-Request-ID"] = request_id

        return response


async def request_id_server_error_handler(request: Request, exc: Exception) -> Response:
    """
    Return the 500 response for unhandled exceptions with X-Request-ID set.

    Starlette builds this response outside application middleware, so
    RequestIDMiddleware never sees it. The ID it stored on request.state
    is still available here because both share the same ASGI scope.
    """
    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID") or str(uuid.uuid4())
    return PlainTextResponse(
        "Internal Server Error",
        status_code=500,
        headers={"X-Request-ID": request_id},
    )
