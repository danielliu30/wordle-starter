"""Tests for outbox event model (PostgreSQL only)

The PostgreSQL integration tests run only when TEST_DATABASE_URL is set, e.g. against
the Compose database (not published to the host) from inside the backend container:
    docker compose exec backend sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest test_outbox_event_model.py'
The role needs CREATE on that database: each test runs in its own throwaway schema.
"""
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateIndex, CreateTable
from app.database.outbox_event_model import Base, OutboxEvent

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

EXPECTED_COLUMNS = ['id', 'event_type', 'aggregate_id', 'aggregate_type', 'payload', 'status', 'created_at', 'processed_at', 'error_message', 'retry_count']


def test_outbox_event_model_columns():
    columns = OutboxEvent.__table__.columns.keys()
    for col in EXPECTED_COLUMNS:
        assert col in columns


def test_outbox_table_compiles_for_postgresql():
    ddl = str(CreateTable(OutboxEvent.__table__).compile(dialect=postgresql.dialect()))
    assert "id UUID NOT NULL" in ddl
    assert "payload JSONB NOT NULL" in ddl


def test_outbox_indexes_compile_for_postgresql():
    ddl = sorted(
        str(CreateIndex(index).compile(dialect=postgresql.dialect()))
        for index in OutboxEvent.__table__.indexes
    )
    assert ddl == [
        "CREATE INDEX idx_outbox_aggregate ON outbox_events (aggregate_type, aggregate_id)",
        "CREATE INDEX idx_outbox_status_created ON outbox_events (status, created_at)",
    ]


requires_postgres = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="TEST_DATABASE_URL (PostgreSQL) not set"
)


@pytest_asyncio.fixture
async def pg_engine():
    # Run in a throwaway schema so existing tables in the target database are never touched.
    schema = f"test_outbox_event_model_{uuid.uuid4().hex}"
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
async def pg_session(pg_engine):
    async with async_sessionmaker(pg_engine, expire_on_commit=False)() as session:
        yield session


@requires_postgres
@pytest.mark.asyncio
async def test_outbox_table_created_on_postgresql(pg_engine):
    async with pg_engine.connect() as conn:
        columns = await conn.run_sync(
            lambda sync_conn: [col['name'] for col in inspect(sync_conn).get_columns('outbox_events')]
        )
    for col in EXPECTED_COLUMNS:
        assert col in columns


@requires_postgres
@pytest.mark.asyncio
async def test_outbox_event_insert_and_lookup_on_postgresql(pg_session):
    event = OutboxEvent(
        event_type="game_completed", aggregate_id="game-1", aggregate_type="game", payload={"won": True}
    )
    pg_session.add(event)
    await pg_session.commit()
    assert isinstance(event.id, uuid.UUID)
    assert event.status == "pending"
    assert event.retry_count == 0

    found = (await pg_session.execute(select(OutboxEvent).where(OutboxEvent.id == event.id))).scalar_one()
    assert found.payload == {"won": True}


@requires_postgres
@pytest.mark.asyncio
async def test_invalid_status_rejected_on_postgresql(pg_session):
    pg_session.add(OutboxEvent(
        event_type="game_completed", aggregate_id="game-1", aggregate_type="game", payload={}, status="bogus"
    ))
    with pytest.raises(IntegrityError):
        await pg_session.commit()
