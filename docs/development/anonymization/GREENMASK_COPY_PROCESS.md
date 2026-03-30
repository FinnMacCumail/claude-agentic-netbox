# How Greenmask Copies Production Database to Anonymized Database

**Date:** 2026-03-24
**Topic:** Detailed explanation of Greenmask database copy/anonymization process

---

## Overview

Greenmask creates an anonymized copy of your production database through a **dump, transform, restore** process. It does NOT modify your production database - it creates a completely separate copy with anonymized data.

---

## The Copy Process (Step-by-Step)

### Method 1: Dump → Transform → Restore (Recommended)

This is the standard Greenmask workflow:

```
Production DB → [Greenmask Dump] → Transformed SQL → [PostgreSQL Restore] → Anonymized DB
```

#### Step 1: Greenmask Dumps Production Database

Greenmask connects to your **production PostgreSQL database** (read-only) and creates a SQL dump:

```bash
# Greenmask internally uses pg_dump logic
# It reads table by table from production database

Production PostgreSQL (localhost:5432/netbox)
    ↓ (Greenmask reads)

SELECT * FROM dcim_device;
+-----+--------------------+---------+--------+
| id  | name               | site_id | status |
+-----+--------------------+---------+--------+
| 147 | core-switch-nyc-01 | 12      | active |
| 148 | core-switch-nyc-02 | 12      | active |
+-----+--------------------+---------+--------+
```

#### Step 2: Greenmask Applies Transformations IN-FLIGHT

**As Greenmask reads each row**, it applies your transformation rules BEFORE writing to the dump file:

```yaml
# Your transformation config
transformations:
  - table: dcim_device
    columns:
      - name: name
        type: hash
        engine: deterministic
        seed: "${ANONYMIZATION_SEED}"
        format: "device-{{.Hash | substr 0 6}}"
```

**In-Flight Transformation:**
```
Row from Production:
  id: 147, name: "core-switch-nyc-01", site_id: 12, status: "active"
      ↓
Greenmask applies transformation:
  - Keep id: 147 (not in transformation rules)
  - Transform name: hash("core-switch-nyc-01") → "device-7a3f2b"
  - Keep site_id: 12 (not in transformation rules)
  - Keep status: "active" (not in transformation rules)
      ↓
Transformed Row Written to Dump:
  id: 147, name: "device-7a3f2b", site_id: 12, status: "active"
```

#### Step 3: Greenmask Writes to Anonymized Database

Greenmask restores the transformed data into the **anonymized PostgreSQL database**:

```bash
Anonymized PostgreSQL (localhost:5433/netbox_anonymized)
    ↑ (Greenmask writes)

INSERT INTO dcim_device VALUES (147, 'device-7a3f2b', 12, 'active');
INSERT INTO dcim_device VALUES (148, 'device-8b9m31', 12, 'active');
```

**Result - Anonymized Database:**
```sql
SELECT * FROM dcim_device;
+-----+----------------+---------+--------+
| id  | name           | site_id | status |
+-----+----------------+---------+--------+
| 147 | device-7a3f2b  | 12      | active |
| 148 | device-8b9m31  | 12      | active |
+-----+----------------+---------+--------+
```

---

## Complete Greenmask Command Flow

### Configuration File

**greenmask-config.yml:**
```yaml
# Source: Production Database (READ-ONLY)
source:
  host: localhost
  port: 5432
  database: netbox
  user: greenmask_readonly  # ← READ-ONLY user (important!)
  password: ${PROD_DB_PASSWORD}

# Destination: Anonymized Database
target:
  host: localhost
  port: 5433  # ← Different port = different database instance
  database: netbox_anonymized
  user: greenmask_writer
  password: ${ANON_DB_PASSWORD}

# Transformation rules
transformations:
  - table: dcim_device
    columns:
      - name: name
        type: hash
        engine: deterministic
        seed: "${ANONYMIZATION_SEED}"
        format: "device-{{.Hash | substr 0 6}}"

  - table: dcim_site
    columns:
      - name: name
        type: hash
        engine: deterministic
        seed: "${ANONYMIZATION_SEED}"
        format: "site-{{.Hash | substr 0 5}}"

  - table: ipam_ipaddress
    columns:
      - name: address
        type: custom
        function: anonymize_ip  # Custom function

# Schema handling
schema:
  include_tables:
    - dcim_device
    - dcim_site
    - ipam_ipaddress
    # ... all other tables

  # Tables NOT to copy (e.g., auth/session tables)
  exclude_tables:
    - django_session
    - auth_token
```

