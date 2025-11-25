name: "Netbox Chatbox with Claude Agent SDK"
description: |
  Complete implementation of a Netbox chatbox application using Claude Agent SDK,
  Netbox MCP server, FastAPI backend, and Nuxt.js frontend with real-time streaming.

## Purpose
Create a full-stack chatbox application that enables natural language interactions with Netbox
infrastructure data through Claude AI, utilizing the Netbox MCP server for data access.

## Core Principles
1. **Context is King**: Full integration with Netbox MCP server and Claude Agent SDK
2. **Validation Loops**: Comprehensive testing at unit, integration, and E2E levels
3. **Information Dense**: Type-safe, well-documented code with clear patterns
4. **Progressive Success**: Build backend first, then frontend, validate at each step
5. **Global rules**: Follow all rules in CLAUDE.md

---

## Goal
Build a production-ready Netbox chatbox that allows users to query Netbox infrastructure data
using natural language through Claude AI, with real-time streaming responses and continuous
conversation support.

## Why
- **Business value**: Democratize Netbox data access for non-technical users
- **Integration**: Leverage existing Netbox MCP server for read-only data access
- **User impact**: Enable quick answers to infrastructure questions without learning Netbox UI
- **Problems solved**: Complex Netbox queries simplified through natural language

## What
A full-stack web application with:
- **Backend**: Python FastAPI with ClaudeSDKClient for continuous conversations
- **Frontend**: Nuxt.js 4.x chat interface with real-time WebSocket streaming
- **Integration**: Netbox MCP server tools accessible through Claude AI
- **Authentication**: Secure Anthropic API key and Netbox token management

### Success Criteria
- [ ] User can send natural language queries about Netbox data
- [ ] Claude AI responds with accurate Netbox information using MCP tools
- [ ] Responses stream in real-time to the frontend
- [ ] Conversation context is maintained across multiple queries
- [ ] Application handles errors gracefully (MCP failures, API errors)
- [ ] All tests pass (unit, integration, E2E)
- [ ] Code follows project conventions (CLAUDE.md)

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window

- url: https://github.com/anthropics/claude-agent-sdk-python
  why: Official Python SDK repository with examples and patterns
  critical: Use ClaudeSDKClient (not query()) for continuous conversations

- url: https://docs.claude.com/en/docs/agent-sdk/python
  why: Complete API reference for ClaudeSDKClient, options, and message types
  critical: Async context manager pattern, type-safe message processing

- url: https://platform.claude.com/docs/en/agent-sdk/overview
  why: Agent SDK overview, authentication, session management
  critical: ANTHROPIC_API_KEY environment variable required

- file: /home/ola/dev/rnd/mcp/testmcp/netbox-mcp-server/server.py
  why: Netbox MCP server implementation with available tools
  critical: Three tools available - netbox_get_objects, netbox_get_object_by_id, netbox_get_changelogs

- file: /home/ola/dev/rnd/mcp/testmcp/netbox-mcp-server/netbox_client.py
  why: Netbox REST client implementation showing API patterns
  critical: Requires NETBOX_URL and NETBOX_TOKEN environment variables

- file: /home/ola/dev/rnd/mcp/testmcp/netbox-mcp-server/.mcp.json
  why: MCP server configuration showing command structure
  critical: Server runs via 'uv run server.py' with env vars

- docfile: examples/claude-agent-sdk-python.md
  why: Complete SDK reference pasted into project
  critical: Shows all available options, message types, and patterns

- url: https://nuxt.com/docs/getting-started/introduction
  why: Nuxt.js 4.x architecture and best practices
  section: Server routes, API endpoints, WebSocket configuration

- url: https://masteringnuxt.com/blog/building-a-realtime-chat-application-with-nuxt-and-socketio
  why: Real-time chat implementation patterns with Nuxt
  critical: WebSocket is experimental in Nuxt, requires explicit config

- url: https://betterstack.com/community/guides/scaling-python/authentication-fastapi/
  why: FastAPI authentication patterns
  critical: Environment variable security, CORS configuration
