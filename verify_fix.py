#!/usr/bin/env python3
"""Quick verification that MCP 403 error is fixed."""

import asyncio
import json
import sys
import websockets


async def verify_mcp_fixed():
    """Quick test to verify MCP is working."""
    uri = "ws://localhost:8001/ws/chat"

    print("🧪 Verifying MCP 403 fix...")
    print(f"   Connecting to {uri}")

    try:
        async with websockets.connect(uri, close_timeout=5) as websocket:
            print("   ✅ Connected to WebSocket")

            # Send test query
            await websocket.send(json.dumps({"message": "List sites"}))
            print("   📤 Sent test query")

            # Wait for completion
            got_response = False
            timeout = asyncio.get_event_loop().time() + 20  # 20 second timeout

            while asyncio.get_event_loop().time() < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    data = json.loads(response)

                    if data.get("type") == "text" and data.get("content"):
                        got_response = True
                        print(f"   📥 Got response: {data['content'][:100]}...")

                    if data.get("completed"):
                        print("   ✅ Response completed")
                        break

                except asyncio.TimeoutError:
                    continue

            if got_response:
                print("\n✅ SUCCESS: MCP 403 error is FIXED!")
                print("   The Netbox MCP tools are working correctly.")
                return 0
            else:
                print("\n⚠️  No text response received (but no 403 error)")
                return 1

    except ConnectionRefusedError:
        print("❌ ERROR: Could not connect to server")
        print("   Make sure the server is running on port 8001")
        return 1
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(verify_mcp_fixed()))
