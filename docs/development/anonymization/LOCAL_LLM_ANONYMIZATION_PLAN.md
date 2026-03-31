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

#### 3. Dynamic Entity Recognition Strategy

Instead of hardcoding entity lists (which is unmaintainable), the system uses intelligent dynamic discovery:

```python
class DynamicLLMAnonymizer:
    def __init__(self, mapping_service):
        self.mapping_service = mapping_service
        # Automatically discover entity types from mappings
        self.entity_types = self._discover_entity_types()
        self.entity_index = self._build_entity_index()

    def _discover_entity_types(self):
        """Extract all table.column patterns from mappings"""
        types = {}
        for key in self.mapping_service.forward_mappings.keys():
            # Parse "dcim_device.name" -> {"dcim_device": ["name"]}
            table, column = key.split('.')
            if table not in types:
                types[table] = []
            types[table].append(column)
        return types
```

**Two-Stage Entity Recognition Process:**

**Stage 1: Entity Type Classification**
```markdown
System: Identify what types of network infrastructure entities are mentioned.

Available categories:
- Sites/Locations (data centers, offices, campuses)
- Devices (routers, switches, servers, PDUs)
- Network (IPs, VLANs, interfaces, circuits)
- Physical (racks, cables, power)

Query: "list all devices at the Butler site"
Response: ["sites", "devices"]
```

**Stage 2: Targeted Entity Extraction**
```markdown
System: You are an entity recognition system. Based on discovered patterns:

Sites in database follow patterns:
- "DM-{City}" (e.g., DM-Albany, DM-Akron)
- "{Name} Communications" (e.g., Butler Communications)
- Sample: [5-10 actual examples from database]
- Total available: 24 sites

Devices in database follow patterns:
- "dmi{##}-{location}-{type}{##}"
- "{prefix}-{function}-{location}"
- Sample: [5-10 actual examples]
- Total available: 72 devices

Query: "list all devices at the Butler site"

Task: Identify entities using fuzzy matching.
"Butler" should match "Butler Communications" if that exists.

Response:
{
  "entities": [
    {
      "text_in_query": "Butler",
      "matched_entity": "Butler Communications",
      "entity_type": "dcim_site.name",
      "confidence": 0.95
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

### Production-Ready Dynamic Implementation

```python
# backend/anonymization/llm_anonymizer.py
import json
import hashlib
from typing import List, Dict, Any, Optional
from collections import defaultdict
from cachetools import TTLCache
import httpx
from backend.anonymization.models import QueryAnonymizationResult

