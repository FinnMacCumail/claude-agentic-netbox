# Greenmask Anonymization - Detailed Explanation

**Date:** 2026-03-24
**Purpose:** Clarify how Greenmask solution works for Netbox-Claude integration

---

## Question 1: How Does Greenmask Copy the Netbox Database?

### Overview
Greenmask creates a **complete structural copy** of your production Netbox PostgreSQL database with **anonymized values**. This is a one-time operation (future development will add automated sync capabilities).

### Step-by-Step Process

#### Step 1: Greenmask Connects to Production Database (READ-ONLY)
```bash
# Greenmask configuration (greenmask-config.yml)
database:
  host: netbox-prod.internal      # Your production Netbox database
  port: 5432
  name: netbox
  user: greenmask_readonly          # READ-ONLY user (important!)
  password: ${GREENMASK_DB_PASSWORD}
```

**Key Point:** Greenmask uses a **read-only** database user, so it cannot modify your production data.

---

#### Step 2: Greenmask Reads Schema + Data
Greenmask reads:
- ✅ All table schemas (columns, types, constraints)
- ✅ All foreign key relationships
- ✅ All indexes
- ✅ All data rows

**Example - What Greenmask sees in `dcim_device` table:**
```sql
-- Production Netbox Database
SELECT id, name, site_id, device_role_id, status FROM dcim_device;

+-----+--------------------+---------+----------------+--------+
| id  | name               | site_id | device_role_id | status |
+-----+--------------------+---------+----------------+--------+
| 147 | core-switch-nyc-01 | 12      | 3              | active |
| 148 | core-switch-nyc-02 | 12      | 3              | active |
| 201 | access-sw-lon-101  | 24      | 7              | active |
+-----+--------------------+---------+----------------+--------+
```

---

#### Step 3: Greenmask Applies Transformation Rules
Based on your configuration, Greenmask transforms **specific columns** while **preserving structure**.

**Your Greenmask transformation config:**
```yaml
transformations:
  - table: dcim_device
    columns:
      - name: name                 # ← Transform this column
        type: hash
        engine: deterministic      # ← Same input = same output (consistency!)
        seed: "${ANONYMIZATION_SEED}"
        format: "device-{{.Hash | substr 0 6}}"

      # These columns are NOT listed, so they pass through unchanged:
      # - id (147, 148, 201)
      # - site_id (12, 12, 24)
      # - device_role_id (3, 3, 7)
      # - status (active, active, active)
```

**Transformation Logic:**
```
Input:  "core-switch-nyc-01"
        ↓ (SHA256 hash with seed)
Hash:   "7a3f2b..."
        ↓ (take first 6 chars + format)
Output: "device-7a3f2b"
```

**CRITICAL:** Using the **same seed**, Greenmask will **always** produce:
- `"core-switch-nyc-01"` → `"device-7a3f2b"`
- `"core-switch-nyc-01"` → `"device-7a3f2b"` (tomorrow)
- `"core-switch-nyc-01"` → `"device-7a3f2b"` (next week)

This **deterministic** behavior is essential for consistency!

---

#### Step 4: Greenmask Writes to Anonymized Database
Greenmask writes the transformed data to a **separate database**.

```bash
output:
  type: postgres
  host: netbox-anon.internal     # ← Different database server!
  port: 5432
  name: netbox_anonymized         # ← Different database name
```

**Result - Anonymized Database (`netbox_anonymized`):**
```sql
SELECT id, name, site_id, device_role_id, status FROM dcim_device;

+-----+----------------+---------+----------------+--------+
| id  | name           | site_id | device_role_id | status |
+-----+----------------+---------+----------------+--------+
| 147 | device-7a3f2b  | 12      | 3              | active |
| 148 | device-8b9m31  | 12      | 3              | active |
| 201 | device-x2p9q7  | 24      | 7              | active |
+-----+----------------+---------+----------------+--------+
```

**Notice:**
- ✅ IDs preserved: `147, 148, 201` (same as production)
- ✅ site_id preserved: `12, 12, 24` (relationships intact!)
- ✅ device_role_id preserved: `3, 3, 7` (metadata intact!)
- ✅ status preserved: `active, active, active`
- ❌ names anonymized: `device-7a3f2b` instead of `core-switch-nyc-01`

---

#### Step 5: Greenmask Saves Mappings
Greenmask exports a **mapping file** showing what was transformed:

