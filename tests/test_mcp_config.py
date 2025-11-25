"""
Tests for Netbox MCP server configuration.

Tests the MCP configuration module including server config structure.
"""

import pytest

from backend.config import Config
from backend.mcp_config import get_allowed_netbox_tools, get_netbox_mcp_config


def test_mcp_config_structure(mock_env_vars: dict[str, str]) -> None:
    """
    Test that MCP config creates correct server configuration structure.

    Args:
        mock_env_vars: Fixture providing mock environment variables.
    """
    config = Config()
    mcp_config = get_netbox_mcp_config(config)

    # Check structure
    assert "netbox" in mcp_config
    assert "type" in mcp_config["netbox"]
    assert "command" in mcp_config["netbox"]
    assert "args" in mcp_config["netbox"]
    assert "env" in mcp_config["netbox"]


def test_mcp_config_uses_stdio_type(mock_env_vars: dict[str, str]) -> None:
    """
    Test that MCP config uses stdio type.

    Args:
        mock_env_vars: Fixture providing mock environment variables.
    """
    config = Config()
    mcp_config = get_netbox_mcp_config(config)

    assert mcp_config["netbox"]["type"] == "stdio"


def test_mcp_config_uses_uv_command(mock_env_vars: dict[str, str]) -> None:
    """
    Test that MCP config uses uv command.

    Args:
        mock_env_vars: Fixture providing mock environment variables.
    """
    config = Config()
    mcp_config = get_netbox_mcp_config(config)

    assert mcp_config["netbox"]["command"] == "uv"


def test_mcp_config_includes_required_args(mock_env_vars: dict[str, str]) -> None:
    """
    Test that MCP config includes required command arguments.

    Args:
        mock_env_vars: Fixture providing mock environment variables.
    """
    config = Config()
    mcp_config = get_netbox_mcp_config(config)

    args = mcp_config["netbox"]["args"]
    assert "--directory" in args
    assert "run" in args
    assert "server.py" in args


def test_mcp_config_uses_absolute_path(mock_env_vars: dict[str, str]) -> None:
    """
    Test that MCP config uses absolute path to server.

    Args:
        mock_env_vars: Fixture providing mock environment variables.
    """
    config = Config()
    mcp_config = get_netbox_mcp_config(config)

    args = mcp_config["netbox"]["args"]
    directory_index = args.index("--directory")
    server_path = args[directory_index + 1]

    # Should be absolute path
    assert server_path.startswith("/")
    assert "netbox-mcp-server" in server_path


def test_mcp_config_includes_env_vars(mock_env_vars: dict[str, str]) -> None:
    """
    Test that MCP config includes required environment variables.

    Args:
        mock_env_vars: Fixture providing mock environment variables.
    """
    config = Config()
    mcp_config = get_netbox_mcp_config(config)

    env = mcp_config["netbox"]["env"]
    assert "NETBOX_URL" in env
    assert "NETBOX_TOKEN" in env
    assert "LOG_LEVEL" in env


def test_mcp_config_env_values_match_config(mock_env_vars: dict[str, str]) -> None:
    """
    Test that MCP config env values match application config.

    Args:
        mock_env_vars: Fixture providing mock environment variables.
    """
    config = Config()
    mcp_config = get_netbox_mcp_config(config)

    env = mcp_config["netbox"]["env"]
    assert env["NETBOX_URL"] == config.netbox_url
    assert env["NETBOX_TOKEN"] == config.netbox_token
    assert env["LOG_LEVEL"] == config.log_level


def test_mcp_config_raises_on_missing_netbox_config() -> None:
    """
    Test that MCP config raises error for missing Netbox configuration.
    """
    # Create config with missing Netbox settings
    import os

    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
    os.environ["NETBOX_URL"] = ""
    os.environ["NETBOX_TOKEN"] = ""
    os.environ["LOG_LEVEL"] = "INFO"

    config = Config.__new__(Config)  # Create without __init__
    config.netbox_url = ""
    config.netbox_token = ""
    config.log_level = "INFO"

    with pytest.raises(ValueError) as exc_info:
        get_netbox_mcp_config(config)

    assert "Netbox configuration incomplete" in str(exc_info.value)


def test_get_allowed_netbox_tools() -> None:
    """
    Test that get_allowed_netbox_tools returns correct tool list.
    """
    tools = get_allowed_netbox_tools()

    # Check it's a list
    assert isinstance(tools, list)

    # Check expected tools are present
    assert "mcp__netbox__netbox_get_objects" in tools
    assert "mcp__netbox__netbox_get_object_by_id" in tools
    assert "mcp__netbox__netbox_get_changelogs" in tools

    # Check all tools have correct prefix
    for tool in tools:
        assert tool.startswith("mcp__netbox__")


def test_get_allowed_netbox_tools_count() -> None:
    """
    Test that get_allowed_netbox_tools returns expected number of tools.
    """
    tools = get_allowed_netbox_tools()

    # Should have 3 tools as per Netbox MCP server
    assert len(tools) == 3
