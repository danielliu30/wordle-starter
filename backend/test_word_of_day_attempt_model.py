"""Tests for word of day attempt model (PostgreSQL only)

The PostgreSQL integration tests run only when TEST_DATABASE_URL is set, e.g. against
the Compose database from inside the backend container:
    docker compose exec backend sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest --noconftest test_word_of_day_attempt_model.py'
The role needs CREATE on that database: each test runs in its own throwaway schema.
"""
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import Column, Table, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable
from app.database.word_of_day_attempt_model import Base, User, WordOfDayAttempt

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

# The games model is not on this branch yet; register a minimal stand-in so the
# game_id foreign key resolves when creating the schema.
if "games" not in Base.metadata.tables:
    Table("games", Base.metadata, Column("id", postgresql.UUID(as_uuid=True), primary_key=True))


def test_word_of_day_attempt_model_columns():
    columns = WordOfDayAttempt.__table__.columns.keys()
    expected_columns = ['id', 'user_id', 'attempt_date', 'game_id', 'created_at']
    for col in expected_columns:
        assert col in columns


def test_shares_metadata_with_users():
    assert WordOfDayAttempt.metadata is User.metadata


def test_word_of_day_attempt_table_compiles_for_postgresql():
    ddl = str(CreateTable(WordOfDayAttempt.__table__).compile(dialect=postgresql.dialect()))
    assert "id UUID NOT NULL" in ddl
    assert "REFERENCES users (id) ON DELETE CASCADE" in ddl
    assert "REFERENCES games (id) ON DELETE SET NULL" in ddl


requires_postgres = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="TEST_DATABASE_URL (PostgreSQL) not set"
)


@pytest_asyncio.fixture
async def pg_session():
    # Run in a throwaway schema so existing tables in the target database are never touched.
    schema = f"test_wod_attempt_model_{uuid.uuid4().hex}"
    admin_engine = create_async_engine(TEST_DATABASE_URL)
    async with admin_engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(
        TEST_DATABASE_URL, connect_args={"server_settings": {"search_path": schema}}
    )
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            yield session
    finally:
        await engine.dispose()
        async with admin_engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin_engine.dispose()


@pytest_asyncio.fixture
async def user(pg_session):
    user = User(email="a@example.com", password_hash="hash")
    pg_session.add(user)
    await pg_session.commit()
    return user


@requires_postgres
@pytest.mark.asyncio
async def test_attempt_insert_on_postgresql(pg_session, user):
    attempt = WordOfDayAttempt(user_id=user.id, attempt_date="2026-11-04")
    pg_session.add(attempt)
    await pg_session.commit()
    assert isinstance(attempt.id, uuid.UUID)
