# Local LLM Anonymization Strategy for Netbox-Claude Integration

## Executive Summary

This document outlines a comprehensive plan to replace the current regex-based anonymization system with an intelligent local LLM approach. This strategy addresses the fundamental limitations of pattern matching while maintaining complete data privacy by ensuring no PII ever reaches external services like Claude API.

## Problem Statement

### Current Regex Limitations

1. **Rigid Pattern Matching**:
   - "Butler site" fails to match "Butler Communications" in mappings
   - "Albany site" works only because "Albany" partially matches "DM-Albany"
   - Requires exact pattern structures that users rarely follow

2. **Maintenance Burden**:
   - Complex regex patterns for every possible entity format
   - Constant updates as new naming conventions emerge
   - Debugging regex is time-consuming and error-prone

3. **Poor User Experience**:
   - Users must use exact phrasing for anonymization to work
   - Natural language queries often fail
   - Claude compensates by manually reading mapping files (inefficient)

4. **Code Bug Identified**:
   - `match.group(0)` returns entire match instead of captured group
   - "Butler Communications site" → looks for entire phrase in mappings
   - Should use `match.group(1)` to get just "Butler Communications"

## Proposed Solution: Local LLM for Intelligent Anonymization

### Core Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│   User      │────▶│  Local LLM   │────▶│  Anonymize   │────▶│  Claude API │
│   Query     │     │  (Entity ID) │     │  (Mappings)  │     │  (w/ MCP)   │
└─────────────┘     └──────────────┘     └──────────────┘     └─────────────┘
                            │                                          │
                       (localhost)                                     │
                       No PII sent                                     │
                        externally                                     ▼
┌─────────────┐     ┌──────────────┐                         ┌─────────────┐
│   User      │◀────│   Restore    │◀─────────────────────────│  Response   │
│   Sees      │     │  Real Names  │                         │  (w/ hashes)│
└─────────────┘     └──────────────┘                         └─────────────┘
```

### Key Components

#### 1. Local LLM Server (Ollama)
- **Purpose**: Run small, fast language model locally
- **Model Options**:
  - Llama 3.2 3B (Recommended - best speed/accuracy balance)
  - Mistral 7B-Instruct (More accurate, slower)
  - Phi-3 Mini (Fastest, less accurate)
- **Resource Requirements**: 4-8GB RAM, runs on CPU
- **Port**: localhost:11434 (Ollama default)

#### 2. LLMAnonymizer Service
Replaces `QueryAnonymizer` with intelligent entity recognition:

```python
class LLMAnonymizer:
    def __init__(self, mapping_service, llm_client):
        self.mapping_service = mapping_service
        self.llm_client = llm_client
        self.entity_cache = {}  # Cache for performance

    async def anonymize(self, query: str) -> AnonymizationResult:
        # 1. Prepare context with available entities
        context = self._prepare_entity_context()

        # 2. Ask LLM to identify entities in query
        entities = await self._identify_entities(query, context)

        # 3. Map entities to anonymized versions
        anonymized = self._apply_anonymization(query, entities)

        return anonymized
```

#### 3. Entity Recognition Prompt

```markdown
System: You are an entity recognition system for network infrastructure queries.
You have access to these mappings:

Sites: ["DM-Albany", "Butler Communications", "DM-Akron", ...]
Devices: ["dmi01-albany-rtr01", "ncsu128-distswitch1", ...]
IPs: ["10.1.1.1", "192.168.1.100", ...]

Task: Identify entities in the user query that match items in the mappings.
Use fuzzy matching - "Butler" should match "Butler Communications".

User Query: "list all devices at the Butler site"

Response Format (JSON):
{
  "entities": [
    {
      "text": "Butler",
      "matched_entity": "Butler Communications",
      "type": "site",
      "start": 27,
      "end": 33
    }
  ]
}
```

#### 4. Smart Fallback Strategy

```python
async def anonymize_with_fallback(self, query: str):
    try:
        # Try LLM first
        result = await self.llm_anonymizer.anonymize(query)
        if result.entities_found > 0:
            return result
    except Exception as e:
        logger.warning(f"LLM anonymization failed: {e}")

    # Fallback to regex for simple patterns
    return self.regex_anonymizer.anonymize(query)
