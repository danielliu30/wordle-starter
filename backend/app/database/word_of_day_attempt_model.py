"""
Word of Day Attempt Model

SQLAlchemy ORM model for Word of the Day attempts.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, CheckConstraint, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import UUID
import uuid
import uuid

Base = declarative_base()

class WordOfDayAttempt(Base):
    """Word of the Day attempts table"""
    __tablename__ = "word_of_day_attempts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    attempt_date = Column(String(10), nullable=False)
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (CheckConstraint("user_id IS NOT NULL"),)
