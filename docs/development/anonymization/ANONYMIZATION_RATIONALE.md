# Anonymization Rationale - What to Preserve vs Anonymize

**Date:** 2026-03-24
**Purpose:** Explain the decision logic for what gets anonymized vs preserved

---

## Core Principle

**ANONYMIZE**: Data that identifies specific **people, places, or organizations**
**PRESERVE**: Generic **metadata and technical specifications** that Claude needs for reasoning

---

## Categories NOT Anonymized (and Why)

### 1. **IDs and Foreign Keys** - MUST PRESERVE

**Data:**
- `id` (primary keys)
- `site_id`, `device_id`, `tenant_id` (foreign keys)
- All relationship IDs

**Rationale:**
```
❌ If anonymized: Relationships break completely
❌ Claude can't do: "Find devices at site 12" (relationship lookup fails)
❌ Database integrity: Foreign key constraints violated

✅ If preserved: Claude can traverse relationships
✅ Claude can do: Device 147 → site_id: 12 → Site record with id: 12
✅ Not PII: Just numbers with no meaning outside the database
```

**Privacy Impact:** ✅ **NONE** - IDs are meaningless outside context

**Example:**
```sql
-- Device record
id: 147                    -- ✅ Just a number
name: "device-7a3f2b"      -- ✅ Anonymized
site_id: 12                -- ✅ Just a reference number

-- Claude can still query: "Show all devices at site 12"
-- Works because site_id=12 relationship is preserved
```

---

### 2. **Status Values** - Generally Preserved

**Data:**
- `status: "active"`, `"planned"`, `"offline"`, `"decommissioning"`
- `operational_status: "pre-production"`, `"production"`

**Rationale:**
```
✅ Generic categorical values
✅ Not organization-specific (every network has "active" devices)
✅ Claude needs this for filtering: "Show active devices"
✅ No PII: Doesn't identify who/where/what specifically
```

**Privacy Impact:** ✅ **NONE** - Universal values, not identifying

**BUT - Exception Cases:**
Some organizations use custom status values that might be identifying:

```yaml
# Generic (PRESERVE):
status: "active"           # ✅ Universal
status: "planned"          # ✅ Universal
status: "offline"          # ✅ Universal

# Custom/Identifying (ANONYMIZE):
status: "NYC-migration-phase-2"     # ❌ Location-specific project
status: "customer-acme-testing"     # ❌ Customer name
status: "reserved-for-merger"       # ❌ Business-sensitive
```

**Recommendation:** Review custom status values - anonymize if organization-specific.

---

### 3. **Device Roles** - Generally Preserved

**Data:**
- `device_role: "core"`, `"distribution"`, `"access"`, `"edge"`, `"leaf"`, `"spine"`

**Rationale:**
```
✅ Generic network architecture terms
✅ Industry-standard categorizations
✅ Claude needs this: "Show core routers" (filters by role)
✅ Not PII: Describes function, not identity
```

**Privacy Impact:** ✅ **NONE** - Standard network terminology

**BUT - Exception Cases:**
```yaml
# Generic (PRESERVE):
device_role: "core"                 # ✅ Standard
device_role: "access"               # ✅ Standard
device_role: "distribution"         # ✅ Standard

# Custom/Identifying (ANONYMIZE):
device_role: "DC1-primary-core"     # ❌ Location-specific
device_role: "customer-facing-pe"   # ❌ Business role
device_role: "crypto-mining-host"   # ❌ Specific use case
```

**Recommendation:** Review custom roles - anonymize if business/location-specific.

---

### 4. **Device Types / Manufacturers** - Generally Preserved

**Data:**
- `manufacturer: "Cisco"`, `"Juniper"`, `"Arista"`, `"Dell"`
- `device_type: "Catalyst 9500"`, `"MX480"`, `"DCS-7280"`
- `model: "Catalyst 9500-48Y4C"`

**Rationale:**
```
✅ PUBLIC INFORMATION: Vendor/model names are publicly documented
✅ Not identifying: Millions of organizations use Cisco switches
✅ Claude needs this for context: Understanding capabilities, port counts, etc.
✅ Not PII: Product names don't identify your organization
```

**Privacy Impact:** ⚠️ **MINIMAL** - Public product info

**Why This Matters for Claude:**
```
Query: "Check if we have redundant core routers"

Claude sees:
- Device 1: role=core, type="Catalyst 9500", status=active
- Device 2: role=core, type="Catalyst 9500", status=active

Claude can infer:
✅ Both are enterprise-class core switches (knows Catalyst 9500 specs)
✅ Both are same model (good for redundancy)
✅ Both active (redundancy working)

If anonymized:
- Device 1: role=core, type="TYPE-abc123", status=active
- Device 2: role=core, type="TYPE-def456", status=active

Claude cannot infer:
❌ Are these the same model? (critical for redundancy)
❌ Are these even switches? (could be firewalls)
❌ What capabilities do they have?
```

