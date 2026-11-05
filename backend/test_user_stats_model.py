"""Tests for user stats model (PostgreSQL only)

The PostgreSQL integration tests run only when TEST_DATABASE_URL is set, e.g. against
the Compose database (not published to the host) from inside the backend container:
    docker compose exec backend sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest test_user_stats_model.py'
The role needs CREATE on that database: each test runs in its own throwaway schema.
"""
import asyncio
import os
import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable
from app.database.user_model import User
from app.database.user_stats_model import Base, UserStats

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def test_user_stats_model_columns():
    columns = UserStats.__table__.columns.keys()
    expected_columns = ['user_id', 'games_played', 'games_won', 'games_lost', 'current_streak', 'best_streak', 'avg_guesses_to_win', 'guess_distribution', 'updated_at']
    for col in expected_columns:
        assert col in columns


def test_shares_metadata_with_users_table():
    assert Base.metadata is User.metadata
    assert [t.name for t in Base.metadata.sorted_tables] == ["users", "user_stats"]


def test_user_stats_table_compiles_for_postgresql():
    ddl = str(CreateTable(UserStats.__table__).compile(dialect=postgresql.dialect()))
    assert "user_id UUID NOT NULL" in ddl
    assert "FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE" in ddl
    assert "avg_guesses_to_win NUMERIC(3, 2)" in ddl


requires_postgres = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="TEST_DATABASE_URL (PostgreSQL) not set"
)


@pytest_asyncio.fixture
async def pg_sessionmaker():
    # Run in a throwaway schema so existing tables in the target database are never touched.
    schema = f"test_user_stats_model_{uuid.uuid4().hex}"
    admin_engine = create_async_engine(TEST_DATABASE_URL)
    async with admin_engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(
        TEST_DATABASE_URL, connect_args={"server_settings": {"search_path": schema}}
    )
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()
        async with admin_engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin_engine.dispose()


@pytest_asyncio.fixture
async def pg_session(pg_sessionmaker):
    async with pg_sessionmaker() as session:
        yield session


async def add_stats(pg_session, **values):
    user = User(email="a@example.com", password_hash="hash")
    pg_session.add(user)
    await pg_session.commit()
    stats = UserStats(user_id=user.id, **values)
    pg_session.add(stats)
    await pg_session.commit()
    return stats


@requires_postgres
@pytest.mark.asyncio
async def test_user_stats_insert_on_postgresql(pg_session):
    stats = await add_stats(pg_session)
    assert stats.games_played == 0


@requires_postgres
@pytest.mark.asyncio
async def test_fractional_avg_guesses_round_trip_on_postgresql(pg_session):
    stats = await add_stats(pg_session, avg_guesses_to_win=Decimal("3.5"))
    stored = (await pg_session.execute(
        select(UserStats.avg_guesses_to_win).where(UserStats.user_id == stats.user_id)
    )).scalar_one()
    assert stored == Decimal("3.50")


async def read_distribution(session, user_id):
    return (await session.execute(
        select(UserStats.guess_distribution).where(UserStats.user_id == user_id)
    )).scalar_one()


@requires_postgres
@pytest.mark.asyncio
async def test_guess_distribution_increments_on_postgresql(pg_session):
    stats = await add_stats(pg_session, guess_distribution={"5": {"3": 1}})
    await pg_session.execute(UserStats.increment_guess_distribution(stats.user_id, 5, 3))
    await pg_session.execute(UserStats.increment_guess_distribution(stats.user_id, 6, 4))
    await pg_session.commit()
    assert await read_distribution(pg_session, stats.user_id) == {"5": {"3": 2}, "6": {"4": 1}}


@requires_postgres
@pytest.mark.asyncio
async def test_guess_distribution_increments_from_null_on_postgresql(pg_session):
    stats = await add_stats(pg_session, guess_distribution=None)
    await pg_session.execute(UserStats.increment_guess_distribution(stats.user_id, 5, 3))
    await pg_session.commit()
    assert await read_distribution(pg_session, stats.user_id) == {"5": {"3": 1}}


@requires_postgres
@pytest.mark.asyncio
async def test_concurrent_guess_distribution_increments_on_postgresql(pg_sessionmaker):
    async with pg_sessionmaker() as setup:
        stats = await add_stats(setup, guess_distribution={"5": {"3": 1}})
    async with pg_sessionmaker() as first, pg_sessionmaker() as second:
        await first.execute(UserStats.increment_guess_distribution(stats.user_id, 5, 3))

        async def second_win():
            await second.execute(UserStats.increment_guess_distribution(stats.user_id, 5, 3))
            await second.commit()

        # The second update waits on the first one's row lock, then applies to the committed value.
        pending = asyncio.create_task(second_win())
        await asyncio.sleep(0.1)
        assert not pending.done()
        await first.commit()
        await pending
        assert await read_distribution(first, stats.user_id) == {"5": {"3": 3}}


@requires_postgres
@pytest.mark.asyncio
async def test_updated_at_refreshes_on_increment_on_postgresql(pg_session):
    stats = await add_stats(pg_session)
    created = (await pg_session.execute(
        select(UserStats.updated_at).where(UserStats.user_id == stats.user_id)
    )).scalar_one()
    await asyncio.sleep(0.01)
    await pg_session.execute(UserStats.increment_guess_distribution(stats.user_id, 5, 3))
    await pg_session.commit()
    updated = (await pg_session.execute(
        select(UserStats.updated_at).where(UserStats.user_id == stats.user_id)
    )).scalar_one()
    assert updated > created
