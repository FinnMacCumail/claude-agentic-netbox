# Anonymization Feature - Development Strategy

**Date:** 2026-03-24
**Purpose:** Recommended approach for developing anonymization feature

---

## Recommended Approach: Git Branch + Docker Compose + Feature Flag

**Best Solution:** Combine all three techniques for maximum flexibility

### Why This Approach?

✅ **Git Branch**: Clean version control, easy code review, safe experimentation
✅ **Docker Compose**: Run prod AND anon versions simultaneously on different ports
✅ **Feature Flag**: Toggle anonymization on/off with environment variable

---

## Step-by-Step Implementation

### Phase 1: Create Feature Branch

```bash
# From master branch
git checkout -b feature/anonymization

# Create branch tracking
git push -u origin feature/anonymization
```

**Benefits:**
- ✅ Master branch stays clean
- ✅ Can merge back when ready
- ✅ Easy code review
- ✅ Rollback if needed

---

### Phase 2: Add Feature Flag to Configuration

**Update `backend/config.py`:**

```python
# backend/config.py

from pydantic_settings import BaseSettings

class Config(BaseSettings):
    # ... existing config fields ...

    # Anonymization Settings
    anonymization_enabled: bool = False  # Feature flag
    anonymization_mode: str = "greenmask"  # or "presidio" (future)

    # Netbox URLs - Support both prod and anonymized
    netbox_url: str  # Default (can point to either)
    netbox_token: str

    # Optional: Separate anon config (if anonymization enabled)
    netbox_anon_url: str | None = None
    netbox_anon_token: str | None = None

    # Mapping Service (if anonymization enabled)
    mapping_service_url: str = "http://localhost:6379"  # Redis
    mapping_db_url: str = "postgresql://localhost:5434/mappings"

    anonymization_seed: str | None = None

    class Config:
        env_file = ".env"
```

---

### Phase 3: Create Docker Compose for Dual Setup

**Create `docker-compose.anonymization.yml`:**

```yaml
version: '3.8'

services:
  #############################################################################
  # PRODUCTION NETBOX (Existing)
  #############################################################################

  netbox-prod-db:
    image: postgres:15
    container_name: netbox-db-prod
    environment:
      POSTGRES_DB: netbox
      POSTGRES_USER: netbox
      POSTGRES_PASSWORD: ${PROD_DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - netbox_prod_data:/var/lib/postgresql/data
    networks:
      - netbox-prod

  netbox-prod:
    image: netboxcommunity/netbox:latest
    container_name: netbox-app-prod
    environment:
      DB_HOST: netbox-prod-db
      DB_NAME: netbox
      DB_USER: netbox
      DB_PASSWORD: ${PROD_DB_PASSWORD}
      SECRET_KEY: ${NETBOX_SECRET_KEY}
      SUPERUSER_API_TOKEN: ${NETBOX_PROD_TOKEN}
    ports:
      - "8000:8080"  # Production on port 8000
    depends_on:
      - netbox-prod-db
    networks:
      - netbox-prod

  #############################################################################
  # ANONYMIZED NETBOX (New)
  #############################################################################

  netbox-anon-db:
    image: postgres:15
    container_name: netbox-db-anon
    environment:
      POSTGRES_DB: netbox_anonymized
      POSTGRES_USER: netbox
      POSTGRES_PASSWORD: ${ANON_DB_PASSWORD}
    ports:
      - "5433:5432"  # Different external port
    volumes:
      - netbox_anon_data:/var/lib/postgresql/data
    networks:
      - netbox-anon

  netbox-anon:
    image: netboxcommunity/netbox:latest
    container_name: netbox-app-anon
    environment:
      DB_HOST: netbox-anon-db
      DB_NAME: netbox_anonymized
      DB_USER: netbox
      DB_PASSWORD: ${ANON_DB_PASSWORD}
      SECRET_KEY: ${NETBOX_SECRET_KEY}
      SUPERUSER_API_TOKEN: ${NETBOX_ANON_TOKEN}
    ports:
      - "8001:8080"  # Anonymized on port 8001
    depends_on:
      - netbox-anon-db
    networks:
      - netbox-anon

  #############################################################################
  # GREENMASK (Trigger manually as needed)
  #############################################################################

  greenmask:
    image: greenmask/greenmask:latest
    container_name: greenmask
    volumes:
      - ./docs/development/anonymization/greenmask-config-complete.yml:/config/greenmask.yml
      - ./greenmask-mappings:/mappings
      - ./greenmask-logs:/logs
    environment:
      PROD_DB_PASSWORD: ${PROD_DB_PASSWORD}
      ANON_DB_PASSWORD: ${ANON_DB_PASSWORD}
      ANONYMIZATION_SEED: ${ANONYMIZATION_SEED}
    networks:
      - netbox-prod  # Access to production (read-only)
      - netbox-anon  # Access to anonymized (write)
    # Keep running, trigger anonymization manually when needed
    command: ["tail", "-f", "/dev/null"]

  #############################################################################
  # MAPPING SERVICE (For query/response translation)
  #############################################################################

  redis:
    image: redis:7-alpine
    container_name: mapping-cache
    ports:
      - "6379:6379"
    networks:
      - mapping

  mapping-db:
    image: postgres:15
    container_name: mapping-db
    environment:
      POSTGRES_DB: mappings
      POSTGRES_USER: mapper
      POSTGRES_PASSWORD: ${MAPPING_DB_PASSWORD}
    ports:
      - "5434:5432"
    volumes:
      - mapping_data:/var/lib/postgresql/data
    networks:
      - mapping

  #############################################################################
  # YOUR APPLICATION (Backend)
  #############################################################################

  # Production Instance (No Anonymization)
  backend-prod:
    build: .
    container_name: netbox-chatbox-backend-prod
    environment:
      NETBOX_URL: http://netbox-prod:8080
      NETBOX_TOKEN: ${NETBOX_PROD_TOKEN}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      ANONYMIZATION_ENABLED: "false"
      LOG_LEVEL: DEBUG
    ports:
      - "8002:8000"  # Backend prod on 8002
    networks:
      - netbox-prod
    command: ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]

  # Anonymized Instance (With Anonymization)
  backend-anon:
    build: .
    container_name: netbox-chatbox-backend-anon
    environment:
      NETBOX_URL: http://netbox-anon:8080
      NETBOX_TOKEN: ${NETBOX_ANON_TOKEN}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      ANONYMIZATION_ENABLED: "true"
      MAPPING_SERVICE_URL: redis://redis:6379
      MAPPING_DB_URL: postgresql://mapper:${MAPPING_DB_PASSWORD}@mapping-db:5432/mappings
      ANONYMIZATION_SEED: ${ANONYMIZATION_SEED}
      LOG_LEVEL: DEBUG
    ports:
      - "8003:8000"  # Backend anon on 8003
    depends_on:
      - redis
      - mapping-db
    networks:
      - netbox-anon
      - mapping
    command: ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]

volumes:
  netbox_prod_data:
  netbox_anon_data:
  mapping_data:

networks:
  netbox-prod:
  netbox-anon:
  mapping:
```

