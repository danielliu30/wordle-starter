"""Tests for user session model"""
import pytest
from sqlalchemy import create_engine, inspect
from app.database.user_session_model import Base, UserSession

def test_user_session_model_columns():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('user_sessions')]
    expected_columns = ['id', 'user_id', 'refresh_token_hash', 'role', 'device_info', 'created_at', 'expires_at', 'revoked_at']
    for col in expected_columns:
        assert col in columns