```

### Current Codebase Tree
```bash
.
├── CLAUDE.md                           # Project rules and conventions
├── examples/
│   └── claude-agent-sdk-python.md      # SDK documentation
├── INITIAL.md                          # Feature specification
├── PRPs/
│   └── templates/
│       └── prp_base.md                 # PRP template
└── README.md                           # Project overview
```

### Desired Codebase Tree
```bash
.
├── CLAUDE.md
├── backend/                            # Python FastAPI backend
│   ├── __init__.py
│   ├── agent.py                        # Claude Agent logic with ClaudeSDKClient
│   ├── api.py                          # FastAPI app, routes, WebSocket
│   ├── config.py                       # Configuration management
│   ├── mcp_config.py                   # Netbox MCP server setup
│   ├── models.py                       # Pydantic models for API
│   └── utils.py                        # Helper functions
├── frontend/                           # Nuxt.js 4.x frontend
│   ├── nuxt.config.ts                  # Nuxt config with WebSocket
│   ├── app.vue                         # Root component
│   ├── pages/
│   │   └── index.vue                   # Chat interface page
│   ├── components/
│   │   ├── ChatMessage.vue             # Individual message component
│   │   ├── ChatInput.vue               # Input component
│   │   └── ChatHistory.vue             # Message history component
│   ├── composables/
│   │   └── useChatSocket.ts            # WebSocket connection logic
│   └── package.json
├── tests/                              # Pytest unit tests
│   ├── __init__.py
│   ├── test_agent.py                   # Agent tests
│   ├── test_api.py                     # API endpoint tests
│   └── test_mcp_config.py              # MCP configuration tests
├── .env.example                        # Example environment variables
├── pyproject.toml                      # Python dependencies
├── uv.lock                             # Locked dependencies
├── README.md                           # Updated with setup instructions
└── TASK.md                             # Task tracking
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: ClaudeSDKClient requires async context manager
# ❌ WRONG:
client = ClaudeSDKClient(options)
await client.connect()  # Manual connection management

# ✅ CORRECT:
async with ClaudeSDKClient(options) as client:
    await client.query("prompt")
    async for message in client.receive_response():
        # Process messages

# CRITICAL: Avoid using break in async iteration
# Can cause asyncio cleanup issues
# ✅ Use flags to track completion instead:
found_result = False
async for message in client.receive_response():
    if isinstance(message, ResultMessage):
        found_result = True
    if found_result:
        continue  # Let iteration complete naturally

# CRITICAL: WebSocket is EXPERIMENTAL in Nuxt 3/4
# Must enable explicitly in nuxt.config.ts:
export default defineNuxtConfig({
  nitro: {
    experimental: {
      websocket: true
    }
  }
})

# CRITICAL: MCP server configuration
# Must use absolute path to server.py and pass env vars:
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

# CRITICAL: Environment variable priority
# Claude SDK prioritizes env vars over other auth methods
# Keep ANTHROPIC_API_KEY unset unless intentionally using API key

# CRITICAL: python-dotenv must load BEFORE any imports that use env vars
from dotenv import load_dotenv
load_dotenv()  # Must be first!
import os  # Now env vars are available

# GOTCHA: FastAPI WebSocket requires proper error handling
# WebSocket connections can close unexpectedly
try:
    await websocket.send_json(data)
except WebSocketDisconnect:
    logger.warning("WebSocket disconnected")
    # Clean up resources

# GOTCHA: Type checking for Claude messages
# Always check message types to avoid AttributeError
if isinstance(message, AssistantMessage):
    for block in message.content:
        if isinstance(block, TextBlock):
            text = block.text  # Safe access
```

## Implementation Blueprint

### Architecture Overview

The application follows a clean separation between backend and frontend:

1. **Backend (FastAPI)**: Manages Claude SDK client, MCP server integration, and WebSocket streaming
2. **Frontend (Nuxt.js)**: Provides chat UI with real-time updates via WebSocket
3. **Integration**: Netbox MCP server provides tools for Netbox data access

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

### Data Models and Structure

```python
# backend/models.py
from pydantic import BaseModel, Field
from typing import Literal, Optional, List
from datetime import datetime

