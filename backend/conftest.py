"""
Test Environment Configuration

Provides test database configuration for running tests.
Uses in-memory SQLite for speed and isolation.
"""
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database.models import Base


@pytest_asyncio.fixture
async def test_engine():
    """
    Create a fresh in-memory SQLite database for each test.

    Using a per-test in-memory database ensures:
    - Tests run quickly (no disk I/O)
    - Tests are isolated (data committed by one test is never seen by another)
    - No cleanup needed beyond disposing the engine
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine):
    """
    Create a test database session for a single test.

    The session is bound to the test's own database, so commits made
    inside the test cannot leak into other tests.
    """
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)

    async with async_session() as session:
        yield session
        await session.rollback()
