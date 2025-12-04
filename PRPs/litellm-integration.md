# Project Requirements Plan: LiteLLM Integration

## Executive Summary
Implement LiteLLM proxy support in the Netbox Chatbox application to enable multi-model LLM support, allowing users to choose between Anthropic Claude models and locally-hosted Ollama models through a frontend modal interface.

## Project Context

### Current State
- **Backend**: FastAPI server with Claude Agent SDK integration (Claude 3.5 Sonnet default)
- **Frontend**: Nuxt 3 with Vue 3 Composition API and TypeScript
- **Communication**: WebSocket-based real-time streaming
- **Configuration**: Environment variables for API keys and endpoints
- **State Management**: Composables pattern (no Vuex/Pinia stores)

### Target State
- Support for multiple LLM providers through LiteLLM proxy
- User-selectable model via frontend modal
- Initial support for:
  - Anthropic Claude models (existing)
  - Ollama qwen2.5:14b-instruct-8k model
- Seamless model switching without session loss

## Technical Architecture

### LiteLLM Proxy Layer
```
Frontend (Port 3000)
    ↓ WebSocket
Backend API (Port 8001)
    ↓ HTTP/HTTPS
LiteLLM Proxy (Port 4000)
    ↓ Provider APIs
├── Anthropic API (Claude)
└── Ollama API (Port 11434)
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

#### Task 1.1: LiteLLM Configuration
```python
# backend/litellm_config.py
from typing import Optional, Dict, Any
from pydantic import BaseModel

class LiteLLMConfig(BaseModel):
    """LiteLLM proxy configuration."""
    enabled: bool = False
    proxy_url: str = "http://localhost:4000"
    api_key: Optional[str] = None
    timeout: int = 120
    max_retries: int = 3

class ModelConfig(BaseModel):
    """Individual model configuration."""
    id: str
    name: str
    provider: str  # "anthropic" | "ollama"
    description: str
    context_length: int
    litellm_model_name: str  # Model identifier for LiteLLM
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
    """Existing Claude SDK implementation."""
    # Current implementation

class LiteLLMAgent(BaseAgent):
    """New LiteLLM proxy implementation."""
    # New implementation

def create_agent(model_id: str, config: Config) -> BaseAgent:
    """Factory to create appropriate agent based on model selection."""
    # Agent creation logic
```

#### Task 1.3: API Endpoints
```python
# backend/api.py additions
@app.get("/models")
async def list_models() -> List[ModelConfig]:
    """Return available models based on configuration."""
    models = []

    # Always include Claude
    models.append(ModelConfig(
        id="claude-3-5-sonnet",
        name="Claude 3.5 Sonnet",
        provider="anthropic",
        description="Most capable Claude model",
        context_length=200000,
        litellm_model_name="claude-3-5-sonnet-20241022"
    ))

    # Include Ollama if configured
    if config.litellm_enabled and config.ollama_available:
        models.append(ModelConfig(
            id="qwen2.5-14b",
            name="Qwen 2.5 14B Instruct",
            provider="ollama",
            description="Local Ollama model",
            context_length=8192,
            litellm_model_name="ollama/qwen2.5:14b-instruct-8k"
        ))

    return models
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

### Risk 1: LiteLLM Compatibility
**Risk**: LiteLLM may not fully support Claude Agent SDK features
**Mitigation**:
- Maintain dual-path implementation
- Direct Claude SDK for Anthropic models
- LiteLLM only for non-Anthropic models

### Risk 2: Session State Loss
**Risk**: Model switching might lose conversation context
**Mitigation**:
- Clear user warning before switching
- Option to start new session on switch
- Consider context transfer if feasible

### Risk 3: Performance Degradation
**Risk**: Proxy layer adds latency
**Mitigation**:
- Direct connection for Claude (bypass proxy)
- Connection pooling for LiteLLM
- Response streaming optimization

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
- Both Claude and Ollama models accessible
- Model switching completes in < 2 seconds
- No session corruption on model change
- Error recovery works as expected

### Performance Metrics
- Response latency < 10% increase with proxy
- Streaming performance maintained
- Memory usage stable during model switches
- WebSocket connection remains stable

### User Experience Metrics
- Modal interaction intuitive
- Model selection persists correctly
- Clear indication of active model
- Smooth transition between models

## Timeline

| Phase | Duration | Dependencies | Milestone |
|-------|----------|--------------|-----------|
| Phase 1: Backend | 2 days | LiteLLM setup | Backend integration complete |
| Phase 2: Frontend | 1 day | None | Modal UI complete |
| Phase 3: Protocol | 1 day | Phase 1 & 2 | End-to-end flow working |
| Phase 4: Setup | 1 day | Phase 3 | Production ready |
| **Total** | **5 days** | | **Feature Complete** |

## Environment Variables

### Required New Variables
```bash
# LiteLLM Configuration
LITELLM_ENABLED=true
LITELLM_PROXY_URL=http://localhost:4000
LITELLM_API_KEY=sk-litellm-key

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b-instruct-8k

# Model Selection
DEFAULT_MODEL=claude-3-5-sonnet
ENABLE_MODEL_SELECTION=true
```

### Updated Variables
```bash
# Existing Anthropic config remains
ANTHROPIC_API_KEY=your-key

# Add optional LiteLLM routing
USE_LITELLM_FOR_ANTHROPIC=false
```

## Testing Strategy

### Unit Tests
- Config validation tests
- Agent factory tests
- Model listing tests
- WebSocket protocol tests

### Integration Tests
- LiteLLM proxy connection
- Model switching flow
- Error handling scenarios
- Performance benchmarks

### E2E Tests
- Complete user flow
- Modal interaction
- Model selection persistence
- Message streaming

## Rollback Plan

If issues arise during deployment:

1. **Feature Flag**: Disable via `ENABLE_MODEL_SELECTION=false`
2. **Revert Branch**: Git revert to main branch
3. **Direct Mode**: Set `USE_LITELLM_FOR_ANTHROPIC=false`
4. **Emergency**: Remove LiteLLM proxy, use direct Claude SDK

## Next Steps

1. **Create feature branch**: `git checkout -b feature/litellm-integration`
2. **Set up development environment**: Install Ollama and LiteLLM
3. **Begin Phase 1**: Backend LiteLLM integration
4. **Daily progress updates**: Track in TASK.md
5. **Code review checkpoints**: After each phase

## References

- [LiteLLM Documentation](https://docs.litellm.ai/)
- [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python)
- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Nuxt 3 Modal Patterns](https://nuxt.com/docs/examples/advanced/teleport)
- Example configuration: `examples/llm-gateway.md`

---

*Generated: 2025-12-04*
*Status: Ready for Implementation*
*Version: 1.0*