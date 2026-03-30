#!/bin/bash
# Start the Production (Non-Anonymized) Frontend
# Runs on port 3001, connects to backend on port 8002

set -e

echo "🌐 Starting Production (Non-Anonymized) Frontend..."
echo "   Configuration: frontend/.env.production"
echo "   Port: 3001"
echo "   Backend: http://localhost:8002"
echo ""

cd frontend

# Use production environment
if [ -f .env.production ]; then
    cp .env.production .env
    echo "✅ Loaded frontend/.env.production"
else
    echo "❌ Error: frontend/.env.production not found!"
    exit 1
fi

echo ""
echo "🌐 Frontend will be available at: http://localhost:3001"
echo "🔌 Connecting to backend: ws://localhost:8002/ws/chat"
echo ""
echo "⚠️  IMPORTANT: Production backend must be running on port 8002"
echo "   Start it in another terminal: ./start_production_backend.sh"
echo ""

# Start the frontend
npm run dev