```json
// mappings_20260324_020000.json
{
  "dcim_device": {
    "name": {
      "core-switch-nyc-01": "device-7a3f2b",
      "core-switch-nyc-02": "device-8b9m31",
      "access-sw-lon-101": "device-x2p9q7"
    }
  },
  "dcim_site": {
    "name": {
      "NYC-DC1": "site-9x4k1",
      "LONDON-DC2": "site-2m7n3"
    }
  }
}
```

These mappings are stored in the **Mapping Service** database for bidirectional translation.

---

#### Complete Anonymization Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│               PRODUCTION ENVIRONMENT (Secure)                    │
│                                                                   │
│  ┌───────────────────────────────────────────────────────┐      │
│  │         Production Netbox Database                    │      │
│  │                                                        │      │
│  │  dcim_device:                                         │      │
│  │  +-----+--------------------+---------+--------+      │      │
│  │  | id  | name               | site_id | status |      │      │
│  │  +-----+--------------------+---------+--------+      │      │
│  │  | 147 | core-switch-nyc-01 | 12      | active |      │      │
│  │  | 148 | core-switch-nyc-02 | 12      | active |      │      │
│  │  +-----+--------------------+---------+--------+      │      │
│  └───────────────────────────────────────────────────────┘      │
│                              ↓                                   │
│                    (One-Time Copy/Manual Trigger)               │
│                              ↓                                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │              GREENMASK PROCESS                         │     │
│  │                                                         │     │
│  │  1. Read production data (read-only)                   │     │
│  │  2. Apply transformations:                             │     │
│  │     - Hash "core-switch-nyc-01" → "device-7a3f2b"     │     │
│  │     - Preserve IDs, foreign keys, status              │     │
│  │  3. Validate integrity                                 │     │
│  │  4. Write to anonymized database                       │     │
│  │  5. Export mappings                                    │     │
│  └────────────────────────────────────────────────────────┘     │
│                              ↓                                   │
└──────────────────────────────┼──────────────────────────────────┘
                               ↓
┌──────────────────────────────┼──────────────────────────────────┐
│            ANONYMIZED ENVIRONMENT (Claude queries this)          │
│                              ↓                                   │
│  ┌───────────────────────────────────────────────────────┐      │
│  │         Anonymized Netbox Database                    │      │
│  │                                                        │      │
│  │  dcim_device:                                         │      │
│  │  +-----+----------------+---------+--------+          │      │
│  │  | id  | name           | site_id | status |          │      │
│  │  +-----+----------------+---------+--------+          │      │
│  │  | 147 | device-7a3f2b  | 12      | active |          │      │
│  │  | 148 | device-8b9m31  | 12      | active |          │      │
│  │  +-----+----------------+---------+--------+          │      │
│  └───────────────────────────────────────────────────────┘      │
│                              ↑                                   │
│                              │                                   │
│                      MCP Server queries HERE                     │
│                      (NOT production!)                           │
└──────────────────────────────────────────────────────────────────┘
```

---

## Question 2: How Do MCP Tools Query the Greenmask Database?

### Current Setup (Before Greenmask)

**File:** `backend/mcp_config.py`

Currently, your MCP server is configured to query the **production** Netbox database:

```python
# backend/mcp_config.py (CURRENT)
def get_netbox_mcp_config(config: Config) -> dict:
    return {
        "netbox": {
            "command": "python",
            "args": [
                "/home/ola/dev/rnd/mcp/testmcp/netbox-mcp-server/server.py"
            ],
            "env": {
                "NETBOX_URL": config.netbox_url,      # ← Points to production!
                "NETBOX_TOKEN": config.netbox_token,   # ← Production token!
                "LOG_LEVEL": "INFO"
            }
        }
    }
```

This means:
- ✅ MCP server connects to `http://production-netbox/api/`
- ✅ Uses production API token
- ❌ Claude sees **real data** (the problem!)

---

### Updated Setup (With Greenmask)

**Change Required:** Point MCP server to the **anonymized** Netbox instance instead.

**Updated File:** `backend/mcp_config.py`

```python
# backend/mcp_config.py (WITH GREENMASK)
def get_netbox_mcp_config(config: Config) -> dict:
    """
    Configure MCP server to query anonymized Netbox database.

    NOTE: With Greenmask solution, MCP queries the anonymized database,
    NOT the production database. This ensures Claude never sees real PII.
    """
    return {
        "netbox": {
            "command": "python",
            "args": [
                "/home/ola/dev/rnd/mcp/testmcp/netbox-mcp-server/server.py"
            ],
            "env": {
                # Point to anonymized Netbox instance
                "NETBOX_URL": config.netbox_anon_url,      # ← NEW: Anonymized instance!
                "NETBOX_TOKEN": config.netbox_anon_token,   # ← NEW: Anon DB token!
                "LOG_LEVEL": "INFO"
            }
        }
    }
```

