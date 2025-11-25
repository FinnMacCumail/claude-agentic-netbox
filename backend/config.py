"""
Configuration management for Netbox Chatbox.

Loads environment variables and validates required configuration.
"""

import os

from dotenv import load_dotenv

# CRITICAL: Load .env file before any other imports that use env vars
load_dotenv()


class Config:
    """
    Application configuration loaded from environment variables.

    Validates required environment variables on initialization.
    """

    def __init__(self) -> None:
        """Initialize configuration from environment variables."""
        # Anthropic API Configuration
        self.anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

        # Netbox Configuration
        self.netbox_url: str = os.getenv("NETBOX_URL", "")
        self.netbox_token: str = os.getenv("NETBOX_TOKEN", "")

        # Application Configuration
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.cors_origins: list[str] = self._parse_cors_origins(
            os.getenv("CORS_ORIGINS", "http://localhost:3000")
        )

        # Validate required configuration
        self.validate()

    def validate(self) -> None:
        """
        Validate that all required environment variables are set.

        Raises:
            ValueError: If any required environment variable is missing or invalid.
        """
        missing_vars: list[str] = []

        if not self.anthropic_api_key:
            missing_vars.append("ANTHROPIC_API_KEY")

        if not self.netbox_url:
            missing_vars.append("NETBOX_URL")

        if not self.netbox_token:
            missing_vars.append("NETBOX_TOKEN")

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                f"Please set these in your .env file or environment."
            )

        # Validate log level
        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_log_levels:
            raise ValueError(
                f"Invalid LOG_LEVEL: {self.log_level}. "
                f"Must be one of: {', '.join(valid_log_levels)}"
            )

        # Validate Netbox URL format
        if not self.netbox_url.startswith(("http://", "https://")):
            raise ValueError(
                f"Invalid NETBOX_URL: {self.netbox_url}. " f"Must start with http:// or https://"
            )

    def _parse_cors_origins(self, origins: str) -> list[str]:
        """
        Parse CORS origins from comma-separated string.

        Args:
            origins: Comma-separated string of allowed origins.

        Returns:
            list[str]: List of allowed CORS origins.
        """
        return [origin.strip() for origin in origins.split(",") if origin.strip()]

    def __repr__(self) -> str:
        """
        Return string representation of config (without sensitive values).

        Returns:
            str: Safe string representation of configuration.
        """
        return (
            f"Config("
            f"anthropic_api_key={'***' if self.anthropic_api_key else 'NOT SET'}, "
            f"netbox_url={self.netbox_url}, "
            f"netbox_token={'***' if self.netbox_token else 'NOT SET'}, "
            f"log_level={self.log_level}, "
            f"cors_origins={self.cors_origins}"
            f")"
        )
