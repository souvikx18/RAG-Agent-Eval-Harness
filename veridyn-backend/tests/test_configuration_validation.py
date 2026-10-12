import pytest
from fastapi.testclient import TestClient

from app.core.config import (
    Settings,
    ConfigurationError,
    DEFAULT_DEV_JWT_SECRET,
    settings,
)
from app.main import app, validate_configuration


@pytest.fixture
def restore_global_settings():
    """Preserve and restore global settings after any mutation during tests."""
    original_env = settings.ENVIRONMENT
    original_debug = settings.DEBUG
    original_db = settings.DATABASE_URL
    original_secret = settings.JWT_SECRET_KEY
    original_algo = settings.JWT_ALGORITHM
    original_exp = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    yield
    settings.ENVIRONMENT = original_env
    settings.DEBUG = original_debug
    settings.DATABASE_URL = original_db
    settings.JWT_SECRET_KEY = original_secret
    settings.JWT_ALGORITHM = original_algo
    settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = original_exp


def test_default_settings_valid_in_development():
    """Default local settings should pass validation in development/test."""
    dev_settings = Settings()
    dev_settings.validate()
    assert dev_settings.is_development or dev_settings.is_testing
    assert not dev_settings.is_production


def test_valid_production_settings():
    """A fully specified, secure production configuration must validate successfully."""
    prod_settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        DATABASE_URL="postgresql://produser:prodpass@db.example.com:5432/proddb",
        JWT_SECRET_KEY="a_very_secure_and_long_production_jwt_secret_key_12345",
        JWT_ALGORITHM="HS256",
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30,
        auto_validate=True,
    )
    assert prod_settings.is_production is True
    assert prod_settings.is_development is False
    assert prod_settings.DEBUG is False
    assert prod_settings.JWT_SECRET == prod_settings.JWT_SECRET_KEY


def test_production_rejects_debug_enabled():
    """Production must reject DEBUG=True to prevent exposing debug handlers and tracebacks."""
    prod_settings = Settings(
        ENVIRONMENT="production",
        DEBUG=True,
        DATABASE_URL="postgresql://produser:prodpass@db.example.com:5432/proddb",
        JWT_SECRET_KEY="a_very_secure_and_long_production_jwt_secret_key_12345",
    )
    with pytest.raises(ConfigurationError) as exc_info:
        prod_settings.validate()
    assert "DEBUG mode must be disabled in production" in str(exc_info.value)


def test_production_rejects_default_dev_jwt_secret():
    """Production must reject the default development JWT secret."""
    prod_settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        DATABASE_URL="postgresql://produser:prodpass@db.example.com:5432/proddb",
        JWT_SECRET_KEY=DEFAULT_DEV_JWT_SECRET,
    )
    with pytest.raises(ConfigurationError) as exc_info:
        prod_settings.validate()
    assert "default development secret" in str(exc_info.value)
    # Ensure default secret value is not exposed in the exception message
    assert DEFAULT_DEV_JWT_SECRET not in str(exc_info.value)


def test_production_rejects_short_jwt_secret():
    """Production must enforce a minimum length of 32 characters for JWT secrets."""
    weak_secret = "too-short-secret"
    prod_settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        DATABASE_URL="postgresql://produser:prodpass@db.example.com:5432/proddb",
        JWT_SECRET_KEY=weak_secret,
    )
    with pytest.raises(ConfigurationError) as exc_info:
        prod_settings.validate()
    assert "at least 32 characters" in str(exc_info.value)
    # Ensure secret value is never leaked in the error message
    assert weak_secret not in str(exc_info.value)


def test_production_rejects_in_memory_sqlite():
    """Production must reject ephemeral in-memory SQLite databases."""
    prod_settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        DATABASE_URL="sqlite:///:memory:",
        JWT_SECRET_KEY="a_very_secure_and_long_production_jwt_secret_key_12345",
    )
    with pytest.raises(ConfigurationError) as exc_info:
        prod_settings.validate()
    assert "In-memory SQLite database is not permitted in production" in str(exc_info.value)


