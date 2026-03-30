#!/bin/bash
# Start the Anonymized Backend
# Runs on port 8003, queries anonymized Netbox data

set -e

echo "🚀 Starting Anonymized Backend..."
echo "   Configuration: .env.anonymization"
echo "   Port: 8003"
echo "   Netbox: http://localhost:8001 (ANONYMIZED DATA)"
echo ""

# Export environment from .env.anonymization
if [ -f .env.anonymization ]; then
    set -a
    source .env.anonymization
    set +a
else
    echo "❌ Error: .env.anonymization not found!"
    exit 1
fi

echo "   NETBOX_ANON_URL: $NETBOX_ANON_URL"
echo "   ANONYMIZATION_ENABLED: $ANONYMIZATION_ENABLED"
echo "   ANONYMIZATION_MODE: $ANONYMIZATION_MODE"
echo "   NETBOX_ANON_TOKEN: ${NETBOX_ANON_TOKEN:0:10}..."
echo ""
echo "📊 Backend will be available at: http://localhost:8003"
echo "🔌 WebSocket endpoint: ws://localhost:8003/ws/chat"
echo ""
echo "⚠️  IMPORTANT: Anonymized Netbox must be running at http://localhost:8001"
echo "   Start it with: docker compose -f docker/docker-compose.anonymization.yml up -d netbox-anon"
echo ""

# Start the server on port 8003
uv run uvicorn backend.api:app --reload --port 8003
