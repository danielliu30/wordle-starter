"""
Tests for test environment configuration

Tests the test fixtures to ensure:
- Test database is created correctly
- Test session is isolated
- Test fixtures work as expected
"""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

pytestmark = pytest.mark.asyncio


async def test_test_engine(test_engine):
    """
    Test that test engine is created correctly.

    Verifies the fixture provides a valid SQLAlchemy engine.
    """
    assert isinstance(test_engine, AsyncEngine)


async def test_test_session(test_session):
    """
    Test that test session is created correctly.

    Verifies the fixture provides a valid SQLAlchemy session.
    """
    assert isinstance(test_session, AsyncSession)
    result = await test_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


async def test_committed_data_written(test_session):
    """
    Commit a row so the next test can verify it does not leak.
    """
    await test_session.execute(text("CREATE TABLE isolation_check (id INTEGER)"))
    await test_session.execute(text("INSERT INTO isolation_check VALUES (1)"))
    await test_session.commit()

    result = await test_session.execute(text("SELECT COUNT(*) FROM isolation_check"))
    assert result.scalar() == 1


async def test_committed_data_does_not_leak(test_session):
    """
    Test that data committed by a previous test is not visible.
    """
    result = await test_session.execute(
        text("SELECT name FROM sqlite_master WHERE name = 'isolation_check'")
    )
    assert result.scalar() is None
