# Netbox CLI - Quick Start Guide

## Installation & Setup

```bash
# 1. Ensure server is running
./start_server.sh

# 2. Test CLI (in another terminal)
uv run python netbox_cli.py "List sites"
```

## Usage Modes

### Single Query (One-Shot)

Execute a query and exit:

```bash
# Basic query
uv run python netbox_cli.py "List all sites"

# Verbose mode (shows tool usage)
uv run python netbox_cli.py --verbose "Show devices in DC1"
uv run python netbox_cli.py -v "What VLANs exist?"

# JSON output (for scripts/piping)
uv run python netbox_cli.py --json "List sites" | jq '.content' | grep -i "active"

# No color (for logs/files)
uv run python netbox_cli.py --no-color "List devices" > devices.txt
```

### Interactive Mode (REPL)

Start an interactive session:

```bash
# Long form
uv run python netbox_cli.py --interactive

# Short form
uv run python netbox_cli.py -i
```

**In interactive mode:**
- Type queries naturally
- Use up/down arrows for command history
- Conversation context is maintained
- Type `exit`, `quit`, or press Ctrl+D to exit
- Press Ctrl+C to cancel current input (not exit)

## Common Queries

### Infrastructure Discovery

```bash
# Sites and locations
"List all sites"
"Show sites in region North Carolina"
"What sites belong to tenant Dunder-Mifflin?"

# Devices
"Show all devices"
"List devices in site MDF"
"Find devices with status active"
"Show me device details for core-router-1"

# Racks
"List all racks"
"Show racks in site DC1"
"What racks are in building B?"
```

### Networking

```bash
# VLANs
"What VLANs exist?"
"Show VLANs in site DC1"
"List VLANs with tag production"

# IP Addressing
"Show IP addresses"
"Find IP addresses in 10.0.0.0/8"
"What IP prefixes exist?"
"Show available IPs in 192.168.1.0/24"

# Interfaces
"List interfaces on device core-switch-1"
"Show interface details for eth0"
```

### Filtering & Search

```bash
# By status
"Find all active devices"
"Show offline sites"

# By tenant
"List devices for tenant NC State University"
"Show sites owned by Jimbob's Banking"

# By type/role
"What device roles are configured?"
"List all switches"
"Show routers in site DC1"
```

### Counts & Summaries

```bash
"How many sites do we have?"
"Count devices per site"
"Summarize our infrastructure"
"Show site statistics"
```

## Options Reference

```
Options:
  -h, --help            Show help message and exit
  -i, --interactive     Run in interactive mode (REPL)
  -v, --verbose         Show verbose output (tool usage, metadata)
  --json                Output raw JSON chunks
  --no-color            Disable colored output
  --url URL             WebSocket URL (default: ws://localhost:8001/ws/chat)
  --timeout TIMEOUT     Query timeout in seconds (default: 60)
```

## Tips & Tricks

### 1. Use Verbose Mode for Learning

See which MCP tools are being used:
```bash
uv run python netbox_cli.py -v "List sites"
# Shows: 🔧 [Using tool: netbox_get_objects]
```

### 2. Pipe JSON Output to jq

```bash
uv run python netbox_cli.py --json "List sites" | jq '.content' | grep -v '^""$'
```

### 3. Save Queries to Files

```bash
uv run python netbox_cli.py --no-color "List all devices" > devices_$(date +%Y%m%d).txt
```

### 4. Chain Queries in Scripts

```bash
#!/bin/bash
echo "=== Sites ==="
uv run python netbox_cli.py "List sites"
echo -e "\n=== Devices ==="
uv run python netbox_cli.py "List devices"
echo -e "\n=== VLANs ==="
uv run python netbox_cli.py "List VLANs"
```

### 5. Interactive Mode for Exploration

Use interactive mode when exploring data or following up on results:
```
netbox> List sites in North Carolina
[Results...]

netbox> Show devices in site MDF
[Results...]

netbox> What's the device role of the first one?
[Results...]
```

## Troubleshooting

### Connection Refused
```bash
# Check if server is running
curl http://localhost:8001/health

# If not, start it
./start_server.sh
```

### Timeout Errors
```bash
# Increase timeout for complex queries
uv run python netbox_cli.py --timeout 120 "Complex query"
```

### CLI Not Found
```bash
# Make sure you're in project directory
cd /home/ola/dev/netboxdev/claude-agentic-sdk
ls netbox_cli.py  # Should exist
```

### Unexpected Results
```bash
# Use verbose mode to see what's happening
uv run python netbox_cli.py -v "Your query"
```

## Examples by Use Case

### Daily Operations

```bash
# Morning infrastructure check
uv run python netbox_cli.py -i <<EOF
List any offline devices
Show sites with less than 80% IP utilization
What critical alerts exist?
exit
EOF
```

### Audit & Compliance

```bash
# Generate compliance report
uv run python netbox_cli.py --no-color "List all sites with their tenant and status" > compliance_$(date +%Y%m%d).txt
```

### Capacity Planning

```bash
# Interactive capacity analysis
uv run python netbox_cli.py -i
> How many total devices do we have?
> What percentage of rack space is used?
> Show sites sorted by device count
> exit
```

### Documentation

```bash
# Document network topology
uv run python netbox_cli.py "Describe the network topology for site DC1" > docs/dc1_topology.md
```

## Advanced: Scripting with the CLI

### Bash Script Example

```bash
#!/bin/bash
# check_sites.sh - Check all sites and report status

echo "Netbox Site Status Report - $(date)"
echo "======================================="

# Get site list
uv run python netbox_cli.py --no-color "List all sites with their status" | tee /tmp/sites.txt

# Count stats
total=$(grep -c "Active\|Offline" /tmp/sites.txt || echo "0")
echo -e "\nTotal sites found: $total"

# Cleanup
rm -f /tmp/sites.txt
```

### Python Script Example

```python
#!/usr/bin/env python3
import subprocess
import json

def query_netbox(query):
    """Query Netbox via CLI and return JSON response."""
    result = subprocess.run(
        ["uv", "run", "python", "netbox_cli.py", "--json", query],
        capture_output=True,
        text=True
    )
    # Parse JSON chunks
    chunks = [json.loads(line) for line in result.stdout.strip().split('\n')]
    text_chunks = [c['content'] for c in chunks if c['type'] == 'text']
    return ''.join(text_chunks)

# Use it
sites = query_netbox("List all sites")
print(sites)
```

## Getting Help

**In the CLI:**
```bash
uv run python netbox_cli.py --help
```

**Documentation:**
- Full docs: [NETBOX_CHATBOX_README.md](NETBOX_CHATBOX_README.md)
- Troubleshooting: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- MCP 403 fix: [MCP_403_FIX.md](MCP_403_FIX.md)

**Testing:**
```bash
# Test suite
uv run pytest tests/test_cli.py -v

# Quick verification
uv run python verify_fix.py
```
