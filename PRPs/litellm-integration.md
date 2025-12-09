# Project Requirements Plan: LiteLLM Integration

## Status: COMPLETED ✅
**Completion Date**: December 8, 2025
**Implementation Time**: ~2 hours

## Executive Summary
Implement LiteLLM proxy support in the Netbox Chatbox application to enable multi-model LLM support, allowing users to choose between Anthropic Claude models and locally-hosted Ollama models through a frontend modal interface.

## Project Context

### Current State
- **Backend**: FastAPI server with Claude Agent SDK integration
  - SDK uses **automatic model routing** (Haiku/Sonnet/Opus based on task complexity)
  - No explicit `model` parameter currently specified in `ClaudeAgentOptions`
  - SDK defaults to intelligent model selection when `model` is None
- **Frontend**: Nuxt 3 with Vue 3 Composition API and TypeScript
- **Communication**: WebSocket-based real-time streaming
- **Configuration**: Environment variables for API keys and endpoints
- **State Management**: Composables pattern (no Vuex/Pinia stores)

### Target State
- Support for multiple LLM providers through LiteLLM proxy
- User-selectable model via frontend modal
- Initial support for:
  - **Anthropic Claude models** (with explicit model control via SDK)
  - **Ollama qwen2.5:14b-instruct-8k** model (via LiteLLM proxy)
- Model control options:
  - **Explicit model selection**: User chooses specific Claude model (Sonnet 4.5, Opus 4, Haiku 4.5)
  - **Automatic routing**: Preserve SDK's intelligent model selection (Anthropic only)
- Seamless model switching without session loss

## Technical Architecture

### Model Selection Strategy

**IMPORTANT**: Claude Agent SDK has two model selection modes:

1. **Automatic Routing** (Current Default):
   - SDK parameter: `model=None`
   - Behavior: SDK automatically selects Haiku/Sonnet/Opus based on task complexity
   - Pros: Cost-optimized, intelligent selection
   - Cons: Less predictable model usage

2. **Explicit Model Control** (Required for User Selection):
   - SDK parameter: `model="claude-sonnet-4-5-20250929"`
   - Behavior: Fixed model for entire session
   - Pros: Predictable model usage, user control
   - Cons: Loses automatic optimization

**Implementation Choice**: Support BOTH modes with dual-path architecture.

### LiteLLM Proxy Layer (Dual-Path Architecture)
```
Frontend (Port 3000)
    ↓ WebSocket
Backend API (Port 8001)
    ├─ Path A: Claude Agent SDK (Direct)
    │   ├─ Automatic mode: model=None (SDK chooses)
    │   └─ Explicit mode: model="claude-sonnet-4-5-20250929"
    │   ↓ Direct HTTPS
    │   └─ Anthropic API (api.anthropic.com)
    │
    └─ Path B: LiteLLM Proxy
        ↓ HTTP
        LiteLLM Proxy (Port 4000, /v1 endpoint)
        ↓ Provider APIs
        └── Ollama API (Port 11434)
```

### Routing Decision Table (MANDATORY)

**CRITICAL RULE**: Anthropic models ALWAYS use SDK Direct (Path A), non-Anthropic models use LiteLLM Proxy (Path B).

| Model ID          | Provider  | Routing Path   | SDK Model Param                | Justification              |
|-------------------|-----------|----------------|--------------------------------|----------------------------|
| `auto`            | Anthropic | SDK Direct (A) | `None`                         | Preserve SDK automatic     |
| `claude-sonnet-4-5` | Anthropic | SDK Direct (A) | `claude-sonnet-4-5-20250929`  | Native SDK features        |
| `claude-opus-4`   | Anthropic | SDK Direct (A) | `claude-opus-4-20250514`       | MCP support required       |
| `claude-haiku-4-5`| Anthropic | SDK Direct (A) | `claude-haiku-4-5-20250929`    | Full SDK stack             |
| `ollama-qwen2.5`  | Ollama    | LiteLLM (B)    | N/A (uses LiteLLM client)      | Non-Anthropic provider     |

**Feature Flag Override** (NOT RECOMMENDED):
- `ALLOW_ANTHROPIC_VIA_LITELLM=false` (default) - Enforce Path A for Anthropic
- `ALLOW_ANTHROPIC_VIA_LITELLM=true` - Allow routing Anthropic via LiteLLM
  - ⚠️ **WARNING**: Loses SDK features (MCP, automatic routing, thinking blocks, prompt caching)

**LiteLLM Endpoint Configuration**:
- Unified endpoint: `http://localhost:4000/v1` (Anthropic Messages API format)
- NOT pass-through: `http://localhost:4000/anthropic` (incompatible)
- Required LiteLLM version: v1.55.0+ (Anthropic format support)

### Session Management and Model Switching

**CRITICAL RULE**: Model switching ALWAYS resets conversation context.

#### Session Lifecycle

```python
# backend/session_manager.py
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

@dataclass
class SessionState:
    """State for a single conversation session."""
    connection_id: str
    model_id: str
    messages: List[ChatMessage]
    created_at: datetime
    agent: BaseAgent

class SessionManager:
    """
    Manage conversation sessions per WebSocket connection.

    Rules:
    1. One active session per WebSocket connection
    2. Session bound to specific model
    3. Model switch = close old session, start new session
    4. Context does NOT transfer between sessions
    5. Frontend preserves message history (display only)
    """

    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}

    async def create_session(
        self,
        connection_id: str,
        model_id: str
    ) -> SessionState:
        """Create new session with model binding."""
        # Validate model
        model_config = ModelRegistry.validate_model_id(model_id)

        # Create agent
        agent = create_agent(model_id, config)
        await agent.start_session()

        # Create session state
        session = SessionState(
            connection_id=connection_id,
            model_id=model_id,
            messages=[],
            created_at=datetime.now(),
            agent=agent
        )

        self.sessions[connection_id] = session
        logger.info(f"Session created: {connection_id} with model {model_id}")
        return session

    async def switch_model(
        self,
        connection_id: str,
        new_model_id: str
    ) -> dict:
        """
        Switch to different model (resets context).

        Process:
        1. Close current agent session
        2. Archive old session messages (for frontend)
        3. Create new session with new model
        4. Return archived messages + reset confirmation

        Returns:
            dict with old_messages and new_session
        """
        old_session = self.sessions.get(connection_id)

        # Archive old session
        archived_messages = []
        if old_session:
            archived_messages = old_session.messages.copy()
            await old_session.agent.close_session()
            logger.info(
                f"Closed session {connection_id} "
                f"(model: {old_session.model_id}, "
                f"messages: {len(archived_messages)})"
            )

        # Create new session
        new_session = await self.create_session(connection_id, new_model_id)

        return {
            "old_messages": archived_messages,  # For frontend display
            "new_session": new_session,
            "context_reset": True  # Always true
        }

    async def close_session(self, connection_id: str):
        """Close session and cleanup agent."""
        session = self.sessions.get(connection_id)
        if session:
            await session.agent.close_session()
            del self.sessions[connection_id]
            logger.info(f"Session closed: {connection_id}")
```

