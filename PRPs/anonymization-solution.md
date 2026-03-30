name: "Netbox Anonymization Solution with Greenmask"
description: |
  Complete implementation of a data anonymization solution for the Netbox-Claude integration,
  enabling secure querying of anonymized Netbox data through Claude AI while preserving
  full functionality and protecting sensitive information.

## Purpose
Implement a production-ready anonymization system that creates and maintains an anonymized
copy of Netbox data, allowing Claude AI to process infrastructure queries without exposure
to PII (personally identifiable information) such as IP addresses, device names, locations,
and contact details.

## Core Principles
1. **Privacy First**: Real production data never reaches Claude API
2. **Functionality Preserved**: 85-90% Claude effectiveness maintained after anonymization
3. **Deterministic Mapping**: Same input always produces same anonymized output
4. **Zero Production Impact**: Read-only access to production database
5. **Global rules**: Follow all rules in CLAUDE.md

---

## Goal
Build a secure anonymization layer that allows organizations to leverage Claude's advanced
reasoning capabilities for Netbox infrastructure queries while maintaining complete data
protection and regulatory compliance (GDPR, HIPAA, SOC2).

## Why
- **Security**: Prevent exposure of sensitive infrastructure data to external AI services
- **Compliance**: Meet GDPR, HIPAA, and SOC2 requirements for data protection
- **Business value**: Enable AI-powered infrastructure insights without security risk
- **User impact**: Transparent anonymization - users never see anonymized data
- **Problems solved**: Organizations can use Claude with Netbox without security concerns

## What
A comprehensive anonymization system with:
- **Greenmask Integration**: PostgreSQL-native database anonymization tool
- **Dual Database Setup**: Separate production and anonymized Netbox instances
- **Mapping Service**: Bidirectional translation between real and anonymized values
- **MCP Configuration**: Point MCP server to anonymized database
- **Feature Flag**: Toggle anonymization on/off for development/testing

### Success Criteria
- [ ] Greenmask successfully anonymizes full Netbox database copy
- [ ] All PII anonymized: device names, IPs, sites, locations, contacts
- [ ] All metadata preserved: IDs, foreign keys, status, roles, technical specs
- [ ] MCP server queries anonymized database (not production)
- [ ] Mapping service loads Greenmask mappings for consistency
- [ ] Query anonymization uses same mappings as database
- [ ] Response de-anonymization restores real values for users
- [ ] Claude maintains 85-90% effectiveness with anonymized data
- [ ] Docker Compose runs production + anonymized instances side-by-side
- [ ] All tests pass (anonymization validation, mapping service)
- [ ] Documentation complete with setup and troubleshooting guides

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window

- url: https://greenmask.io/docs
  why: Official Greenmask documentation for PostgreSQL anonymization
  critical: Deterministic hashing, validation rules, transformation types

- url: https://www.greenmask.io/blog/greenmask-configuration
  why: Configuration patterns and best practices
  critical: How to write transformation rules for complex schemas

- file: docs/development/anonymization/ANONYMIZATION_SOLUTION_REPORT.md
  why: Complete solution architecture and implementation details
  critical: System architecture, components, deployment strategy

- file: docs/development/anonymization/GREENMASK_EXPLAINED.md
  why: How Greenmask copies and anonymizes the database
  critical: Step-by-step process, alignment between DB and query anonymization

- file: docs/development/anonymization/ANONYMIZATION_RATIONALE.md
  why: Decision logic for what to preserve vs anonymize
  critical: What data must be preserved for Claude's reasoning

- file: docs/development/anonymization/greenmask-config-complete.yml
  why: Complete Greenmask configuration for 127+ Netbox tables
  critical: Transformation rules for all major Netbox models

- file: docs/development/anonymization/DEVELOPMENT_STRATEGY.md
  why: Recommended development approach
  critical: Git branch + Docker Compose + feature flag strategy

- file: docs/development/anonymization/GREENMASK_COPY_PROCESS.md
  why: Database copy and anonymization process details
  critical: Dump → Transform → Restore workflow

- file: docs/development/anonymization/GREENMASK_CONFIG_GUIDE.md
  why: Guide to creating and customizing Greenmask config
  critical: What Claude can and cannot help with

- docfile: examples/greenmask-anonymization-patterns.md
  why: Common anonymization patterns and examples
  critical: IP addresses, MAC addresses, deterministic hashing

- docfile: examples/mapping-service-implementation.md
  why: Query/response mapping service patterns
  critical: Loading Greenmask mappings, bidirectional translation

- url: https://docs.netbox.dev/en/stable/models/
  why: Netbox data model reference
  critical: Understanding tables, relationships, and field types

- url: https://docs.docker.com/compose/
  why: Docker Compose for running multiple Netbox instances
  critical: Networking, volumes, environment variables
