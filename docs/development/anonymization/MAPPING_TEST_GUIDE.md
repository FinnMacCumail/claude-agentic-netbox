# Mapping Implementation Test Guide

**Date**: 2026-03-30
**Status**: ✅ Implementation Complete - Ready for Testing

---

## Implementation Summary

### ✅ Phase 1: Mapping Generation (COMPLETE)
- **Generated**: 1,816 total mappings
- **Tables Mapped**: 8 tables (sites, devices, interfaces, VLANs, tenants, providers, circuits)
- **File Location**: `backend/anonymization/mappings/mappings_latest.json` (80KB)
- **Mapping Breakdown**:
  - dcim_site.name: 24 mappings
  - dcim_site.slug: 24 mappings
  - dcim_device.name: 50 mappings
  - dcim_interface.name: 1,586 mappings
  - ipam_vlan.name: 63 mappings
  - tenancy_tenant.name: 11 mappings
  - tenancy_tenant.slug: 11 mappings
  - circuits_provider.name: 9 mappings
  - circuits_provider.slug: 9 mappings
  - circuits_circuit.cid: 29 mappings

### ✅ Phase 2: Backend Integration (COMPLETE)
- **MappingService**: Loaded and ready (verified in code)
- **QueryAnonymizer**: Configured with device/site patterns
- **ResponseRestorer**: Configured for SHA256/MD5 hash restoration
- **Configuration**: `ANONYMIZATION_ENABLED=true` in `.env.anonymization`

### ✅ Phase 3: Services Running (COMPLETE)
- **Backend**: Running on port 8003 (PID: 1393930)
- **Frontend**: Running on port 3002
- **Anonymized Netbox**: Running on port 8001
- **Health Check**: ✅ Passed

---

## How the Translation Works

### Query Flow

```
User: "Show devices at Albany"
   ↓ [1. Pattern Matching]
Frontend sends query to backend
   ↓ [2. Query Anonymization]
Backend finds "Albany" in mappings
Replaces with: "5c64bfcc407eab7e470ed8d4319b7f301aae1195d487c0f4fb28b520fea24434"
   ↓ [3. Query Anonymized Netbox]
MCP queries anonymized Netbox with hash
   ↓ [4. Get Anonymized Results]
Netbox returns devices with hashed names like:
- "0a25438abc45eb6e97c5d973491fc23446af57cac7524097a702c50818009a94"
   ↓ [5. Send to Claude API]
Claude receives ONLY hashed values (PII protected ✅)
   ↓ [6. Claude Processes]
Claude generates response using hashes
   ↓ [7. Response Restoration]
Backend finds hashes in response
Replaces with real names:
- "0a25438abc45eb..." → "dmi01-albany-rtr01"
- "5c64bfcc407eab..." → "DM-Albany"
   ↓ [8. Return to User]
User sees: "Found device dmi01-albany-rtr01 at DM-Albany"
```

**KEY POINT**: Claude never sees "Albany" or "dmi01-albany-rtr01" - only hashes!

---

## Testing Instructions

### Test 1: Basic Site Query

**Query**: `Show devices at Albany`

**Expected Behavior**:
1. Backend log shows: `✅ Anonymized 'Albany' → '5c64bfcc407eab...'`
2. Backend log shows: `✅ Restored '5c64bfcc407eab...' → 'DM-Albany'`
3. Backend log shows: `✅ Restored '0a25438abc45eb...' → 'dmi01-albany-rtr01'`
4. User sees real names: "DM-Albany", "dmi01-albany-rtr01", etc.

**To Verify**:
```bash
# Watch backend logs while testing
tail -f /tmp/backend_anon.log | grep -E "Anonymized|Restored"
```

---

### Test 2: Specific Device Query

**Query**: `Show status of dmi01-albany-rtr01`

**Expected Behavior**:
1. Backend log shows: `✅ Anonymized 'dmi01-albany-rtr01' → '0a25438abc45eb...'`
2. Claude queries with hash
3. Backend log shows: `✅ Restored '0a25438abc45eb...' → 'dmi01-albany-rtr01'`
4. User sees device details with real name

---

### Test 3: Multiple Entities

**Query**: `Compare devices at Albany and Akron`

**Expected Behavior**:
1. Both site names anonymized: "Albany" → hash1, "Akron" → hash2
2. All device names in both sites anonymized
3. Response contains multiple hashes
4. All hashes restored to real names
5. User sees comparative analysis with real names

---

### Test 4: Case Insensitive Matching

**Query**: `show devices at ALBANY` (uppercase)

**Expected Behavior**:
1. Backend finds "ALBANY" matches "DM-Albany" (case-insensitive)
2. Uses correct casing from database: "DM-Albany"
3. Anonymizes with proper hash
4. Response correctly restored

---

### Test 5: Partial Matching

**Query**: `Find routers in Albany`

**Expected Behavior**:
1. "Albany" matches "DM-Albany" via partial/casual matching
2. "routers" is device type filter (not anonymized)
3. Response shows routers at DM-Albany with real names

---

### Test 6: Verify PII Protection

**This is the critical test!**

**Query**: `List all devices at DM-Akron site`

**Check Backend Logs**:
```bash
tail -100 /tmp/backend_anon.log | grep -E "query_to_send|text_to_send|Anonymized|Restored"
```

