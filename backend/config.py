"""
Configuration Management

This module provides centralized configuration for the application.
It reads settings from environment variables and provides type-safe access.

Environment variables are set in .env file or system environment.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Pydantic automatically reads environment variables that match the field names.
    For example, DATABASE_URL env var maps to the database_url field.
    """
    
    # Database Configuration
    # Connection string for the database (PostgreSQL or SQLite)
    database_url: str = "sqlite:///./wordle.db"
    
    # Redis Configuration
    # Connection string for Redis cache
    redis_url: str = "redis://localhost:6379/0"
    
    # Security - JWT Tokens
    # Secret key used to sign JWT tokens (should be kept secret in production)
    jwt_secret_key: str = "change-this-in-production"
    
    # JWT algorithm used for token signing
    jwt_algorithm: str = "HS256"
    
    # Access token time-to-live in seconds (15 minutes = 900 seconds)
    # Short-lived for security - if compromised, limited damage window
    access_token_ttl: int = 900
    
    # Refresh token time-to-live in seconds (7 days = 604800 seconds)
    # Longer-lived for user convenience, stored in httpOnly cookie
    refresh_token_ttl: int = 604800
    
    # Game Configuration
    # Timezone for Word of the Day (UTC ensures consistency across all users)
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
    # Database query timeout
    database_query_timeout: int = 10
    
    # Redis operation timeout
    redis_timeout: int = 5
    
    # API request timeout
    api_request_timeout: int = 30
    
    # Outbox Pattern Configuration
    # How often to poll for outbox events (in seconds)
    outbox_poll_interval: int = 5
    
    # How many events to process per poll
    outbox_batch_size: int = 100
    
    # How long to keep completed outbox events (in days)
    outbox_retention_days: int = 7
    
    class Config:
        # Automatically read from .env file if it exists
        env_file = ".env"
        case_sensitive = False  # Environment variables are case-insensitive


# Global settings instance - import this throughout the application
settings = Settings()
