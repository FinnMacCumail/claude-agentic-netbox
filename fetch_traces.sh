#!/bin/bash
"""
Fetch traces from LangSmith for the netbox-chatbox application.

Usage:
    ./fetch_traces.sh [limit] [minutes]

Arguments:
    limit    - Number of traces to fetch (default: 20)
    minutes  - Fetch traces from last N minutes (default: 60)

Examples:
    ./fetch_traces.sh           # Fetch 20 traces from last hour
    ./fetch_traces.sh 50        # Fetch 50 traces from last hour
    ./fetch_traces.sh 10 30     # Fetch 10 traces from last 30 minutes
"""

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configuration
PROJECT_UUID="${LANGCHAIN_PROJECT_UUID:-your-project-uuid-here}"
OUTPUT_DIR="./langsmith-traces"
LIMIT=${1:-20}
MINUTES=${2:-60}

# Validate required environment variables
if [ -z "$LANGCHAIN_API_KEY" ]; then
    echo "❌ Error: LANGCHAIN_API_KEY not set"
    echo "Please set it in your .env file or export it:"
    echo "  export LANGCHAIN_API_KEY=lsv2_..."
    exit 1
fi

if [ "$PROJECT_UUID" = "your-project-uuid-here" ]; then
    echo "❌ Error: LANGCHAIN_PROJECT_UUID not set"
    echo "Please set it in your .env file or export it:"
    echo "  export LANGCHAIN_PROJECT_UUID=your-actual-uuid"
    echo ""
    echo "Find your project UUID in LangSmith at:"
    echo "  https://smith.langchain.com/settings"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "🔍 Fetching traces from LangSmith..."
echo "   Project UUID: $PROJECT_UUID"
echo "   Output Dir: $OUTPUT_DIR"
echo "   Limit: $LIMIT traces"
echo "   Time Range: Last $MINUTES minutes"
echo ""

# Fetch traces using langsmith-fetch
uv run langsmith-fetch traces "$OUTPUT_DIR" \
    --project-uuid "$PROJECT_UUID" \
    --limit "$LIMIT" \
    --last-n-minutes "$MINUTES" \
    --format json

if [ $? -eq 0 ]; then
    TRACE_COUNT=$(ls -1 "$OUTPUT_DIR"/*.json 2>/dev/null | wc -l)
    echo ""
    echo "✅ Successfully fetched traces!"
    echo "📊 Total traces downloaded: $TRACE_COUNT"
    echo "📁 Location: $OUTPUT_DIR/"
    echo ""
    echo "Next steps:"
    echo "  1. Run analysis: uv run python analyze_traces.py"
    echo "  2. View traces in LangSmith: https://smith.langchain.com/"
else
    echo ""
    echo "❌ Failed to fetch traces"
    echo "Please check your LANGCHAIN_API_KEY and project UUID"
    exit 1
fi
