# Netbox Chatbox - AI-Powered Netbox Query Interface

A full-stack natural language interface for querying Netbox infrastructure data using Claude AI and the Claude Agent SDK.

![Main Interface](docs/screenshots/main-interface.png)

## Features

### Core Capabilities
- **Natural Language Queries**: Ask questions about your Netbox data in plain English
- **Real-time Streaming**: WebSocket-based streaming responses for instant feedback
- **MCP Integration**: Uses Netbox MCP server for secure, structured API access
- **Continuous Conversations**: Maintains context across multiple queries

### Web Interface (New!)
- **Modern Chat UI**: Full-featured web interface built with Nuxt 3
- **Model Selection**: Choose between Claude models (Auto, Haiku, Sonnet, Opus) with intelligent routing
- **Conversation Management**: Multiple conversations with sidebar navigation
- **Message Editing**: Edit and re-send previous messages
- **Professional Tables**: Syntax-highlighted table rendering for structured data
- **Session Reset**: Clear conversation context without losing history
- **Auto-reconnect**: Automatic WebSocket reconnection with exponential backoff

### Developer Experience
- **CLI Tool**: Interactive command-line interface with REPL mode
- **Type-Safe**: Built with Pydantic models and TypeScript
- **Well-Tested**: 83+ unit tests covering all functionality
- **MCP v1.1 Compatible**: Enhanced field filtering and API patterns

## Prerequisites

- Python 3.13+
- Node.js 18+ (for web interface)
- uv (Python package manager)
- Running Netbox instance with API access
- Anthropic API key

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/YOUR_USERNAME/netbox-chatbox.git
cd netbox-chatbox

# Install backend dependencies
uv sync

# Install frontend dependencies
cd frontend
npm install
cp .env.example .env  # Frontend WebSocket configuration
cd ..
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your values:
# - ANTHROPIC_API_KEY: Your Claude API key
# - NETBOX_URL: Your Netbox instance URL
# - NETBOX_TOKEN: Your Netbox API token
```

### 3. Start the Application

**Terminal 1 - Backend:**
```bash
./start_server.sh
# Server starts on http://localhost:8001
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
# UI available at http://localhost:3000
```

### 4. Open the Web Interface

Navigate to `http://localhost:3000` and start chatting with your Netbox data!

![Table Rendering](docs/screenshots/table-rendering.png)

## Usage

### Web Interface (Recommended)

The easiest way to interact with Netbox is through the web interface at `http://localhost:3000`. Features include:

- **Chat Interface**: Natural language queries with real-time responses
- **Model Selection**: Switch between Claude models (Auto, Haiku, Sonnet, Opus) - see [Model Selection Guide](docs/MODEL_SELECTION.md)
- **Conversation Management**: Create, switch between, and manage multiple conversations
- **Message Editing**: Edit and re-send previous messages
- **Session Reset**: Clear Claude's context while preserving chat history
- **Professional Tables**: Beautifully formatted data tables with syntax highlighting

![Edit Message Feature](docs/screenshots/edit-message.png)

### CLI Tool

For command-line usage, the CLI provides both interactive and one-shot modes:

#### Single Query Mode

Execute a query and exit:

```bash
# Simple query
uv run python netbox_cli.py "List all sites"

# With verbose output (shows tool usage)
uv run python netbox_cli.py --verbose "Show devices in DC1"

# JSON output (for piping)
uv run python netbox_cli.py --json "List VLANs" | jq .

# Without colors (for piping/logging)
uv run python netbox_cli.py --no-color "Find active devices" | tee query.log
```

#### Interactive Mode

REPL-style interface with command history:

```bash
# Start interactive mode
uv run python netbox_cli.py --interactive

# Or use shorthand
uv run python netbox_cli.py -i
```

Example session:
```
$ uv run python netbox_cli.py -i
🔌 Connecting to Netbox Chatbox...
✅ Connected! Type your query or 'exit' to quit.

netbox> List all sites
🔧 [Using tool: netbox_get_objects]
Here are the 24 sites in your Netbox instance:
[Table with site details...]

netbox> Show devices in DC1
🔧 [Using tool: netbox_get_objects]
Here are the devices in DC1:
[Device details...]

netbox> exit
👋 Goodbye!
```