```

## Implementation Phases

### Phase 1: Infrastructure Setup (Week 1)

1. **Add Ollama to Docker Compose**:
```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: netbox-ollama
    ports:
      - "11434:11434"
    volumes:
      - ./ollama-models:/root/.ollama
    deploy:
      resources:
        limits:
          memory: 8G
```

2. **Pull and Configure Model**:
```bash
docker exec netbox-ollama ollama pull llama3.2:3b
docker exec netbox-ollama ollama pull mistral:7b-instruct  # Alternative
```

3. **Create Configuration**:
```python
# backend/anonymization/llm_config.py
LLM_CONFIG = {
    "provider": "ollama",
    "base_url": "http://localhost:11434",
    "model": "llama3.2:3b",
    "temperature": 0.1,  # Low for consistency
    "timeout": 5000,  # 5 seconds max
    "cache_ttl": 3600,  # Cache results for 1 hour
}
```

### Phase 2: LLM Anonymizer Development (Week 1-2)

1. **Create Core LLM Anonymizer**:
   - `backend/anonymization/llm_anonymizer.py`
   - Entity recognition logic
   - Caching for performance
   - Error handling and fallback

2. **Prompt Engineering**:
   - Create optimized prompts for entity extraction
   - Fine-tune for Netbox-specific terminology
   - Add few-shot examples for better accuracy

3. **Integration Layer**:
   - Update `ChatAgent` to use LLMAnonymizer
   - Keep ResponseRestorer unchanged (works well)
   - Add feature flag for gradual rollout

### Phase 3: Testing & Optimization (Week 2)

1. **Unit Tests**:
   - Test entity recognition accuracy
   - Benchmark performance (target < 200ms)
   - Test fallback mechanisms

2. **Integration Tests**:
   - End-to-end query processing
   - Complex multi-entity queries
   - Edge cases and error scenarios

3. **Performance Optimization**:
   - Implement result caching
   - Batch processing for multiple queries
   - Connection pooling for LLM client

### Phase 4: Deployment (Week 3)

1. **Feature Flag Rollout**:
```python
ANONYMIZATION_STRATEGY = os.getenv("ANONYMIZATION_STRATEGY", "regex")
if ANONYMIZATION_STRATEGY == "llm":
    anonymizer = LLMAnonymizer(mapping_service)
elif ANONYMIZATION_STRATEGY == "hybrid":
    anonymizer = HybridAnonymizer(llm, regex)
else:
    anonymizer = QueryAnonymizer(mapping_service)  # Current regex
```

2. **Monitoring**:
   - Track anonymization success rate
   - Monitor LLM response times
   - Log failed entity recognitions

3. **Documentation**:
   - Update user guides
   - Document prompt engineering
   - Create troubleshooting guide

## Technical Implementation Details

### Option 1: Ollama Integration (Recommended)

```python
# backend/anonymization/llm_anonymizer.py
import json
from typing import List, Dict, Any
import httpx
from backend.anonymization.models import QueryAnonymizationResult

class LLMAnonymizer:
    def __init__(self, mapping_service, config: Dict[str, Any]):
        self.mapping_service = mapping_service
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.model = config.get("model", "llama3.2:3b")
        self.client = httpx.AsyncClient(timeout=5.0)

    async def anonymize(self, query: str) -> QueryAnonymizationResult:
        # Build context from mappings
        context = {
            "sites": list(self.mapping_service.get_all_original_values("dcim_site.name")),
            "devices": list(self.mapping_service.get_all_original_values("dcim_device.name")),
            "ips": list(self.mapping_service.get_all_original_values("ipam_ipaddress.address"))
        }

        # Prepare prompt
        prompt = self._build_prompt(query, context)

        # Call Ollama
        response = await self.client.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1,
                "format": "json"
            }
        )

        # Parse response
        result = response.json()
        entities = json.loads(result["response"])

        # Apply anonymization
        return self._apply_anonymization(query, entities)
```

### Option 2: LangChain with Local Model

```python
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

class EntityExtraction(BaseModel):
    entities: List[Dict[str, str]] = Field(
        description="List of identified entities with their full names and types"
    )