#### Frontend Warning Modal

**REQUIRED**: Show warning before model switch

```vue
<!-- frontend/components/ModelSwitchWarning.vue -->
<template>
  <Modal :open="isOpen" @close="handleCancel">
    <div class="warning-content">
      <div class="warning-icon">⚠️</div>
      <h2>Switch to {{ newModelName }}?</h2>
      <p class="warning-message">
        Switching models will start a new conversation.
        Your current conversation will be saved in history.
      </p>
      <div class="current-info">
        <p><strong>Current:</strong> {{ currentModelName }}</p>
        <p><strong>New:</strong> {{ newModelName }}</p>
        <p><strong>Messages:</strong> {{ messageCount }} (will be archived)</p>
      </p>
      <div class="actions">
        <button @click="handleCancel" class="btn-secondary">
          Cancel
        </button>
        <button @click="handleConfirm" class="btn-primary">
          Start New Conversation
        </button>
      </div>
    </div>
  </Modal>
</template>
```

#### WebSocket Protocol for Model Switching

```typescript
// Message from frontend to backend
{
  "type": "model_change",
  "model": "claude-opus-4"  // New model ID
}

// Response from backend to frontend
{
  "type": "model_changed",
  "old_model": "auto",
  "new_model": "claude-opus-4",
  "archived_message_count": 15,
  "context_reset": true
}
```

### Integration Points

#### Backend Changes
1. **Configuration Extension** (`backend/config.py`)
   - Add LiteLLM proxy configuration
   - Support model selection parameters
   - Maintain backward compatibility

2. **Agent Modification** (`backend/agent.py`)
   - Integrate LiteLLM client alongside Claude SDK
   - Model routing logic based on selection
   - Session management per model type

3. **API Enhancement** (`backend/api.py`)
   - New endpoint for available models list
   - Model selection in WebSocket protocol
   - Per-connection model state

#### Frontend Changes
1. **Modal Component** (`frontend/components/ModelSelector.vue`)
   - Clean modal UI with Tailwind CSS
   - Model cards with descriptions
   - Current selection indicator

2. **State Management** (`frontend/composables/useModelSelection.ts`)
   - Selected model persistence (localStorage)
   - Model metadata management
   - WebSocket protocol updates

3. **UI Integration**
   - Settings button in chat interface
   - Modal trigger and management
   - Visual indicator of active model

## Implementation Blueprint

### Phase 1: Backend LiteLLM Integration
**Priority**: High | **Complexity**: Medium | **Duration**: 2 days

#### Task 1.1: Model Registry with Server-Side Validation
```python
# backend/litellm_config.py
from typing import Optional, Dict, Any, Callable
from pydantic import BaseModel
from enum import Enum

class RoutingPath(str, Enum):
    """Routing path for model requests."""
    SDK_DIRECT = "sdk_direct"      # Path A: Claude Agent SDK
    LITELLM_PROXY = "litellm_proxy"  # Path B: LiteLLM Proxy

class LiteLLMConfig(BaseModel):
    """LiteLLM proxy configuration."""
    enabled: bool = False
    proxy_url: str = "http://localhost:4000/v1"  # Unified endpoint
    api_key: Optional[str] = None
    timeout: int = 120
    max_retries: int = 3
    min_version: str = "1.55.0"  # Minimum LiteLLM version

class ModelConfig(BaseModel):
    """Individual model configuration with routing information."""
    id: str
    name: str
    provider: str  # "anthropic" | "ollama"
    description: str
    context_length: int
    routing_path: RoutingPath
    sdk_model_param: Optional[str] = None  # For SDK Direct path
    litellm_model_name: Optional[str] = None  # For LiteLLM path
    is_automatic: bool = False
    enabled: bool = True
    health_check: Optional[Callable[[], bool]] = None  # Runtime availability check

class ModelRegistry:
    """
    Centralized model registry with server-side validation.

    SECURITY: Prevents arbitrary model IDs from reaching LiteLLM proxy.
    VALIDATION: Ensures only approved models are accessible.
    """

    ALLOWED_MODELS: Dict[str, ModelConfig] = {
        "auto": ModelConfig(
            id="auto",
            name="Claude (Automatic Selection)",
            provider="anthropic",
            description="SDK intelligently selects Haiku/Sonnet/Opus based on task complexity",
            context_length=200000,
            routing_path=RoutingPath.SDK_DIRECT,
            sdk_model_param=None,  # None = automatic routing
            is_automatic=True,
            enabled=True
        ),
        "claude-sonnet-4-5": ModelConfig(
            id="claude-sonnet-4-5",
            name="Claude Sonnet 4.5",
            provider="anthropic",
            description="Balanced performance and speed",
            context_length=200000,
            routing_path=RoutingPath.SDK_DIRECT,
            sdk_model_param="claude-sonnet-4-5-20250929",
            enabled=True
        ),
        "claude-opus-4": ModelConfig(
            id="claude-opus-4",
            name="Claude Opus 4",
            provider="anthropic",
            description="Most capable, best for complex tasks",
            context_length=200000,
            routing_path=RoutingPath.SDK_DIRECT,
            sdk_model_param="claude-opus-4-20250514",
            enabled=True
        ),
        "claude-haiku-4-5": ModelConfig(
            id="claude-haiku-4-5",
            name="Claude Haiku 4.5",
            provider="anthropic",
            description="Fastest, cost-effective for simple tasks",
            context_length=200000,
            routing_path=RoutingPath.SDK_DIRECT,
            sdk_model_param="claude-haiku-4-5-20250929",
            enabled=True
        ),
        "ollama-qwen2.5": ModelConfig(
            id="ollama-qwen2.5",
            name="Qwen 2.5 14B Instruct",
            provider="ollama",
            description="Local Ollama model (via LiteLLM)",
            context_length=8192,
            routing_path=RoutingPath.LITELLM_PROXY,
            litellm_model_name="ollama/qwen2.5:14b-instruct-8k",
            enabled=True,
            health_check=lambda: ServiceHealth().check_ollama_available()
        )
    }

    @classmethod
    def validate_model_id(cls, model_id: str) -> ModelConfig:
        """
        Validate model ID against allowlist.

        Args:
            model_id: User-provided model identifier

        Returns:
            ModelConfig: Validated model configuration

        Raises:
            ValueError: If model ID is not in allowlist or is disabled
        """
        if model_id not in cls.ALLOWED_MODELS:
            allowed_ids = list(cls.ALLOWED_MODELS.keys())
            raise ValueError(
                f"Invalid model ID: '{model_id}'. "
                f"Allowed models: {allowed_ids}"
            )

        config = cls.ALLOWED_MODELS[model_id]

        # Check if model is enabled
        if not config.enabled:
            raise ValueError(f"Model '{model_id}' is currently disabled")

        # Runtime health check for models with dependencies
        if config.health_check and not config.health_check():
            raise ValueError(
                f"Model '{model_id}' is unavailable "
                f"(dependency check failed: {config.provider})"
            )

        return config

    @classmethod
    def list_available_models(cls) -> list[ModelConfig]:
        """Return list of currently available models."""
        available = []
        for model_id, config in cls.ALLOWED_MODELS.items():
            if not config.enabled:
                continue

            # Skip models that fail health checks
            if config.health_check:
                try:
                    if not config.health_check():
                        logger.info(f"Model {model_id} unavailable (health check failed)")
                        continue
                except Exception as e:
                    logger.warning(f"Health check error for {model_id}: {e}")
                    continue

            available.append(config)

        return available
```