**Features:**
- ✅ Real-time streaming responses
- ✅ Command history (use up/down arrows)
- ✅ Conversation context maintained within session
- ✅ Colored output with visual indicators
- ✅ Tool usage visibility (with `--verbose`)

#### CLI Options

```
usage: netbox_cli.py [-h] [-i] [-v] [--json] [--no-color]
                      [--url URL] [--timeout TIMEOUT] [query]

Options:
  query                 Query to execute (omit for interactive mode)
  -i, --interactive     Run in interactive mode (REPL)
  -v, --verbose         Show verbose output (tool usage, thinking, etc.)
  --json                Output raw JSON chunks (for piping/processing)
  --no-color            Disable colored output
  --url URL             WebSocket URL (default: ws://localhost:8001/ws/chat)
  --timeout TIMEOUT     Query timeout in seconds (default: 60)
```

### Example Queries

Try these queries with the CLI:

- "List all sites"
- "Show me devices in the datacenter"
- "What VLANs are configured?"
- "Find all devices with status active"
- "Show IP addresses in the 10.0.0.0/8 range"
- "List all racks in site MDF"
- "Show me device details for core-router-1"
- "What IP prefixes exist?"

### WebSocket API (Advanced)

For programmatic access, connect directly to the WebSocket API at `ws://localhost:8001/ws/chat`:

**Client → Server:**
```json
{
  "message": "List all sites in Netbox"
}
```

**Server → Client:**
```json
{
  "type": "text",
  "content": "Here are your Netbox sites...",
  "completed": false
}
```

Final message has `completed: true`.

## Architecture

```
backend/
├── api.py          # FastAPI WebSocket server
├── agent.py        # Claude Agent SDK integration
├── config.py       # Environment configuration
├── mcp_config.py   # MCP server configuration
├── models.py       # Pydantic data models
└── utils.py        # Helper functions

frontend/
├── components/     # Vue components (chat UI)
├── composables/    # WebSocket connection logic
├── pages/          # Main chat interface
├── types/          # TypeScript definitions
└── utils/          # Formatting utilities

tests/              # Pytest unit tests (83 tests)
netbox_cli.py       # Interactive CLI tool
docs/               # Documentation and screenshots
```

### Key Design Patterns

1. **ClaudeSDKClient as Context Manager**: Long-lived sessions for continuous conversations
2. **WebSocket Streaming**: Real-time response delivery
3. **MCP Server Integration**: Secure, structured Netbox API access via stdio subprocess
4. **Type Safety**: Pydantic models throughout
5. **Async/Await**: Full async support for performance

## Data Anonymization (Enterprise Security)

The application includes a complete anonymization solution that allows you to query Netbox data through Claude without exposing sensitive infrastructure information. This feature creates an anonymized copy of your production database that Claude queries instead of real data.

### Why Use Anonymization?

- **Security**: Real production data (IPs, device names, locations) never reaches Claude API
- **Compliance**: Meet GDPR, HIPAA, and SOC2 requirements for data protection
- **Business Value**: Enable AI insights without security risks
- **Transparency**: Users see real values while Claude only sees anonymized data

### How It Works

1. **Greenmask** creates an anonymized copy of your Netbox database
2. **MCP Server** queries the anonymized database instead of production
3. **Query Anonymizer** translates user queries to use anonymized values
4. **Response Restorer** converts anonymized responses back to real values
5. **Users** never see anonymized data - everything appears normal

### Prerequisites

- **Existing Netbox instance** running at `http://localhost:8000`
- Docker and Docker Compose installed
- Access to your Netbox database credentials

### Quick Setup

#### 1. Configure Anonymization

```bash
# Copy anonymization environment template
cp .env.anonymization.example .env.anonymization

# Edit .env.anonymization to set:
# - ANTHROPIC_API_KEY=<your-api-key>
# - ANONYMIZATION_ENABLED=true
# - ANONYMIZATION_SEED=<secure-random-seed>
# - SOURCE_DB_PASSWORD=<your-actual-db-password>
#
# Get your database password:
docker inspect netbox-docker-postgres-1 --format '{{json .Config.Env}}' | grep POSTGRES_PASSWORD
```

#### 2. Start Anonymized Netbox Instance

