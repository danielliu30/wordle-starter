"""
Test Environment Configuration

Provides test database fixtures backed by PostgreSQL.

Set TEST_DATABASE_URL to a PostgreSQL connection string (e.g. the Compose
database). Each test gets its own throwaway schema, so existing tables in
the target database are never touched. When TEST_DATABASE_URL is not set,
the database fixtures are skipped.
"""
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.models import Base  # noqa: F401 - registers all tables

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

requires_postgres = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="TEST_DATABASE_URL (PostgreSQL) not set"
)


@pytest_asyncio.fixture
async def test_engine():
    """
    Create a fresh database schema for each test.

    Using a per-test schema ensures:
    - Tests are isolated (data committed by one test is never seen by another)
    - No cleanup needed beyond dropping the schema
    """
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL (PostgreSQL) not set")

    schema = f"test_{uuid.uuid4().hex}"
    admin_engine = create_async_engine(TEST_DATABASE_URL)
    async with admin_engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))

    engine = create_async_engine(
        TEST_DATABASE_URL, connect_args={"server_settings": {"search_path": schema}}
    )
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()
        async with admin_engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin_engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine):
    """
    Create a test database session for a single test.

    The session is bound to the test's own schema, so commits made
    inside the test cannot leak into other tests.
    """
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)

    async with async_session() as session:
        yield session
        await session.rollback()