### Execution Command

```bash
#!/bin/bash
# Script: /opt/greenmask/run_anonymization.sh
# Triggered manually as needed (automated sync is future development)

# Set environment variables
export PROD_DB_PASSWORD="production_password"
export ANON_DB_PASSWORD="anonymized_password"
export ANONYMIZATION_SEED="super-secret-seed-12345"

# Run Greenmask dump and restore
greenmask \
  --config /opt/greenmask/greenmask-config.yml \
  dump-restore \
  --validate \
  --save-mappings /opt/greenmask/mappings/mappings_$(date +%Y%m%d).json
```

---

## What Happens During Execution

### Phase 1: Pre-Flight Validation (2-3 minutes)

```
[Greenmask] Connecting to source database: localhost:5432/netbox
[Greenmask] ✓ Connection successful (read-only user)
[Greenmask] Connecting to target database: localhost:5433/netbox_anonymized
[Greenmask] ✓ Connection successful (write user)

[Greenmask] Validating transformation rules...
[Greenmask] ✓ Transformation for dcim_device.name: valid
[Greenmask] ✓ Transformation for dcim_site.name: valid
[Greenmask] ✓ All transformations valid

[Greenmask] Analyzing source schema...
[Greenmask] Found 127 tables
[Greenmask] Estimated size: 2.4 GB
[Greenmask] Estimated duration: ~15 minutes
```

### Phase 2: Schema Copy (1-2 minutes)

```
[Greenmask] Copying database schema to target...
[Greenmask] Creating tables... (127 tables)
[Greenmask] Creating indexes... (384 indexes)
[Greenmask] Creating foreign key constraints... (142 constraints)
[Greenmask] ✓ Schema copy complete
```

**What this creates:**
```sql
-- Anonymized Database (netbox_anonymized)
-- Has SAME structure as production, but EMPTY tables

CREATE TABLE dcim_device (
    id integer PRIMARY KEY,
    name varchar(100),
    site_id integer REFERENCES dcim_site(id),
    status varchar(50)
);
-- ... all other tables
```

### Phase 3: Data Copy with Transformation (10-20 minutes)

This is where the actual copying happens:

```
[Greenmask] Starting data copy...

[Greenmask] Table: dcim_site (24 rows)
  ↓ Reading from source...
  ↓ Applying transformations...
  ↓ Writing to target...
[Greenmask] ✓ dcim_site: 24/24 rows (100%)
[Greenmask]   Transformed: name (24 values)
[Greenmask]   Duration: 0.3s

[Greenmask] Table: dcim_device (1,247 rows)
  ↓ Reading from source...
  ↓ Applying transformations...
  ↓ Writing to target...
[Greenmask] ✓ dcim_device: 1,247/1,247 rows (100%)
[Greenmask]   Transformed: name (1,247 values), serial (1,247 values)
[Greenmask]   Duration: 4.2s

[Greenmask] Table: ipam_ipaddress (8,456 rows)
  ↓ Reading from source...
  ↓ Applying transformations...
  ↓ Writing to target...
[Greenmask] ✓ ipam_ipaddress: 8,456/8,456 rows (100%)
[Greenmask]   Transformed: address (8,456 values), dns_name (8,456 values)
[Greenmask]   Duration: 11.7s

... (continues for all 127 tables)

[Greenmask] ✓ Data copy complete: 234,891 total rows
[Greenmask] Total duration: 14m 32s
```

**Detailed Row Processing:**

```
Production DB:
  dcim_device row 147: {id: 147, name: "core-switch-nyc-01", site_id: 12}
      ↓ (Greenmask reads)
      ↓ (Applies transformation)
  hash("super-secret-seed-12345:dcim_device.name:core-switch-nyc-01")
    → "7a3f2b9c8d..."
    → format as "device-{{.Hash | substr 0 6}}"
    → "device-7a3f2b"
      ↓ (Greenmask writes)
Anonymized DB:
  dcim_device row 147: {id: 147, name: "device-7a3f2b", site_id: 12}
```

### Phase 4: Post-Copy Operations (1-2 minutes)

```
[Greenmask] Re-enabling foreign key constraints...
[Greenmask] ✓ All constraints valid

[Greenmask] Rebuilding indexes...
[Greenmask] ✓ All indexes rebuilt

[Greenmask] Running ANALYZE on all tables...
[Greenmask] ✓ Statistics updated

[Greenmask] Exporting mappings...
[Greenmask] ✓ Mappings saved to: /opt/greenmask/mappings/mappings_20260324.json
[Greenmask]   Total mappings: 9,703 entries
```