def test_rejects_empty_database_url():
    """All environments must reject an empty or whitespace DATABASE_URL."""
    for empty_url in ["", "   "]:
        dev_settings = Settings(
            ENVIRONMENT="development",
            DATABASE_URL=empty_url,
        )
        with pytest.raises(ConfigurationError) as exc_info:
            dev_settings.validate()
        assert "DATABASE_URL must be configured" in str(exc_info.value)


def test_rejects_empty_jwt_secret():
    """All environments must reject an empty or whitespace JWT secret."""
    for empty_secret in ["", "   "]:
        dev_settings = Settings(
            ENVIRONMENT="development",
            DATABASE_URL="sqlite:///test.db",
            JWT_SECRET_KEY=empty_secret,
        )
        with pytest.raises(ConfigurationError) as exc_info:
            dev_settings.validate()
        assert "JWT_SECRET_KEY must not be empty" in str(exc_info.value)


def test_rejects_invalid_environment():
    """Unsupported ENVIRONMENT names must be rejected."""
    bad_settings = Settings(
        ENVIRONMENT="super_prod_cluster",
        DATABASE_URL="sqlite:///test.db",
    )
    with pytest.raises(ConfigurationError) as exc_info:
        bad_settings.validate()
    assert "ENVIRONMENT 'super_prod_cluster' is invalid" in str(exc_info.value)


def test_rejects_unsupported_jwt_algorithm():
    """Unsupported or insecure JWT algorithms (e.g., none) must be rejected."""
    bad_settings = Settings(
        ENVIRONMENT="development",
        DATABASE_URL="sqlite:///test.db",
        JWT_ALGORITHM="none",
    )
    with pytest.raises(ConfigurationError) as exc_info:
        bad_settings.validate()
    assert "JWT_ALGORITHM 'none' is unsupported" in str(exc_info.value)


def test_rejects_invalid_access_token_expiration():
    """Token expiration minutes must be greater than zero."""
    for bad_exp in [0, -15]:
        bad_settings = Settings(
            ENVIRONMENT="development",
            DATABASE_URL="sqlite:///test.db",
            JWT_ACCESS_TOKEN_EXPIRE_MINUTES=bad_exp,
        )
        with pytest.raises(ConfigurationError) as exc_info:
            bad_settings.validate()
        assert "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer" in str(exc_info.value)


def test_rejects_non_integer_expiration():
    """Non-integer expiration minutes must fail with ConfigurationError."""
    with pytest.raises(ConfigurationError) as exc_info:
        Settings(
            JWT_ACCESS_TOKEN_EXPIRE_MINUTES="not_an_int",  # type: ignore
        )
    assert "must be a valid integer" in str(exc_info.value)


def test_sensitive_values_not_exposed_in_exception_messages():
    """Verify that sensitive tokens, keys, and connection credentials never leak into exceptions."""
    sensitive_token = "ultra-secret-token-xyz-987"
    sensitive_db = "postgresql://my_secret_user:my_secret_pass@127.0.0.1:5432/db"

    # Weak secret in production
    with pytest.raises(ConfigurationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            DATABASE_URL=sensitive_db,
            JWT_SECRET_KEY=sensitive_token,
            auto_validate=True,
        )
    error_message = str(exc_info.value)
    assert sensitive_token not in error_message
    assert "my_secret_pass" not in error_message


def test_startup_validation_succeeds_in_dev():
    """Application startup event executes successfully with current development configuration."""
    validate_configuration()


def test_startup_validation_aborts_on_invalid_production_config(restore_global_settings):
    """Application startup event must abort with ConfigurationError if production is misconfigured."""
    settings.ENVIRONMENT = "production"
    settings.DEBUG = True

    with pytest.raises(ConfigurationError) as exc_info:
        validate_configuration()
    assert "DEBUG mode must be disabled in production" in str(exc_info.value)


def test_testclient_lifecycle_triggers_startup(restore_global_settings):
    """TestClient startup lifecycle properly triggers configuration validation."""
    settings.ENVIRONMENT = "production"
    settings.DEBUG = False
    settings.JWT_SECRET_KEY = DEFAULT_DEV_JWT_SECRET

    with pytest.raises(ConfigurationError) as exc_info:
        with TestClient(app):
            pass
    assert "default development secret" in str(exc_info.value)
