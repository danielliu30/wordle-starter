"""Tests for word of day attempt model (PostgreSQL only)

The PostgreSQL integration tests run only when TEST_DATABASE_URL is set, e.g. against
the Compose database from inside the backend container:
    docker compose exec backend sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest --noconftest test_word_of_day_attempt_model.py'
The role needs CREATE on that database: each test runs in its own throwaway schema.
"""
import datetime
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable
from app.database.word_of_day_attempt_model import Base, Game, User, WordOfDayAttempt

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

def test_word_of_day_attempt_model_columns():
    columns = WordOfDayAttempt.__table__.columns.keys()
    expected_columns = ['id', 'user_id', 'attempt_date', 'game_id', 'created_at']
    for col in expected_columns:
        assert col in columns


def test_shares_metadata_with_users_and_games():
    assert WordOfDayAttempt.metadata is User.metadata is Game.metadata


def test_word_of_day_attempt_table_compiles_for_postgresql():
    ddl = str(CreateTable(WordOfDayAttempt.__table__).compile(dialect=postgresql.dialect()))
    assert "id UUID NOT NULL" in ddl
    assert "REFERENCES users (id) ON DELETE CASCADE" in ddl
    assert "REFERENCES games (id) ON DELETE SET NULL" in ddl
    assert "attempt_date DATE NOT NULL" in ddl
    assert "CONSTRAINT uq_wod_user_date UNIQUE (user_id, attempt_date)" in ddl


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
    attempt = WordOfDayAttempt(user_id=user.id, attempt_date=datetime.date(2026, 11, 4))
    pg_session.add(attempt)
    await pg_session.commit()
    assert isinstance(attempt.id, uuid.UUID)


@requires_postgres
@pytest.mark.asyncio
async def test_attempt_date_rejects_non_dates_on_postgresql(pg_session, user):
    await pg_session.execute(
        text("INSERT INTO word_of_day_attempts (id, user_id, attempt_date) VALUES (:id, :uid, :d)"),
        {"id": uuid.uuid4(), "uid": user.id, "d": datetime.date(2026, 11, 4)},
    )
    await pg_session.commit()
    with pytest.raises(DBAPIError):
        await pg_session.execute(
            text("INSERT INTO word_of_day_attempts (id, user_id, attempt_date) VALUES (:id, :uid, CAST(:d AS DATE))"),
            {"id": uuid.uuid4(), "uid": user.id, "d": "2026-13-40"},
        )


@requires_postgres
@pytest.mark.asyncio
async def test_one_attempt_per_user_per_day_on_postgresql(pg_session, user):
    day = datetime.date(2026, 11, 4)
    pg_session.add(WordOfDayAttempt(user_id=user.id, attempt_date=day))
    await pg_session.commit()
    pg_session.add(WordOfDayAttempt(user_id=user.id, attempt_date=day + datetime.timedelta(days=1)))
    await pg_session.commit()
    pg_session.add(WordOfDayAttempt(user_id=user.id, attempt_date=day))
    with pytest.raises(IntegrityError):
        await pg_session.commit()
