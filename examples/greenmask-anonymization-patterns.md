# Greenmask Anonymization Patterns

This document provides common patterns and examples for anonymizing Netbox data using Greenmask.

## Table of Contents
1. [Deterministic Hashing](#deterministic-hashing)
2. [IP Address Anonymization](#ip-address-anonymization)
3. [MAC Address Anonymization](#mac-address-anonymization)
4. [Device Name Anonymization](#device-name-anonymization)
5. [What to Preserve vs Anonymize](#what-to-preserve-vs-anonymize)
6. [Custom Transformations](#custom-transformations)

---

## Deterministic Hashing

**Key Concept**: Same input always produces same output when using same seed.

### Why Deterministic?
- Query anonymization must match database anonymization
- Consistent results across multiple Greenmask runs
- Allows bidirectional mapping (original ↔ anonymized)

### Example: Device Names

```yaml
# greenmask-config.yml
transformations:
  - table: dcim_device
    columns:
      - name: name
        type: hash
        engine: deterministic           # ← CRITICAL: Makes it consistent
        seed: "${ANONYMIZATION_SEED}"   # ← Same seed = same output
        format: "device-{{.Hash | substr 0 6}}"

# With seed "my-secret-123":
# Input: "core-switch-nyc-01" → Hash: "7a3f2b..." → Output: "device-7a3f2b"
# Input: "core-switch-nyc-01" → Hash: "7a3f2b..." → Output: "device-7a3f2b" (same!)
```

### How It Works

```python
# Pseudocode for deterministic hashing
import hashlib

def deterministic_hash(value: str, seed: str) -> str:
    """Generate deterministic hash."""
    combined = f"{seed}:{value}"
    hash_bytes = hashlib.sha256(combined.encode()).hexdigest()
    return hash_bytes[:6]  # Take first 6 characters

# Examples:
deterministic_hash("core-switch-nyc-01", "my-secret-123")  # → "7a3f2b"
deterministic_hash("core-switch-nyc-01", "my-secret-123")  # → "7a3f2b" (same!)
deterministic_hash("core-switch-nyc-02", "my-secret-123")  # → "8b9c4d" (different input)
deterministic_hash("core-switch-nyc-01", "different-seed") # → "x9z1q4" (different seed)
```

---

## IP Address Anonymization

IP addresses are PII and must be anonymized, but we want to preserve network structure for Claude's reasoning.

### Pattern 1: Preserve Subnet Structure

```yaml
transformations:
  - table: ipam_ipaddress
    columns:
      - name: address
        type: custom
        function: |
          function anonymize_ip(ip_cidr) {
            // Split IP and CIDR
            parts = ip_cidr.split('/');
            ip = parts[0];
            cidr = parts[1] || '';

            // Parse IP octets
            octets = ip.split('.');

            // Hash based on original IP
            hash_val = hash256(ip + SEED);

            // Map to different private range
            if (octets[0] == '192' && octets[1] == '168') {
              // 192.168.x.x → 172.16.x.x
              new_ip = '172.16.' + (hash_val % 256) + '.' + ((hash_val >> 8) % 256);
            } else if (octets[0] == '10') {
              // 10.x.x.x → 172.17.x.x
              new_ip = '172.17.' + (hash_val % 256) + '.' + ((hash_val >> 8) % 256);
            } else {
              // Public IPs → 10.x.x.x
              new_ip = '10.' + (hash_val % 256) + '.' + ((hash_val >> 8) % 256) + '.' + ((hash_val >> 16) % 256);
            }

            // Preserve CIDR
            return cidr ? new_ip + '/' + cidr : new_ip;
          }
```

### Examples

| Original IP | Anonymized IP | Notes |
|-------------|---------------|-------|
| `192.168.1.100/24` | `172.16.45.89/24` | Private range preserved |
| `192.168.1.101/24` | `172.16.92.34/24` | Same subnet, different IPs |
| `10.0.50.1/8` | `172.17.78.12/8` | Different private range |
| `8.8.8.8` | `10.123.45.67` | Public → private |

### Pattern 2: Simple Hash-Based

```yaml
transformations:
  - table: ipam_ipaddress
    columns:
      - name: address
        type: hash
        engine: deterministic
        seed: "${ANONYMIZATION_SEED}"
        format: "10.{{.Hash | substr 0 3}}.{{.Hash | substr 3 3}}.{{.Hash | substr 6 3}}"

# Example:
# Input: "192.168.1.100"
# Hash: "a3f9b2c8..."
# Output: "10.163.249.178"
```

---

## MAC Address Anonymization

### Pattern: Preserve Local Administration Bit

```yaml
transformations:
  - table: dcim_macaddress
    columns:
      - name: mac_address
        type: custom
        function: |
          function anonymize_mac(mac) {
            // Generate hash
            hash_val = hash256(mac + SEED);

            // Create MAC octets from hash
            octets = [];
            for (i = 0; i < 6; i++) {
              octet = (hash_val >> (i * 8)) & 0xFF;
              octets.push(octet);
            }

            // Set locally administered bit (bit 1 of first octet)
            // Clear multicast bit (bit 0 of first octet)
            octets[0] = (octets[0] | 0x02) & 0xFE;

            // Format as MAC address
            return octets.map(o => o.toString(16).padStart(2, '0')).join(':');
          }
```

### Examples

| Original MAC | Anonymized MAC | Notes |
|--------------|----------------|-------|
| `00:1A:2B:3C:4D:5E` | `02:7F:A3:B9:C1:D8` | Bit 1 set (locally admin) |
| `00:1A:2B:3C:4D:5F` | `02:8E:B4:C2:D3:E9` | Different for different input |
| `AA:BB:CC:DD:EE:FF` | `02:9A:C5:D1:E7:F2` | Always starts with `02` or `06` or `0A` etc. |

---

## Device Name Anonymization

### Pattern 1: Preserve Device Type Hint

```yaml
transformations:
  - table: dcim_device
    columns:
      - name: name
        type: custom
        function: |
          function anonymize_device_name(name) {
            // Detect device type from name
            device_type = 'device';
            if (name.toLowerCase().includes('switch')) {
              device_type = 'switch';
            } else if (name.toLowerCase().includes('router')) {
              device_type = 'router';
            } else if (name.toLowerCase().includes('firewall')) {
              device_type = 'fw';
            } else if (name.toLowerCase().includes('server')) {
              device_type = 'server';
            }

            // Generate deterministic hash
            hash_val = hash256(name + SEED).substr(0, 6);

            // Format with type hint
            return device_type + '-' + hash_val;
          }
```

### Examples

| Original Name | Anonymized Name | Type Preserved? |
|---------------|-----------------|-----------------|
| `core-switch-nyc-01` | `switch-7a3f2b` | ✅ Yes |
| `edge-router-lon-05` | `router-8b9c4d` | ✅ Yes |
| `firewall-dmz-primary` | `fw-x1y2z3` | ✅ Yes |
| `web-server-prod-01` | `server-a9b8c7` | ✅ Yes |
| `random-device-123` | `device-m4n5p6` | ✅ Generic |

### Pattern 2: Simple Hash (No Type Hint)

```yaml
transformations:
  - table: dcim_device
    columns:
      - name: name
        type: hash
        engine: deterministic
        seed: "${ANONYMIZATION_SEED}"
        format: "device-{{.Hash | substr 0 8}}"

# Examples:
# "core-switch-nyc-01" → "device-7a3f2bc8"
# "edge-router-lon-05" → "device-8b9c4d1e"
```

**Trade-off**: Loses device type semantic hint, but simpler configuration.

---

## What to Preserve vs Anonymize

### ✅ PRESERVE (Claude Needs These)

```yaml
# IDs and Foreign Keys - NEVER ANONYMIZE
# These are critical for Claude's multi-step reasoning

- table: dcim_device
  columns:
    # ✅ PRESERVE - Just numbers, not PII
    # - id  (don't list in transformations)
    # - site_id
    # - device_role_id
    # - device_type_id
    # - tenant_id

# Status Values - Usually PRESERVE
# Generic states, not identifying

- table: dcim_device
  columns:
    # ✅ PRESERVE
    # - status  (active, planned, offline)

# Technical Specifications - ALWAYS PRESERVE
# Not PII, helps Claude with capacity planning

- table: dcim_device
  columns:
    # ✅ PRESERVE
    # - vcpus
    # - memory
    # - disk

# Vendor/Model Names - USUALLY PRESERVE (configurable)
# Public product info, helps Claude reason about capabilities

- table: dcim_devicetype
  columns:
    # ✅ PRESERVE (unless organization policy forbids)
    # - manufacturer (Cisco, Juniper, Arista)
    # - model (Catalyst 9500, MX480)
```

### ❌ ANONYMIZE (PII / Identifying Information)

```yaml
# Device Names - ALWAYS ANONYMIZE
- table: dcim_device
  columns:
    - name: name
      type: hash
      format: "device-{{.Hash | substr 0 6}}"

# IP Addresses - ALWAYS ANONYMIZE
- table: ipam_ipaddress
  columns:
    - name: address
      type: custom  # Use custom function for structure preservation

# Site/Location Names - ALWAYS ANONYMIZE
- table: dcim_site
  columns:
    - name: name
      type: hash
      format: "site-{{.Hash | substr 0 5}}"
    - name: physical_address
      type: faker
      faker_type: address
    - name: facility
      type: hash
      format: "facility-{{.Hash | substr 0 4}}"

# Contact Information - ALWAYS ANONYMIZE
- table: tenancy_contact
  columns:
    - name: name
      type: faker
      faker_type: name
    - name: email
      type: faker
      faker_type: email
    - name: phone
      type: faker
      faker_type: phoneNumber
    - name: address
      type: faker
      faker_type: address

# Serial Numbers / Asset Tags - ANONYMIZE
- table: dcim_device
  columns:
    - name: serial
      type: hash
      format: "SN-{{.Hash | substr 0 8 | upper}}"
    - name: asset_tag
      type: hash
      format: "ASSET-{{.Hash | substr 0 6}}"

# Descriptions / Comments - ANONYMIZE (may contain PII)
- table: dcim_device
  columns:
    - name: comments
      type: faker
      faker_type: sentence
```

---

## Custom Transformations

### Example: Conditional Anonymization

Only anonymize tags that contain sensitive patterns:

```yaml
transformations:
  - table: extras_tag
    columns:
      - name: name
        type: custom
        function: |
          function anonymize_tag(tag_name) {
            // List of generic tags to preserve
            generic_tags = [
              'critical', 'production', 'staging', 'development',
              'dmz', 'redundancy-a', 'redundancy-b', 'backup'
            ];

            // Check if tag is generic
            if (generic_tags.includes(tag_name.toLowerCase())) {
              return tag_name;  // Preserve generic tags
            }

            // Check for sensitive patterns
            sensitive_patterns = [
              /customer-/i,    // customer-acme
              /project-/i,     // project-merger
              /client-/i,      // client-xyz
              /-datacenter$/i  // manhattan-datacenter
            ];

            for (pattern of sensitive_patterns) {
              if (pattern.test(tag_name)) {
                // Anonymize sensitive tag
                hash_val = hash256(tag_name + SEED).substr(0, 6);
                return 'tag-' + hash_val;
              }
            }

            // Default: preserve
            return tag_name;
          }
```

### Example: Preserve Meaningful VLAN IDs

```yaml
transformations:
  - table: ipam_vlan
    columns:
      - name: name
        type: hash
        format: "VLAN-{{.Hash | substr 0 4}}"
      # Note: vid (VLAN ID number) is NOT anonymized
      # It's just a number (100, 200, etc.) - not identifying
```

### Example: Custom IP Range Mapping

```yaml
transformations:
  - table: ipam_prefix
    columns:
      - name: prefix
        type: custom
        function: |
          function anonymize_prefix(prefix_cidr) {
            // Parse prefix and CIDR
            parts = prefix_cidr.split('/');
            prefix = parts[0];
            cidr = parts[1];

            // Determine new network based on original
            octets = prefix.split('.');
            hash_val = hash256(prefix + SEED);

            // Map entire prefixes deterministically
            if (octets[0] == '192' && octets[1] == '168') {
              // 192.168.0.0/16 range → 172.16.0.0/16 range
              new_prefix = '172.16.' + (hash_val % 256) + '.0';
            } else if (octets[0] == '10') {
              // 10.0.0.0/8 range → 172.17.0.0/12 range
              new_prefix = '172.17.' + (hash_val % 16) + '.0';
            } else {
              // Public prefixes → 10.0.0.0/8 range
              new_prefix = '10.' + (hash_val % 256) + '.' + ((hash_val >> 8) % 256) + '.0';
            }

            return new_prefix + '/' + cidr;
          }
```

---

## Complete Example Configuration

Here's a minimal but complete Greenmask config:

```yaml
database:
  host: netbox-prod.internal
  port: 5432
  name: netbox
  user: greenmask_readonly
  password: ${PROD_DB_PASSWORD}

output:
  type: postgres
  host: netbox-anon.internal
  port: 5432
  name: netbox_anonymized
  user: netbox
  password: ${ANON_DB_PASSWORD}

transformations:
  # Devices - Preserve IDs, anonymize names
  - table: dcim_device
    columns:
      - name: name
        type: hash
        engine: deterministic
        seed: "${ANONYMIZATION_SEED}"
        format: "device-{{.Hash | substr 0 6}}"
      - name: serial
        type: hash
        engine: deterministic
        seed: "${ANONYMIZATION_SEED}"
        format: "SN-{{.Hash | substr 0 8 | upper}}"

  # Sites - Anonymize location info
  - table: dcim_site
    columns:
      - name: name
        type: hash
        engine: deterministic
        seed: "${ANONYMIZATION_SEED}"
        format: "site-{{.Hash | substr 0 5}}"
      - name: physical_address
        type: faker
        faker_type: address
      - name: shipping_address
        type: faker
        faker_type: address

  # IP Addresses - Custom anonymization
  - table: ipam_ipaddress
    columns:
      - name: address
        type: hash
        engine: deterministic
        seed: "${ANONYMIZATION_SEED}"
        format: "10.{{.Hash | substr 0 3}}.{{.Hash | substr 3 3}}.{{.Hash | substr 6 3}}"
      - name: dns_name
        type: hash
        engine: deterministic
        seed: "${ANONYMIZATION_SEED}"
        format: "host-{{.Hash | substr 0 8}}.internal"

validation:
  - type: referential_integrity
    enabled: true
  - type: unique_constraints
    preserve: true
```

---

## Testing Your Transformations

### Validate Config

```bash
greenmask validate --config greenmask-config.yml
```

### Test on Sample Data

```bash
# Dry run (doesn't write to target)
greenmask dump \
  --config greenmask-config.yml \
  --dry-run \
  --output /tmp/test_dump.sql

# Check output for anonymized values
grep "INSERT INTO dcim_device" /tmp/test_dump.sql | head -5
```

### Verify Determinism

```bash
# Run anonymization twice, compare mappings
greenmask dump --save-mappings /tmp/mappings1.json
greenmask dump --save-mappings /tmp/mappings2.json

# Should be identical if seed is same
diff /tmp/mappings1.json /tmp/mappings2.json
```

---

## Best Practices

1. **Always use deterministic hashing** - Ensures consistency
2. **Test transformations on sample data first** - Before running on full DB
3. **Validate after anonymization** - Check for PII leakage
4. **Document your decisions** - Why preserve vendor names? Why anonymize tags?
5. **Keep seed secret** - Never commit to git
6. **Preserve structure** - IPs should still look like IPs
7. **Consider Claude's needs** - Preserve metadata it needs for reasoning
8. **Balance security and functionality** - More anonymization = less Claude effectiveness

---

## References

- [Greenmask Documentation](https://greenmask.io/docs)
- [ANONYMIZATION_RATIONALE.md](../docs/development/anonymization/ANONYMIZATION_RATIONALE.md) - What to preserve
- [greenmask-config-complete.yml](../docs/development/anonymization/greenmask-config-complete.yml) - Full config
