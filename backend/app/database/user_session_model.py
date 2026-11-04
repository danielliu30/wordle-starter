"""
User Session Model

SQLAlchemy ORM model for user sessions (refresh tokens).
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, CheckConstraint, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import UUID
import uuid
import uuid

Base = declarative_base()


class UserSession(Base):
    """
    User sessions for refresh tokens.
    Stores refresh token sessions for JWT authentication.
    Tokens are hashed for security.
    """
    __tablename__ = "user_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    device_info = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime)
    __table_args__ = (CheckConstraint("role IN ('user', 'guest')"),)
