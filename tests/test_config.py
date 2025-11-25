"""
Tests for configuration management.

Tests the Config class including environment variable loading and validation.
"""

import os

import pytest

from backend.config import Config


def test_config_loads_env_vars(mock_env_vars: dict[str, str]) -> None:
    """
    Test that Config loads environment variables correctly.

    Args:
        mock_env_vars: Fixture providing mock environment variables.
    """
    config = Config()

    assert config.anthropic_api_key == mock_env_vars["ANTHROPIC_API_KEY"]
    assert config.netbox_url == mock_env_vars["NETBOX_URL"]
    assert config.netbox_token == mock_env_vars["NETBOX_TOKEN"]
    assert config.log_level == mock_env_vars["LOG_LEVEL"]
    assert len(config.cors_origins) == 2
    assert "http://localhost:3000" in config.cors_origins


def test_config_validates_required_vars(clean_env: None) -> None:
    """
    Test that Config raises error for missing required vars.

    Args:
        clean_env: Fixture that clears environment variables.
    """
    with pytest.raises(ValueError) as exc_info:
        Config()

    error_message = str(exc_info.value)
    assert "ANTHROPIC_API_KEY" in error_message
    assert "NETBOX_URL" in error_message
    assert "NETBOX_TOKEN" in error_message


def test_config_validates_log_level(mock_env_vars: dict[str, str]) -> None:
    """
    Test that Config validates log level.

    Args:
        mock_env_vars: Fixture providing mock environment variables.
    """
    os.environ["LOG_LEVEL"] = "INVALID"

    with pytest.raises(ValueError) as exc_info:
        Config()

    assert "Invalid LOG_LEVEL" in str(exc_info.value)


def test_config_validates_netbox_url(mock_env_vars: dict[str, str]) -> None:
    """
    Test that Config validates Netbox URL format.

    Args:
        mock_env_vars: Fixture providing mock environment variables.
    """
    os.environ["NETBOX_URL"] = "invalid-url"

    with pytest.raises(ValueError) as exc_info:
        Config()

    assert "Invalid NETBOX_URL" in str(exc_info.value)


def test_config_default_log_level(mock_env_vars: dict[str, str]) -> None:
    """
    Test that Config provides default log level.

    Args:
        mock_env_vars: Fixture providing mock environment variables.
    """
    # Remove LOG_LEVEL to test default
    os.environ.pop("LOG_LEVEL", None)

    config = Config()
    assert config.log_level == "INFO"


def test_config_default_cors_origins(mock_env_vars: dict[str, str]) -> None:
    """
    Test that Config provides default CORS origins.

    Args:
        mock_env_vars: Fixture providing mock environment variables.
    """
    # Remove CORS_ORIGINS to test default
    os.environ.pop("CORS_ORIGINS", None)

    config = Config()
    assert "http://localhost:3000" in config.cors_origins


def test_config_repr_hides_secrets(mock_env_vars: dict[str, str]) -> None:
    """
    Test that Config repr doesn't expose sensitive values.

    Args:
        mock_env_vars: Fixture providing mock environment variables.
    """
    config = Config()
    config_repr = repr(config)

    # Should not contain actual API key or token
    assert mock_env_vars["ANTHROPIC_API_KEY"] not in config_repr
    assert mock_env_vars["NETBOX_TOKEN"] not in config_repr

    # Should contain masked values
    assert "***" in config_repr


def test_config_parse_cors_origins_with_spaces(mock_env_vars: dict[str, str]) -> None:
    """
    Test that Config parses CORS origins with spaces correctly.

    Args:
        mock_env_vars: Fixture providing mock environment variables.
    """
    os.environ["CORS_ORIGINS"] = " http://localhost:3000 , http://127.0.0.1:3000 "

    config = Config()
    assert len(config.cors_origins) == 2
    assert "http://localhost:3000" in config.cors_origins
    assert "http://127.0.0.1:3000" in config.cors_origins


def test_config_partial_missing_vars(mock_env_vars: dict[str, str]) -> None:
    """
    Test that Config identifies specific missing vars.

    Args:
        mock_env_vars: Fixture providing mock environment variables.
    """
    # Remove only ANTHROPIC_API_KEY
    os.environ.pop("ANTHROPIC_API_KEY", None)

    with pytest.raises(ValueError) as exc_info:
        Config()

    error_message = str(exc_info.value)
    assert "ANTHROPIC_API_KEY" in error_message
    assert "NETBOX_URL" not in error_message  # This one is still set