class ProductionLLMAnonymizer:
    """
    Production-ready LLM anonymizer with dynamic entity discovery.
    No hardcoded entity lists - everything discovered from mappings.
    """

    def __init__(self, mapping_service, config: Dict[str, Any]):
        self.mapping_service = mapping_service
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.model = config.get("model", "llama3.2:3b")
        self.client = httpx.AsyncClient(timeout=5.0)

        # Dynamic discovery at initialization
        self.entity_schema = self._discover_schema()
        self.entity_index = self._build_entity_index()

        # Performance optimization
        self.prompt_cache = TTLCache(maxsize=1000, ttl=3600)
        self.result_cache = TTLCache(maxsize=1000, ttl=300)

    def _discover_schema(self) -> Dict:
        """Automatically discover Netbox schema from mappings"""
        schema = {}

        for table_column in self.mapping_service.forward_mappings.keys():
            table, column = table_column.split('.')

            if table not in schema:
                schema[table] = {
                    "columns": [],
                    "sample_count": 0,
                    "patterns": set(),
                    "keywords": set()
                }

            schema[table]["columns"].append(column)

            # Analyze samples to learn patterns
            samples = list(self.mapping_service.forward_mappings[table_column].keys())[:100]
            schema[table]["sample_count"] = len(self.mapping_service.forward_mappings[table_column])

            for sample in samples:
                # Extract pattern (e.g., "dmi01-albany-rtr01" -> "XXN-XXX-XXXN")
                pattern = self._extract_pattern(sample)
                schema[table]["patterns"].add(pattern)

                # Extract keywords
                parts = re.split(r'[-_\.]', sample.lower())
                schema[table]["keywords"].update(parts)

        return schema

    def _build_entity_index(self) -> Dict:
        """Build searchable index for efficient entity lookup"""
        index = {
            "by_keyword": defaultdict(list),
            "by_prefix": defaultdict(list),
            "by_pattern": defaultdict(list)
        }

        for table_column, mappings in self.mapping_service.forward_mappings.items():
            for entity_name in mappings.keys():
                # Index by keywords
                keywords = re.split(r'[-_\.]', entity_name.lower())
                for keyword in keywords:
                    index["by_keyword"][keyword].append((entity_name, table_column))

                # Index by prefix
                prefix = entity_name.split('-')[0].lower() if '-' in entity_name else entity_name[:3].lower()
                index["by_prefix"][prefix].append((entity_name, table_column))

                # Index by pattern
                pattern = self._extract_pattern(entity_name)
                index["by_pattern"][pattern].append((entity_name, table_column))

        return index

    async def anonymize(self, query: str) -> QueryAnonymizationResult:
        """Main anonymization with intelligent context building"""

        # Check cache
        cache_key = hashlib.md5(query.encode()).hexdigest()
        if cache_key in self.result_cache:
            return self.result_cache[cache_key]

        # Stage 1: Identify entity types in query
        entity_types = await self._identify_entity_types(query)

        # Stage 2: Build targeted context (not all 1816 mappings!)
        context = self._build_targeted_context(query, entity_types)

        # Stage 3: Extract specific entities
        entities = await self._extract_entities(query, context)

        # Stage 4: Apply anonymization
        result = self._apply_anonymization(query, entities)

        # Cache result
        self.result_cache[cache_key] = result

        return result

    async def _identify_entity_types(self, query: str) -> List[str]:
        """First stage: Identify what types of entities to look for"""

        prompt = f"""Identify infrastructure entity types in this query.

Categories:
- sites: data centers, offices, locations
- devices: routers, switches, servers, PDUs
- network: IPs, VLANs, interfaces
- physical: racks, cables, power

Query: "{query}"

Return JSON list of relevant categories only.
Example: ["sites", "devices"]"""

        response = await self._llm_call(prompt)
        return json.loads(response)

    def _build_targeted_context(self, query: str, entity_types: List[str]) -> Dict:
        """Build minimal context with only relevant entities"""

        context = {"patterns": {}, "samples": {}, "stats": {}}
        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Find potentially relevant entities
        relevant_entities = set()

        # Search by keywords in query
        for word in query_words:
            if word in self.entity_index["by_keyword"]:
                for entity, type_ in self.entity_index["by_keyword"][word][:10]:
                    relevant_entities.add((entity, type_))

        # Group by type and build context
        for entity_type in entity_types:
            table_names = self._get_tables_for_type(entity_type)

            for table in table_names:
                if table in self.entity_schema:
                    # Add patterns
                    context["patterns"][table] = list(self.entity_schema[table]["patterns"])[:5]

                    # Add relevant samples
                    table_entities = [e for e, t in relevant_entities if t.startswith(table)]
                    if not table_entities and f"{table}.name" in self.mapping_service.forward_mappings:
                        # Get a few samples if no keyword matches
                        all_entities = list(self.mapping_service.forward_mappings[f"{table}.name"].keys())
                        table_entities = all_entities[:10]

                    context["samples"][table] = table_entities[:10]
                    context["stats"][table] = self.entity_schema[table]["sample_count"]

        return context

    def _get_tables_for_type(self, entity_type: str) -> List[str]:
        """Map entity type to Netbox tables"""
        mapping = {
            "sites": ["dcim_site", "dcim_location"],
            "devices": ["dcim_device", "dcim_devicetype"],
            "network": ["ipam_ipaddress", "ipam_vlan", "dcim_interface"],
            "physical": ["dcim_rack", "dcim_cable", "dcim_powerfeed"]
        }
        return mapping.get(entity_type, [])
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

### Option 3: Configuration-Driven Approach

Make the entire system configurable without code changes:

```yaml
# config/anonymization_config.yaml
anonymization:
  strategy: "dynamic_llm"  # Options: "regex", "llm", "hybrid"

  llm:
    provider: "ollama"
    base_url: "http://localhost:11434"
    model: "llama3.2:3b"
    temperature: 0.1
    timeout_ms: 500
    max_context_tokens: 1000

  entity_recognition:
    # Automatically discover from database
    auto_discover: true

    # Two-stage recognition
    stages:
      - type: "classification"
        enabled: true
        cache_ttl: 3600
      - type: "extraction"
        enabled: true
        max_samples_per_type: 10

    # Performance tuning
    optimization:
      use_cache: true
      cache_size: 1000
      cache_ttl: 300
      batch_size: 10
      parallel_requests: false

    # Context building
    context:
      max_entities_per_type: 20
      include_patterns: true
      include_statistics: true
      keyword_search_depth: 10

    # Fallback strategies
    fallback:
      - strategy: "fuzzy_match"
        threshold: 0.7
      - strategy: "pattern_match"
        enabled: true
      - strategy: "regex"  # Final fallback
        enabled: true

  # Semantic search (optional)
  embeddings:
    enabled: false
    model: "sentence-transformers/all-MiniLM-L6-v2"
    index_type: "faiss"  # or "annoy", "hnswlib"
    dimension: 384

  # Entity type mappings
  entity_types:
    # Map high-level types to Netbox tables
    sites:
      tables: ["dcim_site", "dcim_location"]
      keywords: ["site", "location", "datacenter", "office"]
    devices:
      tables: ["dcim_device", "dcim_devicetype"]
      keywords: ["device", "router", "switch", "server", "pdu"]
    network:
      tables: ["ipam_ipaddress", "ipam_vlan", "dcim_interface"]
      keywords: ["ip", "vlan", "interface", "network", "subnet"]
    physical:
      tables: ["dcim_rack", "dcim_cable", "dcim_powerfeed"]
      keywords: ["rack", "cable", "power", "port"]

  # Monitoring and metrics
  monitoring:
    log_level: "info"
    metrics_enabled: true
    track_performance: true
    alert_on_fallback: false
```

