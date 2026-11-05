"""
Model Registry

Imports every ORM model so their tables register on the shared declarative
Base. Importing this module is enough for Base.metadata.create_all() to
build the full schema.
"""
from app.database.user_model import Base  # noqa: F401

from app.database import (  # noqa: F401
    game_attempt_model,
    game_model,
    outbox_event_model,
    user_model,
    user_session_model,
    user_stats_model,
    word_of_day_attempt_model,
)