```

### Current Codebase Tree
```bash
.
├── backend/
│   ├── agent.py                        # Claude Agent logic
│   ├── api.py                          # FastAPI server
│   ├── config.py                       # Configuration
│   ├── mcp_config.py                   # MCP server setup (points to PROD)
│   └── models.py                       # Pydantic models
├── docs/development/anonymization/     # All anonymization documentation
│   ├── ANONYMIZATION_SOLUTION_REPORT.md
│   ├── GREENMASK_EXPLAINED.md
│   ├── ANONYMIZATION_RATIONALE.md
│   ├── greenmask-config-complete.yml
│   ├── DEVELOPMENT_STRATEGY.md
│   ├── GREENMASK_COPY_PROCESS.md
│   └── GREENMASK_CONFIG_GUIDE.md
├── frontend/                           # Nuxt.js frontend
├── CLAUDE.md                           # Project rules
├── PRPs/
│   └── netbox-chatbox.md               # Original chatbox PRP
└── README.md
```

### Desired Codebase Tree
```bash
.
├── backend/
│   ├── agent.py                        # EXISTING - may need anonymization hooks
│   ├── api.py                          # EXISTING - may need anonymization routes
│   ├── config.py                       # MODIFIED - add anonymization settings
│   ├── mcp_config.py                   # MODIFIED - point to anonymized DB
│   ├── models.py                       # EXISTING
│   ├── anonymization/                  # NEW - Anonymization logic
│   │   ├── __init__.py
│   │   ├── mapping_service.py          # Greenmask mapping loader
│   │   ├── query_anonymizer.py         # Anonymize user queries
│   │   ├── response_restorer.py        # Restore real values in responses
│   │   └── greenmask_import.py         # Import Greenmask mappings
├── docs/development/anonymization/     # EXISTING - All docs already created
├── docker/                             # NEW - Docker Compose files
│   ├── docker-compose.anonymization.yml
│   ├── greenmask/
│   │   └── Dockerfile
│   └── netbox-anon/
│       └── docker-compose.yml
├── scripts/                            # NEW - Helper scripts
│   ├── run_greenmask.sh                # Trigger Greenmask anonymization
│   ├── import_mappings.py              # Import mappings to service
│   └── validate_anonymization.py       # Validate no PII in anon DB
├── tests/
│   ├── test_anonymization/             # NEW - Anonymization tests
│   │   ├── test_mapping_service.py
│   │   ├── test_query_anonymizer.py
│   │   ├── test_response_restorer.py
│   │   └── test_greenmask_config.py
├── .env.anonymization                  # NEW - Environment for anon mode
├── README.md                           # UPDATED - Add anonymization section
└── TASK.md                             # UPDATED - Track anonymization tasks
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: Greenmask uses DETERMINISTIC hashing
# Same seed + same input = same output ALWAYS
# This ensures query anonymization matches database anonymization
hash("core-switch-nyc-01" + "secret-seed") # → "7a3f2b" (always)

# CRITICAL: Preserve IDs and Foreign Keys
# Greenmask config MUST NOT anonymize:
- table: dcim_device
  columns:
    # ❌ DON'T anonymize these - Claude needs them for reasoning
    # - name: id
    # - name: site_id
    # - name: device_role_id
    # ✅ DO anonymize these
    - name: name
      type: hash
      engine: deterministic

# CRITICAL: MCP Configuration must point to ANONYMIZED database
# NOTE: URLs depend on whether MCP runs on HOST or in DOCKER

# ❌ WRONG (points to production):
# If MCP on HOST:
{
    "netbox": {
        "env": {
            "NETBOX_URL": "http://localhost:8000/api/"  # Production!
        }
    }
}

# If MCP in Docker:
{
    "netbox": {
        "env": {
            "NETBOX_URL": "http://netbox-prod:8080/api/"  # Production!
        }
    }
}

# ✅ CORRECT (points to anonymized):
# If MCP on HOST:
{
    "netbox": {
        "env": {
            "NETBOX_URL": "http://localhost:8001/api/"  # Anonymized!
        }
    }
}

# If MCP in Docker:
{
    "netbox": {
        "env": {
            "NETBOX_URL": "http://netbox-anon:8080/api/"  # Anonymized!
        }
    }
}

# CRITICAL: Mapping Service must load Greenmask's mappings
# Greenmask saves mappings during anonymization:
{
  "dcim_device.name": {
    "core-switch-nyc-01": "device-7a3f2b",
    "core-switch-nyc-02": "device-8b9m31"
  }
}
# Query anonymizer MUST use these exact mappings (not generate new ones)

# CRITICAL: Docker Network Isolation
# Production and anonymized databases should NOT be on same network
# Greenmask needs access to BOTH (for copying)
networks:
  prod-network:     # Production Netbox + DB
  anon-network:     # Anonymized Netbox + DB
  greenmask-network: # Greenmask connects to both

# GOTCHA: Vendor/Model Preservation
# Preserving vendor names (Cisco, Juniper) helps Claude reason
# But may be considered sensitive by some organizations
# Decision: Make it configurable via ANONYMIZE_VENDORS env var

# GOTCHA: Timestamps can reveal patterns
# If only ONE device was added on 2023-09-15
# AND company made public announcement on 2023-09-15
# Could correlate to identify organization
# Decision: Usually safe if many devices share dates

# CRITICAL: Greenmask validation rules
# Always run validation AFTER anonymization:
greenmask validate --config greenmask-config.yml
# Checks: referential integrity, unique constraints, no PII leakage

# GOTCHA: Anonymization is ONE-TIME COPY (for now)
# Future enhancement: Incremental sync for new data
# Current: Manual re-run when production data changes significantly
```

## Implementation Blueprint

### Development Workflow: Git Branch Strategy

**IMPORTANT**: Follow the Git Branch + Docker Compose + Feature Flag approach from DEVELOPMENT_STRATEGY.md.

#### Why This Approach?

✅ **Git Branch**: Clean version control, easy code review, safe experimentation
✅ **Docker Compose**: Run prod AND anon versions simultaneously on different ports
✅ **Feature Flag**: Toggle anonymization on/off with environment variable

#### Step-by-Step Workflow

```bash
# 1. Create feature branch (do this FIRST)
git checkout -b feature/anonymization
git push -u origin feature/anonymization

# 2. Develop anonymization code on this branch
# - All anonymization changes go here
# - Backend anonymization/ directory
# - Docker Compose configs
# - MCP configuration updates
# - Tests

# 3. Test both instances side-by-side using Docker
docker-compose -f docker/docker-compose.anonymization.yml up

# 4. When ready, create PR and merge to master
gh pr create --title "Add anonymization support" --body "..."
git checkout master
git merge feature/anonymization

