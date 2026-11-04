"""
Database Models

SQLAlchemy ORM models for all database tables.
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON, CheckConstraint, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class User(Base):
    """User accounts table"""
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    username = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())


class UserSession(Base):
    """User sessions for refresh tokens"""
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


class Game(Base):
    """Games table"""
    __tablename__ = "games"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    game_mode = Column(String(50), nullable=False)
    word_length = Column(Integer, nullable=False)
    target_word = Column(String(8), nullable=False)
    status = Column(String(50), nullable=False)
    max_turns = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    __table_args__ = (CheckConstraint("word_length BETWEEN 5 AND 8"),)


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


class WordOfDayAttempt(Base):
    """Word of the Day attempts table"""
    __tablename__ = "word_of_day_attempts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    attempt_date = Column(String(10), nullable=False)
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (CheckConstraint("user_id IS NOT NULL"),)


class OutboxEvent(Base):
    """Outbox pattern events table"""
    __tablename__ = "outbox_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False)
    aggregate_id = Column(String(255), nullable=False)
    aggregate_type = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(50), nullable=False, default='pending')
    created_at = Column(DateTime, server_default=func.now())
    processed_at = Column(DateTime)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    __table_args__ = (CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')"),)