#### Task 1.2: Agent Factory Pattern
```python
# backend/agent_factory.py
from abc import ABC, abstractmethod
from typing import AsyncIterator

class BaseAgent(ABC):
    """Abstract base for different agent implementations."""

    @abstractmethod
    async def start_session(self) -> None:
        pass

    @abstractmethod
    async def query(self, message: str) -> AsyncIterator[StreamChunk]:
        pass

    @abstractmethod
    async def close_session(self) -> None:
        pass

class ClaudeAgent(BaseAgent):
    """Claude SDK implementation with explicit model control."""

    def __init__(self, config: Config, model: Optional[str] = None):
        """
        Initialize Claude Agent with optional model specification.

        Args:
            config: Application configuration
            model: Optional explicit model (e.g., "claude-sonnet-4-5-20250929")
                   If None, SDK uses automatic routing (Haiku/Sonnet/Opus)
        """
        self.options = ClaudeAgentOptions(
            model=model,  # KEY: Explicit model or None for automatic
            fallback_model="claude-haiku-4-5-20250929",  # Backup if primary fails
            mcp_servers=get_netbox_mcp_config(config),
            allowed_tools=get_allowed_netbox_tools(),
            system_prompt={"type": "preset", "preset": "claude_code", "append": "..."},
            permission_mode="acceptEdits",
        )

class LiteLLMAgent(BaseAgent):
    """LiteLLM proxy implementation for non-Anthropic models."""
    # New implementation for Ollama and other providers

def create_agent(model_id: str, config: Config) -> BaseAgent:
    """
    Factory to create appropriate agent with validation and graceful fallback.

    Model ID patterns:
        - "auto" → ClaudeAgent(model=None) - SDK automatic routing
        - "claude-sonnet-4-5" → ClaudeAgent(model="claude-sonnet-4-5-20250929")
        - "claude-opus-4" → ClaudeAgent(model="claude-opus-4-20250514")
        - "claude-haiku-4-5" → ClaudeAgent(model="claude-haiku-4-5-20250929")
        - "ollama-qwen2.5" → LiteLLMAgent("ollama/qwen2.5:14b-instruct-8k")

    Fallback strategy:
        - If model validation fails → fallback to ClaudeAgent(model=None)
        - If LiteLLM path unavailable → fallback to ClaudeAgent(model=None)
        - Always ensure Claude SDK path works (Anthropic API)
    """
    try:
        # Validate model ID against allowlist
        model_config = ModelRegistry.validate_model_id(model_id)

        # Route based on path
        if model_config.routing_path == RoutingPath.SDK_DIRECT:
            return ClaudeAgent(config, model=model_config.sdk_model_param)

        elif model_config.routing_path == RoutingPath.LITELLM_PROXY:
            # Health check before creating LiteLLM agent
            if not ServiceHealth().check_litellm_available():
                logger.warning(
                    f"LiteLLM unavailable for model {model_id}, "
                    f"falling back to automatic Claude"
                )
                return ClaudeAgent(config, model=None)  # Graceful fallback

            return LiteLLMAgent(config, model_config.litellm_model_name)

    except ValueError as e:
        logger.error(f"Model validation failed for '{model_id}': {e}")
        logger.info("Falling back to automatic Claude (SDK default)")
        return ClaudeAgent(config, model=None)  # Safe fallback

    except Exception as e:
        logger.error(f"Unexpected error creating agent for '{model_id}': {e}")
        logger.info("Falling back to automatic Claude (SDK default)")
        return ClaudeAgent(config, model=None)  # Safe fallback
```