class ChatMessage(BaseModel):
    """Single chat message from user or assistant."""
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatRequest(BaseModel):
    """User request to send a message."""
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    """Response from assistant."""
    message: str
    session_id: str
    completed: bool

class StreamChunk(BaseModel):
    """Streaming response chunk."""
    type: Literal["text", "tool_use", "tool_result", "thinking", "error"]
    content: str
    completed: bool = False

class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    details: Optional[str] = None
```

### List of Tasks in Implementation Order

```yaml
Task 1: Setup Backend Project Structure
CREATE backend/ directory with Python project files:
  - PRESERVE existing venv_linux (mentioned in CLAUDE.md)
  - CREATE pyproject.toml with dependencies:
      * fastapi
      * uvicorn[standard]
      * claude-agent-sdk
      * python-dotenv
      * pydantic
      * pytest
      * httpx (for testing)
  - CREATE .env.example with required variables
  - CREATE backend/__init__.py
  - RUN: uv sync to install dependencies

Task 2: Implement Configuration Management
CREATE backend/config.py:
  - PATTERN: Use python-dotenv for environment variables
  - LOAD .env file at module level
  - VALIDATE required env vars (ANTHROPIC_API_KEY, NETBOX_URL, NETBOX_TOKEN)
  - PROVIDE configuration class with type hints
  - INJECT validation error messages for missing vars

Task 3: Implement Netbox MCP Server Configuration
CREATE backend/mcp_config.py:
  - PATTERN: Follow .mcp.json structure from Netbox MCP server
  - CONSTRUCT McpStdioServerConfig for Netbox
  - USE absolute path to Netbox MCP server directory
  - PASS NETBOX_URL and NETBOX_TOKEN via env dict
  - RETURN configuration dict for ClaudeAgentOptions

Task 4: Implement Pydantic Models
CREATE backend/models.py:
  - PATTERN: Use pydantic BaseModel for validation
  - DEFINE ChatMessage, ChatRequest, ChatResponse, StreamChunk, ErrorResponse
  - ADD field validators where appropriate
  - INCLUDE docstrings for each model

Task 5: Implement Claude Agent Logic
CREATE backend/agent.py:
  - PATTERN: Use ClaudeSDKClient as async context manager
  - IMPORT ClaudeAgentOptions, ClaudeSDKClient from claude_agent_sdk
  - CREATE ChatAgent class:
      * __init__ with options configuration
      * async start_session() - create ClaudeSDKClient context
      * async query(message: str) -> AsyncIterator[StreamChunk]
      * async close_session() - cleanup
  - CONFIGURE options with:
      * mcp_servers from mcp_config
      * allowed_tools for Netbox MCP (mcp__netbox__*)
      * system_prompt with Claude Code preset
      * permission_mode='acceptEdits'
  - IMPLEMENT type-safe message processing (AssistantMessage, TextBlock, etc.)
  - HANDLE errors gracefully (CLINotFoundError, ProcessError, etc.)

Task 6: Implement FastAPI Server with WebSocket
CREATE backend/api.py:
  - PATTERN: FastAPI with WebSocket support
  - IMPORT FastAPI, WebSocket, WebSocketDisconnect
  - CREATE FastAPI app with CORS middleware
  - IMPLEMENT WebSocket endpoint /ws/chat:
      * Accept connection
      * Manage ChatAgent session per WebSocket
      * Stream responses as JSON chunks
      * Handle disconnections gracefully
  - IMPLEMENT health check endpoint GET /health
  - IMPLEMENT session management (track active WebSocket connections)
  - ADD error handling middleware

Task 7: Implement Helper Utilities
CREATE backend/utils.py:
  - FUNCTION format_message_for_display(message: Message) -> str
  - FUNCTION extract_text_from_blocks(blocks: List[ContentBlock]) -> str
  - FUNCTION create_stream_chunk(message: Message) -> StreamChunk
  - ADD logging configuration
  - ADD retry logic for transient failures

