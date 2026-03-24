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

    When anonymization is enabled, the MCP server will connect to the anonymized
    Netbox instance instead of production, ensuring Claude never sees real data.

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
    # Determine which Netbox instance to use based on anonymization setting
    if config.anonymization_enabled:
        # CRITICAL: Use anonymized Netbox when anonymization is enabled
        # This ensures Claude NEVER sees real production data
        if not config.netbox_anon_url or not config.netbox_anon_token:
            raise ValueError(
                "Anonymization is enabled but NETBOX_ANON_URL and NETBOX_ANON_TOKEN are not set."
            )
        netbox_url = config.netbox_anon_url
        netbox_token = config.netbox_anon_token
    else:
        # Use production Netbox when anonymization is disabled (development/testing)
        if not config.netbox_url or not config.netbox_token:
            raise ValueError(
                "Netbox configuration incomplete. NETBOX_URL and NETBOX_TOKEN are required."
            )
        netbox_url = config.netbox_url
        netbox_token = config.netbox_token

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
                "netbox-mcp-server",
            ],
            "env": {
                "NETBOX_URL": netbox_url,
                "NETBOX_TOKEN": netbox_token,
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
        - mcp__netbox__netbox_search_objects (v1.0.0+)
    """
    return [
        "mcp__netbox__netbox_get_objects",
        "mcp__netbox__netbox_get_object_by_id",
        "mcp__netbox__netbox_get_changelogs",
        "mcp__netbox__netbox_search_objects",
    ]