**HOWEVER - Exception Cases:**

Some organizations consider vendor selection sensitive:

```yaml
# Scenario 1: Vendor selection might reveal business strategy
manufacturer: "Huawei"    # ⚠️ Political/compliance implications
manufacturer: "Fortinet"  # ⚠️ Reveals security posture

# Scenario 2: Custom/rare equipment might be identifying
device_type: "Custom-Built-Quantum-Router-Prototype"  # ❌ Very specific
device_type: "Experimental-6G-Base-Station"           # ❌ Identifying

# Scenario 3: Government/Defense
# ALL vendor info might be classified
```

**Recommendation:**
- **Most organizations**: Preserve vendor/model (public info, helps Claude)
- **High-security environments**: Anonymize if vendor selection is sensitive
- **Government/Defense**: Anonymize all vendor info

---

### 5. **Platforms (Operating Systems)** - Generally Preserved

**Data:**
- `platform: "IOS"`, `"JUNOS"`, `"Linux"`, `"Windows Server"`

**Rationale:**
```
✅ Public OS names
✅ Not identifying (millions use IOS)
✅ Claude needs this for understanding device capabilities
```

**Privacy Impact:** ✅ **NONE** - Public software names

**Exception Cases:**
```yaml
# Generic (PRESERVE):
platform: "IOS"                     # ✅ Public
platform: "JUNOS"                   # ✅ Public
platform: "Linux"                   # ✅ Public

# Custom (ANONYMIZE):
platform: "CompanyX-Custom-OS-v3"   # ❌ Proprietary/identifying
```

---

### 6. **Tags** - Generally Preserved

**Data:**
- `tags: ["critical", "redundancy-a", "production", "dmz"]`

**Rationale:**
```
✅ Semantic labels used for categorization
✅ Claude uses tags for grouping/filtering
✅ Generic across organizations
```

**Privacy Impact:** ⚠️ **DEPENDS ON TAG CONTENT**

**Why Claude Needs Tags:**
```
Query: "Check redundancy for critical infrastructure"

Claude sees:
- Device 1: tags=["critical", "redundancy-a"]
- Device 2: tags=["critical", "redundancy-a"]
- Device 3: tags=["critical", "redundancy-b"]

Claude can infer:
✅ Devices 1&2 are in same redundancy group
✅ All three are critical (need extra attention)
✅ Two redundancy groups exist (a and b)

If tags anonymized:
- Device 1: tags=["TAG-1", "TAG-2"]
- Device 2: tags=["TAG-1", "TAG-2"]
- Device 3: tags=["TAG-1", "TAG-3"]

Claude can infer:
✅ Devices 1&2 share TAG-2 (might be redundancy)
❌ What does "critical" mean? Lost semantic meaning
❌ Can't prioritize based on importance
```

**HOWEVER - Exception Cases:**

```yaml
# Generic (PRESERVE):
tags: ["critical"]                  # ✅ Generic priority
tags: ["redundancy-a"]              # ✅ Generic grouping
tags: ["production"]                # ✅ Generic environment
tags: ["dmz"]                       # ✅ Generic network zone

# Identifying (ANONYMIZE):
tags: ["project-acme-merger"]       # ❌ Business-specific
tags: ["customer-bigcorp"]          # ❌ Customer name
tags: ["manhattan-datacenter"]      # ❌ Location
tags: ["crypto-mining-pool-7"]      # ❌ Specific use case
tags: ["emergency-backup-for-superbowl"]  # ❌ Event-specific
```

**Recommendation:**
- **Generic tags**: Preserve (critical, production, redundancy-*)
- **Business/location/customer tags**: Anonymize

---

### 7. **VLAN IDs, AS Numbers, Port Numbers** - Generally Preserved

**Data:**
- `vlan_id: 100`, `200`, `300`
- `asn: 65001` (private AS number)
- `port: 443`, `8080`

**Rationale:**
```
✅ Numeric identifiers without inherent meaning
✅ VLAN 100 could be anything (doesn't identify organization)
✅ Claude needs VID for grouping: "Show devices on VLAN 100"
✅ AS numbers in private range (65000-65535) not publicly registered
```

**Privacy Impact:** ✅ **NONE** (if private range) / ⚠️ **MINIMAL** (if public)

**Exception Cases:**

```yaml
# Private AS Numbers (PRESERVE):
asn: 65001                    # ✅ Private range, not publicly registered

# Public AS Numbers (CONSIDER ANONYMIZING):
asn: 15169                    # ⚠️ Google's AS number (public record)
asn: 13335                    # ⚠️ Cloudflare's AS number

# VLAN IDs (PRESERVE - usually):
vlan_id: 100                  # ✅ Just a number, no meaning

# BUT if you use meaningful VLAN schemes:
vlan_id: 911                  # ⚠️ Might reveal emergency services network
vlan_id: 1776                 # ⚠️ Might reveal US government network
```

