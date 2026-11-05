"""Tests for user session model (PostgreSQL only)

The PostgreSQL integration tests run only when TEST_DATABASE_URL is set, e.g. against
the Compose database (not published to the host) from inside the backend container:
    docker compose exec backend sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest test_user_session_model.py'
The role needs CREATE on that database: each test runs in its own throwaway schema.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateIndex, CreateTable
from app.database.user_model import User
from app.database.user_session_model import Base, UserSession

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def test_user_session_model_columns():
    columns = UserSession.__table__.columns.keys()
    expected_columns = ['id', 'user_id', 'refresh_token_hash', 'role', 'device_info', 'created_at', 'expires_at', 'revoked_at']
    for col in expected_columns:
        assert col in columns


def test_shares_metadata_with_users_table():
    assert Base.metadata is User.metadata
    assert [t.name for t in Base.metadata.sorted_tables] == ["users", "user_sessions"]


def test_user_session_table_compiles_for_postgresql():
    ddl = str(CreateTable(UserSession.__table__).compile(dialect=postgresql.dialect()))
    assert "id UUID NOT NULL" in ddl
    assert "user_id UUID," in ddl
    assert "FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE" in ddl


def test_lookup_indexes_declared():
    indexes = {
        str(CreateIndex(index).compile(dialect=postgresql.dialect()))
        for index in UserSession.__table__.indexes
    }
    assert indexes == {
        "CREATE INDEX idx_sessions_user ON user_sessions (user_id)",
        "CREATE INDEX idx_sessions_token ON user_sessions (refresh_token_hash)",
    }


requires_postgres = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="TEST_DATABASE_URL (PostgreSQL) not set"
)


@pytest_asyncio.fixture
async def pg_session():
    # Run in a throwaway schema so existing tables in the target database are never touched.
    schema = f"test_user_session_model_{uuid.uuid4().hex}"
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


def make_session(**values):
    return UserSession(
        refresh_token_hash="hash", expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=6), **values
    )


@requires_postgres
@pytest.mark.asyncio
async def test_user_session_insert_on_postgresql(pg_session):
    user = User(email="a@example.com", password_hash="hash")
    pg_session.add(user)
    await pg_session.commit()
    session = make_session(user_id=user.id, role="user")
    pg_session.add(session)
    await pg_session.commit()
    assert isinstance(session.id, uuid.UUID)


@requires_postgres
@pytest.mark.asyncio
async def test_guest_session_insert_on_postgresql(pg_session):
    guest = make_session(role="guest")
    pg_session.add(guest)
    await pg_session.commit()
    assert guest.user_id is None
    assert isinstance(guest.id, uuid.UUID)


@requires_postgres
@pytest.mark.asyncio
async def test_unknown_user_rejected_on_postgresql(pg_session):
    pg_session.add(make_session(user_id=uuid.uuid4(), role="user"))
    with pytest.raises(IntegrityError):
        await pg_session.commit()


@requires_postgres
@pytest.mark.asyncio
@pytest.mark.parametrize("role, has_user", [("user", False), ("guest", True), ("admin", False)])
async def test_role_owner_mismatch_rejected_on_postgresql(pg_session, role, has_user):
    user_id = None
    if has_user:
        user = User(email="a@example.com", password_hash="hash")
        pg_session.add(user)
        await pg_session.commit()
        user_id = user.id
    pg_session.add(make_session(user_id=user_id, role=role))
    with pytest.raises(IntegrityError):
        await pg_session.commit()
