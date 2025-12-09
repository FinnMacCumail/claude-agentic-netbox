# Project Planning Document

## Project Overview

**Name**: Netbox Chatbox with Claude Agent SDK

**Purpose**: Full-stack web application that enables natural language interactions with Netbox infrastructure data through Claude AI, utilizing the Netbox MCP server for data access.

**Tech Stack**:
- **Backend**: Python 3.10+ with FastAPI, Claude Agent SDK, python-dotenv
- **Frontend**: Nuxt.js 4.x with TypeScript, WebSocket
- **Integration**: Netbox MCP server (stdio-based MCP tools)
- **Testing**: Pytest for backend, unit and integration tests

## Architecture

### High-Level Architecture

```
┌─────────────────┐         WebSocket          ┌─────────────────┐
│   Nuxt.js UI    │◄────────────────────────────│  FastAPI Server │
│   (Frontend)    │                             │    (Backend)    │
└─────────────────┘                             └────────┬────────┘
                                                         │
                                                         │ Uses
                                                         ▼
                                                ┌────────────────┐
                                                │ ClaudeSDKClient│
                                                │  (Agent SDK)   │
                                                └────────┬───────┘
                                                         │
                                                         │ MCP Tools
                                                         ▼
                                                ┌────────────────┐
                                                │ Netbox MCP     │
                                                │    Server      │
                                                └────────┬───────┘
                                                         │
                                                         │ API Calls
                                                         ▼
                                                ┌────────────────┐
                                                │  Netbox REST   │
                                                │      API       │
                                                └────────────────┘
```

### Backend Structure

```
backend/
├── __init__.py              # Package initialization
├── agent.py                 # Claude Agent logic with ClaudeSDKClient
├── api.py                   # FastAPI app, routes, WebSocket endpoints
├── config.py                # Configuration management (env vars)
├── mcp_config.py            # Netbox MCP server configuration
├── models.py                # Pydantic models for API
└── utils.py                 # Helper functions and utilities
```

### Frontend Structure

```
frontend/
├── nuxt.config.ts           # Nuxt config with WebSocket
├── app.vue                  # Root component
├── pages/
│   └── index.vue            # Chat interface page
├── components/
│   ├── ChatMessage.vue      # Individual message component
│   ├── ChatInput.vue        # Input component
│   └── ChatHistory.vue      # Message history component
└── composables/
    └── useChatSocket.ts     # WebSocket connection logic
```

### Testing Structure

```
tests/
├── __init__.py
├── test_config.py           # Configuration tests
├── test_mcp_config.py       # MCP configuration tests
├── test_agent.py            # Agent logic tests
├── test_api.py              # API endpoint tests
└── conftest.py              # Pytest fixtures
```

## Core Principles

1. **Context is King**: Full integration with Netbox MCP server and Claude Agent SDK
2. **Validation Loops**: Comprehensive testing at unit, integration, and E2E levels
3. **Information Dense**: Type-safe, well-documented code with clear patterns
4. **Progressive Success**: Build backend first, then frontend, validate at each step
5. **Global Rules**: Follow all rules in CLAUDE.md

## Design Patterns

### Backend Patterns

1. **Configuration Management**:
   - Use `python-dotenv` to load `.env` file
   - Validate all required environment variables at startup
   - Centralize configuration in `config.py`

2. **Agent Session Management**:
   - Use `ClaudeSDKClient` as async context manager
   - One agent session per WebSocket connection
   - Always clean up sessions on disconnect
   - Support explicit model selection via `model` parameter
   - **Note**: SDK uses intelligent routing - the specified model controls response quality while tool execution uses Haiku for cost optimization

3. **Model Selection & Intelligent Routing**:
   - Provide model selector UI (Auto, Haiku, Sonnet, Opus)
   - User's selection sets target quality level
   - SDK automatically uses Haiku for MCP tool calls (70-80% cost savings)
   - Final responses use the selected model
   - See [docs/MODEL_SELECTION.md](../MODEL_SELECTION.md) for detailed explanation

4. **WebSocket Streaming**:
   - Stream responses in real-time using `StreamChunk` objects
   - Type-safe message processing (check `isinstance()` for all messages)
   - Graceful error handling with error chunks
   - Support model_change messages for switching models mid-session