**Environment Variables (`.env`):**
```bash
# Production Netbox (NEVER accessed by MCP when Greenmask is enabled)
NETBOX_URL=http://production-netbox.internal/api/
NETBOX_TOKEN=prod_token_abc123

# Anonymized Netbox (MCP queries THIS)
NETBOX_ANON_URL=http://netbox-anon.internal/api/
NETBOX_ANON_TOKEN=anon_token_xyz789

# Enable Greenmask mode
ANONYMIZATION_MODE=greenmask
```

---

### How It Works After Change

**MCP Tool Call Flow:**

```
Claude makes MCP call:
    netbox_get_objects(
        object_type="dcim.device",
        filters={"site_id": 12}
    )
           ↓
MCP Server receives call
           ↓
MCP Server queries: http://netbox-anon.internal/api/dcim/devices/?site_id=12
           ↓
Anonymized Netbox API returns:
    {
      "results": [
        {
          "id": 147,
          "name": "device-7a3f2b",     ← Anonymized!
          "site": {
            "id": 12,
            "name": "site-9x4k1"        ← Anonymized!
          },
          "status": {"value": "active"}, ← Real metadata preserved
          "device_role": {"name": "core"} ← Real metadata preserved
        }
      ]
    }
           ↓
MCP Server returns to Claude
           ↓
Claude processes anonymized data
```

**Key Point:** The **Netbox MCP server code doesn't change** - you just point it to a different database URL!

---

### Infrastructure Setup

You'll need to run **two Netbox instances**:

```
┌────────────────────────────────────────────────────────┐
│  PRODUCTION NETBOX                                     │
│  URL: http://production-netbox.internal/api/          │
│  Database: netbox (production PostgreSQL)              │
│  Access: Internal network only                         │
│  Used by: Production network management tools          │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│  ANONYMIZED NETBOX                                     │
│  URL: http://netbox-anon.internal/api/                │
│  Database: netbox_anonymized (PostgreSQL)              │
│  Access: MCP server only                               │
│  Used by: Claude via MCP                               │
│  Updated: Manually as needed (auto-sync is future dev) │
└────────────────────────────────────────────────────────┘
```

**Docker Compose Example:**

```yaml
# docker-compose.yml
services:
  # Production Netbox (existing)
  netbox-prod:
    image: netboxcommunity/netbox:latest
    environment:
      - DB_HOST=netbox-db-prod
      - DB_NAME=netbox
    networks:
      - production

  netbox-db-prod:
    image: postgres:15
    volumes:
      - netbox_prod_data:/var/lib/postgresql/data
    networks:
      - production

  # Anonymized Netbox (new)
  netbox-anon:
    image: netboxcommunity/netbox:latest
    environment:
      - DB_HOST=netbox-db-anon
      - DB_NAME=netbox_anonymized
    networks:
      - anonymized
    ports:
      - "8001:8080"  # Different port

  netbox-db-anon:
    image: postgres:15
    volumes:
      - netbox_anon_data:/var/lib/postgresql/data
    networks:
      - anonymized

  # Greenmask (trigger manually as needed)
  greenmask:
    image: greenmask/greenmask:latest
    volumes:
      - ./greenmask-config.yml:/config.yml
      - ./mappings:/mappings
    networks:
      - production  # Needs access to production DB (read-only)
      - anonymized  # Needs access to anonymized DB (write)
    command: ["tail", "-f", "/dev/null"]  # Keep running, trigger manually

volumes:
  netbox_prod_data:
  netbox_anon_data:

networks:
  production:
  anonymized:
```

---

## Question 3: How Does Query Anonymization Align with Database Anonymization?

This is the **critical piece** that makes the whole solution work!

### The Alignment Problem

**User types:** "Check status of core-switch-nyc-01"

**Problems:**
1. ❌ Anonymized database doesn't have "core-switch-nyc-01"
2. ❌ It only has "device-7a3f2b"
3. ❌ If we send "core-switch-nyc-01" to Claude → Claude queries for it → MCP finds nothing!

**Solution:** Use the **same Greenmask mappings** to anonymize the user's query BEFORE sending to Claude.

