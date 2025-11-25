# Troubleshooting Guide

## Common Issues

### 1. MCP 403 Forbidden Error

**Symptoms:**
- Netbox MCP tools return "403 Forbidden" errors
- Direct Netbox API calls work fine
- Error appears in MCP debug logs: `{"detail":"Invalid token"}`

**Root Cause:**
Shell environment variables are overriding the values from `.env` file. The MCP server subprocess inherits these environment variables.

**Solution:**
Use the startup script which explicitly sets environment variables:
```bash
./start_server.sh
```

Or check and fix your environment:
```bash
# Check current environment
env | grep NETBOX

# If wrong token is set, export the correct one
export NETBOX_TOKEN="<your-correct-token>"
export NETBOX_URL="http://localhost:8000"

# Then start the server
uv run uvicorn backend.api:app --reload --port 8001
```

**Prevention:**
- Always use `start_server.sh` to launch the application
- Check for conflicting environment variables before running
- Don't manually export NETBOX_TOKEN in your shell unless necessary

For detailed analysis, see [MCP_403_FIX.md](MCP_403_FIX.md).

---

### 2. Port Already in Use (Error 98)

**Symptoms:**
```
ERROR: [Errno 98] Address already in use
```

**Cause:**
Another application (likely Netbox itself) is using port 8000.

**Solution:**
Use a different port for the backend:
```bash
./start_server.sh  # Uses port 8001 by default
```

Or specify manually:
```bash
uv run uvicorn backend.api:app --reload --port 8001
```

---

### 3. Invalid Anthropic API Key

**Symptoms:**
```
Error: Invalid API key
```

**Solution:**
1. Get a valid API key from https://console.anthropic.com/settings/keys
2. Update your `.env` file:
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-...
   ```
3. Restart the server

---

### 4. WebSocket Connection Refused

**Symptoms:**
```
ConnectionRefusedError: [Errno 111] Connect call failed
```

**Cause:**
The backend server is not running or not listening on the expected port.

**Solution:**
1. Check if the server is running:
   ```bash
   curl http://localhost:8001/health
   ```

2. Check server logs for startup errors

3. Ensure no firewall is blocking the port

---

### 5. MCP Server Not Found

**Symptoms:**
```
Error: MCP server not found
```

**Cause:**
The Netbox MCP server path in [backend/mcp_config.py](backend/mcp_config.py) is incorrect.

**Solution:**
1. Verify the MCP server path exists:
   ```bash
   ls /home/ola/dev/rnd/mcp/testmcp/netbox-mcp-server/server.py
   ```

2. Update the path in `backend/mcp_config.py` if needed

3. Ensure the MCP server's virtual environment is set up:
   ```bash
   cd /home/ola/dev/rnd/mcp/testmcp/netbox-mcp-server
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

---

### 6. CLI Tool Issues

#### CLI Not Found

**Symptoms:**
```
python: can't open file 'netbox_cli.py': [Errno 2] No such file or directory
```

**Solution:**
Make sure you're in the project directory:
```bash
cd /home/ola/dev/netboxdev/claude-agentic-sdk
uv run python netbox_cli.py "List sites"
```

#### CLI Connection Refused

**Symptoms:**
```
❌ ERROR: WebSocket connection failed
```

**Solution:**
1. Ensure the backend server is running:
   ```bash
   ./start_server.sh
   ```

2. Check the URL matches your server:
   ```bash
   # If server is on different port
   uv run python netbox_cli.py --url ws://localhost:XXXX/ws/chat "query"
   ```

#### No Response in Interactive Mode

**Symptoms:**
Interactive mode starts but queries don't return results.

**Solution:**
1. Check server logs for errors
2. Try with `--verbose` to see tool usage
3. Verify WebSocket connection is active:
   ```bash
   curl http://localhost:8001/health
   ```

#### History Not Working

**Symptoms:**
Up/down arrows don't work in interactive mode.

**Solution:**
This requires `readline` support. On most systems it's built-in, but if not:
```bash
# Linux/Mac - usually included
# If issues, try:
pip install gnureadline  # Mac only
```

---

## Debug Mode

To enable detailed logging for troubleshooting:

1. **Set log level in `.env`:**
   ```
   LOG_LEVEL=DEBUG
   ```

2. **Use the debug MCP server:**
   Edit [backend/agent.py](backend/agent.py):
   ```python
   from backend.mcp_config_debug import get_allowed_netbox_tools, get_netbox_mcp_config
   ```

3. **Check MCP debug logs:**
   ```bash
   tail -f /tmp/netbox_mcp_debug.log
   ```

This will show:
- Exact token being used
- Full HTTP request headers
- Response status and body
- Detailed error messages

---

## Verification Commands

**Check environment variables:**
```bash
env | grep -E "(NETBOX|ANTHROPIC)"
```

**Test Netbox API directly:**
```bash
curl -H "Authorization: Token YOUR_TOKEN" \
     -H "Accept: application/json" \
     http://localhost:8000/api/dcim/sites/?limit=1
```

**Test backend health:**
```bash
curl http://localhost:8001/health
```

**Test full WebSocket flow:**
```bash
uv run python verify_fix.py
```

**Test CLI tool:**
```bash
# Single query test
uv run python netbox_cli.py "List sites"

# Interactive mode test
uv run python netbox_cli.py -i
# Then type: exit
```

---

## Getting Help

If none of the above solutions work:

1. Enable DEBUG logging
2. Capture full error output
3. Check the debug logs at `/tmp/netbox_mcp_debug.log`
4. Review server logs in the terminal
5. Create an issue with:
   - Error message
   - Debug logs
   - Steps to reproduce
   - Environment details (OS, Python version, etc.)
