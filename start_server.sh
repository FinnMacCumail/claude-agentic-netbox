#!/bin/bash
# Start the Netbox Chatbox backend server with correct environment variables

# Load from .env file explicitly
export NETBOX_TOKEN="c4af48e5b315a5baf92f7ca449ac5d664239916a"
export NETBOX_URL="http://localhost:8000"

echo "🚀 Starting Netbox Chatbox Backend..."
echo "   NETBOX_URL: $NETBOX_URL"
echo "   NETBOX_TOKEN: ${NETBOX_TOKEN:0:10}..."
echo ""

# Start the server
cd /home/ola/dev/netboxdev/claude-agentic-sdk
uv run uvicorn backend.api:app --reload --port 8001
