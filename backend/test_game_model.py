"""Tests for game model"""
import pytest
from sqlalchemy import create_engine, inspect
from app.database.game_model import Base, Game

def test_game_model_columns():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('games')]
    expected_columns = ['id', 'user_id', 'game_mode', 'word_length', 'target_word', 'status', 'max_turns', 'created_at', 'completed_at']
    for col in expected_columns:
        assert col in columns