#### Task 1.3: Health Checks and Graceful Degradation
```python
# backend/health.py
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ServiceHealth:
    """
    Health monitoring for external LLM services.

    Provides runtime availability checks for:
    - LiteLLM proxy server
    - Ollama server
    - Claude API (via SDK check)

    Used by ModelRegistry and agent factory for graceful degradation.
    """

    def __init__(self):
        self._cache: Dict[str, tuple[bool, float]] = {}
        self._cache_ttl = 30.0  # 30 seconds cache

    async def check_litellm_available(self) -> bool:
        """
        Check if LiteLLM proxy is reachable.

        Returns:
            bool: True if proxy responds to health check
        """
        if not config.litellm_enabled:
            return False

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{config.litellm_proxy_url}/health"
                )
                available = response.status_code == 200

                if available:
                    logger.info("LiteLLM proxy health check: OK")
                else:
                    logger.warning(
                        f"LiteLLM proxy health check failed: {response.status_code}"
                    )

                return available

        except httpx.TimeoutException:
            logger.warning("LiteLLM proxy health check timed out (5s)")
            return False
        except Exception as e:
            logger.warning(f"LiteLLM proxy health check failed: {e}")
            return False

    async def check_ollama_available(self) -> bool:
        """
        Check if Ollama server is reachable and has required model.

        Returns:
            bool: True if Ollama responds and model exists
        """
        if not config.ollama_base_url:
            return False

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Check server health
                response = await client.get(
                    f"{config.ollama_base_url}/api/tags"
                )

                if response.status_code != 200:
                    logger.warning(f"Ollama server unhealthy: {response.status_code}")
                    return False

                # Verify qwen2.5 model exists
                data = response.json()
                models = [m.get("name") for m in data.get("models", [])]
                required_model = "qwen2.5:14b-instruct-8k"

                if required_model not in models:
                    logger.warning(
                        f"Required Ollama model '{required_model}' not found. "
                        f"Available: {models}"
                    )
                    return False

                logger.info(f"Ollama health check: OK (model {required_model} available)")
                return True

        except httpx.TimeoutException:
            logger.warning("Ollama health check timed out (5s)")
            return False
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    async def check_anthropic_available(self) -> bool:
        """
        Check if Claude SDK can reach Anthropic API.

        Returns:
            bool: True if API key is set (SDK handles connectivity)
        """
        # Basic check: API key configured
        if not config.anthropic_api_key:
            logger.error("ANTHROPIC_API_KEY not configured")
            return False

        # SDK handles actual connectivity checks
        logger.info("Anthropic API key configured")
        return True


# Startup health checks
@app.on_event("startup")
async def startup_health_checks():
    """
    Run health checks on application startup.

    Logs status of all services. Does NOT fail startup if optional
    services (LiteLLM, Ollama) are unavailable - they will be disabled
    in the model registry.
    """
    health = ServiceHealth()

    logger.info("=" * 60)
    logger.info("STARTUP HEALTH CHECKS")
    logger.info("=" * 60)

    # Critical: Anthropic API (always required)
    anthropic_ok = await health.check_anthropic_available()
    if not anthropic_ok:
        logger.error("❌ Anthropic API: UNAVAILABLE (CRITICAL)")
        raise RuntimeError("ANTHROPIC_API_KEY required but not configured")
    logger.info("✅ Anthropic API: AVAILABLE (Claude SDK ready)")

    # Optional: LiteLLM proxy
    if config.litellm_enabled:
        litellm_ok = await health.check_litellm_available()
        if litellm_ok:
            logger.info("✅ LiteLLM Proxy: AVAILABLE")
        else:
            logger.warning("⚠️  LiteLLM Proxy: UNAVAILABLE (non-Anthropic models disabled)")
    else:
        logger.info("ℹ️  LiteLLM: DISABLED (config.litellm_enabled=false)")

    # Optional: Ollama
    if config.ollama_base_url:
        ollama_ok = await health.check_ollama_available()
        if ollama_ok:
            logger.info("✅ Ollama: AVAILABLE")
        else:
            logger.warning("⚠️  Ollama: UNAVAILABLE (ollama models disabled)")
    else:
        logger.info("ℹ️  Ollama: NOT CONFIGURED")

    logger.info("=" * 60)
    logger.info("STARTUP COMPLETE - Server ready")
    logger.info("=" * 60)
```

#### Task 1.4: API Endpoints
```python
# backend/api.py additions
@app.get("/models")
async def list_models() -> List[ModelConfig]:
    """Return available models based on configuration."""
    models = []

    # IMPORTANT: Include "Automatic" mode first (recommended default)
    models.append(ModelConfig(
        id="auto",
        name="Claude (Automatic Selection)",
        provider="anthropic",
        description="SDK intelligently selects Haiku/Sonnet/Opus based on task complexity",
        context_length=200000,
        sdk_model_param=None,  # model=None for automatic routing
        is_automatic=True
    ))

    # Explicit Claude models (fixed selection)
    models.append(ModelConfig(
        id="claude-sonnet-4-5",
        name="Claude Sonnet 4.5",
        provider="anthropic",
        description="Balanced performance and speed",
        context_length=200000,
        sdk_model_param="claude-sonnet-4-5-20250929"
    ))

    models.append(ModelConfig(
        id="claude-opus-4",
        name="Claude Opus 4",
        provider="anthropic",
        description="Most capable, best for complex tasks",
        context_length=200000,
        sdk_model_param="claude-opus-4-20250514"
    ))

    models.append(ModelConfig(
        id="claude-haiku-4-5",
        name="Claude Haiku 4.5",
        provider="anthropic",
        description="Fastest, cost-effective for simple tasks",
        context_length=200000,
        sdk_model_param="claude-haiku-4-5-20250929"
    ))

    # Include Ollama if configured
    if config.litellm_enabled and config.ollama_available:
        models.append(ModelConfig(
            id="ollama-qwen2.5",
            name="Qwen 2.5 14B Instruct",
            provider="ollama",
            description="Local Ollama model (via LiteLLM)",
            context_length=8192,
            litellm_model_name="ollama/qwen2.5:14b-instruct-8k"
        ))

    return models
```

