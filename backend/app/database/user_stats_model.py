"""
User Stats Model

SQLAlchemy ORM model for user statistics.
PostgreSQL only (same database for local dev and production).
"""
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, Text, Update, cast, func, literal, update
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

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
    # {word_length: {guesses: count}}
    guess_distribution = Column(JSONB, default=dict)
    updated_at = Column(DateTime, server_default=func.now())

    @classmethod
    def increment_guess_distribution(cls, user_id, word_length: int, guesses: int) -> Update:
        """UPDATE counting a win of a word_length-letter game in the given number of guesses.

        The count is incremented in the database against the row's current value, so concurrent
        wins are not lost (unlike a read-modify-write of the loaded dict).
        """
        def object_or_empty(value):
            # Treat SQL NULL and JSON null (how a None value is stored) as {}.
            return func.coalesce(func.nullif(value, cast(literal("null"), JSONB)), cast(literal("{}"), JSONB))

        length, guess = str(word_length), str(guesses)
        current = object_or_empty(cls.guess_distribution)
        with_length = func.jsonb_set(
            current, cast(literal([length]), ARRAY(Text)), object_or_empty(current[length])
        )
        count = func.coalesce(current[length][guess].astext.cast(Integer), 0) + 1
        return (
            update(cls)
            .where(cls.user_id == user_id)
            .values(guess_distribution=func.jsonb_set(with_length, cast(literal([length, guess]), ARRAY(Text)), func.to_jsonb(count)))
        )
