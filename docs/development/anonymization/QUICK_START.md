# Quick Start Guide: Using Anonymized Netbox

This guide shows you how to quickly start using the anonymized Netbox instance with Claude.

## Current Status

✅ **Anonymized Netbox is running** at http://localhost:8001
✅ **All data has been anonymized** (names, serials, addresses, DNS)
✅ **API is operational** with token: `4ab203e0949fd1bde910ad0a9bb4ac5784950cd2`

## Quick Access

### Web Interface

1. Open your browser to: http://localhost:8001
2. Login with:
   - Username: `admin`
   - Password: `admin`

### API Access

```bash
# Test the API
curl "http://localhost:8001/api/dcim/devices/" \
  -H "Authorization: Token 4ab203e0949fd1bde910ad0a9bb4ac5784950cd2"
```

## Using with Claude (MCP Server)

### Option 1: Switch MCP Configuration

To have Claude use the anonymized instance:

```bash
# Backup your current production config
cp .mcp.json .mcp.json.production

# Switch to anonymized instance
cp .mcp.json.anonymized .mcp.json

# Restart Claude Code
```

### Option 2: Manual Configuration

Edit `.mcp.json` and change:

```json
{
  "mcpServers": {
    "netbox": {
      "env": {
        "NETBOX_URL": "http://localhost:8001",
        "NETBOX_TOKEN": "4ab203e0949fd1bde910ad0a9bb4ac5784950cd2"
      }
    }
  }
}
```

Then restart Claude Code.

## Verifying It Works

After switching to anonymized instance, test with Claude:

```
Ask Claude: "List all devices in Netbox"
```

You should see anonymized device names (64-character SHA256 hashes) instead of real names.

**Example**:
- Production: `dmi01-akron-rtr01`
- Anonymized: `0a25438abc45eb6e97c5d973491fc23446af57cac7524097a702c50818009a94`

## Switching Back to Production

To switch back to using production Netbox:

```bash
# Restore production config
cp .mcp.json.production .mcp.json

# Restart Claude Code
```

## Common Commands

### Start/Stop Anonymized Instance

```bash
# Start the anonymized Netbox
docker compose -f docker/docker-compose.anonymization.yml up -d netbox-anon

# Stop the anonymized Netbox
docker compose -f docker/docker-compose.anonymization.yml down

# View logs
docker logs netbox-anon -f
```

### Re-run Anonymization (Update Data)

If your production data changes and you want to refresh the anonymized copy:

```bash
# Run Greenmask to re-anonymize
docker compose -f docker/docker-compose.anonymization.yml run --rm greenmask

# Restart anonymized Netbox
docker compose -f docker/docker-compose.anonymization.yml restart netbox-anon
```

This takes about 5 minutes and will:
1. Dump production database with anonymization
2. Restore to anonymized database
3. Verify data integrity

## Troubleshooting

### Anonymized Instance Won't Start

```bash
# Check container status
docker ps -a | grep netbox-anon

# Check logs for errors
docker logs netbox-anon

# Restart if needed
docker compose -f docker/docker-compose.anonymization.yml restart netbox-anon
```

### API Returns "Authentication credentials were not provided"

Check that you're using the correct token:
```bash
# Token for anonymized instance
Token: 4ab203e0949fd1bde910ad0a9bb4ac5784950cd2

# Token for production instance (different!)
Token: c4af48e5b315a5baf92f7ca449ac5d664239916a
```

### Claude Still Shows Real Names

This means Claude is still connected to production. Make sure you:
1. Updated `.mcp.json` with anonymized URL and token
2. Restarted Claude Code
3. Confirmed the config change took effect

## What's Been Anonymized?

| Data Type | Status | Example |
|-----------|--------|---------|
| Device names | ✅ Anonymized | SHA256 hash |
| Site names | ✅ Anonymized | SHA256 hash |
| Serial numbers | ✅ Anonymized | MD5 hash |
| Physical addresses | ✅ Masked | "7730 S******" |
| DNS names | ✅ Anonymized | SHA256 hash |
| Tenant names | ✅ Anonymized | SHA256 hash |
| Contact emails | ✅ Randomized | random@example.com |
| IP addresses | ⚠️ Unchanged | Private ranges (low risk) |

## Next Steps

1. **Test Claude Reasoning**: Ask Claude complex questions about your network
2. **Compare Results**: Test same query on both production and anonymized
3. **Validate Functionality**: Ensure Claude can still perform all needed tasks
4. **Deploy to Production**: Once satisfied, use anonymized instance regularly

## Support

For detailed information, see:
- `docs/development/anonymization/ANONYMIZATION_VERIFICATION.md` - Full verification report
- `docs/development/anonymization/DATABASE_AUDIT_REPORT.md` - Database integrity audit
- `DUAL_INSTANCE_SETUP.md` - Original setup documentation

---

**Quick Reference**:
- Production: http://localhost:8000 (token: c4af48e5b315a5baf92f7ca449ac5d664239916a)
- Anonymized: http://localhost:8001 (token: 4ab203e0949fd1bde910ad0a9bb4ac5784950cd2)
