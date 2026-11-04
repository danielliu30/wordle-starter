"""Tests for database models"""
import pytest
from sqlalchemy import create_engine, inspect
from app.database.models import Base, User, UserSession, Game, GameAttempt, UserStats, WordOfDayAttempt, OutboxEvent


def test_user_model_columns():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('users')]
    expected_columns = ['id', 'email', 'password_hash', 'username', 'created_at', 'updated_at']
    for col in expected_columns:
        assert col in columns


def test_game_model_word_length_constraint():
    assert Game.__table_args__[0].sqltext == "word_length BETWEEN 5 AND 8"


def test_foreign_keys():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    game_attempts_fks = [fk['constrained_columns'] for fk in inspector.get_foreign_keys('game_attempts')]
    assert any('game_id' in fk for fk in game_attempts_fks)


def test_models_can_create_tables():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    expected_tables = ['users', 'user_sessions', 'games', 'game_attempts', 'user_stats', 'word_of_day_attempts', 'outbox_events']
    for table in expected_tables:
        assert table in table_names