Task 8: Setup Frontend Project Structure
CREATE frontend/ directory with Nuxt.js project:
  - RUN: npx nuxi init frontend (or manual setup)
  - CONFIGURE nuxt.config.ts:
      * Enable experimental WebSocket support
      * Configure TypeScript strict mode
      * Set up API proxy for development
  - CREATE package.json with dependencies:
      * @nuxt/ui (optional, for components)
      * socket.io-client (if using Socket.IO) OR native WebSocket
  - RUN: npm install

Task 9: Implement WebSocket Composable
CREATE frontend/composables/useChatSocket.ts:
  - PATTERN: Vue composable with WebSocket connection
  - EXPORT useChatSocket() function
  - MANAGE WebSocket connection lifecycle
  - PROVIDE reactive state (connected, messages, loading)
  - IMPLEMENT send(message: string) method
  - HANDLE incoming messages and parse JSON
  - HANDLE connection errors and reconnection
  - USE onMounted/onUnmounted for connection management

Task 10: Implement Chat Components
CREATE frontend/components/ChatMessage.vue:
  - PROPS: message object with role, content, timestamp
  - STYLE: Different styling for user vs assistant
  - DISPLAY: Markdown rendering for assistant messages
  - SHOW: Timestamp in human-readable format

CREATE frontend/components/ChatInput.vue:
  - TEMPLATE: Textarea with send button
  - EMIT: 'send' event with message content
  - HANDLE: Enter key to send (Shift+Enter for newline)
  - CLEAR: Input after sending
  - VALIDATE: Non-empty messages

CREATE frontend/components/ChatHistory.vue:
  - PROPS: messages array
  - ITERATE: Over messages with ChatMessage component
  - SCROLL: Auto-scroll to bottom on new messages
  - HANDLE: Empty state when no messages

Task 11: Implement Main Chat Page
CREATE frontend/pages/index.vue:
  - USE: useChatSocket composable
  - COMPOSE: ChatHistory and ChatInput components
  - HANDLE: Send message from ChatInput
  - DISPLAY: Connection status
  - SHOW: Loading indicator while waiting for response
  - HANDLE: Errors from WebSocket

Task 12: Create Unit Tests for Backend
CREATE tests/test_config.py:
  - TEST: Config loads environment variables correctly
  - TEST: Config raises error for missing required vars
  - TEST: Config provides correct default values

CREATE tests/test_mcp_config.py:
  - TEST: MCP config creates correct server configuration
  - TEST: MCP config includes required environment variables
  - TEST: MCP config uses correct paths

CREATE tests/test_agent.py:
  - TEST: ChatAgent initializes with correct options
  - TEST: ChatAgent handles query successfully (mock ClaudeSDKClient)
  - TEST: ChatAgent handles errors gracefully
  - TEST: ChatAgent formats responses correctly

CREATE tests/test_api.py:
  - TEST: Health check endpoint returns 200
  - TEST: WebSocket connection accepts successfully
  - TEST: WebSocket streams messages correctly
  - TEST: WebSocket handles disconnection

Task 13: Create Environment Configuration Files
CREATE .env.example:
  - LIST all required environment variables
  - PROVIDE example values
  - ADD comments explaining each variable

UPDATE .gitignore:
  - IGNORE .env file
  - IGNORE __pycache__
  - IGNORE .pytest_cache
  - IGNORE frontend/node_modules
  - IGNORE frontend/.nuxt

Task 14: Update Documentation
UPDATE README.md:
  - ADD project overview
  - ADD architecture diagram
  - ADD setup instructions (both backend and frontend)
  - ADD environment variable configuration
  - ADD usage examples
  - ADD troubleshooting section

CREATE backend/README.md:
  - DOCUMENT backend architecture
  - DOCUMENT API endpoints
  - DOCUMENT how to run tests
  - DOCUMENT how to run development server

CREATE frontend/README.md:
  - DOCUMENT frontend architecture
  - DOCUMENT component structure
  - DOCUMENT how to run development server
  - DOCUMENT how to build for production
