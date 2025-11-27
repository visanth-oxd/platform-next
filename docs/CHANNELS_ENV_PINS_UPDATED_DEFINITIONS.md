# Channels and Environment Pins: Updated Definitions for New Architecture

## Executive Summary

This document provides **updated definitions** for Channels and Environment Pins that reflect the new architecture where resources are checked out from Git and copied locally to service folders. It includes detailed explanations, how they work in the new system, and real-world scenarios demonstrating their usage.

---

## Table of Contents

1. [Channel Definition (Updated)](#1-channel-definition-updated)
2. [Environment Pin Definition (Updated)](#2-environment-pin-definition-updated)
3. [How They Work in the New Architecture](#3-how-they-work-in-the-new-architecture)
4. [Resolution Process](#4-resolution-process)
5. [Real-World Scenarios](#5-real-world-scenarios)
6. [When to Use Each](#6-when-to-use-each)
7. [Best Practices](#7-best-practices)

---

## 1. Channel Definition (Updated)

### **What is a Channel?**

A **Channel** is an **abstract name** (like `stable`, `next`, `beta`) that maps to a **specific Git ref** (tag or commit) in the `platform-next` repository. When a service specifies a channel, the system:

1. **Resolves** the channel to a Git ref
2. **Checks out** the repository at that Git ref
3. **Copies** resources from that checked-out version to the service folder
4. **References** those copied resources as local paths in kustomization.yaml

### **Key Characteristics**

- **Abstract Name**: Services reference channels by name, not Git refs
- **Git Ref Mapping**: Channel → Git ref (defined in `channels.yaml`)
- **Version Control**: Determines which version of shared configuration to use
- **Service-Level**: Each service can specify its own channel
- **Centralized Control**: Platform team controls channel → Git ref mapping

### **Structure**

```yaml
# kustomize/catalog/channels.yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.07-rc1
  beta: refs/heads/develop
```

### **How It Works in the New Architecture**

```
Service specifies: channel: stable
    ↓
Lookup in channels.yaml: stable → refs/tags/config-2025.11.06
    ↓
Checkout repository at: refs/tags/config-2025.11.06
    ↓
Copy resources to service folder:
    • kustomize/cb-base → service folder
    • kustomize/archetype/api → service folder
    • kustomize/envs/int-stable → service folder
    • kustomize/regions/euw1 → service folder
    • kustomize/components/* → service folder
    ↓
kustomization.yaml references local paths:
    • kustomize/cb-base (local)
    • kustomize/archetype/api (local)
    • etc.
```

### **What Gets Copied**

When a channel is resolved to a Git ref, the following resources are copied from the checked-out repository:

- `kustomize/cb-base/` - Base configuration
- `kustomize/archetype/<ARCHETYPE>/` - Workload archetype
- `kustomize/envs/<ENV>/` - Environment overlay
- `kustomize/regions/<REGION>/` - Region overlay
- `kustomize/components/<COMPONENT>/` - Each enabled component

**All copied to**: `generated/<SERVICE>/<ENV>/<REGION>/kustomize/`

---

## 2. Environment Pin Definition (Updated)

### **What is an Environment Pin?**

An **Environment Pin** is a **direct Git ref assignment** or **default channel** per environment. It provides a fallback mechanism when services don't specify a channel, ensuring all services in an environment use the same configuration version by:

1. **Resolving** to a Git ref (directly or via defaultChannel)
2. **Checking out** the repository at that Git ref
3. **Copying** resources from that checked-out version to service folders
4. **Referencing** those copied resources as local paths in kustomization.yaml

### **Key Characteristics**

- **Environment-Level**: Applies to all services in an environment (if no channel specified)
- **Direct or Abstract**: Can use direct Git refs (`envPins`) or channels (`defaultChannel`)
- **Consistent**: All services in environment use same version (if no channel)
- **Fallback Mechanism**: Used when service doesn't specify channel
- **Stability Focus**: Often pins production to older, proven versions

### **Structure**

```yaml
# kustomize/catalog/env-pins.yaml
envPins:
  int-stable: refs/tags/config-2025.11.06
  pre-stable: refs/tags/config-2025.11.06
  prod: refs/tags/config-2025.10.28

defaultChannel:
  int-stable: next
  pre-stable: stable
  prod: stable
```

### **Two Sections Explained**

#### **envPins Section**
- **Direct Git ref pinning** per environment
- Used when service has no channel AND no region pin AND no defaultChannel
- Provides environment-level consistency with explicit Git refs

#### **defaultChannel Section**
- **Default channel** to use if service has no channel
- First resolves to channel, then to Git ref
- Provides abstraction layer (channel name → Git ref)

### **How It Works in the New Architecture**

**Path 1: Using defaultChannel**
```
Service has no channel
    ↓
Check defaultChannel for environment: int-stable → next
    ↓
Lookup next in channels.yaml: next → refs/tags/config-2025.11.07-rc1
    ↓
Checkout repository at: refs/tags/config-2025.11.07-rc1
    ↓
Copy resources to service folder
    ↓
kustomization.yaml references local paths
```

**Path 2: Using envPins directly**
```
Service has no channel
    ↓
No defaultChannel for environment (or defaultChannel not used)
    ↓
Use envPins directly: prod → refs/tags/config-2025.10.28
    ↓
Checkout repository at: refs/tags/config-2025.10.28
    ↓
Copy resources to service folder
    ↓
kustomization.yaml references local paths
```

---

## 3. How They Work in the New Architecture

### **3.1 Complete Resolution and Checkout Flow**

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Service Definition                                 │
├─────────────────────────────────────────────────────────────┤
│ services:                                                   │
│   - name: payment-processor                                 │
│     channel: stable  # OR no channel                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Resolution                                          │
├─────────────────────────────────────────────────────────────┤
│ IF channel specified:                                       │
│   → Lookup channels.yaml: stable → refs/tags/config-2025.11.06 │
│                                                              │
│ IF no channel:                                              │
│   → Check regionPins.$REGION.$ENV                          │
│   → IF exists: Use region pin Git ref                       │
│   → ELSE: Check defaultChannel.$ENV                         │
│   → IF exists: Resolve channel → Git ref                    │
│   → ELSE: Use envPins.$ENV → Git ref                       │
│                                                              │
│ Result: CONFIG_REF = refs/tags/config-2025.11.06           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Repository Checkout                                 │
├─────────────────────────────────────────────────────────────┤
│ 1. Clone platform-next repository                           │
│ 2. Checkout at CONFIG_REF:                                  │
│    git checkout refs/tags/config-2025.11.06                │
│ 3. Repository now at specific version                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Copy Resources                                      │
├─────────────────────────────────────────────────────────────┤
│ Copy from checked-out repository to service folder:         │
│ • kustomize/cb-base → generated/.../kustomize/cb-base      │
│ • kustomize/archetype/api → generated/.../kustomize/archetype/api │
│ • kustomize/envs/int-stable → generated/.../kustomize/envs/int-stable │
│ • kustomize/regions/euw1 → generated/.../kustomize/regions/euw1 │
│ • kustomize/components/* → generated/.../kustomize/components/* │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Generate kustomization.yaml                        │
├─────────────────────────────────────────────────────────────┤
│ References local paths only:                                │
│ resources:                                                   │
│   - kustomize/cb-base  # Local, from checked-out ref        │
│   - kustomize/archetype/api  # Local, from checked-out ref  │
│   - patches/resources-patch.yaml  # Generated from size    │
│   - monitoring/servicemonitor.yaml  # Generated from profile │
└─────────────────────────────────────────────────────────────┘
```

### **3.2 Key Difference from Old Architecture**

**Old Architecture**:
- Channels/env pins → Git refs embedded in kustomization.yaml
- Example: `git::https://...//kustomize/archetype/api?ref=refs/tags/config-2025.11.06`
- Kustomize resolves remote Git refs during build

**New Architecture**:
- Channels/env pins → Git ref used to checkout and copy resources
- Example: `kustomize/archetype/api` (local path)
- All resources are local, no Git access needed during build

---

## 4. Resolution Process

### **4.1 Complete Resolution Algorithm**

```bash
# Resolution logic in generate-kz.sh

# Step 1: Check if service specifies channel
CHANNEL=$(echo "$SERVICE_DATA" | yq eval '.channel // ""' -)

if [[ -n "$CHANNEL" ]]; then
  # Path A: Service has channel
  CONFIG_REF=$(yq eval ".channels.$CHANNEL" "$CATALOG_DIR/channels.yaml")
  
  if [[ -z "$CONFIG_REF" ]]; then
    echo "Error: Channel '$CHANNEL' not found in channels.yaml"
    exit 1
  fi
  
  echo "Using channel: $CHANNEL → $CONFIG_REF"
  
else
  # Path B: Service has no channel, check fallbacks
  
  # Step 2: Check region pins
  REGION_PIN=$(yq eval ".regionPins.$REGION.$ENV // \"\"" \
    "$CATALOG_DIR/region-pins.yaml")
  
  if [[ -n "$REGION_PIN" ]]; then
    CONFIG_REF="$REGION_PIN"
    echo "Using region pin: $REGION.$ENV → $CONFIG_REF"
    
  else
    # Step 3: Check defaultChannel
    DEFAULT_CHANNEL=$(yq eval ".defaultChannel.$ENV // \"\"" \
      "$CATALOG_DIR/env-pins.yaml")
    
    if [[ -n "$DEFAULT_CHANNEL" ]]; then
      # Resolve defaultChannel to Git ref
      CONFIG_REF=$(yq eval ".channels.$DEFAULT_CHANNEL" \
        "$CATALOG_DIR/channels.yaml")
      echo "Using defaultChannel: $ENV → $DEFAULT_CHANNEL → $CONFIG_REF"
      
    else
      # Step 4: Use envPins directly
      CONFIG_REF=$(yq eval ".envPins.$ENV" \
        "$CATALOG_DIR/env-pins.yaml")
      
      if [[ -z "$CONFIG_REF" ]]; then
        echo "Error: No config ref found for environment '$ENV'"
        exit 1
      fi
      
      echo "Using envPins: $ENV → $CONFIG_REF"
    fi
  fi
fi

# CONFIG_REF now contains the Git ref to checkout
echo "Final CONFIG_REF: $CONFIG_REF"
```

### **4.2 Resolution Priority**

```
Priority Order (highest to lowest):

1. Service channel (if specified)
   ↓
2. Region pin (if exists for region+environment)
   ↓
3. Environment defaultChannel (if exists)
   ↓
4. Environment envPins (direct Git ref)
   ↓
5. Error (if none found)
```

### **4.3 Resolution Examples**

#### **Example 1: Service with Channel**

```yaml
# Service
services:
  - name: payment-processor
    channel: stable

# Resolution
1. Service specifies channel: stable
2. Lookup channels.yaml: stable → refs/tags/config-2025.11.06
3. CONFIG_REF = refs/tags/config-2025.11.06
4. Checkout repository at that ref
5. Copy resources to service folder
```

#### **Example 2: Service without Channel (Uses defaultChannel)**

```yaml
# Service
services:
  - name: account-service
    # channel: (not specified)

# Environment pins
envPins:
  int-stable: refs/tags/config-2025.11.06

defaultChannel:
  int-stable: next

# Resolution
1. Service has no channel
2. No region pin for euw1+int-stable
3. Check defaultChannel for int-stable: next
4. Lookup channels.yaml: next → refs/tags/config-2025.11.07-rc1
5. CONFIG_REF = refs/tags/config-2025.11.07-rc1
6. Checkout repository at that ref
7. Copy resources to service folder
```

#### **Example 3: Service without Channel (Uses envPins directly)**

```yaml
# Service
services:
  - name: account-service
    # channel: (not specified)

# Environment pins
envPins:
  prod: refs/tags/config-2025.10.28
# No defaultChannel for prod

# Resolution
1. Service has no channel
2. No region pin for euw1+prod
3. No defaultChannel for prod
4. Use envPins directly: prod → refs/tags/config-2025.10.28
5. CONFIG_REF = refs/tags/config-2025.10.28
6. Checkout repository at that ref
7. Copy resources to service folder
```

---

## 5. Real-World Scenarios

### **Scenario 1: Gradual Configuration Rollout (Channels)**

**Situation**: Platform team updates API archetype with new security settings. Want to test with some services first.

**Setup**:
```yaml
# channels.yaml
channels:
  stable: refs/tags/config-2025.11.06  # Old config (no new security)
  next: refs/tags/config-2025.11.07-rc1  # New config (with new security)

# services.yaml
services:
  - name: payment-processor
    channel: next  # Opt-in to new security
  - name: account-service
    channel: stable  # Stay on old config
  - name: user-service
    channel: stable  # Stay on old config
```

**What Happens**:

**For payment-processor**:
1. Channel: `next` → `refs/tags/config-2025.11.07-rc1`
2. Checkout repository at `config-2025.11.07-rc1`
3. Copy resources (including new security settings) to:
   `generated/payment-processor/int-stable/euw1/kustomize/`
4. kustomization.yaml references: `kustomize/archetype/api` (with new security)

**For account-service and user-service**:
1. Channel: `stable` → `refs/tags/config-2025.11.06`
2. Checkout repository at `config-2025.11.06`
3. Copy resources (old security settings) to:
   `generated/account-service/int-stable/euw1/kustomize/`
4. kustomization.yaml references: `kustomize/archetype/api` (old security)

**Result**:
- ✅ `payment-processor` gets new security configuration
- ✅ `account-service` and `user-service` stay on old configuration
- ✅ Can test with one service, then promote when ready

**After Testing - Promote Channel**:
```yaml
# channels.yaml (updated)
channels:
  stable: refs/tags/config-2025.11.07  # Promoted from next
  next: refs/tags/config-2025.11.08-rc1
```

**Regenerate Services**:
- `account-service` and `user-service` (using `stable`) → Regenerate to get new ref
- New `kustomize/` folder copied from `config-2025.11.07`
- All services now use new security configuration

---

### **Scenario 2: Production Stability (Environment Pins)**

**Situation**: Production needs to stay on older, proven configuration. Don't want accidental updates.

**Setup**:
```yaml
# channels.yaml (updated frequently)
channels:
  stable: refs/tags/config-2025.11.07  # Newer version
  next: refs/tags/config-2025.11.08-rc1

# env-pins.yaml
envPins:
  prod: refs/tags/config-2025.10.28  # Pinned to older version
  int-stable: refs/tags/config-2025.11.06

# services.yaml
services:
  - name: payment-processor
    # channel: (not specified)  # Will use envPins
  - name: account-service
    # channel: (not specified)  # Will use envPins
```

**What Happens**:

**For payment-processor in prod**:
1. No channel specified
2. No region pin for euw1+prod
3. No defaultChannel for prod
4. Use envPins: `prod` → `refs/tags/config-2025.10.28`
5. Checkout repository at `config-2025.10.28` (older version)
6. Copy resources to:
   `generated/payment-processor/prod/euw1/kustomize/`
7. kustomization.yaml references: `kustomize/archetype/api` (older version)

**For payment-processor in int-stable**:
1. No channel specified
2. Use envPins: `int-stable` → `refs/tags/config-2025.11.06`
3. Checkout repository at `config-2025.11.06` (newer version)
4. Copy resources to:
   `generated/payment-processor/int-stable/euw1/kustomize/`
5. kustomization.yaml references: `kustomize/archetype/api` (newer version)

**Result**:
- ✅ All services in `prod` use older, proven configuration (`config-2025.10.28`)
- ✅ All services in `int-stable` use newer configuration (`config-2025.11.06`)
- ✅ Production protected from accidental updates
- ✅ Can update `channels.yaml` without affecting production

**When Ready to Update Production**:
```yaml
# env-pins.yaml (updated)
envPins:
  prod: refs/tags/config-2025.11.07  # Updated to newer version
```

**Regenerate Services**:
- All services in `prod` → Regenerate
- New `kustomize/` folder copied from `config-2025.11.07`
- Production now uses newer configuration

---

### **Scenario 3: Testing New Configuration (Channels)**

**Situation**: Platform team wants to test new configuration. Some services should test, others should not.

**Setup**:
```yaml
# channels.yaml
channels:
  stable: refs/tags/config-2025.11.06  # Current stable
  next: refs/tags/config-2025.11.07-rc1  # New config to test

# services.yaml
services:
  - name: payment-processor
    channel: stable  # Production service, stay on stable
  - name: test-api-service
    channel: next  # Test service, use new config
  - name: account-service
    channel: stable  # Production service, stay on stable
```

**What Happens**:

**For test-api-service**:
1. Channel: `next` → `refs/tags/config-2025.11.07-rc1`
2. Checkout repository at `config-2025.11.07-rc1`
3. Copy resources (new configuration) to:
   `generated/test-api-service/int-stable/euw1/kustomize/`
4. Service gets new configuration automatically

**For payment-processor and account-service**:
1. Channel: `stable` → `refs/tags/config-2025.11.06`
2. Checkout repository at `config-2025.11.06`
3. Copy resources (current configuration) to:
   `generated/payment-processor/int-stable/euw1/kustomize/`
4. Services stay on current configuration

**Workflow**:
1. Platform team updates `next` channel to new config
2. `test-api-service` (using `next`) gets new config automatically
3. Test and validate
4. If successful, promote `next` → `stable`
5. Regenerate services using `stable` to get new config

**Result**:
- ✅ Can test with specific services
- ✅ Production services unaffected during testing
- ✅ Easy promotion when ready

---

### **Scenario 4: Emergency Rollback (Environment Pins)**

**Situation**: Critical issue in production. Need to rollback all services immediately.

**Current State**:
```
generated/payment-processor/prod/euw1/
├── kustomization.yaml
├── kustomize/  # From refs/tags/config-2025.11.07 (problematic)
├── patches/
└── monitoring/
```

**Rollback**:
```yaml
# env-pins.yaml (BEFORE - problematic)
envPins:
  prod: refs/tags/config-2025.11.07  # Current (has issue)

# env-pins.yaml (AFTER - rolled back)
envPins:
  prod: refs/tags/config-2025.10.28  # Rolled back to previous
```

**Regenerate Services**:
```bash
# Regenerate all services in prod
for SERVICE in payment-processor account-service user-service; do
  ./scripts/generate-kz.sh "$SERVICE" prod euw1
done
```

**What Happens**:
1. Resolution: `prod` → `refs/tags/config-2025.10.28` (new env pin)
2. Checkout repository at `config-2025.10.28` (previous version)
3. Copy resources (working configuration) to:
   `generated/payment-processor/prod/euw1/kustomize/`
4. New `kustomize/` folder replaces old one
5. kustomization.yaml still references `kustomize/archetype/api` (but folder contents changed)

**Result**:
- ✅ All services in `prod` revert to `config-2025.10.28` immediately
- ✅ Single environment pin update affects all services
- ✅ Fast rollback (regenerate with old ref)
- ✅ No need to update individual services

---

### **Scenario 5: Mixed Approach (Channels + Environment Pins)**

**Situation**: Want flexibility for some services, stability for others.

**Setup**:
```yaml
# channels.yaml
channels:
  stable: refs/tags/config-2025.11.07
  next: refs/tags/config-2025.11.08-rc1

# env-pins.yaml
envPins:
  prod: refs/tags/config-2025.10.28  # Prod pinned to older version
  int-stable: refs/tags/config-2025.11.06

defaultChannel:
  int-stable: next  # Int-stable defaults to next channel

# services.yaml
services:
  - name: payment-processor
    channel: stable  # Explicit channel
  - name: account-service
    # channel: (not specified)  # Will use env pin or defaultChannel
  - name: test-service
    channel: next  # Explicit channel
```

**What Happens**:

**For payment-processor in prod**:
1. Channel: `stable` → `refs/tags/config-2025.11.07`
2. Checkout at `config-2025.11.07`
3. Copy resources to: `generated/payment-processor/prod/euw1/kustomize/`
4. Uses newer configuration (from channel)

**For account-service in prod**:
1. No channel specified
2. Use envPins: `prod` → `refs/tags/config-2025.10.28`
3. Checkout at `config-2025.10.28` (older version)
4. Copy resources to: `generated/account-service/prod/euw1/kustomize/`
5. Uses older configuration (from env pin)

**For account-service in int-stable**:
1. No channel specified
2. Use defaultChannel: `int-stable` → `next`
3. Resolve channel: `next` → `refs/tags/config-2025.11.08-rc1`
4. Checkout at `config-2025.11.08-rc1` (latest RC)
5. Copy resources to: `generated/account-service/int-stable/euw1/kustomize/`
6. Uses latest RC configuration (from defaultChannel)

**For test-service**:
1. Channel: `next` → `refs/tags/config-2025.11.08-rc1`
2. Checkout at `config-2025.11.08-rc1`
3. Copy resources to: `generated/test-service/int-stable/euw1/kustomize/`
4. Uses latest RC configuration (from channel)

**Result**:
- ✅ `payment-processor` in prod: Uses `stable` → newer config
- ✅ `account-service` in prod: Uses env pin → older config (stability)
- ✅ `account-service` in int-stable: Uses defaultChannel → latest RC (flexibility)
- ✅ `test-service`: Uses `next` → latest RC (testing)

**Key Insight**: Channels provide flexibility (service-level choice), while environment pins provide stability (environment-level consistency).

---

### **Scenario 6: Channel Promotion Workflow**

**Initial State**:
```yaml
# channels.yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.07-rc1
```

**Service Folders**:
```
generated/payment-processor/int-stable/euw1/
├── kustomization.yaml
├── kustomize/  # From refs/tags/config-2025.11.06 (stable)
├── patches/
└── monitoring/

generated/test-service/int-stable/euw1/
├── kustomization.yaml
├── kustomize/  # From refs/tags/config-2025.11.07-rc1 (next)
├── patches/
└── monitoring/
```

**Step 1: Test in Next Channel**
- `test-service` uses `next` channel
- Tests configuration from `config-2025.11.07-rc1`
- Validates in int-stable environment
- All tests pass ✅

**Step 2: Create Stable Tag**
```bash
git tag config-2025.11.07
git push origin config-2025.11.07
```

**Step 3: Promote Next to Stable**
```yaml
# channels.yaml (updated)
channels:
  stable: refs/tags/config-2025.11.07  # Promoted from next
  next: refs/tags/config-2025.11.08-rc1  # New next
```

**Step 4: Regenerate Services Using Stable**
```bash
# Regenerate services using stable channel
for SERVICE in payment-processor account-service; do
  ./scripts/generate-kz.sh "$SERVICE" int-stable euw1
done
```

**What Happens**:
1. Service channel: `stable` → `refs/tags/config-2025.11.07` (new)
2. Checkout repository at `config-2025.11.07`
3. Copy new resources to:
   `generated/payment-processor/int-stable/euw1/kustomize/`
4. New `kustomize/` folder replaces old one
5. kustomization.yaml still references `kustomize/archetype/api` (but folder contents updated)

**Result**:
- ✅ `payment-processor` and `account-service` now use `config-2025.11.07`
- ✅ `test-service` still uses `next` → `config-2025.11.08-rc1`
- ✅ All services using `stable` channel get new configuration

---

## 6. When to Use Each

### **Use Channels When**:

1. **Service-Level Control Needed**
   - Different services need different config versions
   - Example: Some services test new config, others stay on stable

2. **Gradual Rollout**
   - Want to test with subset of services first
   - Example: Test new monitoring with `payment-processor` only

3. **Frequent Updates**
   - Configuration changes frequently
   - Example: Weekly config updates, promote next→stable

4. **Service-Specific Testing**
   - Services need to opt-in to new features
   - Example: New service wants to use latest config

5. **A/B Testing**
   - Testing different configs with different services
   - Example: Half services use `stable`, half use `next`

### **Use Environment Pins When**:

1. **Environment Stability**
   - Production needs to stay on proven version
   - Example: Prod pinned to older, tested version

2. **Environment Consistency**
   - All services in environment should use same version
   - Example: All prod services use same config version

3. **Emergency Rollback**
   - Need quick, environment-wide rollback
   - Example: Critical issue, rollback all prod services

4. **Default Behavior**
   - Services don't specify channel, need default
   - Example: New services default to environment pin

5. **Infrastructure Differences**
   - Different environments have different requirements
   - Example: Prod uses older config, dev uses newer

### **Use Both Together**:

**Best Practice**: Use **both channels and environment pins**:
- **Channels** for services that need flexibility
- **Environment pins** for environments that need stability
- **defaultChannel** to provide environment-specific defaults

**Example**:
```yaml
# Services can opt-in to channels
services:
  - name: payment-processor
    channel: stable  # Explicit choice

# Or use environment defaults
services:
  - name: account-service
    # channel: (not specified)  # Uses defaultChannel or envPins
```

---

## 7. Best Practices

### **7.1 Channel Management**

**Channel Naming**:
- Use purpose-based names: `stable`, `next`, `beta`, `alpha`
- Don't use environment names: Avoid `prod`, `dev`, `test`

**Channel Promotion**:
- Always test in `next` before promoting to `stable`
- Create RC tags for testing: `config-YYYY.MM.DD-rc1`
- Promote only after validation

**Tag Naming**:
- Use consistent format: `config-YYYY.MM.DD`
- Include RC suffix for release candidates: `config-YYYY.MM.DD-rc1`

### **7.2 Environment Pin Management**

**Production Stability**:
- Pin production to older, proven versions
- Example: `prod: refs/tags/config-2025.10.28` (older)
- Update only after thorough testing

**Environment Defaults**:
- Use `defaultChannel` for flexibility
- Example: `int-stable: next` (dev gets latest)
- Use `envPins` for stability
- Example: `prod: refs/tags/config-2025.10.28` (prod stays on older)

**Rollback Strategy**:
- Keep previous stable tag available
- Quick rollback: Update env pin to previous tag
- Regenerate services to apply rollback

### **7.3 Service Configuration**

**When to Specify Channel**:
- Service needs specific version (newer or older)
- Service is testing new features
- Service needs to stay on older version

**When to Rely on Environment Pins**:
- Service should follow environment default
- No special version requirements
- Want environment-level consistency

### **7.4 Regeneration Strategy**

**When to Regenerate**:
- Channel promotion (update services using that channel)
- Environment pin update (update all services in environment)
- Service configuration change (archetype, profile, size)
- Profile updates (cost, monitoring)

**When NOT to Regenerate**:
- No changes to service or channels/env pins
- Want to keep existing version (explicit pinning)

**Regeneration Impact**:
- Updates `kustomize/` folder (from new Git ref)
- Keeps `patches/` and `monitoring/` (unless profiles changed)
- Updates kustomization.yaml (if structure changed)

---

## Summary

### **Channel Definition**

**Channel** = Abstract name that maps to Git ref, used to:
- Determine which Git ref to checkout
- Copy resources from that ref to service folder
- Provide service-level version control

**Key Points**:
- Service-level control (each service chooses)
- Abstract (services don't need Git refs)
- Centralized mapping (platform team controls)

### **Environment Pin Definition**

**Environment Pin** = Direct Git ref or default channel per environment, used to:
- Determine which Git ref to checkout (when service has no channel)
- Copy resources from that ref to service folders
- Provide environment-level version control

**Key Points**:
- Environment-level control (all services in environment)
- Direct or abstract (envPins or defaultChannel)
- Stability focus (often pins to proven versions)

### **How They Work Together**

1. **Service specifies channel** → Use channel → Git ref → Checkout → Copy
2. **Service has no channel** → Use region pin OR defaultChannel OR envPins → Git ref → Checkout → Copy
3. **All resources copied locally** → kustomization.yaml references local paths
4. **Deployment** → All resources local, no Git access needed

### **Real-World Usage**

- **Channels**: Gradual rollout, testing, service-specific needs
- **Environment Pins**: Production stability, environment consistency, rollback
- **Both Together**: Flexibility + stability, best of both worlds

This approach provides **flexible version control** (channels) with **stable defaults** (environment pins), all working through **local resource checkout** for efficient, GitOps-friendly deployments.