5. **MCP Server Integration**:
   - Use `McpStdioServerConfig` for Netbox MCP server
   - Pass environment variables through MCP config
   - Use absolute paths to server location

### Frontend Patterns

1. **Composables**:
   - Use Vue composables for shared logic (WebSocket connection)
   - Reactive state management with `ref()`
   - Lifecycle management with `onMounted/onUnmounted`

2. **Component Communication**:
   - Props down, events up
   - Use TypeScript interfaces for type safety
   - Emit custom events for user interactions

3. **WebSocket Management**:
   - Auto-reconnect on disconnect
   - Handle connection errors gracefully
   - Stream response accumulation

## Naming Conventions

### Python (Backend)

- **Files**: Snake case (`config.py`, `mcp_config.py`)
- **Classes**: Pascal case (`ChatAgent`, `StreamChunk`)
- **Functions**: Snake case (`get_netbox_mcp_config()`)
- **Variables**: Snake case (`session_active`, `current_message`)
- **Constants**: Upper snake case (`NETBOX_URL`, `API_KEY`)

### TypeScript (Frontend)

- **Files**: Camel case or Pascal case (`useChatSocket.ts`, `ChatMessage.vue`)
- **Interfaces**: Pascal case (`ChatMessage`, `StreamChunk`)
- **Functions**: Camel case (`sendMessage()`, `connect()`)
- **Variables**: Camel case (`isLoading`, `currentResponse`)
- **Components**: Pascal case (`ChatMessage`, `ChatInput`)

## Code Style

### Python Style

- Follow PEP8
- Use type hints for all function parameters and return values
- Format with `black` (line length: 88)
- Lint with `ruff`
- Type check with `mypy`
- Write Google-style docstrings for all functions

Example:
```python
def get_netbox_mcp_config(config: Config) -> dict[str, Any]:
    """
    Create Netbox MCP server configuration.

    Args:
        config: Application configuration object

    Returns:
        dict: MCP server configuration for ClaudeAgentOptions

    Raises:
        ValueError: If required configuration is missing
    """
    # Implementation
```

### TypeScript Style

- Use TypeScript strict mode
- Define interfaces for all data structures
- Use const for immutable values
- Use async/await for asynchronous operations
- Add JSDoc comments for exported functions

Example:
```typescript
/**
 * Connect to the chat WebSocket server.
 *
 * @returns void
 */
const connect = (): void => {
  // Implementation
}
```

## Environment Variables

Required environment variables:

```bash
# Claude Agent SDK
ANTHROPIC_API_KEY=sk-ant-xxx  # Required for Claude API access

# Netbox Configuration
NETBOX_URL=http://localhost:8000  # URL to Netbox instance
NETBOX_TOKEN=xxxx                 # Read-only API token

# Optional Configuration
LOG_LEVEL=INFO                    # Logging level (DEBUG, INFO, WARNING, ERROR)
CORS_ORIGINS=http://localhost:3000  # Allowed CORS origins
```

## Dependencies

### Backend (pyproject.toml)

```toml
[project]
name = "netbox-chatbox-backend"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "claude-agent-sdk>=1.0.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.27.0",
    "black>=24.0.0",
    "ruff>=0.6.0",
    "mypy>=1.11.0",
]
```

### Frontend (package.json)

```json
{
  "name": "netbox-chatbox-frontend",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "nuxt dev",
    "build": "nuxt build",
    "preview": "nuxt preview"
  },
  "dependencies": {
    "nuxt": "^4.0.0",
    "vue": "latest"
  },
  "devDependencies": {
    "@nuxt/typescript-build": "latest",
    "typescript": "latest"
  }
}
```

## Critical Implementation Notes

### ClaudeSDKClient Pattern

**CRITICAL**: Always use async context manager pattern:

```python
# ✅ CORRECT
async with ClaudeSDKClient(options) as client:
    await client.query("prompt")
    async for message in client.receive_response():
        # Process messages

# ❌ WRONG
client = ClaudeSDKClient(options)
await client.connect()  # Manual connection management
```

### Async Iteration Pattern

**CRITICAL**: Avoid using `break` in async iteration:

```python
# ✅ CORRECT
found_result = False
async for message in client.receive_response():
    if isinstance(message, ResultMessage):
        found_result = True
    if found_result:
        continue  # Let iteration complete naturally

# ❌ WRONG
async for message in client.receive_response():
    if isinstance(message, ResultMessage):
        break  # Can cause asyncio cleanup issues
```

