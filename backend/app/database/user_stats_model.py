"""
User Stats Model

SQLAlchemy ORM model for user statistics.
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import UUID
import uuid
import uuid

Base = declarative_base()

class UserStats(Base):
    """User statistics table"""
    __tablename__ = "user_stats"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    games_played = Column(Integer, default=0)
    games_won = Column(Integer, default=0)
    games_lost = Column(Integer, default=0)
    current_streak = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)
    avg_guesses_to_win = Column(Integer)
    guess_distribution = Column(JSON, default={})
    updated_at = Column(DateTime, server_default=func.now())
