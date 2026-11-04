"""Tests for outbox event model"""
import pytest
from sqlalchemy import create_engine, inspect
from app.database.outbox_event_model import Base, OutboxEvent

def test_outbox_event_model_columns():
    engine = create_engine("postgresql://user:password@localhost:5432/test")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('outbox_events')]
    expected_columns = ['id', 'event_type', 'aggregate_id', 'aggregate_type', 'payload', 'status', 'created_at', 'processed_at', 'error_message', 'retry_count']
    for col in expected_columns:
        assert col in columns