```bash
# Start only the anonymized instance (uses your existing Netbox at port 8000)
docker compose -f docker/docker-compose.anonymization.yml up -d netbox-anon
```

#### 3. Create Anonymized Database

```bash
# IMPORTANT: Ensure your existing Netbox is running first!
docker ps | grep netbox-docker-netbox-1

# Run Greenmask to copy and anonymize data from your existing database
docker compose -f docker/docker-compose.anonymization.yml run --rm greenmask

# This connects to your existing Netbox database and creates an anonymized copy:
# - Device names: "core-switch-nyc-01" → "device-7a3f2b"
# - IP addresses: "192.168.1.10" → "10.234.56.78"
# - Sites: "NYC-DC1" → "site-9x4k1"
```

#### 4. Import Mappings

```bash
# Import Greenmask mappings for query/response translation
python scripts/import_mappings.py docker/greenmask/mappings/mappings_latest.json
```

#### 5. Validate Anonymization

```bash
# Check that no PII exists in anonymized database
python scripts/validate_anonymization.py \
  --database postgresql://netbox:netbox@localhost:5433/netbox_anonymized
```

#### 6. Start Application

```bash
# Backend uses .env.anonymization configuration (anonymized database)
# Make sure to copy it to .env or set it as active environment
cp .env.anonymization .env

./start_server.sh

# Frontend (in another terminal)
cd frontend && npm run dev
```

### Example Query Flow

1. **User asks**: "What's the status of core-switch-nyc-01?"
2. **Query anonymized**: "core-switch-nyc-01" → "device-7a3f2b"
3. **Claude queries**: Anonymized database for "device-7a3f2b"
4. **Claude responds**: "device-7a3f2b is active"
5. **Response restored**: "device-7a3f2b" → "core-switch-nyc-01"
6. **User sees**: "core-switch-nyc-01 is active"

### Anonymization Details

For complete documentation on the anonymization architecture, see:
- [Anonymization Solution Report](docs/development/anonymization/ANONYMIZATION_SOLUTION_REPORT.md)
- [Greenmask Configuration](docs/development/anonymization/greenmask-config-complete.yml)
- [Development Strategy](docs/development/anonymization/DEVELOPMENT_STRATEGY.md)

## Testing

Run all unit tests:
```bash
uv run pytest
```

Run with coverage:
```bash
uv run pytest --cov=backend --cov-report=term-missing
```

Current coverage: 83 tests (59 backend + 24 CLI), all passing ✅

## LangSmith Tracing (Optional)

LangSmith provides observability and debugging for Claude Agent interactions. When enabled, all agent queries, tool invocations, and model interactions are automatically traced.

### Setup