```

### Task 5 Pseudocode: Claude Agent Logic

```python
# backend/agent.py
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage
)
from .config import Config
from .mcp_config import get_netbox_mcp_config
from .models import StreamChunk
from typing import AsyncIterator
import logging

logger = logging.getLogger(__name__)

class ChatAgent:
    """
    Manages Claude Agent sessions for Netbox queries.

    Uses ClaudeSDKClient for continuous conversation support.
    Integrates with Netbox MCP server for data access.
    """

    def __init__(self, config: Config):
        """Initialize agent with configuration."""
        # PATTERN: Configure ClaudeAgentOptions with MCP servers
        self.options = ClaudeAgentOptions(
            mcp_servers=get_netbox_mcp_config(config),
            allowed_tools=[
                "mcp__netbox__netbox_get_objects",
                "mcp__netbox__netbox_get_object_by_id",
                "mcp__netbox__netbox_get_changelogs",
            ],
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": (
                    "You are a Netbox infrastructure assistant. "
                    "Help users query and understand their Netbox data. "
                    "Use the Netbox MCP tools to retrieve information."
                )
            },
            permission_mode="acceptEdits",
            include_partial_messages=False,  # Only complete messages
        )
        self.client: ClaudeSDKClient | None = None
        self.session_active = False

    async def start_session(self):
        """
        Start a new Claude Agent session.

        CRITICAL: Use async context manager pattern.
        """
        # PATTERN: ClaudeSDKClient as async context manager
        self.client = ClaudeSDKClient(options=self.options)
        await self.client.__aenter__()  # Manual context entry
        self.session_active = True
        logger.info("Claude Agent session started")

    async def query(self, message: str) -> AsyncIterator[StreamChunk]:
        """
        Send query to Claude and stream responses.

        Args:
            message: User's natural language query

        Yields:
            StreamChunk objects with response data

        Raises:
            RuntimeError: If session not active
        """
        if not self.session_active or not self.client:
            raise RuntimeError("Session not active. Call start_session() first.")

        try:
            # Send query to Claude
            await self.client.query(message)

            # PATTERN: Type-safe message processing
            # CRITICAL: Don't use break, let iteration complete
            async for msg in self.client.receive_response():
                if isinstance(msg, AssistantMessage):
                    # Process assistant response
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            # Stream text content
                            yield StreamChunk(
                                type="text",
                                content=block.text,
                                completed=False
                            )
                        elif isinstance(block, ToolUseBlock):
                            # Tool being used
                            yield StreamChunk(
                                type="tool_use",
                                content=f"Using tool: {block.name}",
                                completed=False
                            )
                        elif isinstance(block, ToolResultBlock):
                            # Tool result available
                            if block.content:
                                result_text = (
                                    block.content if isinstance(block.content, str)
                                    else str(block.content)
                                )
                                yield StreamChunk(
                                    type="tool_result",
                                    content=result_text,
                                    completed=False
                                )

                elif isinstance(msg, ResultMessage):
                    # Final result - conversation turn complete
                    yield StreamChunk(
                        type="text",
                        content="",
                        completed=True
                    )
                    logger.info(
                        f"Query completed in {msg.duration_ms}ms, "
                        f"{msg.num_turns} turns"
                    )

        except Exception as e:
            # PATTERN: Graceful error handling
            logger.error(f"Query error: {e}", exc_info=True)
            yield StreamChunk(
                type="error",
                content=f"Error: {str(e)}",
                completed=True
            )

    async def close_session(self):
        """Close the Claude Agent session and cleanup resources."""
        if self.client and self.session_active:
            await self.client.__aexit__(None, None, None)  # Manual context exit
            self.session_active = False
            logger.info("Claude Agent session closed")
```

### Task 6 Pseudocode: FastAPI Server with WebSocket

```python
# backend/api.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .agent import ChatAgent
from .config import Config
from .models import StreamChunk, ErrorResponse
import logging
import json

logger = logging.getLogger(__name__)

# PATTERN: Initialize FastAPI app
app = FastAPI(
    title="Netbox Chatbox API",
    description="Backend API for Netbox chatbox with Claude Agent SDK",
    version="1.0.0"
)

