# Quick Reference: Switching Between Production and Anonymized Netbox

## Current Status: ✅ ANONYMIZED

Your MCP configuration is now pointing to the **anonymized Netbox instance**.

## Configuration Summary

| Setting | Production | Anonymized (CURRENT) |
|---------|-----------|----------------------|
| Netbox URL | http://localhost:8000 | **http://localhost:8001** ✅ |
| API Token | c4af48e...916a | **4ab203e...0cd2** ✅ |
| Data Type | Real names | Hashed names |
| PII Protection | ❌ No | ✅ Yes |

## To Complete the Switch

**You must restart Claude Code for this change to take effect:**

1. **Exit Claude Code** (close the application)
2. **Restart Claude Code**
3. **Test the connection** by asking Claude to list devices

After restart, Claude will be querying the anonymized Netbox instance and will see hashed device names.

## Testing the Switch

Once Claude Code is restarted, try this query:

```
"List all devices at the Albany site"
```

**Expected result**: You should see device names like:
- `0a25438abc45eb6e97c5d973491fc23446af57cac7524097a702c50818009a94` (anonymized)

Instead of:
- `dmi01-albany-rtr01` (production)

## Switching Back to Production

If you need to switch back to production Netbox:

```bash
cp .mcp.json.production .mcp.json
# Then restart Claude Code
```

## Files Reference

- `.mcp.json` - **Active configuration** (currently: anonymized)
- `.mcp.json.production` - Backup of production config
- `.mcp.json.anonymized` - Template for anonymized config

## Web Frontends (Independent)

The web frontends continue to work independently:
- **http://localhost:3001** - Production frontend (queries localhost:8000)
- **http://localhost:3002** - Anonymized frontend (queries localhost:8001)

These are **separate** from the MCP configuration and don't need to be restarted.

## Verification

After restarting Claude Code, you can verify the switch worked by:

1. **Ask Claude**: "How many devices are in Netbox?"
   - Should return: 72 devices

2. **Ask Claude**: "List the first device"
   - Production would show: `dmi01-akron-pdu01`
   - Anonymized shows: `0a25438abc45eb6e97c5d973491fc23446af57cac7524097a702c50818009a94`

3. **Check MCP connection**: Claude's tools should show `mcp__netbox__*` tools

## Important Notes

- ✅ **Backup created**: Your production config is saved as `.mcp.json.production`
- ✅ **Reversible**: You can switch back anytime
- ⚠️ **Restart required**: Changes take effect only after Claude Code restart
- ⚠️ **Responses will contain hashes**: Claude will use anonymized names in responses

## Next Steps

1. **Restart Claude Code now**
2. **Test queries** to verify anonymized data
3. **Document any issues** with hash-based responses
4. **Consider mapping solution** if usability becomes a problem

---

**Last Updated**: 2026-03-30
**Status**: MCP switched to anonymized, restart pending
