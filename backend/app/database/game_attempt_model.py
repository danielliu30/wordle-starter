"""
Game Attempt Model

SQLAlchemy ORM model for game attempts (guesses).
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, CheckConstraint, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

class GameAttempt(Base):
    """Game attempts table"""
    __tablename__ = "game_attempts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    guess = Column(String(8), nullable=False)
    feedback = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (CheckConstraint("attempt_number > 0"),)
