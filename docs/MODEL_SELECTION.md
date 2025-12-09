# Claude Model Selection and Intelligent Routing

## Overview

The Netbox Chatbox application uses the Claude Agent SDK's **intelligent routing** feature, which automatically optimizes model selection for cost and performance while maintaining the quality level you specify.

## How Model Selection Works

### The User's Choice

When you select a model in the UI (or specify one programmatically), you're setting the **target quality level** for responses:

- **Auto (Automatic Selection)**: SDK chooses the best model for each task
- **Claude Haiku 4.5**: Fast, cost-effective responses
- **Claude Sonnet 4.5**: Balanced performance and capability
- **Claude Opus 4**: Maximum capability and reasoning

### Behind the Scenes: Intelligent Routing

The Claude Agent SDK uses **multi-model routing** regardless of your selection. This means:

1. **Tool Execution**: Uses Haiku for MCP tool calls (fast, cheap)
2. **Intermediate Processing**: May use Sonnet for complex reasoning
3. **Final Response**: Uses your selected model for user-facing output

This optimization happens automatically and transparently.

## Example: Query with Sonnet Selected

When you ask "How many sites are in NetBox?" with Sonnet 4.5 selected:

### API Calls Made:
```
1. claude-haiku-4-5 (Tool Execution)
   - Processes MCP tool call to query NetBox
   - Gets site count: 24

2. claude-haiku-4-5 (Additional Tools)
   - Any follow-up tool calls for data gathering

3. claude-sonnet-4-5 (Final Response)
   - Generates user-facing response
   - "There are 24 sites in NetBox"
```

### Cost Optimization:
- Haiku calls: ~6 requests × $0.25/1M tokens = $0.0015
- Sonnet call: 1 request × $3/1M tokens = $0.003
- **Total**: ~$0.0045 vs $0.018 if only Sonnet was used
- **Savings**: 75% cost reduction while maintaining response quality

## When Each Model Is Used

### Haiku (claude-haiku-4-5-20251001)
- ✅ MCP tool execution
- ✅ Simple data retrieval
- ✅ Parsing and formatting
- ✅ Quick lookups

### Sonnet (claude-sonnet-4-5-20250929)
- ✅ Complex queries requiring reasoning
- ✅ Multi-step operations
- ✅ Comparative analysis
- ✅ Default for balanced tasks

### Opus (claude-opus-4-20250514)
- ✅ Advanced reasoning tasks
- ✅ Complex infrastructure analysis
- ✅ Multi-hop relationship queries
- ✅ Strategic recommendations

## Model Selection in the UI

The model selector shows your current model:

```
┌──────────────────────────────┐
│ Model: Claude Sonnet 4.5  ▼ │
└──────────────────────────────┘
```

Click to open the model selection modal and choose:
- Auto (Claude) - Recommended
- Claude Sonnet 4.5 - Balanced
- Claude Opus 4 - Maximum capability
- Claude Haiku 4.5 - Fast and economical

### Context Reset Warning

⚠️ **Important**: Switching models resets your conversation context. Claude will not remember previous messages after a model change.

## Programmatic Model Selection

### Backend (Python)

```python
from backend.agent import ChatAgent
from backend.config import Config

config = Config()

# Automatic routing (recommended)
agent = ChatAgent(config, model=None)

# Explicit model selection
agent = ChatAgent(config, model="claude-sonnet-4-5-20250929")
agent = ChatAgent(config, model="claude-opus-4-20250514")
agent = ChatAgent(config, model="claude-haiku-4-5-20250925")
```

### Frontend (TypeScript)

```typescript
// Send model change via WebSocket
socket.send(JSON.stringify({
  type: 'model_change',
  model: 'claude-sonnet-4-5-20250929'
}))

// "auto" maps to None (automatic routing)
socket.send(JSON.stringify({
  type: 'model_change',
  model: 'auto'
}))
```

## Understanding API Costs

### Example Query Breakdown

