# Channels vs Environment Pins: Complete Comparison

## Executive Summary

This document provides a **detailed comparison** between **Channels** and **Environment Pins**, explaining what each is, how they differ, when to use each, and real-world scenarios demonstrating their use cases.

---

## Table of Contents

1. [Quick Comparison](#1-quick-comparison)
2. [What are Channels?](#2-what-are-channels)
3. [What are Environment Pins?](#3-what-are-environment-pins)
4. [Key Differences](#4-key-differences)
5. [Resolution Priority](#5-resolution-priority)
6. [Real-World Scenarios](#6-real-world-scenarios)
7. [When to Use Each](#7-when-to-use-each)
8. [Combined Usage Patterns](#8-combined-usage-patterns)
9. [Decision Matrix](#9-decision-matrix)

---

## 1. Quick Comparison

| Aspect | Channels | Environment Pins |
|--------|----------|------------------|
| **Purpose** | Abstract names for configuration versions | Direct Git ref pinning per environment |
| **Scope** | Service-level (service specifies channel) | Environment-level (applies to all services in environment) |
| **Flexibility** | Services can choose different channels | All services in environment use same ref |
| **Update Frequency** | Updated frequently (promote next→stable) | Updated less frequently (stability focus) |
| **Use Case** | Gradual rollout, testing, service-specific | Production stability, environment consistency |
| **Abstraction** | High (channel name → Git ref) | Low (direct Git ref) |
| **Control** | Service/team controls channel choice | Platform team controls environment pins |

---

## 2. What are Channels?

### **Definition**

**Channels** are **abstract names** (like `stable`, `next`, `beta`) that map to Git refs. Services specify which channel they want to use, and the system resolves the channel to a Git ref.

### **Structure**

```yaml
# kustomize/catalog/channels.yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.07-rc1
  beta: refs/heads/develop
```

### **How Services Use Channels**

```yaml
# kustomize/catalog/services.yaml
services:
  - name: payment-processor
    channel: stable  # Service specifies channel
    # ... other config
```

### **Resolution**

```
Service specifies: channel: stable
    ↓
Lookup in channels.yaml: stable → refs/tags/config-2025.11.06
    ↓
Use configuration from that Git ref
```

### **Key Characteristics**

1. **Service-Level**: Each service can specify its own channel
2. **Abstract**: Services don't need to know specific Git refs
3. **Flexible**: Services can use different channels
4. **Centralized Mapping**: Channel → Git ref mapping in one place
5. **Easy Updates**: Change channel mapping, all services using that channel get update

---

## 3. What are Environment Pins?

### **Definition**

**Environment Pins** are **direct Git ref assignments** per environment. They provide a fallback mechanism when services don't specify a channel, ensuring all services in an environment use the same configuration version.

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
- Used when service has no channel AND no region pin
- Provides environment-level consistency

#### **defaultChannel Section**
- **Default channel** to use if service has no channel
- First resolves to channel, then to Git ref
- Provides abstraction layer

### **How Services Use Environment Pins**

```yaml
# Service has NO channel specified
services:
  - name: payment-processor
    # channel: (not specified)
    # ... other config
```

### **Resolution (Two Paths)**

**Path 1: Using defaultChannel**
```
Service has no channel
    ↓
Check defaultChannel for environment: int-stable → next
    ↓
Lookup next in channels.yaml: next → refs/tags/config-2025.11.07-rc1
    ↓
Use configuration from that Git ref
```

**Path 2: Using envPins directly**
```
Service has no channel
    ↓
No defaultChannel for environment (or defaultChannel not used)
    ↓
Use envPins directly: prod → refs/tags/config-2025.10.28
    ↓
Use configuration from that Git ref
```

### **Key Characteristics**

1. **Environment-Level**: Applies to all services in an environment
2. **Direct or Abstract**: Can use direct Git refs (envPins) or channels (defaultChannel)
3. **Consistent**: All services in environment use same version (if no channel specified)
4. **Fallback Mechanism**: Used when service doesn't specify channel
5. **Stability Focus**: Often pins production to older, proven versions

---

## 4. Key Differences

### **4.1 Scope of Control**

**Channels**:
- **Service-level control**: Each service chooses its channel
- Different services can use different channels
- Example: `payment-processor` uses `stable`, `test-service` uses `next`

**Environment Pins**:
- **Environment-level control**: All services in environment use same version (if no channel)
- Consistent across all services in environment
- Example: All services in `prod` use `refs/tags/config-2025.10.28`

### **4.2 Abstraction Level**

**Channels**:
- **High abstraction**: Channel name → Git ref (two-step resolution)
- Services reference abstract names (`stable`, `next`)
- Platform team controls Git ref mapping

**Environment Pins**:
- **Mixed abstraction**: Can be direct (envPins) or abstract (defaultChannel)
- `envPins` = Direct Git refs (low abstraction)
- `defaultChannel` = Channel names (high abstraction)

### **4.3 Update Frequency**

**Channels**:
- **Updated frequently**: As new versions are promoted
- `stable` channel updated when promoting `next` → `stable`
- Example: `stable: refs/tags/config-2025.11.06` → `stable: refs/tags/config-2025.11.07`

**Environment Pins**:
- **Updated less frequently**: Focus on stability
- Production often pinned to older, proven versions
- Example: `prod: refs/tags/config-2025.10.28` (stays on older version)

### **4.4 Flexibility**

**Channels**:
- **High flexibility**: Services can opt-in to different channels
- Easy to test new config (use `next` channel)
- Easy to rollback (change channel mapping)

**Environment Pins**:
- **Lower flexibility**: Environment-wide consistency
- All services in environment get same version (if no channel)
- Less granular control per service

### **4.5 Use Cases**

**Channels**:
- Gradual rollout of new configuration
- Service-specific testing
- Opt-in to new features
- A/B testing different configs

**Environment Pins**:
- Production stability (pin to proven version)
- Environment consistency (all services same version)
- Emergency rollback (quick revert)
- Default behavior when service doesn't specify channel

---

## 5. Resolution Priority

### **Complete Resolution Order**

```
1. Service channel (if specified)
   ↓ (if not found)
2. Region pin (if exists for region+environment)
   ↓ (if not found)
3. Environment pin (defaultChannel or envPins)
   ↓ (if not found)
4. Error
```

### **Resolution Examples**

#### **Example 1: Service with Channel**

```yaml
# Service
services:
  - name: payment-processor
    channel: stable  # ← Explicit channel

# Resolution
1. Service specifies channel: stable
2. Lookup channels.yaml: stable → refs/tags/config-2025.11.06
3. Use that ref
# Environment pins NOT used (service channel takes priority)
```

#### **Example 2: Service without Channel (Uses defaultChannel)**

```yaml
# Service
services:
  - name: payment-processor
    # channel: (not specified)

# Environment pins
envPins:
  int-stable: refs/tags/config-2025.11.06

defaultChannel:
  int-stable: next  # ← Default channel for int-stable

# Resolution
1. Service has no channel
2. Check defaultChannel for int-stable: next
3. Lookup channels.yaml: next → refs/tags/config-2025.11.07-rc1
4. Use that ref
# envPins NOT used (defaultChannel takes priority)
```

#### **Example 3: Service without Channel (Uses envPins directly)**

```yaml
# Service
services:
  - name: payment-processor
    # channel: (not specified)

# Environment pins
envPins:
  prod: refs/tags/config-2025.10.28
# No defaultChannel for prod

# Resolution
1. Service has no channel
2. No defaultChannel for prod
3. Use envPins directly: prod → refs/tags/config-2025.10.28
4. Use that ref
```

---

## 6. Real-World Scenarios

### **Scenario 1: Gradual Feature Rollout (Channels)**

**Situation**: Platform team adds new monitoring component. Want to test with some services first.

**Solution Using Channels**:

```yaml
# channels.yaml
channels:
  stable: refs/tags/config-2025.11.06  # Old config (no monitoring)
  next: refs/tags/config-2025.11.07-rc1  # New config (with monitoring)

# services.yaml
services:
  - name: payment-processor
    channel: next  # Opt-in to new monitoring
  - name: account-service
    channel: stable  # Stay on old config
  - name: user-service
    channel: stable  # Stay on old config
```

**Result**:
- ✅ `payment-processor` gets new monitoring (uses `next` channel)
- ✅ `account-service` and `user-service` stay on old config (use `stable`)
- ✅ Can test with one service, then promote when ready

**Why Channels Work Here**:
- Service-level control (each service chooses)
- Easy opt-in/opt-out
- Gradual rollout possible

**If Using Environment Pins Only**:
- ❌ All services in environment would get same version
- ❌ Can't test with subset of services
- ❌ All-or-nothing approach

---

### **Scenario 2: Production Stability (Environment Pins)**

**Situation**: Production needs to stay on older, proven configuration. Don't want accidental updates.

**Solution Using Environment Pins**:

```yaml
# env-pins.yaml
envPins:
  prod: refs/tags/config-2025.10.28  # Pinned to older version
  int-stable: refs/tags/config-2025.11.06  # Dev can use newer

# channels.yaml (updated frequently)
channels:
  stable: refs/tags/config-2025.11.07  # Newer version
  next: refs/tags/config-2025.11.08-rc1

# services.yaml
services:
  - name: payment-processor
    # channel: (not specified)  # Will use envPins
  - name: account-service
    # channel: (not specified)  # Will use envPins
```

**Result**:
- ✅ All services in `prod` use `config-2025.10.28` (pinned, older)
- ✅ All services in `int-stable` use `config-2025.11.06` (newer)
- ✅ Production protected from accidental updates
- ✅ Can update `channels.yaml` without affecting production

**Why Environment Pins Work Here**:
- Environment-level control (all services same version)
- Direct pinning (no channel resolution)
- Stability focus (pinned to proven version)

**If Using Channels Only**:
- ❌ Services using `stable` channel would get updates automatically
- ❌ Risk of accidental production updates
- ❌ Need to remember to not use `stable` in production

---

### **Scenario 3: Testing New Config (Channels)**

**Situation**: Platform team wants to test new configuration. Some services should test, others should not.

**Solution Using Channels**:

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

**Workflow**:
1. Platform team updates `next` channel to new config
2. `test-api-service` (using `next`) gets new config automatically
3. Test and validate
4. If successful, promote `next` → `stable`
5. All services using `stable` get new config

**Result**:
- ✅ Can test with specific services
- ✅ Production services unaffected during testing
- ✅ Easy promotion when ready

**Why Channels Work Here**:
- Service-level opt-in
- Easy to identify test services
- Single channel update affects all services using that channel

---

### **Scenario 4: Emergency Rollback (Environment Pins)**

**Situation**: Critical issue in production. Need to rollback all services immediately.

**Solution Using Environment Pins**:

```yaml
# env-pins.yaml (BEFORE - problematic)
envPins:
  prod: refs/tags/config-2025.11.07  # Current (has issue)

# env-pins.yaml (AFTER - rolled back)
envPins:
  prod: refs/tags/config-2025.10.28  # Rolled back to previous

# channels.yaml (unchanged)
channels:
  stable: refs/tags/config-2025.11.07  # Still points to problematic version
```

**Result**:
- ✅ All services in `prod` revert to `config-2025.10.28` immediately
- ✅ Single environment pin update affects all services
- ✅ Fast rollback (no need to update individual services)

**Why Environment Pins Work Here**:
- Environment-wide rollback
- Direct Git ref (no channel resolution needed)
- Fast and reliable

**If Using Channels Only**:
- Would need to update `channels.yaml` (affects all environments)
- Or update each service individually
- Slower and more error-prone

---

### **Scenario 5: Mixed Approach (Channels + Environment Pins)**

**Situation**: Want flexibility for some services, stability for others.

**Solution Using Both**:

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
    channel: stable  # Uses stable channel → config-2025.11.07
  - name: account-service
    # channel: (not specified)
    # In prod: Uses envPins → config-2025.10.28
    # In int-stable: Uses defaultChannel → next → config-2025.11.08-rc1
  - name: test-service
    channel: next  # Uses next channel → config-2025.11.08-rc1
```

**Result**:
- ✅ `payment-processor` in prod: Uses `stable` → `config-2025.11.07`
- ✅ `account-service` in prod: Uses `envPins` → `config-2025.10.28` (pinned, older)
- ✅ `account-service` in int-stable: Uses `defaultChannel` → `next` → `config-2025.11.08-rc1`
- ✅ `test-service`: Uses `next` → `config-2025.11.08-rc1`

**Why Both Work Together**:
- Channels provide flexibility (service-level choice)
- Environment pins provide stability (environment-level consistency)
- Best of both worlds

---

## 7. When to Use Each

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

---

## 8. Combined Usage Patterns

### **Pattern 1: Production Stability + Dev Flexibility**

```yaml
# channels.yaml
channels:
  stable: refs/tags/config-2025.11.07
  next: refs/tags/config-2025.11.08-rc1

# env-pins.yaml
envPins:
  prod: refs/tags/config-2025.10.28  # Prod pinned (stable)
  int-stable: refs/tags/config-2025.11.06

defaultChannel:
  int-stable: next  # Dev defaults to next (flexible)

# Result:
# - Prod services: Use envPins (pinned, stable)
# - Dev services: Use defaultChannel → next (flexible, latest)
# - Services can override: Specify channel to opt-in/out
```

### **Pattern 2: Gradual Production Rollout**

```yaml
# channels.yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.07-rc1

# env-pins.yaml
envPins:
  prod: refs/tags/config-2025.11.06  # Prod default (older)
  # No defaultChannel for prod

# services.yaml
services:
  - name: payment-processor
    channel: next  # Opt-in to new config in prod
  - name: account-service
    # channel: (not specified)  # Uses envPins (older)
```

**Result**:
- `payment-processor` in prod: Uses `next` → `config-2025.11.07-rc1` (new)
- `account-service` in prod: Uses `envPins` → `config-2025.11.06` (older)
- Can test with `payment-processor`, then promote when ready

### **Pattern 3: Environment-Specific Defaults**

```yaml
# channels.yaml
channels:
  stable: refs/tags/config-2025.11.07
  next: refs/tags/config-2025.11.08-rc1

# env-pins.yaml
envPins:
  prod: refs/tags/config-2025.10.28  # Prod pinned (older)

defaultChannel:
  int-stable: next  # Dev defaults to next
  pre-stable: stable  # Pre-stable defaults to stable
  prod: stable  # But prod uses envPins (takes priority)

# Result:
# - Services in int-stable (no channel): Use next (latest)
# - Services in pre-stable (no channel): Use stable (tested)
# - Services in prod (no channel): Use envPins (pinned, older)
```

---

## 9. Decision Matrix

### **Choose Channels If**:

| Requirement | Use Channels? | Why |
|-------------|--------------|-----|
| Different services need different configs | ✅ Yes | Service-level control |
| Want to test with subset of services | ✅ Yes | Easy opt-in/opt-out |
| Frequent config updates | ✅ Yes | Easy to promote next→stable |
| Service-specific testing | ✅ Yes | Each service chooses channel |
| A/B testing different configs | ✅ Yes | Services can use different channels |

### **Choose Environment Pins If**:

| Requirement | Use Environment Pins? | Why |
|-------------|----------------------|-----|
| All services in environment same version | ✅ Yes | Environment-level consistency |
| Production stability critical | ✅ Yes | Pin to proven version |
| Quick environment-wide rollback | ✅ Yes | Single update affects all |
| Default behavior for services | ✅ Yes | Fallback when no channel |
| Infrastructure differences per environment | ✅ Yes | Different configs per environment |

### **Use Both When**:

| Requirement | Use Both? | Why |
|-------------|----------|-----|
| Want flexibility + stability | ✅ Yes | Channels for flexibility, pins for stability |
| Production stability + dev flexibility | ✅ Yes | Prod pinned, dev uses channels |
| Gradual rollout with safety net | ✅ Yes | Test with channels, fallback to pins |
| Service opt-in with environment defaults | ✅ Yes | Services can override, environment provides default |

---

## Summary

### **Channels**:
- **Purpose**: Service-level configuration versioning
- **Abstraction**: High (channel name → Git ref)
- **Flexibility**: High (services choose channels)
- **Use When**: Gradual rollout, testing, service-specific needs

### **Environment Pins**:
- **Purpose**: Environment-level configuration consistency
- **Abstraction**: Mixed (direct refs or channels)
- **Flexibility**: Lower (environment-wide consistency)
- **Use When**: Production stability, environment consistency, rollback

### **Key Takeaway**:

**Channels** = **Flexibility** (service-level control, gradual rollout)
**Environment Pins** = **Stability** (environment-level consistency, proven versions)

**Best Practice**: Use **both together**:
- **Channels** for services that need flexibility
- **Environment Pins** for environments that need stability
- **defaultChannel** to provide environment-specific defaults

This combination provides the **flexibility of channels** with the **stability of environment pins**, enabling both gradual rollouts and production safety.