# 5. Delete feature branch after merge
git branch -d feature/anonymization
```

#### Benefits

- ✅ Master branch stays clean during development
- ✅ Can run both prod and anon versions simultaneously (different ports)
- ✅ Easy stakeholder demos (show prod vs anon side-by-side)
- ✅ Easy to rollback if needed
- ✅ Clean code review process
- ✅ No code duplication

#### Port Allocation During Development

| Service | External Port (Host) | Internal Port (Container) | Purpose |
|---------|---------------------|---------------------------|---------|
| Production Netbox | 8000 | 8080 | Original data |
| Anonymized Netbox | 8001 | 8080 | Greenmask anonymized data |
| Prod Backend | 8002 | 8000 | Uses prod Netbox (no anonymization) |
| Anon Backend | 8003 | 8000 | Uses anon Netbox (with mapping service) |
| Frontend (prod mode) | 3000 | 3000 | Points to backend on 8002 |
| Frontend (anon mode) | 3001 | 3000 | Points to backend on 8003 |

#### CRITICAL: Docker Networking vs Host Access

**Understanding the Port Mapping:**

Netbox containers run on **port 8080 internally**, but get mapped to different **external ports**:

```yaml
# Docker Compose port mapping syntax: "external:internal"
services:
  netbox-prod:
    ports:
      - "8000:8080"  # External 8000 → Internal 8080
    # Inside Docker network: http://netbox-prod:8080
    # From host machine: http://localhost:8000

  netbox-anon:
    ports:
      - "8001:8080"  # External 8001 → Internal 8080
    # Inside Docker network: http://netbox-anon:8080
    # From host machine: http://localhost:8001
```

**Which URL to Use?**

| Your Setup | MCP Server Location | NETBOX_URL to Use |
|------------|---------------------|-------------------|
| **Current (Development)** | MCP runs on HOST | `http://localhost:8000` |
| **Docker (Production)** | MCP runs in container | `http://netbox-prod:8080` |
| **Current (Development)** | MCP runs on HOST | `http://localhost:8001` (anon) |
| **Docker (Production)** | MCP runs in container | `http://netbox-anon:8080` (anon) |

**Your Current Setup:**

```bash
# You currently have:
# - Netbox running at http://localhost:8000/
# - MCP server running on host (not in Docker)

# Therefore your .env should use:
NETBOX_URL=http://localhost:8000/api/
NETBOX_TOKEN=your-token

# When you create anonymized instance:
NETBOX_ANON_URL=http://localhost:8001/api/
NETBOX_ANON_TOKEN=your-anon-token
```

**After Docker Compose Setup:**

If you run everything in Docker, URLs change to **internal Docker names**:

```bash
# Docker network URLs (used when MCP is in Docker):
NETBOX_URL=http://netbox-prod:8080/api/
NETBOX_ANON_URL=http://netbox-anon:8080/api/
```

### Architecture Overview

The anonymization solution creates a complete separation between production and anonymized data:

1. **Production Environment**: Untouched, continues normal operation
2. **Anonymized Environment**: Separate Netbox instance with anonymized database
3. **Greenmask**: One-time copy tool that transforms production → anonymized
4. **Mapping Service**: Translates queries/responses between real and anonymized values
5. **MCP Server**: Points to anonymized database (not production)

```
┌────────────────────────────────────────────────────────────────┐
│                    PRODUCTION ENVIRONMENT                      │
│                                                                │
│  ┌──────────────┐         One-Time Copy        ┌────────────┐ │
│  │ Production   │────────────────────────────→  │ Anonymized │ │
│  │ Netbox DB    │        (Greenmask)            │ Netbox DB  │ │
│  │ (Real Data)  │                               │ (Fake Data)│ │
│  └──────────────┘                               └──────┬─────┘ │
│                                                         │       │
└─────────────────────────────────────────────────────────┼───────┘
                                                          │
┌─────────────────────────────────────────────────────────┼───────┐
│                  APPLICATION LAYER                      │       │
│                                                         ↓       │
│  ┌──────────┐                               ┌────────────────┐ │
│  │   User   │                               │  MCP Server    │ │
│  │  (sees   │                               │ (queries ANON  │ │
│  │   real   │                               │  DB, not PROD) │ │
│  │  names)  │                               └────────┬───────┘ │
│  └────┬─────┘                                        │         │
│       │                                              │         │
│       ↓                                              ↓         │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              MAPPING SERVICE                             │ │
│  │  - Anonymize queries: "core-sw-01" → "device-7a3f2b"   │ │
│  │  - Restore responses: "device-7a3f2b" → "core-sw-01"   │ │
│  │  - Uses Greenmask's mappings (loaded from file)         │ │
│  └──────────────────────────────────────────────────────────┘ │
│                              ↕                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                   CLAUDE AGENT                           │ │
│  │  - Receives: "Check status of device-7a3f2b"           │ │
│  │  - Queries MCP with anonymized names                    │ │
│  │  - Returns: "device-7a3f2b is active"                   │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### Data Models and Structure

```python
# backend/anonymization/models.py
from pydantic import BaseModel, Field
from typing import Dict, Literal, Optional
from datetime import datetime

class MappingEntry(BaseModel):
    """Single anonymization mapping entry."""
    original_value: str
    anonymized_value: str
    value_type: str  # e.g., "dcim_device.name", "dcim_site.name"
    table: str
    column: str

class GreenmaskMapping(BaseModel):
    """Greenmask mapping file structure."""
    mappings: Dict[str, Dict[str, str]]  # table.column -> {original: anonymized}
    run_id: str
    timestamp: datetime
    tables_processed: int

class AnonymizationConfig(BaseModel):
    """Anonymization configuration."""
    enabled: bool = False
    mode: Literal["greenmask"] = "greenmask"
    seed: str
    mappings_file: str
    preserve_vendors: bool = True  # Preserve vendor/model names
    preserve_tags: bool = True     # Preserve generic tags

