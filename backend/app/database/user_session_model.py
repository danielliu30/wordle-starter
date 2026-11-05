"""
User Session Model

SQLAlchemy ORM model for user sessions (refresh tokens).
PostgreSQL only (same database for local dev and production).
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, CheckConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID
import uuid

# Share the users table's metadata so the user_id foreign key resolves.
from app.database.user_model import Base, User  # noqa: F401


class UserSession(Base):
    """
    User sessions for refresh tokens.
    Stores refresh token sessions for JWT authentication.
    Tokens are hashed for security.
    Guest sessions have no users row: user_id is NULL and the session id is the guest's id.
    """
    __tablename__ = "user_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    refresh_token_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    device_info = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime)
    __table_args__ = (
        CheckConstraint(
            "(role = 'user' AND user_id IS NOT NULL) OR (role = 'guest' AND user_id IS NULL)",
            name="ck_user_sessions_role_owner",
        ),
        Index("idx_sessions_user", "user_id"),
        Index("idx_sessions_token", "refresh_token_hash"),
    )