---

### Phase 4: Environment Configuration

**Create `.env.anonymization`:**

```bash
# Copy from .env and add anonymization-specific settings
cp .env .env.anonymization

# Edit .env.anonymization
nano .env.anonymization
```

**.env.anonymization contents:**

```bash
#############################################################################
# ANTHROPIC API
#############################################################################
ANTHROPIC_API_KEY=your-key-here

#############################################################################
# PRODUCTION NETBOX (Original Data)
#############################################################################
NETBOX_PROD_URL=http://localhost:8000
NETBOX_PROD_TOKEN=your-prod-token
PROD_DB_PASSWORD=prod_password

#############################################################################
# ANONYMIZED NETBOX (Greenmask Data)
#############################################################################
NETBOX_ANON_URL=http://localhost:8001
NETBOX_ANON_TOKEN=your-anon-token
ANON_DB_PASSWORD=anon_password

#############################################################################
# ANONYMIZATION SETTINGS
#############################################################################
ANONYMIZATION_ENABLED=true
ANONYMIZATION_MODE=greenmask
ANONYMIZATION_SEED=super-secret-seed-change-this-12345

#############################################################################
# MAPPING SERVICE
#############################################################################
MAPPING_DB_PASSWORD=mapping_password

#############################################################################
# OTHER
#############################################################################
NETBOX_SECRET_KEY=your-secret-key
LOG_LEVEL=DEBUG
```

---

### Phase 5: Start Both Instances

```bash
# Start all services
docker-compose -f docker-compose.anonymization.yml up -d

# Verify all running
docker-compose -f docker-compose.anonymization.yml ps
```

**You'll have:**

| Service | Port | Purpose |
|---------|------|---------|
| Production Netbox | 8000 | Original data |
| Anonymized Netbox | 8001 | Greenmask anonymized data |
| Prod Backend | 8002 | Uses prod Netbox (no anonymization) |
| Anon Backend | 8003 | Uses anon Netbox (with query/response mapping) |
| Redis | 6379 | Mapping cache |
| Mapping DB | 5434 | Mapping storage |

---

### Phase 6: Run Greenmask Manually (for testing)

```bash
# Trigger Greenmask anonymization
docker exec greenmask greenmask \
  --config /config/greenmask.yml \
  dump-restore \
  --save-mappings /mappings/mappings_$(date +%Y%m%d).json

# Import mappings to mapping service
# (You'll create this script)
python scripts/import_greenmask_mappings.py \
  /path/to/greenmask-mappings/mappings_20260324.json
```

---

### Phase 7: Side-by-Side Testing

**Terminal 1: Test Production (No Anonymization)**
```bash
# Query production backend
curl http://localhost:8002/health

# Use frontend pointing to prod backend
cd frontend
NUXT_PUBLIC_API_URL=http://localhost:8002 npm run dev
# Frontend on http://localhost:3000
```

