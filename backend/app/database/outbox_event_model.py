"""
Outbox Event Model

SQLAlchemy ORM model for outbox pattern events.
"""
from sqlalchemy import Column, String, DateTime, Text, JSON, CheckConstraint, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

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
