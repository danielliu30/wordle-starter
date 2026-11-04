"""Timeout configuration"""
import asyncio
from config import settings

class TimeoutConfig:
    DATABASE_QUERY_TIMEOUT = settings.database_query_timeout
    REDIS_TIMEOUT = settings.redis_timeout
    API_REQUEST_TIMEOUT = settings.api_request_timeout

async def execute_with_timeout(coro, timeout: int):
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout} seconds")
