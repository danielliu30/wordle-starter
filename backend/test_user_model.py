"""Tests for user model"""
import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable
from app.database.user_model import Base, User


def test_user_model_columns():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('users')]
    expected_columns = ['id', 'email', 'password_hash', 'username', 'created_at', 'updated_at']
    for col in expected_columns:
        assert col in columns


def test_user_insert_and_update_on_sqlite():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(email="a@example.com", password_hash="hash")
        session.add(user)
        session.commit()
        assert uuid.UUID(user.id)

        user.updated_at = datetime(2000, 1, 1)
        session.commit()
        user.username = "alice"
        session.commit()
        session.refresh(user)
        assert user.updated_at > datetime(2000, 1, 1)


def test_user_table_compiles_for_postgresql():
    ddl = str(CreateTable(User.__table__).compile(dialect=postgresql.dialect()))
    assert "id VARCHAR(36) NOT NULL" in ddl
