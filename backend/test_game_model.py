"""Tests for game model (PostgreSQL only)

The PostgreSQL integration tests run only when TEST_DATABASE_URL is set, e.g. against
the Compose database (not published to the host) from inside the backend container:
    docker compose exec backend sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest test_game_model.py'
The role needs CREATE on that database: each test runs in its own throwaway schema.
"""
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateIndex, CreateTable
from app.database.user_model import User
from app.database.game_model import Base, Game

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def test_game_model_columns():
    columns = Game.__table__.columns.keys()
    expected_columns = ['id', 'user_id', 'game_mode', 'word_length', 'target_word', 'status', 'max_turns', 'created_at', 'completed_at']
    for col in expected_columns:
        assert col in columns


def test_shares_metadata_with_users_table():
    assert Base.metadata is User.metadata
    tables = [t.name for t in Base.metadata.sorted_tables]
    assert tables.index("users") < tables.index("games")


def test_game_table_compiles_for_postgresql():
    ddl = str(CreateTable(Game.__table__).compile(dialect=postgresql.dialect()))
    assert "id UUID NOT NULL" in ddl
    assert "user_id UUID," in ddl
    assert "FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE" in ddl
    assert "CHECK (word_length BETWEEN 5 AND 8)" in ddl


def test_game_history_index_compiles_for_postgresql():
    (index,) = Game.__table__.indexes
    ddl = str(CreateIndex(index).compile(dialect=postgresql.dialect()))
    assert ddl == "CREATE INDEX idx_games_user_created ON games (user_id, created_at DESC)"


requires_postgres = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="TEST_DATABASE_URL (PostgreSQL) not set"
)


@pytest_asyncio.fixture
async def pg_session():
    # Run in a throwaway schema so existing tables in the target database are never touched.
    schema = f"test_game_model_{uuid.uuid4().hex}"
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


def make_game(**values):
    defaults = {"game_mode": "custom", "word_length": 5, "target_word": "crane", "status": "in_progress", "max_turns": 6}
    return Game(**{**defaults, **values})


@requires_postgres
@pytest.mark.asyncio
async def test_game_insert_on_postgresql(pg_session):
    user = User(email="a@example.com", password_hash="hash")
    pg_session.add(user)
    await pg_session.commit()
    game = make_game(user_id=user.id)
    pg_session.add(game)
    await pg_session.commit()
    assert isinstance(game.id, uuid.UUID)


@requires_postgres
@pytest.mark.asyncio
async def test_unknown_user_rejected_on_postgresql(pg_session):
    pg_session.add(make_game(user_id=uuid.uuid4()))
    with pytest.raises(IntegrityError):
        await pg_session.commit()


@requires_postgres
@pytest.mark.asyncio
@pytest.mark.parametrize("word_length", [4, 9])
async def test_word_length_out_of_range_rejected_on_postgresql(pg_session, word_length):
    pg_session.add(make_game(word_length=word_length))
    with pytest.raises(IntegrityError):
        await pg_session.commit()
