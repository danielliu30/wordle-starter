"""Tests for user model (PostgreSQL only)"""
import asyncio
import os
import uuid

import pytest
from sqlalchemy import select, text, update
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


def test_updated_at_refreshes_on_update():
    assert User.__table__.c.updated_at.onupdate is not None


@pytest.mark.asyncio
@pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL (PostgreSQL) not set")
async def test_user_insert_and_update_on_postgresql():
    # Run in a throwaway schema so existing tables in the target database are never touched.
    schema = f"test_user_model_{uuid.uuid4().hex}"
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
            user = User(email="a@example.com", password_hash="hash")
            session.add(user)
            await session.commit()
            assert isinstance(user.id, uuid.UUID)
            created = user.updated_at

            await asyncio.sleep(0.01)
            await session.execute(update(User).where(User.id == user.id).values(username="alice"))
            await session.commit()
            updated = (await session.execute(select(User.updated_at).where(User.id == user.id))).scalar_one()
            assert updated > created
    finally:
        await engine.dispose()
        async with admin_engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin_engine.dispose()
