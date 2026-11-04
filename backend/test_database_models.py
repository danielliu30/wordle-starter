"""
Unit tests for database models

Tests the SQLAlchemy models to ensure:
- Models are correctly defined
- Constraints are properly set
- Foreign keys are configured correctly
- Tables can be created without errors
"""
import pytest
from sqlalchemy import create_engine, inspect
from app.database.models import Base, User, UserSession, Game, GameAttempt, UserStats, WordOfDayAttempt, OutboxEvent


def test_user_model_columns():
    """
    Test that User model has expected columns.
    
    Verifies the model structure matches requirements.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    expected_columns = ['id', 'email', 'password_hash', 'username', 'created_at', 'updated_at']
    for col in expected_columns:
        assert col in columns, f"Column {col} not found in User model"


def test_game_model_word_length_constraint():
    """
    Test that Game model has word_length constraint.
    
    Ensures word length is between 5 and 8.
    """
    assert Game.__table_args__[0].sqltext == "word_length BETWEEN 5 AND 8"


def test_foreign_keys():
    """
    Test that foreign keys are properly defined.
    
    Verifies referential integrity constraints.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    inspector = inspect(engine)
    
    # Check game_attempts foreign key
    game_attempts_fks = [fk['constrained_columns'] for fk in inspector.get_foreign_keys('game_attempts')]
    assert any('game_id' in fk for fk in game_attempts_fks), "game_attempts should have foreign key on game_id"
    
    # Check games foreign key
    games_fks = [fk['constrained_columns'] for fk in inspector.get_foreign_keys('games')]
    assert any('user_id' in fk for fk in games_fks), "games should have foreign key on user_id"


def test_outbox_event_status_constraint():
    """
    Test that OutboxEvent has status constraint.
    
    Ensures status is one of: pending, processing, completed, failed
    """
    assert OutboxEvent.__table_args__[0].sqltext == "status IN ('pending', 'processing', 'completed', 'failed')"


def test_user_session_role_constraint():
    """
    Test that UserSession has role constraint.
    
    Ensures role is either 'user' or 'guest'.
    """
    assert UserSession.__table_args__[0].sqltext == "role IN ('user', 'guest')"


def test_models_can_create_tables():
    """
    Test that all models can create tables without errors.
    
    Verifies there are no issues with model definitions.
    """
    engine = create_engine("sqlite:///:memory:")
    
    # This will raise an error if there are any issues with model definitions
    Base.metadata.create_all(engine)
    
    # Verify all tables were created
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    expected_tables = [
        'users',
        'user_sessions',
        'games',
        'game_attempts',
        'user_stats',
        'word_of_day_attempts',
        'outbox_events'
    ]
    
    for table in expected_tables:
        assert table in table_names, f"Table {table} not created"
