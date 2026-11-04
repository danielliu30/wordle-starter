"""
Unit tests for configuration management

Tests the Settings class to ensure:
- Environment variables are loaded correctly
- Default values work when env vars not set
- Type validation works
- .env file loading works
"""
import os
import pytest
from pydantic import ValidationError
from config import Settings


def test_settings_with_defaults():
    """
    Test that settings load with default values when no env vars set.
    
    This ensures the application works out-of-the-box for local development
    without requiring environment variables to be set.
    """
    # Ensure no env vars are set
    if "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]
    if "REDIS_URL" in os.environ:
        del os.environ["REDIS_URL"]
    
    settings = Settings()
    
    # Verify default values
    assert settings.database_url == "postgresql://user:password@localhost:5432/wordle"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.access_token_ttl == 900
    assert settings.refresh_token_ttl == 604800


def test_settings_with_env_vars():
    """
    Test that settings load from environment variables.
    
    This ensures that in production, environment variables override defaults.
    """
    # Set env vars
    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    os.environ["JWT_SECRET_KEY"] = "test-secret"
    
    settings = Settings()
    
    # Verify env vars are loaded
    assert settings.database_url == "postgresql://user:pass@localhost/db"
    assert settings.redis_url == "redis://localhost:6379/1"
    assert settings.jwt_secret_key == "test-secret"
    
    # Cleanup
    del os.environ["DATABASE_URL"]
    del os.environ["REDIS_URL"]
    del os.environ["JWT_SECRET_KEY"]


def test_settings_validation():
    """
    Test that Pydantic validates types correctly.
    
    This ensures type safety - strings are cast to ints, etc.
    """
    # String should be cast to int
    settings = Settings(access_token_ttl="500")
    assert settings.access_token_ttl == 500


def test_settings_case_insensitive():
    """
    Test that environment variable names are case-insensitive.
    
    This provides flexibility - DATABASE_URL and database_url both work.
    """
    os.environ["DATABASE_URL"] = "postgresql://test/db"
    settings = Settings()
    assert settings.database_url == "postgresql://test/db"
    
    # Test that lowercase env var also works
    del os.environ["DATABASE_URL"]
    os.environ["database_url"] = "postgresql://test/db"
    settings = Settings()
    assert settings.database_url == "postgresql://test/db"
    
    del os.environ["database_url"]


def test_settings_all_required_fields_have_defaults():
    """
    Test that all required configuration fields have sensible defaults.
    
    This ensures the application can start without any environment variables.
    """
    settings = Settings()
    
    # Verify all fields have values
    assert settings.database_url is not None
    assert settings.redis_url is not None
    assert settings.jwt_secret_key is not None
    assert settings.access_token_ttl > 0
    assert settings.refresh_token_ttl > 0
    assert settings.database_query_timeout > 0
    assert settings.redis_timeout > 0
    assert settings.api_request_timeout > 0


def test_jwt_secret_key_default_is_random():
    """
    Test that an unset JWT_SECRET_KEY yields an unpredictable signing key
    instead of a hard-coded public one.
    """
    os.environ.pop("JWT_SECRET_KEY", None)

    first = Settings()
    second = Settings()

    assert len(first.jwt_secret_key) >= 32
    assert first.jwt_secret_key != second.jwt_secret_key


def test_settings_ignores_unrelated_dotenv_entries(tmp_path):
    """
    Test that unrelated keys in a shared .env file don't block loading.
    """
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql://dotenv/db\n"
        "VITE_API_URL=http://localhost:8000\n"
    )
    os.environ.pop("DATABASE_URL", None)

    settings = Settings(_env_file=env_file)

    assert settings.database_url == "postgresql://dotenv/db"


def test_settings_rejects_unknown_overrides():
    """
    Test that a misspelled constructor override fails instead of silently
    falling back to the default.
    """
    with pytest.raises(ValidationError):
        Settings(database_ur1="postgresql://db/prod")