### Phase 5: Validation (1-2 minutes)

```
[Greenmask] Running validation checks...
[Greenmask] ✓ Row counts match: 234,891 rows
[Greenmask] ✓ Foreign key integrity: all valid
[Greenmask] ✓ No PII detected in anonymized data
[Greenmask] ✓ Referential integrity: all constraints satisfied

[Greenmask] === SUMMARY ===
[Greenmask] Source DB: localhost:5432/netbox
[Greenmask] Target DB: localhost:5433/netbox_anonymized
[Greenmask] Tables processed: 127
[Greenmask] Rows copied: 234,891
[Greenmask] Values transformed: 9,703
[Greenmask] Total duration: 18m 47s
[Greenmask] Status: ✓ SUCCESS
```

---

## Database Infrastructure Setup

You need **TWO separate PostgreSQL databases**:

### Option 1: Two PostgreSQL Instances (Recommended)

**Docker Compose:**
```yaml
version: '3.8'

services:
  # Production PostgreSQL
  postgres-prod:
    image: postgres:15
    container_name: netbox-db-prod
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: netbox
      POSTGRES_USER: netbox
      POSTGRES_PASSWORD: ${PROD_DB_PASSWORD}
    volumes:
      - postgres_prod_data:/var/lib/postgresql/data
    networks:
      - netbox-prod

  # Anonymized PostgreSQL (for Claude)
  postgres-anon:
    image: postgres:15
    container_name: netbox-db-anon
    ports:
      - "5433:5432"  # ← Different external port!
    environment:
      POSTGRES_DB: netbox_anonymized
      POSTGRES_USER: netbox
      POSTGRES_PASSWORD: ${ANON_DB_PASSWORD}
    volumes:
      - postgres_anon_data:/var/lib/postgresql/data
    networks:
      - netbox-anon

  # Production Netbox Application
  netbox-prod:
    image: netboxcommunity/netbox:latest
    container_name: netbox-app-prod
    ports:
      - "8000:8080"
    environment:
      DB_HOST: postgres-prod
      DB_NAME: netbox
      DB_USER: netbox
      DB_PASSWORD: ${PROD_DB_PASSWORD}
    depends_on:
      - postgres-prod
    networks:
      - netbox-prod

  # Anonymized Netbox Application (for Claude via MCP)
  netbox-anon:
    image: netboxcommunity/netbox:latest
    container_name: netbox-app-anon
    ports:
      - "8001:8080"  # ← Different port!
    environment:
      DB_HOST: postgres-anon
      DB_NAME: netbox_anonymized
      DB_USER: netbox
      DB_PASSWORD: ${ANON_DB_PASSWORD}
    depends_on:
      - postgres-anon
    networks:
      - netbox-anon

  # Greenmask (trigger manually as needed)
  greenmask:
    image: greenmask/greenmask:latest
    container_name: greenmask
    volumes:
      - ./greenmask-config.yml:/config/greenmask-config.yml
      - ./mappings:/mappings
      - ./scripts:/scripts
    environment:
      PROD_DB_PASSWORD: ${PROD_DB_PASSWORD}
      ANON_DB_PASSWORD: ${ANON_DB_PASSWORD}
      ANONYMIZATION_SEED: ${ANONYMIZATION_SEED}
    networks:
      - netbox-prod  # Access to production (read-only)
      - netbox-anon  # Access to anonymized (write)
    # Keep running, trigger manually when needed
    command: ["tail", "-f", "/dev/null"]

volumes:
  postgres_prod_data:
  postgres_anon_data:

networks:
  netbox-prod:
  netbox-anon:
```

### Option 2: Single PostgreSQL Instance, Two Databases

```yaml
services:
  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    # Create both databases on startup
    command: |
      postgres
      && psql -U postgres -c "CREATE DATABASE netbox;"
      && psql -U postgres -c "CREATE DATABASE netbox_anonymized;"
```

**Greenmask Config for Single Instance:**
```yaml
source:
  host: localhost
  port: 5432
  database: netbox  # ← Production database

target:
  host: localhost
  port: 5432  # ← Same server
  database: netbox_anonymized  # ← Different database name
```

---

## Greenmask Copy Methods

### Method A: Streaming Copy (Default)

Greenmask streams data directly from source to target:

```
Production DB → [Greenmask] → Anonymized DB
              (transform in memory)
```

