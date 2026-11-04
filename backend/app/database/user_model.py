"""
User Model

SQLAlchemy ORM model for user accounts.
PostgreSQL only (same database for local dev and production).
"""
from sqlalchemy import Column, String, Integer, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class User(Base):
    """
    User accounts table.
    
    Stores user credentials and profile information.
    Password is stored as a bcrypt hash, never in plain text.
    """
    __tablename__ = "users"
    
    # Primary key using PostgreSQL UUID
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Email is unique and indexed for fast lookups
    email = Column(String(255), unique=True, nullable=False, index=True)
    
    # Password hash using bcrypt (never store plain text)
    password_hash = Column(String(255), nullable=False)
    
    # Optional username for display
    username = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
