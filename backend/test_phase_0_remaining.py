"""Tests for remaining Phase 0 components"""
import pytest
from app.health import HealthChecker
from app.lifecycle import lifespan, shutdown_gracefully
from app.timeout import TimeoutConfig, execute_with_timeout

async def test_health_checker():
    checker = HealthChecker()
    status = await checker.get_health_status()
    assert status["status"] == "healthy"

async def test_lifecycle():
    from fastapi import FastAPI
    app = FastAPI()
    async with lifespan(app):
        pass

async def test_shutdown():
    await shutdown_gracefully()

async def test_timeout_config():
    assert TimeoutConfig.DATABASE_QUERY_TIMEOUT > 0

async def test_execute_with_timeout():
    async def fast():
        return "done"
    result = await execute_with_timeout(fast(), 1)
    assert result == "done"
