"""
Outbox Event Model

SQLAlchemy ORM model for outbox pattern events.
PostgreSQL only (same database for local dev and production).
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, CheckConstraint, Index, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid

# Register on the shared models metadata so create_all builds every table together.
from app.database.user_model import Base

class OutboxEvent(Base):
    """Outbox pattern events table"""
    __tablename__ = "outbox_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False)
    aggregate_id = Column(String(255), nullable=False)
    aggregate_type = Column(String(50), nullable=False)
    payload = Column(JSONB, nullable=False)
    status = Column(String(50), nullable=False, default='pending')
    created_at = Column(DateTime, server_default=func.now())
    processed_at = Column(DateTime)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')"),
        # Publisher polls pending events oldest first.
        Index("idx_outbox_status_created", "status", "created_at"),
        Index("idx_outbox_aggregate", "aggregate_type", "aggregate_id"),
    )
