"""
Database Models

SQLAlchemy ORM models for all database tables.
These define the database schema and relationships.
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON, CheckConstraint, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class User(Base):
    """
    User accounts table.
    
    Stores user credentials and profile information.
    Password is stored as a bcrypt hash, never in plain text.
    """
    __tablename__ = "users"
    
    # Primary key using UUID for security and uniqueness
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Email is unique and indexed for fast lookups
    email = Column(String(255), unique=True, nullable=False, index=True)
    
    # Password hash using bcrypt (never store plain text)
    password_hash = Column(String(255), nullable=False)
    
    # Optional username for display
    username = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())


class UserSession(Base):
    """
    User sessions for refresh tokens.
    
    Stores refresh token sessions for JWT authentication.
    Tokens are hashed for security.
    Supports both regular users and guest sessions.
    """
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to users table, cascade delete if user is deleted
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Hashed refresh token (never store plain token)
    refresh_token_hash = Column(String(255), nullable=False)
    
    # Role: 'user' for authenticated users, 'guest' for anonymous sessions
    role = Column(String(50), nullable=False)
    
    # Device info for session tracking (user agent, IP, etc.)
    device_info = Column(JSON)
    
    # Session lifecycle timestamps
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime)
    
    # Constraint to ensure role is either 'user' or 'guest'
    __table_args__ = (CheckConstraint("role IN ('user', 'guest')"),)


class Game(Base):
    """
    Games table.
    
    Stores game state and metadata.
    Supports multiple game modes: word_of_day, custom, practice.
    """
    __tablename__ = "games"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to users table, cascade delete if user is deleted
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    
    # Game mode: 'word_of_day', 'custom', or 'practice'
    game_mode = Column(String(50), nullable=False)
    
    # Word length (5-8 letters)
    word_length = Column(Integer, nullable=False)
    
    # The target word (the answer)
    target_word = Column(String(8), nullable=False)
    
    # Game status: 'in_progress', 'won', or 'lost'
    status = Column(String(50), nullable=False)
    
    # Maximum turns allowed (N+1 for N-letter word)
    max_turns = Column(Integer, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    
    # Constraint to ensure word length is between 5 and 8
    __table_args__ = (CheckConstraint("word_length BETWEEN 5 AND 8"),)


class GameAttempt(Base):
    """
    Game attempts (guesses) table.
    
    Stores each guess and its feedback.
    Linked to a game via foreign key.
    """
    __tablename__ = "game_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to games table, cascade delete if game is deleted
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    
    # Attempt number (1, 2, 3, ...)
    attempt_number = Column(Integer, nullable=False)
    
    # The guessed word
    guess = Column(String(8), nullable=False)
    
    # Feedback for each letter: [{"letter": "A", "color": "green"}, ...]
    feedback = Column(JSON, nullable=False)
    
    # Timestamp
    created_at = Column(DateTime, server_default=func.now())
    
    # Constraint to ensure attempt number is positive
    __table_args__ = (CheckConstraint("attempt_number > 0"),)


class UserStats(Base):
    """
    User statistics table.
    
    Stores aggregated statistics for each user.
    Updated asynchronously via outbox pattern.
    """
    __tablename__ = "user_stats"
    
    # Foreign key to users table, acts as primary key (one-to-one)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    
    # Game counts
    games_played = Column(Integer, default=0)
    games_won = Column(Integer, default=0)
    games_lost = Column(Integer, default=0)
    
    # Streak tracking
    current_streak = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)
    
    # Average guesses to win (stored as integer, convert to float in app)
    avg_guesses_to_win = Column(Integer)
    
    # Guess distribution per word length: {5: {1: count, 2: count, ...}, 6: {...}, ...}
    guess_distribution = Column(JSON, default={})
    
    # Timestamp
    updated_at = Column(DateTime, server_default=func.now())


class WordOfDayAttempt(Base):
    """
    Word of the Day attempts table.
    
    Tracks one attempt per user per day for Word of the Day.
    Prevents users from playing Word of the Day multiple times per day.
    """
    __tablename__ = "word_of_day_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to users table, cascade delete if user is deleted
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Attempt date in UTC format 'YYYY-MM-DD'
    attempt_date = Column(String(10), nullable=False)
    
    # Foreign key to games table (set to NULL if game is deleted)
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="SET NULL"))
    
    # Timestamp
    created_at = Column(DateTime, server_default=func.now())
    
    # Constraint to ensure user_id is not null
    __table_args__ = (CheckConstraint("user_id IS NOT NULL"),)


class OutboxEvent(Base):
    """
    Outbox pattern events table for reliable event publishing.
    
    Stores events to be processed asynchronously.
    Ensures events are not lost if the system crashes.
    Used for: game completion, stats updates, leaderboard updates.
    """
    __tablename__ = "outbox_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event type: 'game_completed', 'user_stats_updated', 'leaderboard_updated'
    event_type = Column(String(100), nullable=False)
    
    # ID of the aggregate (game_id, user_id, etc.)
    aggregate_id = Column(String(255), nullable=False)
    
    # Type of aggregate: 'game', 'user', 'leaderboard'
    aggregate_type = Column(String(50), nullable=False)
    
    # Event payload (JSON data)
    payload = Column(JSON, nullable=False)
    
    # Event status: 'pending', 'processing', 'completed', 'failed'
    status = Column(String(50), nullable=False, default='pending')
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    processed_at = Column(DateTime)
    
    # Error information if processing failed
    error_message = Column(Text)
    
    # Retry count (incremented on each failure)
    retry_count = Column(Integer, default=0)
    
    # Constraint to ensure status is one of the allowed values
    __table_args__ = (CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')"),)