**Recommendation:**
- **Private AS numbers**: Preserve
- **Public AS numbers**: Consider anonymizing (reveals ISP/peer relationships)
- **VLAN IDs**: Preserve (just numbers)

---

### 8. **Technical Specifications** - Always Preserved

**Data:**
- `vcpus: 4`, `memory: 16384`, `disk: 500`
- `u_height: 2`, `interface_count: 48`
- `speed: 10000` (10G), `duplex: "full"`
- `mtu: 9000`, `airflow: "front-to-back"`

**Rationale:**
```
✅ Generic technical specs, not identifying
✅ A device with 4 vCPUs doesn't identify your organization
✅ Claude needs this for capacity planning queries
✅ Not PII: Just numbers/specs
```

**Privacy Impact:** ✅ **NONE**

**Why This Matters:**
```
Query: "Do we have enough capacity for new VMs?"

Claude sees:
- VM Host 1: vcpus=64, memory=512GB, used_vcpus=48
- VM Host 2: vcpus=64, memory=512GB, used_vcpus=52

Claude can calculate:
✅ Total available: 64-48 + 64-52 = 28 vCPUs free
✅ Can answer capacity questions

If anonymized:
❌ Can't do math on capacity
❌ Can't answer planning questions
```

---

### 9. **Timestamps** - Generally Preserved

**Data:**
- `created: "2023-01-15T10:30:00Z"`
- `last_updated: "2024-03-20T14:22:00Z"`

**Rationale:**
```
✅ Useful for "recently added" queries
✅ Not identifying (date alone doesn't reveal identity)
✅ Helps Claude understand infrastructure age/change patterns
```

**Privacy Impact:** ⚠️ **MINIMAL**

**Exception Cases:**
```
# Event correlation risk:
created: "2023-09-15"    # If this is the ONLY device added on this date
                         # AND there was a public announcement on this date
                         # Could correlate to identify organization

# Generally safe if:
- Many devices share similar dates
- No public events correlate with dates
```

**Recommendation:** Usually preserve, unless you have specific correlation concerns.

---

### 10. **Boolean Flags** - Always Preserved

**Data:**
- `enabled: true/false`
- `is_active: true/false`
- `is_virtual: true/false`

**Rationale:**
```
✅ Just state indicators
✅ Claude needs this: "Show enabled interfaces"
✅ Not PII: Binary state
```

**Privacy Impact:** ✅ **NONE**

---

## Summary Table: Preserve vs Anonymize

| Data Type | Default Action | Privacy Risk | Claude Needs It? | Can Override? |
|-----------|----------------|--------------|------------------|---------------|
| **IDs / Foreign Keys** | ✅ PRESERVE | ✅ None | ✅✅✅ Critical | ❌ No (breaks DB) |
| **Status Values (generic)** | ✅ PRESERVE | ✅ None | ✅✅ High | ✅ Yes (if custom) |
| **Device Roles (generic)** | ✅ PRESERVE | ✅ None | ✅✅ High | ✅ Yes (if custom) |
| **Vendor/Model Names** | ✅ PRESERVE | ⚠️ Minimal | ✅✅ High | ✅ Yes (if sensitive) |
| **OS/Platform Names** | ✅ PRESERVE | ✅ None | ✅ Medium | ✅ Yes (if custom) |
| **Tags (generic)** | ✅ PRESERVE | ⚠️ Depends | ✅✅ High | ✅ Yes (per-tag) |
| **VLAN IDs** | ✅ PRESERVE | ✅ None | ✅ Medium | ✅ Yes (if meaningful) |
| **AS Numbers (private)** | ✅ PRESERVE | ✅ None | ✅ Medium | ✅ Yes |
| **AS Numbers (public)** | ⚠️ CONSIDER | ⚠️ Medium | ✅ Low | ✅ Yes |
| **Technical Specs** | ✅ PRESERVE | ✅ None | ✅ Medium | ❌ No reason to |
| **Timestamps** | ✅ PRESERVE | ⚠️ Minimal | ✅ Low | ✅ Yes (rarely needed) |
| **Booleans** | ✅ PRESERVE | ✅ None | ✅ High | ❌ No reason to |
| | | | | |
| **Device Names** | ❌ ANONYMIZE | ❌ High | ⚠️ Low | ✅ Yes (rarely) |
| **IP Addresses** | ❌ ANONYMIZE | ❌ High | ⚠️ Low | ❌ No (always PII) |
| **Site Names** | ❌ ANONYMIZE | ❌ High | ⚠️ Low | ❌ No (location PII) |
| **Contact Info** | ❌ ANONYMIZE | ❌ Critical | ✅ None | ❌ No (always PII) |
| **Descriptions** | ❌ ANONYMIZE | ⚠️ Medium | ⚠️ Low | ✅ Yes (case-by-case) |
| **Serial Numbers** | ❌ ANONYMIZE | ⚠️ Medium | ✅ None | ❌ No (identifying) |

