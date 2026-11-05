"""Tests for game attempt model (PostgreSQL only)

The PostgreSQL integration tests run only when TEST_DATABASE_URL is set, e.g. against
the Compose database (not published to the host) from inside the backend container:
    docker compose exec backend sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest test_game_attempt_model.py'
The role needs CREATE on that database: each test runs in its own throwaway schema.
"""
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable
from app.database.game_model import Game
from app.database.game_attempt_model import Base, GameAttempt

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def test_game_attempt_model_columns():
    columns = GameAttempt.__table__.columns.keys()
    expected_columns = ['id', 'game_id', 'attempt_number', 'guess', 'feedback', 'created_at']
    for col in expected_columns:
        assert col in columns


def test_shares_metadata_with_games_table():
    assert Base.metadata is Game.metadata
    assert "games" in Base.metadata.tables


def test_game_attempt_table_compiles_for_postgresql():
    ddl = str(CreateTable(GameAttempt.__table__).compile(dialect=postgresql.dialect()))
    assert "id UUID NOT NULL" in ddl
    assert "game_id UUID NOT NULL" in ddl
    assert "FOREIGN KEY(game_id) REFERENCES games (id) ON DELETE CASCADE" in ddl
    assert "CHECK (attempt_number > 0)" in ddl
    assert "feedback JSONB NOT NULL" in ddl
    assert "CONSTRAINT uq_game_attempts_game_turn UNIQUE (game_id, attempt_number)" in ddl


requires_postgres = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="TEST_DATABASE_URL (PostgreSQL) not set"
)


@pytest_asyncio.fixture
async def pg_session():
    # Run in a throwaway schema so existing tables in the target database are never touched.
    schema = f"test_game_attempt_model_{uuid.uuid4().hex}"
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
async def game(pg_session):
    game = Game(game_mode="custom", word_length=5, target_word="crane", status="in_progress", max_turns=6)
    pg_session.add(game)
    await pg_session.commit()
    return game


def make_attempt(game_id, **values):
    defaults = {
        "attempt_number": 1,
        "guess": "slate",
        "feedback": ["absent", "absent", "correct", "absent", "correct"],
    }
    return GameAttempt(game_id=game_id, **{**defaults, **values})


@requires_postgres
@pytest.mark.asyncio
async def test_attempt_insert_on_postgresql(pg_session, game):
    attempt = make_attempt(game.id)
    pg_session.add(attempt)
    await pg_session.commit()
    stored = (await pg_session.execute(select(GameAttempt).where(GameAttempt.id == attempt.id))).scalar_one()
    assert isinstance(stored.id, uuid.UUID)
    assert stored.game_id == game.id
    assert stored.feedback[2] == "correct"
    assert stored.created_at is not None


@requires_postgres
@pytest.mark.asyncio
async def test_duplicate_turn_rejected_on_postgresql(pg_session, game):
    pg_session.add(make_attempt(game.id, attempt_number=1))
    await pg_session.commit()
    pg_session.add(make_attempt(game.id, attempt_number=1, guess="crane"))
    with pytest.raises(IntegrityError):
        await pg_session.commit()


@requires_postgres
@pytest.mark.asyncio
async def test_non_positive_attempt_number_rejected_on_postgresql(pg_session, game):
    pg_session.add(make_attempt(game.id, attempt_number=0))
    with pytest.raises(IntegrityError):
        await pg_session.commit()


@requires_postgres
@pytest.mark.asyncio
async def test_unknown_game_rejected_on_postgresql(pg_session):
    pg_session.add(make_attempt(uuid.uuid4()))
    with pytest.raises(IntegrityError):
        await pg_session.commit()
