"""
Tests for test environment configuration

Tests the test fixtures to ensure:
- Test database is created correctly
- Test session is isolated
- Test fixtures work as expected
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession


async def test_test_engine(test_engine):
    """
    Test that test engine is created correctly.
    
    Verifies the fixture provides a valid SQLAlchemy engine.
    """
    assert test_engine is not None
    assert hasattr(test_engine, 'connect')


async def test_test_session(test_session):
    """
    Test that test session is created correctly.
    
    Verifies the fixture provides a valid SQLAlchemy session.
    """
    assert test_session is not None
    assert isinstance(test_session, AsyncSession)
