"""
Configuration Management

This module provides centralized configuration for the application.
It reads settings from environment variables and provides type-safe access.

Environment variables are set in .env file or system environment.
This follows the settings pattern to ensure all configuration is in one place.
"""
import secrets

from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Pydantic automatically reads environment variables that match the field names.
    For example, DATABASE_URL env var maps to the database_url field.
    
    This provides:
    - Type validation (e.g., integers for timeouts)
    - Default values for local development
    - Environment-specific configuration
    """
    
    # Database Configuration
    # Connection string for the PostgreSQL database
    # (the same database engine is used for local development and production)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/wordle"
    
    # Redis Configuration
    # Connection string for Redis cache
    # Default is localhost for local development
    redis_url: str = "redis://localhost:6379/0"
    
    # Security - JWT Tokens
    # Secret key used to sign JWT tokens. Set JWT_SECRET_KEY in every deployment.
    # If unset, a random key is generated per process so tokens can't be forged,
    # but they won't survive restarts or be shared across workers.
    jwt_secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    
    # JWT algorithm used for token signing
    # HS256 is symmetric key algorithm (simpler than RS256)
    jwt_algorithm: str = "HS256"
    
    # Access token time-to-live in seconds (15 minutes = 900 seconds)
    # Short-lived for security - if compromised, limited damage window
    # Stored in sessionStorage (cleared on tab close)
    access_token_ttl: int = 900
    
    # Refresh token time-to-live in seconds (7 days = 604800 seconds)
    # Longer-lived for user convenience, stored in httpOnly cookie
    # For guests: 6 hours (21600 seconds)
    refresh_token_ttl: int = 604800
    
    # Game Configuration
    # Timezone for Word of the Day (UTC ensures consistency across all users)
    # All users get the same word regardless of their local timezone
    word_of_day_timezone: str = "UTC"
    
    # Word length for Word of the Day (always 5 for consistency with original Wordle)
    word_of_day_word_length: int = 5
    
    # Rate Limiting
    # Max requests per minute per authenticated user
    rate_limit_per_minute: int = 100
    
    # Max requests per minute per IP address (for unauthenticated requests)
    rate_limit_per_minute_ip: int = 10
    
    # Max requests per minute for auth endpoints (stricter to prevent brute force)
    rate_limit_auth_endpoints: int = 5
    
    # Timeouts (in seconds)
    # Database query timeout - prevents long-running queries from blocking
    database_query_timeout: int = 10
    
    # Redis operation timeout - prevents slow cache operations
    redis_timeout: int = 5
    
    # API request timeout - prevents slow API calls from blocking
    api_request_timeout: int = 30
    
    # Outbox Pattern Configuration
    # How often to poll for outbox events (in seconds)
    # 5 seconds is reasonable balance between real-time and efficiency
    outbox_poll_interval: int = 5
    
    # How many events to process per poll
    # Batch size for processing events
    outbox_batch_size: int = 100
    
    # How long to keep completed outbox events (in days)
    # 7 days retention balances storage cost with debugging needs
    outbox_retention_days: int = 7
    
    class Config:
        # Automatically read from .env file if it exists
        env_file = ".env"
        # Environment variables are case-insensitive
        case_sensitive = False

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Skip unrelated keys in a shared .env file (e.g. VITE_* for the frontend)
        # while still rejecting unknown constructor overrides.
        def known_dotenv_settings() -> dict:
            return {
                key: value
                for key, value in dotenv_settings().items()
                if key in settings_cls.model_fields
            }

        return init_settings, env_settings, known_dotenv_settings, file_secret_settings


# Global settings instance - import this throughout the application
# This ensures a single source of truth for all configuration
settings = Settings()
