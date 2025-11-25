"""
Netbox MCP server configuration.

Provides MCP server configuration for integration with Claude Agent SDK.
"""

from typing import Any

from backend.config import Config


def get_netbox_mcp_config(config: Config) -> dict[str, Any]:
    """
    Create Netbox MCP server configuration for ClaudeAgentOptions.

    This configuration follows the structure defined in the Netbox MCP server's
    .mcp.json file, using absolute path to the server and passing required
    environment variables.

    Args:
        config: Application configuration object containing Netbox credentials.

    Returns:
        dict: MCP server configuration dictionary for use with ClaudeAgentOptions.
              Format: {"server_name": McpStdioServerConfig}

    Raises:
        ValueError: If required configuration is missing.

    Example:
        >>> config = Config()
        >>> mcp_config = get_netbox_mcp_config(config)
        >>> options = ClaudeAgentOptions(mcp_servers=mcp_config, ...)
    """
    # Validate config has required values
    if not config.netbox_url or not config.netbox_token:
        raise ValueError(
            "Netbox configuration incomplete. NETBOX_URL and NETBOX_TOKEN are required."
        )

    # CRITICAL: Use absolute path to Netbox MCP server directory
    # CRITICAL: Pass environment variables through env dict
    return {
        "netbox": {
            "type": "stdio",
            "command": "uv",
            "args": [
                "--directory",
                "/home/ola/dev/rnd/mcp/testmcp/netbox-mcp-server",
                "run",
                "server.py",
            ],
            "env": {
                "NETBOX_URL": config.netbox_url,
                "NETBOX_TOKEN": config.netbox_token,
                "LOG_LEVEL": config.log_level,
            },
        }
    }


def get_allowed_netbox_tools() -> list[str]:
    """
    Get list of allowed Netbox MCP tools.

    Returns:
        list[str]: List of tool names that can be used with the Netbox MCP server.
                   Tool names are prefixed with "mcp__netbox__" by the SDK.

    Note:
        The actual tool names in the SDK will be:
        - mcp__netbox__netbox_get_objects
        - mcp__netbox__netbox_get_object_by_id
        - mcp__netbox__netbox_get_changelogs
    """
    return [
        "mcp__netbox__netbox_get_objects",
        "mcp__netbox__netbox_get_object_by_id",
        "mcp__netbox__netbox_get_changelogs",
    ]
