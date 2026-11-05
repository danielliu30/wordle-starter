"""
User Stats Model

SQLAlchemy ORM model for user statistics.
PostgreSQL only (same database for local dev and production).
"""
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, JSON, func
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
    avg_guesses_to_win = Column(Numeric(3, 2))
    # {word_length: {guesses: count}}; plain JSON doesn't track in-place edits, so update it
    # through record_guess_distribution, which assigns a new object.
    guess_distribution = Column(JSON, default=dict)
    updated_at = Column(DateTime, server_default=func.now())

    def record_guess_distribution(self, word_length: int, guesses: int) -> None:
        """Count a win of a word_length-letter game in the given number of guesses."""
        distribution = {length: dict(counts) for length, counts in (self.guess_distribution or {}).items()}
        counts = distribution.setdefault(str(word_length), {})
        counts[str(guesses)] = counts.get(str(guesses), 0) + 1
        self.guess_distribution = distribution