**Pros:**
- ✅ Fast (no intermediate files)
- ✅ Low disk usage
- ✅ Transactions ensure consistency

**Cons:**
- ⚠️ Requires network connectivity between databases
- ⚠️ No backup of intermediate state

### Method B: Dump to File First

Greenmask can create an intermediate SQL file:

```
Production DB → [Greenmask Dump] → anonymized.sql → [Restore] → Anonymized DB
```

**Command:**
```bash
# Step 1: Create anonymized dump
greenmask dump \
  --config greenmask-config.yml \
  --output /tmp/anonymized_dump.sql

# Step 2: Restore to target
psql -h localhost -p 5433 -d netbox_anonymized -f /tmp/anonymized_dump.sql
```

**Pros:**
- ✅ Can review dump before restoring
- ✅ Can restore multiple times
- ✅ Portable (can move to different server)

**Cons:**
- ❌ Slower (two-step process)
- ❌ Requires disk space for dump file (~same size as DB)

---

## Mapping File Output

After Greenmask completes, it saves a mapping file:

**mappings_20260324.json:**
```json
{
  "run_id": "20260324_020000",
  "timestamp": "2026-03-24T02:00:00Z",
  "source_db": "localhost:5432/netbox",
  "target_db": "localhost:5433/netbox_anonymized",
  "transformations": {
    "dcim_device": {
      "name": {
        "core-switch-nyc-01": "device-7a3f2b",
        "core-switch-nyc-02": "device-8b9m31",
        "access-switch-lon-101": "device-x2p9q7"
      },
      "serial": {
        "FOC1234567": "SN-A7F3B2C9",
        "FOC1234568": "SN-B9M31D4E"
      }
    },
    "dcim_site": {
      "name": {
        "NYC-DC1": "site-9x4k1",
        "LONDON-DC2": "site-2m7n3"
      }
    },
    "ipam_ipaddress": {
      "address": {
        "10.1.1.1/32": "172.17.123.44/32",
        "10.1.1.2/32": "172.17.123.45/32"
      }
    }
  },
  "statistics": {
    "total_rows": 234891,
    "total_transformations": 9703,
    "duration_seconds": 1127
  }
}
```

This mapping file is then imported into your **Mapping Service** for query/response translation.

---

## Manual Trigger for Anonymization

**Script: /opt/greenmask/run_anonymization.sh:**
```bash
#!/bin/bash
set -euo pipefail

# Load environment
source /opt/greenmask/.env

# Run Greenmask
greenmask \
  --config /opt/greenmask/greenmask-config.yml \
  dump-restore \
  --validate \
  --save-mappings /opt/greenmask/mappings/mappings_$(date +%Y%m%d).json

# Import mappings into Mapping Service
python3 /opt/greenmask/import_mappings.py \
  --mappings-file /opt/greenmask/mappings/mappings_$(date +%Y%m%d).json

# Send notification
echo "Greenmask completed successfully at $(date)"
```

**To run manually:**
```bash
# Trigger anonymization when needed
docker exec greenmask /opt/greenmask/run_anonymization.sh
```

**Note:** Automated sync/scheduling is planned for future development.

---

## Summary

### How the Copy Works

1. **Greenmask connects** to production PostgreSQL (read-only)
2. **Reads table schemas** and copies to anonymized PostgreSQL
3. **Streams data row-by-row**, applying transformations in-flight
4. **Writes transformed data** to anonymized PostgreSQL
5. **Rebuilds indexes and constraints** on anonymized database
6. **Exports mapping file** showing original→anonymized mappings
7. **Validates** referential integrity and row counts

### Key Points

✅ **Two separate databases required** (can be same server, different DBs)
✅ **Greenmask streams directly** from source to target (no intermediate files by default)
✅ **Transformations applied in-memory** as data is copied
✅ **Production database NEVER modified** (read-only connection)
✅ **Triggered manually** as needed (automated sync is future development)
✅ **Mapping file exported** for query/response translation

### Infrastructure

- Production Netbox: `http://localhost:8000` → PostgreSQL `localhost:5432/netbox`
- Anonymized Netbox: `http://localhost:8001` → PostgreSQL `localhost:5433/netbox_anonymized`
- Greenmask copies: `5432/netbox` → `5433/netbox_anonymized` (triggered manually)
- MCP Server uses: `http://localhost:8001` (anonymized instance)

---

**The magic:** Greenmask reads from production, transforms on-the-fly, writes to a completely separate anonymized database that Claude queries via the anonymized Netbox application.