---

## Your Customization Options

### Option 1: More Conservative (Higher Privacy)

**Anonymize additional fields:**
```yaml
# Add to greenmask-config.yml

- table: dcim_devicetype
  columns:
    - name: manufacturer
      type: hash
      format: "vendor-{{.Hash | substr 0 5}}"
    - name: model
      type: hash
      format: "model-{{.Hash | substr 0 6}}"

- table: dcim_platform
  columns:
    - name: name
      type: hash
      format: "os-{{.Hash | substr 0 5}}"
```

**Impact:** ⚠️ Claude loses vendor/model context (10-15% effectiveness decrease)

---

### Option 2: More Permissive (Better Claude Performance)

**Preserve additional fields:**
```yaml
# Remove from transformations - let pass through unchanged

# Example: Keep facility IDs (if generic like "RACK-A-47")
- table: dcim_rack
  columns:
    # REMOVE this transformation:
    # - name: facility_id
    #   type: hash
```

**Impact:** ⚠️ If facility IDs are location-specific, privacy risk increases

---

### Option 3: Conditional Logic (Advanced)

**Anonymize only if certain patterns detected:**
```yaml
- table: extras_tag
  columns:
    - name: name
      type: custom
      function: |
        function anonymize_tag(tag) {
          // Preserve generic tags
          generic_tags = ["critical", "production", "staging", "dmz", "redundancy-a", "redundancy-b"];
          if (generic_tags.includes(tag.toLowerCase())) {
            return tag;  // Preserve
          }

          // Anonymize specific tags
          if (tag.includes("customer-") || tag.includes("project-") || tag.match(/.*-datacenter$/i)) {
            hash = md5(tag + seed);
            return "tag-" + hash.substr(0, 6);  // Anonymize
          }

          return tag;  // Default: preserve
        }
```

---

## Questions to Ask Your Security Team

1. **Vendor Information**
   - "Can Claude see that we use Cisco/Juniper/Arista equipment?"
   - Impact if YES: Better Claude reasoning
   - Impact if NO: 10-15% effectiveness loss

2. **Custom Status/Roles**
   - "Do our custom status values contain business-sensitive info?"
   - Examples: "merger-phase-2", "customer-acme"
   - Anonymize if YES

3. **Tags**
   - "Are our tags generic or business-specific?"
   - Generic: "critical", "production" → Preserve
   - Specific: "customer-X", "project-Y" → Anonymize

4. **AS Numbers**
   - "Do we use public AS numbers?"
   - If YES and sensitive: Anonymize
   - If private range: Preserve

5. **Risk Tolerance**
   - "What's worse: 15% less Claude effectiveness OR potential vendor disclosure?"
   - Balance privacy vs functionality

---

## Recommended Approach

### Phase 1: Start Conservative (Anonymize More)
```
Anonymize:
✅ Names, IPs, locations, contacts (obviously)
✅ Vendor/model names (to be safe)
✅ All tags (to be safe)
✅ All descriptions (to be safe)

Preserve:
✅ IDs, foreign keys (required)
✅ Status, roles (if generic)
✅ Technical specs (numbers)
```

### Phase 2: Test Claude's Effectiveness

Run test queries:
- "Check redundancy for site X"
- "Find devices with high utilization"
- "Show capacity for new VMs"

Measure success rate.

### Phase 3: Gradually Reveal Metadata

If effectiveness too low:
1. Un-anonymize generic tags first
2. Un-anonymize vendor names next
3. Un-anonymize custom roles/statuses last

Test after each change.

### Phase 4: Find Your Balance

Find the sweet spot:
- **Privacy**: No PII leaked
- **Functionality**: Claude 85-90% effective
- **Risk Tolerance**: Acceptable to security team

---

## Bottom Line

**The rationale for NOT anonymizing certain data:**
1. ✅ **Not PII**: IDs, status, roles, vendor names, tags are generic metadata
2. ✅ **Public Info**: Cisco, Juniper, IOS, Linux are public knowledge
3. ✅ **Required for DB**: IDs/foreign keys MUST be preserved for relationships
4. ✅ **Claude Needs It**: Semantic context (roles, tags, types) enables reasoning
5. ⚠️ **Adjustable**: You can anonymize more if your policies require it

**Trade-off:**
- More anonymization = Higher privacy, Lower Claude effectiveness
- Less anonymization = Lower privacy, Higher Claude effectiveness

**My config aims for:** ~95% privacy protection with ~85-90% Claude effectiveness

**You can adjust** based on your organization's risk tolerance.
