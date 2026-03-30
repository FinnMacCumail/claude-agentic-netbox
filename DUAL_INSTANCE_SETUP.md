# Running Production and Anonymized Instances Side-by-Side

This guide explains how to run both the production (non-anonymized) and anonymized instances simultaneously for comparison testing.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    PRODUCTION INSTANCE                            │
├──────────────────────────────────────────────────────────────────┤
│ Netbox:   http://localhost:8000  (Real data)                    │
│ Backend:  http://localhost:8002  (Non-anonymized)               │
│ Frontend: http://localhost:3001  (Shows real data)              │
│ Config:   .env.production                                        │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    ANONYMIZED INSTANCE                            │
├──────────────────────────────────────────────────────────────────┤
│ Netbox:   http://localhost:8001  (Anonymized data)              │
│ Backend:  http://localhost:8003  (With anonymization layer)     │
│ Frontend: http://localhost:3002  (Shows real data - restored)   │
│ Config:   .env.anonymization                                     │
└──────────────────────────────────────────────────────────────────┘

Note: Port 3000 is reserved for Grafana
```

## Prerequisites

1. **Existing Netbox** running at `http://localhost:8000`
2. **Docker** and **Docker Compose** installed
3. **Node.js** and **npm** installed
4. All configuration files created (done automatically)

## Step-by-Step Setup

### 1. Start Anonymized Netbox Instance

First, create the anonymized Netbox database:

```bash
# Start the anonymized Netbox instance
docker compose -f docker/docker-compose.anonymization.yml up -d netbox-anon

# Wait for it to be ready (watch logs)
docker compose -f docker/docker-compose.anonymization.yml logs -f netbox-anon
# Press Ctrl+C when you see "Server started successfully"
```

Verify it's running:
```bash
curl http://localhost:8001/api/
```

### 2. Run Greenmask to Create Anonymized Data

```bash
# This copies your production Netbox data and anonymizes it
docker compose -f docker/docker-compose.anonymization.yml run --rm greenmask
```

This will:
- Connect to your existing Netbox database (localhost:8000)
- Copy all data to the anonymized database
- Anonymize sensitive fields (IPs, device names, sites, etc.)
- Generate mapping files for query/response translation

### 3. Import Greenmask Mappings

```bash
# Import the mappings so the backend can translate queries/responses
python scripts/import_mappings.py docker/greenmask/mappings/mappings_latest.json
```

### 4. Start Both Backend Instances

Open **2 separate terminals**:

**Terminal 1 - Production Backend:**
```bash
./start_production_backend.sh
```
- Runs on port **8002**
- Queries **real** Netbox (port 8000)
- **No anonymization** - Claude sees real data

**Terminal 2 - Anonymized Backend:**
```bash
./start_anonymized_backend.sh
```
- Runs on port **8003**
- Queries **anonymized** Netbox (port 8001)
- **With anonymization** - Claude sees fake data, users see real data

### 5. Start Both Frontend Instances

Open **2 more terminals**:

**Terminal 3 - Production Frontend:**
```bash
./start_production_frontend.sh
```
- Runs on port **3001**
- Connects to backend on port 8002
- Access at: http://localhost:3001

**Terminal 4 - Anonymized Frontend:**
```bash
./start_anonymized_frontend.sh
```
- Runs on port **3002**
- Connects to backend on port 8003
- Access at: http://localhost:3002

## Testing Side-by-Side Comparison

Now you can compare both instances:

1. **Open two browser windows:**
   - Window 1: http://localhost:3001 (Production)
   - Window 2: http://localhost:3002 (Anonymized)

2. **Ask the same question in both:**
   ```
   "Show me the status of core-switch-nyc-01"
   ```

3. **Expected Results:**
   - **Both GUIs** show the same answer with **real device names**
   - Users cannot tell the difference
   - But behind the scenes:
     - Production: Claude sees "core-switch-nyc-01" (real data sent to API)
     - Anonymized: Claude sees "device-7a3f2b" (fake data, no PII exposed)

## Verification

### Check What Claude Sees

Enable debug logging in `.env.production` and `.env.anonymization`:
```bash
LOG_LEVEL=DEBUG
```

Then check the backend logs:

**Production Backend (Terminal 1):**
```
Query sent to Claude: "Show status of core-switch-nyc-01"
└─> REAL device name sent to Claude API ⚠️
```

**Anonymized Backend (Terminal 2):**
```
Original query: "Show status of core-switch-nyc-01"
Anonymized query: "Show status of device-7a3f2b"
└─> FAKE device name sent to Claude API ✅
Response from Claude: "device-7a3f2b is active"
Restored response: "core-switch-nyc-01 is active"
└─> User sees real name ✅
```

## Quick Reference

| Component | Production (Real) | Anonymized (Fake) |
|-----------|-------------------|-------------------|
| **Netbox** | localhost:8000 | localhost:8001 |
| **Backend** | localhost:8002 | localhost:8003 |
| **Frontend** | localhost:3001 | localhost:3002 |
| **Config** | .env.production | .env.anonymization |
| **Data to Claude** | Real (PII exposed) | Fake (PII protected) |
| **Data to User** | Real | Real (restored) |

**Other Services:**
- **Grafana**: localhost:3000 (unchanged)

## Stopping Instances

### Stop Frontends
Press `Ctrl+C` in each frontend terminal

### Stop Backends
Press `Ctrl+C` in each backend terminal

### Stop Anonymized Netbox
```bash
docker compose -f docker/docker-compose.anonymization.yml down
```

### Keep Production Netbox Running
Your original Netbox at port 8000 continues running independently.

## Troubleshooting

### Port Already in Use
If you get "Address already in use" errors:
```bash
# Find what's using the port
lsof -i :8002  # or 8003, 3001, 3002
# Kill the process or use different ports

# Note: Port 3000 is used by Grafana (do not stop)
```

### Backend Can't Connect to Netbox
```bash
# Check Netbox is running
curl http://localhost:8000/api/  # Production
curl http://localhost:8001/api/  # Anonymized

# Check Docker networks
docker network ls | grep netbox
```

### Mappings Not Found
```bash
# Re-import mappings
python scripts/import_mappings.py docker/greenmask/mappings/mappings_latest.json

# Check mappings file exists
ls -la backend/anonymization/mappings/
```

## Notes

- Production instance **does NOT require** anonymized Netbox to be running
- Anonymized instance **requires** anonymized Netbox at port 8001
- Both can run simultaneously without conflicts (different ports)
- User experience is **identical** in both - only backend behavior differs
