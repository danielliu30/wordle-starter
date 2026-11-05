"""
User Stats Model

SQLAlchemy ORM model for user statistics.
PostgreSQL only (same database for local dev and production).
"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID

# Share the users table's metadata so the user_id foreign key resolves.
from app.database.user_model import Base, User  # noqa: F401


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
