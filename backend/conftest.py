"""
Test Environment Configuration

Provides test database configuration for running tests.
Uses PostgreSQL for consistency with production.
"""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import settings
from app.database.models import Base


@pytest.fixture(scope="session")
async def test_engine():
    """
    Create a PostgreSQL database for testing.
    
    Uses the same database as production for consistency.
    Tests should be run against a test database, not production.
    """
    engine = create_async_engine(settings.database_url)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def test_session(test_engine):
    """
    Create a test database session for a single test.
    
    Each test gets a fresh session to ensure isolation.
    Session is automatically rolled back after test.
    """
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        
        # Rollback any changes
        await session.rollback()