class QueryAnonymizationResult(BaseModel):
    """Result of query anonymization."""
    original_query: str
    anonymized_query: str
    mappings_applied: Dict[str, str]
    entities_found: int
```

### List of Tasks in Implementation Order

```yaml
Task 0: Create Feature Branch (DO THIS FIRST!)
CRITICAL: Create feature/anonymization branch before any code changes
  - RUN: git checkout -b feature/anonymization
  - RUN: git push -u origin feature/anonymization
  - WORK: All anonymization development happens on this branch
  - BENEFIT: Master stays clean, easy rollback, clean PR
  - MERGE: Only merge to master when fully tested and validated

Task 1: Setup Anonymization Configuration
UPDATE backend/config.py:
  - ADD anonymization settings:
      * ANONYMIZATION_ENABLED: bool
      * ANONYMIZATION_MODE: str (default: "greenmask")
      * ANONYMIZATION_SEED: str (secret, from env)
      * GREENMASK_MAPPINGS_FILE: str
      * NETBOX_ANON_URL: str (anonymized Netbox URL)
      * NETBOX_ANON_TOKEN: str
      * ANONYMIZE_VENDORS: bool (preserve vendor names?)
  - VALIDATE anonymization seed is set if enabled
  - PROVIDE separate config for prod vs anon mode

Task 2: Update MCP Configuration for Anonymized Database
MODIFY backend/mcp_config.py:
  - ADD conditional logic:
      * IF anonymization enabled → use NETBOX_ANON_URL
      * ELSE → use NETBOX_URL (production)
  - ENSURE MCP server env vars point to correct database
  - DOCUMENT why MCP must query anonymized DB

Task 3: Implement Greenmask Mapping Loader
CREATE backend/anonymization/mapping_service.py:
  - FUNCTION load_greenmask_mappings(mappings_file: str) -> Dict:
      * READ Greenmask JSON mapping file
      * PARSE table.column → {original: anonymized} structure
      * STORE in memory for fast lookup
      * INDEX both directions: original→anon AND anon→original
  - FUNCTION get_anonymized_value(original: str, entity_type: str) -> Optional[str]:
      * LOOKUP original value in mappings
      * RETURN anonymized equivalent
      * RETURN None if not found
  - FUNCTION get_original_value(anonymized: str) -> Optional[str]:
      * REVERSE lookup anonymized → original
      * USED for response restoration

Task 4: Implement Query Anonymization
CREATE backend/anonymization/query_anonymizer.py:
  - IMPORT pattern matching for entities (device names, IPs, sites)
  - FUNCTION anonymize_query(query: str, mappings: Dict) -> QueryAnonymizationResult:
      * DETECT entities using regex patterns:
          - Device names: r'[\w]+-switch-[\w]+', r'[\w]+-router-[\w]+'
          - IPs: r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
          - Sites: r'[A-Z]{2,4}-DC\d+', r'[\w]+-Office'
      * LOOKUP each entity in Greenmask mappings
      * REPLACE with anonymized value
      * RETURN anonymized query + metadata
  - HANDLE entities not in mappings (warn user)
  - LOG anonymization operations for audit

Task 5: Implement Response Restoration
CREATE backend/anonymization/response_restorer.py:
  - FUNCTION restore_response(response: str, mappings: Dict) -> str:
      * DETECT anonymized values in response
      * LOOKUP original values using reverse mappings
      * REPLACE anonymized → original
      * SORT by length (longest first) to avoid partial replacements
      * RETURN response with real values restored
  - HANDLE: Multiple occurrences of same anonymized value
  - HANDLE: Anonymized values in different formats (tables, JSON)

Task 6: Create Greenmask Docker Setup
CREATE docker/greenmask/Dockerfile:
  - BASE: greenmask/greenmask:latest
  - COPY greenmask-config-complete.yml
  - INSTALL dependencies if needed
  - SET entrypoint for manual trigger

CREATE docker/docker-compose.anonymization.yml:
  - DEFINE services:
      * netbox-prod (existing production)
      * netbox-prod-db (existing production DB)
      * netbox-anon (new anonymized instance)
      * netbox-anon-db (new anonymized DB)
      * greenmask (anonymization tool)
      * redis (optional, for mapping cache)
  - CONFIGURE networks:
      * prod-network (production only)
      * anon-network (anonymized only)
      * greenmask-network (Greenmask access to both)
  - CONFIGURE volumes for persistence
  - SET environment variables per service

Task 7: Create Greenmask Execution Script
CREATE scripts/run_greenmask.sh:
  - LOAD environment variables
  - VALIDATE source and target databases accessible
  - RUN: greenmask --config /config.yml dump-restore
  - SAVE mappings: --save-mappings /mappings/mappings_$(date).json
  - VALIDATE: Check referential integrity after
  - IMPORT mappings to mapping service
  - LOG results and timing
  - ERROR handling and notifications

Task 8: Create Mapping Import Script
CREATE scripts/import_mappings.py:
  - READ Greenmask mapping JSON file
  - PARSE and validate structure
  - IMPORT into mapping service (if using database)
  - OR: Copy to backend/anonymization/mappings/ (if file-based)
  - VALIDATE all expected tables present
  - LOG import statistics

Task 9: Implement Anonymization Validation
CREATE scripts/validate_anonymization.py:
  - CONNECT to anonymized database
  - RUN queries to check for PII patterns:
      * IP addresses matching private ranges
      * Real device naming patterns
      * Real location names (NYC, London, etc.)
      * Email addresses
      * Phone numbers
  - GENERATE report of any PII found
  - FAIL if PII detected
  - PASS if clean

Task 10: Integrate Anonymization into Agent
MODIFY backend/agent.py (if needed):
  - IF anonymization enabled:
      * WRAP queries with anonymize_query()
      * WRAP responses with restore_response()
  - OR: Keep agent unchanged and handle in API layer
  - DECISION: Prefer API layer for separation of concerns

