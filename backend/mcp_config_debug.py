"""
DEBUG version of MCP config - uses debug server with enhanced logging.

To use: temporarily modify agent.py to import from mcp_config_debug instead of mcp_config.
"""

from typing import Any

from backend.config import Config


def get_netbox_mcp_config(config: Config) -> dict[str, Any]:
    """
    Create Netbox MCP server configuration for ClaudeAgentOptions (DEBUG VERSION).

    This version uses the debug server that logs everything to /tmp/netbox_mcp_debug.log
    """
    if not config.netbox_url or not config.netbox_token:
        raise ValueError(
            "Netbox configuration incomplete. NETBOX_URL and NETBOX_TOKEN are required."
        )

    return {
        "netbox": {
            "type": "stdio",
            "command": "python",
            "args": [
                "/home/ola/dev/netboxdev/claude-agentic-sdk/server_debug.py",
            ],
            "env": {
                "NETBOX_URL": config.netbox_url,
                "NETBOX_TOKEN": config.netbox_token,
                "LOG_LEVEL": "DEBUG",
                "PYTHONUNBUFFERED": "1",  # Force unbuffered output
            },
        }
    }


def get_allowed_netbox_tools() -> list[str]:
    """Get list of allowed Netbox MCP tools."""
    return [
        "mcp__netbox__netbox_get_objects",
        "mcp__netbox__netbox_get_object_by_id",
        "mcp__netbox__netbox_get_changelogs",
    ]