**What to Look For**:
- ✅ Log shows original query: "List all devices at DM-Akron site"
- ✅ Log shows anonymized query with hash instead of "DM-Akron"
- ✅ Log shows Claude's response contains hashes
- ✅ Log shows restoration replacing hashes with real names
- ❌ Log should NEVER show real names being sent to Claude API

---

## How to Check Logs

### Real-Time Monitoring

Open a terminal and run:
```bash
tail -f /tmp/backend_anon.log | grep --color=always -E "Anonymized|Restored|query_to_send"
```

Then send queries in the GUI at http://localhost:3002

### Check Last Query

```bash
tail -100 /tmp/backend_anon.log | grep -A 5 -B 5 "Anonymized"
```

---

## Troubleshooting

### Issue: No Anonymization Happening

**Symptoms**: Logs don't show "Anonymized" messages

**Solution**:
1. Check backend is using .env.anonymization:
```bash
grep "anonymization_enabled=True" /tmp/backend_anon.log
```

2. Check mappings file exists:
```bash
ls -lh backend/anonymization/mappings/mappings_latest.json
```

3. Restart backend:
```bash
./start_anonymized_backend.sh
```

---

### Issue: Hashes Appearing in Response

**Symptoms**: User sees hashes like "0a25438abc45eb..." instead of real names

**Cause**: Response restoration not working

**Solution**:
1. Check backend logs for restoration errors
2. Verify hash is in mappings:
```bash
python3 << 'EOF'
import json
with open('backend/anonymization/mappings/mappings_latest.json') as f:
    data = json.load(f)
hash_to_find = "0a25438abc45eb6e97c5d973491fc23446af57cac7524097a702c50818009a94"
for key in data['reverse']:
    if hash_to_find in data['reverse'][key]:
        print(f"Found in {key}: {data['reverse'][key][hash_to_find]}")
EOF
```

---

### Issue: Query Finds No Results

**Symptoms**: "No devices found at Albany"

**Cause**: Query anonymization may have failed, or mapping doesn't exist

**Solution**:
1. Check backend logs for "No mapping found" warnings
2. Try exact database name instead: "DM-Albany"
3. Verify mapping exists:
```bash
python3 << 'EOF'
import json
with open('backend/anonymization/mappings/mappings_latest.json') as f:
    data = json.load(f)
print("Site names in mappings:")
for original in data['forward']['dcim_site.name']:
    print(f"  - {original}")
EOF
```

---

## Success Criteria

### ✅ Functional Tests
- [ ] Test 1: Basic site query returns real names
- [ ] Test 2: Specific device query works
- [ ] Test 3: Multiple entities handled correctly
- [ ] Test 4: Case-insensitive matching works
- [ ] Test 5: Partial matching works

### ✅ Security Tests
- [ ] Test 6: Backend logs confirm PII not sent to Claude
- [ ] Backend logs show anonymization happening
- [ ] Backend logs show restoration happening
- [ ] User never sees hashes in responses

### ✅ Performance Tests
- [ ] Query anonymization adds < 50ms latency
- [ ] Response restoration adds < 50ms latency
- [ ] Total user experience feels responsive

---

## Expected Log Output Examples

### Successful Query Anonymization
```
2026-03-30 20:45:12,345 - backend.anonymization.query_anonymizer - INFO - ✅ Anonymized 'Albany' → '5c64bfcc407eab...'
2026-03-30 20:45:12,346 - backend.agent - INFO - Query anonymized: 1 entities replaced
```

### Successful Response Restoration
```
2026-03-30 20:45:15,678 - backend.anonymization.response_restorer - INFO - ✅ Restored '5c64bfcc407eab...' → 'DM-Albany'
2026-03-30 20:45:15,679 - backend.anonymization.response_restorer - INFO - ✅ Restored '0a25438abc45eb...' → 'dmi01-albany-rtr01'
2026-03-30 20:45:15,680 - backend.agent - INFO - Response restored: 2 hashes replaced
```

### Warning Example (Expected Sometimes)
```
2026-03-30 20:45:18,123 - backend.anonymization.query_anonymizer - WARNING - ⚠️ No mapping found for 'router' (type: device)
```
This is normal - "router" is a device type, not a device name, so it doesn't need anonymization.

---

## Next Steps After Testing

1. **If Tests Pass**:
   - Document any edge cases discovered
   - Consider generating mappings on a schedule (cron job)
   - Deploy to production use

2. **If Tests Fail**:
   - Save backend logs: `cp /tmp/backend_anon.log /tmp/backend_anon_failed.log`
   - Note which test failed and error messages
   - Check MAPPING_IMPLEMENTATION_PLAN.md for troubleshooting

3. **For Production Deployment**:
   - Set up automated mapping regeneration
   - Add monitoring for mapping staleness
   - Create backup/restore procedures for mappings
   - Document operational procedures

---

## Quick Test Command

Run this to do a quick end-to-end test from command line:

```bash
curl -X POST http://localhost:8003/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show devices at Albany site"}' \
  | python3 -m json.tool
```

Watch logs in another terminal:
```bash
tail -f /tmp/backend_anon.log | grep -E "Anonymized|Restored"
```

---

**Ready to test!** Open http://localhost:3002 and try the test queries above.
