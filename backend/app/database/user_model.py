"""
User Model

SQLAlchemy ORM model for user accounts.
Database-agnostic (works with SQLite and PostgreSQL).
"""
from sqlalchemy import Column, String, Integer, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class User(Base):
    """
    User accounts table.
    
    Stores user credentials and profile information.
    Password is stored as a bcrypt hash, never in plain text.
    """
    __tablename__ = "users"
    
    # Primary key using String UUID for database compatibility
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Email is unique and indexed for fast lookups
    email = Column(String(255), unique=True, nullable=False, index=True)
    
    # Password hash using bcrypt (never store plain text)
    password_hash = Column(String(255), nullable=False)
    
    # Optional username for display
    username = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
