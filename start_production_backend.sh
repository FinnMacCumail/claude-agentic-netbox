#!/bin/bash
# Start the Production (Non-Anonymized) Backend
# Runs on port 8002, queries real Netbox data

set -e

echo "🚀 Starting Production (Non-Anonymized) Backend..."
echo "   Configuration: .env.production"
echo "   Port: 8002"
echo "   Netbox: http://localhost:8000 (REAL DATA)"
echo ""

# Export environment from .env.production
if [ -f .env.production ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
else
    echo "❌ Error: .env.production not found!"
    exit 1
fi

echo "   NETBOX_URL: $NETBOX_URL"
echo "   ANONYMIZATION_ENABLED: $ANONYMIZATION_ENABLED"
echo "   NETBOX_TOKEN: ${NETBOX_TOKEN:0:10}..."
echo ""
echo "📊 Backend will be available at: http://localhost:8002"
echo "🔌 WebSocket endpoint: ws://localhost:8002/ws/chat"
echo ""

# Start the server on port 8002
uv run uvicorn backend.api:app --reload --port 8002