---

### Alignment Mechanism: Shared Mapping Database

#### Step 1: Greenmask Creates Mappings During Anonymization

When Greenmask anonymizes the database, it saves mappings:

```json
// /mappings/mappings_20260324.json
{
  "dcim_device.name": {
    "core-switch-nyc-01": "device-7a3f2b",
    "core-switch-nyc-02": "device-8b9m31",
    "access-sw-lon-101": "device-x2p9q7"
  },
  "dcim_site.name": {
    "NYC-DC1": "site-9x4k1",
    "LONDON-DC2": "site-2m7n3"
  }
}
```

---

#### Step 2: Mapping Service Loads These Mappings

**After Greenmask completes**, the mapping service imports these mappings:

```python
# backend/anonymization/mapping_service.py

async def load_greenmask_mappings(mappings_file: str):
    """
    Load Greenmask mappings into mapping service.

    This ensures query anonymization matches database anonymization.
    """
    with open(mappings_file) as f:
        greenmask_mappings = json.load(f)

    # Store in Redis + PostgreSQL
    for table_column, mappings in greenmask_mappings.items():
        for original, anonymized in mappings.items():
            await mapping_service.store_mapping(
                session_id="global",  # Global mappings from Greenmask
                value_type=table_column,
                original=original,
                anonymized=anonymized
            )
```

Now the mapping service knows:
- `"core-switch-nyc-01"` → `"device-7a3f2b"`
- `"NYC-DC1"` → `"site-9x4k1"`

---

#### Step 3: User Query Gets Anonymized Using Same Mappings

**User sends:** "Check status of core-switch-nyc-01"

**Mapping service processes:**

```python
# backend/anonymization/mapping_service.py

query = "Check status of core-switch-nyc-01"

# Pattern matching detects device name
matches = device_pattern.findall(query)  # Finds: ["core-switch-nyc-01"]

# Lookup in mapping database
for match in matches:
    anonymized = await get_mapping("core-switch-nyc-01", "dcim_device.name")
    # Returns: "device-7a3f2b"

    query = query.replace("core-switch-nyc-01", "device-7a3f2b")

# Result: "Check status of device-7a3f2b"
```

**Anonymized query sent to Claude:** "Check status of device-7a3f2b"

---

#### Step 4: Claude Queries Using Anonymized Name

Claude receives: "Check status of device-7a3f2b"

Claude makes MCP call:
```python
netbox_get_objects(
    object_type="dcim.device",
    filters={"name": "device-7a3f2b"}  # ← Matches anonymized DB!
)
```

MCP queries anonymized database:
```sql
SELECT * FROM dcim_device WHERE name = 'device-7a3f2b';
```

✅ **Found!** Because the anonymized database has this exact name.

Returns:
```json
{
  "id": 147,
  "name": "device-7a3f2b",
  "status": "active",
  "site": {"id": 12, "name": "site-9x4k1"}
}
```

---

#### Step 5: Response Gets De-anonymized

Claude responds: "Device device-7a3f2b is active at site site-9x4k1"

Mapping service reverses the mappings:
```python
response = "Device device-7a3f2b is active at site site-9x4k1"

# Reverse mappings
response = response.replace("device-7a3f2b", "core-switch-nyc-01")
response = response.replace("site-9x4k1", "NYC-DC1")

# Result: "Device core-switch-nyc-01 is active at site NYC-DC1"
```

**User sees:** "Device core-switch-nyc-01 is active at site NYC-DC1"

---

### Complete Flow Diagram