# PATTERN: CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Nuxt dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load configuration
config = Config()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "netbox-chatbox-api"}

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for chat streaming.

    Maintains a Claude Agent session for the duration of the connection.
    Streams responses back to client in real-time.
    """
    # PATTERN: Accept WebSocket connection
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    # Create and start agent session for this WebSocket
    agent = ChatAgent(config)

    try:
        # CRITICAL: Start session before processing queries
        await agent.start_session()
        logger.info("Agent session started for WebSocket")

        # Send connection success message
        await websocket.send_json({
            "type": "connected",
            "content": "Connected to Netbox chatbox",
            "completed": False
        })

        # Main message loop
        while True:
            # PATTERN: Receive message from client
            data = await websocket.receive_text()
            logger.debug(f"Received message: {data[:100]}...")

            try:
                message_data = json.loads(data)
                user_message = message_data.get("message", "")

                if not user_message:
                    await websocket.send_json({
                        "type": "error",
                        "content": "Empty message received",
                        "completed": True
                    })
                    continue

                # PATTERN: Stream responses from agent
                async for chunk in agent.query(user_message):
                    # Send each chunk to client
                    await websocket.send_json(chunk.dict())

            except json.JSONDecodeError:
                logger.error("Invalid JSON received from client")
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid JSON format",
                    "completed": True
                })
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                await websocket.send_json({
                    "type": "error",
                    "content": f"Error: {str(e)}",
                    "completed": True
                })

    except WebSocketDisconnect:
        # PATTERN: Handle disconnection gracefully
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        # CRITICAL: Always close agent session
        await agent.close_session()
        logger.info("Agent session closed for WebSocket")

# PATTERN: Application startup/shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    logger.info("Starting Netbox Chatbox API")
    # Validate configuration
    try:
        config.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    logger.info("Shutting down Netbox Chatbox API")
```

### Task 9 Pseudocode: WebSocket Composable

```typescript
// frontend/composables/useChatSocket.ts
import { ref, onMounted, onUnmounted } from 'vue'

interface StreamChunk {
  type: 'text' | 'tool_use' | 'tool_result' | 'thinking' | 'error' | 'connected'
  content: string
  completed: boolean
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export const useChatSocket = () => {
  // PATTERN: Reactive state
  const socket = ref<WebSocket | null>(null)
  const connected = ref(false)
  const messages = ref<ChatMessage[]>([])
  const currentResponse = ref('')
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // PATTERN: WebSocket connection
  const connect = () => {
    try {
      // Connect to backend WebSocket
      socket.value = new WebSocket('ws://localhost:8000/ws/chat')

      // Handle connection open
      socket.value.onopen = () => {
        console.log('WebSocket connected')
        connected.value = true
        error.value = null
      }

      // PATTERN: Handle incoming messages
      socket.value.onmessage = (event) => {
        try {
          const chunk: StreamChunk = JSON.parse(event.data)

          if (chunk.type === 'connected') {
            // Initial connection message
            return
          }

          if (chunk.type === 'error') {
            // Error message
            error.value = chunk.content
            isLoading.value = false
            return
          }

          if (chunk.type === 'text') {
            // Accumulate text content
            currentResponse.value += chunk.content

            // If response completed, add to messages
            if (chunk.completed) {
              messages.value.push({
                role: 'assistant',
                content: currentResponse.value,
                timestamp: new Date()
              })
              currentResponse.value = ''
              isLoading.value = false
            }
          } else if (chunk.type === 'tool_use') {
            // Tool usage indicator
            currentResponse.value += `\n[${chunk.content}]\n`
          }
        } catch (err) {
          console.error('Error parsing message:', err)
          error.value = 'Failed to parse server response'
        }
      }

      // PATTERN: Handle errors
      socket.value.onerror = (event) => {
        console.error('WebSocket error:', event)
        error.value = 'Connection error'
        connected.value = false
      }

      // PATTERN: Handle connection close
      socket.value.onclose = () => {
        console.log('WebSocket disconnected')
        connected.value = false

        // Attempt reconnection after delay
        setTimeout(() => {
          if (!connected.value) {
            console.log('Attempting to reconnect...')
            connect()
          }
        }, 3000)
      }
    } catch (err) {
      console.error('Connection error:', err)
      error.value = 'Failed to establish connection'
    }
  }

  // PATTERN: Send message
  const sendMessage = (message: string) => {
    if (!socket.value || !connected.value) {
      error.value = 'Not connected to server'
      return
    }

    if (!message.trim()) {
      return
    }

    // Add user message to history
    messages.value.push({
      role: 'user',
      content: message,
      timestamp: new Date()
    })

    // Send to server
    socket.value.send(JSON.stringify({ message }))
    isLoading.value = true
    error.value = null
  }

  // PATTERN: Disconnect
  const disconnect = () => {
    if (socket.value) {
      socket.value.close()
      socket.value = null
    }
    connected.value = false
  }

  // PATTERN: Lifecycle hooks
  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    connected,
    messages,
    currentResponse,
    isLoading,
    error,
    sendMessage,
    disconnect,
    reconnect: connect
  }
}
```

### Integration Points

```yaml
ENVIRONMENT VARIABLES:
  backend/.env:
    - ANTHROPIC_API_KEY: API key for Claude (required)
    - NETBOX_URL: URL to Netbox instance (e.g., http://localhost:8000)
    - NETBOX_TOKEN: Read-only API token for Netbox
    - LOG_LEVEL: Logging level (default: INFO)
    - CORS_ORIGINS: Allowed CORS origins (default: http://localhost:3000)

MCP SERVER:
  location: /home/ola/dev/rnd/mcp/testmcp/netbox-mcp-server/
  command: uv run server.py
  required_env: NETBOX_URL, NETBOX_TOKEN
  tools:
    - netbox_get_objects: Get objects with filters
    - netbox_get_object_by_id: Get specific object by ID
    - netbox_get_changelogs: Get change history

NETWORK:
  backend_port: 8000
  frontend_port: 3000
  websocket_endpoint: ws://localhost:8000/ws/chat

DEPENDENCIES:
  backend:
    - python: ">=3.10"
    - claude-agent-sdk: "latest"
    - fastapi: "latest"
    - uvicorn[standard]: "latest"
    - python-dotenv: "latest"
    - pydantic: ">=2.0"

  frontend:
    - node: ">=18"
    - nuxt: "^4.0.0"
    - typescript: "latest"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Backend - Run these FIRST, fix any errors before proceeding
cd backend
source ../venv_linux/bin/activate  # Use existing venv

# Install dependencies
uv sync

# Format code
black backend/ tests/

# Lint
ruff check backend/ tests/ --fix

# Type checking
mypy backend/ tests/

# Expected: No errors. If errors, READ the error message and fix.
```

### Level 2: Unit Tests
```bash
# Backend unit tests - Use venv_linux
source venv_linux/bin/activate
uv run pytest tests/ -v --cov=backend --cov-report=term-missing

# Expected tests:
# - test_config.py::test_config_loads_env_vars
# - test_config.py::test_config_validates_required_vars
# - test_mcp_config.py::test_mcp_config_structure
# - test_agent.py::test_agent_initialization
# - test_agent.py::test_agent_query_success
# - test_agent.py::test_agent_error_handling
# - test_api.py::test_health_endpoint
# - test_api.py::test_websocket_connection

# Expected: All tests pass. If failing, read error, fix, re-run.
# NEVER mock to pass - fix the actual code.
```

### Level 3: Integration Test
```bash
# Terminal 1: Start backend server
cd backend
source ../venv_linux/bin/activate
uvicorn backend.api:app --reload --port 8000

# Terminal 2: Start frontend dev server
cd frontend
npm run dev

# Terminal 3: Test WebSocket connection
wscat -c ws://localhost:8000/ws/chat
# Send: {"message": "List all devices in Netbox"}
# Expected: Streaming response with device data

# Browser: Open http://localhost:3000
# Test: Send message "What sites do I have in Netbox?"
# Expected: Chat interface shows response with site data

# If error: Check backend logs for stack trace
# Common issues:
# - Missing environment variables
# - Netbox MCP server not accessible
# - ANTHROPIC_API_KEY not set
```

### Level 4: End-to-End Test
```bash
# Full application test with all components

# 1. Verify Netbox MCP server is accessible
cd /home/ola/dev/rnd/mcp/testmcp/netbox-mcp-server
NETBOX_URL=http://localhost:8000 NETBOX_TOKEN=your_token uv run server.py
# Expected: Server starts without errors

# 2. Start backend with all environment variables
cd backend
export ANTHROPIC_API_KEY=your_key
export NETBOX_URL=http://localhost:8000
export NETBOX_TOKEN=your_token
source ../venv_linux/bin/activate
uvicorn backend.api:app --reload

# 3. Start frontend
cd frontend
npm run dev

# 4. Test complete workflow:
#    a. Open browser to http://localhost:3000
#    b. Send: "List all sites in Netbox"
#    c. Verify: Response streams in real-time
#    d. Send: "Tell me about devices in site X" (follow-up)
#    e. Verify: Claude remembers previous context
#    f. Check: No errors in browser console or backend logs

# Expected: Full conversation works with streaming and context
```

## Final Validation Checklist
- [ ] All backend tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `ruff check backend/`
- [ ] No type errors: `mypy backend/`
- [ ] Backend starts without errors: `uvicorn backend.api:app`
- [ ] Frontend builds without errors: `npm run build`
- [ ] WebSocket connection establishes successfully
- [ ] Messages stream in real-time from backend to frontend
- [ ] Follow-up questions maintain conversation context
- [ ] Netbox MCP tools are accessible and return data
- [ ] Error cases handled gracefully (network errors, MCP failures)
- [ ] Environment variables properly configured
- [ ] Documentation updated with setup instructions
- [ ] TASK.md updated with completion status

---

## Anti-Patterns to Avoid
- ❌ Don't use `query()` function - use `ClaudeSDKClient` for continuous conversations
- ❌ Don't forget async context manager for ClaudeSDKClient
- ❌ Don't use `break` in async message iteration - causes asyncio issues
- ❌ Don't skip environment variable validation
- ❌ Don't expose ANTHROPIC_API_KEY in frontend code
- ❌ Don't forget to enable experimental WebSocket in Nuxt config
- ❌ Don't hardcode Netbox MCP server paths - use configuration
- ❌ Don't ignore WebSocket disconnection events
- ❌ Don't skip CORS configuration in FastAPI
- ❌ Don't commit .env file to git
- ❌ Don't skip type checking on message types from Claude SDK
- ❌ Don't forget to close agent sessions on WebSocket disconnect

## Security Considerations
1. **API Key Management**: Never commit ANTHROPIC_API_KEY to version control
2. **Netbox Token**: Use read-only token with minimal required permissions
3. **CORS**: Restrict to specific frontend origins in production
4. **Input Validation**: Validate all user inputs before processing
5. **Error Messages**: Don't expose sensitive information in error responses
6. **Rate Limiting**: Consider adding rate limiting for production
7. **WebSocket Security**: Implement authentication for WebSocket connections in production

## Performance Considerations
1. **Session Management**: One Claude session per WebSocket connection
2. **Streaming**: Use streaming for real-time user feedback
3. **Connection Pooling**: Consider connection pooling for Netbox API calls
4. **Caching**: Cache frequently requested Netbox data where appropriate
5. **Resource Cleanup**: Always close sessions on disconnect

## Future Enhancements
1. **Authentication**: Add user authentication for multi-user support
2. **Session Persistence**: Save conversation history to database
3. **Retry Logic**: Implement exponential backoff for transient failures
4. **Monitoring**: Add metrics and logging for production monitoring
5. **Testing**: Add E2E tests with Playwright or Cypress
6. **Deployment**: Add Docker configuration for easy deployment
7. **Documentation**: Add API documentation with Swagger/OpenAPI
