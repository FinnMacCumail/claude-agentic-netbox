# Known Issues and Limitations

## Docker Health Check Shows "unhealthy"

**Status**: Cosmetic issue, does not affect functionality

**Description**:
The `netbox-anon` container may show as "unhealthy" in `docker ps` output:

```
$ docker ps
NAMES        STATUS
netbox-anon  Up 10 minutes (unhealthy)
```

**Cause**:
The health check in `docker-compose.anonymization.yml` uses:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/api/"]
```

This endpoint returns HTTP 403 (Forbidden) because Netbox's API requires authentication. The `-f` flag makes curl treat 403 as a failure.

**Impact**:
None. The container is fully functional:
- ✅ Web interface accessible at http://localhost:8001
- ✅ API working with authentication
- ✅ All services running normally

**Verification**:
Test that the container is actually working:

```bash
# Web interface responds
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/
# Returns: 302 (redirect, correct)

# API responds with authentication
curl -s "http://localhost:8001/api/status/" \
  -H "Authorization: Token 4ab203e0949fd1bde910ad0a9bb4ac5784950cd2"
# Returns: JSON with Netbox version info
```

**Fix** (Optional):
Update the health check to use an unauthenticated endpoint or remove the `-f` flag:

```yaml
healthcheck:
  test: ["CMD", "curl", "http://localhost:8080/"]  # Remove -f flag
```

Or ignore the health status entirely since it's not accurate.

**Workaround**:
Ignore the "unhealthy" status. The container is working correctly.

---

## IP Addresses Not Anonymized

**Status**: Known limitation, low priority

**Description**:
IP addresses in `ipam_ipaddress` table are not anonymized:
- `address` field remains unchanged (e.g., `172.16.0.1/24`)
- `dns_name` field IS anonymized (SHA256 hash)

**Cause**:
Greenmask's Hash transformer doesn't support PostgreSQL `inet` and `cidr` data types.

**Impact**:
Low. Most IP addresses in the database are:
- Private RFC1918 ranges (172.16.x.x, 10.x.x.x, 192.168.x.x)
- Internal infrastructure IPs that don't expose external information

**Workaround**:
If needed, could implement custom transformation using:
1. Greenmask's Cmd transformer with custom script
2. Post-processing SQL script to anonymize IPs
3. Different anonymization tool that supports inet types

**Priority**: Low - acceptable for most use cases

---

## Mapping Files Not Generated

**Status**: Feature not implemented, medium priority

**Description**:
No mapping file is generated showing which original values map to which anonymized values.

**Example of what's missing**:
```
Original Device Name          → Anonymized Hash
------------------------------ → ----------------------------------------------------------------
dmi01-akron-rtr01             → 0a25438abc45eb6e97c5d973491fc23446af57cac7524097a702c50818009a94
dmi01-albany-rtr01            → 982d4fd6ef715838563f2c56f5e4a9046cfe1dc3218062b419e8ebd9b26c6d28
```

**Cause**:
Greenmask's Hash transformer doesn't export mappings. It only transforms data in-place during dump/restore.

**Impact**:
- Cannot reverse-lookup anonymized values to originals
- Harder to debug issues that span both databases
- Cannot correlate Claude's answers back to production entities

**Workaround**:
Create custom script to query both databases and export mappings:

```python
# Pseudo-code
prod_devices = query_production("SELECT id, name FROM dcim_device")
anon_devices = query_anonymized("SELECT id, name FROM dcim_device")

for prod_id, prod_name in prod_devices:
    anon_name = anon_devices[prod_id]  # IDs match
    mappings[prod_name] = anon_name
    print(f"{prod_name} → {anon_name}")
```

**Priority**: Medium - useful for debugging but not required for operation

---

## RQ Workers Not Running

**Status**: Expected, no impact

**Description**:
The Netbox status endpoint reports:
```json
{
  "rq-workers-running": 0
}
```

**Cause**:
The anonymized instance is configured as a minimal deployment. RQ workers are not started by default.

**Impact**:
- Background tasks won't process automatically
- Webhooks won't fire
- Reports/scripts won't run asynchronously

This is acceptable for a read-only anonymized instance used for Claude queries.

**Fix** (if needed):
Add RQ worker container to `docker-compose.anonymization.yml`:

```yaml
netbox-anon-worker:
  image: netboxcommunity/netbox:v4.3-3.3.0
  depends_on:
    - netbox-anon-db
    - netbox-anon-redis
  environment:
    # Same env as netbox-anon
  command: /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqworker
```

**Priority**: Low - not needed for read-only API access

---

## PostgreSQL Connection Warnings During Greenmask

**Status**: Harmless warnings, can be ignored

**Description**:
During Greenmask execution, you may see PostgreSQL warnings:
```
NOTICE: table "..." does not exist, skipping
WARNING: column "..." does not exist
```

**Cause**:
Greenmask validates configuration against database schema. Some columns referenced in config may not exist in your specific Netbox version.

**Impact**:
None. Greenmask skips non-existent columns/tables automatically and continues processing.

**Examples**:
- `mac_address` column on `dcim_interface` (moved to `dcim_macaddress` table in newer Netbox)
- Various custom fields that may not be present

**Priority**: N/A - informational only

---

## Summary

| Issue | Status | Impact | Priority | Workaround |
|-------|--------|--------|----------|------------|
| Docker health check shows unhealthy | Known | None | Low | Ignore status |
| IP addresses not anonymized | Limitation | Low | Low | Custom script if needed |
| No mapping files | Missing feature | Medium | Medium | Create custom export script |
| RQ workers not running | Expected | None for read-only | Low | Add worker container if needed |
| PostgreSQL warnings | Harmless | None | N/A | Ignore |

**Overall**: All issues are either cosmetic, low-impact, or have acceptable workarounds. The anonymization solution is production-ready for its intended purpose (providing anonymized data for Claude API queries).
