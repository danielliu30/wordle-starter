"""Tests for user model (PostgreSQL only)

The PostgreSQL integration tests run only when TEST_DATABASE_URL is set, e.g. against
the Compose database (not published to the host) from inside the backend container:
    docker compose exec backend sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest test_user_model.py'
The role needs CREATE on that database: each test runs in its own throwaway schema.
"""
import asyncio
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable
from app.database.user_model import Base, User

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def test_user_model_columns():
    columns = User.__table__.columns.keys()
    expected_columns = ['id', 'email', 'password_hash', 'username', 'created_at', 'updated_at']
    for col in expected_columns:
        assert col in columns


def test_user_table_compiles_for_postgresql():
    ddl = str(CreateTable(User.__table__).compile(dialect=postgresql.dialect()))
    assert "id UUID NOT NULL" in ddl


def test_account_constraints_declared():
    columns = User.__table__.c
    assert columns.email.unique
    assert not columns.email.nullable
    assert not columns.password_hash.nullable


def test_updated_at_refreshes_on_update():
    assert User.__table__.c.updated_at.onupdate is not None


requires_postgres = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="TEST_DATABASE_URL (PostgreSQL) not set"
)


@pytest_asyncio.fixture
async def pg_session():
    # Run in a throwaway schema so existing tables in the target database are never touched.
    schema = f"test_user_model_{uuid.uuid4().hex}"
    admin_engine = create_async_engine(TEST_DATABASE_URL)
    engine = create_async_engine(
        TEST_DATABASE_URL, connect_args={"server_settings": {"search_path": schema}}
    )
    async with admin_engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
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


@requires_postgres
@pytest.mark.asyncio
async def test_user_insert_and_update_on_postgresql(pg_session):
    user = User(email="a@example.com", password_hash="hash")
    pg_session.add(user)
    await pg_session.commit()
    assert isinstance(user.id, uuid.UUID)
    created = user.updated_at

    await asyncio.sleep(0.01)
    await pg_session.execute(update(User).where(User.id == user.id).values(username="alice"))
    await pg_session.commit()
    updated = (await pg_session.execute(select(User.updated_at).where(User.id == user.id))).scalar_one()
    assert updated > created


@requires_postgres
@pytest.mark.asyncio
async def test_duplicate_email_rejected_on_postgresql(pg_session):
    pg_session.add(User(email="a@example.com", password_hash="hash"))
    await pg_session.commit()
    pg_session.add(User(email="a@example.com", password_hash="other"))
    with pytest.raises(IntegrityError):
        await pg_session.commit()


@requires_postgres
@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["email", "password_hash"])
async def test_required_credentials_on_postgresql(pg_session, missing):
    values = {"email": "a@example.com", "password_hash": "hash"}
    del values[missing]
    pg_session.add(User(**values))
    with pytest.raises(IntegrityError):
        await pg_session.commit()
