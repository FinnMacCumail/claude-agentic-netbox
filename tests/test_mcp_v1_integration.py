#!/usr/bin/env python3
"""
Test script to verify NetBox MCP Server v1.0.0 integration.

Tests:
1. Backend MCP configuration is correct
2. MCP server can be initialized
3. New search_objects tool is available
"""

import asyncio
import sys

from backend.config import Config
from backend.agent import ChatAgent


async def test_mcp_integration():
    """Test MCP server v1.0.0 integration."""
    print("🔧 Testing NetBox MCP Server v1.0.0 Integration\n")

    # 1. Load config
    print("1️⃣ Loading configuration...")
    try:
        config = Config()
        print(f"   ✅ Config loaded: NETBOX_URL={config.netbox_url}")
    except Exception as e:
        print(f"   ❌ Failed to load config: {e}")
        return False

    # 2. Create agent
    print("\n2️⃣ Creating ChatAgent...")
    try:
        agent = ChatAgent(config)
        print("   ✅ ChatAgent created")
    except Exception as e:
        print(f"   ❌ Failed to create agent: {e}")
        return False

    # 3. Start session (this will initialize MCP server)
    print("\n3️⃣ Starting Claude Agent session (initializing MCP server)...")
    try:
        await agent.start_session()
        print("   ✅ Session started successfully")
    except Exception as e:
        print(f"   ❌ Failed to start session: {e}")
        return False

    # 4. Check available tools
    print("\n4️⃣ Checking available tools...")
    if agent.client:
        # Get the tools from the SDK
        # Note: Claude Agent SDK doesn't expose tools directly, but we can verify
        # by checking the allowed_tools list
        from backend.mcp_config import get_allowed_netbox_tools
        allowed_tools = get_allowed_netbox_tools()

        print(f"   ℹ️  Allowed tools ({len(allowed_tools)}):")
        for tool in allowed_tools:
            # Check for v1.0.0 tools
            if "search_objects" in tool:
                print(f"      ✅ {tool} (NEW in v1.0.0)")
            else:
                print(f"      ✅ {tool}")

        # Verify new search tool is present
        if "mcp__netbox__netbox_search_objects" in allowed_tools:
            print("\n   ✅ New search_objects tool is available!")
        else:
            print("\n   ❌ New search_objects tool NOT found in allowed tools")
            return False
    else:
        print("   ❌ Client not initialized")
        return False

    # 5. Close session
    print("\n5️⃣ Closing session...")
    try:
        await agent.close_session()
        print("   ✅ Session closed")
    except Exception as e:
        print(f"   ❌ Failed to close session: {e}")
        return False

    print("\n✅ All tests passed! NetBox MCP Server v1.0.0 integration is working.\n")
    return True


async def main():
    """Main test runner."""
    success = await test_mcp_integration()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
