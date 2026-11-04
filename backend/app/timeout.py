"""
Timeout Configuration

Provides timeout configurations for various operations.
Uses asyncio.wait_for to enforce timeouts.
"""
import asyncio
from config import settings


class TimeoutConfig:
    """
    Centralized timeout configuration.
    
    Timeouts are in seconds and loaded from settings.
    """
    
    # Database query timeout (10 seconds)
    # Prevents long-running queries from blocking
    DATABASE_QUERY_TIMEOUT = settings.database_query_timeout
    
    # Redis operation timeout (5 seconds)
    # Prevents slow cache operations from blocking
    REDIS_TIMEOUT = settings.redis_timeout
    
    # API request timeout (30 seconds)
    # Prevents slow API calls from blocking
    API_REQUEST_TIMEOUT = settings.api_request_timeout


async def execute_with_timeout(coro, timeout: int):
    """
    Execute a coroutine with a timeout.
    
    Args:
        coro: The coroutine to execute
        timeout: Timeout in seconds
    
    Returns:
        Result of the coroutine
    
    Raises:
        TimeoutError: If timeout is exceeded
    
    Use this to wrap any potentially long-running operation.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout} seconds")