class LangChainLLMAnonymizer:
    def __init__(self, mapping_service):
        self.mapping_service = mapping_service
        self.llm = Ollama(model="llama3.2:3b", temperature=0.1)
        self.parser = PydanticOutputParser(pydantic_object=EntityExtraction)

        self.prompt = PromptTemplate(
            template="""Identify network infrastructure entities in the query.

Available entities:
{context}

Query: {query}

{format_instructions}
""",
            input_variables=["context", "query"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
```

### Option 3: Direct API Integration

```python
class DirectLLMAnonymizer:
    """Minimal implementation without additional dependencies"""

    async def call_llm(self, prompt: str) -> Dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2:3b",
                    "prompt": prompt,
                    "stream": False
                }
            )
            return response.json()
```

## Benefits of Local LLM Approach

### 1. Privacy & Security
- **Zero PII Exposure**: All entity recognition happens locally
- **No External Dependencies**: LLM runs in your infrastructure
- **Audit Trail**: Complete control over data flow

### 2. Intelligence & Flexibility
- **Natural Language Understanding**: Handles variations like "Butler" → "Butler Communications"
- **Context Awareness**: Understands query intent
- **No Rigid Patterns**: Works with any phrasing

### 3. Performance
- **Fast Inference**: Small models respond in < 200ms
- **Caching**: Repeated queries are instant
- **Parallel Processing**: Can batch multiple queries

### 4. Maintainability
- **No Regex Maintenance**: No complex patterns to debug
- **Self-Improving**: Can fine-tune model on your data
- **Clear Separation**: Entity recognition separate from business logic

## Considerations & Tradeoffs

### Resource Requirements
- **RAM**: 4-8GB for model loading
- **CPU**: Works on standard CPUs, GPU optional
- **Storage**: 2-4GB per model

### Performance Characteristics
- **Initial Load**: 5-10 seconds to load model
- **Inference Time**: 50-200ms per query
- **Throughput**: 10-50 queries/second depending on hardware

### Accuracy Considerations
- **Training Data**: Model quality depends on training
- **Fine-tuning**: May need domain-specific tuning
- **Fallback Required**: Keep regex as backup

## Migration Strategy

### Step 1: Parallel Running
- Keep existing regex system
- Run LLM in shadow mode
- Compare results and tune

### Step 2: Gradual Rollout
- Start with 10% of queries
- Monitor success rate
- Increase gradually to 100%

### Step 3: Optimization
- Fine-tune model on failure cases
- Optimize prompts
- Implement caching strategies

## Success Metrics

1. **Accuracy**: > 95% entity recognition rate
2. **Performance**: < 200ms average response time
3. **Availability**: > 99.9% uptime
4. **User Satisfaction**: Reduced failed queries by 80%

## Risk Mitigation

1. **LLM Failure**: Automatic fallback to regex
2. **Performance Issues**: Caching and rate limiting
3. **Resource Exhaustion**: Container limits and monitoring
4. **Model Drift**: Regular evaluation and updates

## Conclusion

The local LLM approach solves the fundamental limitations of regex-based anonymization while maintaining complete data privacy. It provides intelligent entity recognition that understands natural language variations, making the system more robust and user-friendly.

Key advantages:
- No PII sent to external services
- Intelligent fuzzy matching
- Natural language understanding
- Easier to maintain than complex regex patterns

This strategy aligns with the core principle: **Privacy First** while dramatically improving user experience and system reliability.

## Next Steps

1. **Approval**: Review and approve this plan
2. **PoC Development**: Build minimal proof of concept
3. **Testing**: Validate accuracy and performance
4. **Full Implementation**: Complete development
5. **Deployment**: Gradual rollout with monitoring

## Appendix: Example Queries and Expected Behavior

### Current Regex Behavior
| Query | Result |
|-------|--------|
| "Albany site" | ✅ Works (partial match) |
| "Butler site" | ❌ Fails (group(0) bug) |
| "Butler Communications site" | ❌ Fails (looks for whole phrase) |
| "devices at Butler" | ❌ Fails (no pattern match) |

### Local LLM Behavior
| Query | Result |
|-------|--------|
| "Albany site" | ✅ Identifies "DM-Albany" |
| "Butler site" | ✅ Identifies "Butler Communications" |
| "Butler Communications site" | ✅ Identifies "Butler Communications" |
| "devices at Butler" | ✅ Identifies "Butler Communications" |
| "show me the Butler location" | ✅ Identifies "Butler Communications" |
| "Butler Comms devices" | ✅ Fuzzy matches to "Butler Communications" |