For a typical query "Show me device details for core-router-1":

| Model | Requests | Tokens | Cost per 1M | Query Cost |
|-------|----------|--------|-------------|------------|
| Haiku | 5 | 5,000 | $0.25 | $0.00125 |
| Sonnet | 1 | 1,000 | $3.00 | $0.003 |
| **Total** | **6** | **6,000** | - | **$0.00425** |

Compare to using only Sonnet:

| Model | Requests | Tokens | Cost per 1M | Query Cost |
|-------|----------|--------|-------------|------------|
| Sonnet | 6 | 6,000 | $3.00 | $0.018 |
| **Total** | **6** | **6,000** | - | **$0.018** |

**Savings with Intelligent Routing**: 76%

## Best Practices

### When to Use Auto
✅ Most queries
✅ General infrastructure questions
✅ When cost optimization matters
✅ When you're unsure which model to use

### When to Use Haiku
✅ Simple lookups
✅ List operations
✅ Status checks
✅ High-volume automated queries

### When to Use Sonnet
✅ Complex analysis
✅ Multi-step operations
✅ Comparative queries
✅ Default for important queries

### When to Use Opus
✅ Strategic planning
✅ Complex troubleshooting
✅ Advanced reasoning
✅ Critical decision support

## Monitoring Model Usage

You can monitor which models are being used via:

1. **Anthropic Console**: View detailed API logs at https://console.anthropic.com/
2. **Backend Logs**: Enable DEBUG logging to see model selection decisions
3. **Browser DevTools**: WebSocket messages include model metadata

### Backend Logging

```python
# In backend/config.py
LOG_LEVEL=DEBUG  # Shows model routing decisions
```

### Example Log Output

```
INFO: Switching model from auto to claude-sonnet-4-5-20250929
INFO: Agent session started for WebSocket (model: claude-sonnet-4-5-20250929)
DEBUG: Using Haiku for tool execution
DEBUG: Using Sonnet for final response
```

## FAQ

### Q: Why does the UI show Sonnet but Haiku is used in API logs?
**A**: This is expected. The SDK uses Haiku for tool execution (cheap, fast) and your selected model (Sonnet) for generating the final response.

### Q: Can I disable intelligent routing?
**A**: No, it's a built-in SDK optimization. Your model selection controls the quality of the final response, not intermediate operations.

### Q: Does model switching preserve conversation history?
**A**: No, switching models resets Claude's context (server-side). However, the UI preserves the chat history locally for display purposes.

### Q: What's the difference between "Auto" and explicitly selecting a model?
**A**:
- **Auto**: SDK chooses dynamically based on task complexity
- **Explicit**: Your selected model is used for final responses, but the SDK still uses Haiku for tools

### Q: Why are there multiple API calls for one query?
**A**: Each MCP tool call is a separate API request. Complex queries may require multiple tools (e.g., searching, filtering, formatting).

## Technical Details

### Model Identifiers

| Display Name | Model ID | API Endpoint |
|-------------|----------|--------------|
| Auto (Claude) | `null` | SDK chooses |
| Claude Haiku 4.5 | `claude-haiku-4-5-20250925` | messages API |
| Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` | messages API |
| Claude Opus 4 | `claude-opus-4-20250514` | messages API |

### WebSocket Message Format

```typescript
// Model change request
{
  type: 'model_change',
  model: string  // 'auto' | model ID
}

// Model changed confirmation
{
  type: 'model_changed',
  content: string,
  metadata: {
    model: {
      model: string,        // Current model ID or 'automatic'
      model_display: string, // Display name
      is_automatic: boolean  // True if using auto routing
    }
  }
}
```

## See Also

- [Claude Agent SDK Documentation](examples/claude-agent-sdk-python.md)
- [Backend API Documentation](backend/api.py)
- [Frontend Model Selection Component](frontend/components/ModelSelector.vue)
- [Anthropic Pricing](https://www.anthropic.com/pricing)