#### Task 1.5: Logging and Telemetry
```python
# backend/telemetry.py
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class ModelTelemetry:
    """
    Comprehensive logging for model usage, routing, and performance.

    Tracks:
    - Model selection and routing decisions
    - Request/response timing
    - Token usage and costs
    - Errors and fallbacks
    """

    def log_model_request(
        self,
        model_id: str,
        routing_path: str,
        connection_id: str
    ):
        """Log when model request starts."""
        logger.info(
            "model_request",
            extra={
                "event": "model_request",
                "model_id": model_id,
                "routing_path": routing_path,
                "connection_id": connection_id,
                "timestamp": datetime.now().isoformat()
            }
        )

    def log_model_response(
        self,
        model_id: str,
        duration_ms: int,
        tokens: Optional[int],
        cost_usd: Optional[float]
    ):
        """Log model response metrics."""
        logger.info(
            "model_response",
            extra={
                "event": "model_response",
                "model_id": model_id,
                "duration_ms": duration_ms,
                "tokens": tokens,
                "cost_usd": cost_usd,
                "timestamp": datetime.now().isoformat()
            }
        )

    def log_model_error(
        self,
        model_id: str,
        error: str,
        fallback_used: bool,
        fallback_model: Optional[str] = None
    ):
        """Log model errors and fallback decisions."""
        logger.error(
            "model_error",
            extra={
                "event": "model_error",
                "model_id": model_id,
                "error": str(error),
                "fallback_used": fallback_used,
                "fallback_model": fallback_model,
                "timestamp": datetime.now().isoformat()
            }
        )

    def log_routing_decision(
        self,
        model_id: str,
        requested_path: str,
        actual_path: str,
        reason: str
    ):
        """Log routing decisions (especially fallbacks)."""
        logger.info(
            "routing_decision",
            extra={
                "event": "routing_decision",
                "model_id": model_id,
                "requested_path": requested_path,
                "actual_path": actual_path,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }
        )


# Usage in agent factory
telemetry = ModelTelemetry()

def create_agent_with_telemetry(model_id: str, config: Config) -> BaseAgent:
    """Agent creation with comprehensive logging."""
    try:
        model_config = ModelRegistry.validate_model_id(model_id)

        telemetry.log_routing_decision(
            model_id=model_id,
            requested_path=model_config.routing_path.value,
            actual_path=model_config.routing_path.value,
            reason="model_validated"
        )

        if model_config.routing_path == RoutingPath.LITELLM_PROXY:
            if not ServiceHealth().check_litellm_available():
                telemetry.log_routing_decision(
                    model_id=model_id,
                    requested_path="litellm_proxy",
                    actual_path="sdk_direct",
                    reason="litellm_unavailable_fallback"
                )
                return ClaudeAgent(config, model=None)

        # ... agent creation

    except Exception as e:
        telemetry.log_model_error(
            model_id=model_id,
            error=str(e),
            fallback_used=True,
            fallback_model="auto"
        )
        return ClaudeAgent(config, model=None)
```

### Phase 2: Frontend Modal Implementation
**Priority**: High | **Complexity**: Low | **Duration**: 1 day

#### Task 2.1: Modal Component
```vue
<!-- frontend/components/ModelSelector.vue -->
<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="modal-overlay" @click.self="close">
        <div class="modal-container">
          <div class="modal-header">
            <h2>Select Language Model</h2>
            <button @click="close" class="close-button">✕</button>
          </div>

          <div class="modal-body">
            <div v-for="model in models" :key="model.id"
                 class="model-card"
                 :class="{ 'selected': model.id === selectedModel }"
                 @click="selectModel(model.id)">
              <div class="model-icon">
                {{ model.provider === 'anthropic' ? '🤖' : '🦙' }}
              </div>
              <div class="model-info">
                <h3>{{ model.name }}</h3>
                <p>{{ model.description }}</p>
                <span class="model-provider">{{ model.provider }}</span>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="cancel" class="btn-secondary">Cancel</button>
            <button @click="confirm" class="btn-primary">Apply</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
```

#### Task 2.2: Model Selection Composable
```typescript
// frontend/composables/useModelSelection.ts
export const useModelSelection = () => {
  const selectedModel = useState<string>('selected-model', () => {
    // Load from localStorage or default
    return localStorage.getItem('selected-model') || 'claude-3-5-sonnet'
  })

  const availableModels = useState<ModelConfig[]>('available-models', () => [])

  const fetchModels = async () => {
    try {
      const response = await $fetch('/api/models')
      availableModels.value = response
    } catch (error) {
      console.error('Failed to fetch models:', error)
    }
  }

  const selectModel = (modelId: string) => {
    selectedModel.value = modelId
    localStorage.setItem('selected-model', modelId)
  }

  return {
    selectedModel: readonly(selectedModel),
    availableModels: readonly(availableModels),
    fetchModels,
    selectModel
  }
}
```

### Phase 3: WebSocket Protocol Enhancement
**Priority**: High | **Complexity**: Medium | **Duration**: 1 day

#### Task 3.1: Protocol Updates
```typescript
// frontend/types/chat.ts additions
interface WebSocketMessage {
  message?: string
  type?: 'chat' | 'reset' | 'model_change'
  model?: string  // Model ID for selection
}

// backend/models.py additions
class WebSocketRequest(BaseModel):
    """Enhanced WebSocket request with model selection."""
    message: Optional[str] = None
    type: str = "chat"
    model: Optional[str] = None
```

#### Task 3.2: Session Management
```python
# backend/api.py WebSocket handler enhancement
async def websocket_chat(websocket: WebSocket) -> None:
    await websocket.accept()

    # Track model per connection
    current_model = "claude-3-5-sonnet"  # Default
    agent = None

    try:
        while True:
            data = await websocket.receive_text()
            request = WebSocketRequest.parse_raw(data)

            # Handle model change
            if request.type == "model_change" and request.model:
                if agent:
                    await agent.close_session()
                current_model = request.model
                agent = create_agent(current_model, config)
                await agent.start_session()
                # Send confirmation
                continue

            # Regular message handling
            # ...existing logic...
```

### Phase 4: LiteLLM Proxy Setup
**Priority**: Medium | **Complexity**: Low | **Duration**: 1 day

#### Task 4.1: Docker Compose Configuration
```yaml
# docker-compose.litellm.yml
version: '3.8'

services:
  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    ports:
      - "4000:4000"
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
      - DATABASE_URL=postgresql://litellm:password@postgres:5432/litellm
    volumes:
      - ./config/litellm_config.yaml:/app/config.yaml
    command: --config /app/config.yaml --detailed_debug
```

#### Task 4.2: LiteLLM Configuration File
```yaml
# config/litellm_config.yaml
model_list:
  - model_name: claude-3-5-sonnet
    litellm_params:
      model: claude-3-5-sonnet-20241022
      api_key: ${ANTHROPIC_API_KEY}

  - model_name: qwen2.5-14b
    litellm_params:
      model: ollama/qwen2.5:14b-instruct-8k
      api_base: http://host.docker.internal:11434
```