**Terminal 2: Test Anonymized (With Anonymization)**
```bash
# Query anonymized backend
curl http://localhost:8003/health

# Use different frontend instance pointing to anon backend
cd frontend
NUXT_PUBLIC_API_URL=http://localhost:8003 PORT=3001 npm run dev
# Frontend on http://localhost:3001
```

**Now you can compare:**
- Browser 1: `http://localhost:3000` (Production - real data)
- Browser 2: `http://localhost:3001` (Anonymized - fake data)

**Same query to both:**
```
Query: "List all sites"

Production response:
- NYC-DC1
- LONDON-DC2
- TOKYO-DC3

Anonymized response:
- site-9x4k1
- site-2m7n3
- site-7a8b4
```

---

## Alternative: Single Branch with Toggle

If Docker is too complex, use a simpler feature flag approach:

### Option 2: Feature Flag Only

**backend/config.py:**
```python
anonymization_enabled: bool = False
```

**backend/api.py:**
```python
from backend.config import Config

config = Config()

if config.anonymization_enabled:
    # Use anonymized Netbox + mapping service
    netbox_url = config.netbox_anon_url
else:
    # Use production Netbox
    netbox_url = config.netbox_url
```

**Switch between modes:**
```bash
# Production mode
ANONYMIZATION_ENABLED=false ./start_server.sh

# Anonymized mode
ANONYMIZATION_ENABLED=true ./start_server.sh
```

**Limitation:** Can't run both simultaneously (must restart to switch)

---

## Comparison Table

| Approach | Pros | Cons | Recommended? |
|----------|------|------|--------------|
| **Separate Folder/Copy** | Simple, independent | Code duplication, merge hell | ❌ No |
| **Git Branch Only** | Clean git history | Can't run both together | ⚠️ OK for small tests |
| **Git Branch + Docker** | Best of both worlds | Complex setup | ✅ **YES** |
| **Feature Flag Only** | Simple toggle | Must restart to switch | ⚠️ OK if no Docker |

---

## Recommended: Git Branch + Docker Compose

**Why:**
1. ✅ Clean git workflow (feature branch)
2. ✅ Run both instances simultaneously (Docker)
3. ✅ Easy comparison (different ports)
4. ✅ Production-like environment (Docker)
5. ✅ Easy to merge back to master when ready
6. ✅ Can show both versions to stakeholders

**Setup time:** ~2-3 hours (Docker Compose setup)
**Long-term benefit:** Massive (clean dev workflow + easy testing)

---

## File Structure on Feature Branch

```
claude-agentic-sdk/
├── backend/
│   ├── anonymization/         # NEW: Anonymization logic
│   │   ├── __init__.py
│   │   ├── mapping_service.py
│   │   └── greenmask_import.py
│   ├── agent.py               # MODIFIED: Add anonymization
│   ├── api.py                 # MODIFIED: Add mapping routes
│   └── config.py              # MODIFIED: Add anon settings
├── docs/development/anonymization/  # NEW: All your docs
│   ├── GREENMASK_EXPLAINED.md
│   ├── greenmask-config-complete.yml
│   └── ...
├── docker-compose.anonymization.yml  # NEW: Dual setup
├── scripts/
│   └── import_greenmask_mappings.py  # NEW: Import script
├── .env.anonymization         # NEW: Anon-specific env
├── .env                       # EXISTING: Prod env
└── README.md                  # MODIFIED: Add anon section
```

---

## Git Workflow

```bash
# 1. Create feature branch
git checkout -b feature/anonymization

# 2. Develop on branch
# ... make changes ...

# 3. Commit frequently
git add .
git commit -m "feat: add Greenmask config"
git push

# 4. When ready, create PR
gh pr create --title "Add anonymization support" --body "..."

# 5. Review, test, merge to master
git checkout master
git merge feature/anonymization

# 6. Delete feature branch
git branch -d feature/anonymization
```

---

## My Recommendation

**Use: Git Branch + Docker Compose + Feature Flag**

**Steps:**
1. ✅ Create `feature/anonymization` branch
2. ✅ Add feature flag to `backend/config.py`
3. ✅ Create `docker-compose.anonymization.yml`
4. ✅ Create `.env.anonymization`
5. ✅ Develop anonymization code on branch
6. ✅ Test both instances side-by-side using Docker
7. ✅ Merge to master when ready

**Benefits:**
- Clean git history
- Can run both versions simultaneously
- Easy stakeholder demos (show prod vs anon side-by-side)
- No code duplication
- Production-like testing environment
- Easy to merge back

**Time Investment:**
- Initial setup: 2-3 hours
- Long-term savings: Huge (clean workflow, easy testing)

---

## Next Steps

1. **Create feature branch**:
   ```bash
   git checkout -b feature/anonymization
   ```

2. **Copy Docker Compose config** from this document

3. **Create `.env.anonymization`**

4. **Start development**!

Would you like me to help set up the Docker Compose configuration or the feature flag implementation?