### Nuxt WebSocket Configuration

**CRITICAL**: WebSocket is EXPERIMENTAL in Nuxt 3/4. Must enable explicitly:

```typescript
// nuxt.config.ts
export default defineNuxtConfig({
  nitro: {
    experimental: {
      websocket: true
    }
  }
})
```

### MCP Server Configuration

**CRITICAL**: Use absolute paths and pass env vars:

```python
mcp_servers = {
    "netbox": {
        "type": "stdio",
        "command": "uv",
        "args": [
            "--directory",
            "/home/ola/dev/rnd/mcp/testmcp/netbox-mcp-server",
            "run",
            "server.py"
        ],
        "env": {
            "NETBOX_URL": os.getenv("NETBOX_URL"),
            "NETBOX_TOKEN": os.getenv("NETBOX_TOKEN")
        }
    }
}
```

### Type Safety

**CRITICAL**: Always check message types:

```python
# ✅ CORRECT
if isinstance(message, AssistantMessage):
    for block in message.content:
        if isinstance(block, TextBlock):
            text = block.text  # Safe access

# ❌ WRONG
text = message.content[0].text  # AttributeError if type is wrong
```

## Testing Strategy

### Unit Tests

- Test each module in isolation
- Mock external dependencies (ClaudeSDKClient, Netbox MCP)
- Aim for >80% code coverage
- Run with: `uv run pytest tests/ -v --cov=backend`

### Integration Tests

- Test backend + MCP server integration
- Test WebSocket connection and streaming
- Use real Netbox MCP server (test mode)
- Validate end-to-end message flow

### E2E Tests

- Test full application (backend + frontend + MCP)
- Manual testing in browser
- Validate conversation context preservation
- Test error scenarios

## Security Considerations

1. **API Keys**: Never commit to version control
2. **Netbox Token**: Use read-only token with minimal permissions
3. **CORS**: Restrict to specific origins in production
4. **Input Validation**: Validate all user inputs
5. **Error Messages**: Don't expose sensitive information
6. **WebSocket Auth**: Add authentication in production

## Performance Considerations

1. **Session Management**: One session per WebSocket connection
2. **Streaming**: Use streaming for real-time feedback
3. **Resource Cleanup**: Always close sessions on disconnect
4. **Connection Pooling**: Consider for Netbox API calls
5. **Caching**: Cache frequently requested data

## Development Workflow

1. **Create feature branch** (if using git)
2. **Write unit tests first** (TDD approach)
3. **Implement feature** following patterns
4. **Run validation loops** (format, lint, type check)
5. **Run tests** and ensure all pass
6. **Update documentation** if needed
7. **Mark task complete** in TASK.md

## Validation Checklist

Before considering any task complete:

- [ ] Code follows style guide (PEP8 for Python, TypeScript strict mode)
- [ ] All functions have type hints (Python) or types (TypeScript)
- [ ] All functions have docstrings/JSDoc comments
- [ ] Unit tests written and passing
- [ ] No linting errors (`ruff check` or ESLint)
- [ ] No type errors (`mypy` or `tsc`)
- [ ] Code formatted (`black` or Prettier)
- [ ] Manual testing performed
- [ ] Documentation updated
- [ ] Task marked in TASK.md

## Known Issues and Workarounds

### Issue: WebSocket disconnections

**Symptom**: WebSocket closes unexpectedly

**Solution**: Implement auto-reconnect with exponential backoff in frontend

### Issue: MCP server startup failures

**Symptom**: MCP server not found or fails to start

**Solution**: Verify absolute path to server.py, ensure `uv` is in PATH

### Issue: Type errors in message processing

**Symptom**: AttributeError when accessing message fields

**Solution**: Always use `isinstance()` checks before accessing message fields

## Future Enhancements

1. User authentication (OAuth, JWT)
2. Session persistence (database)
3. Multi-user support
4. Conversation history
5. Export conversations
6. Docker deployment
7. Production monitoring
8. Rate limiting
9. API documentation (Swagger)
10. Advanced error recovery

## References

- [Claude Agent SDK Python Docs](https://docs.claude.com/en/docs/agent-sdk/python)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Nuxt.js 4 Documentation](https://nuxt.com/docs)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Pytest Documentation](https://docs.pytest.org/)