## Validation Gates

### Gate 1: Backend Integration (End of Phase 1)
- [ ] LiteLLM proxy connects successfully
- [ ] Both Claude and Ollama models accessible
- [ ] Agent factory creates correct agent type
- [ ] Models endpoint returns available models
- [ ] Unit tests pass for new components

### Gate 2: Frontend UI (End of Phase 2)
- [ ] Modal opens/closes correctly
- [ ] Model cards display properly
- [ ] Selection persists in localStorage
- [ ] UI indicates current model
- [ ] Responsive design works

### Gate 3: End-to-End Flow (End of Phase 3)
- [ ] Model switching works without errors
- [ ] Messages stream correctly for both models
- [ ] Context maintained within sessions
- [ ] Error handling for unavailable models
- [ ] Performance acceptable (< 2s model switch)

### Gate 4: Production Ready (End of Phase 4)
- [ ] Docker compose runs successfully
- [ ] Environment variables documented
- [ ] README updated with setup instructions
- [ ] Error messages user-friendly
- [ ] Logging comprehensive

## Risk Mitigation

### Risk 1: Loss of SDK Automatic Model Routing
**Risk**: Explicit model selection loses SDK's intelligent Haiku/Sonnet/Opus routing
**Impact**:
- Cost optimization lost (no automatic Haiku for simple queries)
- Performance suboptimal (forced Sonnet/Opus for simple tasks)
- Observed in console logs: SDK normally uses Haiku 4.5, Sonnet 4, and Sonnet 4.5 dynamically

**Mitigation**:
- **Offer "Automatic" mode as default** in model selector (model=None)
- Label it clearly: "Claude (Automatic Selection) - Recommended"
- Educate users: "SDK intelligently chooses the best model for each task"
- Track usage patterns to show cost/performance benefits
- Allow users to opt into explicit models if needed for predictability

**Example**: User console shows automatic routing:
```
Claude Haiku 4.5    - Simple queries, list operations
Claude Sonnet 4     - Medium complexity with caching
Claude Sonnet 4.5   - Complex analysis, extended thinking
```

### Risk 2: LiteLLM Compatibility with SDK
**Risk**: LiteLLM may not fully support Claude Agent SDK features
**Mitigation**:
- Maintain dual-path implementation
- Direct Claude SDK for ALL Anthropic models (Path A)
- LiteLLM only for non-Anthropic models (Path B)
- Never route Anthropic models through LiteLLM proxy

### Risk 3: Session State Loss on Model Switch
**Risk**: Model switching might lose conversation context
**Mitigation**:
- Clear user warning before switching: "Switching models will start a new conversation"
- Offer "New Session" vs "Cancel" options
- Preserve message history in frontend (read-only view of previous session)
- Future: Consider context transfer if SDK supports it

### Risk 4: Performance Degradation (LiteLLM Path)
**Risk**: Proxy layer adds latency for non-Anthropic models
**Mitigation**:
- Direct connection for Claude (bypass proxy entirely)
- Connection pooling for LiteLLM
- Response streaming optimization
- Document expected latency differences

### Risk 5: Unauthorized LiteLLM Proxy Access
**Risk**: LiteLLM proxy exposed without authentication allows unauthorized model access
**Impact**:
- Unauthorized users could consume Ollama resources
- Potential abuse of proxy for non-approved models
- Security breach if proxy accessible beyond localhost

**Mitigation**:
```yaml
# config/litellm_config.yaml
general_settings:
  master_key: "${LITELLM_MASTER_KEY}"  # REQUIRED - fail if not set
  allowed_ips: ["127.0.0.1", "::1"]    # Localhost only
  disable_spend_logs: false             # Enable audit logging

# Docker binding
services:
  litellm:
    ports:
      - "127.0.0.1:4000:4000"  # Bind to localhost ONLY (not 0.0.0.0)
```

**Backend Validation**:
```python
# backend/litellm_client.py
async def call_litellm(model_name: str, messages: list) -> Response:
    """Call LiteLLM with authentication."""
    if not config.litellm_master_key:
        raise ValueError("LITELLM_MASTER_KEY required but not set")

    headers = {
        "Authorization": f"Bearer {config.litellm_master_key}",
        "Content-Type": "application/json"
    }

    # Make request...
```

**Network Security**:
- Production: Use Docker network isolation (no host ports)
- Development: Localhost binding only (127.0.0.1:4000)
- Never expose 0.0.0.0:4000 without reverse proxy + auth

### Risk 6: Missing Logging/Observability
**Risk**: Cannot debug model routing issues or track costs without telemetry
**Mitigation**: Add comprehensive logging (see Phase 1, Task 1.5 below)

## Development Checklist

### Pre-Development
- [x] Analyze existing codebase structure
- [x] Research LiteLLM documentation
- [x] Identify integration points
- [ ] Set up local Ollama with qwen2.5 model
- [ ] Install and test LiteLLM proxy

### Backend Tasks
- [ ] Create feature branch `feature/litellm-integration`
- [ ] Implement LiteLLM configuration module
- [ ] Create agent factory pattern
- [ ] Add models listing endpoint
- [ ] Enhance WebSocket protocol
- [ ] Write unit tests for new modules
- [ ] Update backend documentation

### Frontend Tasks
- [ ] Design modal UI mockup
- [ ] Implement ModelSelector component
- [ ] Create useModelSelection composable
- [ ] Add settings button to chat interface
- [ ] Integrate modal with chat page
- [ ] Add model indicator to UI
- [ ] Test responsive design

### Integration Tasks
- [ ] Test Claude model through LiteLLM
- [ ] Test Ollama qwen2.5 model
- [ ] Verify model switching
- [ ] Check error handling
- [ ] Performance testing
- [ ] Update integration tests

### Documentation Tasks
- [ ] Update README with LiteLLM setup
- [ ] Document environment variables
- [ ] Create troubleshooting guide
- [ ] Add architecture diagram
- [ ] Write API documentation

## Success Metrics

### Functional Metrics
- All Claude models accessible (Automatic, Sonnet, Opus, Haiku)
- Ollama model accessible (when enabled)
- Model switching completes in < 2 seconds
- No session corruption on model change
- Error recovery works as expected
- **Automatic mode preserves SDK's dynamic routing**