Task 11: Add Anonymization API Endpoints
MODIFY backend/api.py:
  - ADD GET /anonymization/status:
      * RETURN: enabled, mode, mappings loaded
  - ADD POST /anonymization/validate:
      * TEST query anonymization/restoration
      * RETURN: original, anonymized, restored
  - ADD GET /anonymization/stats:
      * RETURN: number of mappings, tables covered
  - OPTIONAL: WebSocket wrapper for query/response translation

Task 12: Create Unit Tests for Anonymization
CREATE tests/test_anonymization/test_mapping_service.py:
  - TEST: Load Greenmask mappings correctly
  - TEST: Lookup original → anonymized
  - TEST: Reverse lookup anonymized → original
  - TEST: Handle missing mappings gracefully
  - TEST: Case sensitivity handling

CREATE tests/test_anonymization/test_query_anonymizer.py:
  - TEST: Detect device names in queries
  - TEST: Detect IP addresses in queries
  - TEST: Detect site names in queries
  - TEST: Replace with anonymized values
  - TEST: Preserve non-sensitive content
  - TEST: Handle queries with no entities

CREATE tests/test_anonymization/test_response_restorer.py:
  - TEST: Restore device names in responses
  - TEST: Restore IP addresses in responses
  - TEST: Handle multiple occurrences
  - TEST: Handle partial matches correctly
  - TEST: Preserve response format (JSON, text, tables)

CREATE tests/test_anonymization/test_greenmask_config.py:
  - TEST: Greenmask config has all required tables
  - TEST: All PII fields are anonymized
  - TEST: All metadata fields preserved
  - TEST: Deterministic transformations configured

Task 13: Create Example Files
CREATE examples/greenmask-anonymization-patterns.md:
  - DOCUMENT: IP address anonymization patterns
  - DOCUMENT: MAC address anonymization
  - DOCUMENT: Deterministic hashing examples
  - DOCUMENT: What to preserve vs anonymize
  - INCLUDE: Code examples for custom transformations

CREATE examples/mapping-service-implementation.md:
  - DOCUMENT: How mapping service works
  - DOCUMENT: Loading Greenmask mappings
  - DOCUMENT: Query anonymization flow
  - DOCUMENT: Response restoration flow
  - INCLUDE: Example queries and responses

Task 14: Update Documentation
UPDATE README.md:
  - ADD: Anonymization overview section
  - ADD: Setup instructions for anonymized mode
  - ADD: Docker Compose usage
  - ADD: Triggering Greenmask anonymization
  - ADD: Troubleshooting anonymization issues

CREATE docs/development/anonymization/IMPLEMENTATION_GUIDE.md:
  - DOCUMENT: Step-by-step implementation
  - DOCUMENT: Testing anonymization
  - DOCUMENT: Validating results
  - DOCUMENT: Common issues and solutions

Task 15: Create Environment Configuration
CREATE .env.anonymization:
  - SET ANONYMIZATION_ENABLED=true
  - SET ANONYMIZATION_MODE=greenmask
  - SET ANONYMIZATION_SEED=<random-seed>
  # NOTE: URLs depend on your deployment:
  # If MCP runs on HOST (current setup):
  - SET NETBOX_URL=http://localhost:8000/api/
  - SET NETBOX_ANON_URL=http://localhost:8001/api/
  # If MCP runs in Docker (future):
  # - SET NETBOX_URL=http://netbox-prod:8080/api/
  # - SET NETBOX_ANON_URL=http://netbox-anon:8080/api/
  - SET NETBOX_TOKEN=<prod-token>
  - SET NETBOX_ANON_TOKEN=<anon-token>
  - SET GREENMASK_MAPPINGS_FILE=/mappings/latest.json
  - DOCUMENT each variable with comments
