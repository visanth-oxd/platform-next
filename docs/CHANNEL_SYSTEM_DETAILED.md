# Channel System: Detailed Explanation

## Executive Summary

The **Channel System** is a configuration versioning mechanism that allows services to reference different versions of the Kustomize configuration (archetypes, components, overlays) using abstract channel names (like `stable`, `next`) that map to specific Git refs (tags or commits). This enables controlled rollout of configuration changes across environments and regions.

---

## Table of Contents

1. [What is a Channel?](#1-what-is-a-channel)
2. [Why Use Channels?](#2-why-use-channels)
3. [Channel System Architecture](#3-channel-system-architecture)
4. [Channel Resolution Process](#4-channel-resolution-process)
5. [Channel Files Explained](#5-channel-files-explained)
6. [Complete Examples](#6-complete-examples)
7. [Channel vs Environment Pins vs Region Pins](#7-channel-vs-environment-pins-vs-region-pins)
8. [Channel Lifecycle](#8-channel-lifecycle)
9. [Best Practices](#9-best-practices)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. What is a Channel?

### **Definition**

A **Channel** is an **abstract name** (like `stable`, `next`, `beta`) that maps to a **specific Git ref** (tag or commit) in the `platform-next` repository. It provides a way to:

1. **Reference configuration versions** without hardcoding Git refs
2. **Control configuration rollouts** across environments
3. **Enable gradual adoption** of new configuration versions
4. **Support rollback** by switching channels

### **Key Concepts**

- **Channel Name**: Abstract identifier (`stable`, `next`, `beta`)
- **Git Ref**: Concrete Git reference (`refs/tags/config-2025.11.06`, `refs/heads/main`, commit SHA)
- **Mapping**: Channel → Git ref (defined in `channels.yaml`)
- **Resolution**: Service channel → Git ref → Checkout that ref → Use configuration

### **Example**

```yaml
# Service specifies channel
services:
  - name: payment-processor
    channel: stable  # Abstract channel name

# Channel maps to Git ref
channels:
  stable: refs/tags/config-2025.11.06  # Concrete Git ref

# Resolution: stable → refs/tags/config-2025.11.06
# System checks out that tag and uses configuration from that point
```

---

## 2. Why Use Channels?

### **Problem Channels Solve**

**Without Channels**:
- Services would need to hardcode Git refs in catalog
- Changing configuration version requires updating every service
- No easy way to test new configuration before production
- Difficult to rollback configuration changes

**With Channels**:
- Services reference abstract channel names
- Change channel mapping once, all services using that channel get update
- Easy to test new configuration (use `next` channel)
- Easy to rollback (change channel mapping to previous tag)

### **Benefits**

1. **Abstraction**: Services don't need to know specific Git refs
2. **Centralized Control**: Platform team controls channel mappings
3. **Gradual Rollout**: Test in `next`, promote to `stable`
4. **Rollback Safety**: Change channel mapping to rollback
5. **Environment Flexibility**: Different environments can use different channels

---

## 3. Channel System Architecture

### **System Components**

```
┌─────────────────────────────────────────────────────────────┐
│ Service Catalog (services.yaml)                            │
│                                                              │
│ services:                                                    │
│   - name: payment-processor                                  │
│     channel: stable  ← Service specifies channel            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Channel Mapping (channels.yaml)                            │
│                                                              │
│ channels:                                                    │
│   stable: refs/tags/config-2025.11.06  ← Maps to Git ref   │
│   next: refs/tags/config-2025.11.06-rc1                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Resolution Logic (generate-kz.sh)                          │
│                                                              │
│ 1. Read service.channel                                     │
│ 2. Lookup channel in channels.yaml                          │
│ 3. Get Git ref (e.g., refs/tags/config-2025.11.06)         │
│ 4. Checkout that ref (or use it for manifest generation)   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Configuration Used                                          │
│                                                              │
│ Uses configuration from the Git ref specified by channel    │
│ (archetypes, components, overlays from that ref)           │
└─────────────────────────────────────────────────────────────┘
```

### **Fallback Mechanism**

If a service doesn't specify a channel, the system uses a **fallback hierarchy**:

```
1. Service channel (if specified)
   ↓
2. Region pin (if exists for region+environment)
   ↓
3. Environment pin (default for environment)
```

---

## 4. Channel Resolution Process

### **Step-by-Step Resolution**

#### **Step 1: Read Service Channel**

```yaml
# kustomize/catalog/services.yaml
services:
  - name: payment-processor
    channel: stable  # ← Service specifies channel
```

**Script Logic**:
```bash
CHANNEL=$(echo "$SERVICE_DATA" | yq eval '.channel // ""' -)
# Result: CHANNEL="stable"
```

#### **Step 2: Check if Channel Exists**

```bash
if [[ -n "$CHANNEL" ]]; then
  # Channel specified, proceed to lookup
else
  # No channel, use fallback mechanism
fi
```

#### **Step 3: Lookup Channel in channels.yaml**

```yaml
# kustomize/catalog/channels.yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.06-rc1
```

**Script Logic**:
```bash
CONFIG_REF=$(yq eval ".channels.$CHANNEL" "$CATALOG_DIR/channels.yaml")
# Result: CONFIG_REF="refs/tags/config-2025.11.06"
```

#### **Step 4: Use Git Ref for Configuration**

The resolved Git ref is used to:
- **Checkout that ref** (if using Git-based resolution)
- **Reference that ref** in manifest generation
- **Use configuration from that point** (archetypes, components, overlays)

### **Complete Resolution Algorithm**

```bash
# From scripts/generate-kz.sh

# Resolve config ref
CHANNEL=$(echo "$SERVICE_DATA" | yq eval '.channel // ""' -)

if [[ -n "$CHANNEL" ]]; then
  # Option 1: Service specifies channel → use channels.yaml
  CONFIG_REF=$(yq eval ".channels.$CHANNEL" "$CATALOG_DIR/channels.yaml")
  
  if [[ -z "$CONFIG_REF" ]]; then
    echo "Error: Channel '$CHANNEL' not found in channels.yaml"
    exit 1
  fi
else
  # Option 2: No channel → check region pins
  REGION_PIN=$(yq eval ".regionPins.$REGION.$ENV // \"\"" "$CATALOG_DIR/region-pins.yaml")
  
  if [[ -n "$REGION_PIN" ]]; then
    # Region pin exists → use it
    CONFIG_REF="$REGION_PIN"
  else
    # Option 3: No region pin → use environment pin
    CONFIG_REF=$(yq eval ".envPins.$ENV" "$CATALOG_DIR/env-pins.yaml")
    
    if [[ -z "$CONFIG_REF" ]]; then
      echo "Error: No config ref found for environment '$ENV'"
      exit 1
    fi
  fi
fi

# CONFIG_REF now contains the Git ref to use
echo "Using config ref: $CONFIG_REF"
```

---

## 5. Channel Files Explained

### **5.1 channels.yaml**

**Purpose**: Maps abstract channel names to concrete Git refs

**Location**: `kustomize/catalog/channels.yaml`

**Structure**:
```yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.06-rc1
  beta: refs/heads/develop
  alpha: refs/heads/feature/config-updates
```

**Channel Types**:

| Channel | Purpose | Typical Git Ref | Use Case |
|---------|---------|----------------|----------|
| **stable** | Production-ready configuration | `refs/tags/config-YYYY.MM.DD` | Production environments |
| **next** | Release candidate configuration | `refs/tags/config-YYYY.MM.DD-rc1` | Pre-production testing |
| **beta** | Development configuration | `refs/heads/develop` | Integration testing |
| **alpha** | Experimental configuration | `refs/heads/feature/*` | Feature development |

**Example**:
```yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.06-rc1
```

**How It Works**:
- When a service specifies `channel: stable`, the system looks up `channels.stable`
- Gets the value: `refs/tags/config-2025.11.06`
- Uses configuration from that Git tag

**Updating Channels**:
```yaml
# To promote next → stable:
channels:
  stable: refs/tags/config-2025.11.06-rc1  # Changed from config-2025.11.06
  next: refs/tags/config-2025.11.07-rc1    # New next channel
```

**Impact**: All services using `stable` channel will now use the new configuration.

---

### **5.2 env-pins.yaml**

**Purpose**: Pins environments to specific Git refs (fallback when no channel specified)

**Location**: `kustomize/catalog/env-pins.yaml`

**Structure**:
```yaml
envPins:
  int-stable: refs/tags/config-2025.11.06
  pre-stable: refs/tags/config-2025.11.06
  prod: refs/tags/config-2025.10.28

defaultChannel:
  int-stable: next
  pre-stable: stable
  prod: stable
```

**envPins Section**:
- **Purpose**: Direct Git ref pinning per environment
- **Use Case**: When you want to pin an environment to a specific version
- **Example**: `prod: refs/tags/config-2025.10.28` (prod uses older, proven version)

**defaultChannel Section**:
- **Purpose**: Default channel to use if service doesn't specify channel
- **Use Case**: Environment-level channel preference
- **Example**: `int-stable: next` (int-stable prefers `next` channel by default)

**Resolution Logic**:
```bash
# If service has no channel:
# 1. Check defaultChannel for environment
# 2. If defaultChannel exists → use that channel → lookup in channels.yaml
# 3. If no defaultChannel → use envPins directly
```

**Example Flow**:
```yaml
# Service has no channel
services:
  - name: payment-processor
    # channel: (not specified)

# Resolution:
# 1. Check defaultChannel for int-stable → "next"
# 2. Lookup "next" in channels.yaml → refs/tags/config-2025.11.06-rc1
# 3. Use that ref
```

---

### **5.3 region-pins.yaml (Optional)**

**Purpose**: Override environment pins for specific regions

**Location**: `kustomize/catalog/region-pins.yaml`

**Structure**:
```yaml
regionPins:
  euw2:
    prod: refs/tags/config-2025.11.06  # DR region gets newer config
  euw1:
    int-stable: refs/tags/config-2025.11.06-rc1  # Primary region tests new config
```

**Use Case**:
- **DR Region**: May need newer configuration for failover scenarios
- **Primary Region**: May test new configuration before DR region
- **Regional Differences**: Different regions may have different infrastructure requirements

**Resolution Priority**:
```
1. Service channel (highest priority)
   ↓
2. Region pin (region + environment specific)
   ↓
3. Environment pin (environment default)
   ↓
4. Error (if none found)
```

---

## 6. Complete Examples

### **Example 1: Service with Channel**

**Service Definition**:
```yaml
# kustomize/catalog/services.yaml
services:
  - name: payment-processor
    archetype: api
    profile: public-api
    size: large
    channel: stable  # ← Explicit channel
    regions: [euw1]
    enabledIn: [int-stable, prod]
```

**Channel Mapping**:
```yaml
# kustomize/catalog/channels.yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.06-rc1
```

**Resolution**:
```bash
# Step 1: Read service channel
CHANNEL="stable"

# Step 2: Lookup in channels.yaml
CONFIG_REF="refs/tags/config-2025.11.06"

# Step 3: Use configuration from that tag
# All archetypes, components, overlays from config-2025.11.06 tag are used
```

**Result**: Service uses configuration from `config-2025.11.06` tag.

---

### **Example 2: Service without Channel (Uses Environment Pin)**

**Service Definition**:
```yaml
# kustomize/catalog/services.yaml
services:
  - name: account-service
    archetype: api
    profile: public-api
    size: medium
    # channel: (not specified)  ← No channel
    regions: [euw1]
    enabledIn: [int-stable]
```

**Environment Pins**:
```yaml
# kustomize/catalog/env-pins.yaml
envPins:
  int-stable: refs/tags/config-2025.11.06

defaultChannel:
  int-stable: next
```

**Resolution**:
```bash
# Step 1: Service has no channel
CHANNEL=""  # Empty

# Step 2: Check region pins (none for euw1+int-stable)
REGION_PIN=""  # Empty

# Step 3: Check defaultChannel for int-stable
DEFAULT_CHANNEL="next"

# Step 4: Lookup "next" in channels.yaml
CONFIG_REF="refs/tags/config-2025.11.06-rc1"
```

**Result**: Service uses `next` channel (via defaultChannel) → `config-2025.11.06-rc1` tag.

---

### **Example 3: Service with Region Pin Override**

**Service Definition**:
```yaml
# kustomize/catalog/services.yaml
services:
  - name: payment-processor
    archetype: api
    profile: public-api
    size: large
    # channel: (not specified)
    regions: [euw2]
    enabledIn: [prod]
```

**Environment Pins**:
```yaml
# kustomize/catalog/env-pins.yaml
envPins:
  prod: refs/tags/config-2025.10.28  # Prod default (older version)
```

**Region Pins**:
```yaml
# kustomize/catalog/region-pins.yaml
regionPins:
  euw2:
    prod: refs/tags/config-2025.11.06  # DR region gets newer config
```

**Resolution**:
```bash
# Step 1: Service has no channel
CHANNEL=""  # Empty

# Step 2: Check region pins for euw2+prod
REGION_PIN="refs/tags/config-2025.11.06"  # Found!

# Step 3: Use region pin (skips environment pin)
CONFIG_REF="refs/tags/config-2025.11.06"
```

**Result**: Service uses region pin → `config-2025.11.06` tag (newer than prod default).

**Why**: DR region (euw2) needs newer configuration for failover scenarios.

---

### **Example 4: Channel Promotion Workflow**

**Initial State**:
```yaml
# channels.yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.06-rc1
```

**Services**:
```yaml
# services.yaml
services:
  - name: payment-processor
    channel: stable  # Uses config-2025.11.06
  
  - name: account-service
    channel: next    # Uses config-2025.11.06-rc1 (testing)
```

**Step 1: Test New Configuration**
- `account-service` uses `next` channel
- Tests configuration from `config-2025.11.06-rc1`
- Validates in int-stable environment

**Step 2: Create New Stable Tag**
```bash
git tag config-2025.11.07
git push origin config-2025.11.07
```

**Step 3: Promote Next to Stable**
```yaml
# channels.yaml (updated)
channels:
  stable: refs/tags/config-2025.11.07  # Promoted from next
  next: refs/tags/config-2025.11.08-rc1  # New next channel
```

**Impact**:
- `payment-processor` (using `stable`) → Now uses `config-2025.11.07`
- `account-service` (using `next`) → Still uses `config-2025.11.08-rc1`

**Step 4: Rollback (if needed)**
```yaml
# channels.yaml (rollback)
channels:
  stable: refs/tags/config-2025.11.06  # Rolled back
  next: refs/tags/config-2025.11.07-rc1
```

**Impact**: `payment-processor` reverts to `config-2025.11.06`.

---

## 7. Channel vs Environment Pins vs Region Pins

### **Comparison Table**

| Mechanism | Purpose | Priority | Use Case |
|-----------|---------|----------|----------|
| **Service Channel** | Service-specific channel preference | **Highest** | Service wants specific channel |
| **Region Pin** | Region+environment specific ref | **Medium** | DR region needs different config |
| **Environment Pin** | Environment default ref | **Lowest** | Default for environment |

### **Resolution Priority**

```
1. Service channel (if specified)
   ↓
2. Region pin (if exists for region+environment)
   ↓
3. Environment pin (default for environment)
   ↓
4. Error (if none found)
```

### **When to Use Each**

#### **Use Service Channel When**:
- Service needs specific channel (e.g., `next` for testing)
- Service wants to opt-in to new configuration early
- Service needs to stay on older configuration

**Example**:
```yaml
services:
  - name: payment-processor
    channel: stable  # Explicit channel preference
```

#### **Use Region Pin When**:
- DR region needs different configuration than primary
- Regional infrastructure differences require different config
- Testing new config in one region before other

**Example**:
```yaml
regionPins:
  euw2:
    prod: refs/tags/config-2025.11.06  # DR region gets newer config
```

#### **Use Environment Pin When**:
- All services in environment should use same config version
- Environment needs to be pinned to specific version
- Default behavior when service doesn't specify channel

**Example**:
```yaml
envPins:
  prod: refs/tags/config-2025.10.28  # Prod uses older, proven version
```

---

## 8. Channel Lifecycle

### **Typical Workflow**

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Development                                         │
├─────────────────────────────────────────────────────────────┤
│ • Developer makes config changes                           │
│ • Commits to feature branch                                │
│ • Channel: alpha → refs/heads/feature/config-updates      │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Integration Testing                               │
├─────────────────────────────────────────────────────────────┤
│ • Merge to develop branch                                  │
│ • Channel: beta → refs/heads/develop                       │
│ • Services using beta channel test changes                 │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Release Candidate                                 │
├─────────────────────────────────────────────────────────────┤
│ • Create RC tag: config-2025.11.07-rc1                    │
│ • Channel: next → refs/tags/config-2025.11.07-rc1         │
│ • Services using next channel validate in pre-stable       │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┤
│ Phase 4: Production Release                               │
├─────────────────────────────────────────────────────────────┤
│ • Create stable tag: config-2025.11.07                     │
│ • Channel: stable → refs/tags/config-2025.11.07            │
│ • All services using stable channel get update             │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 5: Next Cycle                                         │
├─────────────────────────────────────────────────────────────┤
│ • Channel: next → refs/tags/config-2025.11.08-rc1         │
│ • Cycle repeats                                            │
└─────────────────────────────────────────────────────────────┘
```

### **Channel Update Process**

**Step 1: Create New Tag**
```bash
# After testing in next channel
git tag config-2025.11.07
git push origin config-2025.11.07
```

**Step 2: Update channels.yaml**
```yaml
# Before
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.07-rc1

# After
channels:
  stable: refs/tags/config-2025.11.07  # Updated
  next: refs/tags/config-2025.11.08-rc1  # New next
```

**Step 3: Commit and Push**
```bash
git add kustomize/catalog/channels.yaml
git commit -m "Promote config-2025.11.07 to stable channel"
git push
```

**Step 4: CI/CD Regenerates Manifests**
- CI detects change in `channels.yaml`
- Regenerates manifests for all services using `stable` channel
- Commits to `generated/` directory

**Step 5: Services Get New Configuration**
- Next deployment uses new manifests
- Services using `stable` channel now use `config-2025.11.07`

---

## 9. Best Practices

### **1. Channel Naming**

**Good**:
```yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.07-rc1
```

**Bad**:
```yaml
channels:
  prod: refs/tags/config-2025.11.06  # Don't use environment names
  test: refs/tags/config-2025.11.07-rc1  # Use purpose-based names
```

**Reason**: Channels represent configuration maturity, not environments.

### **2. Tag Naming Convention**

**Good**:
```yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.07-rc1
```

**Format**: `config-YYYY.MM.DD` or `config-YYYY.MM.DD-rcN`

**Benefits**:
- Chronological ordering
- Clear version identification
- Easy to find in Git history

### **3. Channel Promotion Strategy**

**Recommended Flow**:
1. **Development**: `alpha` → feature branch
2. **Integration**: `beta` → develop branch
3. **Testing**: `next` → RC tag
4. **Production**: `stable` → stable tag

**Don't Skip Steps**: Always test in `next` before promoting to `stable`.

### **4. Environment Pinning**

**Use Environment Pins for**:
- Production stability (pin to older, proven version)
- Emergency rollback (quick revert)
- Environment-specific requirements

**Example**:
```yaml
envPins:
  prod: refs/tags/config-2025.10.28  # Prod stays on older version
```

### **5. Service Channel Usage**

**Use Service Channels When**:
- Service needs early access to new config (`next` channel)
- Service needs to stay on older config (pin to specific tag via channel)
- Service-specific testing requirements

**Avoid**:
- Every service having different channels (hard to manage)
- Services using channels that don't exist

---

## 10. Troubleshooting

### **Problem 1: Channel Not Found**

**Error**:
```
Error: Channel 'stable' not found in channels.yaml
```

**Cause**: Service specifies channel that doesn't exist in `channels.yaml`.

**Solution**:
1. Check `channels.yaml` for available channels
2. Either:
   - Add the channel to `channels.yaml`, or
   - Update service to use existing channel

### **Problem 2: Git Ref Not Found**

**Error**:
```
Error: Git ref 'refs/tags/config-2025.11.06' not found
```

**Cause**: Channel maps to Git ref that doesn't exist.

**Solution**:
1. Verify tag exists: `git tag | grep config-2025.11.06`
2. If missing, create tag or update channel mapping

### **Problem 3: Service Using Wrong Configuration**

**Symptom**: Service uses configuration from wrong Git ref.

**Debugging**:
```bash
# 1. Check service channel
yq eval ".services[] | select(.name == \"payment-processor\") | .channel" \
  kustomize/catalog/services.yaml

# 2. Check channel mapping
yq eval ".channels.stable" kustomize/catalog/channels.yaml

# 3. Check resolution logic
./scripts/generate-kz.sh payment-processor int-stable euw1
# Look for "Using config ref: ..." message
```

**Solution**: Verify channel resolution chain (service → channel → Git ref).

### **Problem 4: Configuration Not Updating**

**Symptom**: Changed channel mapping, but services still use old config.

**Cause**: CI/CD hasn't regenerated manifests yet.

**Solution**:
1. Verify `channels.yaml` change is committed
2. Wait for CI/CD to regenerate manifests
3. Or manually trigger: `./scripts/generate-kz.sh <SERVICE> <ENV> <REGION>`

---

## Summary

**Channels** provide a **flexible, abstract way** to manage configuration versions:

1. **Service specifies channel** → `channel: stable`
2. **Channel maps to Git ref** → `stable: refs/tags/config-2025.11.06`
3. **System uses configuration from that ref** → All archetypes, components, overlays from that tag

**Benefits**:
- ✅ Abstraction (services don't need Git refs)
- ✅ Centralized control (platform team manages channels)
- ✅ Gradual rollout (test in `next`, promote to `stable`)
- ✅ Easy rollback (change channel mapping)

**Resolution Priority**:
1. Service channel (if specified)
2. Region pin (if exists)
3. Environment pin (default)

This system enables **controlled, versioned configuration management** at scale.