### Performance Metrics
- **Automatic mode**: No performance regression (SDK default behavior)
- **Explicit Claude models**: Response latency unchanged (direct SDK)
- **Ollama models**: Response latency < 20% increase (via proxy)
- Streaming performance maintained
- Memory usage stable during model switches
- WebSocket connection remains stable

### User Experience Metrics
- Modal shows clear "Automatic (Recommended)" option
- Model selection persists correctly
- Clear indication of active model
- Smooth transition between models
- Users understand automatic vs explicit model trade-offs

### Cost Optimization Metrics (Automatic Mode)
- SDK uses appropriate model tier per task complexity
- Haiku 4.5 for simple queries (lowest cost)
- Sonnet 4/4.5 for complex analysis (balanced)
- Cost tracking shows optimization vs fixed model

## Timeline

| Phase | Duration | Dependencies | Milestone |
|-------|----------|--------------|-----------|
| Phase 1: Backend | 2 days | LiteLLM setup | Backend integration complete |
| Phase 2: Frontend | 1 day | None | Modal UI complete |
| Phase 3: Protocol | 1 day | Phase 1 & 2 | End-to-end flow working |
| Phase 4: Setup | 1 day | Phase 3 | Production ready |
| **Total** | **5 days** | | **Feature Complete** |

## Environment Variables

**CRITICAL**: Configuration depends on deployment scenario. Choose ONE scenario below and set variables accordingly.

### Scenario 1: Anthropic Direct + Ollama via LiteLLM (RECOMMENDED)

**Use Case**: Full model selection with Anthropic SDK features + local Ollama support

```bash
# === Anthropic Configuration (REQUIRED) ===
ANTHROPIC_API_KEY=sk-ant-xxx              # Your Anthropic API key
ANTHROPIC_BASE_URL=""                     # LEAVE EMPTY - uses default (api.anthropic.com)
# DO NOT SET ANTHROPIC_BASE_URL when using direct SDK path

# === LiteLLM Configuration (for Ollama) ===
LITELLM_ENABLED=true                      # Enable LiteLLM proxy
LITELLM_PROXY_URL=http://localhost:4000/v1  # Unified endpoint (/v1 NOT /anthropic)
LITELLM_MASTER_KEY=sk-litellm-xxx         # Security key for proxy
LITELLM_MIN_VERSION=1.55.0                # Minimum version check

# === Ollama Configuration ===
OLLAMA_BASE_URL=http://localhost:11434    # Ollama server
OLLAMA_MODEL=qwen2.5:14b-instruct-8k      # Model name to use

# === Model Selection ===
DEFAULT_MODEL=auto                        # Default to automatic routing
ENABLE_MODEL_SELECTION=true               # Show model selector in UI
ALLOW_ANTHROPIC_VIA_LITELLM=false         # MUST be false (enforce SDK direct)

# === Logging ===
LOG_LEVEL=INFO
LOG_MODEL_USAGE=true                      # Track model selection and costs
```

**Expected Routing**:
- `auto`, `claude-*` models → Claude Agent SDK → api.anthropic.com (Path A)
- `ollama-*` models → LiteLLM Proxy → Ollama (Path B)

---

### Scenario 2: Anthropic Direct Only (NO LiteLLM)

**Use Case**: Simplified deployment, Anthropic models only, no local models

```bash
# === Anthropic Configuration (REQUIRED) ===
ANTHROPIC_API_KEY=sk-ant-xxx              # Your Anthropic API key
ANTHROPIC_BASE_URL=""                     # LEAVE EMPTY

# === LiteLLM Configuration ===
LITELLM_ENABLED=false                     # Disable LiteLLM entirely
# No other LiteLLM/Ollama variables needed

# === Model Selection ===
DEFAULT_MODEL=auto                        # Automatic routing
ENABLE_MODEL_SELECTION=true               # Can still choose explicit Claude models
ALLOW_ANTHROPIC_VIA_LITELLM=false         # Not used (LiteLLM disabled)

# === Logging ===
LOG_LEVEL=INFO
```

**Expected Routing**:
- All models → Claude Agent SDK → api.anthropic.com (Path A only)
- Ollama models NOT available in `/models` endpoint

---

### Scenario 3: All via LiteLLM (⚠️ NOT RECOMMENDED)

**Use Case**: Unified proxy routing for all models (loses SDK features)

```bash
# === Anthropic Configuration ===
ANTHROPIC_API_KEY=""                      # NOT USED (key configured in LiteLLM)
ANTHROPIC_BASE_URL=http://localhost:4000/v1  # Route SDK to LiteLLM proxy
# WARNING: This bypasses Claude Agent SDK features

# === LiteLLM Configuration (REQUIRED) ===
LITELLM_ENABLED=true
LITELLM_PROXY_URL=http://localhost:4000/v1
LITELLM_MASTER_KEY=sk-litellm-xxx
# LiteLLM config must include Anthropic key

# === Model Selection ===
DEFAULT_MODEL=claude-sonnet-4-5           # Cannot use "auto" (SDK features lost)
ENABLE_MODEL_SELECTION=true
ALLOW_ANTHROPIC_VIA_LITELLM=true          # Override safety check

# === Logging ===
LOG_LEVEL=WARNING                         # Expect SDK feature warnings
```

**⚠️ WARNINGS**:
- Loses MCP support
- Loses automatic model routing (Haiku/Sonnet/Opus)
- Loses extended thinking / prompt caching optimizations
- Loses direct SDK error handling
- **Only use if absolutely necessary for unified billing/logging**

**Expected Routing**:
- All models → LiteLLM Proxy → Respective APIs (Path B for everything)

## Testing Strategy

### Unit Tests
- Config validation tests
- Agent factory tests
- Model listing tests
- WebSocket protocol tests

### Integration Tests
- **Automatic mode**: Verify SDK uses multiple models (Haiku/Sonnet/Opus)
- **Explicit modes**: Test each fixed model (Sonnet 4.5, Opus 4, Haiku 4.5)
- **Streaming**: Verify chunks arrive in order, no data loss
- **Timeouts**: Test request timeout handling (SDK: 60s, LiteLLM: 120s)
- **Latency**: Benchmark per model (Anthropic SDK <2s, Ollama <5s)
- **Interruption**: Test mid-stream abort for each routing path
- **Reconnection**: WebSocket reconnect preserves model selection
- LiteLLM proxy connection and auth validation
- Ollama health check and model availability
- Model switching flow with context reset
- Error handling scenarios and fallback logic
- Performance benchmarks (automatic vs explicit)
- Server-side model validation (reject invalid IDs)

