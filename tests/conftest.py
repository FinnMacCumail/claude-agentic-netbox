"""
Pytest configuration and fixtures.

Provides shared fixtures for testing the Netbox Chatbox backend.
"""

import os
from collections.abc import Generator

import pytest


@pytest.fixture
def mock_env_vars() -> Generator[dict[str, str], None, None]:
    """
    Provide mock environment variables for testing.

    Yields:
        dict: Mock environment variables.
    """
    mock_vars = {
        "ANTHROPIC_API_KEY": "sk-ant-test-key-1234567890",
        "NETBOX_URL": "http://localhost:8000",
        "NETBOX_TOKEN": "test-token-1234567890",
        "LOG_LEVEL": "DEBUG",
        "CORS_ORIGINS": "http://localhost:3000,http://127.0.0.1:3000",
    }

    # Save original env vars
    original_env = {key: os.environ.get(key) for key in mock_vars}

    # Set mock env vars
    for key, value in mock_vars.items():
        os.environ[key] = value

    yield mock_vars

    # Restore original env vars
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """
    Clear environment variables for testing missing configs.

    Yields:
        None
    """
    # Save original env vars
    env_keys = ["ANTHROPIC_API_KEY", "NETBOX_URL", "NETBOX_TOKEN", "LOG_LEVEL", "CORS_ORIGINS"]
    original_env = {key: os.environ.get(key) for key in env_keys}

    # Clear env vars
    for key in env_keys:
        os.environ.pop(key, None)

    yield

    # Restore original env vars
    for key, original_value in original_env.items():
        if original_value is not None:
            os.environ[key] = original_value
