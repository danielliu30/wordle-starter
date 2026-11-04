"""
Game Model

SQLAlchemy ORM model for games.
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, CheckConstraint, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

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