1. **Get a LangSmith API key** from [https://smith.langchain.com/settings](https://smith.langchain.com/settings)

2. **Update your `.env` file**:
   ```bash
   # Enable LangSmith tracing
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your-langsmith-api-key-here
   LANGCHAIN_PROJECT=netbox-chatbox
   ```

3. **Restart the backend server**:
   ```bash
   ./start_server.sh
   ```

### What Gets Traced

- ✅ Agent queries and responses
- ✅ Tool invocations (netbox_get_objects, netbox_search_objects, etc.)
- ✅ Claude model interactions
- ✅ MCP server operations
- ✅ Multi-turn conversation context
- ✅ Performance metrics (duration, token usage)

### Viewing Traces

Visit [https://smith.langchain.com](https://smith.langchain.com) and navigate to your project to view detailed traces of all agent interactions.

### Disabling Tracing

Set `LANGCHAIN_TRACING_V2=false` in `.env` or remove the variable entirely. Tracing is **disabled by default**.

### Analyzing Traces

Fetch and analyze your LangSmith traces locally using `langsmith-fetch`:

```bash
# Fetch traces (default: 20 traces from last hour)
./fetch_traces.sh

# Fetch specific number of traces from custom time range
./fetch_traces.sh 50 1440  # 50 traces from last 24 hours

# Analyze fetched traces
uv run python analyze_traces.py

# View the generated report
cat trace_analysis_report.md
```

**What the Analysis Provides:**
- Completion rates and conversation metrics
- Tool usage patterns and frequency
- Sample user queries
- Performance insights and recommendations
- Detailed per-trace breakdown

Traces are saved to `./langsmith-traces/` and analyzed locally without needing to open the LangSmith web interface.

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.

Most common issue: **MCP 403 Forbidden Error**
- **Cause**: Wrong NETBOX_TOKEN in shell environment
- **Fix**: Use `./start_server.sh` to ensure correct environment
- **Details**: See [MCP_403_FIX.md](docs/troubleshooting/MCP_403_FIX.md)

## API Endpoints

### WebSocket `/ws/chat`

Bidirectional streaming chat interface.

**Client → Server - Message:**
```json
{
  "message": "your query here"
}
```

**Client → Server - Model Change:**
```json
{
  "type": "model_change",
  "model": "claude-sonnet-4-5-20250929"
}
```

**Server → Client:**
```json
{
  "type": "text|tool_use|error|model_changed",
  "content": "response content",
  "completed": false|true,
  "metadata": {
    "model": {
      "model": "claude-sonnet-4-5-20250929",
      "model_display": "Claude Sonnet 4.5",
      "is_automatic": false
    }
  }
}
```

See [Model Selection Guide](docs/MODEL_SELECTION.md) for details on intelligent routing.

### GET `/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "netbox-chatbox-api",
  "version": "0.1.0"
}
```

### GET `/models`

Get available Claude models.

**Response:**
```json
[
  {
    "id": "auto",
    "name": "Claude (Automatic Selection)",
    "provider": "anthropic",
    "available": true
  },
  {
    "id": "claude-sonnet-4-5-20250929",
    "name": "Claude Sonnet 4.5",
    "provider": "anthropic",
    "available": true
  },
  {
    "id": "claude-opus-4-20250514",
    "name": "Claude Opus 4",
    "provider": "anthropic",
    "available": true
  },
  {
    "id": "claude-haiku-4-5-20250925",
    "name": "Claude Haiku 4.5",
    "provider": "anthropic",
    "available": true
  }
]
```

## Development

### Project Structure

- `backend/` - Core application code
- `tests/` - Pytest unit tests
- `.env` - Environment configuration (not committed)
- `docs/development/PLANNING.md` - Architecture and design decisions
- `docs/development/TASK.md` - Task tracking

### Adding New Features

1. Check `docs/development/TASK.md` for existing tasks
2. Add new task with description and date
3. Implement with unit tests
4. Mark task as completed in `docs/development/TASK.md`

### Code Style

- Follow PEP8
- Use type hints everywhere
- Document functions with Google-style docstrings
- Format with `black`
- Files must be < 500 lines (split if larger)

## MCP Server Configuration

The Netbox MCP server is configured in [backend/mcp_config.py](backend/mcp_config.py:1-50).

**Location:** `/home/ola/dev/rnd/mcp/testmcp/netbox-mcp-server/server.py`

**Environment Variables Passed:**
- `NETBOX_URL`: Netbox instance URL
- `NETBOX_TOKEN`: API authentication token
- `LOG_LEVEL`: Logging verbosity

**Available Tools:**
- `netbox_get_objects`: Query Netbox objects with filters
- `netbox_get_object_by_id`: Get specific object details
- `netbox_create_object`: Create new Netbox objects
- `netbox_update_object`: Update existing objects
- `netbox_delete_object`: Delete objects

## Security

- API tokens stored in `.env` (not committed)
- MCP server runs as subprocess with explicit env vars
- CORS configured for specified origins only
- Read-only token recommended for MCP server

## Performance

- WebSocket for low-latency streaming
- Async/await throughout for concurrency
- Claude Agent SDK handles rate limiting
- MCP server connection pooling

## Future Enhancements

See `docs/development/TASK.md` for potential improvements:
- User authentication (OAuth, JWT)
- Query history export/import
- Multi-user support with separate sessions
- Advanced filtering and search operators
- Docker containerization
- Kubernetes deployment manifests
- Real-time collaboration features

## License

MIT License - see [LICENSE](LICENSE) file for details

## Contributing

1. Check `CLAUDE.md` for coding guidelines
2. Follow the patterns in `PLANNING.md`
3. Add unit tests for all new code
4. Update `TASK.md` with your work

## Support

For issues, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or create an issue in the repository.
