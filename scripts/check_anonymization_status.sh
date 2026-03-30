#!/bin/bash

# Check anonymization system status
echo "============================================="
echo "🔍 Anonymization System Status Check"
echo "============================================="
echo ""

# Check mapping file
echo "📁 Mapping Files:"
if [ -f "backend/anonymization/mappings/mappings_latest.json" ]; then
    echo "✅ Mapping file exists"
    MAPPINGS=$(python3 -c "import json; data=json.load(open('backend/anonymization/mappings/mappings_latest.json')); print(data['metadata']['total_mappings'])" 2>/dev/null)
    GENERATED=$(python3 -c "import json; data=json.load(open('backend/anonymization/mappings/mappings_latest.json')); print(data['metadata']['generated_at'])" 2>/dev/null)
    echo "   Total mappings: $MAPPINGS"
    echo "   Generated: $GENERATED"
else
    echo "❌ Mapping file missing"
    echo "   Run: python scripts/generate_mappings.py"
fi
echo ""

# Check anonymization configuration
echo "⚙️ Configuration (.env.anonymization):"
if grep -q "ANONYMIZATION_ENABLED=true" .env.anonymization 2>/dev/null; then
    echo "✅ Anonymization ENABLED"
else
    echo "⚠️ Anonymization DISABLED"
fi

NETBOX_URL=$(grep "^NETBOX_URL=" .env.anonymization 2>/dev/null | cut -d'=' -f2)
if [ "$NETBOX_URL" = "http://localhost:8001" ]; then
    echo "✅ Backend pointing to anonymized Netbox ($NETBOX_URL)"
else
    echo "⚠️ Backend pointing to: $NETBOX_URL"
fi

MAPPINGS_FILE=$(grep "^GREENMASK_MAPPINGS_FILE=" .env.anonymization 2>/dev/null | cut -d'=' -f2)
echo "   Mappings file path: $MAPPINGS_FILE"
echo ""

# Check Docker containers
echo "🐳 Docker Services:"
if docker ps | grep -q "netbox-anon"; then
    echo "✅ Anonymized Netbox is running (localhost:8001)"
else
    echo "❌ Anonymized Netbox is NOT running"
    echo "   Start with: docker compose -f docker/docker-compose.anonymization.yml up -d netbox-anon"
fi

if docker ps | grep -q "netbox-anon-db"; then
    echo "✅ Anonymized database is running (localhost:5433)"
else
    echo "❌ Anonymized database is NOT running"
fi

if docker ps | grep -q "netbox-docker-netbox-1"; then
    echo "✅ Production Netbox is running (localhost:8000)"
else
    echo "⚠️ Production Netbox is NOT running"
fi
echo ""

# Check backend processes
echo "🚀 Backend Processes:"
if lsof -i :8003 2>/dev/null | grep -q LISTEN; then
    echo "✅ Anonymized backend is running (localhost:8003)"
else
    echo "❌ Anonymized backend is NOT running"
    echo "   Start with: ./start_anonymized_backend.sh"
fi

if lsof -i :3002 2>/dev/null | grep -q LISTEN; then
    echo "✅ Anonymized frontend is running (localhost:3002)"
else
    echo "❌ Anonymized frontend is NOT running"
    echo "   Start with: ./start_anonymized_frontend.sh"
fi
echo ""

# Summary
echo "============================================="
echo "📊 Summary"
echo "============================================="

ALL_GOOD=true

if [ ! -f "backend/anonymization/mappings/mappings_latest.json" ]; then
    echo "❌ Missing mapping file"
    ALL_GOOD=false
fi

if ! grep -q "ANONYMIZATION_ENABLED=true" .env.anonymization 2>/dev/null; then
    echo "⚠️ Anonymization disabled in config"
    ALL_GOOD=false
fi

if ! docker ps | grep -q "netbox-anon" 2>/dev/null; then
    echo "❌ Anonymized Netbox not running"
    ALL_GOOD=false
fi

if $ALL_GOOD; then
    echo "✅ Anonymization system is READY"
    echo ""
    echo "To use:"
    echo "1. Start backend: ./start_anonymized_backend.sh"
    echo "2. Start frontend: ./start_anonymized_frontend.sh"
    echo "3. Open: http://localhost:3002"
else
    echo "⚠️ Anonymization system needs setup"
    echo ""
    echo "Fix the issues above, then retry"
fi
echo ""