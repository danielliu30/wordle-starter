"""
Test Environment Configuration

Provides test database and Redis configuration for running tests.
Uses in-memory SQLite for speed and isolation.
"""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.database.models import Base


@pytest.fixture(scope="session")
async def test_engine():
    """
    Create an in-memory SQLite database for testing.
    
    Using in-memory SQLite ensures:
    - Tests run quickly (no disk I/O)
    - Tests are isolated (each test gets fresh database)
    - No cleanup needed (database is in-memory, discarded after test)
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup is automatic (in-memory database is discarded)


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
        
        # Rollback any changes (database is in-memory, so this is optional)
        await session.rollback()


@pytest.fixture
def test_redis():
    """
    Create a mock Redis client for testing.
    
    For now, returns None. Will be replaced with actual Redis mock
    when Redis dependency is added.
    """
    # TODO: Add Redis mock when Redis is integrated
    return None