```

### Task 3 Pseudocode: Greenmask Mapping Loader

```python
# backend/anonymization/mapping_service.py
import json
import logging
from typing import Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class MappingService:
    """
    Loads and manages Greenmask anonymization mappings.

    Provides fast bidirectional lookup between original and anonymized values.
    Uses Greenmask's mapping file as the source of truth.
    """

    def __init__(self, mappings_file: str):
        """
        Initialize mapping service.

        Args:
            mappings_file: Path to Greenmask mapping JSON file
        """
        self.mappings_file = Path(mappings_file)
        self.forward_mappings: Dict[str, Dict[str, str]] = {}  # original → anon
        self.reverse_mappings: Dict[str, str] = {}  # anon → original
        self.loaded_at: Optional[datetime] = None
        self.tables_count = 0
        self.mappings_count = 0

    def load_mappings(self) -> None:
        """
        Load Greenmask mappings from JSON file.

        Expected format:
        {
          "dcim_device.name": {
            "core-switch-nyc-01": "device-7a3f2b",
            "access-sw-lon-01": "device-x2p9q7"
          },
          "dcim_site.name": {
            "NYC-DC1": "site-9x4k1"
          }
        }

        Raises:
            FileNotFoundError: If mappings file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        logger.info(f"Loading Greenmask mappings from {self.mappings_file}")

        if not self.mappings_file.exists():
            raise FileNotFoundError(
                f"Greenmask mappings file not found: {self.mappings_file}"
            )

        with open(self.mappings_file, 'r') as f:
            raw_mappings = json.load(f)

        # Build forward and reverse mappings
        for table_column, mapping_dict in raw_mappings.items():
            self.forward_mappings[table_column] = mapping_dict

            # Build reverse index (anon → original)
            for original, anonymized in mapping_dict.items():
                # PATTERN: Include table.column context for disambiguation
                key = f"{table_column}:{anonymized}"
                self.reverse_mappings[key] = original

                # Also store without prefix for faster generic lookup
                # RISK: Collisions if same anon value used in multiple tables
                if anonymized not in self.reverse_mappings:
                    self.reverse_mappings[anonymized] = original

            self.mappings_count += len(mapping_dict)

        self.tables_count = len(raw_mappings)
        self.loaded_at = datetime.utcnow()

        logger.info(
            f"Loaded {self.mappings_count} mappings across {self.tables_count} "
            f"tables from Greenmask"
        )

    def get_anonymized(
        self,
        original: str,
        entity_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Get anonymized value for original value.

        Args:
            original: Original value (e.g., "core-switch-nyc-01")
            entity_type: Optional table.column hint (e.g., "dcim_device.name")

        Returns:
            Anonymized value if found, None otherwise
        """
        # PATTERN: Try with entity_type first for accuracy
        if entity_type and entity_type in self.forward_mappings:
            return self.forward_mappings[entity_type].get(original)

        # PATTERN: Fall back to searching all tables
        for table_column, mappings in self.forward_mappings.items():
            if original in mappings:
                return mappings[original]

        # Not found - may be data added after Greenmask run
        logger.warning(
            f"No anonymized value found for '{original}' "
            f"(type: {entity_type}). May need to re-run Greenmask."
        )
        return None

    def get_original(
        self,
        anonymized: str,
        entity_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Get original value for anonymized value (reverse lookup).

        Args:
            anonymized: Anonymized value (e.g., "device-7a3f2b")
            entity_type: Optional table.column hint

        Returns:
            Original value if found, None otherwise
        """
        # PATTERN: Try with context first
        if entity_type:
            key = f"{entity_type}:{anonymized}"
            if key in self.reverse_mappings:
                return self.reverse_mappings[key]

        # PATTERN: Fall back to generic lookup
        return self.reverse_mappings.get(anonymized)

    def get_stats(self) -> Dict:
        """Get mapping statistics."""
        return {
            "loaded": self.loaded_at is not None,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "tables_count": self.tables_count,
            "mappings_count": self.mappings_count,
            "file": str(self.mappings_file),
        }
```

### Task 4 Pseudocode: Query Anonymization

```python
# backend/anonymization/query_anonymizer.py
import re
from typing import Dict, List, Tuple
from .mapping_service import MappingService
from .models import QueryAnonymizationResult
import logging

logger = logging.getLogger(__name__)

class QueryAnonymizer:
    """
    Anonymizes user queries by replacing real values with anonymized values.

    Uses Greenmask mappings to ensure consistency with anonymized database.
    """

    def __init__(self, mapping_service: MappingService):
        """Initialize with mapping service."""
        self.mapping_service = mapping_service

        # PATTERN: Compile regex patterns for different entity types
        self.patterns = {
            'device': re.compile(
                r'\b([\w]+-switch-[\w]+|[\w]+-router-[\w]+|'
                r'[\w]+-firewall-[\w]+|[\w]+-server-[\w]+)\b',
                re.IGNORECASE
            ),
            'site': re.compile(
                r'\b([A-Z]{2,4}-DC\d+|[\w]+-Office|[\w]+-DataCenter)\b',
                re.IGNORECASE
            ),
            'ip': re.compile(
                r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)\b'
            ),
        }

    def anonymize(self, query: str) -> QueryAnonymizationResult:
        """
        Anonymize a user query.

        Args:
            query: Original user query with real values

        Returns:
            QueryAnonymizationResult with anonymized query and metadata
        """
        anonymized_query = query
        mappings_applied = {}
        entities_found = 0

        # PATTERN: Process each entity type
        for entity_type, pattern in self.patterns.items():
            matches = pattern.findall(query)

            for match in matches:
                entities_found += 1

                # PATTERN: Lookup in Greenmask mappings
                # Use table.column hint based on entity type
                table_column = self._get_table_column(entity_type)
                anonymized = self.mapping_service.get_anonymized(
                    match,
                    entity_type=table_column
                )

                if anonymized:
                    # Replace in query
                    anonymized_query = anonymized_query.replace(match, anonymized)
                    mappings_applied[match] = anonymized
                    logger.debug(f"Anonymized '{match}' → '{anonymized}'")
                else:
                    # PATTERN: Handle missing mapping
                    logger.warning(
                        f"No mapping found for '{match}'. "
                        f"This entity may not exist in anonymized DB."
                    )
                    # Keep original value (will likely not match in anon DB)

        return QueryAnonymizationResult(
            original_query=query,
            anonymized_query=anonymized_query,
            mappings_applied=mappings_applied,
            entities_found=entities_found
        )

    def _get_table_column(self, entity_type: str) -> Optional[str]:
        """Map entity type to Netbox table.column."""
        mapping = {
            'device': 'dcim_device.name',
            'site': 'dcim_site.name',
            'ip': 'ipam_ipaddress.address',
        }
        return mapping.get(entity_type)
```

### Task 5 Pseudocode: Response Restoration

```python
# backend/anonymization/response_restorer.py
from typing import Dict
from .mapping_service import MappingService
import logging

logger = logging.getLogger(__name__)

class ResponseRestorer:
    """
    Restores original values in Claude's responses.

    Replaces anonymized values with real values so users see actual data.
    """

    def __init__(self, mapping_service: MappingService):
        """Initialize with mapping service."""
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
        replacements_made = 0

        # PATTERN: Get all reverse mappings
        # Sort by length (longest first) to avoid partial replacements
        # Example: "device-7a3f2b-backup" before "device-7a3f2b"
        reverse_mappings = self.mapping_service.reverse_mappings.items()
        sorted_mappings = sorted(
            reverse_mappings,
            key=lambda x: len(x[0]),
            reverse=True
        )

        # PATTERN: Replace anonymized → original
        for anonymized, original in sorted_mappings:
            # Skip table.column prefixed keys (used internally)
            if ':' in anonymized:
                continue

            if anonymized in restored:
                restored = restored.replace(anonymized, original)
                replacements_made += 1
                logger.debug(f"Restored '{anonymized}' → '{original}'")

        if replacements_made > 0:
            logger.info(f"Restored {replacements_made} values in response")

        return restored
```

### Integration Points

```yaml
ENVIRONMENT VARIABLES:
  .env.anonymization:
    - ANONYMIZATION_ENABLED: "true"
    - ANONYMIZATION_MODE: "greenmask"
    - ANONYMIZATION_SEED: "<random-secret-seed>"  # KEEP SECRET!
    # URLs for MCP on HOST (current setup):
    - NETBOX_URL: "http://localhost:8000/api/"
    - NETBOX_ANON_URL: "http://localhost:8001/api/"
    # URLs for MCP in Docker (alternative):
    # - NETBOX_URL: "http://netbox-prod:8080/api/"
    # - NETBOX_ANON_URL: "http://netbox-anon:8080/api/"
    - NETBOX_TOKEN: "<prod-token>"
    - NETBOX_ANON_TOKEN: "<anon-token>"
    - GREENMASK_MAPPINGS_FILE: "/mappings/mappings_latest.json"
    - ANONYMIZE_VENDORS: "true"  # Preserve vendor/model names
    - LOG_LEVEL: "INFO"

GREENMASK:
  config_file: docs/development/anonymization/greenmask-config-complete.yml
  source_db: postgresql://netbox:password@netbox-prod-db:5432/netbox
  target_db: postgresql://netbox:password@netbox-anon-db:5432/netbox_anonymized
  mappings_output: /mappings/mappings_$(date +%Y%m%d_%H%M%S).json
  execution: Manual trigger via docker exec greenmask /scripts/run_greenmask.sh

DOCKER COMPOSE:
  file: docker/docker-compose.anonymization.yml
  services:
    - netbox-prod (port 8000)
    - netbox-prod-db (port 5432)
    - netbox-anon (port 8001)
    - netbox-anon-db (port 5433)
    - greenmask (on-demand)
  networks:
    - prod-network (isolated)
    - anon-network (isolated)
    - greenmask-network (bridge to both)

MCP SERVER:
  config_update: backend/mcp_config.py
  change: NETBOX_URL → NETBOX_ANON_URL when anonymization enabled
  critical: MCP MUST query anonymized database, NOT production

MAPPING SERVICE:
  location: backend/anonymization/mapping_service.py
  data_source: Greenmask mapping JSON file
  startup: Load mappings on application start
  refresh: Reload when new Greenmask run completes

QUERY FLOW:
  1. User: "Check core-switch-nyc-01 status"
  2. QueryAnonymizer: "core-switch-nyc-01" → "device-7a3f2b"
  3. Claude receives: "Check device-7a3f2b status"
  4. Claude → MCP → Anonymized DB query
  5. MCP returns: {name: "device-7a3f2b", status: "active"}
  6. Claude responds: "device-7a3f2b is active"
  7. ResponseRestorer: "device-7a3f2b" → "core-switch-nyc-01"
  8. User sees: "core-switch-nyc-01 is active"
```

## Validation Loop

### Level 1: Greenmask Validation
```bash
# Validate Greenmask configuration
greenmask validate \
  --config docs/development/anonymization/greenmask-config-complete.yml

# Expected: All validation checks pass
# - Referential integrity preserved
# - All required fields present
# - Transformation rules valid
# - No syntax errors

# If errors: Read validation output, fix greenmask-config-complete.yml
```

### Level 2: Anonymization Execution
```bash
# Run Greenmask anonymization (one-time copy)
docker exec greenmask bash -c "
  greenmask \
    --config /config/greenmask-config-complete.yml \
    dump-restore \
    --validate \
    --save-mappings /mappings/mappings_$(date +%Y%m%d).json
"

# Expected:
# - Database copied successfully
# - All tables anonymized
# - Mapping file created
# - No errors in output

# Verify mapping file exists:
ls -lh docker/greenmask/mappings/

# If errors: Check database connectivity, disk space, config syntax
```

### Level 3: Anonymization Validation
```bash
# Validate no PII in anonymized database
python scripts/validate_anonymization.py \
  --database postgresql://netbox:pass@netbox-anon-db:5432/netbox_anonymized

# Expected checks:
# - No real IP addresses (192.168.x.x, 10.x.x.x)
# - No real device names (patterns like core-switch-nyc-01)
# - No real site names (NYC-DC1, London-Office)
# - No email addresses
# - No phone numbers
# - All IDs and foreign keys preserved

# Expected output:
# ✅ All PII checks passed
# ✅ Found 0 real IP addresses
# ✅ Found 0 real device names
# ✅ Found 0 real site names
# ✅ IDs preserved: 100%
# ✅ Foreign keys intact: 100%

# If PII found: Review Greenmask config, add missing transformations
```

### Level 4: Mapping Service Tests
```bash
# Test mapping service loads Greenmask mappings correctly
source venv_linux/bin/activate
uv run pytest tests/test_anonymization/ -v

# Expected tests:
# - test_mapping_service::test_load_mappings
# - test_mapping_service::test_forward_lookup
# - test_mapping_service::test_reverse_lookup
# - test_query_anonymizer::test_anonymize_device_names
# - test_query_anonymizer::test_anonymize_ip_addresses
# - test_response_restorer::test_restore_device_names

# Expected: All tests pass

# If failing: Fix mapping service logic, ensure mappings file correct
```

### Level 5: Integration Test
```bash
# Terminal 1: Start production + anonymized Netbox instances
docker-compose -f docker/docker-compose.anonymization.yml up

# Terminal 2: Verify both Netbox instances running
curl http://localhost:8000/api/  # Production Netbox
curl http://localhost:8001/api/  # Anonymized Netbox

# Terminal 3: Test MCP queries anonymized database
# Update backend/mcp_config.py to use NETBOX_ANON_URL
# Start backend:
cd backend
export ANONYMIZATION_ENABLED=true
# Use localhost URLs since MCP runs on host (not in Docker):
export NETBOX_ANON_URL=http://localhost:8001/api/
export GREENMASK_MAPPINGS_FILE=../docker/greenmask/mappings/mappings_latest.json
source ../venv_linux/bin/activate
uvicorn backend.api:app --reload

# Terminal 4: Test query flow
# Open http://localhost:3000
# Query: "List all sites"
# Expected: See real site names (NYC-DC1, London-Office)
# Verify in backend logs: Query was anonymized before sending to Claude

# If error: Check MCP config points to port 8001, not 8000
```

### Level 6: End-to-End Anonymization Test
```bash
# Full workflow test:
# 1. User sends query with real values
# 2. Query gets anonymized
# 3. Claude queries anonymized DB via MCP
# 4. Response gets restored with real values
# 5. User sees real values

# Test query: "What's the status of core-switch-nyc-01?"

# Expected backend logs:
# [QueryAnonymizer] Anonymized 'core-switch-nyc-01' → 'device-7a3f2b'
# [Claude] Querying MCP for device-7a3f2b
# [MCP] Query: netbox_get_objects(filters={"name": "device-7a3f2b"})
# [MCP] Result: {name: "device-7a3f2b", status: "active"}
# [Claude] Response: device-7a3f2b is active
# [ResponseRestorer] Restored 'device-7a3f2b' → 'core-switch-nyc-01'
# [API] Sending to user: core-switch-nyc-01 is active

# User sees: "core-switch-nyc-01 is active"

# Verify: User NEVER sees anonymized values
# Verify: Claude NEVER sees real values
# Verify: MCP queries anonymized DB (port 8001), not prod (port 8000)
```

## Final Validation Checklist
- [ ] Working on feature/anonymization branch (not master)
- [ ] Greenmask config validates successfully
- [ ] Anonymization completes without errors
- [ ] Mapping file generated with all tables
- [ ] No PII found in anonymized database
- [ ] All IDs and foreign keys preserved
- [ ] Mapping service loads Greenmask mappings
- [ ] Query anonymization detects and replaces real values
- [ ] Response restoration replaces anonymized values
- [ ] MCP server points to anonymized database (not production)
- [ ] Docker Compose runs both Netbox instances
- [ ] End-to-end query flow works correctly
- [ ] Users never see anonymized values
- [ ] Claude never sees real values
- [ ] All tests pass
- [ ] Documentation complete and accurate
- [ ] Feature branch ready for PR to master
- [ ] All commits on feature/anonymization branch

---

## Git Workflow Reminders
- ✅ **Always work on feature/anonymization branch** - Never commit directly to master
- ✅ **Commit frequently** - Small, atomic commits with clear messages
- ✅ **Test before committing** - Run validation checks before each commit
- ✅ **Create PR when ready** - Use GitHub PR for code review
- ✅ **Merge only when validated** - All tests pass, all checklists complete
- ✅ **Delete branch after merge** - Clean up feature branch post-merge

## Anti-Patterns to Avoid
- ❌ Don't develop on master branch - use feature/anonymization branch
- ❌ Don't skip creating feature branch - leads to messy git history
- ❌ Don't anonymize IDs or foreign keys - breaks Claude's reasoning
- ❌ Don't point MCP to production database when anonymization enabled
- ❌ Don't generate new anonymized values - use Greenmask's mappings
- ❌ Don't forget deterministic hashing seed - inconsistent anonymization
- ❌ Don't run Greenmask on production database write mode - READ ONLY
- ❌ Don't skip validation after anonymization - PII might leak
- ❌ Don't use same database for prod and anon - separate completely
- ❌ Don't expose anonymization seed in logs or error messages
- ❌ Don't forget to update mappings when re-running Greenmask
- ❌ Don't anonymize vendor/model names unless security requires it
- ❌ Don't skip testing reverse lookup (anonymized → original)
- ❌ Don't put Greenmask mappings file in version control - contains mappings

## Security Considerations
1. **Anonymization Seed**: Keep secret, never commit to git, rotate periodically
2. **Greenmask Mappings**: Treat as sensitive - contains real↔anonymized mappings
3. **Database Isolation**: Production and anonymized DBs on separate networks
4. **Read-Only Access**: Greenmask uses read-only credentials for production
5. **Audit Logging**: Log all query anonymization/restoration operations
6. **Mapping File Access**: Restrict access to mapping files (file permissions)
7. **Network Segmentation**: MCP should only access anonymized DB, never prod
8. **Environment Variables**: Use secrets management for all credentials

## Performance Considerations
1. **Mapping Lookup**: In-memory index for O(1) lookups
2. **Query Complexity**: Regex pattern matching adds ~5-10ms per query
3. **Response Processing**: Sorted replacement prevents partial matches
4. **Greenmask Runtime**: Depends on database size (estimate 1-2 hours for large DBs)
5. **Memory Usage**: Mapping service holds all mappings in memory (~10-50MB)
6. **Caching**: Consider Redis for mapping service if scaling needed

## Future Enhancements
1. **Incremental Sync**: Update anonymized DB with new production data
2. **Real-Time Anonymization**: Stream-based anonymization instead of batch
3. **Multi-Tenant**: Support multiple organizations with separate mappings
4. **Mapping API**: REST API for mapping service queries
5. **Audit Dashboard**: Web UI showing anonymization statistics
6. **Automated Testing**: CI/CD integration for anonymization validation
7. **Configurable Rules**: UI for customizing what gets anonymized
8. **Encryption**: Encrypt mapping files at rest
