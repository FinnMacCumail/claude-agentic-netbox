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

        # LangSmith Tracing Configuration (Optional)
        self.langchain_tracing_v2: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        self.langchain_api_key: str = os.getenv("LANGCHAIN_API_KEY", "")
        self.langchain_project: str = os.getenv("LANGCHAIN_PROJECT", "netbox-chatbox")

        # Anonymization Configuration (Optional)
        self.anonymization_enabled: bool = os.getenv("ANONYMIZATION_ENABLED", "false").lower() == "true"
        self.anonymization_mode: str = os.getenv("ANONYMIZATION_MODE", "greenmask")
        self.anonymization_seed: str = os.getenv("ANONYMIZATION_SEED", "")
        self.greenmask_mappings_file: str = os.getenv("GREENMASK_MAPPINGS_FILE", "")
        self.netbox_anon_url: str = os.getenv("NETBOX_ANON_URL", "")
        self.netbox_anon_token: str = os.getenv("NETBOX_ANON_TOKEN", "")
        self.anonymize_vendors: bool = os.getenv("ANONYMIZE_VENDORS", "true").lower() == "true"

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

        # Validate anonymization configuration if enabled
        if self.anonymization_enabled:
            anon_missing = []

            if not self.anonymization_seed:
                anon_missing.append("ANONYMIZATION_SEED")

            if not self.greenmask_mappings_file:
                anon_missing.append("GREENMASK_MAPPINGS_FILE")

            if not self.netbox_anon_url:
                anon_missing.append("NETBOX_ANON_URL")

            if not self.netbox_anon_token:
                anon_missing.append("NETBOX_ANON_TOKEN")

            if anon_missing:
                raise ValueError(
                    f"Anonymization is enabled but missing required variables: {', '.join(anon_missing)}"
                )

            # Validate anonymization mode
            if self.anonymization_mode not in ["greenmask"]:
                raise ValueError(
                    f"Invalid ANONYMIZATION_MODE: {self.anonymization_mode}. "
                    f"Currently only 'greenmask' is supported."
                )

            # Validate anonymized Netbox URL format
            if not self.netbox_anon_url.startswith(("http://", "https://")):
                raise ValueError(
                    f"Invalid NETBOX_ANON_URL: {self.netbox_anon_url}. "
                    f"Must start with http:// or https://"
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
        repr_str = (
            f"Config("
            f"anthropic_api_key={'***' if self.anthropic_api_key else 'NOT SET'}, "
            f"netbox_url={self.netbox_url}, "
            f"netbox_token={'***' if self.netbox_token else 'NOT SET'}, "
            f"log_level={self.log_level}, "
            f"cors_origins={self.cors_origins}, "
            f"langchain_tracing_v2={self.langchain_tracing_v2}"
        )

        if self.anonymization_enabled:
            repr_str += (
                f", anonymization_enabled={self.anonymization_enabled}, "
                f"anonymization_mode={self.anonymization_mode}, "
                f"netbox_anon_url={self.netbox_anon_url}"
            )

        repr_str += ")"
        return repr_str
