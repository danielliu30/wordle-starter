"""Tests for word of day attempt model"""
import pytest
from sqlalchemy import create_engine, inspect
from app.database.word_of_day_attempt_model import Base, WordOfDayAttempt

def test_word_of_day_attempt_model_columns():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('word_of_day_attempts')]
    expected_columns = ['id', 'user_id', 'attempt_date', 'game_id', 'created_at']
    for col in expected_columns:
        assert col in columns
