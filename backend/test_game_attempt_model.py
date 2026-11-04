"""Tests for game attempt model"""
import pytest
from sqlalchemy import create_engine, inspect
from app.database.game_attempt_model import Base, GameAttempt

def test_game_attempt_model_columns():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('game_attempts')]
    expected_columns = ['id', 'game_id', 'attempt_number', 'guess', 'feedback', 'created_at']
    for col in expected_columns:
        assert col in columns
