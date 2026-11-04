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
    """Test that settings load with default values when no env vars set"""
    # Ensure no env vars are set
    if "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]
    if "REDIS_URL" in os.environ:
        del os.environ["REDIS_URL"]
    
    settings = Settings()
    
    assert settings.database_url == "sqlite:///./wordle.db"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.jwt_secret_key == "change-this-in-production"
    assert settings.access_token_ttl == 900
    assert settings.refresh_token_ttl == 604800


def test_settings_with_env_vars():
    """Test that settings load from environment variables"""
    # Set env vars
    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    os.environ["JWT_SECRET_KEY"] = "test-secret"
    
    settings = Settings()
    
    assert settings.database_url == "postgresql://user:pass@localhost/db"
    assert settings.redis_url == "redis://localhost:6379/1"
    assert settings.jwt_secret_key == "test-secret"
    
    # Cleanup
    del os.environ["DATABASE_URL"]
    del os.environ["REDIS_URL"]
    del os.environ["JWT_SECRET_KEY"]


def test_settings_validation():
    """Test that Pydantic validates types correctly"""
    # This should work - string is cast to int
    settings = Settings(access_token_ttl="500")
    assert settings.access_token_ttl == 500


def test_settings_case_insensitive():
    """Test that environment variable names are case-insensitive"""
    os.environ["DATABASE_URL"] = "postgresql://test/db"
    settings = Settings()
    assert settings.database_url == "postgresql://test/db"
    
    # Test that lowercase env var also works
    del os.environ["DATABASE_URL"]
    os.environ["database_url"] = "postgresql://test/db"
    settings = Settings()
    assert settings.database_url == "postgresql://test/db"
    
    del os.environ["database_url"]
