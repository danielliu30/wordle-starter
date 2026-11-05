"""
Word of Day Attempt Model

SQLAlchemy ORM model for Word of the Day attempts.
PostgreSQL only (same database for local dev and production).
"""
from sqlalchemy import Column, Date, DateTime, ForeignKey, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID
import uuid

# Share the users table's metadata so the user_id foreign key resolves.
from app.database.user_model import Base, User  # noqa: F401


class WordOfDayAttempt(Base):
    """Word of the Day attempts table"""
    __tablename__ = "word_of_day_attempts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    attempt_date = Column(Date, nullable=False)
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (CheckConstraint("user_id IS NOT NULL"),)