```python
# backend/anonymization/llm_config.py
import yaml
from pathlib import Path
from typing import Dict, Any

class AnonymizationConfig:
    """Load and manage anonymization configuration"""

    def __init__(self, config_path: str = "config/anonymization_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            # Return sensible defaults
            return self._get_defaults()

        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def _get_defaults(self) -> Dict[str, Any]:
        """Provide sensible defaults if no config file"""
        return {
            "anonymization": {
                "strategy": "hybrid",
                "llm": {
                    "provider": "ollama",
                    "base_url": "http://localhost:11434",
                    "model": "llama3.2:3b",
                    "temperature": 0.1
                },
                "entity_recognition": {
                    "auto_discover": True,
                    "optimization": {
                        "use_cache": True,
                        "cache_ttl": 300
                    }
                }
            }
        }

    def get_strategy(self) -> str:
        return self.config["anonymization"]["strategy"]

    def get_llm_config(self) -> Dict:
        return self.config["anonymization"]["llm"]

    def should_use_embeddings(self) -> bool:
        return self.config["anonymization"].get("embeddings", {}).get("enabled", False)
```

## Key Implementation Principles

### 1. Dynamic Discovery Over Hardcoding
```python
# ❌ AVOID: Hardcoded entity lists
context = {
    "sites": ["DM-Albany", "Butler Communications", ...],  # Unmaintainable!
    "devices": ["dmi01-albany-rtr01", ...]  # Gets outdated!
}

# ✅ PREFERRED: Dynamic discovery
context = {
    "patterns": self._discover_patterns_from_mappings(),
    "samples": self._get_relevant_samples(query),
    "stats": {"total_sites": len(self.mapping_service.forward_mappings["dcim_site.name"])}
}
```

### 2. Intelligent Context Building
- **Analyze the query first** to determine what types of entities to look for
- **Load only relevant subsets** of mappings based on query keywords
- **Use pattern matching** to identify potential entity formats
- **Provide statistics** instead of full lists when appropriate

### 3. Multi-Stage Recognition
1. **Classification Stage**: Identify entity categories (sites, devices, network)
2. **Context Building**: Load only relevant patterns and samples
3. **Extraction Stage**: Find specific entities using focused context
4. **Validation Stage**: Verify matches exist in mappings

### 4. Performance Optimization
- **Cache aggressively** at multiple levels (prompts, results, patterns)
- **Index entities** by keyword, prefix, and pattern for fast lookup
- **Limit context size** to stay within LLM token limits
- **Use fallback strategies** to handle edge cases

### 5. Configuration Over Code
- Make all parameters tunable via configuration files
- Support multiple strategies (LLM, regex, hybrid)
- Allow feature flags for gradual rollout
- Enable/disable components without code changes

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

The local LLM approach with **dynamic entity discovery** solves the fundamental limitations of regex-based anonymization while maintaining complete data privacy. By automatically discovering entities from the mapping database rather than hardcoding lists, the system remains maintainable and scalable as your Netbox instance evolves.

Key advantages:
- **No hardcoded entity lists** - Everything discovered dynamically from mappings
- **No PII sent to external services** - LLM runs entirely locally
- **Intelligent fuzzy matching** - Understands variations like "Butler" → "Butler Communications"
- **Natural language understanding** - Works with any query phrasing
- **Self-adapting** - Automatically handles new entities added to Netbox
- **Configuration-driven** - Tune behavior without code changes
- **Production-ready fallbacks** - Multiple strategies ensure reliability

The dynamic approach ensures that:
1. **New entities are automatically included** when mappings are regenerated
2. **No maintenance required** for entity lists as infrastructure grows
3. **Context is intelligently built** based on query analysis, not brute force
4. **Performance is optimized** by loading only relevant entity subsets

This strategy aligns with the core principles:
- **Privacy First** - All processing happens locally
- **Dynamic Discovery** - No hardcoded assumptions about your infrastructure
- **Intelligent Context** - Smart sampling instead of loading all 1,816+ mappings
- **Production Reliability** - Multiple fallback strategies ensure consistent operation

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