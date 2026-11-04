"""Tests for user stats model"""
import pytest
from sqlalchemy import create_engine, inspect
from app.database.user_stats_model import Base, UserStats

def test_user_stats_model_columns():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('user_stats')]
    expected_columns = ['user_id', 'games_played', 'games_won', 'games_lost', 'current_streak', 'best_streak', 'avg_guesses_to_win', 'guess_distribution', 'updated_at']
    for col in expected_columns:
        assert col in columns
