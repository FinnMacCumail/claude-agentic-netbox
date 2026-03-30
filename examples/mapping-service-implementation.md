# Mapping Service Implementation Guide

This document explains how the mapping service works to provide bidirectional translation between real and anonymized values.

## Table of Contents
1. [Overview](#overview)
2. [Loading Greenmask Mappings](#loading-greenmask-mappings)
3. [Query Anonymization Flow](#query-anonymization-flow)
4. [Response Restoration Flow](#response-restoration-flow)
5. [Example Queries and Responses](#example-queries-and-responses)
6. [Implementation Patterns](#implementation-patterns)

---

## Overview

### The Problem

Users think in terms of real data:
- "Check status of **core-switch-nyc-01**"
- "List devices at **NYC-DC1**"
- "Show me IPs in **192.168.1.0/24**"

Claude must query anonymized data:
- Device: `device-7a3f2b` (not `core-switch-nyc-01`)
- Site: `site-9x4k1` (not `NYC-DC1`)
- IP: `10.172.45.89` (not `192.168.1.100`)

### The Solution

The **Mapping Service** provides:
1. **Query Anonymization**: User query → Anonymized query (for Claude)
2. **Response Restoration**: Anonymized response → Real response (for user)
3. **Consistency**: Uses Greenmask's exact mappings (not new hashes)

### Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    MAPPING SERVICE                         │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │           Greenmask Mapping File                     │ │
│  │  {                                                   │ │
│  │    "dcim_device.name": {                            │ │
│  │      "core-switch-nyc-01": "device-7a3f2b",        │ │
│  │      "edge-router-lon-05": "device-8b9c4d"         │ │
│  │    },                                                │ │
│  │    "dcim_site.name": {                              │ │
│  │      "NYC-DC1": "site-9x4k1"                        │ │
│  │    }                                                 │ │
│  │  }                                                   │ │
│  └──────────────────────────────────────────────────────┘ │
│                           ↓                                │
│                      Loaded into                           │
│                           ↓                                │
│  ┌──────────────────────────────────────────────────────┐ │
│  │     Forward Mappings (Original → Anonymized)        │ │
│  │  "core-switch-nyc-01" → "device-7a3f2b"            │ │
│  │  "NYC-DC1" → "site-9x4k1"                           │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │     Reverse Mappings (Anonymized → Original)        │ │
│  │  "device-7a3f2b" → "core-switch-nyc-01"            │ │
│  │  "site-9x4k1" → "NYC-DC1"                           │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## Loading Greenmask Mappings

### Greenmask Output Format

When Greenmask completes anonymization, it generates a mapping file:

```json
{
  "dcim_device.name": {
    "core-switch-nyc-01": "device-7a3f2b",
    "core-switch-nyc-02": "device-8b9m31",
    "edge-router-lon-05": "device-x2p9q7",
    "firewall-dmz-01": "device-m4n5p6"
  },
  "dcim_site.name": {
    "NYC-DC1": "site-9x4k1",
    "LONDON-DC2": "site-2m7n3",
    "TOKYO-DC3": "site-7a8b4"
  },
  "ipam_ipaddress.address": {
    "192.168.1.100/24": "10.172.45.89/24",
    "192.168.1.101/24": "10.172.98.12/24",
    "10.0.50.1/8": "10.173.78.34/8"
  },
  "dcim_interface.name": {
    "GigabitEthernet0/0": "interface-a1b2c3",
    "TenGigabitEthernet0/1": "interface-d4e5f6"
  }
}
```

### Loading Implementation

```python
# backend/anonymization/mapping_service.py
import json
from pathlib import Path
from typing import Dict, Optional

class MappingService:
    """Manages Greenmask anonymization mappings."""

    def __init__(self, mappings_file: str):
        self.mappings_file = Path(mappings_file)
        self.forward: Dict[str, Dict[str, str]] = {}  # original → anon
        self.reverse: Dict[str, str] = {}  # anon → original

    def load(self) -> None:
        """Load Greenmask mappings from JSON file."""
        with open(self.mappings_file) as f:
            raw = json.load(f)

        # Build forward mappings (table.column → {original: anon})
        for table_column, mappings in raw.items():
            self.forward[table_column] = mappings

            # Build reverse index (anon → original)
            for original, anonymized in mappings.items():
                # Store with table.column context
                key = f"{table_column}:{anonymized}"
                self.reverse[key] = original

                # Also store without prefix for fast lookup
                # WARNING: May have collisions if same anon value
                # used in multiple tables
                if anonymized not in self.reverse:
                    self.reverse[anonymized] = original

    def get_anonymized(
        self,
        original: str,
        entity_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Get anonymized value.

        Args:
            original: Original value (e.g., "core-switch-nyc-01")
            entity_type: Optional hint (e.g., "dcim_device.name")

        Returns:
            Anonymized value or None
        """
        # Try with entity type first
        if entity_type and entity_type in self.forward:
            return self.forward[entity_type].get(original)

        # Fall back to searching all tables
        for mappings in self.forward.values():
            if original in mappings:
                return mappings[original]

        return None

    def get_original(
        self,
        anonymized: str,
        entity_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Get original value (reverse lookup).

        Args:
            anonymized: Anonymized value (e.g., "device-7a3f2b")
            entity_type: Optional hint

        Returns:
            Original value or None
        """
        # Try with context
        if entity_type:
            key = f"{entity_type}:{anonymized}"
            if key in self.reverse:
                return self.reverse[key]

        # Fall back to generic lookup
        return self.reverse.get(anonymized)
```

### Usage Example

```python
# Initialize and load mappings
mapping_service = MappingService("/mappings/mappings_20260324.json")
mapping_service.load()

# Forward lookup
anon = mapping_service.get_anonymized("core-switch-nyc-01", "dcim_device.name")
print(anon)  # → "device-7a3f2b"

# Reverse lookup
orig = mapping_service.get_original("device-7a3f2b")
print(orig)  # → "core-switch-nyc-01"
```

---

## Query Anonymization Flow

### Step-by-Step Process

```
User Query: "Check status of core-switch-nyc-01 at NYC-DC1"
                           ↓
┌─────────────────────────────────────────────────────────┐
│ 1. DETECT ENTITIES                                      │
│    Regex patterns find:                                 │
│    - Device: "core-switch-nyc-01"                      │
│    - Site: "NYC-DC1"                                    │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ 2. LOOKUP IN MAPPINGS                                   │
│    - "core-switch-nyc-01" → "device-7a3f2b"           │
│    - "NYC-DC1" → "site-9x4k1"                          │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ 3. REPLACE IN QUERY                                     │
│    "Check status of device-7a3f2b at site-9x4k1"      │
└─────────────────────────────────────────────────────────┘
                           ↓
                  Send to Claude
```

### Implementation

```python
# backend/anonymization/query_anonymizer.py
import re
from typing import Dict, List, Tuple
from .mapping_service import MappingService

class QueryAnonymizer:
    """Anonymizes user queries."""

    def __init__(self, mapping_service: MappingService):
        self.mapping_service = mapping_service

        # Define entity detection patterns
        self.patterns = {
            'device': re.compile(
                r'\b([\w]+-switch-[\w]+|[\w]+-router-[\w]+|'
                r'[\w]+-firewall-[\w]+|[\w]+-server-[\w]+)\b',
                re.IGNORECASE
            ),
            'site': re.compile(
                r'\b([A-Z]{2,4}-DC\d+|[\w]+-Office|[\w]+-DataCenter)\b'
            ),
            'ip': re.compile(
                r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)\b'
            ),
        }

        # Map entity types to Netbox tables
        self.entity_tables = {
            'device': 'dcim_device.name',
            'site': 'dcim_site.name',
            'ip': 'ipam_ipaddress.address',
        }

    def anonymize(self, query: str) -> Tuple[str, Dict[str, str]]:
        """
        Anonymize a query.

        Args:
            query: Original user query

        Returns:
            Tuple of (anonymized_query, mappings_applied)
        """
        anonymized = query
        mappings_applied = {}

        # Process each entity type
        for entity_type, pattern in self.patterns.items():
            matches = pattern.findall(query)

            for match in matches:
                # Lookup in Greenmask mappings
                table_column = self.entity_tables.get(entity_type)
                anon_value = self.mapping_service.get_anonymized(
                    match,
                    entity_type=table_column
                )

                if anon_value:
                    # Replace in query
                    anonymized = anonymized.replace(match, anon_value)
                    mappings_applied[match] = anon_value

        return anonymized, mappings_applied
```

### Example Usage

```python
anonymizer = QueryAnonymizer(mapping_service)

# Example 1: Device query
query = "What's the status of core-switch-nyc-01?"
anon_query, mappings = anonymizer.anonymize(query)

print(f"Original: {query}")
print(f"Anonymized: {anon_query}")
print(f"Mappings: {mappings}")

# Output:
# Original: What's the status of core-switch-nyc-01?
# Anonymized: What's the status of device-7a3f2b?
# Mappings: {'core-switch-nyc-01': 'device-7a3f2b'}

# Example 2: Complex query
query = "List devices at NYC-DC1 with IPs in 192.168.1.0/24"
anon_query, mappings = anonymizer.anonymize(query)

print(f"Anonymized: {anon_query}")
# Output: List devices at site-9x4k1 with IPs in 10.172.45.0/24
```

---

## Response Restoration Flow

### Step-by-Step Process

```
Claude Response: "device-7a3f2b is active at site-9x4k1"
                           ↓
┌─────────────────────────────────────────────────────────┐
│ 1. DETECT ANONYMIZED VALUES                             │
│    Find all values matching anonymized patterns:        │
│    - "device-7a3f2b"                                   │
│    - "site-9x4k1"                                       │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ 2. REVERSE LOOKUP                                        │
│    - "device-7a3f2b" → "core-switch-nyc-01"           │
│    - "site-9x4k1" → "NYC-DC1"                          │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ 3. REPLACE IN RESPONSE                                   │
│    "core-switch-nyc-01 is active at NYC-DC1"           │
└─────────────────────────────────────────────────────────┘
                           ↓
                   Show to User
```

### Implementation

```python
# backend/anonymization/response_restorer.py
from .mapping_service import MappingService

class ResponseRestorer:
    """Restores original values in Claude's responses."""

    def __init__(self, mapping_service: MappingService):
        self.mapping_service = mapping_service

    def restore(self, response: str) -> str:
        """
        Restore original values in response.

        Args:
            response: Claude's response with anonymized values

        Returns:
            Response with real values restored
        """
        restored = response

        # CRITICAL: Sort by length (longest first)
        # Prevents partial replacements
        # Example: Replace "device-7a3f2b-backup" before "device-7a3f2b"
        reverse_items = sorted(
            self.mapping_service.reverse.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

        # Replace anonymized → original
        for anonymized, original in reverse_items:
            # Skip table.column prefixed keys
            if ':' in anonymized:
                continue

            if anonymized in restored:
                restored = restored.replace(anonymized, original)

        return restored
```

### Example Usage

```python
restorer = ResponseRestorer(mapping_service)

# Example 1: Simple response
response = "device-7a3f2b is active"
restored = restorer.restore(response)

print(f"Claude said: {response}")
print(f"User sees: {restored}")

# Output:
# Claude said: device-7a3f2b is active
# User sees: core-switch-nyc-01 is active

# Example 2: Complex response
response = """
Found 2 devices at site-9x4k1:
- device-7a3f2b (active)
- device-8b9m31 (offline)

IPs assigned:
- 10.172.45.89/24
- 10.172.98.12/24
"""

restored = restorer.restore(response)
print(restored)

# Output:
# Found 2 devices at NYC-DC1:
# - core-switch-nyc-01 (active)
# - core-switch-nyc-02 (offline)
#
# IPs assigned:
# - 192.168.1.100/24
# - 192.168.1.101/24
```

---

## Example Queries and Responses

### Example 1: Device Status Check

**User Query:**
```
"What's the status of core-switch-nyc-01?"
```

**Query Anonymization:**
```python
Original: "What's the status of core-switch-nyc-01?"
Anonymized: "What's the status of device-7a3f2b?"
Mappings: {'core-switch-nyc-01': 'device-7a3f2b'}
```

**Claude Receives:**
```
"What's the status of device-7a3f2b?"
```

**Claude Queries MCP:**
```python
netbox_get_objects(
    object_type="dcim.device",
    filters={"name": "device-7a3f2b"},
    fields=["id", "name", "status"]
)
```

**MCP Returns (from anonymized DB):**
```json
{
  "count": 1,
  "results": [{
    "id": 147,
    "name": "device-7a3f2b",
    "status": {"value": "active", "label": "Active"}
  }]
}
```

**Claude Responds:**
```
"device-7a3f2b is currently active."
```

**Response Restoration:**
```python
Anonymized: "device-7a3f2b is currently active."
Restored: "core-switch-nyc-01 is currently active."
```

**User Sees:**
```
"core-switch-nyc-01 is currently active."
```

---

### Example 2: Site Device List

**User Query:**
```
"List all devices at NYC-DC1"
```

**Query Anonymization:**
```python
Anonymized: "List all devices at site-9x4k1"
```

**Claude → MCP:**
```python
# Step 1: Find site
netbox_get_objects(
    object_type="dcim.site",
    filters={"name": "site-9x4k1"},
    fields=["id", "name"]
)
# Returns: {"id": 12, "name": "site-9x4k1"}

# Step 2: Find devices at site
netbox_get_objects(
    object_type="dcim.device",
    filters={"site_id": 12},
    fields=["id", "name", "status"]
)
```

**MCP Returns:**
```json
{
  "count": 3,
  "results": [
    {"id": 147, "name": "device-7a3f2b", "status": "active"},
    {"id": 148, "name": "device-8b9m31", "status": "active"},
    {"id": 201, "name": "device-x2p9q7", "status": "offline"}
  ]
}
```

**Claude Responds:**
```
"Site site-9x4k1 has 3 devices:
1. device-7a3f2b (active)
2. device-8b9m31 (active)
3. device-x2p9q7 (offline)"
```

**Response Restoration:**
```
"Site NYC-DC1 has 3 devices:
1. core-switch-nyc-01 (active)
2. core-switch-nyc-02 (active)
3. access-sw-lon-101 (offline)"
```

---

### Example 3: IP Address Query

**User Query:**
```
"Show me devices with IP 192.168.1.100"
```

**Query Anonymization:**
```python
Anonymized: "Show me devices with IP 10.172.45.89"
```

**Claude → MCP:**
```python
# Find IP address
netbox_get_objects(
    object_type="ipam.ipaddress",
    filters={"address": "10.172.45.89"},
    fields=["id", "address", "assigned_object_id", "dns_name"]
)
# Returns: {
#   "address": "10.172.45.89/24",
#   "assigned_object_id": 147,
#   "dns_name": "host-a1b2c3d4.internal"
# }

# Find device
netbox_get_object_by_id(
    object_type="dcim.device",
    object_id=147,
    fields=["id", "name", "status"]
)
```

**MCP Returns:**
```json
{
  "id": 147,
  "name": "device-7a3f2b",
  "status": "active"
}
```

**Claude Responds:**
```
"IP 10.172.45.89 is assigned to device-7a3f2b (DNS: host-a1b2c3d4.internal)"
```

**Response Restoration:**
```
"IP 192.168.1.100 is assigned to core-switch-nyc-01 (DNS: core-switch-nyc-01.prod.internal)"
```

---

## Implementation Patterns

### Pattern 1: Middleware Approach

Wrap all Claude interactions with anonymization:

```python
# backend/anonymization/middleware.py
class AnonymizationMiddleware:
    """Middleware for query/response translation."""

    def __init__(self, mapping_service, anonymizer, restorer):
        self.mapping_service = mapping_service
        self.anonymizer = anonymizer
        self.restorer = restorer

    async def process_query(self, user_query: str) -> str:
        """Anonymize before sending to Claude."""
        anon_query, mappings = self.anonymizer.anonymize(user_query)
        return anon_query

    async def process_response(self, claude_response: str) -> str:
        """Restore before showing to user."""
        restored = self.restorer.restore(claude_response)
        return restored

# Usage in API:
middleware = AnonymizationMiddleware(mapping_service, anonymizer, restorer)

# WebSocket handler
async for message from websocket:
    # Anonymize user query
    anon_query = await middleware.process_query(message)

    # Send to Claude
    async for chunk in agent.query(anon_query):
        # Restore response
        restored_chunk = await middleware.process_response(chunk.content)
        await websocket.send(restored_chunk)
```

### Pattern 2: Streaming with Partial Restoration

Handle streaming responses that may contain partial anonymized values:

```python
class StreamingRestorer:
    """Handles streaming response restoration."""

    def __init__(self, mapping_service):
        self.mapping_service = mapping_service
        self.buffer = ""

    def restore_chunk(self, chunk: str) -> str:
        """
        Restore a streaming chunk.

        Buffers partial values to handle word boundaries.
        """
        # Add to buffer
        self.buffer += chunk

        # Try to restore complete anonymized values in buffer
        restored = self.buffer
        for anon, orig in self.mapping_service.reverse.items():
            if ':' in anon:  # Skip prefixed keys
                continue
            if anon in restored:
                restored = restored.replace(anon, orig)

        # Determine how much we can safely return
        # Keep last few characters in buffer (might be partial anon value)
        if len(restored) > 20:
            safe_length = len(restored) - 20
            result = restored[:safe_length]
            self.buffer = restored[safe_length:]
            return result

        return ""

    def flush(self) -> str:
        """Flush remaining buffer."""
        result = self.buffer
        self.buffer = ""
        return result
```

### Pattern 3: Caching for Performance

Cache frequently used mappings:

```python
from functools import lru_cache

class CachedMappingService(MappingService):
    """Mapping service with LRU cache."""

    @lru_cache(maxsize=10000)
    def get_anonymized(self, original: str, entity_type: str = None) -> str:
        return super().get_anonymized(original, entity_type)

    @lru_cache(maxsize=10000)
    def get_original(self, anonymized: str, entity_type: str = None) -> str:
        return super().get_original(anonymized, entity_type)
```

---

## Testing Your Implementation

### Unit Tests

```python
# tests/test_anonymization/test_mapping_service.py
def test_forward_lookup():
    service = MappingService("test_mappings.json")
    service.load()

    result = service.get_anonymized("core-switch-nyc-01", "dcim_device.name")
    assert result == "device-7a3f2b"

def test_reverse_lookup():
    service = MappingService("test_mappings.json")
    service.load()

    result = service.get_original("device-7a3f2b")
    assert result == "core-switch-nyc-01"

# tests/test_anonymization/test_query_anonymizer.py
def test_anonymize_device_query():
    anonymizer = QueryAnonymizer(mapping_service)

    query = "Check status of core-switch-nyc-01"
    anon, mappings = anonymizer.anonymize(query)

    assert anon == "Check status of device-7a3f2b"
    assert mappings["core-switch-nyc-01"] == "device-7a3f2b"

# tests/test_anonymization/test_response_restorer.py
def test_restore_response():
    restorer = ResponseRestorer(mapping_service)

    response = "device-7a3f2b is active"
    restored = restorer.restore(response)

    assert restored == "core-switch-nyc-01 is active"
```

### Integration Test

```bash
# Test full flow
python -m pytest tests/test_anonymization/test_integration.py -v

# Test should:
# 1. Load mappings
# 2. Anonymize a query
# 3. Simulate Claude response
# 4. Restore response
# 5. Verify user sees original values
```

---

## Best Practices

1. **Always use Greenmask's mappings** - Don't generate new hashes
2. **Handle missing mappings gracefully** - Warn user if entity not found
3. **Sort by length when restoring** - Prevents partial replacements
4. **Cache frequently used lookups** - Improves performance
5. **Log anonymization operations** - For audit and debugging
6. **Test with real queries** - Ensure patterns match actual usage
7. **Monitor for new entities** - Alert when unmapped values appear

---

## References

- [GREENMASK_EXPLAINED.md](../docs/development/anonymization/GREENMASK_EXPLAINED.md) - Alignment concepts
- [greenmask-anonymization-patterns.md](./greenmask-anonymization-patterns.md) - Anonymization patterns
- [ANONYMIZATION_SOLUTION_REPORT.md](../docs/development/anonymization/ANONYMIZATION_SOLUTION_REPORT.md) - Full architecture