```
┌───────────────────────────────────────────────────────────────┐
│ 1. USER QUERY                                                 │
│    "Check status of core-switch-nyc-01"                       │
└────────────────────┬──────────────────────────────────────────┘
                     ↓
┌───────────────────────────────────────────────────────────────┐
│ 2. MAPPING SERVICE: Anonymize Query                           │
│    Lookup: "core-switch-nyc-01" → "device-7a3f2b"            │
│    (Uses same mappings Greenmask created!)                    │
│                                                                │
│    Anonymized: "Check status of device-7a3f2b"              │
└────────────────────┬──────────────────────────────────────────┘
                     ↓
┌───────────────────────────────────────────────────────────────┐
│ 3. CLAUDE RECEIVES                                            │
│    "Check status of device-7a3f2b"                           │
│                                                                │
│    Claude decides to use MCP tool:                            │
│    netbox_get_objects(                                        │
│        object_type="dcim.device",                             │
│        filters={"name": "device-7a3f2b"}                     │
│    )                                                          │
└────────────────────┬──────────────────────────────────────────┘
                     ↓
┌───────────────────────────────────────────────────────────────┐
│ 4. MCP SERVER QUERIES ANONYMIZED DATABASE                     │
│    SQL: SELECT * FROM dcim_device WHERE name='device-7a3f2b' │
│                                                                │
│    Database has:                                              │
│    {id: 147, name: "device-7a3f2b", status: "active"}       │
│                                                                │
│    ✅ MATCH! Returns data to Claude                           │
└────────────────────┬──────────────────────────────────────────┘
                     ↓
┌───────────────────────────────────────────────────────────────┐
│ 5. CLAUDE PROCESSES                                           │
│    Receives: {name: "device-7a3f2b", status: "active"}       │
│                                                                │
│    Generates response:                                        │
│    "Device device-7a3f2b is active"                          │
└────────────────────┬──────────────────────────────────────────┘
                     ↓
┌───────────────────────────────────────────────────────────────┐
│ 6. MAPPING SERVICE: De-anonymize Response                     │
│    Reverse lookup: "device-7a3f2b" → "core-switch-nyc-01"   │
│                                                                │
│    De-anonymized: "Device core-switch-nyc-01 is active"     │
└────────────────────┬──────────────────────────────────────────┘
                     ↓
┌───────────────────────────────────────────────────────────────┐
│ 7. USER SEES                                                  │
│    "Device core-switch-nyc-01 is active"                     │
└───────────────────────────────────────────────────────────────┘
```

---

### Key Alignment Principles

#### Principle 1: Deterministic Hashing
Greenmask uses **deterministic hashing** with a seed:
```
hash("core-switch-nyc-01" + "secret-seed") → "7a3f2b"
```

This means:
- ✅ Same input always produces same output
- ✅ Greenmask anonymizes to "device-7a3f2b" today
- ✅ Greenmask anonymizes to "device-7a3f2b" tomorrow
- ✅ Mapping service can replicate this transformation

#### Principle 2: Shared Mapping Store
Both anonymization processes use the **same mapping database**:
- Greenmask writes mappings after database anonymization
- Mapping service reads those mappings for query anonymization
- No mismatch possible!

#### Principle 3: Session Isolation
Each user session has its own mapping scope:
```python
session_mappings = {
    "session_abc123": {
        "core-switch-nyc-01": "device-7a3f2b",
        "NYC-DC1": "site-9x4k1"
    }
}
```

But Greenmask mappings are **global** and loaded into all sessions.

---

### What If There's a Mismatch?

**Scenario:** User asks about a device that was added AFTER the last Greenmask anonymization.

**Problem:**
- User: "Check status of core-switch-nyc-99"
- Greenmask hasn't anonymized this yet (needs manual re-run)
- Mapping service has no mapping for "core-switch-nyc-99"

**Solution Options:**

**Option A: Generate On-the-Fly Mapping**
```python
if not found_in_mapping:
    # Generate consistent anonymization using same algorithm
    anonymized = deterministic_hash("core-switch-nyc-99", seed)
    # But warn: this device won't exist in anonymized DB yet!
```

**Option B: Return Error**
```python
if not found_in_mapping:
    return "Device core-switch-nyc-99 not found (anonymized DB out of sync)"
```

**Option C: Real-Time Greenmask (Advanced)**
Trigger Greenmask incremental update for new entities.

---

## Summary

### Question 1: How Greenmask Copies Database
✅ Greenmask reads production DB (read-only), applies transformations, writes to separate anonymized DB
✅ Uses deterministic hashing for consistency
✅ Preserves structure (IDs, relationships, metadata)
✅ Saves mappings for query alignment

### Question 2: How MCP Tools Query Greenmask DB
✅ Change `NETBOX_URL` in MCP config to point to anonymized instance
✅ Run two Netbox instances (production + anonymized)
✅ MCP server code doesn't change - just different URL
✅ Claude queries anonymized data via MCP

### Question 3: How Query Anonymization Aligns
✅ Mapping service loads Greenmask's mappings
✅ User query anonymized using SAME mappings as database
✅ Claude queries using anonymized names that exist in DB
✅ Response de-anonymized before showing to user
✅ Deterministic hashing ensures consistency

---

**The magic:** Same seed + same algorithm = guaranteed alignment between query anonymization and database anonymization!
