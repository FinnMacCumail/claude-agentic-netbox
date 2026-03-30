#!/bin/bash
# Start the Anonymized Frontend
# Runs on port 3002, connects to backend on port 8003

set -e

echo "🌐 Starting Anonymized Frontend..."
echo "   Configuration: frontend/.env.anonymization"
echo "   Port: 3002"
echo "   Backend: http://localhost:8003"
echo ""

cd frontend

# Use anonymization environment
if [ -f .env.anonymization ]; then
    cp .env.anonymization .env
    echo "✅ Loaded frontend/.env.anonymization"
else
    echo "❌ Error: frontend/.env.anonymization not found!"
    exit 1
fi

echo ""
echo "🌐 Frontend will be available at: http://localhost:3002"
echo "🔌 Connecting to backend: ws://localhost:8003/ws/chat"
echo ""
echo "⚠️  IMPORTANT: Anonymized backend must be running on port 8003"
echo "   Start it in another terminal: ./start_anonymized_backend.sh"
echo ""
echo "⚠️  IMPORTANT: Anonymized Netbox must be running at http://localhost:8001"
echo "   Start it with: docker compose -f docker/docker-compose.anonymization.yml up -d netbox-anon"
echo ""

# Start the frontend
npm run dev