### E2E Tests
- Complete user flow with "Automatic" selection (verify SDK routing)
- Complete user flow with explicit Claude model (verify fixed model)
- Complete user flow with Ollama model (verify LiteLLM path)
- Model switch warning modal displays correctly
- Model selection persists in localStorage across sessions
- Message streaming works for all model types
- Cost tracking comparison (automatic vs explicit)
- Health check failures degrade gracefully (hide unavailable models)
- Telemetry logs routing decisions correctly

## Rollback Plan

If issues arise during deployment:

1. **Feature Flag**: Disable via `ENABLE_MODEL_SELECTION=false`
2. **Revert to Automatic**: Set `DEFAULT_MODEL=auto` (preserves SDK default behavior)
3. **Revert Branch**: Git revert to main branch
4. **Emergency**: Remove LiteLLM proxy, disable Ollama (Anthropic models unaffected)

## Next Steps

1. ✅ **Create feature branch**: `git checkout -b feature/litellm-integration` (COMPLETED)
2. ✅ **Update PRP with model parameter details** (COMPLETED)
3. **Set up development environment**: Install Ollama and LiteLLM
4. **Test automatic mode**: Verify SDK's dynamic routing works with model=None
5. **Begin Phase 1**: Backend LiteLLM integration
6. **Daily progress updates**: Track in TASK.md
7. **Code review checkpoints**: After each phase

## Key Implementation Notes

### Critical: Model Parameter Usage

The `model` parameter in `ClaudeAgentOptions` controls SDK behavior:

```python
# AUTOMATIC MODE (Recommended Default)
options = ClaudeAgentOptions(
    model=None,  # SDK chooses Haiku/Sonnet/Opus dynamically
    fallback_model="claude-haiku-4-5-20250929",
    # ... other options
)

# EXPLICIT MODE (User-selected)
options = ClaudeAgentOptions(
    model="claude-sonnet-4-5-20250929",  # Fixed model
    fallback_model="claude-haiku-4-5-20250929",
    # ... other options
)
```

**Observed Behavior** (from Anthropic console logs):
- SDK uses Haiku 4.5 for simple list/count queries
- SDK uses Sonnet 4 with prompt caching for medium complexity
- SDK uses Sonnet 4.5 for complex analysis and extended thinking

**Implementation Decision**: Default to automatic mode to preserve this intelligent behavior.

## References

- [LiteLLM Documentation](https://docs.litellm.ai/)
- [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python)
- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Nuxt 3 Modal Patterns](https://nuxt.com/docs/examples/advanced/teleport)
- Example configuration: `examples/llm-gateway.md`

---

## Open Questions - RESOLVED

### Q1: Should Anthropic requests ever go through LiteLLM, or only non-Anthropic models?

**Answer**: Anthropic requests should NEVER go through LiteLLM by default.

**Rationale**:
- Preserves Claude Agent SDK features (MCP, automatic routing, thinking blocks)
- Maintains direct API access for best performance
- Avoids proxy layer overhead

**Implementation**:
- Default: `ALLOW_ANTHROPIC_VIA_LITELLM=false`
- Routing table enforces: All Anthropic → Path A (SDK Direct)
- Only non-Anthropic (Ollama) → Path B (LiteLLM Proxy)
- Override available but NOT RECOMMENDED (loses SDK features)

### Q2: What is the definitive proxy endpoint path for the Claude SDK?

**Answer**: Use unified endpoint `/v1` (NOT pass-through `/anthropic`)

**Specification**:
- LiteLLM proxy URL: `http://localhost:4000/v1`
- API format: Anthropic Messages API compatible
- Required LiteLLM version: v1.55.0+ (Anthropic format support)
- Endpoints used: `/v1/messages` (matches Anthropic API)

**NOT COMPATIBLE**:
- ❌ `/anthropic` (pass-through endpoint) - incompatible with SDK
- ❌ `/v1/chat/completions` (OpenAI format) - wrong API format

### Q3: Do we maintain per-model conversation state, or always reset on model change?

**Answer**: ALWAYS RESET conversation context on model switch.

**Rationale**:
- Different models have different context windows
- Different providers have different conversation formats
- Prevents context confusion and errors
- Clear user expectations (explicit warning modal)

**Implementation**:
- Backend: Close old agent session, start new session
- Frontend: Show warning modal before switch ("This will start a new conversation")
- Frontend: Preserve message history for display (read-only archive)
- Backend: Conversation context fully reset (no transfer)
- User explicitly confirms understanding via modal

---

*Generated: 2025-01-08*
*Status: Ready for Implementation*
*Version: 2.0 - Critical Gaps Addressed*

## Implementation Complete

### Completion Summary

All components of the LiteLLM integration have been successfully implemented:

#### Backend ✅
- Model registry with server-side validation
- Health monitoring for all services (Anthropic, LiteLLM, Ollama)
- Session management with model-specific state
- Telemetry and metrics tracking
- Agent factory with dual-path routing
- Graceful fallback to automatic Claude on any failure

#### API ✅
- /models endpoint for available models listing
- WebSocket protocol extended for model switching
- Health checks integrated into startup
- Full telemetry integration

#### Frontend ✅
- ModelSelector.vue component with modal UI
- useModelSelection composable for state management
- WebSocket handler updated for model switching
- Main UI integrated with model selector in header

#### Documentation ✅
- Complete implementation guide (docs/LITELLM_INTEGRATION.md)
- Environment template with 3 deployment scenarios
- Test suite for validation
- Security and performance considerations documented

### Test Results

All tests passing:
- Model registry validation ✅
- Health checks ✅
- Agent creation with fallback ✅
- Telemetry logging ✅
- API endpoints functional ✅

### Deployment Ready

The feature is now ready for deployment. To enable:
1. Configure .env from .env.template
2. Start LiteLLM proxy if using Ollama
3. Run the application with model selection enabled

---
*Implementation completed: December 8, 2025*
