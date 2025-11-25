# Debug Session Summary - MCP 403 Error Resolution

**Date:** 2025-11-24
**Issue:** Netbox MCP tools returning 403 Forbidden errors
**Status:** ✅ RESOLVED

## Problem Statement

The Netbox Chatbox backend was successfully implemented with Claude Agent SDK and Netbox MCP server integration. All 59 unit tests passed. However, when testing the WebSocket API, the MCP tools consistently returned 403 Forbidden errors when trying to access the Netbox API.

**Confusing Factor:** Direct API calls to Netbox using the same token worked perfectly, suggesting the issue was not with Netbox or the token itself.

## Investigation Process

### 1. Initial Debugging Attempts
- Verified Netbox API was accessible directly with curl
- Confirmed the token in `.env` file was correct
- Checked backend configuration loading
- All appeared correct, but 403 errors persisted

### 2. Creating Debug Infrastructure
Created `server_debug.py` - a modified version of the Netbox MCP server with extensive logging:
- Logged environment variables at startup
- Logged every HTTP request with full headers
- Logged response status and body
- Output to `/tmp/netbox_mcp_debug.log`

### 3. The Breakthrough
When examining the debug logs, we discovered:

```
2025-11-24 19:02:30,702 - __main__ - INFO -   token: 6dd174288c...
2025-11-24 19:02:30,702 - __main__ - INFO -   headers: {...'Authorization': 'Token 6dd174288c66b205eb4687bcc9394277f381626c'...}
2025-11-24 19:02:30,712 - __main__ - ERROR -   response_body: {"detail":"Invalid token"}
```

**The MCP server was using a DIFFERENT token** than what was in the `.env` file!

### 4. Root Cause Identification

Checked the shell environment:
```bash
$ env | grep NETBOX_TOKEN
NETBOX_TOKEN=6dd174288c66b205eb4687bcc9394277f381626c
```

**Root Cause:** The shell environment had an old/incorrect token set, which was being inherited by the backend process and subsequently passed to the MCP server subprocess, overriding the correct token from the `.env` file.

## Solution

### Immediate Fix
Created `start_server.sh` that explicitly exports the correct environment variables before starting the server:

```bash
#!/bin/bash
export NETBOX_TOKEN="c4af48e5b315a5baf92f7ca449ac5d664239916a"
export NETBOX_URL="http://localhost:8000"
uv run uvicorn backend.api:app --reload --port 8001
```

### Verification
After applying the fix, the debug logs showed:
```
2025-11-24 19:09:15,751 - __main__ - INFO -   token: c4af48e5b3...
2025-11-24 19:09:15,917 - urllib3.connectionpool - DEBUG - http://localhost:8000 "GET /api/dcim/sites/ HTTP/1.1" 200 39611
2025-11-24 19:09:15,920 - __main__ - INFO -   returned: 24 results
```

✅ **Success!** The correct token was being used and API calls returned 200 OK.

## Key Learnings

### 1. Environment Variable Inheritance
Subprocesses inherit their parent's environment variables, which can override values loaded from `.env` files. This is a common source of configuration bugs.

### 2. Debug Logging is Essential
Without detailed logging at the MCP server level, we would never have discovered the token mismatch. The debug logs showed:
- Exact environment variables received
- Complete HTTP headers being sent
- Response status and body

### 3. Shell State Matters
Shell environment variables persist across commands and can interfere with application configuration. Always verify the environment when debugging configuration issues.

### 4. Test at Multiple Levels
Testing the Netbox API directly worked, but testing through the full stack (backend → MCP server → Netbox) revealed the issue. Integration testing is crucial.

## Files Created During Debug Session

1. **server_debug.py** - Debug version of MCP server with extensive logging
2. **backend/mcp_config_debug.py** - Configuration to use debug MCP server
3. **debug_mcp_403.py** - Comprehensive debug script testing all components
4. **start_server.sh** - Startup script with correct environment
5. **verify_fix.py** - Quick verification script
6. **MCP_403_FIX.md** - Detailed documentation of the issue and fix
7. **TROUBLESHOOTING.md** - General troubleshooting guide
8. **NETBOX_CHATBOX_README.md** - Complete project documentation

## Prevention Going Forward

### For Developers
1. Always use `start_server.sh` to launch the application
2. Check environment before running: `env | grep NETBOX`
3. Don't manually export NETBOX_TOKEN unless necessary
4. If debugging, enable DEBUG log level and check MCP logs

### For System Design
1. Consider validating environment variables at startup
2. Log configuration values (masked) at startup
3. Provide clear error messages when auth fails
4. Include environment verification in health checks

## Timeline

1. **Issue Reported:** User got 403 errors when testing the WebSocket API
2. **Initial Investigation:** Verified token, Netbox access, backend config
3. **Debug Infrastructure:** Created debug MCP server with detailed logging
4. **Root Cause Found:** Debug logs revealed token mismatch
5. **Fix Applied:** Created startup script with correct environment
6. **Verification:** Confirmed MCP tools working with 200 OK responses
7. **Documentation:** Created comprehensive troubleshooting guides

Total time: ~2 hours of debugging, but the debug infrastructure will prevent similar issues in the future.

## Conclusion

What initially appeared to be a complex authentication or MCP configuration issue was actually a simple environment variable problem. The key to solving it was:

1. **Systematic debugging** - Test each layer independently
2. **Detailed logging** - See exactly what's happening at each step
3. **Verify assumptions** - Don't assume .env values are being used
4. **Document solutions** - Help others avoid the same issue

The Netbox Chatbox backend is now fully functional with working MCP integration! 🎉

## Next Steps

With the 403 error resolved:
- ✅ Backend fully functional
- ✅ WebSocket API working
- ✅ MCP tools accessing Netbox successfully
- ⏭️ Ready for frontend implementation (Nuxt.js)
- ⏭️ Ready for production deployment considerations
