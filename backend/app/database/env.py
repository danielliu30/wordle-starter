"""
Alembic Environment Configuration

Configures Alembic for database schema migrations.
Supports both SQLite (local dev) and PostgreSQL (production).
"""
from sqlalchemy import engine
from sqlalchemy.ext.asyncio import create_async_engine
from config import settings
from app.database.models import Base

# Create async engine based on database URL
# For SQLite (local dev): use sqlite+aiosqlite://
# For PostgreSQL (production): use postgresql+asyncpg://
if settings.database_url.startswith("sqlite"):
    engine = create_async_engine(settings.database_url.replace("sqlite://", "sqlite+aiosqlite://"))
else:
    engine = create_async_engine(settings.database_url.replace("postgresql://", "postgresql+asyncpg://"))

# Target metadata for autogenerate support
# This allows Alembic to detect schema changes automatically
target_metadata = Base.metadata


def run_migrations_online():
    """
    Run migrations in 'online' mode.
    
    In 'online' mode, we connect to the database and run migrations directly.
    This is the recommended approach for production.
    """
    connectable = engine
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if __name__ == "__main__":
    run_migrations_online()
