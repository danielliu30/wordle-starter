"""
Game Attempt Model

SQLAlchemy ORM model for game attempts (guesses).
PostgreSQL only (same database for local dev and production).
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, CheckConstraint, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
import uuid

# Share the games table's metadata so the game_id foreign key resolves.
from app.database.game_model import Base, Game  # noqa: F401


class GameAttempt(Base):
    """Game attempts table"""
    __tablename__ = "game_attempts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    guess = Column(String(8), nullable=False)
    feedback = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        CheckConstraint("attempt_number > 0"),
        UniqueConstraint("game_id", "attempt_number", name="uq_game_attempts_game_turn"),
    )
